"""Testes do Organizador de Arquivos (rodam numa cópia temporária do projeto, sem sujar a pasta de origem).

Cobrem os defeitos encontrados nesta revisão: importações quebradas, configuração sem método `load`/`save`,
temas com chaves erradas, layout misto pack/grid, logs, atributo de arquivo oculto exclusivo do Windows
e a execução completa (análise → organização → backup → restauração).
"""
import os
import re
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

ORIG = Path(__file__).resolve().parent.parent


def copia_do_projeto():
    destino = Path(tempfile.mkdtemp(prefix="org-teste-")) / "projeto"
    shutil.copytree(ORIG, destino, ignore=shutil.ignore_patterns("__pycache__", "backups", "logs", "tests", "*.pyc"))
    return destino


PROJ = copia_do_projeto()
sys.path.insert(0, str(PROJ))
sys.path.insert(0, str(PROJ / "src"))

from config.settings import config, THEMES            # noqa: E402
from src.core.organizer import AdvancedOrganizer      # noqa: E402
from src.utils.backup import BackupManager            # noqa: E402
from src.utils import validator                       # noqa: E402

try:
    import tkinter  # noqa: F401
    HAS_TK = True
except ImportError:
    HAS_TK = False


class ConfiguracaoTests(unittest.TestCase):
    def test_config_tem_os_metodos_usados_pela_interface(self):
        self.assertTrue(callable(config.save_settings))
        self.assertTrue(callable(config.get))

    def test_salvar_e_ler_tema(self):
        config.set("theme", "dark")
        self.assertTrue(config.save_settings())
        self.assertEqual(config.get("theme"), "dark")
        config.set("theme", "light")

    def test_temas_tem_as_chaves_que_a_interface_usa(self):
        usadas = set()
        for linha in (PROJ / "src" / "gui" / "main_window.py").read_text(encoding="utf-8").splitlines():
            usadas.update(re.findall(r'theme\["([a-z_]+)"\]', linha))
        self.assertTrue(usadas)
        for nome in ("light", "dark"):
            self.assertTrue(usadas <= set(THEMES[nome]), (nome, usadas - set(THEMES[nome])))

    def test_nenhuma_importacao_quebrada(self):
        """Nenhum `from ..config` ou `src.config` (a pasta de configuração fica na raiz)."""
        for arq in (PROJ).rglob("*.py"):
            texto = arq.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("src.config", texto, arq)
            self.assertIsNone(re.search(r"from \.\.+config", texto), arq)


class LogTests(unittest.TestCase):
    def test_conteudo_do_log_e_texto(self):
        from src.utils.logger import logger
        self.assertIsInstance(logger.get_log_content(5), str)
        logger.info("linha de teste")
        self.assertIn("linha de teste", logger.get_log_content(50))


class ArquivosTests(unittest.TestCase):
    def test_oculto_em_sistemas_sem_atributo_do_windows(self):
        d = Path(tempfile.mkdtemp())
        (d / ".segredo").write_text("x")
        (d / "visivel.txt").write_text("x")
        self.assertTrue(validator._is_hidden(d / ".segredo", (d / ".segredo").stat()))
        self.assertFalse(validator._is_hidden(d / "visivel.txt", (d / "visivel.txt").stat()))

    def test_info_de_arquivo_funciona_no_linux(self):
        v = validator.FileValidator()
        d = Path(tempfile.mkdtemp())
        f = d / "a.pdf"
        f.write_bytes(b"%PDF")
        info = v.get_file_info(f)
        self.assertEqual(info["extension"], ".pdf")
        self.assertFalse(info["is_hidden"])


class OrganizacaoTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp()) / "bagunca"
        self.base.mkdir()
        self.amostra = {"contrato.pdf": b"%PDF-1.4", "foto.jpg": b"\xff\xd8", "planilha.xlsx": b"PK",
                        "notas.txt": b"oi", "musica.mp3": b"ID3", "apresentacao.pptx": b"PK", "video.mp4": b"0000",
                        "contrato (1).pdf": b"%PDF-1.4 b"}
        for nome, dados in self.amostra.items():
            (self.base / nome).write_bytes(dados)

    def test_analise_por_tipo_sugere_todos_os_arquivos(self):
        r = AdvancedOrganizer().analyze_folder(str(self.base), "por_tipo")
        self.assertTrue(r["success"], r.get("error"))
        self.assertEqual(len(r["suggestions"]), len(self.amostra))

    def test_todos_os_modos_de_organizacao(self):
        base = Path(tempfile.mkdtemp()) / "modos"
        base.mkdir()
        for i, nome in enumerate(["a.pdf", "b.pdf", "c.jpg", "d.txt", "relatorio final.docx", "zz.mp3"]):
            f = base / nome
            f.write_bytes(b"x" * (i + 1) * 100)
            t = time.time() - i * 86400 * 40
            os.utime(f, (t, t))
        for modo in ("por_tipo", "por_data", "por_nome"):
            r = AdvancedOrganizer().analyze_folder(str(base), modo)
            self.assertTrue(r["success"], (modo, r.get("error")))
            self.assertEqual(len(r["suggestions"]), 6, modo)

    def test_executa_faz_backup_e_restaura(self):
        org = AdvancedOrganizer()
        sugestoes = org.analyze_folder(str(self.base), "por_tipo")["suggestions"]
        res = org.execute_organization(sugestoes, create_backup=True)
        self.assertTrue(res["success"], res)
        self.assertEqual([p for p in self.base.iterdir() if p.is_file()], [])        # nada solto na raiz
        pastas = {p.name for p in self.base.iterdir() if p.is_dir()}
        self.assertTrue({"Documentos", "Imagens"} <= pastas, pastas)
        self.assertTrue((self.base / "Documentos" / "contrato (1).pdf").exists())  # nome repetido não sobrescreve

        bm = BackupManager()
        backups = bm.list_backups()
        self.assertTrue(backups)
        bid = backups[0].get("backup_id") or backups[0].get("id") or backups[0].get("timestamp")
        self.assertTrue(bm.restore_backup(bid))
        self.assertEqual(sorted(p.name for p in self.base.iterdir() if p.is_file()), sorted(self.amostra))


@unittest.skipUnless(HAS_TK and os.environ.get("DISPLAY"), "precisa de tkinter e display (use xvfb-run)")
class InterfaceTests(unittest.TestCase):
    def test_janela_abre_sem_erro(self):
        from src.gui.main_window import AdvancedOrganizerGUI
        app = AdvancedOrganizerGUI()
        try:
            app.root.update()
            for tema in ("light", "dark"):
                app.apply_theme(tema)
                app.root.update()
        finally:
            app.root.destroy()


if __name__ == "__main__":
    unittest.main()
