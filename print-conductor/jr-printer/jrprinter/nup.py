"""Várias páginas por folha (N-up) e logotipos: rasteriza as páginas e monta folhas em um PDF.

As folhas são imagens (150 dpi) — pronta para imprimir em qualquer impressora, mas o texto dentro das folhas
não é selecionável. Precisa de pypdfium2 e pillow (ambos já estão em requirements-windows.txt).
"""
import io
import re
from pathlib import Path
from typing import List, Optional, Tuple

from . import pdfgen

PER_SHEET = (1, 2, 4, 6, 9)
# Grades (linhas, colunas) que cabem bem em uma folha; a escolhida é a que deixa cada página maior.
CANDIDATES = {2: [(2, 1), (1, 2)], 4: [(2, 2)], 6: [(3, 2), (2, 3)], 9: [(3, 3)]}
PAPER_PT = {"A4": (595, 842), "Letter": (612, 792), "A3": (842, 1191), "A5": (420, 595), "Legal": (612, 1008)}
MARGIN_PT = 18
PAD_PT = 4
DPI = 150
JPEG_QUALITY = 88
REF_PAGE = (595, 842)              # página de referência (A4 em retrato) para escolher a grade
BORDER = (170, 170, 170)


def _need_libs():
    try:
        import pypdfium2  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as e:
        raise RuntimeError("Para várias páginas por folha e logotipos instale pypdfium2 e pillow: "
                           "pip install pypdfium2 pillow") from e


def parse_pages(spec: Optional[str], total: int) -> List[int]:
    """'1-3,5,7-' -> índices 0-based das páginas existentes (sem repetição, em ordem)."""
    if not spec:
        return list(range(total))
    picked = set()
    for raw in spec.replace(" ", "").split(","):
        if not raw:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d*))?", raw)
        if not m:
            raise ValueError(f"intervalo inválido: {raw!r}")
        a = int(m.group(1))
        b = total if m.group(2) == "" else int(m.group(2) or a)
        if a < 1 or b < a:
            raise ValueError(f"intervalo inválido: {raw!r}")
        picked.update(range(a - 1, min(b, total)))
    return sorted(picked)


def sheet_size(paper: Optional[str], landscape: bool) -> Tuple[float, float]:
    w, h = PAPER_PT.get(paper or "A4", PAPER_PT["A4"])
    return (h, w) if landscape else (w, h)


def grid_for(per_sheet: int, sheet_w: float, sheet_h: float, margin: float = MARGIN_PT):
    """(linhas, colunas) com a maior escala para uma página de referência."""
    if per_sheet == 1:
        return 1, 1
    if per_sheet not in CANDIDATES:
        raise ValueError(f"páginas por folha deve ser um de {PER_SHEET}")
    best, best_score = None, -1.0
    for r, c in CANDIDATES[per_sheet]:
        cw = (sheet_w - 2 * margin) / c
        ch = (sheet_h - 2 * margin) / r
        score = min(cw / REF_PAGE[0], ch / REF_PAGE[1])
        if score > best_score:
            best, best_score = (r, c), score
    return best


def cells(per_sheet: int, sheet_w: float, sheet_h: float, margin: float = MARGIN_PT):
    """Retângulos (x, y, w, h) em pontos, do canto inferior esquerdo, na ordem de leitura (topo → base)."""
    r, c = grid_for(per_sheet, sheet_w, sheet_h, margin)
    cw = (sheet_w - 2 * margin) / c
    ch = (sheet_h - 2 * margin) / r
    out = []
    for row in range(r):
        for col in range(c):
            x = margin + col * cw
            y = sheet_h - margin - (row + 1) * ch
            out.append((x, y, cw, ch))
    return out[:per_sheet]


def _fit_box(cell_pt: Tuple[float, float]) -> Tuple[float, float]:
    return cell_pt[0] - 2 * PAD_PT, cell_pt[1] - 2 * PAD_PT


def _page_images(src: Path, pages_spec: Optional[str], box_pt: Tuple[float, float]):
    """Gera (imagem PIL) de cada página selecionada, já cabendo na caixa (em pontos -> pixels)."""
    from PIL import Image
    import pypdfium2 as pdfium
    k = DPI / 72.0
    bw, bh = box_pt[0] * k, box_pt[1] * k
    ext = src.suffix.lower()
    if ext == ".pdf":
        try:
            doc = pdfium.PdfDocument(str(src))
        except Exception as e:
            raise RuntimeError(f"PDF ilegível ou protegido: {e}") from e
        try:
            total = len(doc)
            if total == 0:
                raise RuntimeError("o documento não tem páginas")
            for i in parse_pages(pages_spec, total):
                page = doc[i]
                w, h = page.get_size()
                scale = min(bw / w, bh / h)      # pixels por ponto para caber na caixa
                yield page.render(scale=scale).to_pil().convert("RGB")
        finally:
            doc.close()
    else:
        im = Image.open(src)
        im.seek(0)
        im = im.convert("RGB")
        im.thumbnail((int(bw), int(bh)))
        yield im


def _sheet(pics, rects, sw, sh, border):
    from PIL import Image, ImageDraw
    k = DPI / 72.0
    im = Image.new("RGB", (round(sw * k), round(sh * k)), "white")
    d = ImageDraw.Draw(im)
    for pic, (x, y, w, h) in zip(pics, rects):
        px, py = round(x * k), round((sh - (y + h)) * k)
        pw, ph = round(w * k), round(h * k)
        im.paste(pic, (px + (pw - pic.width) // 2, py + (ph - pic.height) // 2))
        if border:
            d.rectangle([px, py, px + pw - 1, py + ph - 1], outline=BORDER)
    return im


def _jpeg(im) -> Tuple[bytes, int, int]:
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=JPEG_QUALITY, dpi=(DPI, DPI))
    return buf.getvalue(), im.width, im.height


def build_sheets(src, out_pdf, per_sheet: int, pages_spec: Optional[str] = None, landscape: bool = False,
                 paper: Optional[str] = "A4", border: bool = True) -> int:
    """Monta o PDF de folhas. Devolve quantas folhas foram criadas."""
    _need_libs()
    src = Path(src)
    if per_sheet not in PER_SHEET:
        raise ValueError(f"páginas por folha deve ser um de {PER_SHEET}")
    sw, sh = sheet_size(paper, landscape)
    rects = cells(per_sheet, sw, sh)
    box = _fit_box(rects[0][2:])
    sheets, group = [], []
    for pic in _page_images(src, pages_spec, box):
        group.append(pic)
        if len(group) == per_sheet:
            sheets.append(_jpeg(_sheet(group, rects, sw, sh, border)))
            group = []
    if group:
        sheets.append(_jpeg(_sheet(group, rects, sw, sh, border)))
    if not sheets:
        raise RuntimeError("nenhuma página selecionada (confira o intervalo de páginas)")
    pdfgen.image_pages_pdf(out_pdf, sheets, sw, sh)
    return len(sheets)


def count_sheets(pages: int, per_sheet: int) -> int:
    return -(-pages // per_sheet)


def load_logo(path) -> Tuple[bytes, int, int]:
    """Logotipo (PNG, JPG, etc.) como JPEG pronto para o rosto. Transparência vira fundo branco."""
    _need_libs()
    from PIL import Image
    im = Image.open(path)
    im.seek(0)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", im.size, "white")
        bg.paste(rgba, mask=rgba.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((900, 900))
    return _jpeg(im)
