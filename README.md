# QuickVault

A comfortable Python desktop app for Windows. Store quick notes, API keys, and environment-variable values with title/tag search, hidden secrets, and quick copy.

## Run

For the installed Windows app, double-click **Install QuickVault.bat**. This copies the built executable to `%LOCALAPPDATA%\Programs\QuickVault` and creates Desktop and Start menu shortcuts. No administrator access is needed. Existing vault data stays in `%LOCALAPPDATA%\QuickVault`.

Save, Copy value, and Delete entry are in the fixed toolbar above the editor. Delete becomes available after an entry is saved or selected.

Install Python 3.10 or newer with Tkinter (included in the standard Windows installer), then double-click **Run QuickVault.bat**. The launcher creates a private `.venv` environment so dependencies do not change your shared Python installation. Or run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Create a master password on first launch. Use Ctrl+N for a new entry, Ctrl+S to save, and Ctrl+L to lock. Secret values are hidden until you choose Reveal secret. Copy clears the clipboard after 30 seconds if it still contains that value. The vault locks after five minutes of inactivity; titled drafts are saved first. An untitled draft or failed save delays locking to avoid losing work.

## Storage

The entire entry collection, including titles and tags, is encrypted using Fernet authenticated encryption. The encryption key is derived from your password with PBKDF2-SHA256, a random salt, and 600,000 iterations. Data is saved atomically to `%LOCALAPPDATA%\QuickVault\vault.json`. No account or cloud service is used.

There is no password recovery. Back up the encrypted vault file and keep your password safe. The app stores environment variable values; it does not modify Windows environment settings. Revealed or copied values can be read by other software on your computer, and clipboard history can retain copies. Python cannot guarantee erasure of secrets from process memory.

## Optional standalone executable

From a fresh checkout, double-click **Build QuickVault.bat** first, then **Install QuickVault.bat**. The build script bundles Python, dependencies, and the app icon. Generated executables are excluded from Git.

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --onefile --windowed --name QuickVault --icon assets\quickvault.ico --add-data "assets;assets" app.py
```

The executable will be in `dist\QuickVault.exe`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```
