@echo off
rem Build the Windows app folder dist\SupplyChainDataReview\ and zip it for download.
rem Steps: tests -> PyInstaller -> selftest of the built .exe -> zip named by
rem tool version and reference-tables version.
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe call setup.bat
.venv\Scripts\python -m pip install -r requirements-build.txt
.venv\Scripts\python -m pytest tests -q || exit /b 1
.venv\Scripts\python -m PyInstaller --clean --noconfirm SupplyChainDataReview.spec || exit /b 1
dist\SupplyChainDataReview\SupplyChainDataReview.exe --selftest
if errorlevel 1 (
  echo Selftest of the built app FAILED
  exit /b 1
)
.venv\Scripts\python -c "from protocol_engine import __version__ as v; from protocol_engine.tables_version import tables_version_for as t; print(v + '-tables-' + t())" > dist\version.txt
set /p VER=<dist\version.txt
powershell -NoProfile -Command "Compress-Archive -Force -Path dist\SupplyChainDataReview -DestinationPath dist\SupplyChainDataReview-%VER%-win64.zip"
echo Built dist\SupplyChainDataReview-%VER%-win64.zip
