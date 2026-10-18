"""Diagnóstico e metadados de arquivos: caminhos que faltavam, com impressora simulada quando preciso."""
import os
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from printbatch import core, diagnostico, fileinfo, pdfgen
from test_e2e import FakePrinterMixin
from _plataforma import POSIX_ONLY


def zip_with(path, members):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return path


class FileInfoTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_pptx_slide_count_and_odt_page_count(self):
        pp = zip_with(self.d / "apresentacao.pptx", {"docProps/app.xml": "<Properties><Slides>12</Slides></Properties>"})
        od = zip_with(self.d / "texto.odt", {"meta.xml": '<meta:document-statistic meta:page-count="5"/>'})
        self.assertEqual(fileinfo.page_count(pp), 12)
        self.assertEqual(fileinfo.page_count(od), 5)

    def test_unknown_metadata_returns_none_not_error(self):
        vazio = zip_with(self.d / "vazio.docx", {"outro.xml": "x"})
        self.assertIsNone(fileinfo.page_count(vazio))
        self.assertIsNone(fileinfo.page_count(self.d / "nao-existe.docx"))

    def test_eml_counts_as_one_page_and_images_too(self):
        (self.d / "m.eml").write_text("Subject: x\n\ncorpo")
        self.assertEqual(fileinfo.page_count(self.d / "m.eml"), 1)

    def test_corrupt_pdf_is_flagged(self):
        bad = self.d / "corrompido.pdf"
        bad.write_bytes(b"isto nao e um pdf")
        issues = fileinfo.check_files([bad], find_duplicates=False)
        self.assertTrue(any("sem páginas" in i.message or "protegido" in i.message or "corrompido" in i.message
                            for i in issues), [i.message for i in issues])

    def test_office_without_converter_warns(self):
        doc = zip_with(self.d / "carta.docx", {"x": "y"})
        with mock.patch.object(core, "IS_WINDOWS", False), mock.patch.object(core, "find_soffice", return_value=None):
            issues = fileinfo.check_files([doc], find_duplicates=False)
        self.assertTrue(any("sem Office" in i.message for i in issues))

    def test_converter_available_on_linux_with_soffice(self):
        if not core.find_soffice():
            self.skipTest("LibreOffice ausente")
        with mock.patch.object(core, "IS_WINDOWS", False):
            self.assertTrue(fileinfo.converter_available())

    def test_temporary_and_system_files_are_flagged(self):
        t = self.d / "Thumbs.db"
        t.write_bytes(b"x")
        m = self.d / "~$contrato.docx"
        m.write_bytes(b"x")
        msgs = [i.message for i in fileinfo.check_files([t, m], find_duplicates=False)]
        self.assertTrue(all("temporário" in x for x in msgs), msgs)


class DiagnosticTests(FakePrinterMixin, unittest.TestCase):
    @POSIX_ONLY
    def test_printers_found_and_engine_present(self):
        r = diagnostico.check_printers()
        self.assertEqual(r.status, diagnostico.OK)
        self.assertIn("HP", r.detail)
        e = diagnostico.check_print_engine()
        self.assertEqual(e.status, diagnostico.OK)

    @POSIX_ONLY
    def test_no_printers_is_a_failure_with_hint(self):
        with mock.patch.dict(os.environ, {"FAKE_PRINTERS": ""}):
            r = diagnostico.check_printers()
        self.assertEqual(r.status, diagnostico.FAIL)
        self.assertTrue(r.hint)

    @POSIX_ONLY
    def test_missing_cups_is_a_failure(self):
        with mock.patch.dict(os.environ, {"PATH": str(self.tmp / "vazio")}):
            (self.tmp / "vazio").mkdir()
            r = diagnostico.check_print_engine()
        self.assertEqual(r.status, diagnostico.FAIL)

    @POSIX_ONLY
    def test_real_test_print_goes_through_lp(self):
        r = diagnostico.check_print_test("HP")
        self.assertEqual(r.status, diagnostico.OK, r.detail)
        calls = self.calls()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["args"][calls[0]["args"].index("-d") + 1], "HP")
        self.assertEqual(calls[0]["title"], "teste.pdf")

    def test_libreoffice_and_preview_checks(self):
        r = diagnostico.check_libreoffice()
        self.assertIn(r.status, (diagnostico.OK, diagnostico.WARN, diagnostico.INFO))
        if core.find_soffice():
            self.assertEqual(r.status, diagnostico.OK)
        self.assertEqual(diagnostico.check_preview().status, diagnostico.OK)
        with mock.patch("printbatch.preview.renderer_available", return_value=False):
            self.assertEqual(diagnostico.check_preview().status, diagnostico.WARN)

    def test_unwritable_config_folder_is_reported(self):
        blocker = self.tmp / "nao-e-pasta"
        blocker.write_text("x")
        with mock.patch.object(core, "config_dir", return_value=blocker):
            results = diagnostico.check_system()
        falhas = [r for r in results if r.name == "Pasta de configuração"]
        self.assertEqual(falhas[0].status, diagnostico.FAIL)

    @POSIX_ONLY
    def test_full_report_has_summary_and_privacy_line(self):
        text = diagnostico.format_report(diagnostico.run(full=False, printer="HP"))
        self.assertIn("Página de teste", text)
        self.assertIn("Resumo:", text)
        self.assertIn("não inclui nomes de arquivos", text)


if __name__ == "__main__":
    unittest.main()
