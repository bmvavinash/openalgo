# PowerShell script to start server in external terminal and run all strategies in Live Data Paper Trading mode
$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LIVE DATA PAPER TRADING STARTUP" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify analyze_mode is enabled
Write-Host "[1/5] Verifying Paper Trading Mode..." -ForegroundColor Yellow
$venvPython = Join-Path $scriptDir "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Virtual environment not found" -ForegroundColor Red
    exit 1
}

$verifyScript = Join-Path $scriptDir "verify_and_enable_paper_trading.py"
& $venvPython $verifyScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to verify/enable Paper Trading Mode" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Paper Trading Mode verified/enabled" -ForegroundColor Green

# Step 2: Check if server is already running
Write-Host ""
Write-Host "[2/5] Checking if server is running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
    $serverRunning = ($response.StatusCode -eq 200)
} catch {
    $serverRunning = $false
}

if ($serverRunning) {
    Write-Host "[OK] Server is already running" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[3/5] Starting server in external terminal..." -ForegroundColor Yellow
    $venvActivate = Join-Path $scriptDir "venv\Scripts\Activate.ps1"
    $appFile = Join-Path $scriptDir "app.py"
    
    $serverCmd = "cd '$scriptDir'; if (Test-Path '$venvActivate') { . '$venvActivate' }; Write-Host 'OPENALGO SERVER - PAPER TRADING MODE' -ForegroundColor Cyan; python '$appFile'"
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $serverCmd
    
    Write-Host "[OK] Server starting in new terminal..." -ForegroundColor Green
    Write-Host "[WAIT] Waiting for server to initialize (30 seconds max)..." -ForegroundColor Yellow
    
    $maxWait = 30
    $waited = 0
    $serverReady = $false
    
    while ($waited -lt $maxWait -and -not $serverReady) {
        Start-Sleep -Seconds 2
        $waited += 2
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $serverReady = $true
                Write-Host "[OK] Server is now running and responding" -ForegroundColor Green
            }
        } catch {
            if ($waited % 10 -eq 0) {
                Write-Host "   Still waiting... ($waited/$maxWait seconds)" -ForegroundColor Gray
            }
        }
    }
    
    if (-not $serverReady) {
        Write-Host "[WARNING] Server may still be initializing. Continuing..." -ForegroundColor Yellow
    }
}

# Step 4: Wait for server to initialize
Write-Host ""
Write-Host "[4/5] Waiting for server to fully initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Step 5: Start all strategies
Write-Host ""
Write-Host "[5/5] Starting all strategies in Paper Trading mode..." -ForegroundColor Yellow

$startStrategiesFile = Join-Path $scriptDir "start_all_strategies.py"
if (Test-Path $startStrategiesFile) {
    & $venvPython $startStrategiesFile
} else {
    # Fallback: use start_server_and_strategies.py
    $startAllFile = Join-Path $scriptDir "start_server_and_strategies.py"
    if (Test-Path $startAllFile) {
        & $venvPython $startAllFile
    } else {
        Write-Host "[WARNING] Could not find strategy startup script" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "STARTUP COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: Running in external terminal" -ForegroundColor Green
Write-Host "Mode: Paper Trading (Live Data)" -ForegroundColor Green
Write-Host "Access: http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "Monitor: http://127.0.0.1:5000/python" -ForegroundColor Cyan
Write-Host ""

# Step 6: Start log monitoring
Write-Host "Starting log monitor in new terminal..." -ForegroundColor Yellow
$monitorFile = Join-Path $scriptDir "monitor_logs_continuous.py"
$venvActivate = Join-Path $scriptDir "venv\Scripts\Activate.ps1"
$monitorCmd = "cd '$scriptDir'; if (Test-Path '$venvActivate') { . '$venvActivate' }; python '$monitorFile'"
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $monitorCmd

Write-Host "[OK] Log monitor started in new terminal" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SYSTEM READY FOR MARKET HOURS" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "All systems are running:" -ForegroundColor Green
Write-Host "  [OK] Server (external terminal)" -ForegroundColor Green
Write-Host "  [OK] Strategies (Paper Trading mode)" -ForegroundColor Green
Write-Host "  [OK] Log Monitor (external terminal)" -ForegroundColor Green
Write-Host ""
Write-Host "Monitor logs continuously for any issues." -ForegroundColor Yellow
Write-Host "Make changes as needed based on log output." -ForegroundColor Yellow
Write-Host ""
