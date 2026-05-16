@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
echo ========================================
echo   StoryCanvas - Install Dependencies
echo ========================================
echo.

:: Copy .env if not exists
if not exist .env (
    copy .env.example .env
    echo [OK] .env file created, please edit your API Key
)

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

:: ---------- Python dependencies ----------
echo.
echo [1/2] Installing Python dependencies...
echo    If download is slow, try: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r backend\requirements.txt
!PYTHON! -m pip install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Python dependencies installation failed
    pause
    exit /b 1
)
echo [OK] Python dependencies installed

:: ---------- Frontend dependencies ----------
echo.
echo [2/2] Installing frontend dependencies...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Frontend dependencies installation failed
    pause
    exit /b 1
)
cd ..
echo [OK] Frontend dependencies installed

echo.
echo ========================================
echo   Installation Complete!
echo.
echo   How to start:
echo   1. Edit .env file to configure LLM API Key
echo   2. Run start.bat to launch the system
echo ========================================
pause