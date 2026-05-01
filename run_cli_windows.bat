@echo off
setlocal
cd /d "%~dp0"
py -3 .\gns3_ccnp_lab_generator.py %*
endlocal
