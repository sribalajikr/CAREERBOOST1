@echo off
REM ============================================================
REM  AI Interview Preparation ^& Career Guidance System
REM  STOP script - closes the backend and frontend servers
REM ============================================================
title AI Career Assistant - STOPPING...

echo.
echo  Stopping the AI Career Assistant servers...
echo.

REM ---------- 1. Frontend (Vite dev server on port 5173) ----------
set FOUND=0
for /f "tokens=5" %%P in ('netstat -aon ^| findstr "LISTENING" ^| findstr ":5173"') do (
    set FOUND=1
    echo   Stopping frontend, PID %%P ...
    taskkill /F /PID %%P >nul 2>&1
)
if "%FOUND%"=="0" echo   Frontend was not running.

REM ---------- 2. Backend (uvicorn on port 8000) ----------
set FOUND=0
for /f "tokens=5" %%P in ('netstat -aon ^| findstr "LISTENING" ^| findstr ":8000"') do (
    set FOUND=1
    echo   Stopping backend, PID %%P ...
    taskkill /F /PID %%P >nul 2>&1
)
if "%FOUND%"=="0" echo   Backend was not running.

echo.
echo  All servers stopped. Goodbye!
ping -n 4 127.0.0.1 >NUL
