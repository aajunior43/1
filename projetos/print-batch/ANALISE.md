# Análise de origem — PrintBatch

Registro de como este projeto nasceu, para servir de modelo aos próximos projetos do repositório.

## Alvo observado
- **Programa:** Print Conductor (software comercial de impressão em lote para Windows), instalador de avaliação.
- **Instalador:** Inno Setup 5.5.7 (Unicode), ~207 MB, PE32 x86.
- **SHA-256 do instalador:** `8faf38b2821ba4568f68a8b722f7304767435b3c70d2a05b07a7e48ba1affe4d`
- O instalador **não é distribuído neste repositório**.

## Método
1. Extração do instalador com `innoextract` (sem executar o programa).
2. Inspeção estática do executável principal com o **REA** (`inspect-managed-artifact`, `inspect-managed-members`).
3. Leitura das pastas e arquivos instalados para entender os recursos visíveis.

## O que foi observado
- Aplicativo **.NET Framework 4.5** com interface WPF, ~311 tipos e ~2.859 métodos; nomes **ofuscados**.
- Conversão de documentos feita por **bibliotecas comerciais** (Aspose Words/Cells/PDF, ABCpdf, EO.Pdf, pdfium,
  WW.Cad, Independentsoft.Pst, Rebex), em vez de imprimir cada formato diretamente.
- Impressão por componentes próprios (`PrintHook32/64.dll`, `GP-x86/x64.dll`) e integração com o Explorer (`ShellExt.dll`).
- Recursos visíveis nos arquivos: páginas de rosto (`coverpages/*.cover`), páginas substitutas para arquivos que
  falharam, marcadores de anexos de e-mail e conversão de ZPL para PDF.

## Limite adotado
- A análise ficou em **recursos observáveis e arquitetura geral**. O código ofuscado **não foi decompilado nem
  reconstruído**, e **nenhum código, recurso ou arte do original foi copiado**.
- O PrintBatch foi escrito do zero: usa SumatraPDF, Office/LibreOffice e CUPS para imprimir, com implementação própria
  de fila, páginas de rosto, aviso de falha, pré-visualização, plano de impressão e relatórios.
- É uma ferramenta independente, sem afiliação com o produto analisado.
