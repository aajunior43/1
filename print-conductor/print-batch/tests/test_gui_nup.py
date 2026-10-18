import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from printbatch import core, pdfgen

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


@unittest.skipUnless(HAS_TK and os.environ.get("DISPLAY"), "precisa de tkinter e display (xvfb-run)")
class GuiSheetsTests(unittest.TestCase):
    def setUp(self):
        self.cfg = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": self.cfg, "APPDATA": self.cfg})
        self.env.start()
        from printbatch import gui
        self.gui = gui
        self.d = Path(tempfile.mkdtemp())
        pdfgen.text_pdf(self.d / "relatorio.pdf", "\n".join(f"Linha {i}" for i in range(200)))   # 4 páginas
        self.root = tk.Tk()
        self.app = gui.App(self.root, [str(self.d / "relatorio.pdf")])
        self.root.update()

    def tearDown(self):
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

    def test_options_read_sheet_settings(self):
        self.app.per_sheet.set("4 por folha")
        self.app.sheet_border.set(False)
        o = self.app.options()
        self.assertEqual(o.per_sheet, 4)
        self.assertFalse(o.sheet_border)
        self.assertIsNone(o.cover_logo)

    def test_preview_shows_sheets_when_per_sheet(self):
        self.app.per_sheet.set("4 por folha")
        if not self.app.preview_on:
            self.app.toggle_preview()
        self.app.tree.selection_set("0")
        for _ in range(80):
            self.pump(0.1)
            if self.app.prev_total:
                break
        self.assertEqual(self.app.prev_total, 1)                   # 4 páginas em uma folha
        self.assertIn("folha 1 de 1", self.app.prev_page.cget("text"))
        self.assertIn("4 páginas por folha", self.app.prev_note.cget("text"))

    def test_summary_updates_with_sheets_and_cover(self):
        self.app.per_sheet.set("1 página (normal)")
        self.app.cover.set("Sem página de rosto")
        self.app.update_summary()
        base = self.app.summary.cget("text")
        self.app.per_sheet.set("4 por folha")
        self.assertNotEqual(self.app.summary.cget("text"), base)
        self.app.cover.set("Nome do arquivo")
        self.assertIn("folha", self.app.summary.cget("text"))
        self.assertIn("2", self.app.summary.cget("text").split("≈")[1].split()[0])   # 1 folha da página + 1 do rosto

    def test_state_roundtrip_includes_sheets_and_logo(self):
        self.app.per_sheet.set("6 por folha")
        self.app.sheet_border.set(False)
        st = self.app.get_state()
        self.app.per_sheet.set("1 página (normal)")
        self.app.set_state(st)
        self.assertEqual(self.app.per_sheet.get(), "6 por folha")
        self.assertFalse(self.app.sheet_border.get())

    def test_logo_choice_validates_image(self):
        bad = self.d / "texto.png"
        bad.write_text("nada")
        with mock.patch.object(self.gui.filedialog, "askopenfilename", return_value=str(bad)), \
                mock.patch.object(self.gui.messagebox, "showerror") as err:
            self.app.choose_logo()
        err.assert_called_once()
        self.assertEqual(self.app.cover_logo.get(), "")

        from PIL import Image
        good = self.d / "logo.png"
        Image.new("RGB", (120, 60), "navy").save(good)
        with mock.patch.object(self.gui.filedialog, "askopenfilename", return_value=str(good)):
            self.app.choose_logo()
        self.assertEqual(self.app.cover_logo.get(), str(good))
        self.assertEqual(self.app.logo_lbl.cget("text"), "logo.png")
        self.app.cover.set("Nome do arquivo")
        self.assertEqual(self.app.options().cover_logo, str(good))


if __name__ == "__main__":
    unittest.main()
