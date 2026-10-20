# PR Agent Startup Script for Windows PowerShell
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   PR Agent Runner" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start FastAPI backend in background (with auto-managed Ollama lifecycle)
Write-Host "[1/2] Launching FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Green
$backendProc = Start-Process python -ArgumentList "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000" -PassThru

Start-Sleep -Seconds 2

# 2. Start Frontend Vite Dev Server and trap shutdown signals
Write-Host "[2/2] Launching React/Vite Frontend on http://localhost:5173..." -ForegroundColor Green
Set-Location frontend

try {
    npm run dev
} finally {
    Write-Host "`n[SHUTDOWN] Stopping PR Agent services..." -ForegroundColor Yellow
    if ($backendProc -and -not $backendProc.HasExited) {
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    }
    python -c "from backend.ollama_service import ollama_service; ollama_service.stop_ollama()" -ErrorAction SilentlyContinue
    Write-Host "[SHUTDOWN] PR Agent and Ollama background processes stopped cleanly." -ForegroundColor Green
}
