import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from printbatch import core
from printbatch.watcher import FolderWatcher


class WatcherTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "antigo.pdf").write_bytes(b"%PDF-1.4 old")

    def test_ignores_existing_and_needs_two_stable_scans(self):
        w = FolderWatcher(self.d)
        self.assertEqual(w.scan(), [])
        (self.d / "novo.pdf").write_bytes(b"%PDF-1.4 new")
        self.assertEqual(w.scan(), [])                     # 1ª leitura: ainda pode estar gravando
        self.assertEqual([f.name for f in w.scan()], ["novo.pdf"])
        self.assertEqual(w.scan(), [])                     # não repete

    def test_growing_file_waits(self):
        w = FolderWatcher(self.d)
        f = self.d / "baixando.pdf"
        f.write_bytes(b"a")
        w.scan()
        f.write_bytes(b"ab")                               # cresceu entre as leituras
        self.assertEqual(w.scan(), [])
        self.assertEqual(len(w.scan()), 1)

    def test_skips_temp_and_unsupported(self):
        w = FolderWatcher(self.d)
        for n in ("~$x.docx", "a.crdownload", "b.tmp", "c.xyz", "ok.txt"):
            (self.d / n).write_text("x")
        w.scan()
        self.assertEqual([f.name for f in w.scan()], ["ok.txt"])

    def test_empty_file_never_ready_until_content(self):
        w = FolderWatcher(self.d)
        f = self.d / "vazio.txt"
        f.write_text("")
        w.scan()
        self.assertEqual(w.scan(), [])
        f.write_text("agora tem")
        w.scan()
        self.assertEqual(len(w.scan()), 1)

    def test_vanishing_file_is_forgotten_and_filters_work(self):
        w = FolderWatcher(self.d, patterns=["*.pdf"])
        f = self.d / "x.pdf"
        f.write_bytes(b"1")
        w.scan()
        f.unlink()
        self.assertEqual(w.scan(), [])
        self.assertEqual(w.pending, {})
        (self.d / "y.txt").write_text("1")
        w.scan()
        self.assertEqual(w.scan(), [])                     # txt não casa com *.pdf

    def test_include_existing_and_recursive(self):
        (self.d / "sub").mkdir()
        (self.d / "sub" / "z.pdf").write_bytes(b"1")
        w = FolderWatcher(self.d, recursive=True, include_existing=True)
        w.scan()
        self.assertEqual(sorted(f.name for f in w.scan()), ["antigo.pdf", "z.pdf"])


try:
    import tkinter as tk
    HAS_TK = True
except ImportError:
    HAS_TK = False


@unittest.skipUnless(HAS_TK and os.environ.get("DISPLAY"), "precisa de tkinter e display (xvfb-run)")
class UiTests(unittest.TestCase):
    def setUp(self):
        self.cfg = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": self.cfg, "APPDATA": self.cfg})
        self.env.start()
        from printbatch import gui
        self.gui = gui
        self.d = Path(tempfile.mkdtemp())
        for n in ("a.txt", "b.txt"):
            (self.d / n).write_text("x\n" * 70)
        self.root = tk.Tk()
        self.app = gui.App(self.root, [])
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        self.env.stop()

    def pump(self, s=0.3):
        t = time.time()
        while time.time() - t < s:
            self.root.update()
            time.sleep(0.02)

    def test_empty_state_shows_and_hides(self):
        self.assertTrue(self.app.empty.winfo_ismapped())
        self.app.add_paths([str(self.d)])
        self.root.update()
        self.assertFalse(self.app.empty.winfo_ismapped())
        self.app.clear.__func__
        with mock.patch.object(self.gui.messagebox, "askyesno", return_value=True):
            self.app.clear()
        self.root.update()
        self.assertTrue(self.app.empty.winfo_ismapped())

    def test_tooltips_attached_to_buttons(self):
        found = []

        def walk(w):
            for c in w.winfo_children():
                if isinstance(c, (self.gui.ttk.Button, self.gui.ttk.Menubutton)) and str(c.cget("text")) in self.gui.TIPS:
                    found.append(str(c.cget("text")))
                walk(c)
        walk(self.root)
        for must in ("＋ Arquivos…", "✓ Verificar fila", "Ver plano…", "Mais ▾"):
            self.assertIn(must, found)
        tip = self.gui.Tooltip(self.app.btn_print, "teste", self.app.pal)
        tip.show()
        self.assertIsNotNone(tip.tip)
        tip.hide()
        self.assertIsNone(tip.tip)

    def test_shortcuts_window_and_f1(self):
        self.app.show_shortcuts()
        self.root.update()
        tops = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)]
        self.assertTrue(tops)
        labels = []

        def walk(w):
            for c in w.winfo_children():
                if isinstance(c, self.gui.ttk.Label):
                    labels.append(str(c.cget("text")))
                walk(c)
        walk(tops[-1])
        self.assertIn("Ctrl+P", labels)
        self.assertIn("F1", labels)

    def test_progress_label_and_eta(self):
        self.app.t0, self.app.done_n, self.app.total_n = time.time() - 30, 3, 10
        self.app.update_progress("x.pdf")
        txt = self.app.prog_label.cget("text")
        self.assertIn("3/10 (30%)", txt)
        self.assertIn("restam", txt)
        self.assertIn("x.pdf", txt)
        self.assertEqual(self.app.fmt_time(75), "01:15")

    def test_job_updates_progress_and_finishes(self):
        self.app.add_paths([str(self.d)])
        self.app.dry.set(True)
        self.app.start()
        for _ in range(100):
            self.pump(0.1)
            if str(self.app.btn_print["state"]) == "normal" and self.app.rows:
                break
        self.assertIn("Concluído", self.app.prog_label.cget("text"))
        self.assertEqual(self.app.done_n, 2)

    def test_start_only_prints_just_those_items(self):
        self.app.add_paths([str(self.d)])
        self.app.dry.set(True)
        only = [self.app.q.items[0]]
        self.app.start(only=only)
        for _ in range(100):
            self.pump(0.1)
            if str(self.app.btn_print["state"]) == "normal" and self.app.rows:
                break
        self.assertEqual(len(self.app.rows), 1)

    def test_monitor_adds_new_files_and_autoprints(self):
        self.app.dry.set(True)
        self.app.watcher = FolderWatcher(self.d)
        self.app.watch_auto = True
        self.app.watch_job = None
        (self.d / "chegou.txt").write_text("conteudo\n" * 3)
        self.app.watch_tick()                  # 1ª leitura
        self.app.root.after_cancel(self.app.watch_job)
        self.app.watch_tick()                  # 2ª leitura: estável, entra na fila e imprime
        self.app.root.after_cancel(self.app.watch_job)
        names = [i.path.name for i in self.app.q.items]
        self.assertEqual(names, ["chegou.txt"])
        for _ in range(100):
            self.pump(0.1)
            if str(self.app.btn_print["state"]) == "normal" and self.app.rows:
                break
        self.assertEqual([Path(r["arquivo"]).name for r in self.app.rows], ["chegou.txt"])
        self.app.stop_watch()
        self.assertIsNone(self.app.watcher)

    def test_sort_labels_fit(self):
        self.assertIn("Natural", self.gui.SORT_LABELS)


if __name__ == "__main__":
    unittest.main()
