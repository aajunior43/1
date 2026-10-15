@echo off
rem Cria um atalho em "Enviar para" para imprimir arquivos selecionados no Explorer (botao direito > Enviar para > PrintBatch)
set "TARGET=%~dp0executar.bat"
set "LNK=%APPDATA%\Microsoft\Windows\SendTo\PrintBatch.lnk"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%'); $s.TargetPath='%TARGET%'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Save()"
echo Atalho criado em: %LNK%
pause
