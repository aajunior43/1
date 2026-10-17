@echo off
rem Cria um atalho em "Enviar para": botao direito nos arquivos > Enviar para > PrintBatch
rem (abre o PrintBatch ja com os arquivos na fila, sem imprimir nada sozinho)
set "LNK=%APPDATA%\Microsoft\Windows\SendTo\PrintBatch.lnk"
if exist "%~dp0PrintBatch.exe" (
  set "TARGET=%~dp0PrintBatch.exe"
) else (
  set "TARGET=%~dp0executar.bat"
)
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%'); $s.TargetPath='%TARGET%'; $s.Arguments='--gui'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Save()"
echo Atalho criado em: %LNK%
echo Destino: %TARGET%
pause
