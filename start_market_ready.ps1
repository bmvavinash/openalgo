# Market Ready Startup Script
# Starts server, verifies paper trading, disables scalping, starts strategies, and monitors

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MARKET READY STARTUP" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify Paper Trading Mode
Write-Host "[1/6] Verifying Paper Trading Mode..." -ForegroundColor Yellow
& ".\venv\Scripts\python.exe" verify_and_enable_paper_trading.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Failed to enable paper trading mode" -ForegroundColor Red
    exit 1
}
Write-Host "  OK - Paper Trading Mode Enabled" -ForegroundColor Green
Write-Host ""

# Step 2: Disable Scalping in All Strategies
Write-Host "[2/6] Disabling scalping in all strategies..." -ForegroundColor Yellow
& ".\venv\Scripts\python.exe" -c @"
import sys
import os
sys.path.insert(0, os.getcwd())
from app import create_app
from blueprints.python_strategy import STRATEGY_CONFIGS, load_configs, ENV_FILE
import json

app = create_app()
with app.app_context():
    load_configs()
    env_vars = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            env_vars = json.load(f)
    
    disabled = 0
    for strategy_id, config in STRATEGY_CONFIGS.items():
        strategy_env = env_vars.get(strategy_id, {})
        if strategy_env.get('STRATEGY_SCALPING_ENABLED', 'false').lower() != 'false':
            strategy_env['STRATEGY_SCALPING_ENABLED'] = 'false'
            env_vars[strategy_id] = strategy_env
            disabled += 1
    
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        json.dump(env_vars, f, indent=2, ensure_ascii=False)
    
    print(f'  OK - Scalping disabled in {disabled} strategy(ies)')
"@
Write-Host ""

# Step 3: Check if server is running
Write-Host "[3/6] Checking server status..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "  OK - Server is running" -ForegroundColor Green
    }
} catch {
    Write-Host "  WARNING - Server is not running" -ForegroundColor Yellow
    Write-Host "  Starting server in new window..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; .\venv\Scripts\Activate.ps1; python app.py"
    Start-Sleep -Seconds 5
    Write-Host "  OK - Server started" -ForegroundColor Green
}
Write-Host ""

# Step 4: Start All Strategies
Write-Host "[4/6] Starting all strategies..." -ForegroundColor Yellow
& ".\venv\Scripts\python.exe" start_server_and_strategies.py
Write-Host ""

# Step 5: Test Price Fetching
Write-Host "[5/6] Testing price fetching..." -ForegroundColor Yellow
& ".\venv\Scripts\python.exe" -c @"
import sys
import os
sys.path.insert(0, os.getcwd())
from app import create_app
from services.quotes_service import get_quotes
from database.auth_db import ApiKeys, decrypt_token

app = create_app()
with app.app_context():
    api_key_obj = ApiKeys.query.first()
    api_key = decrypt_token(api_key_obj.api_key_encrypted) if api_key_obj else None
    
    test_symbols = [('NIFTY', 'NSE_INDEX'), ('BANKNIFTY', 'NSE_INDEX')]
    success = 0
    for symbol, exchange in test_symbols:
        try:
            success_flag, response, status = get_quotes(symbol=symbol, exchange=exchange, api_key=api_key)
            if success_flag and response.get('data', {}).get('ltp', 0) > 0:
                ltp = response['data']['ltp']
                print(f'  OK - {symbol}: LTP = {ltp:.2f}')
                success += 1
            else:
                print(f'  WARNING - {symbol}: Price fetch failed')
        except Exception as e:
            print(f'  WARNING - {symbol}: {e}')
    
    if success > 0:
        print(f'  OK - Price fetching working for {success}/{len(test_symbols)} symbols')
    else:
        print('  WARNING - Price fetching may have issues')
"@
Write-Host ""

# Step 6: Start Monitoring
Write-Host "[6/6] Starting continuous monitoring..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SYSTEM READY FOR MARKET HOURS" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting log monitor in new window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; .\venv\Scripts\Activate.ps1; python start_and_monitor_market.py"
Write-Host ""
Write-Host "Monitoring will:" -ForegroundColor Cyan
Write-Host "  - Check logs every 30 seconds" -ForegroundColor White
Write-Host "  - Auto-fix errors as they appear" -ForegroundColor White
Write-Host "  - Monitor all strategy logs" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to exit this script (monitoring will continue)..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")








