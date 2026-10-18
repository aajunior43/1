import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jrprinter import core, fileinfo, jobqueue, pdfgen
from jrprinter.core import Item, Options
from jrprinter.jobqueue import PrintQueue, sheets_for
from test_core import FakeBackend


def make_docx(path, pages):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("docProps/app.xml", f"<Properties><Pages>{pages}</Pages></Properties>")


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        for n in ("doc10.txt", "doc2.txt", "doc1.txt"):
            (self.d / n).write_text("x\n" * 130)          # 3 páginas de texto
        pdfgen.text_pdf(self.d / "p.pdf", "a\n" * 130)     # 3 páginas
        make_docx(self.d / "w.docx", 7)
        (self.d / "sub").mkdir()
        (self.d / "sub" / "z.txt").write_text("z")

    def names(self, q):
        return [i.path.name for i in q.items]

    def test_natural_sort(self):
        q = PrintQueue()
        q.add_paths([self.d], patterns=["doc*.txt"])
        self.assertEqual(self.names(q), ["doc1.txt", "doc2.txt", "doc10.txt"])
        q.sort("name")
        self.assertEqual(self.names(q), ["doc1.txt", "doc10.txt", "doc2.txt"])

    def test_page_counts(self):
        self.assertEqual(fileinfo.page_count(self.d / "p.pdf"), 3)
        self.assertEqual(fileinfo.page_count(self.d / "w.docx"), 7)
        self.assertEqual(fileinfo.page_count(self.d / "doc1.txt"), 3)
        self.assertEqual(fileinfo.count_range("1-3,5", 10), 4)
        self.assertEqual(fileinfo.count_range("2-", 5), 4)
        with self.assertRaises(ValueError):
            fileinfo.count_range("5-2", 9)
        with self.assertRaises(ValueError):
            fileinfo.count_range("abc", 9)

    def test_stats_and_sheets(self):
        q = PrintQueue()
        q.add_paths([self.d / "p.pdf", self.d / "w.docx"])
        s = q.stats(Options(copies=2))
        self.assertEqual((s["enabled"], s["pages"], s["sheets"]), (2, (3 + 7) * 2, (3 + 7) * 2))
        s = q.stats(Options(copies=2, duplex="long"))
        self.assertEqual(s["sheets"], (2 + 4) * 2)
        s = q.stats(Options(cover="filename"))
        self.assertEqual(s["sheets"], 3 + 7 + 2)
        q.set_overrides([0], pages="1-2")
        self.assertEqual(q.stats(Options())["pages"], 2 + 7)
        q.toggle([1], False)
        self.assertEqual(q.stats(Options())["enabled"], 1)
        self.assertEqual(sheets_for(None, 1, False), None)

    def test_move_and_undo(self):
        q = PrintQueue()
        q.add_paths([self.d], patterns=["doc*.txt"])
        a = self.names(q)
        self.assertEqual(q.move([0], +1), [1])
        self.assertEqual(self.names(q), [a[1], a[0], a[2]])
        q.move_to([2], 0)
        self.assertEqual(self.names(q), [a[2], a[1], a[0]])
        self.assertTrue(q.undo() and q.undo())
        self.assertEqual(self.names(q), a)
        self.assertTrue(q.redo())
        self.assertEqual(self.names(q), [a[1], a[0], a[2]])

    def test_group_by_folder(self):
        q = PrintQueue()
        q.add_paths([self.d], recursive=True, patterns=["*.txt"], sort="name")
        q.sort("folder")
        self.assertEqual(self.names(q)[-1], "z.txt")

    def test_duplicates(self):
        (self.d / "copia.txt").write_text("x\n" * 130)
        q = PrintQueue()
        q.add_paths([self.d], patterns=["*.txt"])
        issues = q.check()
        self.assertTrue(any("duplicado" in i.message for i in issues))
        removed = q.remove_duplicates()
        self.assertEqual(len(removed), 3)  # doc1, doc2, doc10 e copia são idênticos: sobra 1
        self.assertEqual(len(q), 1)

    def test_health_checks(self):
        (self.d / "vazio.txt").write_text("")
        (self.d / "~$lock.docx").write_text("x")
        (self.d / "a.xyz").write_text("x")
        enc = self.d / "enc.pdf"
        enc.write_bytes(b"%PDF-1.4\n1 0 obj<</Encrypt 2 0 R>>endobj\ntrailer<</Encrypt 2 0 R>>\n%%EOF")
        msgs = {i.path.name: i.message for i in fileinfo.check_files(
            [self.d / n for n in ("vazio.txt", "~$lock.docx", "a.xyz", "enc.pdf", "nao.txt")], False)}
        self.assertIn("vazio", msgs["vazio.txt"])
        self.assertIn("temporário", msgs["~$lock.docx"])
        self.assertIn("não suportado", msgs["a.xyz"])
        self.assertIn("protegido", msgs["enc.pdf"])
        self.assertIn("não encontrado", msgs["nao.txt"])

    def test_search_and_keep_matching(self):
        q = PrintQueue()
        q.add_paths([self.d], recursive=True)
        q.set_overrides([0], note="urgente")
        self.assertEqual(q.search("urgente"), [0])
        self.assertEqual(len(q.search("")), len(q))
        q.keep_matching(["*.pdf"])
        self.assertEqual(self.names(q), ["p.pdf"])

    def test_project_roundtrip(self):
        q = PrintQueue()
        q.add_paths([self.d / "p.pdf", self.d / "w.docx"])
        q.set_overrides([0], copies=3, pages="1-2", duplex="long", color="mono", note="n")
        q.toggle([1], False)
        f = self.d / "proj.jrq"
        q.save(f, Options(copies=5, cover="full"))
        q2, o2 = PrintQueue.load(f)
        self.assertEqual(q2.items[0].overrides(), {"copies": 3, "pages": "1-2", "duplex": "long", "color": "mono"})
        self.assertEqual(q2.items[0].note, "n")
        self.assertFalse(q2.items[1].enabled)
        self.assertEqual((o2.copies, o2.cover), (5, "full"))

    def test_overrides_validation(self):
        q = PrintQueue()
        q.add_paths([self.d / "p.pdf"])
        with self.assertRaises(ValueError):
            q.set_overrides([0], pages="9-1")
        with self.assertRaises(ValueError):
            q.set_overrides([0], copies=0)
        with self.assertRaises(ValueError):
            q.set_overrides([0], duplex="x")

    def test_job_overrides_disabled_divider_and_set_copies(self):
        q = PrintQueue()
        q.add_paths([self.d], recursive=True, patterns=["doc1.txt", "z.txt", "doc2.txt"], sort="folder")
        q.set_overrides([0], copies=4)
        q.toggle([1], False)
        be = FakeBackend()
        rows = core.run_job(q.items, Options(copies=2, folder_divider=True), be)
        self.assertEqual(sorted(r["status"] for r in rows), ["ignorado", "ok", "ok"])
        printed = [c for c in be.calls if c[1] not in ("separador de pasta",)]
        self.assertEqual(printed[0][2], 4)                  # ajuste do item
        self.assertEqual(printed[1][2], 2)                  # padrão
        self.assertEqual(sum(1 for c in be.calls if c[1] == "separador de pasta"), 2)  # duas pastas
        self.assertTrue(any(r["status"] == "ignorado" for r in rows))
        be2 = FakeBackend()
        core.run_job([Item(self.d / "doc1.txt")], Options(set_copies=3), be2)
        self.assertEqual(len(be2.calls), 3)


if __name__ == "__main__":
    unittest.main()
