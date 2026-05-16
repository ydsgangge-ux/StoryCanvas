@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title StoryCanvas
echo ========================================
echo   StoryCanvas - Starting...
echo ========================================
echo.

:: ---------- Python detection ----------
echo Detecting Python...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON=python
) else (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON=py
    ) else (
        echo [ERROR] Python not found, please install Python 3.11+
        pause
        exit /b 1
    )
)
echo Using !PYTHON!

:: ---------- Check Python dependencies ----------
echo Checking Python dependencies...
!PYTHON! -c "import fastapi, uvicorn, pydantic, aiosqlite" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python dependencies missing, please run install.bat first
    pause
    exit /b 1
)
echo [OK]

:: ---------- Node.js detection ----------
echo Detecting Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found, please install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VER=%%i
echo Using !NODE_VER!

:: ---------- Check frontend dependencies ----------
if not exist "%~dp0frontend\node_modules" (
    echo [ERROR] Frontend dependencies not installed, please run install.bat first
    pause
    exit /b 1
)

:: ---------- Start backend ----------
echo.
echo [1/2] Starting backend service (port 8767)...
start "StoryCanvas-Backend" cmd /c "cd /d %~dp0 && !PYTHON! -m uvicorn backend.main:app --host 0.0.0.0 --port 8767 --reload"

:: Wait a moment for backend to start
timeout /t 3 /nobreak >nul

:: ---------- Start frontend ----------
echo [2/2] Starting frontend dev server (port 5173)...
start "StoryCanvas-Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

echo.
echo [OK] Services started
echo.
echo   Backend API: http://localhost:8767
echo   Frontend UI: http://localhost:5173
echo   API Docs: http://localhost:8767/docs
echo.
echo   Press any key to stop all services...
pause >nul

:: Cleanup
taskkill /f /fi "WINDOWTITLE eq StoryCanvas-Backend" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq StoryCanvas-Frontend" >nul 2>&1
echo Services stopped