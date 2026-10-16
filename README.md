# Projetos

Repositório de projetos independentes. **Cada projeto vive na própria pasta dentro de `projetos/`**, com README,
dependências e testes próprios. Vários nascem de análise (engenharia reversa observacional) de um programa existente,
seguida de uma implementação própria.

| Projeto | O que é | Origem |
|---|---|---|
| [`projetos/print-batch`](projetos/print-batch) | **PrintBatch** — impressão em lote para Windows/Linux/macOS: fila organizável, pré-visualização, plano de impressão, páginas de rosto, relatório. | Análise de um programa de impressão em lote ([`ANALISE.md`](projetos/print-batch/ANALISE.md)) |
| [`projetos/organizador-arquivos`](projetos/organizador-arquivos) | Organizador de Arquivos com IA (organização, filtros, backup, logs). | Projeto original |

## Convenção para novos projetos
```
projetos/<nome-do-projeto>/
├── README.md        o que é, como instalar e usar
├── ANALISE.md       (se houver análise) alvo, método, achados e limites adotados
├── tests/           testes automáticos
└── ...              código, requisitos, scripts
```
- Uma pasta por projeto; nada de arquivos soltos na raiz do repositório.
- Workflows do GitHub ficam em `.github/workflows/`, com `paths:` e `working-directory:` apontando para a pasta do projeto.
- Binários de terceiros (instaladores, executáveis analisados) **não** entram no repositório; registre o nome,
  a versão e o SHA-256 em `ANALISE.md`.
- Análise de programas de terceiros: apenas observação e arquitetura geral; sem copiar código, recursos ou arte.
