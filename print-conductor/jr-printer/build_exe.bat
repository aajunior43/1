@echo off
setlocal
cd /d "%~dp0"
python -m pip install pyinstaller pywin32 tkinterdnd2 pypdfium2 pillow
python -m PyInstaller --noconfirm --onefile --noconsole --name JRPrinter ^
  --icon jrprinter\assets\icon.ico --add-data "jrprinter\assets;jrprinter\assets" --collect-all tkinterdnd2 --collect-all pypdfium2 --hidden-import win32com.client --hidden-import pythoncom ^
  jr_printer.py
echo.
echo Executavel gerado em dist\JRPrinter.exe
pause
