"""Automação do Office (Word, Excel, PowerPoint, Outlook) com objetos simulados.

Não há Office aqui, então `pythoncom` e `win32com.client` são substituídos por objetos que registram cada
chamada. Isto confere se o programa chama o modelo de objetos certo, com os argumentos certos e na ordem
certa, e se fecha o aplicativo mesmo quando a conversão falha. A compatibilidade real com o Office é
validada só no Windows (diagnóstico e primeira impressão).
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from printbatch import core


class Registro:
    def __init__(self):
        self.itens = []

    def add(self, *a):
        self.itens.append(a)


class FakeDoc:
    def __init__(self, reg, falha_export=False):
        self.reg, self.falha_export = reg, falha_export

    def ExportAsFixedFormat(self, saida, formato):
        self.reg.add("export", formato)
        if self.falha_export:
            return
        Path(saida).write_bytes(b"%PDF-1.4 simulado")

    def Close(self, salvar):
        self.reg.add("close", salvar)


class FakeCollection:
    def __init__(self, reg, falha=False, falha_export=False):
        self.reg, self.falha, self.falha_export = reg, falha, falha_export

    def Open(self, caminho, **kw):
        self.reg.add("open", Path(caminho).name, kw)
        if self.falha:
            raise RuntimeError("documento protegido por senha")
        return FakeDoc(self.reg, self.falha_export)


class FakeApp:
    def __init__(self, reg, nome, falha_open=False, falha_export=False):
        self.reg, self.nome = reg, nome
        self.Visible = True
        self.DisplayAlerts = None
        self.AutomationSecurity = None
        self.Documents = FakeCollection(reg, falha_open, falha_export)
        self.Workbooks = FakeCollection(reg, falha_open)
        self.Presentations = FakeCollection(reg, falha_open)

    def Quit(self):
        self.reg.add("quit", self.nome)


class FakeWorkbook(FakeDoc):
    def ExportAsFixedFormat(self, tipo, saida):
        self.reg.add("export", tipo)
        Path(saida).write_bytes(b"%PDF-1.4 planilha")


class FakePresentation:
    def __init__(self, reg):
        self.reg = reg

    def SaveAs(self, saida, formato):
        self.reg.add("saveas", formato)
        Path(saida).write_bytes(b"%PDF-1.4 slides")

    def Close(self):
        self.reg.add("close_pres")


def fake_com(reg, **opts):
    apps = {}

    def DispatchEx(prog):
        app = FakeApp(reg, prog, **opts)
        if prog == "Excel.Application":
            app.Workbooks = type("W", (), {"Open": lambda self, c, **kw: (reg.add("open", Path(c).name, kw) or FakeWorkbook(reg))})()
        if prog == "PowerPoint.Application":
            app.Presentations = type("P", (), {"Open": lambda self, c, **kw: (reg.add("open", Path(c).name, kw) or FakePresentation(reg))})()
        apps[prog] = app
        return app

    client = mock.Mock()
    client.DispatchEx = DispatchEx
    client.Dispatch = lambda prog: outlook_item(reg) if prog == "Outlook.Application" else None
    client.apps = apps                                  # para o teste conferir as propriedades do app
    return client


def outlook_item(reg):
    class Anexos:
        def __init__(self, nomes):
            self.nomes = nomes
            self.Count = len(nomes)

        def Item(self, i):
            return type("A", (), {"FileName": self.nomes[i - 1]})()

    item = type("Mail", (), {})()
    item.SenderName, item.To, item.Subject = "Ana", "bruno@x.com", "Proposta"
    item.SentOn, item.Body = "2026-10-01 10:00", "Segue a proposta."
    item.Attachments = Anexos(["proposta.pdf", "tabela.xlsx"])
    session = type("S", (), {})()
    session.OpenSharedItem = lambda caminho: (reg.add("outlook", Path(caminho).name) or item)
    app = type("O", (), {})()
    app.Session = session
    return app


class OfficeSimuladoTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.reg = Registro()

    def modulos(self, client):
        pythoncom = mock.Mock()
        pkg = mock.Mock()
        pkg.client = client
        return {"pythoncom": pythoncom, "win32com": pkg, "win32com.client": client}

    def converter(self, arquivo, client):
        doc = self.d / arquivo
        doc.write_bytes(b"PK")
        with mock.patch.dict(sys.modules, self.modulos(client)):
            return core.office_via_com_inprocess(doc, self.d)

    def test_word_exporta_pdf_com_formato_17_e_fecha_o_app(self):
        out = self.converter("carta.docx", fake_com(self.reg))
        self.assertEqual(out.name, "carta.pdf")
        self.assertTrue(out.read_bytes().startswith(b"%PDF"))
        self.assertIn(("export", 17), self.reg.itens)
        self.assertIn(("quit", "Word.Application"), self.reg.itens)
        abertura = next(i for i in self.reg.itens if i[0] == "open")
        self.assertEqual(abertura[2], {"ReadOnly": True, "AddToRecentFiles": False})

    def test_excel_exporta_tipo_pdf_zero(self):
        out = self.converter("planilha.xlsx", fake_com(self.reg))
        self.assertTrue(out.exists())
        self.assertIn(("export", 0), self.reg.itens)
        self.assertIn(("quit", "Excel.Application"), self.reg.itens)

    def test_powerpoint_salva_formato_32(self):
        out = self.converter("slides.pptx", fake_com(self.reg))
        self.assertTrue(out.exists())
        self.assertIn(("saveas", 32), self.reg.itens)
        self.assertIn(("quit", "PowerPoint.Application"), self.reg.itens)

    def test_app_e_fechado_mesmo_quando_o_documento_falha(self):
        client = fake_com(self.reg, falha_open=True)
        with self.assertRaisesRegex(RuntimeError, "protegido"):
            self.converter("protegido.docx", client)
        self.assertIn(("quit", "Word.Application"), self.reg.itens)     # não deixa o Word aberto

    def test_office_que_nao_gera_pdf_e_erro_claro(self):
        with self.assertRaisesRegex(RuntimeError, "não gerou o PDF"):
            self.converter("vazio.docx", fake_com(self.reg, falha_export=True))

    def test_tipo_sem_suporte_no_com(self):
        with self.assertRaisesRegex(RuntimeError, "não suportado"):
            self.converter("x.rtfx", fake_com(self.reg))

    def test_alertas_e_macros_desligados(self):
        client = fake_com(self.reg)
        self.converter("carta.docx", client)
        word = client.apps["Word.Application"]
        self.assertEqual(word.DisplayAlerts, 0)                 # wdAlertsNone
        self.assertEqual(word.AutomationSecurity, 3)            # msoAutomationSecurityForceDisable (sem macros)
        self.assertFalse(word.Visible)
        client2 = fake_com(self.reg)
        self.converter("planilha.xlsx", client2)
        excel = client2.apps["Excel.Application"]
        self.assertFalse(excel.DisplayAlerts)
        self.assertEqual(excel.AutomationSecurity, 3)
        client3 = fake_com(self.reg)
        self.converter("slides.pptx", client3)
        self.assertEqual(client3.apps["PowerPoint.Application"].DisplayAlerts, 1)   # ppAlertsNone

    def test_outlook_le_o_msg_com_anexos(self):
        msg = self.d / "mensagem.msg"
        msg.write_bytes(b"x")
        with mock.patch.dict(sys.modules, self.modulos(fake_com(self.reg))):
            texto, _ = core.msg_to_text(msg)
        self.assertIn("Assunto: Proposta", texto)
        self.assertIn("Segue a proposta.", texto)
        self.assertIn("Anexos: proposta.pdf, tabela.xlsx", texto)
        self.assertIn(("outlook", "mensagem.msg"), self.reg.itens)

    def test_no_windows_o_word_vem_antes_do_libreoffice(self):
        ordem = []
        with mock.patch.object(core, "IS_WINDOWS", True), \
                mock.patch.object(core, "office_via_com", side_effect=lambda s, o: ordem.append("com") or (self.d / "x.pdf")), \
                mock.patch.object(core, "office_via_libreoffice", side_effect=lambda s, o: ordem.append("lo")):
            core.office_to_pdf(self.d / "a.docx", self.d)
        self.assertEqual(ordem, ["com"])                                   # se o COM funcionou, nem tenta o LibreOffice

    def test_no_windows_sem_office_usa_libreoffice(self):
        ordem = []
        with mock.patch.object(core, "IS_WINDOWS", True), \
                mock.patch.object(core, "office_via_com", side_effect=RuntimeError("Word não instalado")), \
                mock.patch.object(core, "office_via_libreoffice", side_effect=lambda s, o: ordem.append("lo") or (self.d / "y.pdf")):
            out = core.office_to_pdf(self.d / "a.docx", self.d)
        self.assertEqual(ordem, ["lo"])
        self.assertEqual(out.name, "y.pdf")


if __name__ == "__main__":
    unittest.main()
