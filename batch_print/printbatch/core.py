"""Núcleo: modelo de opções, fila, conversões, páginas de rosto e execução do lote."""
import csv
import datetime
import email
import email.policy
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Callable, List, Optional

from . import pdfgen

IS_WINDOWS = sys.platform.startswith("win")
PRINTABLE = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
TEXT = {".txt", ".log", ".csv"}
OFFICE = {".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ods", ".ppt", ".pptx", ".odp", ".html", ".htm"}
MAIL = {".eml", ".msg"}
SUPPORTED = PRINTABLE | TEXT | OFFICE | MAIL

COVERS = {
    "filename": ["{name}"],
    "filename-folder": ["{name}", "Pasta: {folder}"],
    "full": ["{name}", "Pasta: {folder}", "Caminho: {folder_path}", "Tipo: {ext}", "Arquivo {index} de {total}"],
    "number": ["Arquivo {index} de {total}", "{name}"],
}
SORTS = ("natural", "name", "date", "size", "type", "folder")
NO_WINDOW = 0x08000000 if IS_WINDOWS else 0


@dataclass
class Options:
    printer: Optional[str] = None
    copies: int = 1
    duplex: Optional[str] = None      # None | "long" | "short"
    pages: Optional[str] = None       # ex.: "1-3,5"
    paper: Optional[str] = None       # ex.: "A4"
    landscape: bool = False
    fit: bool = False
    color: Optional[bool] = None      # None=padrão, True=cor, False=P&B
    cover: Optional[str] = None       # nome em COVERS
    cover_text: Optional[str] = None  # modelo próprio (usa os mesmos campos)
    failed_page: bool = False
    attachments: bool = False         # imprime anexos de e-mail
    dry_run: bool = False
    folder_divider: bool = False      # página separadora quando muda a pasta
    set_copies: int = 1               # quantas vezes imprimir a fila inteira

    def validate(self):
        if self.copies < 1:
            raise ValueError("cópias deve ser >= 1")
        if self.cover and self.cover not in COVERS:
            raise ValueError("modelo de rosto desconhecido: " + self.cover)
        if self.duplex not in (None, "long", "short"):
            raise ValueError("duplex inválido")
        if self.set_copies < 1:
            raise ValueError("cópias do conjunto deve ser >= 1")


# ---------- Fila ----------
@dataclass
class Item:
    """Um arquivo da fila, com ajustes opcionais que valem só para ele."""
    path: Path
    enabled: bool = True
    copies: Optional[int] = None      # None = usa o padrão
    pages: Optional[str] = None
    duplex: Optional[str] = None      # None = padrão; "off" | "long" | "short"
    color: Optional[str] = None       # None = padrão; "color" | "mono"
    note: str = ""

    def __post_init__(self):
        self.path = Path(self.path)

    def effective(self, base: "Options") -> "Options":
        d = asdict(base)
        if self.copies:
            d["copies"] = self.copies
        if self.pages:
            d["pages"] = self.pages
        if self.duplex:
            d["duplex"] = None if self.duplex == "off" else self.duplex
        if self.color:
            d["color"] = self.color == "color"
        return Options(**d)

    def overrides(self):
        return {k: v for k, v in (("copies", self.copies), ("pages", self.pages),
                                  ("duplex", self.duplex), ("color", self.color)) if v}


def natural_key(text):
    import re
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(text))]


def collect(paths, recursive=False, patterns=None, sort="natural", reverse=False, warn=None):
    files = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            files += [f for f in it if f.is_file() and f.suffix.lower() in SUPPORTED]
        elif p.is_file():
            files.append(p)
        elif warn:
            warn(f"não encontrado: {raw}")
    seen, uniq = set(), []
    for f in files:
        k = str(f.resolve())
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return sort_files(filter_files(uniq, patterns), sort, reverse)


def filter_files(files, patterns):
    if not patterns:
        return list(files)
    return [f for f in files if any(fnmatch.fnmatch(f.name.lower(), p.lower()) for p in patterns)]


def sort_files(files, sort="natural", reverse=False):
    keys = {"natural": lambda f: natural_key(f),
            "name": lambda f: str(f).lower(), "date": lambda f: f.stat().st_mtime,
            "size": lambda f: f.stat().st_size,
            "type": lambda f: (f.suffix.lower(), natural_key(f)),
            "folder": lambda f: (natural_key(f.parent), natural_key(f.name))}
    return sorted(files, key=keys[sort], reverse=reverse)


# ---------- Páginas de rosto / aviso ----------
def cover_lines(opts, f, index, total):
    ctx = dict(name=f.name, folder=f.parent.resolve().name or "/", folder_path=str(f.parent.resolve()),
               ext=f.suffix.lstrip(".").upper(), index=index, total=total,
               date=datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
    tpl = opts.cover_text.splitlines() if opts.cover_text else COVERS[opts.cover]
    out = []
    for t in tpl:
        try:
            out.append(t.format(**ctx))
        except (KeyError, IndexError, ValueError):
            out.append(t)
    return out


# ---------- Conversões ----------
def read_text(path):
    data = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def find_soffice():
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    if IS_WINDOWS:
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if base:
                p = Path(base) / "LibreOffice" / "program" / "soffice.exe"
                if p.exists():
                    return str(p)
    return None


def office_via_libreoffice(src, outdir):
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError("LibreOffice não encontrado")
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(src)],
                   check=True, capture_output=True, timeout=300, creationflags=NO_WINDOW)
    out = Path(outdir) / (Path(src).stem + ".pdf")
    if not out.exists():
        raise RuntimeError("falha na conversão com LibreOffice")
    return out


def office_via_com(src, outdir):
    """Word/Excel/PowerPoint instalados (Windows + pywin32)."""
    import pythoncom  # noqa
    import win32com.client as wc
    src = Path(src).resolve()
    out = (Path(outdir) / (src.stem + ".pdf")).resolve()
    ext = src.suffix.lower()
    pythoncom.CoInitialize()
    try:
        if ext in {".doc", ".docx", ".odt", ".rtf", ".html", ".htm"}:
            app = wc.DispatchEx("Word.Application")
            app.Visible = False
            try:
                doc = app.Documents.Open(str(src), ReadOnly=True, AddToRecentFiles=False)
                doc.ExportAsFixedFormat(str(out), 17)
                doc.Close(False)
            finally:
                app.Quit()
        elif ext in {".xls", ".xlsx", ".ods"}:
            app = wc.DispatchEx("Excel.Application")
            app.Visible = False
            app.DisplayAlerts = False
            try:
                wb = app.Workbooks.Open(str(src), ReadOnly=True)
                wb.ExportAsFixedFormat(0, str(out))
                wb.Close(False)
            finally:
                app.Quit()
        elif ext in {".ppt", ".pptx", ".odp"}:
            app = wc.DispatchEx("PowerPoint.Application")
            try:
                pres = app.Presentations.Open(str(src), ReadOnly=True, WithWindow=False)
                pres.SaveAs(str(out), 32)
                pres.Close()
            finally:
                app.Quit()
        else:
            raise RuntimeError("tipo não suportado via COM")
    finally:
        pythoncom.CoUninitialize()
    if not out.exists():
        raise RuntimeError("o Office não gerou o PDF")
    return out


def office_to_pdf(src, outdir):
    errors = []
    if IS_WINDOWS:
        try:
            return office_via_com(src, outdir)
        except Exception as e:  # Office ausente, pywin32 ausente etc.
            errors.append(f"Office/COM: {e}")
    try:
        return office_via_libreoffice(src, outdir)
    except Exception as e:
        errors.append(f"LibreOffice: {e}")
    raise RuntimeError("não foi possível converter " + Path(src).name + " (" + "; ".join(errors) + ")")


def msg_to_text(src):
    """.msg do Outlook (requer Outlook + pywin32 no Windows)."""
    import pythoncom  # noqa
    import win32com.client as wc
    pythoncom.CoInitialize()
    try:
        item = wc.Dispatch("Outlook.Application").Session.OpenSharedItem(str(Path(src).resolve()))
        txt = "\n".join([f"De: {item.SenderName}", f"Para: {item.To}", f"Assunto: {item.Subject}",
                         f"Data: {item.SentOn}", "-" * 60, item.Body or ""])
        atts = [item.Attachments.Item(i + 1).FileName for i in range(item.Attachments.Count)]
        if atts:
            txt += "\n" + "-" * 60 + "\nAnexos: " + ", ".join(atts)
        return txt, []
    finally:
        pythoncom.CoUninitialize()


def eml_parts(src, outdir, want_attachments):
    msg = email.message_from_bytes(Path(src).read_bytes(), policy=email.policy.default)
    body = msg.get_body(preferencelist=("plain", "html"))
    text = body.get_content() if body else ""
    if body is not None and body.get_content_type() == "text/html":
        import re
        text = re.sub(r"<[^>]+>", "", re.sub(r"(?is)<(script|style).*?</\1>", "", text))
    atts = [p for p in msg.iter_attachments() if p.get_filename()]
    head = [f"De: {msg['from']}", f"Para: {msg['to']}", f"Data: {msg['date']}",
            f"Assunto: {msg['subject']}", "-" * 60, text]
    if atts:
        head += ["-" * 60, "Anexos: " + ", ".join(p.get_filename() for p in atts)]
    saved = []
    if want_attachments:
        for n, p in enumerate(atts):
            name = Path(p.get_filename()).name
            dst = Path(outdir) / f"{Path(src).stem}_anexo{n}_{name}"
            payload = p.get_payload(decode=True)
            if payload is not None and dst.suffix.lower() in SUPPORTED - MAIL:
                dst.write_bytes(payload)
                saved.append(dst)
    return "\n".join(head), saved


def prepare(f, tmp, opts, depth=0):
    """Converte `f` em uma lista de arquivos imprimíveis (PDF/imagem) na ordem de impressão."""
    f = Path(f)
    ext = f.suffix.lower()
    if ext in PRINTABLE:
        return [f]
    if ext in TEXT:
        return [pdfgen.text_pdf(Path(tmp) / (f.stem + ".pdf"), read_text(f))]
    if ext == ".eml":
        text, atts = eml_parts(f, tmp, opts.attachments and depth == 0)
        out = [pdfgen.text_pdf(Path(tmp) / (f.stem + ".pdf"), text)]
        for a in atts:
            out += prepare(a, tmp, opts, depth + 1)
        return out
    if ext == ".msg":
        if not IS_WINDOWS:
            raise RuntimeError(".msg só é suportado no Windows com Outlook")
        text, _ = msg_to_text(f)
        return [pdfgen.text_pdf(Path(tmp) / (f.stem + ".pdf"), text)]
    if ext in OFFICE:
        return [office_to_pdf(f, tmp)]
    raise RuntimeError("formato não suportado: " + ext)


# ---------- Execução ----------
Event = Callable[..., None]


def run_job(files, opts: Options, backend, on_event: Optional[Event] = None,
            cancel: Optional[threading.Event] = None):
    """Imprime a fila (Paths ou Items). Itens desmarcados são ignorados.
    Retorna lista de dicts de relatório. Eventos: start, ok, error, skipped, cancelled, done."""
    opts.validate()
    emit = on_event or (lambda *a, **k: None)
    items = [x if isinstance(x, Item) else Item(x) for x in files]
    rows, ok, fail = [], 0, 0
    now = lambda: datetime.datetime.now().isoformat(timespec="seconds")
    plain = Options(**{**asdict(opts), "copies": 1, "pages": None, "duplex": None})  # rosto/aviso: simples
    active = [it for it in items if it.enabled]
    total = len(active) * opts.set_copies
    for it in items:
        if not it.enabled:
            rows.append({"arquivo": str(it.path), "status": "ignorado", "detalhe": "desmarcado", "hora": now()})
            emit("skipped", file=it.path)
    n = 0
    stop = False
    last_folder = None
    with tempfile.TemporaryDirectory(prefix="printbatch_") as tmp:
        for rep in range(opts.set_copies):
            for it in active:
                if cancel is not None and cancel.is_set():
                    emit("cancelled", index=n + 1, total=total)
                    stop = True
                    break
                n += 1
                f = it.path
                emit("start", index=n, total=total, file=f)
                try:
                    if not f.exists():
                        raise RuntimeError("arquivo não encontrado")
                    eff = it.effective(opts)
                    eff.validate()
                    work = Path(tmp) / f"f{n}"
                    work.mkdir()
                    if opts.folder_divider and f.parent != last_folder:
                        div = pdfgen.centered_page_pdf(
                            work / "_pasta.pdf", ["PASTA", f.parent.resolve().name or "/", str(f.parent.resolve())])
                        backend.print_file(div, plain, "separador de pasta")
                    last_folder = f.parent
                    parts = [f] if opts.dry_run and f.suffix.lower() in OFFICE else prepare(f, work, eff)
                    if opts.cover or opts.cover_text:
                        cov = pdfgen.centered_page_pdf(work / "_rosto.pdf", cover_lines(opts, f, n, total))
                        backend.print_file(cov, plain, f"rosto {f.name}")
                    detail = [backend.print_file(p, eff, f.name) or "" for p in parts]
                    ok += 1
                    rows.append({"arquivo": str(f), "status": "ok", "detalhe": "; ".join(d for d in detail if d), "hora": now()})
                    emit("ok", index=n, total=total, file=f)
                except Exception as e:
                    fail += 1
                    rows.append({"arquivo": str(f), "status": "falhou", "detalhe": str(e), "hora": now()})
                    emit("error", index=n, total=total, file=f, error=str(e))
                    if opts.failed_page:
                        try:
                            pg = pdfgen.centered_page_pdf(Path(tmp) / f"_falha_{n}.pdf",
                                                          ["ARQUIVO NÃO IMPRESSO", f.name, "Motivo: " + str(e)[:160]])
                            backend.print_file(pg, plain, "aviso de falha")
                        except Exception as e2:
                            emit("error", index=n, total=total, file=f, error="aviso de falha também falhou: " + str(e2))
            if stop:
                break
    emit("done", ok=ok, fail=fail, total=total)
    return rows


def write_report(path, rows):
    path = Path(path)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=["arquivo", "status", "detalhe", "hora"], delimiter=";")
            w.writeheader()
            w.writerows(rows)


# ---------- Configuração ----------
def config_dir():
    base = os.environ.get("APPDATA") if IS_WINDOWS else os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    d = Path(base or Path.home()) / "PrintBatch"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_config():
    try:
        return json.loads((config_dir() / "config.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(data):
    try:
        (config_dir() / "config.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
