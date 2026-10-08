@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -m venv .venv
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --onefile --windowed --name QuickVault --icon assets\quickvault.ico --add-data "assets;assets" app.py
if errorlevel 1 goto failed
echo Build complete. Run Install QuickVault.bat to install.
exit /b 0
:failed
echo Build failed.
pause
exit /b 1
