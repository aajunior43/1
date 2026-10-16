"""Informações sobre arquivos da fila: contagem de páginas e verificação de problemas."""
import hashlib
import math
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from . import core

LINES_PER_TEXT_PAGE = 60


def count_range(spec: Optional[str], total: Optional[int]) -> Optional[int]:
    """Quantas páginas um intervalo ('1-3,5', '7-') seleciona. None se indeterminável."""
    if not spec:
        return total
    pages = set()
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d*))?", part)
        if not m:
            raise ValueError(f"intervalo inválido: {part!r}")
        a = int(m.group(1))
        if m.group(2) is None:
            b = a
        elif m.group(2) == "":
            if total is None:
                return None
            b = total
        else:
            b = int(m.group(2))
        if b < a or a < 1:
            raise ValueError(f"intervalo inválido: {part!r}")
        pages.update(range(a, (min(b, total) if total else b) + 1))
    return len(pages)


def _zip_text(path, name):
    try:
        with zipfile.ZipFile(path) as z:
            return z.read(name).decode("utf-8", "ignore")
    except Exception:
        return ""


def pdf_info(path):
    data = Path(path).read_bytes()
    encrypted = b"/Encrypt" in data[-4096:] or b"/Encrypt" in data[:4096]
    n = None
    try:
        import pypdf
        r = pypdf.PdfReader(str(path))
        if not r.is_encrypted:
            n = len(r.pages)
    except Exception:
        pass
    if n is None:
        direct = len(re.findall(rb"/Type\s*/Page(?![A-Za-z])", data))
        counts = [int(c) for c in re.findall(rb"/Count\s+(\d+)", data)]
        n = max([direct] + counts) or None
    return n, encrypted


def page_count(path) -> Optional[int]:
    """Melhor estimativa do número de páginas; None se desconhecido."""
    p = Path(path)
    ext = p.suffix.lower()
    try:
        if ext == ".pdf":
            return pdf_info(p)[0]
        if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}:
            return 1
        if ext in core.TEXT:
            return max(1, math.ceil(len(core.read_text(p).splitlines()) / LINES_PER_TEXT_PAGE))
        if ext == ".docx":
            m = re.search(r"<Pages>(\d+)</Pages>", _zip_text(p, "docProps/app.xml"))
            return int(m.group(1)) if m else None
        if ext == ".pptx":
            m = re.search(r"<Slides>(\d+)</Slides>", _zip_text(p, "docProps/app.xml"))
            return int(m.group(1)) if m else None
        if ext in {".odt", ".ods", ".odp"}:
            m = re.search(r'page-count="(\d+)"', _zip_text(p, "meta.xml"))
            return int(m.group(1)) if m else None
        if ext in core.MAIL:
            return 1
    except Exception:
        return None
    return None


def sha256(path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


@dataclass
class Issue:
    level: str       # "erro" | "aviso"
    path: Path
    message: str


def converter_available() -> bool:
    if core.IS_WINDOWS:
        try:
            import win32com.client  # noqa: F401
            return True
        except Exception:
            pass
    return core.find_soffice() is not None


def check_files(paths: List[Path], find_duplicates=True) -> List[Issue]:
    issues: List[Issue] = []
    seen = {}
    office_ok = None
    for p in paths:
        p = Path(p)
        ext = p.suffix.lower()
        if not p.exists():
            issues.append(Issue("erro", p, "arquivo não encontrado"))
            continue
        if p.name.startswith("~$") or p.name.startswith(".~lock") or p.name.lower() in {"thumbs.db", "desktop.ini", ".ds_store"}:
            issues.append(Issue("aviso", p, "arquivo temporário/de sistema — provavelmente não deve ser impresso"))
        try:
            size = p.stat().st_size
        except OSError as e:
            issues.append(Issue("erro", p, f"não foi possível ler: {e}"))
            continue
        if size == 0:
            issues.append(Issue("erro", p, "arquivo vazio"))
            continue
        if ext not in core.SUPPORTED:
            issues.append(Issue("erro", p, f"formato não suportado ({ext or 'sem extensão'})"))
            continue
        if size > 200 * 1024 * 1024:
            issues.append(Issue("aviso", p, "arquivo muito grande (>200 MB)"))
        if ext == ".pdf":
            try:
                n, enc = pdf_info(p)
                if enc:
                    issues.append(Issue("aviso", p, "PDF protegido/criptografado — pode não imprimir"))
                elif not n:
                    issues.append(Issue("aviso", p, "PDF sem páginas detectadas — pode estar corrompido"))
            except OSError as e:
                issues.append(Issue("erro", p, f"não foi possível ler: {e}"))
        if ext in core.OFFICE:
            if office_ok is None:
                office_ok = converter_available()
            if not office_ok:
                issues.append(Issue("aviso", p, "sem Office/LibreOffice para converter este documento"))
        if find_duplicates:
            try:
                key = (size, sha256(p))
            except OSError:
                continue
            if key in seen:
                issues.append(Issue("aviso", p, f"duplicado de {seen[key].name} ({seen[key].parent})"))
            else:
                seen[key] = p
    return issues
