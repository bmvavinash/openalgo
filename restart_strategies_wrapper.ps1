# Wrapper script to run restart_strategies.py with unbuffered output
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESTART STRATEGIES WRAPPER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

if (Test-Path "venv\Scripts\Activate.ps1") {
    & ".\venv\Scripts\Activate.ps1"
}

Write-Host "[WRAPPER] Running restart_strategies.py with unbuffered output..." -ForegroundColor Yellow
Write-Host ""

# Run Python with -u flag for unbuffered output
python -u restart_strategies.py

$exitCode = $LASTEXITCODE
Write-Host ""
Write-Host "[WRAPPER] Script completed with exit code: $exitCode" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Red" })






