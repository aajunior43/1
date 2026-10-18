import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jrprinter import core, pdfgen, preview
from jrprinter.core import Item, Options
from jrprinter.jobqueue import PrintQueue
from test_core import FakeBackend

HAS = preview.renderer_available()
PNG = b"\x89PNG\r\n\x1a\n"


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        pdfgen.text_pdf(self.d / "a.pdf", "x\n" * 130)      # 3 págs
        (self.d / "sub").mkdir()
        pdfgen.text_pdf(self.d / "sub" / "b.pdf", "x\n" * 10)  # 1 pág

    def test_plan_sequence_and_sheets(self):
        q = PrintQueue()
        q.add_paths([self.d], recursive=True, sort="folder")
        steps = q.plan(Options(copies=2, cover="filename", folder_divider=True))
        kinds = [s["tipo"] for s in steps]
        self.assertEqual(kinds, ["separador", "rosto", "arquivo", "separador", "rosto", "arquivo"])
        self.assertEqual(steps[-1]["acumulado"], 1 + 1 + 6 + 1 + 1 + 2)
        self.assertEqual([s["passo"] for s in steps], list(range(1, 7)))

    def test_plan_matches_run_job_order(self):
        q = PrintQueue()
        q.add_paths([self.d], recursive=True, sort="folder")
        opts = Options(cover="filename", folder_divider=True, set_copies=2)
        be = FakeBackend()
        core.run_job(q.items, opts, be)
        self.assertEqual(len(be.calls), len(q.plan(opts)))
        self.assertEqual(sum(1 for c in be.calls if c[1] == "separador de pasta"), 4)  # 2 pastas x 2 conjuntos

    def test_test_print(self):
        items, o = core.as_test_job([Item(self.d / "a.pdf", copies=5, pages="2-3")],
                                    Options(copies=3, cover="full", set_copies=4, folder_divider=True))
        be = FakeBackend()
        core.run_job(items, o, be)
        self.assertEqual(len(be.calls), 1)
        self.assertEqual(be.calls[0][2], 1)
        self.assertEqual(items[0].pages, "1")


@unittest.skipUnless(HAS, "pypdfium2/pillow não instalados")
class RenderTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.pv = preview.Previewer()

    def test_pdf_pages(self):
        pdfgen.text_pdf(self.d / "a.pdf", "x\n" * 130)
        png, n = self.pv.render(self.d / "a.pdf", 0)
        self.assertTrue(png.startswith(PNG))
        self.assertEqual(n, 3)
        self.assertEqual(self.pv.render(self.d / "a.pdf", 99)[1], 3)  # índice é limitado

    def test_text_eml_image(self):
        (self.d / "t.txt").write_text("olá\n" * 5, encoding="utf-8")
        (self.d / "m.eml").write_bytes(b"From: a@x\nSubject: oi\n\ncorpo\n")
        from PIL import Image
        Image.new("RGB", (800, 600), "red").save(self.d / "i.png")
        for n in ("t.txt", "m.eml", "i.png"):
            png, pages = self.pv.render(self.d / n)
            self.assertTrue(png.startswith(PNG), n)
            self.assertEqual(pages, 1)

    def test_cover_and_errors(self):
        pdf = self.pv.cover_pdf(Options(cover="full"), self.d / "x.pdf", 1, 3)
        self.assertTrue(self.pv.render_pdf(pdf)[0].startswith(PNG))
        with self.assertRaises(preview.PreviewError):
            self.pv.render(self.d / "nao.pdf")
        bad = self.d / "bad.pdf"
        bad.write_bytes(b"isto nao e pdf")
        with self.assertRaises(preview.PreviewError):
            self.pv.render(bad)

    def test_cache_reuses_conversion(self):
        (self.d / "t.txt").write_text("x")
        self.assertEqual(self.pv.pdf_for(self.d / "t.txt"), self.pv.pdf_for(self.d / "t.txt"))


if __name__ == "__main__":
    unittest.main()
