# Monitor System Status Script
# Checks server, execution engine, and strategies

Write-Host "========================================"
Write-Host "SYSTEM MONITORING - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "========================================"

# Check server
Write-Host "`n[1] Server Status:"
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -TimeoutSec 5 -UseBasicParsing
    Write-Host "  [OK] Server is running (Status: $($response.StatusCode))"
} catch {
    Write-Host "  [ERROR] Server is not responding"
}

# Check execution engine
Write-Host "`n[2] Execution Engine:"
cd "F:\2nd Income\Stock Market\Code\openalgo"
if (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
    $result = python -c "from sandbox.execution_thread import is_execution_engine_running; print('Running' if is_execution_engine_running() else 'Not Running')" 2>&1
    Write-Host "  Status: $result"
}

# Check today's orders/trades
Write-Host "`n[3] Today's Activity:"
$orders = python -c "from database.sandbox_db import SandboxOrders; from database.sandbox_db import db_session; from datetime import datetime, date; import pytz; ist = pytz.timezone('Asia/Kolkata'); today = date.today(); start = ist.localize(datetime.combine(today, datetime.min.time())); orders = db_session.query(SandboxOrders).filter(SandboxOrders.order_timestamp >= start).all(); print(len(orders))" 2>&1
$trades = python -c "from database.sandbox_db import SandboxTrades; from database.sandbox_db import db_session; from datetime import datetime, date; import pytz; ist = pytz.timezone('Asia/Kolkata'); today = date.today(); start = ist.localize(datetime.combine(today, datetime.min.time())); trades = db_session.query(SandboxTrades).filter(SandboxTrades.trade_timestamp >= start).all(); print(len(trades))" 2>&1
Write-Host "  Orders: $orders"
Write-Host "  Trades: $trades"

# Check strategy logs
Write-Host "`n[4] Strategy Logs (Latest):"
$latestLog = Get-ChildItem "log\strategies\*$(Get-Date -Format 'yyyyMMdd')*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($latestLog) {
    Write-Host "  Latest: $($latestLog.Name)"
    Write-Host "  Last Updated: $($latestLog.LastWriteTime)"
    if ($latestLog.Length -gt 0) {
        $lastLines = Get-Content $latestLog.FullName -Tail 3
        Write-Host "  Last 3 lines:"
        $lastLines | ForEach-Object { Write-Host "    $_" }
    }
} else {
    Write-Host "  [WARNING] No strategy logs found for today"
}

Write-Host "`n========================================"




