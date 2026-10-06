@echo off
rem Start the desktop runner from source (run setup.bat once first).
cd /d "%~dp0"
start "" .venv\Scripts\pythonw.exe app.py
