#!/usr/bin/env python3
"""Impressão em lote: imprime vários documentos (PDF, Office, imagens, texto, e-mail) de uma vez.

Usa CUPS (`lp`) em Linux/macOS. Documentos Office são convertidos para PDF com LibreOffice.

Exemplos:
  python3 batch_print.py --list-printers
  python3 batch_print.py pasta/ -r -p MinhaImpressora -n 2 --duplex --cover filename-folder
  python3 batch_print.py *.docx --sort date --filter '*relatorio*' --failed-page --report fila.csv --dry-run
"""
import argparse
import csv
import datetime
import email
import email.policy
import fnmatch
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DIRECT = {".pdf", ".txt", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
OFFICE = {".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ods", ".ppt", ".pptx", ".odp", ".html", ".htm"}
MAIL = {".eml"}
SUPPORTED = DIRECT | OFFICE | MAIL

# Modelos de página de rosto: cada um é uma lista de campos exibidos.
COVERS = {
    "filename": ["{name}"],
    "filename-folder": ["{name}", "Pasta: {folder}"],
    "full": ["{name}", "Pasta: {folder}", "Caminho: {folder_path}", "Tipo: {ext}", "{index}/{total}"],
    "number": ["Arquivo {index} de {total}", "{name}"],
}


# ---------- PDF mínimo (sem dependências) ----------
def _esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_text_pdf(path, lines, big_first=True, title=None):
    """Gera um PDF A4 de uma página com linhas centralizadas (cover/placeholder)."""
    content = []
    y = 520
    for i, line in enumerate(lines):
        size = 28 if (i == 0 and big_first) else 14
        text = line.encode("cp1252", "replace").decode("cp1252")
        while len(text) > (45 if size > 20 else 85):  # quebra simples de linhas longas
            cut = (45 if size > 20 else 85)
            content.append((size, y, text[:cut]))
            text, y = text[cut:], y - size - 6
        content.append((size, y, text))
        y -= size + 14
    stream = "\n".join(
        f"BT /F1 {s} Tf {max(30, 297 - len(t) * s * 0.25):.1f} {yy} Td ({_esc(t)}) Tj ET" for s, yy, t in content
    ).encode("cp1252", "replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for n, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % n + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offs:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    Path(path).write_bytes(bytes(out))
    return path


def cover_lines(template, f, index, total):
    ctx = dict(name=f.name, folder=f.parent.name or "/", folder_path=str(f.parent.resolve()),
               ext=f.suffix.lstrip(".").upper(), index=index, total=total)
    return [t.format(**ctx) for t in COVERS[template]]


# ---------- Conversões ----------
def to_pdf(src, outdir):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError("LibreOffice não encontrado para converter " + src.name)
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(src)],
                   check=True, capture_output=True, timeout=180)
    out = Path(outdir) / (src.stem + ".pdf")
    if not out.exists():
        raise RuntimeError("falha na conversão de " + src.name)
    return out


def eml_to_txt(src, outdir):
    """Converte e-mail (.eml) em texto: cabeçalhos, corpo e lista de anexos."""
    msg = email.message_from_bytes(src.read_bytes(), policy=email.policy.default)
    body = msg.get_body(preferencelist=("plain", "html"))
    text = body.get_content() if body else ""
    atts = [p.get_filename() for p in msg.iter_attachments() if p.get_filename()]
    parts = [f"De: {msg['from']}", f"Para: {msg['to']}", f"Data: {msg['date']}",
             f"Assunto: {msg['subject']}", "-" * 60, text]
    if atts:
        parts += ["-" * 60, "Anexos: " + ", ".join(atts)]
    out = Path(outdir) / (src.stem + ".txt")
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


# ---------- Fila ----------
def collect(paths, recursive, patterns, sort, reverse):
    files = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            files += [f for f in it if f.is_file() and f.suffix.lower() in SUPPORTED]
        elif p.is_file():
            files.append(p)
        else:
            print(f"aviso: não encontrado: {raw}", file=sys.stderr)
    if patterns:
        files = [f for f in files if any(fnmatch.fnmatch(f.name.lower(), pt.lower()) for pt in patterns)]
    keys = {"name": lambda f: str(f).lower(), "date": lambda f: f.stat().st_mtime,
            "size": lambda f: f.stat().st_size, "type": lambda f: (f.suffix.lower(), str(f).lower())}
    return sorted(files, key=keys[sort], reverse=reverse)


def build_cmd(f, a):
    cmd = ["lp", "-n", str(a.copies)]
    if a.printer:
        cmd += ["-d", a.printer]
    if a.duplex:
        cmd += ["-o", "sides=two-sided-long-edge"]
    if a.pages:
        cmd += ["-P", a.pages]
    if a.paper:
        cmd += ["-o", f"media={a.paper}"]
    if a.landscape:
        cmd += ["-o", "landscape"]
    if a.fit:
        cmd += ["-o", "fit-to-page"]
    if a.color is not None:
        cmd += ["-o", "print-color-mode=" + ("color" if a.color else "monochrome")]
    return cmd + ["-t", f.name, str(f)]


def send(f, a, label, results, status, note=""):
    """Envia um arquivo (ou simula) e devolve a saída do lp."""
    cmd = build_cmd(f, a)
    if a.dry_run:
        print(label, "->", " ".join(cmd))
        return ""
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def write_report(path, rows):
    path = Path(path)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["arquivo", "status", "detalhe", "hora"])
            w.writeheader()
            w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="arquivos e/ou pastas")
    ap.add_argument("-p", "--printer", help="nome da impressora (padrão do sistema se omitido)")
    ap.add_argument("-n", "--copies", type=int, default=1)
    ap.add_argument("--duplex", action="store_true", help="frente e verso")
    ap.add_argument("--pages", help="intervalo de páginas, ex: 1-3,5")
    ap.add_argument("--paper", help="tamanho do papel, ex: A4")
    ap.add_argument("--landscape", action="store_true")
    ap.add_argument("--fit", action="store_true", help="ajustar à página")
    ap.add_argument("--color", dest="color", action="store_true", default=None)
    ap.add_argument("--mono", dest="color", action="store_false")
    ap.add_argument("-r", "--recursive", action="store_true")
    ap.add_argument("--filter", action="append", metavar="GLOB", help="só nomes que casam (repetível), ex: '*.pdf'")
    ap.add_argument("--sort", choices=["name", "date", "size", "type"], default="name", help="ordem da fila")
    ap.add_argument("--reverse", action="store_true", help="inverter a ordem")
    ap.add_argument("--cover", choices=sorted(COVERS), help="imprime uma página de rosto antes de cada arquivo")
    ap.add_argument("--failed-page", action="store_true", help="imprime uma página avisando quando um arquivo falha")
    ap.add_argument("--report", metavar="ARQ", help="grava relatório (.csv ou .json)")
    ap.add_argument("--dry-run", action="store_true", help="só mostra o que seria impresso")
    ap.add_argument("--list-printers", action="store_true")
    a = ap.parse_args()

    if a.list_printers:
        return subprocess.call(["lpstat", "-p", "-d"])
    if not a.paths:
        ap.error("informe arquivos ou pastas")
    if not a.dry_run and not shutil.which("lp"):
        sys.exit("erro: 'lp' (CUPS) não encontrado; instale o CUPS ou use --dry-run")

    files = collect(a.paths, a.recursive, a.filter, a.sort, a.reverse)
    if not files:
        sys.exit("nenhum arquivo imprimível encontrado")

    rows, ok, fail = [], 0, 0
    now = lambda: datetime.datetime.now().isoformat(timespec="seconds")
    with tempfile.TemporaryDirectory() as tmp:
        for i, f in enumerate(files, 1):
            tag = f"[{i}/{len(files)}] {f}"
            try:
                src = f
                ext = f.suffix.lower()
                if ext in MAIL:
                    src = eml_to_txt(f, tmp)
                elif ext in OFFICE and not a.dry_run:
                    src = to_pdf(f, tmp)
                elif ext not in SUPPORTED:
                    raise RuntimeError("formato não suportado")
                if a.cover:
                    cov = make_text_pdf(Path(tmp) / f"_cover_{i}.pdf", cover_lines(a.cover, f, i, len(files)))
                    send(cov, argparse.Namespace(**{**vars(a), "copies": 1, "pages": None}), tag + " [rosto]", rows, "")
                out = send(src, a, tag, rows, "")
                if not a.dry_run:
                    print(tag, "OK", out)
                ok += 1
                rows.append({"arquivo": str(f), "status": "ok", "detalhe": out, "hora": now()})
            except Exception as e:
                fail += 1
                print(tag, "FALHOU:", e, file=sys.stderr)
                rows.append({"arquivo": str(f), "status": "falhou", "detalhe": str(e), "hora": now()})
                if a.failed_page:
                    try:
                        pg = make_text_pdf(Path(tmp) / f"_fail_{i}.pdf",
                                           ["ARQUIVO NÃO IMPRESSO", f.name, "Motivo: " + str(e)[:150]])
                        send(pg, argparse.Namespace(**{**vars(a), "copies": 1, "pages": None}), tag + " [aviso]", rows, "")
                    except Exception as e2:
                        print("  também falhou ao imprimir o aviso:", e2, file=sys.stderr)
    if a.report:
        write_report(a.report, rows)
        print("relatório:", a.report)
    print(f"\nTotal: {ok} ok, {fail} falha(s)")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
