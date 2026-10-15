"""Fila de impressão organizável: ordenar, agrupar, desfazer, verificar, estimar folhas e salvar projetos."""
import copy
import json
import math
from pathlib import Path
from typing import Dict, List, Optional

from . import core, fileinfo
from .core import Item, Options

PROJECT_VERSION = 1


def sheets_for(pages: Optional[int], copies: int, duplex: bool) -> Optional[int]:
    if pages is None:
        return None
    per_copy = math.ceil(pages / 2) if duplex else pages
    return per_copy * copies


class PrintQueue:
    def __init__(self):
        self.items: List[Item] = []
        self._undo: List[List[Item]] = []
        self._redo: List[List[Item]] = []
        self._pages: Dict[str, Optional[int]] = {}

    # ---- histórico ----
    def snapshot(self):
        self._undo.append(copy.deepcopy(self.items))
        del self._undo[:-100]
        self._redo.clear()

    def undo(self):
        if not self._undo:
            return False
        self._redo.append(copy.deepcopy(self.items))
        self.items = self._undo.pop()
        return True

    def redo(self):
        if not self._redo:
            return False
        self._undo.append(copy.deepcopy(self.items))
        self.items = self._redo.pop()
        return True

    # ---- conteúdo ----
    def __len__(self):
        return len(self.items)

    def add_paths(self, paths, recursive=False, patterns=None, sort="natural", warn=None) -> List[Item]:
        new = core.collect(paths, recursive, patterns, sort, False, warn)
        have = {str(i.path.resolve()) for i in self.items}
        added = [Item(f) for f in new if str(f.resolve()) not in have]
        if added:
            self.snapshot()
            self.items += added
        return added

    def remove(self, indices):
        idx = set(indices)
        if idx:
            self.snapshot()
            self.items = [it for i, it in enumerate(self.items) if i not in idx]

    def clear(self):
        if self.items:
            self.snapshot()
            self.items = []

    def remove_disabled(self):
        self.remove([i for i, it in enumerate(self.items) if not it.enabled])

    def keep_matching(self, patterns):
        keep = {id(it) for it in self.items if core.filter_files([it.path], patterns)}
        self.remove([i for i, it in enumerate(self.items) if id(it) not in keep])

    def move(self, indices, delta) -> List[int]:
        """Move os itens selecionados `delta` posições (+1 baixo, -1 cima). Devolve os novos índices."""
        sel = sorted(set(indices))
        if not sel:
            return []
        if (delta < 0 and sel[0] == 0) or (delta > 0 and sel[-1] == len(self.items) - 1):
            return sel
        self.snapshot()
        order = sel if delta < 0 else list(reversed(sel))
        for i in order:
            self.items[i + delta], self.items[i] = self.items[i], self.items[i + delta]
        return [i + delta for i in sel]

    def move_to(self, indices, target) -> List[int]:
        """Move itens selecionados para antes da posição `target` (arrastar e soltar)."""
        sel = sorted(set(indices))
        if not sel:
            return []
        self.snapshot()
        moving = [self.items[i] for i in sel]
        rest = [it for i, it in enumerate(self.items) if i not in set(sel)]
        shift = sum(1 for i in sel if i < target)
        pos = max(0, min(len(rest), target - shift))
        self.items = rest[:pos] + moving + rest[pos:]
        return list(range(pos, pos + len(moving)))

    def sort(self, key="natural", reverse=False):
        self.snapshot()
        if key == "pages":
            self.items.sort(key=lambda it: (self.pages(it) is None, self.pages(it) or 0), reverse=reverse)
            return
        order = core.sort_files([it.path for it in self.items], key, reverse)
        pos = {str(p): n for n, p in enumerate(order)}
        self.items.sort(key=lambda it: pos[str(it.path)])

    def toggle(self, indices, value=None):
        if not indices:
            return
        self.snapshot()
        for i in indices:
            self.items[i].enabled = (not self.items[i].enabled) if value is None else value

    def set_overrides(self, indices, **kw):
        """copies/pages/duplex/color/note; valor ''/None limpa o ajuste."""
        if not indices:
            return
        if kw.get("pages"):
            fileinfo.count_range(kw["pages"], None)  # valida
        if kw.get("duplex") not in (None, "", "off", "long", "short"):
            raise ValueError("duplex inválido")
        if kw.get("color") not in (None, "", "color", "mono"):
            raise ValueError("cor inválida")
        if kw.get("copies") is not None and kw["copies"] != "" and int(kw["copies"]) < 1:
            raise ValueError("cópias deve ser >= 1")
        self.snapshot()
        for i in indices:
            it = self.items[i]
            for k, v in kw.items():
                if k == "copies":
                    it.copies = int(v) if v not in (None, "") else None
                elif k in ("pages", "duplex", "color"):
                    setattr(it, k, v or None)
                elif k == "note":
                    it.note = v or ""

    def remove_duplicates(self) -> List[Item]:
        """Remove itens com conteúdo idêntico (mantém o primeiro). Devolve os removidos."""
        seen, drop, removed = {}, [], []
        for i, it in enumerate(self.items):
            try:
                key = (it.path.stat().st_size, fileinfo.sha256(it.path))
            except OSError:
                continue
            if key in seen:
                drop.append(i)
                removed.append(it)
            else:
                seen[key] = i
        self.remove(drop)
        return removed

    # ---- informações ----
    def pages(self, item: Item) -> Optional[int]:
        key = str(item.path)
        if key not in self._pages:
            self._pages[key] = fileinfo.page_count(item.path)
        return self._pages[key]

    def pages_for_print(self, item: Item) -> Optional[int]:
        try:
            return fileinfo.count_range(item.pages, self.pages(item))
        except ValueError:
            return None

    def stats(self, opts: Optional[Options] = None) -> dict:
        opts = opts or Options()
        files = [it for it in self.items if it.enabled]
        pages = sheets = unknown = 0
        by_type: Dict[str, int] = {}
        for it in files:
            eff = it.effective(opts)
            n = self.pages_for_print(it)
            by_type[it.path.suffix.lstrip(".").lower() or "?"] = by_type.get(it.path.suffix.lstrip(".").lower() or "?", 0) + 1
            extra = 1 if (opts.cover or opts.cover_text) else 0
            if n is None:
                unknown += 1
                sheets += (1 + extra) * opts.set_copies
                continue
            pages += n * eff.copies * opts.set_copies
            s = sheets_for(n, eff.copies, bool(eff.duplex)) + extra
            sheets += s * opts.set_copies
        return {"total": len(self.items), "enabled": len(files), "pages": pages, "sheets": sheets,
                "unknown": unknown, "by_type": by_type}

    def check(self, duplicates=True) -> List[fileinfo.Issue]:
        return fileinfo.check_files([it.path for it in self.items], duplicates)

    def search(self, text: str) -> List[int]:
        """Índices dos itens cujo nome/pasta/nota contêm o texto (sem alterar a fila)."""
        t = text.strip().lower()
        if not t:
            return list(range(len(self.items)))
        return [i for i, it in enumerate(self.items)
                if t in it.path.name.lower() or t in str(it.path.parent).lower() or t in it.note.lower()]

    # ---- projeto ----
    def to_dict(self, opts: Optional[Options] = None) -> dict:
        from dataclasses import asdict
        d = {"version": PROJECT_VERSION,
             "items": [{"path": str(it.path), "enabled": it.enabled, **it.overrides(), "note": it.note}
                       for it in self.items]}
        if opts is not None:
            d["options"] = asdict(opts)
        return d

    def save(self, path, opts: Optional[Options] = None):
        Path(path).write_text(json.dumps(self.to_dict(opts), ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def load(path):
        """Lê um projeto (.pbq/.json) ou uma lista simples de caminhos. Devolve (fila, Options|None)."""
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        q = PrintQueue()
        raw = data["items"] if isinstance(data, dict) else data
        for r in raw:
            if isinstance(r, str):
                q.items.append(Item(r))
            else:
                q.items.append(Item(r["path"], r.get("enabled", True), r.get("copies"), r.get("pages"),
                                    r.get("duplex"), r.get("color"), r.get("note", "")))
        opts = None
        if isinstance(data, dict) and "options" in data:
            allowed = Options.__dataclass_fields__
            opts = Options(**{k: v for k, v in data["options"].items() if k in allowed})
        return q, opts
