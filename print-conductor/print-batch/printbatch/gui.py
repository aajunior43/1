"""Interface gráfica (tkinter) com fila organizável."""
import base64
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__, core, fileinfo, nup, preview as pv, theme
from .watcher import FolderWatcher
from .backends import get_backend
from .jobqueue import PrintQueue

try:  # arrastar e soltar arquivos do Explorer (opcional: pip install tkinterdnd2)
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _Root = TkinterDnD.Tk
except Exception:  # pragma: no cover
    DND_FILES, _Root = None, tk.Tk

DUPLEX = {"Desligado": None, "Borda longa": "long", "Borda curta": "short"}
COLOR = {"Padrão da impressora": None, "Colorido": True, "Preto e branco": False}
PER_SHEET = {"1 página (normal)": 1, "2 por folha": 2, "4 por folha": 4, "6 por folha": 6, "9 por folha": 9}
COVER_NAMES = {"Sem página de rosto": None, "Nome do arquivo": "filename", "Nome + pasta": "filename-folder",
               "Completa": "full", "Número na fila": "number", "Personalizada…": "custom"}
ITEM_DUPLEX = {"(padrão)": None, "Desligado": "off", "Borda longa": "long", "Borda curta": "short"}
ITEM_COLOR = {"(padrão)": None, "Colorido": "color", "Preto e branco": "mono"}
SORT_LABELS = {"Natural": "natural", "Nome": "name", "Data": "date", "Tamanho": "size",
               "Tipo": "type", "Pasta": "folder", "Nº de páginas": "pages"}
PAPERS = ["", "A4", "A3", "A5", "Letter", "Legal"]
COL_SORT = {"nome": "natural", "tipo": "type", "pags": "pages", "tam": "size", "pasta": "folder"}
COLS = ("on", "n", "nome", "tipo", "pags", "copias", "fv", "sel", "tam", "pasta", "estado", "nota")
HEAD = {"on": "✔", "n": "#", "nome": "Nome", "tipo": "Tipo", "pags": "Págs", "copias": "Cópias", "fv": "F/V",
        "sel": "Intervalo", "tam": "Tamanho", "pasta": "Pasta", "estado": "Estado", "nota": "Nota"}
WIDTH = {"on": 34, "n": 38, "nome": 230, "tipo": 52, "pags": 52, "copias": 56, "fv": 52, "sel": 80, "tam": 76,
         "pasta": 220, "estado": 110, "nota": 140}


def fmt_size(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


def open_path(path):
    try:
        if core.IS_WINDOWS:
            os.startfile(str(path))  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:
        messagebox.showerror("PrintBatch", str(e))


def reveal(path):
    path = Path(path)
    try:
        if core.IS_WINDOWS:
            subprocess.Popen(["explorer", "/select,", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent)])
    except Exception as e:
        messagebox.showerror("PrintBatch", str(e))


TIPS = {
    "＋ Arquivos…": "Adicionar arquivos à fila  (Ctrl+O)",
    "＋ Pasta…": "Adicionar todos os documentos de uma pasta",
    "👁 Pré-visualização": "Mostrar ou esconder a miniatura da página",
    "Remover": "Tirar os selecionados da fila  (Delete)",
    "Limpar": "Esvaziar a fila (dá para desfazer)",
    "▲": "Subir os selecionados  (Alt+↑)",
    "▼": "Descer os selecionados  (Alt+↓)",
    "↶ Desfazer": "Desfazer a última alteração  (Ctrl+Z)",
    "↷ Refazer": "Refazer  (Ctrl+Y)",
    "Aplicar": "Aplicar",
    "Remover duplicados": "Remove arquivos com conteúdo idêntico, mantendo o primeiro",
    "Remover desmarcados": "Tira da fila os arquivos desmarcados (☐)",
    "✓ Verificar fila": "Procura arquivos vazios, protegidos, temporários e duplicados",
    "Marcar": "Marcar todos para impressão",
    "Desmarcar": "Desmarcar todos",
    "Ajustes…": "Cópias, páginas, frente e verso e cor só dos selecionados  (duplo clique)",
    "Ver plano…": "Mostra a sequência exata do que vai sair e o total de folhas",
    "Imprimir teste": "Imprime só a 1ª página de cada arquivo, para conferir sem gastar papel",
    "Cancelar": "Interrompe a impressão depois do arquivo atual",
    "Mais ▾": "Projetos, relatório, monitorar pasta, histórico, diagnóstico e atalhos",
    "☾ Escuro": "Trocar para o tema escuro",
    "☀ Claro": "Trocar para o tema claro",
}


class Tooltip:
    """Dica que aparece ao parar o mouse sobre um botão."""

    def __init__(self, widget, text, pal):
        self.w, self.text, self.pal, self.tip, self.job = widget, text, pal, None, None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def schedule(self, e=None):
        self.hide()
        self.job = self.w.after(600, self.show)

    def show(self):
        if self.tip or not self.w.winfo_exists():
            return
        self.tip = tk.Toplevel(self.w)
        self.tip.wm_overrideredirect(True)
        x, y = self.w.winfo_rootx() + 10, self.w.winfo_rooty() + self.w.winfo_height() + 6
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, background=self.pal["text"], foreground=self.pal["card"],
                 padx=8, pady=4, font=(self.pal["font"], 9)).pack()

    def hide(self, e=None):
        if self.job:
            self.w.after_cancel(self.job)
            self.job = None
        if self.tip:
            self.tip.destroy()
            self.tip = None


SHORTCUTS = (
    ("Ctrl+O", "Adicionar arquivos"), ("Ctrl+P", "Imprimir os marcados"), ("Ctrl+Z / Ctrl+Y", "Desfazer / refazer"),
    ("Ctrl+A", "Selecionar tudo na lista"), ("Delete", "Remover os selecionados"), ("Espaço", "Marcar/desmarcar os selecionados"),
    ("Alt+↑ / Alt+↓", "Mover os selecionados"), ("Duplo clique", "Ajustes do arquivo (cópias, páginas, frente e verso)"),
    ("Clique em ☑", "Marcar/desmarcar um arquivo"), ("Arrastar linha", "Reordenar a fila"),
    ("Clique no cabeçalho", "Ordenar pela coluna (de novo inverte)"), ("Botão direito", "Abrir, mostrar na pasta, duplicar, remover"),
    ("F1", "Esta janela"),
)


class ItemDialog(tk.Toplevel):
    """Ajustes que valem só para os itens selecionados."""

    def __init__(self, app, indices):
        super().__init__(app.root)
        self.app, self.indices = app, indices
        self.title(f"Ajustes de {len(indices)} arquivo(s)")
        self.transient(app.root)
        self.configure(background=app.pal["bg"])
        self.resizable(False, False)
        first = app.q.items[indices[0]]
        f = ttk.Frame(self, padding=12)
        f.pack()
        self.copies = tk.StringVar(value=str(first.copies or ""))
        self.pages = tk.StringVar(value=first.pages or "")
        rev = lambda m, v: next((k for k, x in m.items() if x == v), "(padrão)")
        self.duplex = tk.StringVar(value=rev(ITEM_DUPLEX, first.duplex))
        self.color = tk.StringVar(value=rev(ITEM_COLOR, first.color))
        self.note = tk.StringVar(value=first.note)
        rows = (("Cópias (vazio = padrão)", ttk.Spinbox(f, from_=1, to=999, textvariable=self.copies, width=8)),
                ("Páginas (ex.: 1-3,5)", ttk.Entry(f, textvariable=self.pages, width=18)),
                ("Frente e verso", ttk.Combobox(f, textvariable=self.duplex, values=list(ITEM_DUPLEX), state="readonly")),
                ("Cor", ttk.Combobox(f, textvariable=self.color, values=list(ITEM_COLOR), state="readonly")),
                ("Nota", ttk.Entry(f, textvariable=self.note, width=30)))
        for r, (label, w) in enumerate(rows):
            ttk.Label(f, text=label).grid(row=r, column=0, sticky="w", pady=3, padx=(0, 10))
            w.grid(row=r, column=1, sticky="w", pady=3)
        b = ttk.Frame(f)
        b.grid(row=len(rows), column=0, columnspan=2, pady=(10, 0), sticky="e")
        ttk.Button(b, text="Limpar ajustes", command=self.clear).pack(side="left", padx=4)
        ttk.Button(b, text="Cancelar", command=self.destroy).pack(side="left", padx=4)
        ttk.Button(b, text="Aplicar", command=self.apply).pack(side="left", padx=4)
        self.bind("<Return>", lambda e: self.apply())
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()

    def clear(self):
        self.app.q.set_overrides(self.indices, copies="", pages="", duplex="", color="", note="")
        self.app.refresh()
        self.destroy()

    def apply(self):
        try:
            self.app.q.set_overrides(self.indices, copies=self.copies.get().strip(), pages=self.pages.get().strip(),
                                     duplex=ITEM_DUPLEX[self.duplex.get()], color=ITEM_COLOR[self.color.get()],
                                     note=self.note.get())
        except ValueError as e:
            messagebox.showerror("PrintBatch", str(e), parent=self)
            return
        self.app.refresh()
        self.destroy()


class App:
    def __init__(self, root, initial=(), project=None):
        self.root = root
        root.title(f"PrintBatch {__version__} — organizar e imprimir em lote")
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{min(1600, sw - 40) if sw >= 1500 else min(1280, sw - 40)}x{min(860, sh - 60)}")
        root.minsize(1000, 600)
        self.q = PrintQueue()
        self.status, self.issues = {}, {}
        self.visible = []
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker, self.rows = None, []
        self.cfg = core.load_config()
        self.mode = self.cfg.get("theme", "light")
        self.pal = theme.apply(root, self.mode)
        self.set_icon()
        self.sort_col, self.sort_rev = None, False
        self.watcher, self.watch_auto, self.watch_job, self.watch_backlog = None, False, None, []
        self.backend = get_backend(False)
        self.drag = None
        self.build()
        self.load_printers()
        self.set_state(self.cfg)
        self.refresh_presets()
        for p in self.backend.problems():
            self.log("AVISO: " + p)
        if project:
            self.open_project(project)
        if initial:
            self.add_paths(initial)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.report_callback_exception = self.on_callback_error
        self.restore_geometry()
        self.refresh()
        root.after(100, self.poll)
        root.after(60000, self.autosave_loop)
        if not project and not initial:
            root.after(400, self.offer_restore)

    # ================= construção =================
    def build(self):
        pad = dict(padx=4, pady=3)
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=14, pady=(12, 2))
        ttk.Label(header, text="🖨  PrintBatch", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Organize e imprima documentos em lote", style="Subtitle.TLabel").pack(side="left", padx=14, pady=(7, 0))
        self.theme_btn = ttk.Button(header, text="☾ Escuro" if self.mode == "light" else "☀ Claro",
                                    style="Tool.TButton", command=self.toggle_theme)
        self.theme_btn.pack(side="right")
        self.summary = ttk.Label(header, text="", style="Chip.TLabel")
        self.summary.pack(side="right", padx=12)
        self.watch_chip = ttk.Label(header, text="", style="Chip.TLabel")
        main = ttk.PanedWindow(self.root, orient="horizontal")
        main.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        left, right = ttk.Frame(main), ttk.Frame(main, width=330)
        self.main, self.mid = main, ttk.Frame(main, width=330)
        main.add(left, weight=1)
        main.add(right, weight=0)
        self.build_preview(self.mid)
        self.preview_on = self.root.winfo_screenwidth() >= 1500
        if self.preview_on:
            main.insert(1, self.mid, weight=0)

        # --- barra 1: adicionar / editar ---
        bar = ttk.Frame(left)
        bar.pack(fill="x")
        for text, cmd in (("＋ Arquivos…", self.add_files), ("＋ Pasta…", self.add_folder)):
            ttk.Button(bar, style="Tool.TButton", text=text, command=cmd).pack(side="left", **pad)
        self.recursive = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="subpastas", variable=self.recursive).pack(side="left", **pad)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(bar, style="Tool.TButton", text="👁 Pré-visualização", command=self.toggle_preview).pack(side="left", **pad)
        bar1b = ttk.Frame(left)
        bar1b.pack(fill="x")
        for text, cmd in (("Remover", self.remove), ("Limpar", self.clear), ("▲", lambda: self.move(-1)), ("▼", lambda: self.move(1)),
                          ("↶ Desfazer", self.undo), ("↷ Refazer", self.redo)):
            ttk.Button(bar1b, style="Tool.TButton", text=text, command=cmd, width=3 if len(text) == 1 else None).pack(side="left", **pad)

        # --- barra 2: organizar ---
        bar2 = ttk.LabelFrame(left, text="Organizar")
        bar2.pack(fill="x", pady=3)
        bar2a = ttk.Frame(bar2)
        bar2a.pack(fill="x")
        ttk.Label(bar2a, text="Ordenar").pack(side="left", **pad)
        self.sort = tk.StringVar(value="Natural")
        ttk.Combobox(bar2a, textvariable=self.sort, values=list(SORT_LABELS), width=15, state="readonly").pack(side="left")
        self.reverse = tk.BooleanVar()
        ttk.Checkbutton(bar2a, text="inverter", variable=self.reverse).pack(side="left", **pad)
        ttk.Button(bar2a, style="Tool.TButton", text="Aplicar", command=self.apply_sort).pack(side="left", **pad)
        ttk.Label(bar2a, text="Agrupar:", style="Muted.TLabel").pack(side="left", padx=(12, 2))
        ttk.Button(bar2a, style="Tool.TButton", text="Pasta", command=lambda: self.apply_sort("folder")).pack(side="left", **pad)
        ttk.Button(bar2a, style="Tool.TButton", text="Tipo", command=lambda: self.apply_sort("type")).pack(side="left", **pad)
        bar2b = ttk.Frame(bar2)
        bar2b.pack(fill="x")
        ttk.Button(bar2b, style="Tool.TButton", text="Remover duplicados", command=self.remove_duplicates).pack(side="left", **pad)
        ttk.Button(bar2b, style="Tool.TButton", text="Remover desmarcados", command=lambda: (self.q.remove_disabled(), self.refresh())).pack(side="left", **pad)
        ttk.Button(bar2b, style="Tool.TButton", text="✓ Verificar fila", command=self.verify).pack(side="left", **pad)
        ttk.Separator(bar2b, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(bar2b, style="Tool.TButton", text="Marcar", command=lambda: self.set_enabled(True, all_rows=True)).pack(side="left", **pad)
        ttk.Button(bar2b, style="Tool.TButton", text="Desmarcar", command=lambda: self.set_enabled(False, all_rows=True)).pack(side="left", **pad)
        ttk.Button(bar2b, style="Tool.TButton", text="Ajustes…", command=self.edit_selected).pack(side="left", **pad)

        # --- barra 3: busca / filtro / seleção ---
        bar3 = ttk.Frame(left)
        bar3.pack(fill="x")
        ttk.Label(bar3, text="Buscar").pack(side="left", **pad)
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *a: self.refresh())
        ttk.Entry(bar3, textvariable=self.search, width=22).pack(side="left")
        ttk.Button(bar3, style="Tool.TButton", text="✕", width=2, command=lambda: self.search.set("")).pack(side="left", **pad)
        ttk.Label(bar3, text="Manter só (padrões)").pack(side="left", padx=(14, 2))
        self.filter = tk.StringVar()
        ttk.Entry(bar3, textvariable=self.filter, width=18).pack(side="left")
        ttk.Button(bar3, style="Tool.TButton", text="Aplicar", command=self.apply_filter).pack(side="left", **pad)

        # --- lista ---
        frame = ttk.Frame(left)
        frame.pack(fill="both", expand=True, pady=4)
        self.tree = ttk.Treeview(frame, columns=COLS, show="headings", selectmode="extended")
        for c in COLS:
            self.tree.heading(c, text=HEAD[c], command=(lambda c=c: self.sort_by_column(c)) if c in COL_SORT else "")
            self.tree.column(c, width=WIDTH[c], anchor="center" if c in ("on", "n", "tipo", "pags", "copias", "fv", "sel") else "w",
                             stretch=c in ("nome", "pasta", "nota"))
        self.empty = ttk.Label(frame, style="Empty.TLabel", justify="center", cursor="hand2",
                               text="🗂\n\nArraste arquivos ou pastas para cá\nou clique para escolher\n\n"
                                    "PDF · Word · Excel · PowerPoint · imagens · texto · e-mail")
        self.empty.bind("<Button-1>", lambda e: self.add_files())
        ys = ttk.Scrollbar(frame, command=self.tree.yview)
        xs = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.style_tags()
        self.tree.bind("<ButtonPress-1>", self.on_press)
        self.tree.bind("<B1-Motion>", self.on_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_release)
        self.tree.bind("<Double-1>", lambda e: self.edit_selected() if self.tree.identify_column(e.x) != "#1" else None)
        self.tree.bind("<Button-3>", self.popup)
        self.tree.bind("<Button-2>", self.popup)
        self.tree.bind("<<TreeviewSelect>>", lambda e: (self.show_details(), self.schedule_preview()))
        for seq, fn in (("<Delete>", lambda e: self.remove()), ("<space>", lambda e: self.toggle_selected()),
                        ("<Control-a>", lambda e: (self.tree.selection_set(self.tree.get_children()), "break")[1]),
                        ("<Control-z>", lambda e: self.undo()), ("<Control-y>", lambda e: self.redo()),
                        ("<Control-o>", lambda e: self.add_files()), ("<Control-p>", lambda e: self.start()),
                        ("<Alt-Up>", lambda e: self.move(-1)), ("<Alt-Down>", lambda e: self.move(1))):
            self.root.bind(seq, fn)
        if DND_FILES:
            self.tree.drop_target_register(DND_FILES)
            self.tree.dnd_bind("<<Drop>>", lambda e: self.add_paths(self.root.tk.splitlist(e.data)))
        self.menu = tk.Menu(self.root, tearoff=0)
        theme.style_menu(self.menu, self.pal)
        for label, cmd in (("Abrir arquivo", self.open_selected), ("Mostrar na pasta", self.reveal_selected),
                           (None, None), ("Marcar/desmarcar", self.toggle_selected), ("Ajustes do arquivo…", self.edit_selected),
                           ("Duplicar na fila (reimprimir)", self.duplicate_selected), (None, None), ("Remover da fila", self.remove)):
            self.menu.add_separator() if label is None else self.menu.add_command(label=label, command=cmd)

        # --- resumo / detalhes / progresso / log ---
        self.details = ttk.Label(left, text="", style="Muted.TLabel")
        self.details.pack(anchor="w", pady=(2, 0))
        self.progress = ttk.Progressbar(left, mode="determinate")
        self.progress.pack(fill="x", pady=(4, 0))
        self.prog_label = ttk.Label(left, text="", style="Muted.TLabel")
        self.prog_label.pack(anchor="w")
        self.logbox = tk.Text(left, height=7, state="disabled", wrap="word")
        theme.style_text(self.logbox, self.pal)
        self.logbox.pack(fill="x", pady=3)

        # ================= painel direito =================
        pr = ttk.LabelFrame(right, text="Perfil")
        pr.pack(fill="x", **pad)
        self.preset = tk.StringVar()
        self.preset_cb = ttk.Combobox(pr, textvariable=self.preset, width=18)
        self.preset_cb.pack(side="left", fill="x", expand=True, padx=4, pady=2)
        self.preset_cb.bind("<<ComboboxSelected>>", lambda e: self.load_preset())
        ttk.Button(pr, text="Salvar", style="Tool.TButton", command=self.save_preset).pack(side="left", padx=2, pady=2)
        ttk.Button(pr, text="✕", width=3, style="Tool.TButton", command=self.delete_preset).pack(side="left", padx=2, pady=2)

        rpad = dict(padx=4, pady=1)
        box = ttk.LabelFrame(right, text="Impressão")
        box.pack(fill="x", **rpad)
        ttk.Label(box, text="Impressora").grid(row=0, column=0, sticky="w", **rpad)
        self.printer = tk.StringVar()
        self.printer_cb = ttk.Combobox(box, textvariable=self.printer, state="readonly", width=24)
        self.printer_cb.grid(row=1, column=0, columnspan=2, sticky="we", **rpad)
        ttk.Button(box, text="↻", width=3, command=self.load_printers).grid(row=1, column=2, **rpad)
        self.copies = tk.IntVar(value=1)
        self.set_copies = tk.IntVar(value=1)
        self.retries = tk.IntVar(value=1)
        self.duplex = tk.StringVar(value="Desligado")
        self.color = tk.StringVar(value="Padrão da impressora")
        self.paper = tk.StringVar()
        self.pages = tk.StringVar()
        self.landscape, self.fit = tk.BooleanVar(), tk.BooleanVar()
        self.per_sheet = tk.StringVar(value="1 página (normal)")
        self.sheet_border = tk.BooleanVar(value=True)
        grid = (("Cópias de cada arquivo", ttk.Spinbox(box, from_=1, to=999, textvariable=self.copies, width=6)),
                ("Repetir a fila inteira", ttk.Spinbox(box, from_=1, to=99, textvariable=self.set_copies, width=6)),
                ("Tentar de novo se falhar", ttk.Spinbox(box, from_=0, to=10, textvariable=self.retries, width=6)),
                ("Frente e verso", ttk.Combobox(box, textvariable=self.duplex, values=list(DUPLEX), state="readonly", width=14)),
                ("Cor", ttk.Combobox(box, textvariable=self.color, values=list(COLOR), state="readonly", width=18)),
                ("Papel", ttk.Combobox(box, textvariable=self.paper, values=PAPERS, width=8)),
                ("Páginas (todos)", ttk.Entry(box, textvariable=self.pages, width=12)),
                ("Páginas por folha", ttk.Combobox(box, textvariable=self.per_sheet, values=list(PER_SHEET), state="readonly", width=16)))
        for r, (label, w) in enumerate(grid, start=2):
            ttk.Label(box, text=label).grid(row=r, column=0, sticky="w", **rpad)
            w.grid(row=r, column=1, columnspan=2, sticky="w", **rpad)
        ttk.Checkbutton(box, text="Paisagem", variable=self.landscape).grid(row=10, column=0, sticky="w", **rpad)
        ttk.Checkbutton(box, text="Ajustar à página", variable=self.fit).grid(row=10, column=1, columnspan=2, sticky="w", **rpad)
        ttk.Checkbutton(box, text="Linha em volta de cada página da folha", variable=self.sheet_border).grid(
            row=11, column=0, columnspan=3, sticky="w", **rpad)

        ext = ttk.LabelFrame(right, text="Separadores e extras")
        ext.pack(fill="x", **rpad)
        self.cover = tk.StringVar(value="Sem página de rosto")
        ttk.Label(ext, text="Página de rosto (antes de cada arquivo)").pack(anchor="w", **rpad)
        cb = ttk.Combobox(ext, textvariable=self.cover, values=list(COVER_NAMES), state="readonly")
        cb.pack(fill="x", **rpad)
        cb.bind("<<ComboboxSelected>>", lambda e: (self.toggle_cover(), self.update_summary()))
        self.cover_logo = tk.StringVar()
        logo_row = ttk.Frame(ext)
        logo_row.pack(fill="x", **rpad)
        ttk.Button(logo_row, text="Logotipo…", style="Tool.TButton", command=self.choose_logo).pack(side="left")
        ttk.Button(logo_row, text="✕", width=3, style="Tool.TButton", command=lambda: self.cover_logo.set("")).pack(side="left", padx=4)
        self.logo_lbl = ttk.Label(logo_row, text="sem logotipo", style="Muted.TLabel")
        self.logo_lbl.pack(side="left", padx=4)
        self.cover_logo.trace_add("write", lambda *a: self.logo_lbl.config(
            text=Path(self.cover_logo.get()).name if self.cover_logo.get() else "sem logotipo"))
        self.cover_text = tk.Text(ext, height=4, width=30)
        theme.style_text(self.cover_text, self.pal)
        self.cover_text.insert("1.0", "{name}\nPasta: {folder}\nArquivo {index} de {total}")
        self.cover_hint = ttk.Label(ext, text="Campos: {name} {folder} {folder_path} {ext} {index} {total} {date}",
                                    style="Muted.TLabel", wraplength=290)
        self.divider = tk.BooleanVar()
        self.failed = tk.BooleanVar(value=True)
        self.attach = tk.BooleanVar()
        self.dry = tk.BooleanVar()
        self.check_frame = ttk.Frame(ext)
        self.check_frame.pack(fill="x")
        for text, var in (("Separador quando mudar a pasta", self.divider),
                          ("Imprimir aviso se um arquivo falhar", self.failed),
                          ("Imprimir anexos de e-mails (.eml)", self.attach),
                          ("Simular (não imprime)", self.dry)):
            ttk.Checkbutton(self.check_frame, text=text, variable=var).pack(anchor="w", **rpad)
        for v in (self.copies, self.set_copies, self.duplex, self.pages, self.divider, self.per_sheet,
                  self.sheet_border, self.cover):
            v.trace_add("write", lambda *a: self.update_summary())

        act = ttk.Frame(right)
        act.pack(fill="x", padx=4, pady=(8, 2))
        self.btn_print = ttk.Button(act, text="🖨  Imprimir marcados  (Ctrl+P)", style="Accent.TButton", command=self.start)
        self.btn_print.pack(fill="x", pady=(0, 4))
        row = ttk.Frame(act)
        row.pack(fill="x")
        ttk.Button(row, text="Ver plano…", style="Tool.TButton", command=self.show_plan).pack(side="left", fill="x", expand=True, padx=(0, 3))
        ttk.Button(row, text="Imprimir teste", style="Tool.TButton", command=lambda: self.start(test=True)).pack(side="left", fill="x", expand=True, padx=(3, 0))
        row2 = ttk.Frame(act)
        row2.pack(fill="x", pady=(4, 0))
        self.btn_cancel = ttk.Button(row2, text="Cancelar", style="Danger.TButton", command=self.cancel.set, state="disabled")
        self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 3))
        more = ttk.Menubutton(row2, text="Mais ▾", style="Tool.TButton")
        mm = tk.Menu(more, tearoff=0)
        theme.style_menu(mm, self.pal)
        for text, cmd in (("Abrir projeto…", self.open_project_dialog), ("Salvar projeto…", self.save_project),
                          ("Salvar relatório…", self.save_report), (None, None),
                          ("Reimprimir só as falhas", self.retry_failed), ("Abrir histórico de impressões", self.open_history), (None, None),
                          ("Monitorar uma pasta…", self.toggle_watch), (None, None),
                          ("Atalhos de teclado (F1)", self.show_shortcuts),
                          ("Diagnóstico…", self.show_diagnostico), ("Abrir pasta de logs", lambda: open_path(core.config_dir()))):
            mm.add_separator() if text is None else mm.add_command(label=text, command=cmd)
        more["menu"] = mm
        more.pack(side="left", fill="x", expand=True, padx=(3, 0))
        self.more_menu = mm
        self.toggle_cover()
        self.root.bind("<F1>", lambda e: self.show_shortcuts())
        self.attach_tips(self.root)

    # ================= ícone, janela e sessão =================
    def set_icon(self):
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "printbatch" / "assets"
        try:
            self._icon = tk.PhotoImage(file=str(base / "icon.png"))
            self.root.iconphoto(True, self._icon)
        except Exception:
            pass

    def restore_geometry(self):
        g = self.cfg.get("geometry")
        if isinstance(g, str):
            import re
            m = re.fullmatch(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", g)
            if m:
                w, h, x, y = map(int, m.groups())
                sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
                if 600 <= w <= sw and 400 <= h <= sh and -50 <= x < sw - 100 and -10 <= y < sh - 100:
                    self.root.geometry(g)
        for c, w in (self.cfg.get("col_widths") or {}).items():
            if c in COLS and isinstance(w, int) and 20 <= w <= 800:
                self.tree.column(c, width=w)

    SESSION_FILE = "fila-anterior.pbq"

    def autosave(self):
        if len(self.q):
            try:
                self.q.save(core.config_dir() / self.SESSION_FILE, self.options(validate=False))
            except Exception:
                pass

    def autosave_loop(self):
        self.autosave()
        self.root.after(60000, self.autosave_loop)

    def offer_restore(self):
        f = core.config_dir() / self.SESSION_FILE
        if len(self.q) or not f.exists():
            return
        try:
            old, _ = PrintQueue.load(f)
        except Exception:
            return
        if not len(old):
            return
        if messagebox.askyesno("PrintBatch", f"Restaurar a fila da última sessão ({len(old)} arquivo(s))?"):
            self.open_project(str(f))

    # ================= monitorar pasta =================
    def toggle_watch(self):
        if self.watcher:
            self.stop_watch()
            return
        d = filedialog.askdirectory(title="Pasta a monitorar (arquivos novos entram na fila)")
        if not d:
            return
        auto = messagebox.askyesno("Monitorar pasta", "Imprimir automaticamente os arquivos que chegarem?\n\n"
                                   "Sim = imprime sozinho com as opções atuais.\nNão = só coloca na fila para você conferir.")
        self.watcher, self.watch_auto = FolderWatcher(d, recursive=self.recursive.get()), auto
        self.watch_chip.config(text=f"👁 Monitorando: {Path(d).name or d}" + ("  (imprime sozinho)" if auto else ""))
        self.watch_chip.pack(side="right", padx=(0, 10))
        self.log(f"Monitorando {d} — arquivos novos {'serão impressos' if auto else 'entram na fila'}")
        self.watch_job = self.root.after(3000, self.watch_tick)

    def stop_watch(self):
        self.watcher = None
        if self.watch_job:
            self.root.after_cancel(self.watch_job)
            self.watch_job = None
        self.watch_chip.pack_forget()
        self.log("Monitoramento de pasta desligado")

    def watch_tick(self):
        self.watch_job = None
        if not self.watcher:
            return
        try:
            new = self.watcher.scan()
            if new:
                added = self.q.add_paths([str(f) for f in new], False, None, "natural", self.log)
                self.refresh()
                if added:
                    self.log(f"{len(added)} arquivo(s) novo(s) na pasta monitorada")
                    if self.watch_auto:
                        if self.worker and self.worker.is_alive():
                            self.watch_backlog += added
                        else:
                            self.start(only=added + self.watch_backlog)
                            self.watch_backlog = []
            elif self.watch_backlog and not (self.worker and self.worker.is_alive()):
                self.start(only=self.watch_backlog)
                self.watch_backlog = []
        except Exception as e:
            core.log_error(f"monitoramento: {e}")
        self.watch_job = self.root.after(3000, self.watch_tick)

    def show_shortcuts(self):
        win = tk.Toplevel(self.root)
        win.configure(background=self.pal["bg"])
        win.title("Atalhos de teclado e dicas")
        win.transient(self.root)
        win.resizable(False, False)
        f = ttk.Frame(win, padding=16)
        f.pack()
        ttk.Label(f, text="Atalhos e dicas", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        for r, (k, d) in enumerate(SHORTCUTS, start=1):
            ttk.Label(f, text=k, style="Chip.TLabel").grid(row=r, column=0, sticky="w", pady=3, padx=(0, 14))
            ttk.Label(f, text=d).grid(row=r, column=1, sticky="w", pady=3)
        ttk.Button(f, text="Fechar", command=win.destroy).grid(row=len(SHORTCUTS) + 1, column=1, sticky="e", pady=(12, 0))
        win.bind("<Escape>", lambda e: win.destroy())

    def attach_tips(self, widget):
        for w in widget.winfo_children():
            if isinstance(w, (ttk.Button, ttk.Menubutton)):
                t = TIPS.get(str(w.cget("text")))
                if t:
                    Tooltip(w, t, self.pal)
            self.attach_tips(w)

    def retry_failed(self):
        failed = {r["arquivo"] for r in self.rows if r["status"] == "falhou"}
        if not failed:
            messagebox.showinfo("PrintBatch", "Não há falhas no último lote.")
            return
        self.q.snapshot()
        for it in self.q.items:
            it.enabled = str(it.path) in failed
        self.refresh()
        self.start()

    def open_history(self):
        f = core.config_dir() / "historico.csv"
        if f.exists():
            open_path(f)
        else:
            messagebox.showinfo("PrintBatch", "Ainda não há histórico: ele é criado depois da primeira impressão.")

    # ================= erros e diagnóstico =================
    def on_callback_error(self, kind, value, tb):
        import traceback
        text = "".join(traceback.format_exception(kind, value, tb))
        core.log_error(text)
        self.log("ERRO inesperado: " + str(value) + "  (detalhes em erros.log)")

    def show_diagnostico(self):
        win = tk.Toplevel(self.root)
        win.configure(background=self.pal["bg"])
        win.title("Diagnóstico")
        win.geometry("860x560")
        win.transient(self.root)
        box = tk.Text(win, wrap="word")
        theme.style_text(box, self.pal)
        box.insert("1.0", "Testando o seu sistema… (a conversão de documentos pode levar alguns segundos)")
        box.config(state="disabled")
        box.pack(fill="both", expand=True, padx=8, pady=8)
        bar = ttk.Frame(win)
        bar.pack(fill="x", padx=8, pady=(0, 8))

        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(box.get("1.0", "end").strip())
            self.log("Relatório de diagnóstico copiado")

        ttk.Button(bar, text="Copiar relatório", command=copy).pack(side="left")
        ttk.Button(bar, text="Fechar", command=win.destroy).pack(side="right")
        res = {}

        def work():
            from . import diagnostico
            res["text"] = diagnostico.format_report(diagnostico.run(full=True))

        def poll():
            if "text" in res:
                box.config(state="normal")
                box.delete("1.0", "end")
                box.insert("1.0", res["text"])
                box.config(state="disabled")
            else:
                win.after(300, poll)

        threading.Thread(target=work, daemon=True).start()
        win.after(300, poll)

    def sort_by_column(self, col):
        """Clique no cabeçalho ordena; novo clique na mesma coluna inverte."""
        key = COL_SORT.get(col)
        if not key:
            return
        self.sort_rev = (not self.sort_rev) if self.sort_col == col else False
        self.sort_col = col
        self.q.sort(key, self.sort_rev)
        for c in COLS:
            arrow = (" ▼" if self.sort_rev else " ▲") if c == col else ""
            self.tree.heading(c, text=HEAD[c] + arrow)
        self.refresh()

    # ================= aparência =================
    def style_tags(self):
        p = self.pal
        self.tree.tag_configure("odd", background=p["zebra"])
        self.tree.tag_configure("even", background=p["card"])
        self.tree.tag_configure("off", foreground=p["off"])
        self.tree.tag_configure("erro", foreground=p["error"])
        self.tree.tag_configure("aviso", foreground=p["warn"])
        self.tree.tag_configure("ok", foreground=p["ok"])

    def toggle_theme(self):
        self.mode = "dark" if self.mode == "light" else "light"
        self.cfg["theme"] = self.mode
        self.pal = theme.apply(self.root, self.mode)
        self.theme_btn.config(text="☾ Escuro" if self.mode == "light" else "☀ Claro")
        theme.style_text(self.logbox, self.pal)
        theme.style_text(self.cover_text, self.pal)
        theme.style_menu(self.menu, self.pal)
        theme.style_menu(self.more_menu, self.pal)
        self.prev_canvas.config(background=self.pal["preview_bg"], foreground=self.pal["muted"])
        self.prev_title.config(font=(self.pal["font"], 10, "bold"))
        self.style_tags()
        self.refresh()

    # ================= pré-visualização =================
    def build_preview(self, f):
        self.previewer = pv.Previewer()
        self.prev_req, self.prev_index, self.prev_total, self.prev_job = 0, 0, 0, None
        self.prev_img = None
        box = ttk.LabelFrame(f, text="Pré-visualização")
        box.pack(fill="both", expand=True, padx=4, pady=2)
        self.prev_title = ttk.Label(box, text="", font=(self.pal["font"], 10, "bold"), wraplength=300)
        self.prev_title.pack(fill="x", padx=6, pady=(4, 0))
        self.prev_canvas = tk.Label(box, text="Selecione um arquivo", background=self.pal["preview_bg"], foreground=self.pal["muted"], anchor="center",
                                    width=44, height=24)
        self.prev_canvas.pack(fill="both", expand=True, padx=6, pady=4)
        nav = ttk.Frame(box)
        nav.pack(fill="x")
        ttk.Button(nav, text="◀", width=3, command=lambda: self.prev_goto(-1)).pack(side="left", padx=6)
        self.prev_page = ttk.Label(nav, text="")
        self.prev_page.pack(side="left", expand=True)
        ttk.Button(nav, text="▶", width=3, command=lambda: self.prev_goto(1)).pack(side="right", padx=6)
        self.show_cover = tk.BooleanVar()
        ttk.Checkbutton(box, text="Ver a página de rosto deste arquivo", variable=self.show_cover,
                        command=self.schedule_preview).pack(anchor="w", padx=6, pady=2)
        self.prev_note = ttk.Label(box, text="", style="Muted.TLabel", wraplength=300)
        self.prev_note.pack(fill="x", padx=6, pady=(0, 4))
        ttk.Button(box, text="Abrir arquivo", command=self.open_selected).pack(fill="x", padx=6, pady=(0, 6))

    def toggle_preview(self):
        if self.preview_on:
            self.main.forget(self.mid)
        else:
            self.main.insert(1, self.mid, weight=0)
        self.preview_on = not self.preview_on
        self.schedule_preview()

    def schedule_preview(self, reset=True):
        if reset:
            self.prev_index = 0
        if self.prev_job:
            self.root.after_cancel(self.prev_job)
        self.prev_job = self.root.after(120, self.request_preview)

    def prev_goto(self, d):
        if self.prev_total:
            self.prev_index = max(0, min(self.prev_total - 1, self.prev_index + d))
            self.schedule_preview(reset=False)

    def request_preview(self):
        self.prev_job = None
        if not self.preview_on:
            return
        sel = self.selected()
        if not sel:
            self.prev_title.config(text="")
            self.prev_canvas.config(image="", text="Selecione um arquivo")
            self.prev_page.config(text="")
            self.prev_note.config(text="")
            return
        i = sel[0]
        it = self.q.items[i]
        self.prev_req += 1
        req, index, cover = self.prev_req, self.prev_index, self.show_cover.get()
        self.prev_title.config(text=it.path.name)
        slow = it.path.suffix.lower() in core.OFFICE
        self.prev_note.config(text="Convertendo o documento… (pode levar alguns segundos)" if slow else "")
        try:
            opts = self.options(validate=False)
        except Exception:
            opts = core.Options()
        total = max(1, sum(1 for x in self.q.items if x.enabled))
        pos = 1 + sum(1 for x in self.q.items[:i] if x.enabled)

        def work():
            try:
                mode = "pagina"
                if cover:
                    if not (opts.cover or opts.cover_text):
                        opts.cover = "filename-folder"
                    pdf = self.previewer.cover_pdf(opts, it.path, pos, total)
                    png, n = self.previewer.render_pdf(pdf, 0)
                    mode = "rosto"
                elif opts.per_sheet > 1:
                    pdf, _ = self.previewer.sheets_pdf(it.path, opts)
                    png, n = pv.render_pdf_page(pdf, index, (340, 480))
                    mode = "folha"
                else:
                    png, n = self.previewer.render(it.path, index)
                self.events.put(("preview", {"req": req, "png": png, "n": n, "index": index, "mode": mode,
                                             "per": opts.per_sheet, "logo": bool(opts.cover_logo)}))
            except Exception as e:
                self.events.put(("preview", {"req": req, "error": str(e)}))

        threading.Thread(target=work, daemon=True).start()

    def on_preview(self, d):
        if d["req"] != self.prev_req:
            return
        if d.get("error"):
            self.prev_canvas.config(image="", text="Sem pré-visualização")
            self.prev_note.config(text=d["error"])
            self.prev_page.config(text="")
            self.prev_total = 0
            return
        self.prev_img = tk.PhotoImage(data=base64.b64encode(d["png"]).decode())
        self.prev_canvas.config(image=self.prev_img, text="")
        mode = d.get("mode", "pagina")
        if mode == "rosto":
            note = "Página de rosto" + (" com logotipo" if d.get("logo") else "")
            self.prev_total, pos_txt = 1, "rosto"
        elif mode == "folha":
            note = f"Como sai na folha: {d['per']} páginas por folha" + (" · com linha entre elas" if self.sheet_border.get() else "")
            self.prev_total, pos_txt = d["n"], f"folha {d['index'] + 1} de {d['n']}"
        else:
            note, self.prev_total, pos_txt = "", d["n"], f"página {d['index'] + 1} de {d['n']}"
        self.prev_note.config(text=note)
        self.prev_page.config(text=pos_txt)

    # ================= plano de impressão =================
    def show_plan(self):
        try:
            opts = self.options()
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("PrintBatch", str(e))
            return
        steps = self.q.plan(opts)
        if not steps:
            messagebox.showinfo("PrintBatch", "Nenhum arquivo marcado na fila.")
            return
        win = tk.Toplevel(self.root)
        win.configure(background=self.pal["bg"])
        win.title("Plano de impressão — o que vai sair, na ordem")
        win.geometry("900x520")
        win.transient(self.root)
        cols = ("passo", "tipo", "desc", "pags", "cop", "folhas", "acum")
        t = ttk.Treeview(win, columns=cols, show="headings")
        for c, h, w, a in (("passo", "#", 44, "center"), ("tipo", "Tipo", 80, "w"), ("desc", "Descrição", 430, "w"),
                           ("pags", "Págs", 56, "center"), ("cop", "Cópias", 60, "center"),
                           ("folhas", "Folhas", 60, "center"), ("acum", "Acumulado", 80, "center")):
            t.heading(c, text=h)
            t.column(c, width=w, anchor=a)
        t.tag_configure("rosto", foreground=self.pal["muted"])
        t.tag_configure("separador", foreground=self.pal["accent"])
        for st in steps:
            t.insert("", "end", tags=(st["tipo"],), values=(
                st["passo"], st["tipo"], st["descrição"], "?" if st["páginas"] is None else st["páginas"],
                st["cópias"], "?" if st["folhas"] is None else st["folhas"], st["acumulado"]))
        t.pack(fill="both", expand=True, padx=8, pady=8)
        s = self.q.stats(opts)
        ttk.Label(win, text=f"{s['enabled']} arquivo(s) • {s['pages']} página(s) • ≈ {s['sheets']} folha(s) de papel"
                            + (f" • {s['unknown']} sem contagem de páginas" if s["unknown"] else "")).pack(anchor="w", padx=8)
        b = ttk.Frame(win)
        b.pack(fill="x", padx=8, pady=8)
        ttk.Button(b, text="Fechar", command=win.destroy).pack(side="right", padx=4)
        ttk.Button(b, text="Imprimir agora", command=lambda: (win.destroy(), self.start())).pack(side="right", padx=4)

    def choose_logo(self):
        p = filedialog.askopenfilename(title="Logotipo para a página de rosto",
                                       filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif"), ("Todos", "*.*")])
        if not p:
            return
        try:
            nup.load_logo(p)                      # confere agora se a imagem abre
        except Exception as e:
            messagebox.showerror("Logotipo", f"Não foi possível usar esta imagem:\n{e}")
            return
        self.cover_logo.set(p)
        self.update_summary()

    def toggle_cover(self):
        if COVER_NAMES[self.cover.get()] == "custom":
            self.cover_text.pack(fill="x", padx=4, pady=2, before=self.check_frame)
            self.cover_hint.pack(anchor="w", padx=4, before=self.check_frame)
        else:
            self.cover_text.pack_forget()
            self.cover_hint.pack_forget()

    # ================= lista =================
    def refresh(self, keep_selection=True):
        sel_items = [id(self.q.items[i]) for i in self.selected()] if keep_selection else []
        self.visible = self.q.search(self.search.get())
        self.tree.delete(*self.tree.get_children())
        for pos, i in enumerate(self.visible):
            it = self.q.items[i]
            try:
                size = fmt_size(it.path.stat().st_size)
            except OSError:
                size = "—"
            pg = self.q.pages(it)
            tags = ["odd" if pos % 2 else "even"]
            if not it.enabled:
                tags.append("off")
            issue = self.issues.get(str(it.path))
            if issue:
                tags.append(issue[0])
            state = self.status.get(str(it.path), "")
            if state.startswith("✔"):
                tags.append("ok")
            elif state.startswith("✘"):
                tags.append("erro")
            self.tree.insert("", "end", iid=str(i), tags=tags, values=(
                "☑" if it.enabled else "☐", i + 1, it.path.name, it.path.suffix.lstrip(".").upper(),
                "?" if pg is None else pg, f"{it.copies}*" if it.copies else "",
                {"off": "não*", "long": "longa*", "short": "curta*"}.get(it.duplex, ""),
                it.pages or "", size, str(it.path.parent), state or (issue[1] if issue else ""), it.note))
        keep = [str(i) for i in self.visible if id(self.q.items[i]) in sel_items]
        if keep:
            self.tree.selection_set(keep)
        if len(self.q):
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.45, anchor="center")
            self.empty.lift()
        self.update_summary()
        self.show_details()

    def selected(self):
        return sorted(int(i) for i in self.tree.selection() if i.isdigit())

    def update_summary(self):
        try:
            opts = self.options(validate=False)
        except Exception:
            opts = core.Options()
        s = self.q.stats(opts)
        extra = f"  (+{s['unknown']} sem contagem)" if s["unknown"] else ""
        shown = f"  •  exibindo {len(self.visible)}" if len(self.visible) != len(self.q) else ""
        self.summary.config(text=f"{s['enabled']}/{s['total']} marcados  •  {s['pages']} págs  •  ≈ {s['sheets']} folhas{extra}{shown}")

    def show_details(self):
        sel = self.selected()
        if len(sel) == 1:
            it = self.q.items[sel[0]]
            pg = self.q.pages(it)
            try:
                import datetime
                mt = datetime.datetime.fromtimestamp(it.path.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
            except OSError:
                mt = "—"
            issue = self.issues.get(str(it.path))
            self.details.config(text=f"{it.path}   •   {pg if pg is not None else '?'} pág.   •   modificado {mt}"
                                     + (f"   •   ⚠ {issue[1]}" if issue else ""))
        elif sel:
            self.details.config(text=f"{len(sel)} selecionados")
        else:
            self.details.config(text="Dica: ☑ marca/desmarca  •  arraste para reordenar  •  duplo clique: ajustes  •  F1: atalhos")

    # ================= ações da fila =================
    def add_paths(self, paths):
        added = self.q.add_paths(paths, self.recursive.get(), None, SORT_LABELS[self.sort.get()] if self.sort.get() != "Nº de páginas" else "natural", self.log)
        self.log(f"{len(added)} arquivo(s) adicionado(s)")
        self.refresh()

    def add_files(self):
        exts = " ".join("*" + e for e in sorted(core.SUPPORTED))
        paths = filedialog.askopenfilenames(title="Escolha os arquivos", filetypes=[("Documentos suportados", exts), ("Todos", "*.*")])
        if paths:
            self.add_paths(paths)

    def add_folder(self):
        d = filedialog.askdirectory(title="Escolha a pasta")
        if d:
            self.add_paths([d])

    def remove(self):
        self.q.remove(self.selected())
        self.refresh(False)

    def clear(self):
        if len(self.q) and messagebox.askyesno("PrintBatch", "Limpar toda a fila? (dá para desfazer)"):
            self.q.clear()
            self.status, self.issues = {}, {}
            self.refresh(False)

    def move(self, d):
        sel = self.selected()
        new = self.q.move(sel, d)
        self.refresh(False)
        self.tree.selection_set([str(i) for i in new if str(i) in self.tree.get_children()])

    def undo(self):
        if self.q.undo():
            self.refresh(False)
        return "break"

    def redo(self):
        if self.q.redo():
            self.refresh(False)
        return "break"

    def apply_sort(self, key=None):
        key = key or SORT_LABELS[self.sort.get()]
        self.q.sort(key, self.reverse.get())
        self.refresh()

    def apply_filter(self):
        pats = [p.strip() for p in self.filter.get().replace(";", ",").split(",") if p.strip()]
        if pats:
            self.q.keep_matching(pats)
            self.refresh(False)

    def remove_duplicates(self):
        removed = self.q.remove_duplicates()
        self.log(f"{len(removed)} duplicado(s) removido(s)" + (": " + ", ".join(r.path.name for r in removed[:5]) if removed else ""))
        self.refresh(False)

    def set_enabled(self, value, all_rows=False):
        idx = list(range(len(self.q))) if all_rows else self.selected()
        self.q.toggle(idx, value)
        self.refresh()

    def toggle_selected(self):
        sel = self.selected()
        if sel:
            self.q.toggle(sel, not self.q.items[sel[0]].enabled)
            self.refresh()
        return "break"

    def duplicate_selected(self):
        sel = self.selected()
        if sel:
            self.q.snapshot()
            for i in reversed(sel):
                src = self.q.items[i]
                self.q.items.insert(i + 1, core.Item(src.path, src.enabled, src.copies, src.pages, src.duplex, src.color, src.note))
            self.refresh(False)

    def edit_selected(self):
        sel = self.selected()
        if sel:
            ItemDialog(self, sel)

    def open_selected(self):
        for i in self.selected()[:3]:
            open_path(self.q.items[i].path)

    def reveal_selected(self):
        sel = self.selected()
        if sel:
            reveal(self.q.items[sel[0]].path)

    def popup(self, e):
        row = self.tree.identify_row(e.y)
        if row and row not in self.tree.selection():
            self.tree.selection_set(row)
        if self.tree.selection():
            self.menu.tk_popup(e.x_root, e.y_root)

    # ----- arrastar para reordenar / clicar na caixa -----
    def on_press(self, e):
        if self.tree.identify_region(e.x, e.y) != "cell":
            self.drag = None
            return
        row = self.tree.identify_row(e.y)
        if row and self.tree.identify_column(e.x) == "#1":
            self.q.toggle([int(row)])
            self.refresh()
            self.drag = None
            return "break"
        self.drag = (row, e.y) if row else None

    def on_motion(self, e):
        if self.drag:
            self.tree.configure(cursor="fleur")

    def on_release(self, e):
        self.tree.configure(cursor="")
        if not self.drag:
            return
        row0, y0 = self.drag
        self.drag = None
        target = self.tree.identify_row(e.y)
        if not target or abs(e.y - y0) < 6 or target == row0 or len(self.visible) != len(self.q):
            return
        sel = self.selected() or [int(row0)]
        pos = int(target)
        if e.y > self.tree.bbox(target)[1] + self.tree.bbox(target)[3] / 2:
            pos += 1
        new = self.q.move_to(sel, pos)
        self.refresh(False)
        self.tree.selection_set([str(i) for i in new])

    # ================= verificação =================
    def verify(self):
        if not len(self.q):
            return
        issues = self.q.check()
        self.issues = {}
        for i in issues:
            old = self.issues.get(str(i.path))
            if not old or i.level == "erro":
                self.issues[str(i.path)] = (i.level, i.message)
        self.refresh()
        if not issues:
            messagebox.showinfo("Verificar fila", f"Nenhum problema encontrado em {len(self.q)} arquivo(s). ✔")
            return
        errs = sum(i.level == "erro" for i in issues)
        win = tk.Toplevel(self.root)
        win.configure(background=self.pal["bg"])
        win.title(f"Verificação: {errs} erro(s), {len(issues) - errs} aviso(s)")
        win.geometry("940x420")
        win.transient(self.root)
        t = ttk.Treeview(win, columns=("n", "arq", "msg"), show="headings")
        for c, h, w in (("n", "Nível", 60), ("arq", "Arquivo", 220), ("msg", "Problema", 620)):
            t.heading(c, text=h)
            t.column(c, width=w, anchor="w")
        for i in issues:
            t.insert("", "end", values=(i.level, i.path.name, i.message), tags=(i.level,))
        t.tag_configure("erro", foreground=self.pal["error"])
        t.tag_configure("aviso", foreground=self.pal["warn"])
        t.pack(fill="both", expand=True, padx=8, pady=8)
        b = ttk.Frame(win)
        b.pack(fill="x", padx=8, pady=(0, 8))

        def drop(levels):
            bad = {str(i.path) for i in issues if i.level in levels}
            self.q.remove([k for k, it in enumerate(self.q.items) if str(it.path) in bad])
            self.issues = {k: v for k, v in self.issues.items() if k not in bad}
            self.refresh(False)
            win.destroy()

        def uncheck():
            bad = {str(i.path) for i in issues}
            self.q.toggle([k for k, it in enumerate(self.q.items) if str(it.path) in bad], False)
            self.refresh()
            win.destroy()

        ttk.Button(b, text="Remover os com erro", command=lambda: drop({"erro"})).pack(side="left", padx=4)
        ttk.Button(b, text="Desmarcar todos com problema", command=uncheck).pack(side="left", padx=4)
        ttk.Button(b, text="Fechar", command=win.destroy).pack(side="right", padx=4)

    # ================= perfis / config =================
    def load_printers(self):
        names, default = self.backend.list_printers()
        self.printer_cb["values"] = names
        if not self.printer.get() or self.printer.get() not in names:
            self.printer.set(default or (names[0] if names else ""))

    def get_state(self):
        return {"printer": self.printer.get(), "copies": self.copies.get(), "set_copies": self.set_copies.get(), "retries": self.retries.get(),
                "duplex": self.duplex.get(), "color": self.color.get(), "paper": self.paper.get(),
                "landscape": self.landscape.get(), "fit": self.fit.get(), "cover": self.cover.get(),
                "divider": self.divider.get(), "failed": self.failed.get(), "attach": self.attach.get(),
                "cover_text": self.cover_text.get("1.0", "end").strip(),
                "per_sheet": self.per_sheet.get(), "sheet_border": self.sheet_border.get(),
                "cover_logo": self.cover_logo.get()}

    def set_state(self, c, with_printer=True):
        if with_printer and c.get("printer") in (self.printer_cb["values"] or ()):
            self.printer.set(c["printer"])
        self.copies.set(c.get("copies", 1))
        self.set_copies.set(c.get("set_copies", 1))
        self.retries.set(c.get("retries", 1))
        self.duplex.set(c.get("duplex", "Desligado") if c.get("duplex") in DUPLEX else "Desligado")
        self.color.set(c.get("color", "Padrão da impressora") if c.get("color") in COLOR else "Padrão da impressora")
        self.paper.set(c.get("paper", ""))
        self.landscape.set(c.get("landscape", False))
        self.fit.set(c.get("fit", False))
        self.cover.set(c.get("cover", "Sem página de rosto") if c.get("cover") in COVER_NAMES else "Sem página de rosto")
        self.divider.set(c.get("divider", False))
        self.failed.set(c.get("failed", True))
        self.attach.set(c.get("attach", False))
        if c.get("cover_text"):
            self.cover_text.delete("1.0", "end")
            self.cover_text.insert("1.0", c["cover_text"])
        self.per_sheet.set(c.get("per_sheet") if c.get("per_sheet") in PER_SHEET else "1 página (normal)")
        self.sheet_border.set(c.get("sheet_border", True))
        self.cover_logo.set(c.get("cover_logo", "") if Path(c.get("cover_logo", "") or "x").is_file() else "")
        self.toggle_cover()

    def refresh_presets(self):
        self.preset_cb["values"] = sorted(self.cfg.get("presets", {}))

    def save_preset(self):
        name = self.preset.get().strip()
        if not name:
            messagebox.showinfo("Perfis", "Digite um nome para o perfil na caixa acima.")
            return
        self.cfg.setdefault("presets", {})[name] = self.get_state()
        core.save_config(self.cfg)
        self.refresh_presets()
        self.log(f"Perfil “{name}” salvo")

    def load_preset(self):
        st = self.cfg.get("presets", {}).get(self.preset.get())
        if st:
            self.set_state(st, with_printer=True)
            self.update_summary()

    def delete_preset(self):
        if self.cfg.get("presets", {}).pop(self.preset.get(), None) is not None:
            core.save_config(self.cfg)
            self.preset.set("")
            self.refresh_presets()

    def options(self, validate=True):
        cv = COVER_NAMES[self.cover.get()]
        text = self.cover_text.get("1.0", "end").strip() if cv == "custom" else None

        def num(var, default=1, low=1, high=9999):
            try:
                return min(high, max(low, int(var.get())))
            except (tk.TclError, ValueError):
                return default

        o = core.Options(
            printer=self.printer.get() or None, copies=num(self.copies), set_copies=num(self.set_copies),
            duplex=DUPLEX[self.duplex.get()], pages=self.pages.get().strip() or None,
            paper=self.paper.get().strip() or None, landscape=self.landscape.get(), fit=self.fit.get(),
            color=COLOR[self.color.get()], cover=None if cv == "custom" else cv, cover_text=text,
            failed_page=self.failed.get(), attachments=self.attach.get(), dry_run=self.dry.get(),
            folder_divider=self.divider.get(), retries=num(self.retries, 1, 0, 10),
            per_sheet=PER_SHEET.get(self.per_sheet.get(), 1), sheet_border=self.sheet_border.get(),
            cover_logo=self.cover_logo.get().strip() or None)
        if validate:
            o.validate()
        return o

    # ================= execução =================
    def start(self, test=False, only=None):
        enabled = [it for it in self.q.items if it.enabled] if only is None else list(only)
        if not enabled:
            messagebox.showinfo("PrintBatch", "Nenhum arquivo marcado na fila.")
            return "break"
        try:
            opts = self.options()
            fileinfo.count_range(opts.pages, None)
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("PrintBatch", str(e))
            return "break"
        src = self.q.items if only is None else only
        items = [core.Item(i.path, i.enabled, i.copies, i.pages, i.duplex, i.color, i.note) for i in src]
        if test:
            items, opts = core.as_test_job(items, opts)
        tq = PrintQueue()
        tq.items = items
        s = tq.stats(opts)
        what = "IMPRESSÃO DE TESTE (só a 1ª página de cada)\n" if test else ""
        if only is None and not opts.dry_run and not messagebox.askyesno(
                "Confirmar impressão",
                f"{what}Imprimir {s['enabled']} arquivo(s) — {s['pages']} página(s), ≈ {s['sheets']} folha(s) —\n"
                f"em “{opts.printer or 'impressora padrão'}”?"):
            return "break"
        self.cfg.update(self.get_state())
        core.save_config(self.cfg)
        self.status = {}
        self.refresh()
        self.cancel.clear()
        self.progress.config(maximum=s["enabled"] * opts.set_copies, value=0)
        self.t0, self.done_n, self.total_n = time.time(), 0, s["enabled"] * opts.set_copies
        self.prog_label.config(text=f"0/{self.total_n} — iniciando…")
        self.btn_print.config(state="disabled")
        self.btn_cancel.config(state="normal")
        backend = get_backend(opts.dry_run, log=lambda *a: self.events.put(("log", " ".join(map(str, a)))))

        def work():
            try:
                self.rows = core.run_job(items, opts, backend, lambda kind, **k: self.events.put((kind, k)), self.cancel)
                if not opts.dry_run:
                    core.append_history(self.rows, opts.printer)
            except Exception as e:
                self.events.put(("fatal", str(e)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()
        return "break"

    def poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "log":
                    self.log(data)
                elif kind == "preview":
                    self.on_preview(data)
                elif kind == "retry":
                    self.mark(data["file"], f"tentando de novo ({data['attempt']})…")
                    self.log(f"Falhou ao enviar {Path(data['file']).name}: {data['error']} — nova tentativa")
                elif kind == "start":
                    self.mark(data["file"], "imprimindo…")
                    self.update_progress(Path(data["file"]).name)
                elif kind == "ok":
                    self.mark(data["file"], "✔ ok")
                    self.progress.step(1)
                    self.done_n += 1
                    self.update_progress()
                elif kind == "error":
                    self.mark(data["file"], "✘ falhou")
                    self.log(f"FALHOU {Path(data['file']).name}: {data['error']}")
                    self.progress.step(1)
                    self.done_n += 1
                    self.update_progress()
                elif kind == "cancelled":
                    self.log("Cancelado.")
                elif kind == "done":
                    self.log(f"Concluído: {data['ok']} ok, {data['fail']} falha(s) de {data['total']}.")
                    self.finish()
                elif kind == "fatal":
                    self.log("ERRO: " + data)
                    self.finish()
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def mark(self, f, text):
        self.status[str(f)] = text
        for i in self.visible:
            if str(self.q.items[i].path) == str(f) and self.tree.exists(str(i)):
                self.tree.set(str(i), "estado", text)
                self.tree.item(str(i), tags=[t for t in self.tree.item(str(i), "tags") if t not in ("ok", "erro")]
                               + (["ok"] if text.startswith("✔") else ["erro"] if text.startswith("✘") else []))
                self.tree.see(str(i))
                break

    @staticmethod
    def fmt_time(sec):
        sec = int(max(0, sec))
        return f"{sec // 60:02d}:{sec % 60:02d}"

    def update_progress(self, current=None):
        done, total = getattr(self, "done_n", 0), getattr(self, "total_n", 0)
        if not total:
            return
        el = time.time() - self.t0
        eta = (el / done * (total - done)) if done else None
        txt = f"{done}/{total} ({100 * done // total}%) · decorrido {self.fmt_time(el)}"
        if eta is not None and done < total:
            txt += f" · restam ≈ {self.fmt_time(eta)}"
        if current:
            txt += f" · {current}"
        self.prog_label.config(text=txt)

    def finish(self):
        if getattr(self, "total_n", 0):
            self.prog_label.config(text=f"Concluído em {self.fmt_time(time.time() - self.t0)} — "
                                        f"{self.done_n} de {self.total_n} arquivo(s) processado(s)")
        self.btn_print.config(state="normal")
        self.btn_cancel.config(state="disabled")

    # ================= projeto / relatório =================
    def open_project_dialog(self):
        p = filedialog.askopenfilename(filetypes=[("Projeto PrintBatch", "*.pbq"), ("JSON", "*.json")])
        if p:
            self.open_project(p)

    def open_project(self, path):
        try:
            q, opts = PrintQueue.load(path)
        except Exception as e:
            messagebox.showerror("PrintBatch", f"Não foi possível abrir o projeto:\n{e}")
            return
        self.q = q
        self.status, self.issues = {}, {}
        if opts:
            st = self.get_state()
            self.copies.set(opts.copies)
            self.set_copies.set(opts.set_copies)
            self.paper.set(opts.paper or "")
            self.pages.set(opts.pages or "")
            self.landscape.set(opts.landscape)
            self.fit.set(opts.fit)
            self.duplex.set(next((k for k, v in DUPLEX.items() if v == opts.duplex), st["duplex"]))
            self.color.set(next((k for k, v in COLOR.items() if v == opts.color), st["color"]))
            self.divider.set(opts.folder_divider)
            self.failed.set(opts.failed_page)
            self.attach.set(opts.attachments)
            cv = opts.cover or ("custom" if opts.cover_text else None)
            self.cover.set(next((k for k, v in COVER_NAMES.items() if v == cv), "Sem página de rosto"))
            if opts.cover_text:
                self.cover_text.delete("1.0", "end")
                self.cover_text.insert("1.0", opts.cover_text)
            self.toggle_cover()
        self.log(f"Projeto aberto: {path} ({len(q)} arquivo(s))")
        self.refresh(False)

    def save_project(self):
        p = filedialog.asksaveasfilename(defaultextension=".pbq", filetypes=[("Projeto PrintBatch", "*.pbq")])
        if p:
            self.q.save(p, self.options(validate=False))
            self.log("Projeto salvo em " + p)

    def save_report(self):
        if not self.rows:
            messagebox.showinfo("PrintBatch", "Ainda não há relatório; imprima primeiro.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("JSON", "*.json")])
        if p:
            core.write_report(p, self.rows)
            self.log("Relatório salvo em " + p)

    def log(self, msg):
        self.logbox.config(state="normal")
        self.logbox.insert("end", msg + "\n")
        self.logbox.see("end")
        self.logbox.config(state="disabled")

    def on_close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("PrintBatch", "Há uma impressão em andamento. Sair mesmo assim?"):
                return
            self.cancel.set()
        self.cfg.update(self.get_state())
        try:
            self.cfg["geometry"] = self.root.winfo_geometry()
            self.cfg["col_widths"] = {c: int(self.tree.column(c, "width")) for c in COLS}
        except tk.TclError:
            pass
        core.save_config(self.cfg)
        self.autosave()
        if self.watcher:
            self.stop_watch()
        self.root.destroy()


def run_gui(initial=(), project=None):
    theme.enable_hidpi()
    root = _Root()
    App(root, list(initial), project)
    root.mainloop()
    return 0
