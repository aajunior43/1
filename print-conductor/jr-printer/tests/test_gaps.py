"""Caminhos que faltavam: validações, cancelamento na espera, falhas em cascata, comandos da CLI
(--plan, --stats, --test-print, sem CUPS, sem tkinter), LibreOffice simulado e registro de erros."""
import contextlib
import io
import os
import shutil
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _plataforma import POSIX_ONLY
from jrprinter import cli, core, pdfgen
from jrprinter.backends import Backend
from jrprinter.core import Item, Options
from test_core import FakeBackend


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = cli.main(argv)
        except SystemExit as e:
            rc = e.code
    return rc, out.getvalue(), err.getvalue()


class ValidationTests(unittest.TestCase):
    def test_messages(self):
        with self.assertRaisesRegex(ValueError, "duplex"):
            Options(duplex="diagonal").validate()
        with self.assertRaisesRegex(ValueError, "conjunto"):
            Options(set_copies=0).validate()
        with self.assertRaisesRegex(ValueError, "modelo de rosto"):
            Options(cover="inventado").validate()

    def test_item_overrides_duplex_off_and_color(self):
        it = Item(Path("a.pdf"), duplex="off", color="color")
        eff = it.effective(Options(duplex="long", color=False))
        self.assertIsNone(eff.duplex)
        self.assertTrue(eff.color)
        it2 = Item(Path("a.pdf"), color="mono")
        self.assertFalse(it2.effective(Options(color=None)).color)


class ReadTextTests(unittest.TestCase):
    def test_undefined_cp1252_bytes_fall_back_to_latin1(self):
        p = Path(tempfile.mkdtemp()) / "estranho.txt"
        p.write_bytes(b"ok \x81\x8d\x8f fim")
        self.assertIn("ok", core.read_text(p))

    def test_utf8_bom_and_cp1252(self):
        d = Path(tempfile.mkdtemp())
        (d / "a.txt").write_bytes("olá".encode("utf-8-sig"))
        (d / "b.txt").write_bytes("olá".encode("cp1252"))
        self.assertEqual(core.read_text(d / "a.txt"), "olá")
        self.assertEqual(core.read_text(d / "b.txt"), "olá")


class RetryAndFailureTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "a.txt").write_text("x")

    def test_cancel_while_waiting_to_retry(self):
        class AlwaysFail(Backend):
            def print_file(self, path, opts, title=""):
                raise RuntimeError("fila cheia")
        cancel = threading.Event()
        events = []

        def on_event(kind, **k):
            events.append(kind)
            if kind == "retry":
                cancel.set()                              # cancela durante a espera
        rows = core.run_job([self.d / "a.txt"], Options(retries=3, retry_wait=5), AlwaysFail(), on_event, cancel)
        self.assertEqual(rows[0]["status"], "falhou")
        self.assertIn("retry", events)
        self.assertNotIn("ok", events)

    def test_failure_page_that_also_fails_is_reported(self):
        class OnlyTheFile(Backend):
            def print_file(self, path, opts, title=""):
                if "falha" in title or "aviso" in title:
                    raise RuntimeError("impressora desligada")
                raise RuntimeError("arquivo recusado")
        events = []
        rows = core.run_job([self.d / "a.txt"], Options(failed_page=True), OnlyTheFile(),
                            lambda k, **d: events.append((k, d.get("error", ""))))
        self.assertEqual(rows[0]["status"], "falhou")
        self.assertTrue(any("também falhou" in e for k, e in events if k == "error"))

    def test_msg_requires_windows(self):
        with self.assertRaisesRegex(RuntimeError, "Windows"):
            core.prepare(self.d / "mensagem.msg", self.d, Options())

    def test_unknown_format_in_prepare(self):
        f = self.d / "x.xyz"
        f.write_text("x")
        with self.assertRaisesRegex(RuntimeError, "formato não suportado"):
            core.prepare(f, self.d, Options())


class LibreOfficeTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.doc = self.d / "doc.docx"
        self.doc.write_bytes(b"PK")

    def test_no_libreoffice_message(self):
        with mock.patch.object(core, "find_soffice", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "LibreOffice não encontrado"):
                core.office_via_libreoffice(self.doc, self.d)

    @POSIX_ONLY
    def test_conversion_that_produces_no_pdf(self):
        fake = self.d / "soffice"
        fake.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        with mock.patch.object(core, "find_soffice", return_value=str(fake)):
            with self.assertRaisesRegex(RuntimeError, "falha na conversão"):
                core.office_via_libreoffice(self.doc, self.d)

    def test_all_converters_fail_reports_both(self):
        with mock.patch.object(core, "IS_WINDOWS", False), \
                mock.patch.object(core, "office_via_libreoffice", side_effect=RuntimeError("sem soffice")):
            with self.assertRaisesRegex(RuntimeError, "LibreOffice: sem soffice"):
                core.office_to_pdf(self.doc, self.d)

    def test_windows_install_path_is_found(self):
        pf = self.d / "Programas"
        exe = pf / "LibreOffice" / "program" / "soffice.exe"
        exe.parent.mkdir(parents=True)
        exe.write_text("x")
        with mock.patch.object(core, "IS_WINDOWS", True), \
                mock.patch.dict(os.environ, {"ProgramFiles": str(pf), "ProgramFiles(x86)": ""}), \
                mock.patch("shutil.which", return_value=None):
            self.assertEqual(Path(core.find_soffice()), exe)

    def test_frozen_child_command(self):
        with mock.patch.object(sys, "frozen", True, create=True):
            cmd, cwd = core.child_command(["--_office-convert", "a", "b"])
        self.assertEqual(cmd[0], sys.executable)
        self.assertEqual(cmd[1:], ["--_office-convert", "a", "b"])
        self.assertIsNone(cwd)


class HistoryAndLogTests(unittest.TestCase):
    def test_history_and_logs_survive_unwritable_folder(self):
        blocker = Path(tempfile.mkdtemp()) / "arquivo"
        blocker.write_text("não é pasta")
        with mock.patch.object(core, "config_dir", return_value=blocker):
            self.assertIsNone(core.append_history([{"arquivo": "a", "status": "ok", "detalhe": "", "hora": "t"}]))
            core.log_error("algo")                          # não deve levantar exceção
            core.save_config({"x": 1})

    def test_log_error_writes_file(self):
        d = Path(tempfile.mkdtemp())
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(d)}):
            core.log_error("falha de teste")
            text = (d / "JRPrinter" / "erros.log").read_text(encoding="utf-8")
        self.assertIn("falha de teste", text)


class CliExtraTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        pdfgen.text_pdf(self.d / "a.pdf", "\n".join(f"L{i}" for i in range(130)))
        (self.d / "b.txt").write_text("olá\n" * 5)
        self.cfg = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.cfg), "APPDATA": str(self.cfg)})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_plan_prints_steps(self):
        rc, out, err = run_cli([str(self.d), "--plan", "--cover", "full", "--folder-divider", "--set-copies", "2"])
        self.assertEqual(rc, 0, err)
        self.assertIn("separador", out)
        self.assertIn("rosto", out)
        self.assertIn("arquivo", out)

    def test_stats_prints_totals(self):
        rc, out, err = run_cli([str(self.d), "--stats", "--por-folha", "4"])
        self.assertEqual(rc, 0, err)
        self.assertIn("marcados", out)
        self.assertIn("por tipo", out)

    def test_test_print_dry_run_one_page_each(self):
        rc, out, err = run_cli([str(self.d / "a.pdf"), "--test-print", "--dry-run", "-n", "4", "--cover", "full"])
        self.assertEqual(rc, 0, err)
        self.assertNotIn("rosto", out)                     # sem rosto na impressão de teste
        self.assertIn("-n 1", out)                         # 1 cópia
        self.assertIn("-P 1", out)                         # só a 1ª página

    def test_bad_values_exit_with_usage_error(self):
        rc, out, err = run_cli([str(self.d), "--set-copies", "0", "--dry-run"])
        self.assertEqual(rc, 2)
        self.assertIn("conjunto", err)

    def test_sort_and_reverse_apply(self):
        rc, out, err = run_cli([str(self.d), "--sort", "size", "--reverse", "--dry-run"])
        self.assertEqual(rc, 0, err)
        first = out.splitlines()[0]
        self.assertIn("a.pdf", first)                       # o PDF é o maior

    @POSIX_ONLY
    def test_warning_when_cups_missing(self):
        with mock.patch.dict(os.environ, {"PATH": str(self.d / "vazio")}):
            (self.d / "vazio").mkdir()
            rc, out, err = run_cli([str(self.d / "b.txt"), "-p", "HP"])
        self.assertIn("CUPS", err)

    def test_gui_missing_tkinter_is_reported(self):
        with mock.patch.dict(sys.modules, {"jrprinter.gui": None}):
            rc, out, err = run_cli([])
        self.assertEqual(rc, 2)
        self.assertIn("tkinter", err)

    def test_gui_flag_with_files_still_starts_gui(self):
        fake_gui = mock.Mock()
        fake_gui.run_gui = mock.Mock(return_value=0)
        with mock.patch.dict(sys.modules, {"jrprinter.gui": fake_gui}):
            rc, out, err = run_cli(["--gui", str(self.d / "b.txt")])
        self.assertEqual(rc, 0)
        fake_gui.run_gui.assert_called_once()


if __name__ == "__main__":
    unittest.main()
