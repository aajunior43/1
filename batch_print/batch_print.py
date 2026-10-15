#!/usr/bin/env python3
"""Impressão em lote: imprime vários documentos (PDF, Office, imagens, texto) de uma vez.

Usa CUPS (`lp`) em Linux/macOS. Documentos Office são convertidos para PDF com LibreOffice.
Exemplos:
  python3 batch_print.py --list-printers
  python3 batch_print.py pasta/ arquivo.docx -p MinhaImpressora -n 2 --duplex --dry-run
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DIRECT = {".pdf", ".txt", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
OFFICE = {".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ods", ".ppt", ".pptx", ".odp"}


def collect(paths, recursive):
    files = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            files += [f for f in it if f.is_file() and f.suffix.lower() in DIRECT | OFFICE]
        elif p.is_file():
            files.append(p)
        else:
            print(f"aviso: não encontrado: {raw}", file=sys.stderr)
    return sorted(files, key=lambda f: str(f).lower())


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
    ap.add_argument("--dry-run", action="store_true", help="só mostra o que seria impresso")
    ap.add_argument("--list-printers", action="store_true")
    a = ap.parse_args()

    if a.list_printers:
        return subprocess.call(["lpstat", "-p", "-d"])
    if not a.paths:
        ap.error("informe arquivos ou pastas")
    if not a.dry_run and not shutil.which("lp"):
        sys.exit("erro: 'lp' (CUPS) não encontrado; instale o CUPS ou use --dry-run")

    files = collect(a.paths, a.recursive)
    if not files:
        sys.exit("nenhum arquivo imprimível encontrado")

    ok = fail = 0
    with tempfile.TemporaryDirectory() as tmp:
        for i, f in enumerate(files, 1):
            tag = f"[{i}/{len(files)}] {f}"
            try:
                src = f
                if f.suffix.lower() in OFFICE:
                    src = to_pdf(f, tmp) if not a.dry_run else f
                elif f.suffix.lower() not in DIRECT:
                    raise RuntimeError("formato não suportado")
                cmd = build_cmd(src, a)
                if a.dry_run:
                    print(tag, "->", " ".join(cmd))
                else:
                    r = subprocess.run(cmd, capture_output=True, text=True)
                    if r.returncode:
                        raise RuntimeError(r.stderr.strip())
                    print(tag, "OK", r.stdout.strip())
                ok += 1
            except Exception as e:
                fail += 1
                print(tag, "FALHOU:", e, file=sys.stderr)
    print(f"\nTotal: {ok} ok, {fail} falha(s)")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
