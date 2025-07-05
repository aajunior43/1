# 📄 Conversor Moderno de PDF para PNG - Instruções de Uso

## 🚀 Instalação Rápida

### Opção 1: Instalação Automática (Windows)
1. Clique duas vezes no arquivo `install.bat`
2. Aguarde a instalação das dependências
3. Execute `executar.bat` para iniciar o programa

### Opção 2: Instalação Manual
1. Abra o terminal/prompt de comando
2. Navegue até a pasta do projeto
3. Execute: `pip install -r requirements.txt`
4. Execute: `python pdf_converter.py`

## 📋 Pré-requisitos

- **Python 3.7 ou superior**
- **4GB RAM** (recomendado)
- **Espaço em disco** suficiente para as imagens

## 🎯 Como Usar

### 1. Selecionar Arquivos PDF
- Clique em **"📁 Arraste e Solte ou Clique para Selecionar PDFs"**
- Escolha um ou mais arquivos PDF.
- Você pode selecionar múltiplos arquivos de uma vez.

### 2. Configurar Opções de Conversão
- **Resolução (DPI)**: Ajuste a qualidade da imagem. Valores maiores resultam em melhor qualidade e maior tamanho de arquivo.
- **Formato de Saída**: Escolha entre PNG, JPG ou WEBP.
- **Qualidade da Imagem (para JPG/WEBP)**: Um slider aparecerá dinamicamente para ajustar a qualidade (1-100) quando JPG ou WEBP for selecionado.

### 3. Iniciar Conversão
- Clique em **"🚀 Converter PDFs"** para iniciar o processo.
- Acompanhe o progresso na barra.
- Veja os detalhes no log de conversão.
- Use **"🧹 Limpar Tudo"** para resetar todos os campos e resultados.

## 📁 Estrutura de Saída

Para cada PDF convertido, será criada uma pasta com o nome do arquivo PDF:

```
pasta_saida/
├── documento1/
│   ├── pagina_001.png
│   ├── pagina_002.png
│   └── ...
├── documento2/
│   ├── pagina_001.png
│   └── ...
└── ...
```

## ✨ Características da Interface Moderna

### 🎨 Design Atraente
- Interface escura moderna
- Ícones intuitivos
- Cores harmoniosas
- Layout responsivo

### 🔧 Funcionalidades Avançadas
- Log detalhado com timestamps
- Barra de progresso em tempo real

## ⚠️ Solução de Problemas

### Erro: "ModuleNotFoundError: No module named 'fitz'"
```bash
pip install --only-binary=all PyMuPDF
```

### Erro: "ModuleNotFoundError: No module named 'PIL'"
```bash
pip install Pillow
```

### PDF não abre
- Verifique se o arquivo não está corrompido
- Tente abrir o PDF em outro programa
- Verifique se o PDF não está protegido por senha

### Conversão muito lenta
- Reduza o DPI (150 ou 300)
- Feche outros programas
- Verifique se há espaço suficiente em disco

### Erro de permissão
- Execute como administrador
- Verifique permissões da pasta de saída
- Tente uma pasta diferente

## 📊 Dicas de Uso

### Para Melhor Qualidade
- Use DPI 300 ou superior
- Certifique-se de que o PDF original é de boa qualidade
- Use PNG para preservar transparência

### Para Conversões Rápidas
- Use DPI 150 ou 300
- Converta poucos arquivos por vez
- Feche outros programas

### Para Economizar Espaço
- Use DPI 150 ou 300
- Considere usar JPG em vez de PNG (se não precisar de transparência)

## 🆘 Suporte

Se encontrar problemas:

1. **Verifique as dependências**: `pip list`
2. **Atualize o pip**: `pip install --upgrade pip`
3. **Reinstale as dependências**: `pip install -r requirements.txt --force-reinstall`

## 📝 Arquivos do Projeto

- `pdf_converter_gradio.py` - Programa principal
- `install.bat` - Script de instalação automática
- `executar.bat` - Script para executar o programa
- `requirements.txt` - Dependências necessárias
- `INSTRUCOES.md` - Este arquivo de instruções

## 🎉 Novidades da Versão Moderna

- ✅ Interface escura moderna e atraente
- ✅ Ícones intuitivos em todas as ações
- ✅ Log detalhado com opção de salvar
- ✅ Barra de progresso melhorada
- ✅ Status em tempo real
- ✅ Qualidade de imagem ajustável para JPG/WEBP (slider dinâmico)
- ✅ Limpeza completa dos campos ao clicar em "Limpar Tudo"
- ✅ Melhor organização visual 
