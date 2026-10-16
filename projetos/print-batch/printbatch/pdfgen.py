"""Gerador mínimo de PDF (sem dependências) para páginas de rosto, avisos e texto."""
from pathlib import Path

PAGE_W, PAGE_H = 595, 842


def _esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _enc(s):
    return _esc(s).encode("cp1252", "replace")


def write_pdf(path, pages):
    """pages: lista de páginas; cada página é lista de (fonte, tamanho, x, y, texto).
    fonte: 'F1' = Helvetica, 'F2' = Courier."""
    objs = [None, None,
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>"]
    kids = []
    for items in pages or [[]]:
        stream = b"\n".join(
            b"BT /" + f.encode() + b" %d Tf %.1f %.1f Td (" % (size, x, y) + _enc(t) + b") Tj ET"
            for f, size, x, y, t in items)
        content_id = len(objs) + 2
        page_id = len(objs) + 1
        objs.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Contents %d 0 R "
            b"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>" % (PAGE_W, PAGE_H, content_id))
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
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


def centered_page_pdf(path, lines):
    """Uma página com linhas centralizadas; a primeira em fonte grande."""
    items, y = [], 540
    for i, line in enumerate(lines):
        size = 26 if i == 0 else 14
        for chunk in _wrap(line, 42 if size > 20 else 80):
            items.append(("F1", size, max(30, PAGE_W / 2 - len(chunk) * size * 0.25), y, chunk))
            y -= size + 8
        y -= 8
    return write_pdf(path, [items])


def text_pdf(path, text, cols=82, lines_per_page=60):
    """Texto simples em várias páginas (Courier 10)."""
    lines = _wrap(text, cols)
    pages = []
    for start in range(0, max(len(lines), 1), lines_per_page):
        chunk = lines[start:start + lines_per_page]
        pages.append([("F2", 10, 50, PAGE_H - 50 - 12 * n, l) for n, l in enumerate(chunk)])
    return write_pdf(path, pages)
