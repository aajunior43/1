import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jrprinter import core, jobqueue, nup, pdfgen
from jrprinter.backends import Backend
from jrprinter.core import Item, Options

try:
    import pypdfium2 as pdfium
    from PIL import Image, ImageDraw
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False


def pages_in(pdf):
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return len(doc), doc[0].get_size() if len(doc) else None
    finally:
        doc.close()


def render_page(pdf, index=0, scale=1.0):
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return doc[index].render(scale=scale).to_pil().convert("RGB")
    finally:
        doc.close()


def pixels(img):
    return img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata()


class ParsePagesTests(unittest.TestCase):
    def test_ranges(self):
        self.assertEqual(nup.parse_pages("1-3,5", 10), [0, 1, 2, 4])
        self.assertEqual(nup.parse_pages("2-", 5), [1, 2, 3, 4])
        self.assertEqual(nup.parse_pages("3,1,1", 5), [0, 2])          # ordenado, sem repetição
        self.assertEqual(nup.parse_pages("", 3), [0, 1, 2])
        self.assertEqual(nup.parse_pages(None, 2), [0, 1])
        self.assertEqual(nup.parse_pages("4-99", 6), [3, 4, 5])        # corta no fim

    def test_invalid(self):
        for bad in ("5-2", "abc", "0-3", "1--2"):
            with self.assertRaises(ValueError, msg=bad):
                nup.parse_pages(bad, 10)


class GridTests(unittest.TestCase):
    def test_grid_sizes_and_orientation(self):
        expected = {(2, False): (2, 1), (2, True): (1, 2), (4, False): (2, 2), (4, True): (2, 2),
                    (6, False): (3, 2), (9, False): (3, 3)}
        for (n, land), rc in expected.items():
            w, h = nup.sheet_size("A4", land)
            self.assertEqual(nup.grid_for(n, w, h), rc, (n, land))

    def test_cells_inside_sheet_and_do_not_overlap(self):
        for n in (1, 2, 4, 6, 9):
            for land in (False, True):
                sw, sh = nup.sheet_size("A4", land)
                rects = nup.cells(n, sw, sh)
                self.assertEqual(len(rects), n)
                for x, y, w, h in rects:
                    self.assertGreaterEqual(x, 0)
                    self.assertGreaterEqual(y, 0)
                    self.assertLessEqual(x + w, sw + 1e-6)
                    self.assertLessEqual(y + h, sh + 1e-6)
                for i, a in enumerate(rects):
                    for b in rects[i + 1:]:
                        overlap_x = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
                        overlap_y = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
                        self.assertFalse(overlap_x > 1e-6 and overlap_y > 1e-6)

    def test_sheet_counts(self):
        self.assertEqual(nup.count_sheets(5, 4), 2)
        self.assertEqual(nup.count_sheets(4, 4), 1)
        self.assertEqual(nup.count_sheets(1, 9), 1)


@unittest.skipUnless(HAS_LIBS, "precisa de pypdfium2 e pillow")
class SheetBuildTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        pdfgen.text_pdf(self.d / "a.pdf", "\n".join(f"Linha {i}" for i in range(150)))   # 3 páginas
        Image.new("RGB", (300, 200), "red").save(self.d / "foto.png")

    def test_pages_per_sheet(self):
        self.assertEqual(nup.build_sheets(self.d / "a.pdf", self.d / "f1.pdf", 1), 3)
        self.assertEqual(pages_in(self.d / "f1.pdf")[0], 3)
        self.assertEqual(nup.build_sheets(self.d / "a.pdf", self.d / "f2.pdf", 2), 2)
        self.assertEqual(pages_in(self.d / "f2.pdf")[0], 2)
        self.assertEqual(nup.build_sheets(self.d / "a.pdf", self.d / "f4.pdf", 4), 1)
        self.assertEqual(pages_in(self.d / "f4.pdf")[0], 1)

    def test_sheet_is_paper_sized(self):
        nup.build_sheets(self.d / "a.pdf", self.d / "p.pdf", 4)
        _, size = pages_in(self.d / "p.pdf")
        self.assertEqual((round(size[0]), round(size[1])), (595, 842))
        nup.build_sheets(self.d / "a.pdf", self.d / "l.pdf", 4, landscape=True)
        _, size = pages_in(self.d / "l.pdf")
        self.assertEqual((round(size[0]), round(size[1])), (842, 595))
        nup.build_sheets(self.d / "a.pdf", self.d / "lt.pdf", 4, paper="Letter")
        _, size = pages_in(self.d / "lt.pdf")
        self.assertEqual((round(size[0]), round(size[1])), (612, 792))

    def test_page_range_selects_before_grouping(self):
        self.assertEqual(nup.build_sheets(self.d / "a.pdf", self.d / "r.pdf", 2, pages_spec="2-3"), 1)
        self.assertEqual(pages_in(self.d / "r.pdf")[0], 1)

    def test_empty_selection_and_bad_values(self):
        with self.assertRaises(RuntimeError):
            nup.build_sheets(self.d / "a.pdf", self.d / "x.pdf", 2, pages_spec="9-10")
        with self.assertRaises(ValueError):
            nup.build_sheets(self.d / "a.pdf", self.d / "x.pdf", 3)

    def test_image_source_and_content_in_cells(self):
        self.assertEqual(nup.build_sheets(self.d / "foto.png", self.d / "img.pdf", 4), 1)
        img = render_page(self.d / "img.pdf", scale=1.0)              # 595x842 px
        self.assertGreater(sum(1 for px in pixels(img) if px[0] > 200 and px[1] < 80), 500)   # há vermelho
        self.assertEqual(img.getpixel((5, 5))[0] > 240, True)          # margem branca

    def test_border_lines_only_when_asked(self):
        """A linha da borda superior da 1ª célula fica na altura do topo da margem (18 pt)."""
        nup.build_sheets(self.d / "a.pdf", self.d / "com.pdf", 4, border=True)
        nup.build_sheets(self.d / "a.pdf", self.d / "sem.pdf", 4, border=False)
        scale = nup.DPI / 72.0
        row = round(nup.MARGIN_PT * scale)
        def dark_fraction(pdf):
            img = render_page(pdf, scale=scale)
            xs = range(round(60 * scale), round(280 * scale))
            return sum(1 for x in xs if img.getpixel((x, row))[0] < 215) / len(xs)
        self.assertGreater(dark_fraction(self.d / "com.pdf"), 0.9)
        self.assertLess(dark_fraction(self.d / "sem.pdf"), 0.05)

    def test_first_page_is_top_left(self):
        """Com 2 por folha (uma em cima da outra), a 1ª página de texto aparece na metade de cima."""
        pdfgen.write_pdf(self.d / "marca.pdf", [pdfgen.Page(items=[("F1", 40, 50, 700, "TOPO")]),
                                                pdfgen.Page(items=[("F1", 40, 50, 700, "BASE")])])
        nup.build_sheets(self.d / "marca.pdf", self.d / "marca2.pdf", 2, border=False)
        img = render_page(self.d / "marca2.pdf", scale=1.0)
        h = img.height
        top_ink = sum(1 for x in range(img.width) for y in range(0, h // 2) if sum(img.getpixel((x, y))) < 300)
        bottom_ink = sum(1 for x in range(img.width) for y in range(h // 2, h) if sum(img.getpixel((x, y))) < 300)
        self.assertGreater(top_ink, 50)
        self.assertGreater(bottom_ink, 50)


@unittest.skipUnless(HAS_LIBS, "precisa de pypdfium2 e pillow")
class LogoTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        im = Image.new("RGBA", (400, 160), (0, 0, 0, 0))          # transparente, com um quadrado azul
        ImageDraw.Draw(im).rectangle([20, 20, 380, 140], fill=(0, 0, 255, 255))
        im.save(self.d / "logo.png")

    def test_load_logo_flattens_transparency(self):
        jpeg, w, h = nup.load_logo(self.d / "logo.png")
        self.assertEqual((w, h), (400, 160))
        self.assertTrue(jpeg.startswith(b"\xff\xd8"))
        im = Image.open(__import__("io").BytesIO(jpeg)).convert("RGB")
        self.assertGreater(im.getpixel((2, 2))[0], 200)            # canto transparente virou branco

    def test_cover_with_logo_shows_logo_at_top(self):
        logo = nup.load_logo(self.d / "logo.png")
        pdfgen.centered_page_pdf(self.d / "rosto.pdf", ["Contrato 1", "Pasta: x"], logo=logo)
        img = render_page(self.d / "rosto.pdf", scale=1.0)
        blue = [(x, y) for x in range(0, img.width, 2) for y in range(0, img.height, 2)
                if img.getpixel((x, y))[2] > 200 and img.getpixel((x, y))[0] < 80]
        self.assertGreater(len(blue), 200)
        self.assertLess(min(y for _, y in blue), img.height * 0.2)   # no topo
        self.assertLess(sum(1 for x, y in blue if y > img.height * 0.5), 5)

    def test_cover_without_logo_has_no_blue(self):
        pdfgen.centered_page_pdf(self.d / "sem.pdf", ["Contrato 1"])
        img = render_page(self.d / "sem.pdf", scale=1.0)
        blue = sum(1 for px in pixels(img) if px[2] > 200 and px[0] < 80)
        self.assertEqual(blue, 0)

    def test_logo_box_keeps_proportion(self):
        w, h = pdfgen.logo_box(800, 200)
        self.assertAlmostEqual(w / h, 4.0, places=2)
        self.assertLessEqual(w, 200 + 1e-6)
        w, h = pdfgen.logo_box(100, 400)
        self.assertLessEqual(h, 120 + 1e-6)


class OptionsAndCountingTests(unittest.TestCase):
    def test_validation(self):
        with self.assertRaises(ValueError):
            Options(per_sheet=3).validate()
        with self.assertRaises(ValueError):
            Options(cover_logo="nao-existe.png").validate()
        Options(per_sheet=9).validate()

    def test_sheets_for_with_pages_per_sheet_and_duplex(self):
        self.assertEqual(jobqueue.sheets_for(5, 2, False, 4), 2 * 2)          # 5 págs / 4 = 2 folhas, x2 cópias
        self.assertEqual(jobqueue.sheets_for(5, 1, True, 4), 1)              # 2 folhas em frente e verso = 1 papel
        self.assertEqual(jobqueue.sheets_for(5, 2, True), 6)                 # comportamento antigo preservado
        self.assertIsNone(jobqueue.sheets_for(None, 1, False, 4))

    def test_stats_and_plan_use_sheets(self):
        d = Path(tempfile.mkdtemp())
        pdfgen.text_pdf(d / "a.pdf", "x\n" * 300)          # 5 páginas
        q = jobqueue.PrintQueue()
        q.add_paths([d / "a.pdf"])
        s1 = q.stats(Options(per_sheet=1))
        s4 = q.stats(Options(per_sheet=4))
        self.assertEqual(s1["sheets"], 5)
        self.assertEqual(s4["sheets"], 2)
        self.assertEqual(s4["pages"], s1["pages"])          # páginas continuam as mesmas
        plan = q.plan(Options(per_sheet=4))
        self.assertEqual(plan[-1]["acumulado"], 2)


class FakeFolhas(Backend):
    def __init__(self):
        self.calls = []

    def print_file(self, path, opts, title=""):
        n = pages_in(path)[0] if HAS_LIBS and str(path).endswith(".pdf") else None
        self.calls.append((Path(path).name, title, opts.copies, opts.pages, opts.landscape, n))
        return "ok"


@unittest.skipUnless(HAS_LIBS, "precisa de pypdfium2 e pillow")
class JobTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        pdfgen.text_pdf(self.d / "a.pdf", "\n".join(f"Linha {i}" for i in range(150)))   # 3 páginas
        Image.new("RGB", (300, 200), "blue").save(self.d / "foto.png")

    def test_job_prints_sheets_not_pages(self):
        be = FakeFolhas()
        rows = core.run_job([self.d / "a.pdf"], Options(per_sheet=2, copies=2, pages="1-3", landscape=True), be)
        self.assertEqual(rows[0]["status"], "ok")
        name, title, copies, pages, landscape, n_pages = be.calls[0]
        self.assertEqual(n_pages, 2)                 # 3 páginas em folhas de 2 = 2 folhas
        self.assertEqual(copies, 2)                  # cópias continuam valendo
        self.assertIsNone(pages)                     # o intervalo já foi aplicado nas folhas
        self.assertFalse(landscape)                  # a orientação já foi aplicada na folha

    def test_job_with_cover_and_logo(self):
        logo_path = self.d / "logo.png"
        Image.new("RGB", (200, 100), "green").save(logo_path)
        be = FakeFolhas()
        core.run_job([self.d / "foto.png"], Options(cover="filename", cover_logo=str(logo_path), per_sheet=4), be)
        self.assertTrue(any(c[1].startswith("rosto") for c in be.calls))
        self.assertTrue(any(c[0].endswith(".pdf") and c[5] == 1 for c in be.calls if c[5]))

    def test_bad_logo_fails_before_printing_anything(self):
        bad = self.d / "isto_nao_e_imagem.png"
        bad.write_text("não é uma imagem")
        be = FakeFolhas()
        with self.assertRaises(RuntimeError) as cm:
            core.run_job([self.d / "a.pdf"], Options(cover="full", cover_logo=str(bad)), be)
        self.assertIn("logotipo", str(cm.exception))
        self.assertEqual(be.calls, [])

    def test_test_print_ignores_sheets(self):
        items, o = core.as_test_job([Item(self.d / "a.pdf")], Options(per_sheet=4, cover="full", cover_logo="x"))
        self.assertEqual(o.per_sheet, 1)
        self.assertIsNone(o.cover)


if __name__ == "__main__":
    unittest.main()
