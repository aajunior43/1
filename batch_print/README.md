# PrintBatch — impressão em lote (Windows, Linux e macOS)

Imprime vários documentos de uma vez: **PDF, Word, Excel, PowerPoint, OpenDocument, RTF, HTML,
imagens, TXT e e-mails (.eml / .msg)**. Tem interface gráfica e linha de comando.

## Recursos
- Fila com arquivos e pastas (subpastas opcionais), arrastar e soltar, reordenar, remover, ordenar
  (nome/data/tamanho/tipo), filtrar por padrão (`*.pdf, *relatorio*`), salvar e carregar a fila.
- Opções: impressora, cópias, frente e verso (borda longa/curta), cor ou P&B, papel, paisagem,
  ajustar à página, intervalo de páginas.
- **Página de rosto** antes de cada arquivo (nome, pasta, caminho, tipo, nº na fila, data) com modelos
  prontos ou texto próprio.
- **Página de aviso** impressa quando um arquivo falha; o lote continua.
- **E-mails**: imprime cabeçalho + corpo e, opcionalmente, os anexos suportados.
- Progresso, cancelamento, log e **relatório** CSV/JSON. Suas escolhas ficam salvas.
- Modo **simulação** (não imprime, só mostra o que seria feito).

## Windows — instalação
1. Instale o Python 3.12 (ou use `instalar.bat`, que usa o `winget`).
2. Execute **`instalar.bat`**: instala `pywin32`, `tkinterdnd2` e o **SumatraPDF**.
3. Execute **`executar.bat`** para abrir o programa.
4. (Opcional) **`criar_atalho_enviar_para.bat`**: adiciona “Enviar para > PrintBatch” no botão direito.
5. (Opcional) **`build_exe.bat`** gera `dist\PrintBatch.exe` sem precisar de Python
   (o GitHub Actions também gera, em *Actions > Build PrintBatch (Windows) > Artifacts*).

### Como imprime no Windows
| Tipo | Caminho |
|---|---|
| Word / Excel / PowerPoint | exporta para PDF com o próprio Office (pywin32); se não houver, usa LibreOffice |
| PDF, imagens, TXT, e-mail | PDF/imagem enviado ao **SumatraPDF** com todas as opções |
| .msg | lido pelo Outlook (pywin32) |

Sem o SumatraPDF o programa ainda imprime pelo verbo `printto` do Windows, **mas sem cópias, frente e
verso, papel e páginas** (aparece um aviso).

## Linha de comando
```bat
python batch_print.py --list-printers
python batch_print.py "C:\Docs" -r -p "Minha Impressora" -n 2 --duplex long --cover filename-folder --failed-page --report fila.csv
python batch_print.py *.docx --sort date --filter "*relatorio*" --dry-run
```
Sem argumentos abre a interface gráfica. Veja `python batch_print.py --help`.

## Linux / macOS
Funciona via CUPS (`lp`); Office converte com LibreOffice. A GUI precisa de `python3-tk`.

## Testes
```
python -m unittest discover -s tests
```
