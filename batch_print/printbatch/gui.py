"""Interface gráfica (tkinter)."""
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__, core
from .backends import get_backend

try:  # arrastar e soltar (opcional: pip install tkinterdnd2)
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _Root = TkinterDnD.Tk
except Exception:  # pragma: no cover
    DND_FILES, _Root = None, tk.Tk

DUPLEX = {"Desligado": None, "Borda longa": "long", "Borda curta": "short"}
COLOR = {"Padrão da impressora": None, "Colorido": True, "Preto e branco": False}
COVER_NAMES = {"Sem página de rosto": None, "Nome do arquivo": "filename", "Nome + pasta": "filename-folder",
               "Completa": "full", "Número na fila": "number", "Personalizada…": "custom"}
PAPERS = ["", "A4", "A3", "A5", "Letter", "Legal"]


def fmt_size(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


class App:
    def __init__(self, root, initial):
        self.root = root
        root.title(f"PrintBatch {__version__} — impressão em lote")
        root.geometry("1100x720")
        root.minsize(900, 600)
        self.files = []
        self.status = {}
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.rows = []
        self.cfg = core.load_config()
        self.backend = get_backend(False)
        self.build()
        self.load_printers()
        self.apply_cfg()
        if initial:
            self.add_paths(initial)
        for p in self.backend.problems():
            self.log("AVISO: " + p)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(100, self.poll)

    # ---------- UI ----------
    def build(self):
        pad = dict(padx=6, pady=3)
        main = ttk.PanedWindow(self.root, orient="horizontal")
        main.pack(fill="both", expand=True, padx=6, pady=6)
        left, right = ttk.Frame(main), ttk.Frame(main, width=330)
        main.add(left, weight=3)
        main.add(right, weight=1)

        bar = ttk.Frame(left)
        bar.pack(fill="x")
        for text, cmd in (("Adicionar arquivos…", self.add_files), ("Adicionar pasta…", self.add_folder),
                          ("Remover", self.remove), ("Limpar", self.clear), ("▲", lambda: self.move(-1)),
                          ("▼", lambda: self.move(1))):
            ttk.Button(bar, text=text, command=cmd, width=(3 if len(text) == 1 else 0) or None).pack(side="left", **pad)
        self.recursive = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="incluir subpastas", variable=self.recursive).pack(side="left", **pad)

        bar2 = ttk.Frame(left)
        bar2.pack(fill="x")
        ttk.Label(bar2, text="Ordenar por:").pack(side="left", **pad)
        self.sort = tk.StringVar(value="name")
        ttk.Combobox(bar2, textvariable=self.sort, values=list(core.SORTS), width=8, state="readonly").pack(side="left")
        self.reverse = tk.BooleanVar()
        ttk.Checkbutton(bar2, text="inverter", variable=self.reverse).pack(side="left", **pad)
        ttk.Button(bar2, text="Aplicar", command=self.apply_sort).pack(side="left", **pad)
        ttk.Label(bar2, text="Filtro:").pack(side="left", padx=(16, 2))
        self.filter = tk.StringVar()
        e = ttk.Entry(bar2, textvariable=self.filter, width=16)
        e.pack(side="left")
        ttk.Button(bar2, text="Manter só os que casam", command=self.apply_filter).pack(side="left", **pad)

        cols = ("nome", "tipo", "tamanho", "pasta", "status")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="extended")
        for c, w in zip(cols, (260, 60, 80, 300, 110)):
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=w, anchor="w")
        sb = ttk.Scrollbar(left, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="top", fill="both", expand=True, pady=4)
        sb.place(in_=self.tree, relx=1.0, rely=0, relheight=1.0, anchor="ne")
        self.tree.bind("<Delete>", lambda e: self.remove())
        if DND_FILES:
            self.tree.drop_target_register(DND_FILES)
            self.tree.dnd_bind("<<Drop>>", lambda e: self.add_paths(self.root.tk.splitlist(e.data)))

        self.progress = ttk.Progressbar(left, mode="determinate")
        self.progress.pack(fill="x", pady=2)
        self.info = ttk.Label(left, text="0 arquivos")
        self.info.pack(anchor="w")
        self.logbox = tk.Text(left, height=8, state="disabled", wrap="word")
        self.logbox.pack(fill="x", pady=4)

        # --- opções ---
        box = ttk.LabelFrame(right, text="Impressão")
        box.pack(fill="x", **pad)
        ttk.Label(box, text="Impressora").grid(row=0, column=0, sticky="w", **pad)
        self.printer = tk.StringVar()
        self.printer_cb = ttk.Combobox(box, textvariable=self.printer, state="readonly", width=28)
        self.printer_cb.grid(row=1, column=0, columnspan=2, sticky="we", **pad)
        ttk.Button(box, text="↻", width=3, command=self.load_printers).grid(row=1, column=2, **pad)
        self.copies = tk.IntVar(value=1)
        ttk.Label(box, text="Cópias").grid(row=2, column=0, sticky="w", **pad)
        ttk.Spinbox(box, from_=1, to=999, textvariable=self.copies, width=6).grid(row=2, column=1, sticky="w", **pad)
        self.duplex = tk.StringVar(value="Desligado")
        ttk.Label(box, text="Frente e verso").grid(row=3, column=0, sticky="w", **pad)
        ttk.Combobox(box, textvariable=self.duplex, values=list(DUPLEX), state="readonly", width=16).grid(row=3, column=1, columnspan=2, sticky="w", **pad)
        self.color = tk.StringVar(value="Padrão da impressora")
        ttk.Label(box, text="Cor").grid(row=4, column=0, sticky="w", **pad)
        ttk.Combobox(box, textvariable=self.color, values=list(COLOR), state="readonly", width=20).grid(row=4, column=1, columnspan=2, sticky="w", **pad)
        self.paper = tk.StringVar()
        ttk.Label(box, text="Papel").grid(row=5, column=0, sticky="w", **pad)
        ttk.Combobox(box, textvariable=self.paper, values=PAPERS, width=10).grid(row=5, column=1, sticky="w", **pad)
        self.pages = tk.StringVar()
        ttk.Label(box, text="Páginas").grid(row=6, column=0, sticky="w", **pad)
        ttk.Entry(box, textvariable=self.pages, width=12).grid(row=6, column=1, sticky="w", **pad)
        ttk.Label(box, text="ex.: 1-3,5", foreground="gray").grid(row=6, column=2, sticky="w")
        self.landscape = tk.BooleanVar()
        self.fit = tk.BooleanVar()
        ttk.Checkbutton(box, text="Paisagem", variable=self.landscape).grid(row=7, column=0, sticky="w", **pad)
        ttk.Checkbutton(box, text="Ajustar à página", variable=self.fit).grid(row=7, column=1, columnspan=2, sticky="w", **pad)

        ext = ttk.LabelFrame(right, text="Extras")
        ext.pack(fill="x", **pad)
        self.cover = tk.StringVar(value="Sem página de rosto")
        ttk.Label(ext, text="Página de rosto").pack(anchor="w", **pad)
        cb = ttk.Combobox(ext, textvariable=self.cover, values=list(COVER_NAMES), state="readonly")
        cb.pack(fill="x", **pad)
        cb.bind("<<ComboboxSelected>>", lambda e: self.toggle_cover())
        self.cover_text = tk.Text(ext, height=4, width=30)
        self.cover_text.insert("1.0", "{name}\nPasta: {folder}\nArquivo {index} de {total}")
        self.cover_hint = ttk.Label(ext, text="Campos: {name} {folder} {folder_path} {ext} {index} {total} {date}", foreground="gray", wraplength=300)
        self.failed = tk.BooleanVar(value=True)
        self.attach = tk.BooleanVar()
        self.dry = tk.BooleanVar()
        self.check_frame = ttk.Frame(ext)
        self.check_frame.pack(fill="x")
        for text, var in (("Imprimir aviso quando um arquivo falhar", self.failed),
                          ("Imprimir anexos de e-mails (.eml)", self.attach),
                          ("Simular (não imprime)", self.dry)):
            ttk.Checkbutton(self.check_frame, text=text, variable=var).pack(anchor="w", **pad)

        act = ttk.Frame(right)
        act.pack(fill="x", **pad)
        self.btn_print = ttk.Button(act, text="🖨  Imprimir", command=self.start)
        self.btn_print.pack(fill="x", **pad)
        self.btn_cancel = ttk.Button(act, text="Cancelar", command=self.cancel.set, state="disabled")
        self.btn_cancel.pack(fill="x", **pad)
        ttk.Button(act, text="Salvar relatório…", command=self.save_report).pack(fill="x", **pad)
        ttk.Button(act, text="Salvar fila…", command=self.save_queue).pack(fill="x", **pad)
        ttk.Button(act, text="Carregar fila…", command=self.load_queue).pack(fill="x", **pad)

    def toggle_cover(self):
        if COVER_NAMES[self.cover.get()] == "custom":
            self.cover_text.pack(fill="x", padx=6, pady=3, before=self.check_frame)
            self.cover_hint.pack(anchor="w", padx=6, before=self.check_frame)
        else:
            self.cover_text.pack_forget()
            self.cover_hint.pack_forget()

    # ---------- fila ----------
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        total = 0
        for i, f in enumerate(self.files):
            try:
                size = f.stat().st_size
            except OSError:
                size = 0
            total += size
            self.tree.insert("", "end", iid=str(i), values=(f.name, f.suffix.lstrip(".").upper(), fmt_size(size),
                                                           str(f.parent), self.status.get(str(f), "")))
        self.info.config(text=f"{len(self.files)} arquivo(s) — {fmt_size(total)}")

    def add_paths(self, paths):
        new = core.collect(paths, self.recursive.get(), None, self.sort.get(), self.reverse.get(), warn=self.log)
        have = {str(f.resolve()) for f in self.files}
        added = [f for f in new if str(f.resolve()) not in have]
        self.files += added
        self.refresh()
        self.log(f"{len(added)} arquivo(s) adicionado(s)")

    def add_files(self):
        exts = " ".join("*" + e for e in sorted(core.SUPPORTED))
        paths = filedialog.askopenfilenames(title="Escolha os arquivos",
                                            filetypes=[("Documentos suportados", exts), ("Todos", "*.*")])
        if paths:
            self.add_paths(paths)

    def add_folder(self):
        d = filedialog.askdirectory(title="Escolha a pasta")
        if d:
            self.add_paths([d])

    def selected(self):
        return sorted(int(i) for i in self.tree.selection())

    def remove(self):
        for i in reversed(self.selected()):
            del self.files[i]
        self.refresh()

    def clear(self):
        self.files, self.status = [], {}
        self.refresh()

    def move(self, d):
        sel = self.selected()
        if not sel or (d < 0 and sel[0] == 0) or (d > 0 and sel[-1] == len(self.files) - 1):
            return
        for i in (sel if d < 0 else reversed(sel)):
            self.files[i + d], self.files[i] = self.files[i], self.files[i + d]
        self.refresh()
        self.tree.selection_set([str(i + d) for i in sel])

    def apply_sort(self):
        self.files = core.sort_files(self.files, self.sort.get(), self.reverse.get())
        self.refresh()

    def apply_filter(self):
        pats = [p.strip() for p in self.filter.get().replace(";", ",").split(",") if p.strip()]
        if pats:
            self.files = core.filter_files(self.files, pats)
            self.refresh()

    # ---------- impressoras / config ----------
    def load_printers(self):
        names, default = self.backend.list_printers()
        self.printer_cb["values"] = names
        if not self.printer.get() or self.printer.get() not in names:
            self.printer.set(default or (names[0] if names else ""))

    def apply_cfg(self):
        c = self.cfg
        if c.get("printer") in (self.printer_cb["values"] or ()):
            self.printer.set(c["printer"])
        self.copies.set(c.get("copies", 1))
        self.duplex.set(c.get("duplex", "Desligado"))
        self.color.set(c.get("color", "Padrão da impressora"))
        self.paper.set(c.get("paper", ""))
        self.landscape.set(c.get("landscape", False))
        self.fit.set(c.get("fit", False))
        self.cover.set(c.get("cover", "Sem página de rosto"))
        self.failed.set(c.get("failed", True))
        self.attach.set(c.get("attach", False))
        if c.get("cover_text"):
            self.cover_text.delete("1.0", "end")
            self.cover_text.insert("1.0", c["cover_text"])
        self.toggle_cover()

    def save_cfg(self):
        core.save_config({
            "printer": self.printer.get(), "copies": self.copies.get(), "duplex": self.duplex.get(),
            "color": self.color.get(), "paper": self.paper.get(), "landscape": self.landscape.get(),
            "fit": self.fit.get(), "cover": self.cover.get(), "failed": self.failed.get(),
            "attach": self.attach.get(), "cover_text": self.cover_text.get("1.0", "end").strip()})

    def options(self):
        cv = COVER_NAMES[self.cover.get()]
        text = self.cover_text.get("1.0", "end").strip() if cv == "custom" else None
        return core.Options(
            printer=self.printer.get() or None, copies=max(1, int(self.copies.get() or 1)),
            duplex=DUPLEX[self.duplex.get()], pages=self.pages.get().strip() or None,
            paper=self.paper.get().strip() or None, landscape=self.landscape.get(), fit=self.fit.get(),
            color=COLOR[self.color.get()], cover=None if cv == "custom" else cv, cover_text=text,
            failed_page=self.failed.get(), attachments=self.attach.get(), dry_run=self.dry.get())

    # ---------- execução ----------
    def start(self):
        if not self.files:
            messagebox.showinfo("PrintBatch", "Adicione arquivos à fila primeiro.")
            return
        try:
            opts = self.options()
            opts.validate()
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("PrintBatch", str(e))
            return
        if not opts.dry_run and not messagebox.askyesno(
                "Confirmar", f"Imprimir {len(self.files)} arquivo(s) em “{opts.printer or 'impressora padrão'}” "
                             f"({opts.copies} cópia(s) cada)?"):
            return
        self.save_cfg()
        self.status = {}
        self.refresh()
        self.cancel.clear()
        self.progress.config(maximum=len(self.files), value=0)
        self.btn_print.config(state="disabled")
        self.btn_cancel.config(state="normal")
        files = list(self.files)
        backend = get_backend(opts.dry_run, log=lambda *a: self.events.put(("log", " ".join(map(str, a)))))

        def work():
            try:
                self.rows = core.run_job(files, opts, backend,
                                         lambda kind, **k: self.events.put((kind, k)), self.cancel)
            except Exception as e:
                self.events.put(("fatal", str(e)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "log":
                    self.log(data)
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
        for i, x in enumerate(self.files):
            if str(x) == str(f) and self.tree.exists(str(i)):
                self.tree.set(str(i), "status", text)
                self.tree.see(str(i))
                break

    def finish(self):
        self.btn_print.config(state="normal")
        self.btn_cancel.config(state="disabled")

    # ---------- relatório / fila ----------
    def save_report(self):
        if not self.rows:
            messagebox.showinfo("PrintBatch", "Ainda não há relatório; imprima primeiro.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("JSON", "*.json")])
        if p:
            core.write_report(p, self.rows)
            self.log("Relatório salvo em " + p)

    def save_queue(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Fila", "*.json")])
        if p:
            import json
            Path(p).write_text(json.dumps([str(f) for f in self.files], ensure_ascii=False, indent=2), encoding="utf-8")

    def load_queue(self):
        p = filedialog.askopenfilename(filetypes=[("Fila", "*.json")])
        if p:
            import json
            self.add_paths(json.loads(Path(p).read_text(encoding="utf-8")))

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
        self.save_cfg()
        self.root.destroy()


def run_gui(initial=()):
    root = _Root()
    App(root, list(initial))
    root.mainloop()
    return 0
