@echo off
setlocal
cd /d "%~dp0"
echo === JR Printer - instalacao (Windows) ===
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instalando via winget...
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
  echo Feche e abra este terminal e execute instalar.bat novamente.
  pause
  exit /b 1
)
echo Instalando dependencias opcionais (pywin32, tkinterdnd2)...
python -m pip install --upgrade pip
python -m pip install -r requirements-windows.txt
echo.
echo Instalando SumatraPDF (necessario para copias, frente e verso, papel e paginas)...
winget install -e --id SumatraPDF.SumatraPDF --accept-source-agreements --accept-package-agreements
echo.
echo Pronto. Execute executar.bat para abrir o programa.
echo (Opcional) Para Office sem Word/Excel/PowerPoint instale o LibreOffice: winget install TheDocumentFoundation.LibreOffice
pause
