# Engenharia reversa — apps analisados e projetos criados

Cada **app analisado** tem uma pasta própria na raiz. Dentro dela ficam o registro da análise (`ANALISE.md`) e,
em pastas à parte, os **projetos criados** a partir dela. Projetos que não nasceram de análise ficam em `outros/`, e as ferramentas de apoio em `ferramentas/`.

| App analisado | Projeto(s) criado(s) |
|---|---|
| [`print-conductor/`](print-conductor) — impressão em lote para Windows ([análise](print-conductor/ANALISE.md)) | [`jr-printer/`](print-conductor/jr-printer) — **JR Printer**: impressão em lote para Windows, Linux e macOS, com fila organizável, pré-visualização, plano de impressão, páginas de rosto e relatórios |

| Ferramentas | O que é |
|---|---|
| [`ferramentas/rea`](ferramentas/rea) | **REA** (Reverse Engineer Anything) — a ferramenta usada nas análises; cópia do repositório oficial, com a origem em [`UPSTREAM.md`](ferramentas/rea/UPSTREAM.md) |

| Outros projetos | O que é |
|---|---|
| [`outros/organizador-arquivos`](outros/organizador-arquivos) | Organizador de Arquivos com IA (organização, filtros, backup, logs) |

## Convenção para novos apps
```
<app-analisado>/
├── README.md        o que é o app e o que foi criado a partir dele
├── ANALISE.md       alvo, método, achados e limites adotados
└── <projeto>/       o projeto criado (README, código, tests/, scripts)
```
- Uma pasta por app analisado, na raiz; cada projeto criado fica numa subpasta própria dentro dela.
- Workflows do GitHub ficam em `.github/workflows/`, com `paths:` e `working-directory:` apontando para a pasta do projeto.
- Binários de terceiros (instaladores, executáveis analisados) **não** entram no repositório; registre nome,
  versão e SHA-256 em `ANALISE.md`.
- Análise de programas de terceiros: apenas observação e arquitetura geral; sem copiar código, recursos ou arte.
