# batch_print

Impressão em lote por linha de comando (CUPS `lp`). Imprime PDF, TXT, imagens,
documentos Office/HTML (convertidos com LibreOffice) e e-mails `.eml`.

```bash
python3 batch_print.py --list-printers
python3 batch_print.py pasta/ -r -p Impressora -n 2 --duplex --paper A4
python3 batch_print.py pasta/ --cover filename-folder --failed-page --report fila.csv
python3 batch_print.py pasta/ --filter '*.pdf' --sort date --reverse --dry-run
```

| Opção | O que faz |
|---|---|
| `-r` | entra nas subpastas |
| `--filter GLOB` | só nomes que casam (repetível) |
| `--sort name\|date\|size\|type`, `--reverse` | ordem da fila |
| `--cover filename\|filename-folder\|full\|number` | página de rosto antes de cada arquivo |
| `--failed-page` | imprime um aviso quando um arquivo falha |
| `--report arq.csv\|.json` | relatório com status de cada arquivo |
| `--dry-run` | simula sem imprimir |
| `-n`, `--duplex`, `--pages`, `--paper`, `--landscape`, `--fit`, `--color/--mono` | opções de impressão |

Requisitos: Python 3, CUPS (`lp`) e, para Office, LibreOffice. Sem dependências Python extras.
