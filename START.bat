@echo off
REM ============================================================
REM  AI Interview Preparation ^& Career Guidance System
REM  START script - launches backend (FastAPI) + frontend (Vite)
REM  then opens the app in Chrome:  http://localhost:5173
REM ============================================================
title AI Career Assistant - STARTING...
cd /d "%~dp0"

echo.
echo  ==============================================
echo   AI Interview Prep ^& Career Guidance System
echo   Starting servers, please wait...
echo  ==============================================
echo.

REM ---------- 0. Already running? Skip straight to Chrome ----------
curl -s -o NUL http://localhost:5173
if not errorlevel 1 (
    echo   The website is already running - opening Chrome...
    goto openchrome
)

REM ---------- 1. Backend (FastAPI on port 8000) ----------
echo  [1/2] Starting backend, FastAPI on port 8000 ...
if not exist "backend\venv\Scripts\python.exe" (
    echo   ERROR: backend\venv not found. Create it first:
    echo     cd backend   then   python -m venv venv   then   venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
start "AI-Career-Backend" /min cmd /c "cd /d "%~dp0backend" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

REM ---------- 2. Frontend (Vite dev server on port 5173) ----------
echo  [2/2] Starting frontend, Vite on port 5173 ...
if not exist "frontend\node_modules" (
    echo   node_modules missing - installing dependencies once, this can take a minute...
    cd /d "%~dp0frontend"
    call npm install --no-fund --no-audit
    cd /d "%~dp0"
)
start "AI-Career-Frontend" /min cmd /c "cd /d "%~dp0frontend" && npm run dev"

REM ---------- 3. Wait until both respond ----------
set /a tries=0
:waitloop
ping -n 3 127.0.0.1 >NUL
set /a tries+=1
set BACKEND_OK=0
set FRONTEND_OK=0
curl -s -o NUL http://127.0.0.1:8000/api/health && set BACKEND_OK=1
curl -s -o NUL http://localhost:5173 && set FRONTEND_OK=1
if "%BACKEND_OK%"=="1" if "%FRONTEND_OK%"=="1" goto ready
if %tries% lss 30 goto waitloop

echo.
echo   WARNING: servers did not respond in time. Check the two minimized
echo   windows named "AI-Career-Backend" and "AI-Career-Frontend" for errors.
pause
exit /b 1

:ready
echo.
echo  ==============================================
echo   READY!  Opening http://localhost:5173 in Chrome
echo   Demo login: demo@career.ai / demo1234
echo   To stop everything later: run STOP.bat
echo  ==============================================
echo.

:openchrome
REM ---------- Open the app in Chrome (fallback: default browser) ----------
set CHROME=
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe
if defined CHROME (
    start "" "%CHROME%" --new-window "http://localhost:5173"
) else (
    echo   Chrome not found - opening in your default browser instead...
    start "" http://localhost:5173
)
pause
