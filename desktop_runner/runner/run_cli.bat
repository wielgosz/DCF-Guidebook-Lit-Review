@echo off
rem Command-line run from source, for example:
rem   run_cli.bat --register-only --pdf-folder "C:\corpus" --output-folder "C:\runs"
rem   run_cli.bat --pdf-folder "C:\corpus" --output-folder "C:\runs" --tables "C:\my_tables" --template "C:\RDI.xlsx"
cd /d "%~dp0"
.venv\Scripts\python.exe -m protocol_engine.run_protocol %*
