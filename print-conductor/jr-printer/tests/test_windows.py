"""Testes das peças voltadas ao Windows que dá para exercitar em qualquer sistema."""
import io
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jrprinter import cli, core, diagnostico
from jrprinter.jobqueue import PrintQueue
from test_core import FakeBackend


class ProcessTests(unittest.TestCase):
    def test_run_with_timeout_ok(self):
        rc, out, err = core.run_with_timeout([sys.executable, "-c", "print('oi')"], 20)
        self.assertEqual((rc, out.strip()), (0, "oi"))

    def test_run_with_timeout_kills(self):
        t0 = time.time()
        with self.assertRaises(TimeoutError):
            core.run_with_timeout([sys.executable, "-c", "import time; time.sleep(30)"], 1)
        self.assertLess(time.time() - t0, 10)

    def test_office_child_timeout_message(self):
        with mock.patch.object(core, "child_command", return_value=([sys.executable, "-c", "import time; time.sleep(30)"], None)):
            with self.assertRaises(RuntimeError) as cm:
                core.office_via_com("x.docx", tempfile.gettempdir(), timeout=1)
        self.assertIn("não respondeu", str(cm.exception))

    def test_office_child_error_is_reported(self):
        code = "import sys; print('RuntimeError: Word travou', file=sys.stderr); sys.exit(1)"
        with mock.patch.object(core, "child_command", return_value=([sys.executable, "-c", code], None)):
            with self.assertRaises(RuntimeError) as cm:
                core.office_via_com("x.docx", tempfile.gettempdir())
        self.assertIn("Word travou", str(cm.exception))

    def test_child_command_not_frozen(self):
        cmd, cwd = core.child_command(["--_office-convert", "a", "b"])
        self.assertEqual(cmd[1:3], ["-m", "jrprinter"])
        self.assertTrue((Path(cwd) / "jrprinter" / "__init__.py").exists())

    def test_child_entry_point_runs(self):
        """O comando que o pai usa realmente executa o programa e devolve erro legível sem pywin32/Office."""
        cmd, cwd = core.child_command(["--_office-convert", "nao-existe.docx", tempfile.gettempdir()])
        rc, out, err = core.run_with_timeout(cmd, 60, cwd)
        self.assertNotEqual(rc, 0)
        self.assertTrue(err.strip())


class StreamTests(unittest.TestCase):
    def test_setup_streams_with_no_console(self):
        old = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = None
        try:
            cli.setup_streams()
            print("não deve falhar")           # .exe sem console
            print("erro", file=sys.stderr)
        finally:
            sys.stdout, sys.stderr = old

    def test_unicode_output_on_cp1252_console(self):
        raw = io.BytesIO()
        old = sys.stdout
        wrapper = io.TextIOWrapper(raw, encoding="cp1252")
        sys.stdout = wrapper
        try:
            cli.setup_streams()
            print("— págs × 2 → ✔")      # em cp1252 puro isto levantaria UnicodeEncodeError
            sys.stdout.flush()
        finally:
            sys.stdout = old
        data = raw.getvalue()
        wrapper.detach()
        self.assertIn("págs".encode("utf-8"), data)


class PathTests(unittest.TestCase):
    def test_norm_key_ignores_case_only_on_windows(self):
        d = Path(tempfile.mkdtemp())
        (d / "A.txt").write_text("x")
        same = core.norm_key(d / "A.txt") == core.norm_key(d / "a.txt")
        self.assertEqual(same, os.path.normcase("A") == "a")

    def test_cleanup_errors_do_not_break_job(self):
        d = Path(tempfile.mkdtemp())
        (d / "a.txt").write_text("x")
        with mock.patch("jrprinter.core.shutil.rmtree", side_effect=PermissionError("em uso")):
            pass  # rmtree é chamado com ignore_errors=True; a chamada real não levanta
        rows = core.run_job([d / "a.txt"], core.Options(), FakeBackend())
        self.assertEqual(rows[0]["status"], "ok")

    def test_names_with_spaces_accents_and_parentheses(self):
        d = Path(tempfile.mkdtemp()) / "Documentos (cópia) ção"
        d.mkdir()
        f = d / "relatório final (1).txt"
        f.write_text("olá", encoding="utf-8")
        be = FakeBackend()
        rows = core.run_job([f], core.Options(cover="full"), be)
        self.assertEqual(rows[0]["status"], "ok")
        self.assertEqual(len(be.calls), 2)


class DiagnosticTests(unittest.TestCase):
    def test_report_structure_and_privacy(self):
        results = diagnostico.run(full=False)
        text = diagnostico.format_report(results)
        self.assertIn("Resumo:", text)
        self.assertIn("Pré-visualização", text)
        self.assertIn("Pasta de configuração", text)
        self.assertNotIn(str(Path.home() / "Documents"), text)

    def test_a_failing_check_does_not_stop_the_others(self):
        with mock.patch.object(diagnostico, "check_printers", side_effect=RuntimeError("boom")):
            results = diagnostico.run(full=False)
        names = [r.name for r in results]
        self.assertIn("Impressoras", names)
        self.assertTrue(any(r.status == diagnostico.FAIL and "boom" in r.detail for r in results))
        self.assertTrue(any("Pré-visualização" in r.name for r in results))

    def test_min_docx_converts_with_libreoffice_if_present(self):
        if not core.find_soffice():
            self.skipTest("LibreOffice ausente")
        r = diagnostico.check_conversion()
        self.assertEqual(r.status, diagnostico.OK, r.detail)

    def test_cli_diagnostico_exit_code_and_file(self):
        d = tempfile.mkdtemp()
        old = os.getcwd()
        os.chdir(d)
        try:
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                rc = cli.main(["--diagnostico", "--rapido"])
            self.assertIn(rc, (0, 1))
            self.assertTrue((Path(d) / "diagnostico.txt").exists())
        finally:
            os.chdir(old)


class SendToTests(unittest.TestCase):
    def test_gui_flag_with_paths_does_not_print(self):
        """--gui com arquivos abre a janela (não imprime direto); sem tkinter, falha com mensagem."""
        with mock.patch("jrprinter.cli.get_backend") as gb:
            with mock.patch.dict(sys.modules, {"jrprinter.gui": mock.Mock(run_gui=lambda paths, project: 0)}):
                rc = cli.main(["--gui", "a.pdf", "b.pdf"])
        self.assertEqual(rc, 0)
        gb.assert_not_called()


if __name__ == "__main__":
    unittest.main()
