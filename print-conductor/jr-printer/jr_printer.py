#!/usr/bin/env python3
"""Ponto de entrada do JR Printer. Sem argumentos abre a interface gráfica."""
import sys
import traceback

from jrprinter import core
from jrprinter.cli import main, setup_streams


def _excepthook(kind, value, tb):
    text = "".join(traceback.format_exception(kind, value, tb))
    core.log_error(text)
    try:
        sys.stderr.write(text)
    except Exception:
        pass


if __name__ == "__main__":
    setup_streams()
    sys.excepthook = _excepthook
    sys.exit(main())
