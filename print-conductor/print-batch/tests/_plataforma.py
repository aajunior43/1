"""Marcas de plataforma compartilhadas pelos testes.

Testes que simulam o `lp` (Linux/macOS) ou o SumatraPDF (script de shell) só rodam fora do Windows.
Motivo: num Windows o programa usa a impressora de verdade; um teste assim poderia imprimir na
impressora padrão de quem roda `GERAR_EXE.bat` ou do runner do GitHub. Por isso, no Windows, esses testes
são pulados — e nunca enviam nada à impressora.
"""
import sys
import unittest

IS_WINDOWS = sys.platform.startswith("win")
POSIX_ONLY = unittest.skipIf(
    IS_WINDOWS,
    "simula lp/SumatraPDF em Linux/macOS; no Windows este teste pularia para não imprimir de verdade")
