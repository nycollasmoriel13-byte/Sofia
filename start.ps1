# ─── Sofia + Dashboard — Startup Script ──────────────────────────────────────
# Uso: clique com o botão direito → "Executar com PowerShell"
# Ou no terminal: .\start.ps1

$root = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SOFIA — Iniciando servicos..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ── 1. Matar processos antigos nas portas 8000 e 8501 ─────────────────────────
foreach ($port in @(8000, 8501)) {
    $connections = netstat -ano | Select-String ":$port\s" | Select-String "LISTENING"
    foreach ($line in $connections) {
        if ($line -match '\s(\d+)$') {
            $pid = [int]$Matches[1]
            if ($pid -gt 0) {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  [OK] Processo antigo PID $pid (porta $port) encerrado." -ForegroundColor Yellow
                Start-Sleep -Seconds 1
            }
        }
    }
}

Write-Host ""

# ── 2. Iniciar Sofia (main.py) ─────────────────────────────────────────────────
Write-Host "  [>>] Iniciando Sofia (porta 8000)..." -ForegroundColor Green
$sofia = Start-Process -FilePath "$root\.venv\Scripts\python.exe" `
    -ArgumentList "$root\main.py" `
    -WorkingDirectory $root `
    -PassThru -WindowStyle Normal
Write-Host "  [OK] Sofia iniciada — PID $($sofia.Id)" -ForegroundColor Green

Start-Sleep -Seconds 3

# ── 3. Iniciar Dashboard Streamlit (porta 8501) ────────────────────────────────
Write-Host "  [>>] Iniciando Dashboard (porta 8501)..." -ForegroundColor Green
$dashboard = Start-Process -FilePath "$root\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "streamlit", "run", "$root\dashboard.py", `
                  "--server.port", "8501", "--server.headless", "true" `
    -WorkingDirectory $root `
    -PassThru -WindowStyle Normal
Write-Host "  [OK] Dashboard iniciado — PID $($dashboard.Id)" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PRONTO!" -ForegroundColor Cyan
Write-Host "  Sofia:     http://localhost:8000" -ForegroundColor White
Write-Host "  Dashboard: http://localhost:8501" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
