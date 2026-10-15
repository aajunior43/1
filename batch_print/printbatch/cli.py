"""Interface de linha de comando."""
import argparse
import sys

from . import __version__, core
from .backends import get_backend

DOC = """PrintBatch: imprime vários documentos de uma vez (PDF, Office, imagens, texto, e-mail).

Exemplos:
  printbatch --list-printers
  printbatch pasta\\ -r -p "Minha Impressora" -n 2 --duplex long --cover filename-folder
  printbatch *.docx --sort date --filter "*relatorio*" --failed-page --report fila.csv --dry-run
Sem argumentos abre a interface gráfica."""


def build_parser():
    ap = argparse.ArgumentParser(prog="printbatch", description=DOC, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="arquivos e/ou pastas")
    ap.add_argument("-p", "--printer", help="impressora (padrão do sistema se omitido)")
    ap.add_argument("-n", "--copies", type=int, default=1)
    ap.add_argument("--duplex", nargs="?", const="long", choices=["long", "short"], help="frente e verso (borda longa/curta)")
    ap.add_argument("--pages", help="intervalo de páginas, ex: 1-3,5")
    ap.add_argument("--paper", help="papel, ex: A4")
    ap.add_argument("--landscape", action="store_true")
    ap.add_argument("--fit", action="store_true", help="ajustar à página")
    ap.add_argument("--color", dest="color", action="store_true", default=None)
    ap.add_argument("--mono", dest="color", action="store_false")
    ap.add_argument("-r", "--recursive", action="store_true")
    ap.add_argument("--filter", action="append", metavar="GLOB", help="só nomes que casam (repetível)")
    ap.add_argument("--sort", choices=core.SORTS, default="name")
    ap.add_argument("--reverse", action="store_true")
    ap.add_argument("--cover", choices=sorted(core.COVERS), help="página de rosto antes de cada arquivo")
    ap.add_argument("--cover-text", help="modelo próprio de rosto; campos: {name} {folder} {folder_path} {ext} {index} {total} {date}")
    ap.add_argument("--failed-page", action="store_true", help="imprime aviso quando um arquivo falha")
    ap.add_argument("--attachments", action="store_true", help="imprime também os anexos de e-mails .eml")
    ap.add_argument("--report", metavar="ARQ", help="relatório .csv ou .json")
    ap.add_argument("--dry-run", action="store_true", help="simula sem imprimir")
    ap.add_argument("--list-printers", action="store_true")
    ap.add_argument("--gui", action="store_true", help="abre a interface gráfica")
    ap.add_argument("--version", action="version", version="PrintBatch " + __version__)
    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.gui or (not a.paths and not a.list_printers):
        from .gui import run_gui
        return run_gui(a.paths)
    backend = get_backend(a.dry_run, log=print)
    if a.list_printers:
        names, default = backend.list_printers()
        for n in names:
            print(("* " if n == default else "  ") + n)
        return 0
    for w in backend.problems():
        print("aviso:", w, file=sys.stderr)
    opts = core.Options(printer=a.printer, copies=a.copies, duplex=a.duplex, pages=a.pages, paper=a.paper,
                        landscape=a.landscape, fit=a.fit, color=a.color, cover=a.cover, cover_text=a.cover_text,
                        failed_page=a.failed_page, attachments=a.attachments, dry_run=a.dry_run)
    try:
        opts.validate()
    except ValueError as e:
        ap.error(str(e))
    files = core.collect(a.paths, a.recursive, a.filter, a.sort, a.reverse,
                         warn=lambda m: print("aviso:", m, file=sys.stderr))
    if not files:
        print("nenhum arquivo imprimível encontrado", file=sys.stderr)
        return 2

    def on_event(kind, **k):
        if kind == "start":
            print(f"[{k['index']}/{k['total']}] {k['file']}")
        elif kind == "error":
            print("   FALHOU:", k["error"], file=sys.stderr)
        elif kind == "ok" and not a.dry_run:
            print("   OK")

    rows = core.run_job(files, opts, backend, on_event)
    if a.report:
        core.write_report(a.report, rows)
        print("relatório:", a.report)
    fail = sum(r["status"] != "ok" for r in rows)
    print(f"\nTotal: {len(rows) - fail} ok, {fail} falha(s)")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
