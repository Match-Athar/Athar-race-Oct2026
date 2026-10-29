@echo off
rem Double-click to open both boards on http://localhost:8000 with a "Refresh now" button
rem (it pulls the latest sales from the API). No automatic refresh. Close this window to stop.
rem For automatic refresh as well, add  --every  after --serve below.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
start "" "http://localhost:8000/internal.html"
python run.py --api --target data\target.xlsx --serve
pause
