@echo off
echo ========================================================
echo Launching Network Feeder Design (Rubber Tree Feeder Viewer)
echo ========================================================
cd /d "%~dp0"

if exist "E:\invlfa\venv\Scripts\python.exe" (
    "E:\invlfa\venv\Scripts\python.exe" network_feeder_viewer.py
) else (
    python network_feeder_viewer.py
)

if exist "network.html" (
    echo Opening network.html in default browser...
    start network.html
)
pause
