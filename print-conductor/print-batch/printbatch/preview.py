"""Pré-visualização: renderiza páginas de qualquer arquivo suportado em PNG (miniaturas)."""
import atexit
import io
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from . import core, nup, pdfgen

_IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}


def renderer_available() -> bool:
    try:
        import pypdfium2  # noqa: F401
        import PIL  # noqa: F401
        return True
    except Exception:
        return False


class PreviewError(Exception):
    pass


class Previewer:
    """Converte (e guarda em cache) cada arquivo em PDF e renderiza páginas sob demanda."""

    def __init__(self, opts: Optional[core.Options] = None):
        self.dir = Path(tempfile.mkdtemp(prefix="printbatch_prev_"))
        atexit.register(shutil.rmtree, str(self.dir), True)
        self.cache = {}
        self.opts = opts or core.Options()

    def _key(self, path):
        st = Path(path).stat()
        return (str(path), st.st_mtime_ns, st.st_size)

    def pdf_for(self, path) -> Path:
        """PDF que representa o arquivo (o próprio PDF, ou uma conversão em cache)."""
        path = Path(path)
        if not path.exists():
            raise PreviewError("arquivo não encontrado")
        key = self._key(path)
        if key in self.cache:
            return self.cache[key]
        ext = path.suffix.lower()
        if ext == ".pdf":
            out = path
        else:
            work = self.dir / f"p{len(self.cache)}"
            work.mkdir()
            try:
                parts = core.prepare(path, work, self.opts)
            except Exception as e:
                raise PreviewError(str(e))
            out = parts[0]
        self.cache[key] = out
        return out

    def render(self, path, index=0, size: Tuple[int, int] = (340, 480)) -> Tuple[bytes, int]:
        """Devolve (PNG, total_de_páginas) da página `index` (0-based)."""
        if not renderer_available():
            raise PreviewError("Instale pypdfium2 e pillow para ver miniaturas: pip install pypdfium2 pillow")
        from PIL import Image
        path = Path(path)
        if path.suffix.lower() in _IMAGES:
            try:
                im = Image.open(path)
                n = getattr(im, "n_frames", 1)
                im.seek(max(0, min(index, n - 1)))
                im = im.convert("RGB")
            except Exception as e:
                raise PreviewError(f"imagem ilegível: {e}")
            im.thumbnail(size)
            return _png(im), n
        return render_pdf_page(self.pdf_for(path), index, size)

    def render_pdf(self, pdf, index=0, size=(340, 480)):
        return render_pdf_page(pdf, index, size)

    def cover_pdf(self, opts, f, index, total) -> Path:
        out = self.dir / f"cover_{abs(hash((str(f), index, total, opts.cover, opts.cover_text, opts.cover_logo)))}.pdf"
        logo = nup.load_logo(opts.cover_logo) if opts.cover_logo else None
        return pdfgen.centered_page_pdf(out, core.cover_lines(opts, Path(f), index, total), logo=logo)

    def sheets_pdf(self, path, opts) -> Tuple[Path, int]:
        """PDF com as folhas (N por folha) do arquivo e o número de folhas. Fica em cache."""
        key = ("folhas", self._key(path), opts.per_sheet, opts.paper, opts.landscape, opts.pages, opts.sheet_border)
        if key not in self.cache:
            base = self.pdf_for(path)
            out = self.dir / f"folhas_{len(self.cache)}.pdf"
            n = nup.build_sheets(base, out, opts.per_sheet, pages_spec=opts.pages, landscape=opts.landscape,
                                 paper=opts.paper, border=opts.sheet_border)
            self.cache[key] = (out, n)
        return self.cache[key]


def _png(im) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def render_pdf_page(pdf, index, size):
    import pypdfium2 as pdfium
    try:
        doc = pdfium.PdfDocument(str(pdf))
    except Exception as e:
        raise PreviewError("PDF protegido, corrompido ou ilegível" if "assword" in str(e) or "ormat" in str(e) else str(e))
    try:
        n = len(doc)
        if n == 0:
            raise PreviewError("documento sem páginas")
        page = doc[max(0, min(index, n - 1))]
        w, h = page.get_size()
        scale = min(size[0] / w, size[1] / h)
        im = page.render(scale=scale).to_pil().convert("RGB")
        return _png(im), n
    finally:
        doc.close()
