#!/bin/bash
set -e

PASS=0
FAIL=0
WARN=0

echo "========================================"
echo "  StoryCanvas - Environment Check"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ========== 1. Python ==========
echo "[1/8] Python ..."
PYTHON=""
if command -v python3 &> /dev/null; then
  PYTHON="python3"
elif command -v python &> /dev/null; then
  PYTHON="python"
fi

if [ -z "$PYTHON" ]; then
  echo "  [FAIL] Python not found"
  FAIL=$((FAIL+1))
else
  PYVER=$($PYTHON --version 2>&1 | awk '{print $2}')
  echo "  [OK] $PYTHON $PYVER"
  PASS=$((PASS+1))

  PYMAJOR=$(echo "$PYVER" | cut -d. -f1)
  PYMINOR=$(echo "$PYVER" | cut -d. -f2)

  if [ "$PYMAJOR" -lt 3 ]; then
    echo "  [FAIL] Python 3.11+ required, got $PYVER"
    FAIL=$((FAIL+1))
  elif [ "$PYMAJOR" -eq 3 ] && [ "$PYMINOR" -lt 11 ]; then
    echo "  [WARN] Python 3.11+ recommended, got $PYVER"
    WARN=$((WARN+1))
  elif [ "$PYMAJOR" -eq 3 ] && [ "$PYMINOR" -ge 13 ]; then
    echo "  [WARN] Python $PYVER may have compatibility issues with some packages"
    WARN=$((WARN+1))
  fi
fi

# ========== 2. Python deps ==========
echo ""
echo "[2/8] Python dependencies ..."
if [ -z "$PYTHON" ]; then
  echo "  [SKIP] Python not found"
else
  DEPS_OK=1
  for dep in fastapi uvicorn pydantic aiosqlite httpx dotenv sse_starlette; do
    if $PYTHON -c "import $dep" 2>/dev/null; then
      echo "  [OK] $dep"
      PASS=$((PASS+1))
    else
      if [ "$dep" = "dotenv" ]; then
        if $PYTHON -c "import python_dotenv" 2>/dev/null; then
          echo "  [OK] $dep"
          PASS=$((PASS+1))
          continue
        fi
      fi
      echo "  [FAIL] $dep - missing"
      DEPS_OK=0
      FAIL=$((FAIL+1))
    fi
  done
  if [ "$DEPS_OK" -eq 0 ]; then
    echo "  Fix: run install.sh or $PYTHON -m pip install -r backend/requirements.txt"
  fi
fi

# ========== 3. Backend import test ==========
echo ""
echo "[3/8] Backend import test ..."
if [ -z "$PYTHON" ]; then
  echo "  [SKIP] Python not found"
else
  if $PYTHON -c "from backend.main import app" 2>/dev/null; then
    echo "  [OK] backend.main imports successfully"
    PASS=$((PASS+1))
  else
    echo "  [FAIL] Cannot import backend.main"
    echo "  Detail:"
    $PYTHON -c "from backend.main import app" 2>&1 | head -5
    FAIL=$((FAIL+1))
    echo "  Fix: check error above, usually a missing or incompatible package"
  fi
fi

# ========== 4. Node.js ==========
echo ""
echo "[4/8] Node.js ..."
if ! command -v node &> /dev/null; then
  echo "  [FAIL] Node.js not found"
  FAIL=$((FAIL+1))
  echo "  Fix: install from https://nodejs.org"
else
  NODERAW=$(node --version)
  NODEVER=$(echo "$NODERAW" | sed 's/v//' | cut -d. -f1)
  echo "  [OK] Node.js $NODERAW"
  PASS=$((PASS+1))
  if [ "$NODEVER" -lt 18 ]; then
    echo "  [WARN] Node.js 18+ recommended, got $NODERAW"
    WARN=$((WARN+1))
  fi
fi

# ========== 5. Frontend deps ==========
echo ""
echo "[5/8] Frontend dependencies ..."
if [ ! -d "frontend/node_modules" ]; then
  echo "  [FAIL] frontend/node_modules not found"
  FAIL=$((FAIL+1))
  echo "  Fix: run install.sh or cd frontend && npm install"
else
  echo "  [OK] frontend/node_modules exists"
  PASS=$((PASS+1))
fi
if [ ! -f "frontend/package.json" ]; then
  echo "  [FAIL] frontend/package.json not found"
  FAIL=$((FAIL+1))
else
  echo "  [OK] frontend/package.json exists"
  PASS=$((PASS+1))
fi

# ========== 6. Ports ==========
echo ""
echo "[6/8] Port check ..."
if lsof -i :8767 -sTCP:LISTEN &>/dev/null; then
  PID=$(lsof -ti :8767 -sTCP:LISTEN 2>/dev/null | head -1)
  echo "  [WARN] Port 8767 already in use (backend may not start)"
  echo "  PID: $PID"
  WARN=$((WARN+1))
  echo "  Fix: kill $PID or change PORT in .env"
else
  echo "  [OK] Port 8767 available"
  PASS=$((PASS+1))
fi
if lsof -i :5173 -sTCP:LISTEN &>/dev/null; then
  echo "  [WARN] Port 5173 already in use (frontend may not start)"
  WARN=$((WARN+1))
else
  echo "  [OK] Port 5173 available"
  PASS=$((PASS+1))
fi

# ========== 7. Config files ==========
echo ""
echo "[7/8] Config files ..."
if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    echo "  [WARN] .env not found, will use defaults"
    WARN=$((WARN+1))
  else
    echo "  [FAIL] .env and .env.example not found"
    FAIL=$((FAIL+1))
  fi
else
  echo "  [OK] .env exists"
  PASS=$((PASS+1))
fi
if [ ! -f "backend/requirements.txt" ]; then
  echo "  [FAIL] backend/requirements.txt not found"
  FAIL=$((FAIL+1))
else
  echo "  [OK] backend/requirements.txt exists"
  PASS=$((PASS+1))
fi

# ========== 8. LLM config ==========
echo ""
echo "[8/8] LLM configuration ..."
if [ -z "$PYTHON" ]; then
  echo "  [SKIP] Python not found"
else
  LLM_PROV=$($PYTHON -c "from backend.core.config import settings; print(settings.llm_provider)" 2>/dev/null || echo "")
  if [ -z "$LLM_PROV" ]; then
    echo "  [WARN] Cannot read LLM settings"
    WARN=$((WARN+1))
  else
    echo "  Provider: $LLM_PROV"
    if [ "$LLM_PROV" = "deepseek" ]; then
      LLM_KEY=$($PYTHON -c "from backend.core.config import settings; k=settings.deepseek_api_key; print(k[:4] if k else '')" 2>/dev/null || echo "")
      if [ -z "$LLM_KEY" ]; then
        echo "  [WARN] DeepSeek API Key not set"
        WARN=$((WARN+1))
      else
        echo "  [OK] DeepSeek API Key: ${LLM_KEY}..."
        PASS=$((PASS+1))
      fi
    elif [ "$LLM_PROV" = "ollama" ]; then
      echo "  [OK] Using Ollama (local)"
      PASS=$((PASS+1))
    else
      echo "  [OK] Using $LLM_PROV"
      PASS=$((PASS+1))
    fi
  fi
fi

# ========== Summary ==========
echo ""
echo "========================================"
echo "  Summary"
echo "========================================"
echo "  PASS: $PASS    WARN: $WARN    FAIL: $FAIL"
echo ""
if [ "$FAIL" -gt 0 ]; then
  echo "  [!] Problems found, please fix FAIL items above before starting."
  echo "  Run install.sh first if dependencies are missing."
elif [ "$WARN" -gt 0 ]; then
  echo "  [i] Warnings found, the app may still work but check them."
else
  echo "  [OK] All checks passed! Run bash start.sh to launch."
fi
echo "========================================"
echo ""
