# CricFit AI — Start both servers
# Run from the project root: .\start.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CRICFIT AI — Starting Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Start FastAPI backend in a new window
Write-Host "`n[1/2] Starting FastAPI backend on http://127.0.0.1:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\Users\VARSHINI\hackathon'; python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

# Give FastAPI a moment to boot
Start-Sleep -Seconds 3

# Start Streamlit frontend in a new window
Write-Host "[2/2] Starting Streamlit frontend on http://localhost:8501 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\Users\VARSHINI\hackathon'; streamlit run app.py"

Write-Host "`n? Both services launched." -ForegroundColor Green
Write-Host "   FastAPI  -> http://127.0.0.1:8000" -ForegroundColor White
Write-Host "   FastAPI docs -> http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "   Streamlit   -> http://localhost:8501" -ForegroundColor White
