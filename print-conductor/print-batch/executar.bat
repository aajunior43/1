@echo off
cd /d "%~dp0"
rem Abre a janela do PrintBatch; arquivos passados como argumento (ex.: Enviar para) entram na fila sem imprimir nada.
if exist "%~dp0PrintBatch.exe" goto :exe
where pythonw >nul 2>nul
if errorlevel 1 goto :py
start "" pythonw batch_print.py --gui %*
exit /b
:py
python batch_print.py --gui %*
exit /b
:exe
start "" "%~dp0PrintBatch.exe" --gui %*
exit /b
