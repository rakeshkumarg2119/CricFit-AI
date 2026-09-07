<#
.SYNOPSIS
    CRICFIT AI - PowerShell Launcher
.DESCRIPTION
    Starts the FastAPI backend and Streamlit frontend in one command.
.PARAMETER Separate
    If specified, launches services in separate terminal windows instead of unified mode.
.EXAMPLE
    .\run_project.ps1
.EXAMPLE
    .\run_project.ps1 -Separate
#>
param(
    [switch]$Separate
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "           CRICFIT AI - PowerShell Launcher        " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Activate Virtual Environment if present
$venvActivate = Join-Path $PSScriptRoot "venv\Scripts\Activate.ps1"
$dotVenvActivate = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"

if (Test-Path $venvActivate) {
    Write-Host "[INFO] Activating virtual environment (venv)..." -ForegroundColor DarkCyan
    & $venvActivate
} elseif (Test-Path $dotVenvActivate) {
    Write-Host "[INFO] Activating virtual environment (.venv)..." -ForegroundColor DarkCyan
    & $dotVenvActivate
} else {
    Write-Host "[INFO] No virtual environment folder detected, using system Python." -ForegroundColor DarkGray
}

if ($Separate) {
    Write-Host "`n[1/2] Starting FastAPI backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot'; python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

    Write-Host "[INFO] Waiting 3 seconds for backend initialization..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 3

    Write-Host "[2/2] Starting Streamlit frontend on http://localhost:8501..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot'; streamlit run frontend/app.py"

    Write-Host "`n[OK] Both services launched in separate windows!" -ForegroundColor Green
    Write-Host "     - FastAPI Backend : http://127.0.0.1:8000" -ForegroundColor White
    Write-Host "     - Streamlit App   : http://localhost:8501" -ForegroundColor White
} else {
    # Default: Run the unified cross-platform launcher
    $launcherPy = Join-Path $PSScriptRoot "run_project.py"
    if (Test-Path $launcherPy) {
        python $launcherPy @args
    } else {
        Write-Error "run_project.py not found in $PSScriptRoot."
    }
}
