@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title StoryCanvas - 自由画布叙事创作系统
echo ========================================
echo   StoryCanvas - 启动中...
echo ========================================
echo.

:: Detect python command
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON=python
) else (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON=py
    ) else (
        echo ❌ 未找到 Python
        pause
        exit /b 1
    )
)

:: Start backend
echo [1/2] 启动后端服务 (端口 8767)...
start "StoryCanvas-Backend" cmd /c "cd /d %~dp0 && !PYTHON! -m uvicorn backend.main:app --host 0.0.0.0 --port 8767 --reload"

:: Wait a moment for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend
echo [2/2] 启动前端开发服务器 (端口 5173)...
start "StoryCanvas-Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

echo.
echo ✓ 已启动服务
echo.
echo   后端 API: http://localhost:8767
echo   前端界面: http://localhost:5173
echo   API 文档: http://localhost:8767/docs
echo.
echo   按任意键关闭所有服务...
pause >nul

:: Cleanup
taskkill /f /fi "WINDOWTITLE eq StoryCanvas-Backend" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq StoryCanvas-Frontend" >nul 2>&1
echo 服务已停止
