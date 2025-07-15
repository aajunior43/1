@echo off
chcp 65001 >nul
color 0A
title Organizador de Arquivos com IA - Versão Avançada

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║          🗂️  ORGANIZADOR DE ARQUIVOS COM IA                  ║
echo ║                    Versão Avançada 2.0.0                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 🚀 Iniciando aplicação...
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python não encontrado!
    echo.
    echo Por favor, instale o Python 3.8 ou superior:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Verificar se o arquivo principal existe
if not exist "main.py" (
    echo ❌ Arquivo main.py não encontrado!
    echo.
    echo Certifique-se de estar no diretório correto do projeto.
    echo.
    pause
    exit /b 1
)

REM Executar a aplicação
echo ✅ Python encontrado. Executando aplicação...
echo.
python main.py

REM Verificar se houve erro na execução
if errorlevel 1 (
    echo.
    echo ❌ Erro na execução da aplicação!
    echo.
    echo Possíveis soluções:
    echo 1. Verifique se todos os arquivos estão presentes
    echo 2. Execute como administrador se necessário
    echo 3. Verifique se o Python 3.8+ está instalado
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Aplicação finalizada com sucesso!
echo.
pause