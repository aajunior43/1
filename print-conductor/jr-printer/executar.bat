@echo off
cd /d "%~dp0"
rem Abre a janela do JR Printer; arquivos passados como argumento (ex.: Enviar para) entram na fila sem imprimir nada.
if exist "%~dp0JRPrinter.exe" goto :exe
where pythonw >nul 2>nul
if errorlevel 1 goto :py
start "" pythonw jr_printer.py --gui %*
exit /b
:py
python jr_printer.py --gui %*
exit /b
:exe
start "" "%~dp0JRPrinter.exe" --gui %*
exit /b
