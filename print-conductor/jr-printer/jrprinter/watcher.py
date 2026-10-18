"""Monitoramento de pasta: detecta arquivos novos e espera terminarem de ser gravados."""
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import core


class FolderWatcher:
    """`scan()` devolve só arquivos NOVOS e estáveis (mesmo tamanho e data em duas leituras seguidas),
    para não pegar um arquivo ainda sendo copiado/baixado."""

    TEMP_SUFFIXES = (".tmp", ".crdownload", ".part", ".partial", ".download")

    def __init__(self, folder, recursive=False, patterns: Optional[List[str]] = None, include_existing=False):
        self.folder = Path(folder)
        self.recursive = recursive
        self.patterns = patterns
        self.seen = set()
        self.pending: Dict[str, Tuple[int, float]] = {}
        if not include_existing:
            self.seen = {core.norm_key(f) for f in self._list()}

    def _list(self) -> List[Path]:
        try:
            it = self.folder.rglob("*") if self.recursive else self.folder.glob("*")
            files = [f for f in it if f.is_file() and f.suffix.lower() in core.SUPPORTED
                     and not f.name.startswith(("~$", ".~lock"))
                     and not f.name.lower().endswith(self.TEMP_SUFFIXES)]
        except OSError:
            return []
        return core.filter_files(files, self.patterns)

    def scan(self) -> List[Path]:
        ready = []
        current = set()
        for f in self._list():
            key = core.norm_key(f)
            current.add(key)
            if key in self.seen:
                continue
            try:
                st = f.stat()
            except OSError:
                continue
            sig = (st.st_size, st.st_mtime)
            if st.st_size > 0 and self.pending.get(key) == sig:
                self.seen.add(key)
                self.pending.pop(key, None)
                ready.append(f)
            else:
                self.pending[key] = sig
        for k in list(self.pending):           # sumiu antes de estabilizar
            if k not in current:
                del self.pending[k]
        return core.sort_files(ready, "natural")
