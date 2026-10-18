import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jrprinter import core, pdfgen
from jrprinter.backends import CupsBackend, WindowsBackend, Backend


class FakeBackend(Backend):
    def __init__(self, fail_on=None):
        self.calls, self.fail_on = [], fail_on

    def print_file(self, path, opts, title=""):
        if self.fail_on and self.fail_on in title:
            raise RuntimeError("boom")
        self.calls.append((Path(path).name, title, opts.copies))
        return "ok"


EML = (b"From: a@x.com\nTo: b@x.com\nSubject: Oi\nDate: Mon, 1 Jan 2026 10:00:00 +0000\n"
       b"MIME-Version: 1.0\nContent-Type: multipart/mixed; boundary=B\n\n--B\nContent-Type: text/plain\n\ncorpo\n"
       b"--B\nContent-Type: text/plain; name=\"n.txt\"\nContent-Disposition: attachment; filename=\"n.txt\"\n\nanexo\n--B--\n")


class Tests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "b.txt").write_text("bbb")
        (self.d / "a.txt").write_text("a")
        (self.d / "c.pdf").write_bytes(b"%PDF-1.4")
        (self.d / "x.xyz").write_text("no")
        (self.d / "sub").mkdir()
        (self.d / "sub" / "d.txt").write_text("d")
        (self.d / "m.eml").write_bytes(EML)

    def test_collect_sort_filter(self):
        names = lambda fs: [f.name for f in fs]
        self.assertEqual(names(core.collect([self.d])), ["a.txt", "b.txt", "c.pdf", "m.eml"])
        self.assertIn("d.txt", names(core.collect([self.d], recursive=True)))
        self.assertEqual(names(core.collect([self.d], patterns=["*.pdf"])), ["c.pdf"])
        self.assertEqual(names(core.collect([self.d], sort="size", reverse=True))[0], "m.eml")
        self.assertEqual(len(core.collect([self.d, self.d])), 4)  # sem duplicatas

    def test_pdf_valid(self):
        p = pdfgen.text_pdf(self.d / "t.pdf", "linha\n" * 130 + "(parênteses) \\ ção")
        data = p.read_bytes()
        self.assertTrue(data.startswith(b"%PDF-1.4") and data.rstrip().endswith(b"%%EOF"))
        self.assertEqual(data.count(b"/Type /Page "), 3)
        try:
            import pypdf
            r = pypdf.PdfReader(str(p))
            self.assertEqual(len(r.pages), 3)
            self.assertIn("ção", r.pages[-1].extract_text())
        except ImportError:
            pass

    def test_cover_and_job(self):
        be = FakeBackend()
        opts = core.Options(copies=3, cover="filename-folder")
        files = core.collect([self.d], patterns=["*.txt"])
        rows = core.run_job(files, opts, be)
        self.assertEqual([r["status"] for r in rows], ["ok"] * 2)
        covers = [c for c in be.calls if c[0].startswith("_rosto")]
        self.assertEqual(len(covers), 2)
        self.assertTrue(all(c[2] == 1 for c in covers))          # rosto sempre 1 cópia
        self.assertTrue(all(c[2] == 3 for c in be.calls if not c[0].startswith("_rosto")))

    def test_failure_page_and_continue(self):
        be = FakeBackend(fail_on="a.txt")
        files = core.collect([self.d], patterns=["*.txt"])
        rows = core.run_job(files, core.Options(failed_page=True), be)
        self.assertEqual([r["status"] for r in rows], ["falhou", "ok"])
        self.assertTrue(any(c[0].startswith("_falha") for c in be.calls))

    def test_missing_file_fails_cleanly(self):
        rows = core.run_job([self.d / "nao.txt"], core.Options(), FakeBackend())
        self.assertEqual(rows[0]["status"], "falhou")

    def test_eml_attachments(self):
        be = FakeBackend()
        core.run_job([self.d / "m.eml"], core.Options(attachments=True), be)
        self.assertEqual(len(be.calls), 2)
        be2 = FakeBackend()
        core.run_job([self.d / "m.eml"], core.Options(attachments=False), be2)
        self.assertEqual(len(be2.calls), 1)

    def test_cancel(self):
        ev = threading.Event()
        ev.set()
        be = FakeBackend()
        core.run_job(core.collect([self.d]), core.Options(), be, cancel=ev)
        self.assertEqual(be.calls, [])

    def test_report(self):
        rows = [{"arquivo": "a", "status": "ok", "detalhe": "", "hora": "t"}]
        for ext in (".csv", ".json"):
            p = self.d / ("r" + ext)
            core.write_report(p, rows)
            self.assertIn("a", p.read_text(encoding="utf-8-sig"))

    def test_options_validate(self):
        with self.assertRaises(ValueError):
            core.Options(copies=0).validate()
        with self.assertRaises(ValueError):
            core.Options(cover="nope").validate()

    def test_cups_command(self):
        o = core.Options(printer="P", copies=2, duplex="short", pages="1-2", paper="A4", landscape=True, fit=True, color=False)
        c = CupsBackend().command(Path("/x/f.pdf"), o)
        self.assertEqual(c[:5], ["lp", "-n", "2", "-d", "P"])
        for part in ("sides=two-sided-short-edge", "media=A4", "landscape", "fit-to-page", "print-color-mode=monochrome"):
            self.assertIn(part, c)

    def test_windows_command(self):
        w = WindowsBackend(sumatra="C:\\S\\SumatraPDF.exe")
        o = core.Options(printer="HP LaserJet", copies=2, duplex="long", pages="1-3, 5", paper="A4", landscape=True, color=True)
        c = w.command(Path("f.pdf"), o)
        self.assertEqual(c[:3], ["C:\\S\\SumatraPDF.exe", "-print-to", "HP LaserJet"])
        self.assertEqual(c[c.index("-print-settings") + 1], "2x,duplex,1-3,5,paper=A4,landscape,noscale,color")
        self.assertIn("-silent", c)
        d = w.command(Path("f.pdf"), core.Options())
        self.assertEqual(d[1], "-print-to-default")
        self.assertEqual(d[d.index("-print-settings") + 1], "simplex,noscale")

    def test_cover_custom_text_tolerant(self):
        o = core.Options(cover_text="{name} {inexistente}\nTotal {total}")
        lines = core.cover_lines(o, Path("a.txt"), 1, 5)
        self.assertEqual(lines[1], "Total 5")
        self.assertIn("{inexistente}", lines[0])


if __name__ == "__main__":
    unittest.main()
