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
echo Instalando dependencias obrigatorias (requirements.txt)...
python -m pip install -r requirements.txt

echo.
echo Instalando recursos opcionais (conversor de PDF)...
pip install --only-binary=all PyMuPDF
pip install Pillow

echo.
echo ========================================
echo   Instalacao concluida com sucesso!
echo ========================================
echo.
echo Verificando a instalacao...
python -c "import psutil, tkinter; print('Dependencias OK')"
echo.
echo Para executar o programa, use:
echo   executar.bat
echo   ou
echo   python main.py
echo.
pause 