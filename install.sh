#!/bin/bash
set -e

echo "========================================"
echo "  StoryCanvas - 安装依赖"
echo "========================================"
echo ""

# Detect python command
PYTHON=""
if command -v python3 &> /dev/null; then
  PYTHON="python3"
elif command -v python &> /dev/null; then
  PYTHON="python"
else
  echo "❌ 未找到 Python，请安装 Python 3.11+"
  exit 1
fi

echo "使用 Python: $($PYTHON --version)"

# Copy .env if not exists
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✓ 已创建 .env 配置文件，请编辑 API Key"
fi

# Install Python dependencies
echo ""
echo "[1/2] 安装 Python 依赖..."
$PYTHON -m pip install -r backend/requirements.txt --quiet
echo "✓ Python 依赖安装完成"

# Install Node.js dependencies
echo ""
echo "[2/2] 安装前端依赖..."
cd frontend
npm install --silent
cd ..
echo "✓ 前端依赖安装完成"

echo ""
echo "========================================"
echo "  安装完成！"
echo ""
echo "  启动方式："
echo "  1. 编辑 .env 文件配置 LLM API Key"
echo "  2. 运行 bash start.sh 启动系统"
echo "========================================"
