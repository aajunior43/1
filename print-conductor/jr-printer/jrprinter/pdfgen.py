"""Gerador mínimo de PDF (sem dependências) para páginas de rosto, avisos, texto e imagens (folhas e logotipos)."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

PAGE_W, PAGE_H = 595, 842          # A4 em pontos
LETTER_W, LETTER_H = 612, 792


@dataclass
class PdfImage:
    """Imagem JPEG (bytes) posicionada na página, em pontos. (x, y) é o canto inferior esquerdo."""
    jpeg: bytes
    px_w: int
    px_h: int
    x: float
    y: float
    w: float
    h: float


@dataclass
class Page:
    items: list = field(default_factory=list)     # (fonte, tamanho, x, y, texto)
    images: List[PdfImage] = field(default_factory=list)


def _esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _enc(s):
    return _esc(s).encode("cp1252", "replace")


def _image_object(im: PdfImage) -> bytes:
    head = (f"<< /Type /XObject /Subtype /Image /Width {im.px_w} /Height {im.px_h} /ColorSpace /DeviceRGB "
            f"/BitsPerComponent 8 /Filter /DCTDecode /Length {len(im.jpeg)} >>\nstream\n").encode()
    return head + im.jpeg + b"\nendstream"


def write_pdf(path, pages, page_w=PAGE_W, page_h=PAGE_H):
    """pages: lista de páginas. Cada página é um `Page` ou, por compatibilidade, uma lista de
    (fonte, tamanho, x, y, texto) — fonte 'F1' = Helvetica, 'F2' = Courier."""
    norm = [p if isinstance(p, Page) else Page(items=list(p)) for p in (pages or [Page()])]
    objs = [None, None,
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>"]
    kids = []
    for pg in norm:
        page_id = len(objs) + 1
        objs.append(None)                        # reservado: objeto da página
        content_id = len(objs) + 1
        objs.append(None)                        # reservado: conteúdo
        img_ids = []
        for im in pg.images:
            img_ids.append(len(objs) + 1)
            objs.append(_image_object(im))
        ops = [b"BT /" + f.encode() + b" %d Tf %.1f %.1f Td (" % (size, x, y) + _enc(t) + b") Tj ET"
               for f, size, x, y, t in pg.items]
        ops += [b"q %.2f 0 0 %.2f %.2f %.2f cm /Im%d Do Q" % (im.w, im.h, im.x, im.y, k + 1)
                for k, im in enumerate(pg.images)]
        stream = b"\n".join(ops)
        objs[content_id - 1] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        xobj = (" /XObject << " + " ".join(f"/Im{k + 1} {iid} 0 R" for k, iid in enumerate(img_ids)) + " >>") if img_ids else ""
        objs[page_id - 1] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Contents %d 0 R "
            b"/Resources << /Font << /F1 3 0 R /F2 4 0 R >>%s >> >>" % (page_w, page_h, content_id, xobj.encode()))
        kids.append(page_id)
    objs[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[1] = b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % k for k in kids) + b"] /Count %d >>" % len(kids)
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for n, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % n + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offs:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    Path(path).write_bytes(bytes(out))
    return Path(path)


def _wrap(text, width):
    out = []
    for raw in text.expandtabs(4).splitlines() or [""]:
        while len(raw) > width:
            out.append(raw[:width])
            raw = raw[width:]
        out.append(raw)
    return out


def logo_box(px_w, px_h, max_w=200.0, max_h=120.0) -> Tuple[float, float]:
    """Tamanho em pontos de um logotipo, mantendo a proporção e cabendo na caixa."""
    ratio = px_w / px_h
    if ratio >= max_w / max_h:
        return max_w, max_w / ratio
    return max_h * ratio, max_h


def centered_page_pdf(path, lines, logo: Optional[Tuple[bytes, int, int]] = None, page_w=PAGE_W, page_h=PAGE_H):
    """Uma página com linhas centralizadas; a primeira em fonte grande. `logo` = (jpeg, largura_px, altura_px)
    é desenhado no topo, centralizado, e o texto desce logo abaixo dele."""
    page = Page()
    y = 540
    if logo:
        jpeg, pw, ph = logo
        w, h = logo_box(pw, ph)
        top = page_h - 60
        page.images.append(PdfImage(jpeg, pw, ph, (page_w - w) / 2, top - h, w, h))
        y = top - h - 40
    for i, line in enumerate(lines):
        size = 26 if i == 0 else 14
        for chunk in _wrap(line, 42 if size > 20 else 80):
            page.items.append(("F1", size, max(30, page_w / 2 - len(chunk) * size * 0.25), y, chunk))
            y -= size + 8
        y -= 8
    return write_pdf(path, [page], page_w, page_h)


def text_pdf(path, text, cols=82, lines_per_page=60):
    """Texto simples em várias páginas (Courier 10)."""
    lines = _wrap(text, cols)
    pages = []
    for start in range(0, max(len(lines), 1), lines_per_page):
        chunk = lines[start:start + lines_per_page]
        pages.append([("F2", 10, 50, PAGE_H - 50 - 12 * n, l) for n, l in enumerate(chunk)])
    return write_pdf(path, pages)


def image_pages_pdf(path, pages_jpeg: List[Tuple[bytes, int, int]], page_w=PAGE_W, page_h=PAGE_H):
    """Uma página por imagem JPEG, ocupando a página inteira."""
    return write_pdf(path, [Page(images=[PdfImage(j, pw, ph, 0, 0, page_w, page_h)]) for j, pw, ph in pages_jpeg],
                     page_w, page_h)
