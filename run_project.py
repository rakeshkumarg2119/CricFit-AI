#!/usr/bin/env python3
"""
CRICFIT AI - Unified Application Launcher
==========================================
Starts both the FastAPI backend and Streamlit frontend with a single command.
Performs health checking and handles graceful termination (Ctrl+C).

Usage:
    python run_project.py
"""

import os
import sys
import time
import signal
import socket
import subprocess
import urllib.request
import urllib.error
from urllib.parse import urlparse

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Load environment variables from .env
# ---------------------------------------------------------------------------
def load_env_file():
    """Load key-value pairs from .env file without external dependencies."""
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            print(f"[WARN] Could not parse .env file: {e}")

load_env_file()

# ---------------------------------------------------------------------------
# Detect Virtual Environment Python Executable
# ---------------------------------------------------------------------------
def detect_python_executable():
    """
    Locate the Python executable in the virtual environment or fallback
    to the active Python interpreter.
    """
    # 1. If currently inside a virtual environment
    if getattr(sys, "base_prefix", sys.prefix) != sys.prefix or os.environ.get("VIRTUAL_ENV"):
        return sys.executable

    # 2. Check standard venv directories in project root
    candidate_dirs = ["venv", ".venv", "env"]
    for d in candidate_dirs:
        if sys.platform == "win32":
            candidate = os.path.join(PROJECT_ROOT, d, "Scripts", "python.exe")
        else:
            candidate = os.path.join(PROJECT_ROOT, d, "bin", "python")
        if os.path.isfile(candidate):
            return candidate

    # 3. Fallback to sys.executable
    return sys.executable

# ---------------------------------------------------------------------------
# Configuration & Endpoints
# ---------------------------------------------------------------------------
backend_url_env = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
parsed_url = urlparse(backend_url_env)
BACKEND_HOST = parsed_url.hostname or "127.0.0.1"
BACKEND_PORT = parsed_url.port or 8000
BACKEND_HEALTH_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}/health"
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))

# Track subprocesses for graceful cleanup
subprocesses = []
shutting_down = False

def terminate_processes(signum=None, frame=None):
    """Gracefully terminate backend and frontend subprocesses."""
    global shutting_down
    if shutting_down:
        return
    shutting_down = True

    print("\n" + "=" * 55)
    print(" [CRICFIT AI] Shutting down services cleanly...")
    print("=" * 55)

    for proc, name in subprocesses:
        if proc.poll() is None:
            print(f" [INFO] Stopping {name} (PID: {proc.pid})...")
            try:
                proc.terminate()
            except Exception as e:
                print(f" [WARN] Failed to terminate {name}: {e}")

    # Wait up to 4 seconds for processes to finish gracefully
    deadline = time.time() + 4.0
    for proc, name in subprocesses:
        remaining = max(0.1, deadline - time.time())
        try:
            proc.wait(timeout=remaining)
            print(f" [OK] {name} stopped.")
        except subprocess.TimeoutExpired:
            print(f" [WARN] {name} did not exit in time. Force killing...")
            try:
                proc.kill()
            except Exception:
                pass

    print(" [OK] All CRICFIT AI services stopped.")
    sys.exit(0)

# Register signal handlers for clean exit on Ctrl+C / SIGTERM
signal.signal(signal.SIGINT, terminate_processes)
signal.signal(signal.SIGTERM, terminate_processes)
if hasattr(signal, "SIGBREAK"):  # Windows break signal
    signal.signal(signal.SIGBREAK, terminate_processes)

def check_backend_health(health_url: str, timeout: float = 1.0) -> bool:
    """Check if the backend health endpoint returns HTTP 200 OK."""
    try:
        req = urllib.request.Request(
            health_url,
            headers={"User-Agent": "CRICFIT-AI-Launcher/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False

def wait_for_backend(proc: subprocess.Popen, health_url: str, max_retries: int = 30, delay: float = 0.5) -> bool:
    """Poll the backend health endpoint until reachable or timeout expires."""
    print(f" [INFO] Waiting for FastAPI backend at {health_url}...")
    for attempt in range(1, max_retries + 1):
        if proc.poll() is not None:
            print(f" [ERROR] FastAPI backend process exited unexpectedly with code {proc.returncode}!")
            return False

        if check_backend_health(health_url):
            return True

        if attempt % 4 == 0:
            print(f" [INFO] Backend initializing... (attempt {attempt}/{max_retries})")
        time.sleep(delay)

    return False

def main():
    python_exe = detect_python_executable()
    print("=" * 60)
    print("           CRICFIT AI - UNIFIED LAUNCHER           ")
    print("=" * 60)
    print(f" [CONFIG] Project Root : {PROJECT_ROOT}")
    print(f" [CONFIG] Python Exec  : {python_exe}")
    print(f" [CONFIG] Backend URL  : http://{BACKEND_HOST}:{BACKEND_PORT}")
    print(f" [CONFIG] Streamlit URL: http://localhost:{STREAMLIT_PORT}")
    print("=" * 60)

    # 1. Start FastAPI backend
    print("\n[1/2] Starting FastAPI backend (uvicorn)...")
    backend_cmd = [
        python_exe,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        BACKEND_HOST,
        "--port",
        str(BACKEND_PORT),
    ]

    try:
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=PROJECT_ROOT,
            env=os.environ.copy()
        )
        subprocesses.append((backend_proc, "FastAPI Backend"))
    except Exception as e:
        print(f" [ERROR] Failed to start FastAPI backend: {e}")
        sys.exit(1)

    # 2. Health check verification before launching Streamlit
    is_ready = wait_for_backend(backend_proc, BACKEND_HEALTH_URL, max_retries=30, delay=0.5)
    if not is_ready:
        print("\n [WARNING] FastAPI backend did not respond to health checks in time.")
        print("          Streamlit will still launch, but backend-dependent features")
        print("          (such as live Injury Analysis) may fail until backend is up.")
    else:
        print(f" [OK] FastAPI backend is live and healthy at {BACKEND_HEALTH_URL}!")

    # 3. Start Streamlit frontend
    print("\n[2/2] Starting Streamlit frontend...")
    frontend_cmd = [
        python_exe,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        str(STREAMLIT_PORT),
        "--server.headless",
        "false",
    ]

    try:
        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=PROJECT_ROOT,
            env=os.environ.copy()
        )
        subprocesses.append((frontend_proc, "Streamlit Frontend"))
    except Exception as e:
        print(f" [ERROR] Failed to start Streamlit frontend: {e}")
        terminate_processes()
        sys.exit(1)

    print("\n" + "=" * 60)
    print(" [READY] Both CRICFIT AI services are now running!")
    print(f"         - Streamlit App : http://localhost:{STREAMLIT_PORT}")
    print(f"         - FastAPI Docs  : http://{BACKEND_HOST}:{BACKEND_PORT}/docs")
    print("         Press Ctrl+C in this terminal to stop both services.")
    print("=" * 60 + "\n")

    # Keep running and monitor child processes
    try:
        while True:
            # Check if any process died
            for proc, name in subprocesses:
                ret = proc.poll()
                if ret is not None:
                    print(f"\n [ALERT] {name} exited with return code {ret}.")
                    terminate_processes()
                    return
            time.sleep(1)
    except KeyboardInterrupt:
        terminate_processes()

if __name__ == "__main__":
    main()
