"""Interface de verdade (xvfb) + impressora simulada: clique em Imprimir, cancelamento e reimpressão das falhas."""
import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from printbatch import core, pdfgen
from test_e2e import FakePrinterMixin

try:
    import tkinter as tk
    HAS_TK = True
except ImportError:
    HAS_TK = False


@unittest.skipUnless(HAS_TK and os.environ.get("DISPLAY"), "precisa de tkinter e display (use xvfb-run)")
class GuiPrintFlowTests(FakePrinterMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        from printbatch import gui
        self.gui = gui
        self.docs = self.tmp / "docs"
        self.docs.mkdir()
        for i in range(1, 4):
            (self.docs / f"contrato {i}.txt").write_text(f"contrato {i}\n" * 20, encoding="utf-8")
        pdfgen.text_pdf(self.docs / "anexo.pdf", "\n".join(f"Linha {i}" for i in range(120)))
        self.root = tk.Tk()
        self.app = gui.App(self.root, [str(self.docs)])
        self.root.update()
        self.confirm = mock.patch.object(gui.messagebox, "askyesno", return_value=True)
        self.confirm.start()
        self.info = mock.patch.object(gui.messagebox, "showinfo")
        self.info.start()

    def tearDown(self):
        self.confirm.stop()
        self.info.stop()
        from test_gui_nup import _cancel_pending  # noqa: E402  (mesmo auxiliar dos outros testes de interface)
        _cancel_pending(self.root)
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        super().tearDown()

    def wait_job(self, timeout=90):
        t = time.time()
        while time.time() - t < timeout:
            self.root.update()
            time.sleep(0.02)
            if self.app.worker is not None and not self.app.worker.is_alive() and self.app.events.empty():
                break
        for _ in range(10):
            self.root.update()
            time.sleep(0.02)

    def test_print_button_sends_every_marked_file_with_options(self):
        self.app.printer.set("HP")
        self.app.copies.set(2)
        self.app.start()
        self.wait_job()
        calls = self.calls()
        self.assertEqual(len(calls), 4)                                   # 3 .txt + 1 .pdf
        for c in calls:
            self.assertIn("-n", c["args"])
            self.assertEqual(c["args"][c["args"].index("-n") + 1], "2")
            self.assertEqual(c["args"][c["args"].index("-d") + 1], "HP")
        self.assertIn("Concluído", self.app.prog_label.cget("text"))
        self.assertTrue(all(v.startswith("✔") for v in self.app.status.values()), self.app.status)
        hist = (Path(self.cfg) / "PrintBatch" / "historico.csv")
        self.assertTrue(hist.exists())
        self.assertEqual(hist.read_text(encoding="utf-8-sig").count("\n"), 5)   # cabeçalho + 4

    def test_marked_off_files_are_not_sent(self):
        self.app.q.toggle([0], False)
        self.app.refresh()
        self.app.printer.set("HP")
        self.app.start()
        self.wait_job()
        self.assertEqual(len(self.calls()), 3)

    def test_sheets_from_gui_option(self):
        self.app.per_sheet.set("2 por folha")
        pdf_index = next(i for i, it in enumerate(self.app.q.items) if it.path.name == "anexo.pdf")
        self.app.q.toggle([i for i in range(len(self.app.q.items)) if i != pdf_index], False)
        self.app.refresh()
        self.app.printer.set("HP")
        self.app.start()
        self.wait_job()
        calls = self.calls()
        self.assertEqual(len(calls), 1)                                 # só o PDF marcado foi enviado
        self.assertIn("folhas", calls[0]["title"])                      # e saiu em folhas de 2 páginas
        self.assertIn("anexo", calls[0]["title"])

    def test_cancel_stops_the_batch(self):
        os.environ["FAKE_LP_SLEEP"] = "0.35"
        for i in range(4):
            (self.docs / f"extra {i}.txt").write_text("x\n" * 5, encoding="utf-8")
        self.app.q.add_paths([str(self.docs / f"extra {i}.txt") for i in range(4)])
        self.app.refresh()
        self.app.printer.set("HP")
        self.app.start()
        t = time.time()
        while time.time() - t < 30 and len(self.calls()) < 2:          # espera começar a imprimir
            self.root.update()
            time.sleep(0.02)
        self.app.cancel.set()
        self.wait_job()
        self.assertLess(len(self.calls()), len(self.app.q.items))
        self.assertIn("Cancelado", self.app.logbox.get("1.0", "end"))

    def test_reprint_only_failures(self):
        os.environ["FAKE_LP_FAIL"] = "anexo:1"
        self.app.printer.set("HP")
        self.app.retries.set(0)
        self.app.failed.set(False)
        self.app.start()
        self.wait_job()
        failed = [r for r in self.app.rows if r["status"] == "falhou"]
        self.assertEqual(len(failed), 1)
        self.assertIn("anexo", failed[0]["arquivo"])
        before = len(self.calls())
        self.app.retry_failed()
        self.wait_job()
        self.assertEqual(len(self.calls()) - before, 1)                 # só o arquivo que falhou foi reenviado
        enviados = [r["status"] for r in self.app.rows if r["status"] != "ignorado"]
        self.assertEqual(enviados, ["ok"])                              # os desmarcados aparecem como "ignorado"


if __name__ == "__main__":
    unittest.main()
