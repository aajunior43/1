"""Tema visual (claro/escuro) para a interface tkinter, sem dependências extras."""
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

PALETTES = {
    "light": dict(bg="#f3f4f6", card="#ffffff", card_alt="#f8fafc", border="#d9dde3", text="#1f2937", muted="#6b7280",
                  accent="#2563eb", accent_hover="#1d4ed8", accent_text="#ffffff", accent_soft="#dbeafe",
                  btn="#ffffff", btn_hover="#eef2f7", btn_active="#e2e8f0", field="#ffffff",
                  ok="#15803d", error="#b91c1c", warn="#b45309", off="#9ca3af", danger="#dc2626",
                  sel="#dbeafe", sel_text="#1e3a8a", zebra="#f8fafc", preview_bg="#e5e7eb"),
    "dark": dict(bg="#16181d", card="#1f2229", card_alt="#252932", border="#343944", text="#e5e7eb", muted="#9ca3af",
                 accent="#3b82f6", accent_hover="#60a5fa", accent_text="#ffffff", accent_soft="#1e3a5f",
                 btn="#2a2e37", btn_hover="#343a46", btn_active="#3e4552", field="#16181d",
                 ok="#4ade80", error="#f87171", warn="#fbbf24", off="#6b7280", danger="#ef4444",
                 sel="#1e3a5f", sel_text="#dbeafe", zebra="#232730", preview_bg="#0f1115"),
}


def ui_family():
    fams = set(tkfont.families())
    order = {"win": ("Segoe UI Variable Text", "Segoe UI"), "darwin": ("SF Pro Text", "Helvetica Neue")}
    key = "win" if sys.platform.startswith("win") else "darwin" if sys.platform == "darwin" else "x"
    for f in order.get(key, ()) + ("Inter", "Noto Sans", "DejaVu Sans", "Helvetica"):
        if f in fams:
            return f
    return tkfont.nametofont("TkDefaultFont").actual("family")


def mono_family():
    fams = set(tkfont.families())
    for f in ("Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "Courier New"):
        if f in fams:
            return f
    return "TkFixedFont"


def apply(root, mode="light"):
    """Aplica o tema à janela e devolve a paleta usada."""
    p = dict(PALETTES.get(mode, PALETTES["light"]))
    fam = ui_family()
    p["font"], p["mono"] = fam, mono_family()
    for name, size, weight in (("TkDefaultFont", 10, "normal"), ("TkTextFont", 10, "normal"),
                               ("TkMenuFont", 10, "normal"), ("TkHeadingFont", 10, "bold")):
        try:
            tkfont.nametofont(name).configure(family=fam, size=size, weight=weight)
        except tk.TclError:
            pass
    root.configure(background=p["bg"])
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    st.configure(".", background=p["bg"], foreground=p["text"], fieldbackground=p["field"], bordercolor=p["border"],
                 lightcolor=p["border"], darkcolor=p["border"], troughcolor=p["card_alt"], focuscolor=p["accent"],
                 font=(fam, 10))
    st.configure("TFrame", background=p["bg"])
    st.configure("Card.TFrame", background=p["card"], relief="solid", borderwidth=1)
    st.configure("TLabel", background=p["bg"], foreground=p["text"])
    st.configure("Muted.TLabel", foreground=p["muted"])
    st.configure("Title.TLabel", font=(fam, 16, "bold"), foreground=p["text"])
    st.configure("Subtitle.TLabel", foreground=p["muted"])
    st.configure("Chip.TLabel", background=p["accent_soft"], foreground=p["sel_text"] if mode == "light" else p["text"],
                 padding=(10, 4), font=(fam, 10, "bold"))
    st.configure("TLabelframe", background=p["bg"], bordercolor=p["border"], relief="solid", borderwidth=1, padding=6)
    st.configure("TLabelframe.Label", background=p["bg"], foreground=p["muted"], font=(fam, 9, "bold"))
    st.configure("TSeparator", background=p["border"])

    # botões
    st.configure("TButton", background=p["btn"], foreground=p["text"], bordercolor=p["border"], relief="flat",
                 borderwidth=1, padding=(10, 5), focusthickness=0, focuscolor=p["btn"])
    st.map("TButton", background=[("disabled", p["card_alt"]), ("pressed", p["btn_active"]), ("active", p["btn_hover"])],
           foreground=[("disabled", p["off"])], bordercolor=[("active", p["accent"])])
    st.configure("Tool.TButton", padding=(7, 3))
    st.configure("Accent.TButton", background=p["accent"], foreground=p["accent_text"], bordercolor=p["accent"],
                 padding=(14, 8), font=(fam, 11, "bold"))
    st.map("Accent.TButton", background=[("disabled", p["border"]), ("pressed", p["accent_hover"]), ("active", p["accent_hover"])],
           foreground=[("disabled", p["muted"])], bordercolor=[("active", p["accent_hover"])])
    st.configure("Danger.TButton", foreground=p["danger"], padding=(10, 5))
    st.map("Danger.TButton", foreground=[("disabled", p["off"])])

    # campos
    for w in ("TEntry", "TSpinbox", "TCombobox"):
        st.configure(w, fieldbackground=p["field"], foreground=p["text"], bordercolor=p["border"], padding=4,
                     insertcolor=p["text"], arrowcolor=p["muted"], selectbackground=p["accent"], selectforeground="#ffffff")
    st.map("TCombobox", fieldbackground=[("readonly", p["field"])], foreground=[("readonly", p["text"])],
           bordercolor=[("focus", p["accent"])])
    st.map("TEntry", bordercolor=[("focus", p["accent"])])
    st.map("TSpinbox", bordercolor=[("focus", p["accent"])])
    root.option_add("*TCombobox*Listbox.background", p["field"])
    root.option_add("*TCombobox*Listbox.foreground", p["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", p["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.font", (fam, 10))
    st.configure("TCheckbutton", background=p["bg"], foreground=p["text"], indicatorbackground=p["field"],
                 indicatorforeground=p["accent"], padding=2)
    st.map("TCheckbutton", background=[("active", p["bg"])], indicatorbackground=[("selected", p["accent"])],
           indicatorforeground=[("selected", "#ffffff")])

    # lista
    st.configure("Treeview", background=p["card"], fieldbackground=p["card"], foreground=p["text"], rowheight=28,
                 bordercolor=p["border"], borderwidth=1, relief="flat", font=(fam, 10))
    st.map("Treeview", background=[("selected", p["sel"])], foreground=[("selected", p["sel_text"] if mode == "light" else p["text"])])
    st.configure("Treeview.Heading", background=p["card_alt"], foreground=p["muted"], relief="flat", padding=(6, 6),
                 font=(fam, 9, "bold"), bordercolor=p["border"])
    st.map("Treeview.Heading", background=[("active", p["btn_hover"])])

    st.configure("Horizontal.TProgressbar", background=p["accent"], troughcolor=p["card_alt"], bordercolor=p["border"],
                 lightcolor=p["accent"], darkcolor=p["accent"], thickness=10)
    for o in ("Vertical", "Horizontal"):
        st.configure(f"{o}.TScrollbar", background=p["btn"], troughcolor=p["bg"], bordercolor=p["bg"],
                     arrowcolor=p["muted"], relief="flat", gripcount=0)
        st.map(f"{o}.TScrollbar", background=[("active", p["btn_hover"])])
    st.configure("TPanedwindow", background=p["bg"])
    st.configure("Sash", sashthickness=8, background=p["bg"], gripcount=0)
    return p


def style_text(widget, p):
    """Estiliza um tk.Text (log, modelo de rosto)."""
    widget.configure(background=p["card"], foreground=p["text"], insertbackground=p["text"], relief="flat",
                     highlightthickness=1, highlightbackground=p["border"], highlightcolor=p["accent"],
                     selectbackground=p["accent"], selectforeground="#ffffff", font=(p["mono"], 9), padx=8, pady=6)


def style_menu(menu, p):
    menu.configure(background=p["card"], foreground=p["text"], activebackground=p["accent"],
                   activeforeground="#ffffff", relief="flat", borderwidth=1)


def enable_hidpi():
    """Texto nítido em telas de alta resolução no Windows."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
