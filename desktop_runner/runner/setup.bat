@echo off
rem One-time setup for running from source: creates .venv and installs requirements.
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv 2>nul || python -m venv .venv
)
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
echo.
echo Setup complete. Start the app with run_gui.bat
