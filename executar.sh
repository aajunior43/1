#!/bin/bash

# Organizador de Arquivos com IA - Versão Avançada
# Script de execução para Linux/Mac

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir cabeçalho
print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║          🗂️  ORGANIZADOR DE ARQUIVOS COM IA                  ║"
    echo "║                    Versão Avançada 2.0.0                    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo
}

# Função para verificar Python
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}❌ Python não encontrado!${NC}"
        echo
        echo "Por favor, instale o Python 3.8 ou superior:"
        echo "- Ubuntu/Debian: sudo apt install python3"
        echo "- CentOS/RHEL: sudo yum install python3"
        echo "- macOS: brew install python3"
        echo
        exit 1
    fi
    
    # Verificar versão do Python
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    MINOR_VERSION=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$MAJOR_VERSION" -lt 3 ] || ([ "$MAJOR_VERSION" -eq 3 ] && [ "$MINOR_VERSION" -lt 8 ]); then
        echo -e "${RED}❌ Python $PYTHON_VERSION encontrado, mas é necessário Python 3.8+${NC}"
        echo
        exit 1
    fi
    
    echo -e "${GREEN}✅ Python $PYTHON_VERSION encontrado${NC}"
}

# Função para verificar arquivos
check_files() {
    if [ ! -f "main.py" ]; then
        echo -e "${RED}❌ Arquivo main.py não encontrado!${NC}"
        echo
        echo "Certifique-se de estar no diretório correto do projeto."
        echo
        exit 1
    fi
    
    echo -e "${GREEN}✅ Arquivos do projeto encontrados${NC}"
}

# Função para criar diretórios necessários
setup_directories() {
    mkdir -p logs
    mkdir -p backups
    mkdir -p temp
    echo -e "${GREEN}✅ Diretórios configurados${NC}"
}

# Função para executar aplicação
run_application() {
    echo -e "${YELLOW}🚀 Iniciando aplicação...${NC}"
    echo
    
    $PYTHON_CMD main.py
    
    if [ $? -eq 0 ]; then
        echo
        echo -e "${GREEN}✅ Aplicação finalizada com sucesso!${NC}"
    else
        echo
        echo -e "${RED}❌ Erro na execução da aplicação!${NC}"
        echo
        echo "Possíveis soluções:"
        echo "1. Verifique se todos os arquivos estão presentes"
        echo "2. Execute com permissões adequadas"
        echo "3. Verifique se o Python 3.8+ está instalado"
        echo "4. Verifique se tkinter está instalado (sudo apt install python3-tk no Ubuntu)"
        echo
        exit 1
    fi
}

# Função principal
main() {
    print_header
    check_python
    check_files
    setup_directories
    echo
    run_application
}

# Executar função principal
main