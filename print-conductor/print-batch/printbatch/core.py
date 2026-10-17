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
import time
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
    retries: int = 0                  # tentativas extras se o envio à impressora falhar
    retry_wait: float = 2.0           # segundos entre tentativas

    def validate(self):
        if self.copies < 1:
            raise ValueError("cópias deve ser >= 1")
        if self.cover and self.cover not in COVERS:
            raise ValueError("modelo de rosto desconhecido: " + self.cover)
        if self.duplex not in (None, "long", "short"):
            raise ValueError("duplex inválido")
        if self.set_copies < 1:
            raise ValueError("cópias do conjunto deve ser >= 1")
        if not 0 <= self.retries <= 10:
            raise ValueError("tentativas extras deve estar entre 0 e 10")


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


def norm_key(path):
    """Chave para comparar caminhos (no Windows maiúsculas/minúsculas e / \\ são equivalentes)."""
    return os.path.normcase(str(Path(path).resolve()))


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
        k = norm_key(f)
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


def office_via_com_inprocess(src, outdir):
    """Word/Excel/PowerPoint instalados (Windows + pywin32). Roda dentro do processo filho."""
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
            app.DisplayAlerts = 0          # sem caixas de diálogo
            app.AutomationSecurity = 3     # macros desativadas
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
            app.AutomationSecurity = 3
            try:
                wb = app.Workbooks.Open(str(src), ReadOnly=True)
                wb.ExportAsFixedFormat(0, str(out))
                wb.Close(False)
            finally:
                app.Quit()
        elif ext in {".ppt", ".pptx", ".odp"}:
            app = wc.DispatchEx("PowerPoint.Application")
            try:
                app.DisplayAlerts = 1      # sem caixas de diálogo
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


OFFICE_TIMEOUT = 240


def child_command(args):
    """Comando para chamar este mesmo programa em outro processo (funciona no .exe e no Python)."""
    if getattr(sys, "frozen", False):
        return [sys.executable] + list(args), None
    return [sys.executable, "-m", "printbatch"] + list(args), str(Path(__file__).resolve().parent.parent)


def run_with_timeout(cmd, timeout, cwd=None):
    """Roda `cmd`; se passar do tempo, mata o processo (e a árvore, no Windows). Devolve (rc, saída, erro)."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd,
                            creationflags=NO_WINDOW)
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err
    except subprocess.TimeoutExpired:
        if IS_WINDOWS:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, creationflags=NO_WINDOW)
        else:
            proc.kill()
        proc.communicate()
        raise TimeoutError(f"sem resposta em {timeout} s")


def office_via_com(src, outdir, timeout=None):
    """Converte com o Office num processo separado, com limite de tempo (evita travar se o Office abrir um diálogo)."""
    cmd, cwd = child_command(["--_office-convert", str(src), str(outdir)])
    try:
        rc, out, err = run_with_timeout(cmd, timeout or OFFICE_TIMEOUT, cwd)
    except TimeoutError:
        raise RuntimeError(f"o Office não respondeu em {timeout or OFFICE_TIMEOUT} s (documento protegido ou com diálogo aberto?)")
    out_pdf = Path(outdir) / (Path(src).stem + ".pdf")
    if rc != 0 or not out_pdf.exists():
        raise RuntimeError((err or out or "falha na conversão pelo Office").strip().splitlines()[-1][:300])
    return out_pdf


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


def as_test_job(files, opts: Options):
    """Impressão de teste: só a 1ª página de cada arquivo marcado, 1 cópia, sem rosto/separadores."""
    from dataclasses import replace
    items = [x if isinstance(x, Item) else Item(x) for x in files]
    test_items = [Item(i.path, i.enabled, 1, "1", i.duplex, i.color, i.note) for i in items]
    return test_items, replace(opts, copies=1, pages=None, cover=None, cover_text=None,
                               folder_divider=False, set_copies=1, attachments=False)


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
    def send(path, o, title, name, n, total):
        """Envia à impressora repetindo só este envio se falhar (assim nada é impresso em duplicidade)."""
        for attempt in range(opts.retries + 1):
            try:
                return backend.print_file(path, o, title) or ""
            except Exception as e:
                if attempt >= opts.retries or (cancel is not None and cancel.is_set()):
                    raise
                emit("retry", index=n, total=total, file=name, attempt=attempt + 1, error=str(e))
                if cancel is not None:
                    cancel.wait(opts.retry_wait)
                else:
                    time.sleep(opts.retry_wait)

    tmp = tempfile.mkdtemp(prefix="printbatch_")
    try:
        for rep in range(opts.set_copies):
            last_folder = None
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
                        send(div, plain, "separador de pasta", f, n, total)
                    last_folder = f.parent
                    parts = [f] if opts.dry_run and f.suffix.lower() in OFFICE else prepare(f, work, eff)
                    if opts.cover or opts.cover_text:
                        cov = pdfgen.centered_page_pdf(work / "_rosto.pdf", cover_lines(opts, f, n, total))
                        send(cov, plain, f"rosto {f.name}", f, n, total)
                    detail = [send(p, eff, f.name, f, n, total) for p in parts]
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
                            send(pg, plain, "aviso de falha", f, n, total)
                        except Exception as e2:
                            emit("error", index=n, total=total, file=f, error="aviso de falha também falhou: " + str(e2))
            if stop:
                break
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
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


HISTORY_FIELDS = ["arquivo", "status", "detalhe", "hora"]


def append_history(rows, printer=None):
    """Acrescenta o resultado de um lote ao histórico (historico.csv na pasta de configuração)."""
    if not rows:
        return None
    path = config_dir() / "historico.csv"
    new = not path.exists()
    try:
        with open(path, "a", newline="", encoding="utf-8-sig" if new else "utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=HISTORY_FIELDS + ["impressora"], delimiter=";")
            if new:
                w.writeheader()
            for r in rows:
                w.writerow({**r, "impressora": printer or ""})
        return path
    except OSError:
        return None


# ---------- Configuração e registro de erros ----------
def log_error(text):
    """Acrescenta uma mensagem ao arquivo de erros (útil no .exe, que não tem console)."""
    try:
        with open(config_dir() / "erros.log", "a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {text}\n")
    except OSError:
        pass



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
