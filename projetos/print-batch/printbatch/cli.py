"""Interface de linha de comando."""
import argparse
import sys
from dataclasses import replace

from . import __version__, core, jobqueue
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
    ap.add_argument("--sort", choices=core.SORTS, default="natural", help="ordem da fila (natural: doc2 antes de doc10; folder: agrupa por pasta)")
    ap.add_argument("--reverse", action="store_true")
    ap.add_argument("--cover", choices=sorted(core.COVERS), help="página de rosto antes de cada arquivo")
    ap.add_argument("--cover-text", help="modelo próprio de rosto; campos: {name} {folder} {folder_path} {ext} {index} {total} {date}")
    ap.add_argument("--failed-page", action="store_true", help="imprime aviso quando um arquivo falha")
    ap.add_argument("--attachments", action="store_true", help="imprime também os anexos de e-mails .eml")
    ap.add_argument("--folder-divider", action="store_true", help="página separadora quando muda a pasta")
    ap.add_argument("--set-copies", type=int, default=1, help="imprime a fila inteira N vezes (conjuntos)")
    ap.add_argument("--project", metavar="ARQ", help="carrega fila e opções de um projeto .pbq")
    ap.add_argument("--save-project", metavar="ARQ", help="salva a fila e as opções em um projeto .pbq")
    ap.add_argument("--test-print", action="store_true", help="impressão de teste: só a 1ª página de cada arquivo")
    ap.add_argument("--plan", action="store_true", help="mostra a sequência exata do que seria impresso e sai")
    ap.add_argument("--check", action="store_true", help="verifica a fila (vazios, duplicados, protegidos…) e sai")
    ap.add_argument("--stats", action="store_true", help="mostra páginas e folhas estimadas e sai")
    ap.add_argument("--report", metavar="ARQ", help="relatório .csv ou .json")
    ap.add_argument("--dry-run", action="store_true", help="simula sem imprimir")
    ap.add_argument("--list-printers", action="store_true")
    ap.add_argument("--gui", action="store_true", help="abre a interface gráfica")
    ap.add_argument("--version", action="version", version="PrintBatch " + __version__)
    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.gui or (not a.paths and not a.project and not a.list_printers):
        try:
            from .gui import run_gui
        except ImportError as e:
            print("A interface gráfica precisa do tkinter (Linux: instale python3-tk). Use --help para a linha de comando.\n", e, file=sys.stderr)
            return 2
        return run_gui(a.paths, a.project)
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
                        failed_page=a.failed_page, attachments=a.attachments, dry_run=a.dry_run,
                        folder_divider=a.folder_divider, set_copies=a.set_copies)
    warn = lambda m: print("aviso:", m, file=sys.stderr)
    q = jobqueue.PrintQueue()
    if a.project:
        q, saved = jobqueue.PrintQueue.load(a.project)
        if saved is not None and replace(opts, dry_run=False) == core.Options():
            opts = replace(saved, dry_run=a.dry_run)   # sem opções na linha de comando: usa as salvas no projeto
    if a.paths:
        q.add_paths(a.paths, a.recursive, a.filter, a.sort, warn)
        if a.sort != "natural" or a.reverse:
            q.sort(a.sort, a.reverse)
    try:
        opts.validate()
    except ValueError as e:
        ap.error(str(e))
    if not len(q):
        print("nenhum arquivo imprimível encontrado", file=sys.stderr)
        return 2
    if a.save_project:
        q.save(a.save_project, opts)
        print("projeto salvo:", a.save_project)
    if a.check:
        issues = q.check()
        for i in issues:
            print(f"[{i.level}] {i.path}: {i.message}")
        print(f"{len(issues)} problema(s) em {len(q)} arquivo(s)")
        return 1 if any(i.level == "erro" for i in issues) else 0
    if a.stats:
        s = q.stats(opts)
        print(f"{s['enabled']} de {s['total']} arquivo(s) marcados — {s['pages']} página(s) — "
              f"~{s['sheets']} folha(s)" + (f" (+{s['unknown']} arquivo(s) sem contagem de páginas)" if s["unknown"] else ""))
        print("por tipo:", ", ".join(f"{k}: {v}" for k, v in sorted(s["by_type"].items())))
        return 0

    if a.plan:
        for st in q.plan(opts):
            pg = "?" if st["páginas"] is None else st["páginas"]
            fo = "?" if st["folhas"] is None else st["folhas"]
            print(f"{st['passo']:>3}. {st['tipo']:<9} {st['descrição']}  — págs {pg} × {st['cópias']} → {fo} folha(s)  (total {st['acumulado']})")
        return 0
    items = q.items
    if a.test_print:
        items, opts = core.as_test_job(items, opts)

    def on_event(kind, **k):
        if kind == "start":
            print(f"[{k['index']}/{k['total']}] {k['file']}")
        elif kind == "error":
            print("   FALHOU:", k["error"], file=sys.stderr)
        elif kind == "ok" and not a.dry_run:
            print("   OK")

    rows = core.run_job(items, opts, backend, on_event)
    if a.report:
        core.write_report(a.report, rows)
        print("relatório:", a.report)
    fail = sum(r["status"] == "falhou" for r in rows)
    ok = sum(r["status"] == "ok" for r in rows)
    print(f"\nTotal: {ok} ok, {fail} falha(s)")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
