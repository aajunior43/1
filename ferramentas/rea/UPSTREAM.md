# REA — origem desta cópia

Cópia do projeto **REA (Reverse Engineer Anything)**, a ferramenta usada nas análises de engenharia reversa deste repositório.

- **Projeto oficial:** https://github.com/morluto/rea (site: https://rea.tools/, npm: `rea-agents`)
- **Commit copiado:** `93c620c3e7c401be40b71c480518147c76ade4dc` (versão do pacote: 6.5.0)
- **Licença:** MIT — veja `LICENSE`, `THIRD_PARTY_NOTICES.md` e `licenses/`. Os créditos e avisos originais foram mantidos.
- **Uso responsável:** leia `DISCLAIMER.md` e `SECURITY.md` antes de usar.

## O que não veio na cópia
- O histórico do Git (só os arquivos do commit acima).
- Os **submódulos** de `third_party/` (binwalk, unblob, wakaru, ghidra-nativeaot, jadx-headless-mcp etc.): as pastas
  estão vazias. Para obtê-los, use o repositório oficial: `git clone --recurse-submodules https://github.com/morluto/rea`.

## Como usar nas análises
Sem instalar nada aqui, direto do npm:
```bash
npx -y rea-agents@latest --help
npx -y rea-agents@latest inspect-managed-artifact caminho/do/arquivo.exe --json
```
Para rodar esta cópia: `npm ci` e `npm run build` dentro desta pasta (Node 22.19+, 24.11+ ou 26+).

## Atualizar
Esta pasta é uma fotografia. Para atualizar, baixe o commit mais novo do repositório oficial e substitua o conteúdo,
atualizando o commit registrado acima.
