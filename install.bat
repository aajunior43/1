@echo off
echo ========================================
echo   Conversor de PDF para PNG - Instalacao
echo ========================================
echo.

echo Verificando se Python esta instalado...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    echo Por favor, instale Python 3.7+ de https://www.python.org/downloads/
    echo Certifique-se de marcar "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

echo Python encontrado!
echo.

echo Atualizando pip...
python -m pip install --upgrade pip

echo.
echo Instalando dependencias...
echo.

echo Instalando PyMuPDF (versao pre-compilada)...
pip install --only-binary=all PyMuPDF

echo.
echo Instalando Pillow...
pip install Pillow

echo.
echo ========================================
echo   Instalacao concluida com sucesso!
echo ========================================
echo.
echo Testando o sistema...
python teste_exemplo.py
echo.
echo Para executar o programa, use:
echo   python pdf_converter.py
echo   ou
echo   python pdf_converter_avancado.py
echo.
pause 