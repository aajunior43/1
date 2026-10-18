"""Testes de ponta a ponta: o envio REAL à impressora (com lp/lpstat simulados que registram os argumentos),
conversão real com LibreOffice, o SumatraPDF simulado e o fluxo de impressão pela interface."""
import contextlib
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from _plataforma import POSIX_ONLY
from printbatch import cli, core, pdfgen
from printbatch.backends import CupsBackend, WindowsBackend

try:
    import pypdfium2 as pdfium
    HAS_PDFIUM = True
except ImportError:
    HAS_PDFIUM = False

HAS_SOFFICE = core.find_soffice() is not None

FAKE_LP = """#!__PY__
import json, os, shutil, sys, time
args = sys.argv[1:]
if os.environ.get("FAKE_LP_SLEEP"):
    time.sleep(float(os.environ["FAKE_LP_SLEEP"]))
title = args[args.index("-t") + 1] if "-t" in args else "?"
log = os.environ.get("FAKE_LP_LOG")
if log:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"args": args, "title": title}, ensure_ascii=False) + "\\n")
src = args[-1]
state = os.environ.get("FAKE_LP_STATE")
for item in filter(None, os.environ.get("FAKE_LP_FAIL", "").split(",")):
    key, times = item.rsplit(":", 1)
    if key and key in title:
        counter = os.path.join(state, "".join(c if c.isalnum() else "_" for c in key) + ".count")
        n = int(open(counter).read()) if os.path.exists(counter) else 0
        open(counter, "w").write(str(n + 1))
        if n < int(times):
            print("lp: erro simulado da impressora ao enviar " + title, file=sys.stderr)
            sys.exit(1)
keep = os.environ.get("FAKE_LP_KEEP")
if keep:
    os.makedirs(keep, exist_ok=True)
    shutil.copy(src, os.path.join(keep, "%03d-%s" % (len(os.listdir(keep)) + 1, title)))
print("request id is HP-1 (1 file(s))")
"""

FAKE_LPSTAT = """#!__PY__
import os, sys
if "-e" in sys.argv:
    print("\\n".join(p for p in os.environ.get("FAKE_PRINTERS", "").split(";") if p))
elif "-d" in sys.argv:
    print("system default destination: " + os.environ.get("FAKE_DEFAULT", "HP"))
"""

FAKE_SUMATRA = """#!/bin/sh
for a in "$@"; do printf '%s\\n' "$a" >> "$FAKE_SUMATRA_LOG"; done
printf '%s\\n' '--' >> "$FAKE_SUMATRA_LOG"
if [ -n "$FAKE_SUMATRA_FAIL" ]; then echo "SumatraPDF: falha simulada" >&2; exit 1; fi
exit 0
"""


def write_exec(path, text):
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def make_docx(path, text="Documento de teste"):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>')


def first_call(log):
    """Argumentos da 1ª chamada registrada pelo SumatraPDF simulado (separadas por uma linha '--')."""
    lines = log.read_text(encoding="utf-8").splitlines()
    return lines[:lines.index("--")] if "--" in lines else lines


class FakePrinterMixin:
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        write_exec(self.bin / "lp", FAKE_LP.replace("__PY__", sys.executable))
        write_exec(self.bin / "lpstat", FAKE_LPSTAT.replace("__PY__", sys.executable))
        self.log = self.tmp / "lp.log"
        self.keep = self.tmp / "enviados"
        self.state = self.tmp / "estado"
        self.state.mkdir()
        self.cfg = self.tmp / "cfg"
        self.env = mock.patch.dict(os.environ, {
            "PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "FAKE_LP_LOG": str(self.log), "FAKE_LP_KEEP": str(self.keep), "FAKE_LP_STATE": str(self.state),
            "FAKE_LP_FAIL": "", "FAKE_LP_SLEEP": "", "FAKE_PRINTERS": "HP;Brother", "FAKE_DEFAULT": "HP",
            "XDG_CONFIG_HOME": str(self.cfg), "APPDATA": str(self.cfg)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines() if line.strip()]

    def sent(self):
        """Arquivos efetivamente recebidos pelo 'lp', na ordem (cópias feitas pelo lp simulado)."""
        if not self.keep.exists():
            return []
        return sorted(self.keep.iterdir())

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = cli.main(argv)
        return rc, out.getvalue(), err.getvalue()


@POSIX_ONLY
class CupsCliTests(FakePrinterMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.docs = self.tmp / "docs"
        self.docs.mkdir()
        pdfgen.text_pdf(self.docs / "relatorio.pdf", "\n".join(f"Linha {i}" for i in range(150)))   # 3 páginas
        (self.docs / "notas.txt").write_text("primeira linha\nsegunda linha\n", encoding="utf-8")

    def test_list_printers_uses_lpstat(self):
        rc, out, _ = self.run_cli(["--list-printers"])
        self.assertEqual(rc, 0)
        self.assertIn("* HP", out)
        self.assertIn("  Brother", out)

    def test_real_send_passes_every_option_to_lp(self):
        rep = self.tmp / "fila.csv"
        rc, out, _ = self.run_cli([str(self.docs / "relatorio.pdf"), str(self.docs / "notas.txt"),
                                   "-p", "HP", "-n", "2", "--duplex", "long", "--pages", "1-2", "--paper", "A4",
                                   "--landscape", "--fit", "--mono", "--report", str(rep)])
        self.assertEqual(rc, 0, out)
        calls = self.calls()
        self.assertEqual(len(calls), 2)
        by_title = {c["title"]: c for c in calls}
        self.assertEqual(sorted(by_title), ["notas.pdf", "relatorio.pdf"])   # o .txt sai convertido em PDF
        args = by_title["relatorio.pdf"]["args"]
        for needle in (["-n", "2"], ["-d", "HP"], ["-o", "sides=two-sided-long-edge"], ["-P", "1-2"],
                       ["-o", "media=A4"], ["-o", "landscape"], ["-o", "fit-to-page"],
                       ["-o", "print-color-mode=monochrome"]):
            self.assertTrue(any(args[i:i + len(needle)] == needle for i in range(len(args))), (needle, args))
        sent = self.sent()
        self.assertEqual(len(sent), 2)
        self.assertTrue(sent[0].read_bytes().startswith(b"%PDF"))
        self.assertTrue(sent[1].read_bytes().startswith(b"%PDF"))        # o .txt foi convertido antes de enviar
        rows = list(__import__("csv").DictReader(rep.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
        self.assertEqual([r["status"] for r in rows], ["ok", "ok"])
        hist = (Path(self.cfg) / "PrintBatch" / "historico.csv").read_text(encoding="utf-8-sig")
        self.assertIn("HP", hist)
        self.assertEqual(hist.count("\n"), 3)                             # cabeçalho + 2 linhas

    def test_printer_error_retry_and_failure_page(self):
        pdf = self.docs / "relatorio.pdf"
        os.environ["FAKE_LP_FAIL"] = "relatorio:1"                       # falha só na 1ª tentativa
        rc, out, err = self.run_cli([str(pdf), "-p", "HP", "--failed-page"])
        self.assertEqual(rc, 1)
        self.assertIn("erro simulado", err + out)
        titles = [c["title"] for c in self.calls()]
        self.assertTrue(any("_falha" in t for t in titles), titles)     # página de aviso foi enviada

        self.log.unlink(missing_ok=True)
        shutil.rmtree(self.keep, ignore_errors=True)
        for f in self.state.iterdir():
            f.unlink()
        rc, out, err = self.run_cli([str(pdf), "-p", "HP", "--retries", "1"])
        self.assertEqual(rc, 0, err)
        self.assertIn("tentando de novo", err)
        calls = self.calls()
        self.assertEqual(len(calls), 2)                                 # 1 tentativa que falhou + 1 que deu certo
        self.assertEqual({c["title"] for c in calls}, {"relatorio.pdf"})  # só o arquivo com erro foi repetido
        self.assertEqual(len(self.sent()), 1)                           # e só uma cópia chegou à impressora

    def test_sheets_are_sent_as_pages_per_sheet(self):
        if not HAS_PDFIUM:
            self.skipTest("pypdfium2 ausente")
        rc, out, err = self.run_cli([str(self.docs / "relatorio.pdf"), "-p", "HP", "--por-folha", "2"])
        self.assertEqual(rc, 0, err)
        sent = self.sent()
        self.assertEqual(len(sent), 1)
        doc = pdfium.PdfDocument(str(sent[0]))
        try:
            self.assertEqual(len(doc), 2)                               # 3 páginas em folhas de 2
        finally:
            doc.close()
        self.assertIn("folhas", self.calls()[0]["title"])

    @unittest.skipUnless(HAS_SOFFICE, "LibreOffice ausente")
    def test_word_document_is_converted_by_libreoffice_and_sent(self):
        docx = self.docs / "carta.docx"
        make_docx(docx, "Carta de teste da impressão em lote")
        rc, out, err = self.run_cli([str(docx), "-p", "HP"])
        self.assertEqual(rc, 0, err + out)
        sent = self.sent()
        self.assertEqual(len(sent), 1)
        self.assertTrue(sent[0].read_bytes().startswith(b"%PDF"))
        if HAS_PDFIUM:
            doc = pdfium.PdfDocument(str(sent[0]))
            try:
                self.assertGreaterEqual(len(doc), 1)
            finally:
                doc.close()

    def test_project_saved_options_are_used_later(self):
        proj = self.tmp / "lote.pbq"
        rc, out, err = self.run_cli([str(self.docs / "notas.txt"), "-p", "HP", "-n", "3", "--cover", "filename",
                                     "--save-project", str(proj), "--dry-run"])
        self.assertEqual(rc, 0, err)
        self.assertTrue(proj.exists())
        rc, out, err = self.run_cli(["--project", str(proj), "--dry-run"])
        self.assertEqual(rc, 0, err)
        self.assertIn("-n 3", out)                                      # cópias salvas no projeto
        self.assertIn("rosto", out + err)
        self.assertEqual(self.calls(), [])                              # simulação: nada foi enviado

    def test_check_exit_codes(self):
        bad = self.tmp / "verificar"
        bad.mkdir()
        (bad / "vazio.txt").write_text("")
        rc, out, err = self.run_cli([str(bad), "--check"])
        self.assertEqual(rc, 1)                                         # arquivo vazio é erro
        self.assertIn("vazio", out)
        ok = self.tmp / "so-aviso"
        ok.mkdir()
        (ok / "a.txt").write_text("x")
        (ok / "b.txt").write_text("x")                                  # idêntico -> só aviso de duplicado
        rc, out, err = self.run_cli([str(ok), "--check"])
        self.assertEqual(rc, 0)
        self.assertIn("duplicado", out)

    def test_no_files_exit_code(self):
        rc, out, err = self.run_cli([str(self.tmp / "nada-aqui"), "-p", "HP"])
        self.assertEqual(rc, 2)
        self.assertEqual(self.calls(), [])

    def test_cups_without_lp_reports_problem(self):
        with mock.patch.dict(os.environ, {"PATH": str(self.tmp / "vazio")}):
            (self.tmp / "vazio").mkdir()
            self.assertEqual(CupsBackend().problems(), ["CUPS ('lp') não encontrado."])


@POSIX_ONLY
class WindowsBackendTests(unittest.TestCase):
    """SumatraPDF simulado: confere os argumentos reais que seriam passados e o tratamento de erro."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sumatra = self.tmp / "SumatraPDF"
        write_exec(self.sumatra, FAKE_SUMATRA)
        self.log = self.tmp / "sumatra.log"
        self.env = mock.patch.dict(os.environ, {"FAKE_SUMATRA_LOG": str(self.log), "FAKE_SUMATRA_FAIL": ""})
        self.env.start()
        self.pdf = self.tmp / "f.pdf"
        pdfgen.text_pdf(self.pdf, "x")

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_arguments_sent_to_sumatra(self):
        be = WindowsBackend(sumatra=str(self.sumatra))
        out = be.print_file(self.pdf, core.Options(printer="HP LaserJet", copies=2, duplex="long", pages="1-3, 5",
                                                   paper="A4", landscape=True, color=False), "teste")
        self.assertEqual(out, "enviado")
        argv = first_call(self.log)
        self.assertEqual(argv[:3], ["-print-to", "HP LaserJet", "-print-settings"])
        self.assertEqual(argv[3], "2x,duplex,1-3,5,paper=A4,landscape,noscale,monochrome")
        self.assertIn("-silent", argv)
        self.assertIn("-exit-when-done", argv)
        self.assertEqual(argv[-1], str(self.pdf))                      # caminho com espaços vai como um argumento só

    def test_default_printer_and_simplex(self):
        WindowsBackend(sumatra=str(self.sumatra)).print_file(self.pdf, core.Options(), "x")
        argv = first_call(self.log)
        self.assertEqual(argv[0], "-print-to-default")
        self.assertEqual(argv[2], "simplex,noscale")

    def test_sumatra_failure_is_reported(self):
        os.environ["FAKE_SUMATRA_FAIL"] = "1"
        with self.assertRaises(RuntimeError) as cm:
            WindowsBackend(sumatra=str(self.sumatra)).print_file(self.pdf, core.Options(), "x")
        self.assertIn("falha simulada", str(cm.exception))

    def test_find_sumatra_on_path(self):
        d = self.tmp / "programas"
        d.mkdir()
        write_exec(d / "SumatraPDF", "#!/bin/sh\nexit 0\n")
        with mock.patch.dict(os.environ, {"PATH": f"{d}{os.pathsep}{os.environ.get('PATH', '')}"}):
            self.assertEqual(Path(WindowsBackend.find_sumatra()).name, "SumatraPDF")
        WindowsBackend(sumatra=None)                                   # não deve falhar mesmo sem SumatraPDF


if __name__ == "__main__":
    unittest.main()
