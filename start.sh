#!/bin/bash
set -e

echo "========================================"
echo "  StoryCanvas - 启动中..."
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Detect python
PYTHON=""
if command -v python3 &> /dev/null; then
  PYTHON="python3"
elif command -v python &> /dev/null; then
  PYTHON="python"
fi

cleanup() {
  echo ""
  echo "正在停止服务..."
  kill $BACKEND_PID 2>/dev/null || true
  kill $FRONTEND_PID 2>/dev/null || true
  echo "服务已停止"
  exit 0
}
trap cleanup SIGINT SIGTERM

# Start backend
echo "[1/2] 启动后端服务 (端口 8767)..."
$PYTHON -m uvicorn backend.main:app --host 0.0.0.0 --port 8767 &
BACKEND_PID=$!

# Wait for backend
sleep 3

# Start frontend
echo "[2/2] 启动前端开发服务器 (端口 5173)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✓ 已启动服务"
echo ""
echo "  后端 API: http://localhost:8767"
echo "  前端界面: http://localhost:5173"
echo "  API 文档: http://localhost:8767/docs"
echo ""
echo "  按 Ctrl+C 停止所有服务"

wait