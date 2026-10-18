@echo off
rem Testa o sistema (impressoras, SumatraPDF, Office, conversao...) e salva diagnostico.txt nesta pasta.
rem Para imprimir tambem uma pagina de teste: DIAGNOSTICO.bat "Nome da Impressora"
cd /d "%~dp0"
set "PRN=%~1"
if exist "%~dp0JRPrinter.exe" goto :exe
if "%PRN%"=="" goto :py_sem
python jr_printer.py --diagnostico --imprimir-teste "%PRN%"
goto :fim
:py_sem
python jr_printer.py --diagnostico
goto :fim
:exe
if "%PRN%"=="" goto :exe_sem
"%~dp0JRPrinter.exe" --diagnostico --imprimir-teste "%PRN%"
goto :fim
:exe_sem
"%~dp0JRPrinter.exe" --diagnostico
:fim
echo.
pause
