"""Interface gráfica (tkinter) com fila organizável."""
import base64
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__, core, fileinfo, preview as pv
from .backends import get_backend
from .jobqueue import PrintQueue

try:  # arrastar e soltar arquivos do Explorer (opcional: pip install tkinterdnd2)
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _Root = TkinterDnD.Tk
except Exception:  # pragma: no cover
    DND_FILES, _Root = None, tk.Tk

DUPLEX = {"Desligado": None, "Borda longa": "long", "Borda curta": "short"}
COLOR = {"Padrão da impressora": None, "Colorido": True, "Preto e branco": False}
COVER_NAMES = {"Sem página de rosto": None, "Nome do arquivo": "filename", "Nome + pasta": "filename-folder",
               "Completa": "full", "Número na fila": "number", "Personalizada…": "custom"}
ITEM_DUPLEX = {"(padrão)": None, "Desligado": "off", "Borda longa": "long", "Borda curta": "short"}
ITEM_COLOR = {"(padrão)": None, "Colorido": "color", "Preto e branco": "mono"}
SORT_LABELS = {"Natural (doc2 < doc10)": "natural", "Nome": "name", "Data": "date", "Tamanho": "size",
               "Tipo": "type", "Pasta": "folder", "Nº de páginas": "pages"}
PAPERS = ["", "A4", "A3", "A5", "Letter", "Legal"]
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


class ItemDialog(tk.Toplevel):
    """Ajustes que valem só para os itens selecionados."""

    def __init__(self, app, indices):
        super().__init__(app.root)
        self.app, self.indices = app, indices
        self.title(f"Ajustes de {len(indices)} arquivo(s)")
        self.transient(app.root)
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
        root.geometry(f"{min(1600, sw - 40) if sw >= 1500 else min(1280, sw - 40)}x{min(820, sh - 60)}")
        root.minsize(1000, 600)
        self.q = PrintQueue()
        self.status, self.issues = {}, {}
        self.visible = []
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker, self.rows = None, []
        self.cfg = core.load_config()
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
        root.after(100, self.poll)

    # ================= construção =================
    def build(self):
        pad = dict(padx=4, pady=2)
        main = ttk.PanedWindow(self.root, orient="horizontal")
        main.pack(fill="both", expand=True, padx=6, pady=6)
        left, right = ttk.Frame(main), ttk.Frame(main, width=350)
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
            ttk.Button(bar, text=text, command=cmd).pack(side="left", **pad)
        self.recursive = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="subpastas", variable=self.recursive).pack(side="left", **pad)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(bar, text="👁 Pré-visualização", command=self.toggle_preview).pack(side="left", **pad)
        bar1b = ttk.Frame(left)
        bar1b.pack(fill="x")
        for text, cmd in (("Remover", self.remove), ("Limpar", self.clear), ("▲", lambda: self.move(-1)), ("▼", lambda: self.move(1)),
                          ("↶ Desfazer", self.undo), ("↷ Refazer", self.redo)):
            ttk.Button(bar1b, text=text, command=cmd, width=3 if len(text) == 1 else None).pack(side="left", **pad)

        # --- barra 2: organizar ---
        bar2 = ttk.LabelFrame(left, text="Organizar")
        bar2.pack(fill="x", pady=3)
        bar2a = ttk.Frame(bar2)
        bar2a.pack(fill="x")
        ttk.Label(bar2a, text="Ordenar por").pack(side="left", **pad)
        self.sort = tk.StringVar(value="Natural (doc2 < doc10)")
        ttk.Combobox(bar2a, textvariable=self.sort, values=list(SORT_LABELS), width=20, state="readonly").pack(side="left")
        self.reverse = tk.BooleanVar()
        ttk.Checkbutton(bar2a, text="inverter", variable=self.reverse).pack(side="left", **pad)
        ttk.Button(bar2a, text="Aplicar", command=self.apply_sort).pack(side="left", **pad)
        ttk.Button(bar2a, text="Agrupar por pasta", command=lambda: self.apply_sort("folder")).pack(side="left", **pad)
        ttk.Button(bar2a, text="Agrupar por tipo", command=lambda: self.apply_sort("type")).pack(side="left", **pad)
        bar2b = ttk.Frame(bar2)
        bar2b.pack(fill="x")
        ttk.Button(bar2b, text="Remover duplicados", command=self.remove_duplicates).pack(side="left", **pad)
        ttk.Button(bar2b, text="Remover desmarcados", command=lambda: (self.q.remove_disabled(), self.refresh())).pack(side="left", **pad)
        ttk.Button(bar2b, text="✓ Verificar fila", command=self.verify).pack(side="left", **pad)
        ttk.Separator(bar2b, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(bar2b, text="Marcar todos", command=lambda: self.set_enabled(True, all_rows=True)).pack(side="left", **pad)
        ttk.Button(bar2b, text="Desmarcar todos", command=lambda: self.set_enabled(False, all_rows=True)).pack(side="left", **pad)
        ttk.Button(bar2b, text="Ajustes…", command=self.edit_selected).pack(side="left", **pad)

        # --- barra 3: busca / filtro / seleção ---
        bar3 = ttk.Frame(left)
        bar3.pack(fill="x")
        ttk.Label(bar3, text="Buscar").pack(side="left", **pad)
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *a: self.refresh())
        ttk.Entry(bar3, textvariable=self.search, width=22).pack(side="left")
        ttk.Button(bar3, text="✕", width=2, command=lambda: self.search.set("")).pack(side="left", **pad)
        ttk.Label(bar3, text="Manter só (padrões)").pack(side="left", padx=(14, 2))
        self.filter = tk.StringVar()
        ttk.Entry(bar3, textvariable=self.filter, width=18).pack(side="left")
        ttk.Button(bar3, text="Aplicar", command=self.apply_filter).pack(side="left", **pad)

        # --- lista ---
        frame = ttk.Frame(left)
        frame.pack(fill="both", expand=True, pady=4)
        self.tree = ttk.Treeview(frame, columns=COLS, show="headings", selectmode="extended")
        for c in COLS:
            self.tree.heading(c, text=HEAD[c])
            self.tree.column(c, width=WIDTH[c], anchor="center" if c in ("on", "n", "tipo", "pags", "copias", "fv", "sel") else "w",
                             stretch=c in ("nome", "pasta", "nota"))
        ys = ttk.Scrollbar(frame, command=self.tree.yview)
        xs = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.tree.tag_configure("off", foreground="#9a9a9a")
        self.tree.tag_configure("erro", foreground="#c0392b")
        self.tree.tag_configure("aviso", foreground="#b9770e")
        self.tree.tag_configure("ok", foreground="#1e8449")
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
        for label, cmd in (("Abrir arquivo", self.open_selected), ("Mostrar na pasta", self.reveal_selected),
                           (None, None), ("Marcar/desmarcar", self.toggle_selected), ("Ajustes do arquivo…", self.edit_selected),
                           ("Duplicar na fila (reimprimir)", self.duplicate_selected), (None, None), ("Remover da fila", self.remove)):
            self.menu.add_separator() if label is None else self.menu.add_command(label=label, command=cmd)

        # --- resumo / detalhes / progresso / log ---
        self.summary = ttk.Label(left, text="", font=("TkDefaultFont", 10, "bold"))
        self.summary.pack(anchor="w")
        self.details = ttk.Label(left, text="", foreground="gray")
        self.details.pack(anchor="w")
        self.progress = ttk.Progressbar(left, mode="determinate")
        self.progress.pack(fill="x", pady=2)
        self.logbox = tk.Text(left, height=7, state="disabled", wrap="word")
        self.logbox.pack(fill="x", pady=3)

        # ================= painel direito =================
        pr = ttk.LabelFrame(right, text="Perfis")
        pr.pack(fill="x", **pad)
        self.preset = tk.StringVar()
        self.preset_cb = ttk.Combobox(pr, textvariable=self.preset, width=24)
        self.preset_cb.grid(row=0, column=0, columnspan=3, sticky="we", **pad)
        self.preset_cb.bind("<<ComboboxSelected>>", lambda e: self.load_preset())
        ttk.Button(pr, text="Salvar perfil", command=self.save_preset).grid(row=1, column=0, **pad)
        ttk.Button(pr, text="Excluir", command=self.delete_preset).grid(row=1, column=1, **pad)

        box = ttk.LabelFrame(right, text="Impressão")
        box.pack(fill="x", **pad)
        ttk.Label(box, text="Impressora").grid(row=0, column=0, sticky="w", **pad)
        self.printer = tk.StringVar()
        self.printer_cb = ttk.Combobox(box, textvariable=self.printer, state="readonly", width=24)
        self.printer_cb.grid(row=1, column=0, columnspan=2, sticky="we", **pad)
        ttk.Button(box, text="↻", width=3, command=self.load_printers).grid(row=1, column=2, **pad)
        self.copies = tk.IntVar(value=1)
        self.set_copies = tk.IntVar(value=1)
        self.duplex = tk.StringVar(value="Desligado")
        self.color = tk.StringVar(value="Padrão da impressora")
        self.paper = tk.StringVar()
        self.pages = tk.StringVar()
        self.landscape, self.fit = tk.BooleanVar(), tk.BooleanVar()
        grid = (("Cópias de cada arquivo", ttk.Spinbox(box, from_=1, to=999, textvariable=self.copies, width=6)),
                ("Repetir a fila inteira", ttk.Spinbox(box, from_=1, to=99, textvariable=self.set_copies, width=6)),
                ("Frente e verso", ttk.Combobox(box, textvariable=self.duplex, values=list(DUPLEX), state="readonly", width=14)),
                ("Cor", ttk.Combobox(box, textvariable=self.color, values=list(COLOR), state="readonly", width=18)),
                ("Papel", ttk.Combobox(box, textvariable=self.paper, values=PAPERS, width=8)),
                ("Páginas (todos)", ttk.Entry(box, textvariable=self.pages, width=12)))
        for r, (label, w) in enumerate(grid, start=2):
            ttk.Label(box, text=label).grid(row=r, column=0, sticky="w", **pad)
            w.grid(row=r, column=1, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(box, text="Paisagem", variable=self.landscape).grid(row=8, column=0, sticky="w", **pad)
        ttk.Checkbutton(box, text="Ajustar à página", variable=self.fit).grid(row=8, column=1, columnspan=2, sticky="w", **pad)

        ext = ttk.LabelFrame(right, text="Separadores e extras")
        ext.pack(fill="x", **pad)
        self.cover = tk.StringVar(value="Sem página de rosto")
        ttk.Label(ext, text="Página de rosto (antes de cada arquivo)").pack(anchor="w", **pad)
        cb = ttk.Combobox(ext, textvariable=self.cover, values=list(COVER_NAMES), state="readonly")
        cb.pack(fill="x", **pad)
        cb.bind("<<ComboboxSelected>>", lambda e: (self.toggle_cover(), self.update_summary()))
        self.cover_text = tk.Text(ext, height=4, width=30)
        self.cover_text.insert("1.0", "{name}\nPasta: {folder}\nArquivo {index} de {total}")
        self.cover_hint = ttk.Label(ext, text="Campos: {name} {folder} {folder_path} {ext} {index} {total} {date}",
                                    foreground="gray", wraplength=290)
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
            ttk.Checkbutton(self.check_frame, text=text, variable=var).pack(anchor="w", **pad)
        for v in (self.copies, self.set_copies, self.duplex, self.pages, self.divider):
            v.trace_add("write", lambda *a: self.update_summary())

        act = ttk.Frame(right)
        act.pack(fill="x", **pad)
        self.btn_print = ttk.Button(act, text="🖨  Imprimir marcados  (Ctrl+P)", command=self.start)
        self.btn_print.pack(fill="x", **pad)
        ttk.Button(act, text="Ver plano de impressão…", command=self.show_plan).pack(fill="x", **pad)
        ttk.Button(act, text="Imprimir teste (1ª página de cada)", command=lambda: self.start(test=True)).pack(fill="x", **pad)
        self.btn_cancel = ttk.Button(act, text="Cancelar", command=self.cancel.set, state="disabled")
        self.btn_cancel.pack(fill="x", **pad)
        for text, cmd in (("Abrir projeto…", self.open_project_dialog), ("Salvar projeto…", self.save_project),
                          ("Salvar relatório…", self.save_report)):
            ttk.Button(act, text=text, command=cmd).pack(fill="x", **pad)
        self.toggle_cover()

    # ================= pré-visualização =================
    def build_preview(self, f):
        self.previewer = pv.Previewer()
        self.prev_req, self.prev_index, self.prev_total, self.prev_job = 0, 0, 0, None
        self.prev_img = None
        box = ttk.LabelFrame(f, text="Pré-visualização")
        box.pack(fill="both", expand=True, padx=4, pady=2)
        self.prev_title = ttk.Label(box, text="", font=("TkDefaultFont", 9, "bold"), wraplength=300)
        self.prev_title.pack(fill="x", padx=6, pady=(4, 0))
        self.prev_canvas = tk.Label(box, text="Selecione um arquivo", background="#e8e8e8", anchor="center",
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
        self.prev_note = ttk.Label(box, text="", foreground="gray", wraplength=300)
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
                if cover:
                    if not (opts.cover or opts.cover_text):
                        opts.cover = "filename-folder"
                    pdf = self.previewer.cover_pdf(opts, it.path, pos, total)
                    png, n = self.previewer.render_pdf(pdf, 0)
                else:
                    png, n = self.previewer.render(it.path, index)
                self.events.put(("preview", {"req": req, "png": png, "n": n, "index": index, "cover": cover}))
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
        self.prev_note.config(text="Página de rosto (modelo atual)" if d["cover"] else "")
        self.prev_total = 1 if d["cover"] else d["n"]
        self.prev_page.config(text="rosto" if d["cover"] else f"página {d['index'] + 1} de {d['n']}")

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
        t.tag_configure("rosto", foreground="#7f8c8d")
        t.tag_configure("separador", foreground="#2874a6")
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
            sel_pages = self.q.pages_for_print(it)
            tags = []
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
        extra = f" (+{s['unknown']} sem contagem de páginas)" if s["unknown"] else ""
        shown = f" — exibindo {len(self.visible)}" if len(self.visible) != len(self.q) else ""
        self.summary.config(text=f"{s['enabled']} de {s['total']} arquivo(s) marcados — {s['pages']} página(s) — "
                                 f"≈ {s['sheets']} folha(s) de papel{extra}{shown}")

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
            self.details.config(text="Dica: clique em ☑ para marcar/desmarcar, arraste para reordenar, "
                                     "duplo clique para ajustes do arquivo, botão direito para mais opções.")

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
        win.title(f"Verificação: {errs} erro(s), {len(issues) - errs} aviso(s)")
        win.geometry("760x420")
        win.transient(self.root)
        t = ttk.Treeview(win, columns=("n", "arq", "msg"), show="headings")
        for c, h, w in (("n", "Nível", 60), ("arq", "Arquivo", 220), ("msg", "Problema", 440)):
            t.heading(c, text=h)
            t.column(c, width=w, anchor="w")
        for i in issues:
            t.insert("", "end", values=(i.level, i.path.name, i.message), tags=(i.level,))
        t.tag_configure("erro", foreground="#c0392b")
        t.tag_configure("aviso", foreground="#b9770e")
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
        return {"printer": self.printer.get(), "copies": self.copies.get(), "set_copies": self.set_copies.get(),
                "duplex": self.duplex.get(), "color": self.color.get(), "paper": self.paper.get(),
                "landscape": self.landscape.get(), "fit": self.fit.get(), "cover": self.cover.get(),
                "divider": self.divider.get(), "failed": self.failed.get(), "attach": self.attach.get(),
                "cover_text": self.cover_text.get("1.0", "end").strip()}

    def set_state(self, c, with_printer=True):
        if with_printer and c.get("printer") in (self.printer_cb["values"] or ()):
            self.printer.set(c["printer"])
        self.copies.set(c.get("copies", 1))
        self.set_copies.set(c.get("set_copies", 1))
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

        def num(var, default=1):
            try:
                return max(1, int(var.get()))
            except (tk.TclError, ValueError):
                return default

        o = core.Options(
            printer=self.printer.get() or None, copies=num(self.copies), set_copies=num(self.set_copies),
            duplex=DUPLEX[self.duplex.get()], pages=self.pages.get().strip() or None,
            paper=self.paper.get().strip() or None, landscape=self.landscape.get(), fit=self.fit.get(),
            color=COLOR[self.color.get()], cover=None if cv == "custom" else cv, cover_text=text,
            failed_page=self.failed.get(), attachments=self.attach.get(), dry_run=self.dry.get(),
            folder_divider=self.divider.get())
        if validate:
            o.validate()
        return o

    # ================= execução =================
    def start(self, test=False):
        enabled = [it for it in self.q.items if it.enabled]
        if not enabled:
            messagebox.showinfo("PrintBatch", "Nenhum arquivo marcado na fila.")
            return "break"
        try:
            opts = self.options()
            fileinfo.count_range(opts.pages, None)
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("PrintBatch", str(e))
            return "break"
        items = [core.Item(i.path, i.enabled, i.copies, i.pages, i.duplex, i.color, i.note) for i in self.q.items]
        if test:
            items, opts = core.as_test_job(items, opts)
        tq = PrintQueue()
        tq.items = items
        s = tq.stats(opts)
        what = "IMPRESSÃO DE TESTE (só a 1ª página de cada)\n" if test else ""
        if not opts.dry_run and not messagebox.askyesno(
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
        self.btn_print.config(state="disabled")
        self.btn_cancel.config(state="normal")
        backend = get_backend(opts.dry_run, log=lambda *a: self.events.put(("log", " ".join(map(str, a)))))

        def work():
            try:
                self.rows = core.run_job(items, opts, backend, lambda kind, **k: self.events.put((kind, k)), self.cancel)
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
                elif kind == "start":
                    self.mark(data["file"], "imprimindo…")
                elif kind == "ok":
                    self.mark(data["file"], "✔ ok")
                    self.progress.step(1)
                elif kind == "error":
                    self.mark(data["file"], "✘ falhou")
                    self.log(f"FALHOU {Path(data['file']).name}: {data['error']}")
                    self.progress.step(1)
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

    def finish(self):
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
        core.save_config(self.cfg)
        self.root.destroy()


def run_gui(initial=(), project=None):
    root = _Root()
    App(root, list(initial), project)
    root.mainloop()
    return 0
