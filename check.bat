@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title StoryCanvas - Diagnostics

set PASS=0
set FAIL=0
set WARN=0

echo ========================================
echo   StoryCanvas - Environment Check
echo ========================================
echo.

:: ========== 1. Python ==========
echo [1/8] Python ...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON=python
) else (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON=py
    ) else (
        echo   [FAIL] Python not found
        set /a FAIL+=1
        goto :skip_python_ver
    )
)
for /f "tokens=2 delims= " %%v in ('!PYTHON! --version 2^>^&1') do set PYVER=%%v
echo   [OK] !PYTHON! !PYVER!
set /a PASS+=1

for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set PYMAJOR=%%a
    set PYMINOR=%%b
)
if !PYMAJOR! lss 3 (
    echo   [FAIL] Python 3.11+ required, got !PYVER!
    set /a FAIL+=1
) else if !PYMAJOR! equ 3 if !PYMINOR! lss 11 (
    echo   [WARN] Python 3.11+ recommended, got !PYVER!
    set /a WARN+=1
) else if !PYMAJOR! equ 3 if !PYMINOR! geq 13 (
    echo   [WARN] Python !PYVER! may have compatibility issues with some packages
    set /a WARN+=1
)
:skip_python_ver

:: ========== 2. Python deps ==========
echo.
echo [2/8] Python dependencies ...
if not defined PYTHON (
    echo   [SKIP] Python not found
    goto :skip_py_deps
)
set DEPS_OK=1
for %%d in (fastapi uvicorn pydantic aiosqlite httpx dotenv sse_starlette) do (
    !PYTHON! -c "import %%d" >nul 2>&1
    if !errorlevel! neq 0 (
        if "%%d"=="dotenv" (
            !PYTHON! -c "import python_dotenv" >nul 2>&1
            if !errorlevel! neq 0 (
                echo   [FAIL] %%d - missing
                set DEPS_OK=0
                set /a FAIL+=1
            ) else (
                echo   [OK] %%d
                set /a PASS+=1
            )
        ) else (
            echo   [FAIL] %%d - missing
            set DEPS_OK=0
            set /a FAIL+=1
        )
    ) else (
        echo   [OK] %%d
        set /a PASS+=1
    )
)
if "!DEPS_OK!"=="0" (
    echo   Fix: run install.bat or !PYTHON! -m pip install -r backend\requirements.txt
)
:skip_py_deps

:: ========== 3. Backend import test ==========
echo.
echo [3/8] Backend import test ...
if not defined PYTHON (
    echo   [SKIP] Python not found
    goto :skip_backend_test
)
!PYTHON! -c "from backend.main import app; print('OK')" >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FAIL] Cannot import backend.main
    echo   Detail:
    !PYTHON! -c "from backend.main import app" 2>&1 | findstr /n "." | findstr "^[1-5]:"
    set /a FAIL+=1
    echo   Fix: check error above, usually a missing or incompatible package
) else (
    echo   [OK] backend.main imports successfully
    set /a PASS+=1
)
:skip_backend_test

:: ========== 4. Node.js ==========
echo.
echo [4/8] Node.js ...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FAIL] Node.js not found
    set /a FAIL+=1
    echo   Fix: install from https://nodejs.org
) else (
    for /f "tokens=1 delims=." %%v in ('node --version') do set NODERAW=%%v
    set NODEVER=!NODERAW:v=!
    echo   [OK] Node.js !NODERAW!
    set /a PASS+=1
    if !NODEVER! lss 18 (
        echo   [WARN] Node.js 18+ recommended, got !NODERAW!
        set /a WARN+=1
    )
)

:: ========== 5. Frontend deps ==========
echo.
echo [5/8] Frontend dependencies ...
if not exist "%~dp0frontend\node_modules" (
    echo   [FAIL] frontend\node_modules not found
    set /a FAIL+=1
    echo   Fix: run install.bat or cd frontend ^&^& npm install
) else (
    echo   [OK] frontend\node_modules exists
    set /a PASS+=1
)
if not exist "%~dp0frontend\package.json" (
    echo   [FAIL] frontend\package.json not found
    set /a FAIL+=1
) else (
    echo   [OK] frontend\package.json exists
    set /a PASS+=1
)

:: ========== 6. Ports ==========
echo.
echo [6/8] Port check ...
netstat -ano | findstr ":8767 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [WARN] Port 8767 already in use (backend may not start)
    set /a WARN+=1
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8767 " ^| findstr "LISTENING"') do (
        echo   PID: %%p
    )
    echo   Fix: taskkill /PID %%p /F or change PORT in .env
) else (
    echo   [OK] Port 8767 available
    set /a PASS+=1
)
netstat -ano | findstr ":5173 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [WARN] Port 5173 already in use (frontend may not start)
    set /a WARN+=1
) else (
    echo   [OK] Port 5173 available
    set /a PASS+=1
)

:: ========== 7. Config files ==========
echo.
echo [7/8] Config files ...
if not exist "%~dp0.env" (
    if exist "%~dp0.env.example" (
        echo   [WARN] .env not found, will use defaults
        set /a WARN+=1
    ) else (
        echo   [FAIL] .env and .env.example not found
        set /a FAIL+=1
    )
) else (
    echo   [OK] .env exists
    set /a PASS+=1
)
if not exist "%~dp0backend\requirements.txt" (
    echo   [FAIL] backend\requirements.txt not found
    set /a FAIL+=1
) else (
    echo   [OK] backend\requirements.txt exists
    set /a PASS+=1
)

:: ========== 8. LLM config ==========
echo.
echo [8/8] LLM configuration ...
if not defined PYTHON (
    echo   [SKIP] Python not found
    goto :skip_llm
)
!PYTHON! -c "from backend.core.config import settings; p=settings.llm_provider; c=settings.llm_config; k=list(c.keys()); print(f'provider={p} keys={k}')" >nul 2>&1
if %errorlevel% neq 0 (
    echo   [WARN] Cannot read LLM settings
    set /a WARN+=1
    goto :skip_llm
)
for /f "tokens=*" %%o in ('!PYTHON! -c "from backend.core.config import settings; print(settings.llm_provider)" 2^>nul') do set LLM_PROV=%%o
echo   Provider: !LLM_PROV!
if "!LLM_PROV!"=="deepseek" (
    for /f "tokens=*" %%o in ('!PYTHON! -c "from backend.core.config import settings; print(settings.deepseek_api_key[:4] if settings.deepseek_api_key else '')" 2^>nul') do set LLM_KEY=%%o
    if "!LLM_KEY!"=="" (
        echo   [WARN] DeepSeek API Key not set
        set /a WARN+=1
    ) else (
        echo   [OK] DeepSeek API Key: !LLM_KEY!...
        set /a PASS+=1
    )
) else if "!LLM_PROV!"=="ollama" (
    echo   [OK] Using Ollama (local)
    set /a PASS+=1
) else (
    echo   [OK] Using !LLM_PROV!
    set /a PASS+=1
)
:skip_llm

:: ========== Summary ==========
echo.
echo ========================================
echo   Summary
echo ========================================
echo   PASS: !PASS!    WARN: !WARN!    FAIL: !FAIL!
echo.
if !FAIL! gtr 0 (
    echo   [!] Problems found, please fix FAIL items above before starting.
    echo   Run install.bat first if dependencies are missing.
) else if !WARN! gtr 0 (
    echo   [i] Warnings found, the app may still work but check them.
) else (
    echo   [OK] All checks passed! Run start.bat to launch.
)
echo ========================================
echo.
pause