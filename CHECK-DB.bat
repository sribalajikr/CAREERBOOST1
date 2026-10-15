@echo off
rem Shows what is inside the CareerBoost database
cd /d "%~dp0backend"
venv\Scripts\python.exe check_db.py
echo.
pause
