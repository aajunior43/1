import csv
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jrprinter import core
from jrprinter.core import Item, Options
from jrprinter.backends import Backend
from jrprinter.jobqueue import PrintQueue


class Flaky(Backend):
    """Falha as primeiras `fails` chamadas por título."""
    def __init__(self, fails):
        self.fails, self.calls, self.seen = fails, [], {}

    def print_file(self, path, opts, title=""):
        n = self.seen[title] = self.seen.get(title, 0) + 1
        if n <= self.fails:
            raise RuntimeError("spooler ocupado")
        self.calls.append(title)
        return "ok"


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "a.txt").write_text("x")

    def run_job(self, fails, retries, **kw):
        events = []
        be = Flaky(fails)
        rows = core.run_job([self.d / "a.txt"], Options(retries=retries, retry_wait=0, **kw), be,
                            lambda k, **d: events.append(k))
        return rows, be, events

    def test_retry_recovers(self):
        rows, be, ev = self.run_job(fails=2, retries=2)
        self.assertEqual(rows[0]["status"], "ok")
        self.assertEqual(ev.count("retry"), 2)

    def test_retry_gives_up(self):
        rows, be, ev = self.run_job(fails=5, retries=1)
        self.assertEqual(rows[0]["status"], "falhou")
        self.assertIn("spooler ocupado", rows[0]["detalhe"])
        self.assertEqual(ev.count("retry"), 1)

    def test_no_duplicate_when_second_part_retries(self):
        """Rosto já impresso não é impresso de novo se só o arquivo falhou."""
        rows, be, ev = self.run_job(fails=1, retries=1, cover="filename")
        self.assertEqual(rows[0]["status"], "ok")
        self.assertEqual(sum(1 for t in be.calls if t.startswith("rosto")), 1)

    def test_default_has_no_retry(self):
        rows, be, ev = self.run_job(fails=1, retries=0)
        self.assertEqual(rows[0]["status"], "falhou")
        self.assertNotIn("retry", ev)

    def test_cancel_during_wait(self):
        cancel = threading.Event()
        cancel.set()
        be = Flaky(1)
        rows = core.run_job([self.d / "a.txt"], Options(retries=3, retry_wait=30), be, cancel=cancel)
        self.assertEqual(rows, [])             # cancelado antes de começar

    def test_retries_validation(self):
        with self.assertRaises(ValueError):
            Options(retries=11).validate()
        with self.assertRaises(ValueError):
            Options(retries=-1).validate()


class HistoryTests(unittest.TestCase):
    def test_append_history_keeps_header_once(self):
        d = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": d, "APPDATA": d}):
            rows = [{"arquivo": "a.pdf", "status": "ok", "detalhe": "", "hora": "t"}]
            p = core.append_history(rows, "HP")
            core.append_history(rows, "HP")
            lines = Path(p).read_text(encoding="utf-8-sig").splitlines()
            self.assertEqual(len(lines), 3)
            self.assertTrue(lines[0].startswith("arquivo;status"))
            self.assertEqual(list(csv.reader(lines[1:2], delimiter=";"))[0][-1], "HP")

    def test_empty_rows_do_nothing(self):
        self.assertIsNone(core.append_history([]))


class AssetTests(unittest.TestCase):
    def test_icon_files_exist_and_valid(self):
        a = Path(__file__).resolve().parent.parent / "jrprinter" / "assets"
        self.assertTrue((a / "icon.png").read_bytes().startswith(b"\x89PNG"))
        self.assertEqual((a / "icon.ico").read_bytes()[:4], b"\x00\x00\x01\x00")


try:
    import tkinter as tk
    HAS_TK = True
except ImportError:
    HAS_TK = False


def _cancel_pending(root):
    """Cancela retornos agendados (after) para não tentar rodar depois que a janela fechou."""
    try:
        for job in root.tk.splitlist(root.tk.call("after", "info")):
            root.after_cancel(job)
    except Exception:
        pass


@unittest.skipUnless(HAS_TK and os.environ.get("DISPLAY"), "precisa de tkinter e de um display (use xvfb-run)")
class GuiExtraTests(unittest.TestCase):
    def setUp(self):
        self.cfgdir = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": self.cfgdir, "APPDATA": self.cfgdir})
        self.env.start()
        from jrprinter import gui
        self.gui = gui
        self.d = Path(tempfile.mkdtemp())
        for n, size in (("b.txt", 5), ("a10.txt", 50), ("a2.txt", 20)):
            (self.d / n).write_text("x\n" * size)
        self.root = tk.Tk()

    def tearDown(self):
        _cancel_pending(self.root)
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        self.env.stop()

    def names(self, app):
        return [i.path.name for i in app.q.items]

    def test_sort_by_header_toggles(self):
        app = self.gui.App(self.root, [str(self.d)])
        app.sort_by_column("nome")
        self.assertEqual(self.names(app), ["a2.txt", "a10.txt", "b.txt"])
        app.sort_by_column("nome")
        self.assertEqual(self.names(app), ["b.txt", "a10.txt", "a2.txt"])
        self.assertIn("▼", self.root.nametowidget(app.tree).heading("nome", "text"))
        app.sort_by_column("tam")
        self.assertEqual(self.names(app)[0], "b.txt")

    def test_session_is_saved_and_offered_back(self):
        app = self.gui.App(self.root, [str(self.d)])
        app.on_close.__func__  # existe
        app.autosave()
        f = core.config_dir() / "fila-anterior.jrq"
        self.assertTrue(f.exists())
        q, _ = PrintQueue.load(f)
        self.assertEqual(len(q), 3)
        _cancel_pending(self.root)
        self.root.destroy()
        self.root = tk.Tk()
        with mock.patch.object(self.gui.messagebox, "askyesno", return_value=True) as ask:
            app2 = self.gui.App(self.root, [])
            app2.offer_restore()
        ask.assert_called_once()
        self.assertEqual(len(app2.q), 3)

    def test_geometry_and_columns_restored(self):
        core.save_config({"geometry": "1000x600+20+20", "col_widths": {"nome": 333, "xx": 1}})
        app = self.gui.App(self.root, [])
        self.root.update()
        self.assertEqual(int(app.tree.column("nome", "width")), 333)
        self.assertTrue(self.root.winfo_geometry().startswith("1000x600"))

    def test_retries_option_roundtrip_and_retry_failed(self):
        app = self.gui.App(self.root, [str(self.d)])
        app.retries.set(4)
        self.assertEqual(app.options().retries, 4)
        app.retries.set(99)
        self.assertEqual(app.options().retries, 10)
        app.rows = [{"arquivo": str(self.d / "b.txt"), "status": "falhou", "detalhe": "x", "hora": "t"}]
        with mock.patch.object(app, "start") as st:
            app.retry_failed()
        st.assert_called_once()
        self.assertEqual([i.path.name for i in app.q.items if i.enabled], ["b.txt"])


if __name__ == "__main__":
    unittest.main()
