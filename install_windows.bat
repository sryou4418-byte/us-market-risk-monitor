@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Installation failed. Please check Python and internet access.
) else (
  echo Installation complete. Run start_windows.bat.
)
pause
