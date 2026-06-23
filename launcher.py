#!/usr/bin/env python3
"""StoryCanvas 统一启动器 - 在单个窗口中管理后端 + 前端"""
import subprocess
import sys
import os
import time
import socket
import signal
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
BACKEND_PORT = 8767
FRONTEND_PORT = 5173

backend_proc = None
frontend_proc = None


def print_banner():
    print("=" * 50)
    print("   StoryCanvas - Starting...")
    print("=" * 50)
    print()


def check_python():
    print("Detecting Python...")
    print(f"Using {sys.executable}")
    print()


def check_deps():
    print("Checking Python dependencies...")
    try:
        import fastapi, uvicorn, pydantic, aiosqlite  # noqa
        print("[OK]")
    except ImportError:
        print("[ERROR] Python dependencies missing, please run install.bat first")
        sys.exit(1)
    print()


def check_node():
    print("Detecting Node.js...")
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        print(f"Using {result.stdout.strip()}")
    except FileNotFoundError:
        print("[ERROR] Node.js not found")
        sys.exit(1)
    print()


def check_frontend_deps():
    if not os.path.exists(os.path.join(FRONTEND_DIR, "node_modules")):
        print("[ERROR] Frontend dependencies not installed")
        sys.exit(1)


def port_is_open(host, port, timeout=1):
    """Check if a TCP port is accepting connections"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except:
        return False


def start_backend():
    global backend_proc
    print("[1/2] Starting backend service (port 8767)...")

    # Kill any existing process on the port first
    try:
        subprocess.run(
            ["powershell", "-Command",
             f"Get-NetTCPConnection -LocalPort {BACKEND_PORT} -ErrorAction SilentlyContinue | "
             f"Select-Object -ExpandProperty OwningProcess | "
             f"ForEach-Object {{ Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }}"],
            capture_output=True, timeout=5)
    except:
        pass
    time.sleep(1)

    print("--- Backend log ---")
    # Start WITHOUT --reload for reliability (reloader + subprocess has issues)
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )

    # Read backend output in a separate thread
    def read_output():
        try:
            for line in backend_proc.stdout:
                print(f"  {line}", end="")
                sys.stdout.flush()
        except:
            pass

    t = threading.Thread(target=read_output, daemon=True)
    t.start()

    # Wait for backend to be ready (poll TCP port directly)
    print("Waiting for backend to be ready...")
    ready = False
    for i in range(30):
        time.sleep(1)
        if port_is_open("127.0.0.1", BACKEND_PORT):
            ready = True
            break
        if i == 15:
            # Check if process is still alive
            if backend_proc.poll() is not None:
                print(f"  [ERROR] Backend process exited early (code: {backend_proc.returncode})")
                break
            print("  (still waiting for backend...)")

    if ready:
        print("[OK] Backend is ready")
    else:
        if backend_proc.poll() is not None:
            print(f"[ERROR] Backend crashed with exit code {backend_proc.returncode}")
            print("[ERROR] Check the backend log above for details")
        else:
            print("[WARN] Backend process is running but not accepting connections")
            print("[WARN] Try refreshing the browser after frontend starts")
    print()


def start_frontend():
    global frontend_proc
    print("[2/2] Starting frontend dev server (port 5173)...")
    print("--- Frontend log ---")
    frontend_proc = subprocess.Popen(
        ["npx.cmd", "vite"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )

    def read_output():
        try:
            for line in frontend_proc.stdout:
                print(f"  {line}", end="")
                sys.stdout.flush()
        except:
            pass

    t = threading.Thread(target=read_output, daemon=True)
    t.start()


def print_urls():
    print()
    print("[OK] Services started")
    print()
    print(f"  Backend API: http://127.0.0.1:{BACKEND_PORT}")
    print(f"  Frontend UI: http://localhost:{FRONTEND_PORT}")
    print(f"  API Docs:    http://127.0.0.1:{BACKEND_PORT}/docs")
    print()
    print("  Press Ctrl+C to stop all services...")
    print()


def cleanup(signum=None, frame=None):
    print()
    print("Stopping services...")
    for name, proc in [("Backend", backend_proc), ("Frontend", frontend_proc)]:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
                print(f"[OK] {name} stopped")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"[OK] {name} killed (forced)")
    print("All services stopped.")


if __name__ == "__main__":
    print_banner()
    check_python()
    check_deps()
    check_node()
    check_frontend_deps()

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    start_backend()
    start_frontend()
    print_urls()

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print(f"[ERROR] Backend exited with code {backend_proc.returncode}")
                cleanup()
                break
            if frontend_proc.poll() is not None:
                print(f"[ERROR] Frontend exited with code {frontend_proc.returncode}")
                cleanup()
                break
    except KeyboardInterrupt:
        cleanup()