@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
echo ========================================
echo   StoryCanvas - 安装依赖
echo ========================================
echo.

:: Copy .env if not exists
if not exist .env (
    copy .env.example .env
    echo ✓ 已创建 .env 配置文件，请编辑 API Key
)

:: Detect python command
echo 检测 Python...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON=python
) else (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON=py
    ) else (
        echo ❌ 未找到 Python，请安装 Python 3.11+
        pause
        exit /b 1
    )
)
echo 使用 !PYTHON!

:: Install Python dependencies
echo.
echo [1/2] 安装 Python 依赖...
echo   如果下载慢，可手动执行：pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r backend\requirements.txt
!PYTHON! -m pip install -r backend\requirements.txt
echo ✓ Python 依赖安装完成

:: Install Node.js dependencies
echo.
echo [2/2] 安装前端依赖...
cd frontend
call npm install
cd ..
echo ✓ 前端依赖安装完成

echo.
echo ========================================
echo   安装完成！
echo.
echo   启动方式：
echo   1. 编辑 .env 文件配置 LLM API Key
echo   2. 运行 start.bat 启动系统
echo ========================================
pause
