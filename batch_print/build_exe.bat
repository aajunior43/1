@echo off
setlocal
cd /d "%~dp0"
python -m pip install pyinstaller pywin32 tkinterdnd2 pypdfium2 pillow
python -m PyInstaller --noconfirm --onefile --noconsole --name PrintBatch ^
  --collect-all tkinterdnd2 --collect-all pypdfium2 --hidden-import win32com.client --hidden-import pythoncom ^
  batch_print.py
echo.
echo Executavel gerado em dist\PrintBatch.exe
pause
