"""Modo diagnóstico: testa cada peça do programa na máquina e gera um relatório de texto para colar em suporte."""
import datetime
import platform
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from . import __version__, core, pdfgen, preview
from .backends import WindowsBackend, get_backend

OK, WARN, FAIL, INFO, NA = "OK", "AVISO", "FALHA", "INFO", "N/A"
MARK = {OK: "[ OK ]", WARN: "[ !! ]", FAIL: "[FALHA]", INFO: "[info]", NA: "[ -- ]"}


@dataclass
class Result:
    status: str
    name: str
    detail: str = ""
    hint: str = ""


def _try(name: str, fn: Callable[[], Result]) -> Result:
    try:
        return fn()
    except Exception as e:  # um teste nunca derruba os outros
        return Result(FAIL, name, f"{type(e).__name__}: {e}")


def _registry_has(prog_id: str) -> bool:
    import winreg
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, prog_id))
        return True
    except OSError:
        return False


def _min_docx(path: Path):
    """.docx mínimo e válido, para testar a conversão de verdade."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Teste de diagnostico do PrintBatch</w:t></w:r></w:p></w:body></w:document>')


# ---------------------------------------------------------------- verificações
def check_system() -> List[Result]:
    frozen = getattr(sys, "frozen", False)
    out = [Result(INFO, "Programa", f"PrintBatch {__version__} ({'executável' if frozen else 'Python'})"),
           Result(INFO, "Sistema", f"{platform.system()} {platform.release()} ({platform.version()}) {platform.machine()}"),
           Result(INFO, "Python", f"{platform.python_version()} em {sys.executable}")]
    try:
        d = core.config_dir()
        t = d / ".teste"
        t.write_text("ok", encoding="utf-8")
        t.unlink()
        out.append(Result(OK, "Pasta de configuração", f"{d} (leitura e escrita OK)"))
    except OSError as e:
        out.append(Result(FAIL, "Pasta de configuração", str(e), "Verifique as permissões da pasta %APPDATA%."))
    return out


def check_tk() -> Result:
    try:
        import tkinter
        v = tkinter.TkVersion
        return Result(OK, "Interface gráfica (Tkinter)", f"Tk {v}")
    except Exception as e:
        return Result(FAIL, "Interface gráfica (Tkinter)", str(e), "Reinstale o Python marcando 'tcl/tk and IDLE' (Linux: python3-tk).")


def check_dnd() -> Result:
    try:
        import tkinterdnd2  # noqa: F401
        return Result(OK, "Arrastar e soltar (tkinterdnd2)", "disponível")
    except Exception:
        return Result(WARN, "Arrastar e soltar (tkinterdnd2)", "não instalado", "pip install tkinterdnd2 (opcional)")


def check_printers() -> Result:
    names, default = get_backend(False).list_printers()
    if not names:
        return Result(FAIL, "Impressoras", "nenhuma impressora encontrada", "Instale/ligue uma impressora; no Windows confira o serviço 'Spooler' e o PowerShell.")
    return Result(OK, "Impressoras", f"{len(names)} encontrada(s); padrão: {default or '(nenhuma)'} — " + "; ".join(names[:8]))


def check_print_engine() -> Result:
    if core.IS_WINDOWS:
        s = WindowsBackend().sumatra
        if s:
            return Result(OK, "Motor de impressão (SumatraPDF)", s)
        return Result(WARN, "Motor de impressão (SumatraPDF)", "não encontrado",
                      "Sem ele, cópias, frente e verso, papel e páginas NÃO são aplicados. winget install SumatraPDF.SumatraPDF")
    import shutil
    p = shutil.which("lp")
    return Result(OK if p else FAIL, "Motor de impressão (CUPS lp)", p or "não encontrado", "" if p else "Instale o CUPS.")


def check_office_presence() -> List[Result]:
    if not core.IS_WINDOWS:
        return [Result(NA, "Microsoft Office", "só no Windows")]
    out = []
    for prog, label in (("Word.Application", "Word"), ("Excel.Application", "Excel"), ("PowerPoint.Application", "PowerPoint"),
                        ("Outlook.Application", "Outlook (.msg)")):
        has = _registry_has(prog)
        out.append(Result(OK if has else INFO, label, "instalado" if has else "não encontrado"))
    try:
        import win32com.client  # noqa: F401
        out.append(Result(OK, "pywin32 (automação do Office)", "disponível"))
    except Exception:
        out.append(Result(WARN, "pywin32 (automação do Office)", "não instalado", "pip install pywin32 — sem ele só o LibreOffice converte documentos."))
    return out


def check_libreoffice() -> Result:
    p = core.find_soffice()
    if not p:
        return Result(INFO, "LibreOffice", "não encontrado", "Opcional: winget install TheDocumentFoundation.LibreOffice")
    try:
        r = subprocess.run([p, "--version"], capture_output=True, text=True, timeout=30, creationflags=core.NO_WINDOW)
        return Result(OK, "LibreOffice", f"{p} — {(r.stdout or '').strip()}")
    except Exception as e:
        return Result(WARN, "LibreOffice", f"{p} — não respondeu: {e}")


def check_conversion() -> Result:
    from .fileinfo import converter_available
    if not converter_available():
        return Result(FAIL, "Conversão de documentos", "nem Office/pywin32 nem LibreOffice disponíveis",
                      "Instale o Microsoft Office (com pywin32) ou o LibreOffice para imprimir .docx/.xlsx/.pptx.")
    tmp = Path(tempfile.mkdtemp(prefix="pb_diag_"))
    try:
        src = tmp / "teste.docx"
        _min_docx(src)
        t0 = time.time()
        out = core.office_to_pdf(src, tmp)
        return Result(OK, "Conversão de documentos (.docx → PDF)", f"{out.stat().st_size} bytes em {time.time() - t0:.1f} s")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def check_preview() -> Result:
    if not preview.renderer_available():
        return Result(WARN, "Pré-visualização (pypdfium2 + pillow)", "não instalados", "pip install pypdfium2 pillow")
    tmp = Path(tempfile.mkdtemp(prefix="pb_diag_"))
    try:
        pdf = pdfgen.centered_page_pdf(tmp / "t.pdf", ["Teste"])
        png, n = preview.Previewer().render_pdf(pdf)
        return Result(OK, "Pré-visualização (pypdfium2 + pillow)", f"miniatura de {len(png)} bytes")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def check_print_test(printer: str) -> Result:
    """Imprime UMA página de teste de verdade (gasta uma folha)."""
    tmp = Path(tempfile.mkdtemp(prefix="pb_diag_"))
    try:
        pdf = pdfgen.centered_page_pdf(tmp / "teste.pdf", ["TESTE DO PRINTBATCH", f"Impressora: {printer}",
                                                          datetime.datetime.now().strftime("%d/%m/%Y %H:%M")])
        backend = get_backend(False)
        cmd = " ".join(backend.command(pdf, core.Options(printer=printer)))
        out = backend.print_file(pdf, core.Options(printer=printer), "teste")
        return Result(OK, f"Página de teste em '{printer}'", f"enviada ({out or 'ok'}). Comando: {cmd}")
    finally:
        # o Windows pode manter o arquivo aberto por instantes
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def run(full: bool = True, printer: Optional[str] = None) -> List[Result]:
    results: List[Result] = []
    steps = (("Sistema", check_system), ("Interface gráfica (Tkinter)", check_tk), ("Arrastar e soltar", check_dnd),
             ("Impressoras", check_printers), ("Motor de impressão", check_print_engine),
             ("Microsoft Office", check_office_presence), ("LibreOffice", check_libreoffice),
             ("Pré-visualização (pypdfium2 + pillow)", check_preview))
    for label, fn in steps:
        r = _try(label, fn)
        results += r if isinstance(r, list) else [r]
    if full:
        results.append(_try("Conversão de documentos", check_conversion))
    if printer:
        results.append(_try("Página de teste", lambda: check_print_test(printer)))
    return results


def format_report(results: List[Result]) -> str:
    lines = [f"PrintBatch {__version__} — diagnóstico ({datetime.datetime.now():%d/%m/%Y %H:%M})", "=" * 64]
    for r in results:
        lines.append(f"{MARK[r.status]} {r.name}: {r.detail}".rstrip())
        if r.hint and r.status in (WARN, FAIL, INFO):
            lines.append(f"         → {r.hint}")
    fails = sum(r.status == FAIL for r in results)
    warns = sum(r.status == WARN for r in results)
    lines += ["=" * 64, f"Resumo: {fails} falha(s), {warns} aviso(s). "
              + ("Tudo certo para imprimir." if not fails else "Corrija as falhas acima antes de imprimir."),
              "Privacidade: este relatório não inclui nomes de arquivos nem o conteúdo de documentos."]
    return "\n".join(lines)
