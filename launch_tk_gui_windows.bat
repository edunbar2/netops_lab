@echo off
setlocal
cd /d "%~dp0"
py -3 gns3_ccnp_lab_gui.py
if errorlevel 1 (
    echo.
    echo GUI exited with an error. Install/update dependencies with:
    echo py -3 -m pip install -r requirements.txt
    echo.
    pause
)
