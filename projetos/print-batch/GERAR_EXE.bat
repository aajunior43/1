@echo off
setlocal EnableExtensions
title PrintBatch - gerar executavel
rem ============================================================================
rem  GERAR_EXE.bat  -  baixa, instala tudo e gera o PrintBatch.exe no Windows.
rem  Pode ser copiado SOZINHO para qualquer pasta e executado com duplo clique.
rem  Requer Windows 10 ou 11 e internet. Nao precisa de administrador.
rem ============================================================================

set "REPO_USER=aajunior43"
set "REPO_NAME=1"
set "PROJ=projetos\print-batch"
rem Ramos tentados em ordem (depois do merge do Pull Request, main passa a funcionar)
set "BRANCHES=main ccr-d29b596d-8x3y7z"
set "PY_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
set "SUMATRA_VER=3.5.2"
set "WORK=%USERPROFILE%\PrintBatch-build"
set "OUTDIR=%~dp0"
set "PSX=powershell -NoProfile -ExecutionPolicy Bypass -Command"
set "PSPRE=$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;"
set "MSG="

echo.
echo ==============================================================
echo   PrintBatch - gerador do executavel PrintBatch.exe
echo ==============================================================
echo.
if not exist "%WORK%" mkdir "%WORK%"
if not exist "%WORK%\downloads" mkdir "%WORK%\downloads"

rem ---------------------------------------------------------------- 1. Python
echo [1/6] Procurando o Python 3.9 ou superior com Tkinter...
call :findpy
if defined PY goto :py_ok

echo      Python nao encontrado. Instalando pelo winget...
where winget >nul 2>nul
if not errorlevel 1 winget install -e --id Python.Python.3.12 --scope user --silent --accept-source-agreements --accept-package-agreements
call :findpy
if defined PY goto :py_ok

echo      Baixando o instalador oficial do python.org...
%PSX% "%PSPRE% Invoke-WebRequest -UseBasicParsing -Uri '%PY_URL%' -OutFile '%WORK%\downloads\python-setup.exe'"
if exist "%WORK%\downloads\python-setup.exe" start /wait "" "%WORK%\downloads\python-setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_tcltk=1 Include_launcher=0
call :findpy
if defined PY goto :py_ok
set "MSG=Nao foi possivel instalar o Python automaticamente. Instale o Python 3.12 em https://www.python.org/downloads/ marcando Add python.exe to PATH e execute este arquivo de novo."
goto :fail
:py_ok
echo      Usando: %PY%

rem ---------------------------------------------------------- 2. Codigo-fonte
echo.
echo [2/6] Obtendo o codigo-fonte do PrintBatch...
set "SRC="
if exist "%~dp0batch_print.py" if exist "%~dp0printbatch\core.py" set "SRC=%~dp0"
if defined SRC echo      Usando a pasta local deste arquivo.
if defined SRC goto :src_ok

if exist "%WORK%\src" rmdir /s /q "%WORK%\src"
mkdir "%WORK%\src"
for %%B in (%BRANCHES%) do if not defined SRC call :getbranch %%B
if defined SRC goto :src_ok
set "MSG=Nao foi possivel baixar o codigo do GitHub. Verifique a internet. Se o repositorio for privado, instale o Git for Windows, faca login e tente de novo."
goto :fail
:src_ok
if not exist "%SRC%\batch_print.py" set "MSG=batch_print.py nao encontrado na pasta do codigo."
if not exist "%SRC%\batch_print.py" goto :fail
echo      Codigo em: %SRC%

rem --------------------------------------------------- 3. Ambiente + pacotes
echo.
echo [3/6] Criando ambiente virtual e instalando pacotes. Pode demorar...
set "VENV=%WORK%\venv"
if exist "%VENV%\Scripts\python.exe" goto :venv_ok
%PY% -m venv "%VENV%"
if errorlevel 1 set "MSG=Falha ao criar o ambiente virtual."
if errorlevel 1 goto :fail
:venv_ok
set "VPY=%VENV%\Scripts\python.exe"
"%VPY%" -m pip install --upgrade pip
"%VPY%" -m pip install --upgrade pyinstaller pywin32 tkinterdnd2 pypdfium2 pillow
if errorlevel 1 set "MSG=Falha ao instalar os pacotes Python. Verifique a internet."
if errorlevel 1 goto :fail

rem --------------------------------------------------------- 4. SumatraPDF
echo.
echo [4/6] Baixando o SumatraPDF, usado para imprimir com todas as opcoes...
set "SUMATRA="
set "SZIP=%WORK%\downloads\sumatra.zip"
if exist "%SZIP%" del /q "%SZIP%"
%PSX% "%PSPRE% try { Invoke-WebRequest -UseBasicParsing -Uri 'https://www.sumatrapdfreader.org/dl/rel/%SUMATRA_VER%/SumatraPDF-%SUMATRA_VER%-64.zip' -OutFile '%SZIP%' } catch { exit 1 }"
if not exist "%SZIP%" goto :sumatra_done
if exist "%WORK%\sumatra" rmdir /s /q "%WORK%\sumatra"
%PSX% "Expand-Archive -Force '%SZIP%' '%WORK%\sumatra'"
for %%F in ("%WORK%\sumatra\SumatraPDF-*.exe") do copy /y "%%~fF" "%WORK%\SumatraPDF.exe" >nul 2>nul
if exist "%WORK%\SumatraPDF.exe" set "SUMATRA=%WORK%\SumatraPDF.exe"
:sumatra_done
if defined SUMATRA echo      SumatraPDF sera embutido no executavel.
if not defined SUMATRA echo      AVISO: nao foi possivel baixar o SumatraPDF. O executavel sera gerado assim mesmo.
if not defined SUMATRA echo      No PC de uso, instale com: winget install SumatraPDF.SumatraPDF

rem ------------------------------------------------------------- 5. Testes
echo.
echo [5/6] Rodando os testes automaticos...
pushd "%SRC%"
"%VPY%" -m unittest discover -s tests
if errorlevel 1 echo      AVISO: algum teste falhou. O executavel sera gerado mesmo assim.
if not errorlevel 1 echo      Testes OK.

rem ------------------------------------------------------ 6. Gerar o .exe
echo.
echo [6/6] Gerando o executavel com o PyInstaller...
set "ADDBIN="
if defined SUMATRA set ADDBIN=--add-binary "%SUMATRA%;."
"%VPY%" -m PyInstaller --noconfirm --clean --onefile --noconsole --name PrintBatch ^
  --distpath "%WORK%\dist" --workpath "%WORK%\pybuild" --specpath "%WORK%" ^
  --collect-all tkinterdnd2 --collect-all pypdfium2 ^
  --hidden-import win32com.client --hidden-import pythoncom --hidden-import win32timezone ^
  %ADDBIN% batch_print.py
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" set "MSG=O PyInstaller falhou. Veja as mensagens acima."
if not "%RC%"=="0" goto :fail
if not exist "%WORK%\dist\PrintBatch.exe" set "MSG=PrintBatch.exe nao foi gerado."
if not exist "%WORK%\dist\PrintBatch.exe" goto :fail

copy /y "%WORK%\dist\PrintBatch.exe" "%OUTDIR%PrintBatch.exe" >nul 2>nul
if errorlevel 1 set "OUTDIR=%WORK%\dist\"
echo.
echo ==============================================================
echo   PRONTO!  Executavel gerado em:
echo   %OUTDIR%PrintBatch.exe
echo ==============================================================
echo.
echo Dica: antivirus ou SmartScreen podem alertar por ser um programa novo sem assinatura.
echo       No SmartScreen escolha Mais informacoes e depois Executar assim mesmo.
echo.
choice /c SN /n /m "Abrir o PrintBatch agora? (S/N) "
if not errorlevel 2 start "" "%OUTDIR%PrintBatch.exe"
pause
exit /b 0

rem ============================================================ sub-rotinas
:findpy
set "PY="
where py >nul 2>nul
if errorlevel 1 goto :findpy2
py -3 -c "import sys,tkinter;sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if defined PY exit /b 0
:findpy2
where python >nul 2>nul
if errorlevel 1 goto :findpy3
python -c "import sys,tkinter;sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>nul
if not errorlevel 1 set "PY=python"
if defined PY exit /b 0
:findpy3
for %%D in ("%LOCALAPPDATA%\Programs\Python\Python312" "%LOCALAPPDATA%\Programs\Python\Python313" "%LOCALAPPDATA%\Programs\Python\Python311" "%ProgramFiles%\Python312") do if not defined PY if exist "%%~D\python.exe" set PY="%%~D\python.exe"
exit /b 0

:getbranch
rem %1 = ramo. Tenta o ZIP do GitHub; se falhar, tenta git clone.
set "BR=%~1"
echo      Tentando o ramo %BR% ...
set "ZIP=%WORK%\downloads\repo-%BR%.zip"
if exist "%ZIP%" del /q "%ZIP%"
%PSX% "%PSPRE% try { Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/%REPO_USER%/%REPO_NAME%/archive/refs/heads/%BR%.zip' -OutFile '%ZIP%' } catch { exit 1 }"
if not exist "%ZIP%" goto :getbranch_git
if exist "%WORK%\src\x" rmdir /s /q "%WORK%\src\x"
%PSX% "Expand-Archive -Force '%ZIP%' '%WORK%\src\x'"
for /d %%D in ("%WORK%\src\x\*") do if exist "%%~fD\%PROJ%\batch_print.py" set "SRC=%%~fD\%PROJ%"
if defined SRC exit /b 0
:getbranch_git
where git >nul 2>nul
if errorlevel 1 exit /b 0
if exist "%WORK%\src\g" rmdir /s /q "%WORK%\src\g"
git clone --depth 1 --branch "%BR%" "https://github.com/%REPO_USER%/%REPO_NAME%.git" "%WORK%\src\g"
if exist "%WORK%\src\g\%PROJ%\batch_print.py" set "SRC=%WORK%\src\g\%PROJ%"
exit /b 0

:fail
echo.
echo ERRO: %MSG%
echo.
pause
exit /b 1
