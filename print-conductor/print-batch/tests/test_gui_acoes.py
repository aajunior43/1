"""Cada ação da interface é executada de verdade (com diálogos de arquivo e mensagens simulados)."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from printbatch import core, pdfgen
from test_gui_nup import _cancel_pending

try:
    import tkinter as tk
    HAS_TK = True
except ImportError:
    HAS_TK = False


@unittest.skipUnless(HAS_TK and os.environ.get("DISPLAY"), "precisa de tkinter e display (use xvfb-run)")
class GuiActionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = self.tmp / "cfg"
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.cfg), "APPDATA": str(self.cfg),
                                                "PATH": os.environ.get("PATH", "")})
        self.env.start()
        from printbatch import gui
        self.gui = gui
        self.docs = self.tmp / "docs"
        self.docs.mkdir()
        for n, body in (("carta.txt", "carta\n" * 30), ("nota10.txt", "nota\n" * 5), ("nota2.txt", "nota\n" * 9),
                        ("copia.txt", "carta\n" * 30)):
            (self.docs / n).write_text(body, encoding="utf-8")
        pdfgen.text_pdf(self.docs / "relatorio.pdf", "\n".join(f"Linha {i}" for i in range(120)))
        self.root = tk.Tk()
        self.app = gui.App(self.root, [str(self.docs)])
        self.root.update()
        self.msg = {
            "askyesno": mock.patch.object(gui.messagebox, "askyesno", return_value=True),
            "showinfo": mock.patch.object(gui.messagebox, "showinfo"),
            "showerror": mock.patch.object(gui.messagebox, "showerror"),
        }
        self.mocks = {k: v.start() for k, v in self.msg.items()}

    def tearDown(self):
        for v in self.msg.values():
            v.stop()
        _cancel_pending(self.root)
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

    def names(self):
        return [i.path.name for i in self.app.q.items]

    def select(self, *idx):
        self.app.tree.selection_set([str(i) for i in idx])
        self.root.update()

    # ---------------------------------------------------------------- fila
    def test_add_files_and_folder_through_dialogs(self):
        extra = self.tmp / "extra.txt"
        extra.write_text("x")
        with mock.patch.object(self.gui.filedialog, "askopenfilenames", return_value=(str(extra),)):
            self.app.add_files()
        self.assertIn("extra.txt", self.names())
        with mock.patch.object(self.gui.filedialog, "askdirectory", return_value=str(self.docs)):
            self.app.add_folder()                                  # pasta já na fila: não duplica
        self.assertEqual(self.names().count("carta.txt"), 1)

    def test_remove_clear_move_and_undo_redo(self):
        before = self.names()
        self.select(0)
        self.app.move(1)
        self.assertEqual(self.names()[1], before[0])
        self.app.undo()
        self.assertEqual(self.names(), before)
        self.app.redo()
        self.assertNotEqual(self.names(), before)
        self.app.undo()
        self.select(0)
        self.app.remove()
        after_remove = self.names()
        self.assertEqual(len(after_remove), len(before) - 1)
        self.assertNotIn(before[0], after_remove)
        self.app.clear()
        self.assertEqual(len(self.app.q.items), 0)
        self.app.undo()                                        # desfaz a limpeza: volta ao estado após remover
        self.assertEqual(self.names(), after_remove)

    def test_sort_filter_and_duplicates(self):
        self.app.sort.set("Nome")
        self.app.apply_sort()
        self.assertEqual(self.names()[0], "carta.txt")
        self.app.sort.set("Pasta")
        self.app.apply_sort()
        self.app.sort_by_column("nome")
        self.app.sort_by_column("nome")                            # segundo clique inverte
        self.assertTrue(self.app.sort_rev)
        self.app.filter.set("*.pdf")
        self.app.apply_filter()
        self.assertEqual(self.names(), ["relatorio.pdf"])
        self.app.undo()
        self.app.q.add_paths([self.docs], patterns=["*.txt"])
        self.app.remove_duplicates()
        self.assertEqual(self.names().count("copia.txt") + self.names().count("carta.txt"), 1)

    def test_marks_toggle_and_duplicate(self):
        self.select(0, 1)
        self.app.toggle_selected()
        self.assertFalse(self.app.q.items[0].enabled)
        self.app.set_enabled(True, all_rows=True)
        self.assertTrue(all(i.enabled for i in self.app.q.items))
        self.select(2)
        n = len(self.app.q.items)
        self.app.duplicate_selected()
        self.assertEqual(len(self.app.q.items), n + 1)
        self.assertEqual(self.names()[2], self.names()[3])     # a cópia fica logo depois do original

    def test_item_dialog_applies_and_clears_overrides(self):
        self.select(0)
        dlg = self.gui.ItemDialog(self.app, [0])
        self.root.update()
        dlg.copies.set("4")
        dlg.pages.set("1-2")
        dlg.duplex.set("Borda longa")
        dlg.color.set("Preto e branco")
        dlg.note.set("urgente")
        dlg.apply()
        it = self.app.q.items[0]
        self.assertEqual((it.copies, it.pages, it.duplex, it.color, it.note), (4, "1-2", "long", "mono", "urgente"))
        dlg2 = self.gui.ItemDialog(self.app, [0])
        dlg2.clear()
        it = self.app.q.items[0]
        self.assertEqual((it.copies, it.pages, it.duplex, it.color, it.note), (None, None, None, None, ""))

    def test_item_dialog_rejects_bad_values(self):
        self.select(0)
        dlg = self.gui.ItemDialog(self.app, [0])
        dlg.pages.set("9-2")
        dlg.apply()
        self.mocks["showerror"].assert_called()
        self.assertIsNone(self.app.q.items[0].pages)
        dlg.destroy()

    def test_open_reveal_and_menu(self):
        self.select(0)
        with mock.patch.object(self.gui, "open_path") as op, mock.patch.object(self.gui, "reveal") as rv:
            self.app.open_selected()
            self.app.reveal_selected()
        op.assert_called_once()
        rv.assert_called_once()
        ev = mock.Mock(x=5, y=5, x_root=10, y_root=10)
        with mock.patch.object(self.app.menu, "tk_popup") as pop:
            self.app.popup(ev)
        pop.assert_called_once()

    # ---------------------------------------------------------------- perfis e projetos
    def test_presets_save_load_delete(self):
        self.app.copies.set(3)
        self.app.preset.set("lote-contratos")
        self.app.save_preset()
        self.assertIn("lote-contratos", self.app.preset_cb["values"])
        self.app.copies.set(1)
        self.app.preset.set("lote-contratos")
        self.app.load_preset()
        self.assertEqual(self.app.copies.get(), 3)
        self.app.delete_preset()
        self.assertNotIn("lote-contratos", self.app.cfg.get("presets", {}))

    def test_project_save_and_open_via_dialogs(self):
        proj = self.tmp / "lote.pbq"
        with mock.patch.object(self.gui.filedialog, "asksaveasfilename", return_value=str(proj)):
            self.app.save_project()
        self.assertTrue(proj.exists())
        self.app.clear()
        with mock.patch.object(self.gui.filedialog, "askopenfilename", return_value=str(proj)):
            self.app.open_project_dialog()
        self.assertEqual(len(self.app.q.items), len(json.loads(proj.read_text(encoding="utf-8"))["items"]))

    def test_open_project_with_broken_file_shows_error(self):
        bad = self.tmp / "ruim.pbq"
        bad.write_text("{ não é json")
        self.app.open_project(str(bad))
        self.mocks["showerror"].assert_called()

    # ---------------------------------------------------------------- janelas
    def test_plan_shortcuts_and_verify_windows(self):
        self.app.show_plan()
        self.pump(0.2)
        self.app.show_shortcuts()
        (self.docs / "vazio.txt").write_text("")
        self.app.q.add_paths([self.docs / "vazio.txt"])
        self.app.refresh()
        self.app.verify()
        self.pump(0.2)
        tops = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)]
        titles = [t.title() for t in tops]
        self.assertTrue(any("Verificação" in t for t in titles), titles)
        self.assertTrue(any("Atalhos" in t for t in titles), titles)
        self.assertTrue(any("Plano" in t for t in titles), titles)
        self.assertIn("vazio.txt", [i.path.name for i in self.app.q.items])

    def test_verify_clean_queue_says_so(self):
        self.app.clear()
        self.app.add_paths([str(self.docs / "carta.txt")])
        self.app.verify()
        self.mocks["showinfo"].assert_called()

    def test_diagnostico_window_fills_report(self):
        self.app.show_diagnostico()
        deadline = time.time() + 60
        tops = []
        while time.time() < deadline:
            self.pump(0.3)
            tops = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)]
            if tops and "PrintBatch" in self._text_of(tops[-1]) and "Resumo" in self._text_of(tops[-1]):
                break
        self.assertTrue(tops)
        self.assertIn("Resumo", self._text_of(tops[-1]))

    def _text_of(self, win):
        for c in win.winfo_children():
            if isinstance(c, tk.Text):
                return c.get("1.0", "end")
        return ""

    def test_theme_and_preview_toggles(self):
        self.app.toggle_theme()
        self.assertEqual(self.app.mode, "dark")
        self.app.toggle_theme()
        self.assertEqual(self.app.mode, "light")
        self.app.toggle_preview()
        self.app.toggle_preview()

    # ---------------------------------------------------------------- pasta monitorada e histórico
    def test_watch_folder_start_and_stop(self):
        watched = self.tmp / "entrada"
        watched.mkdir()
        self.mocks["askyesno"].return_value = False            # não imprime sozinho
        with mock.patch.object(self.gui.filedialog, "askdirectory", return_value=str(watched)):
            self.app.toggle_watch()
        self.assertIsNotNone(self.app.watcher)
        (watched / "novo.txt").write_text("chegou\n" * 3)
        self.app.watch_tick()
        self.app.watch_tick()
        self.pump(0.1)
        self.assertIn("novo.txt", self.names())
        self.app.toggle_watch()                                # desliga
        self.assertIsNone(self.app.watcher)

    def test_history_missing_message(self):
        self.app.open_history()
        self.mocks["showinfo"].assert_called()

    def test_history_opens_when_exists(self):
        d = self.cfg / "PrintBatch"
        d.mkdir(parents=True, exist_ok=True)
        (d / "historico.csv").write_text("arquivo;status\n", encoding="utf-8")
        with mock.patch.object(self.gui, "open_path") as op:
            self.app.open_history()
        op.assert_called_once()

    def test_save_report_writes_rows(self):
        self.app.rows = [{"arquivo": "a.txt", "status": "ok", "detalhe": "", "hora": "t"}]
        dest = self.tmp / "rel.csv"
        with mock.patch.object(self.gui.filedialog, "asksaveasfilename", return_value=str(dest)):
            self.app.save_report()
        self.assertIn("a.txt", dest.read_text(encoding="utf-8-sig"))

    def test_close_saves_state_and_session(self):
        self.app.add_paths([str(self.docs / "carta.txt")])
        with mock.patch.object(self.app.root, "destroy") as destroy:
            self.app.on_close()
        destroy.assert_called_once()
        self.assertTrue((self.cfg / "PrintBatch" / "fila-anterior.pbq").exists())
        self.assertIn("geometry", json.loads((self.cfg / "PrintBatch" / "config.json").read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
