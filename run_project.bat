@echo off
setlocal enabledelayedexpansion

title CRICFIT AI Launcher
cd /d "%~dp0"

echo ===================================================
echo             CRICFIT AI - Windows Launcher
echo ===================================================

:: 1. Activate Virtual Environment if present
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment (venv)...
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment (.venv)...
    call ".venv\Scripts\activate.bat"
) else (
    echo [INFO] No virtual environment folder detected, using system Python.
)

:: 2. Check for optional --separate parameter
if "%1"=="--separate" goto separate_windows
if "%1"=="-s" goto separate_windows

:: 3. Default: Start services via Python unified launcher
::    Provides automated health check, live logs, and clean Ctrl+C shutdown
if exist "run_project.py" (
    python run_project.py %*
    goto end
)

:separate_windows
echo.
echo [1/2] Starting FastAPI backend on http://127.0.0.1:8000 ...
start "CRICFIT AI - FastAPI Backend" cmd /k "title CRICFIT AI Backend && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

echo [INFO] Waiting for FastAPI backend to initialize...
timeout /t 3 /nobreak >nul

echo [2/2] Starting Streamlit frontend on http://localhost:8501 ...
start "CRICFIT AI - Streamlit Frontend" cmd /k "title CRICFIT AI Frontend && streamlit run frontend/app.py"

echo.
echo ===================================================
echo  Both services launched in separate windows!
echo   - FastAPI Backend  : http://127.0.0.1:8000
echo   - Streamlit App    : http://localhost:8501
echo ===================================================

:end
