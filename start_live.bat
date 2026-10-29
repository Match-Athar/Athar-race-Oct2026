@echo off
rem Double-click to keep both boards up to date from the API every 5 minutes AND open them on
rem http://localhost:8000 with a "Refresh now" button. Close this window to stop.
rem Odoo connection: .env in this folder. Targets: data\target.xlsx.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
start "" "http://localhost:8000/internal.html"
python run.py --api --target data\target.xlsx --serve --every
pause
