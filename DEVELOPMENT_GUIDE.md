# Development Guide - OpenAlgo

## Template Auto-Reload (UI Changes)

### Issue
UI changes (HTML templates) require server restart to be visible, even after hard refresh.

### Solution
**Template auto-reload is now enabled in debug mode.** When `FLASK_DEBUG=True`:
- Templates automatically reload on file changes
- Static files are not cached
- No server restart needed for UI changes

### How to Enable Debug Mode
Set environment variable:
```bash
# Windows PowerShell
$env:FLASK_DEBUG="True"

# Or in .env file
FLASK_DEBUG=True
```

### Backend Changes
- **Python code changes**: Require server restart (Flask doesn't auto-reload Python files)
- **Template changes**: Auto-reload in debug mode (no restart needed)
- **Static files (CSS/JS)**: Auto-reload in debug mode (no restart needed)

## Execution Engine

### Purpose
The execution engine monitors pending orders and executes them when conditions are met (price triggers, market conditions).

### Status Check
Run: `python check_system_status.py`

### Start Execution Engine
1. Via UI: Go to `/settings/services` and start "Execution Engine"
2. Via Code: It auto-starts when analyzer mode is enabled (on server startup)

### Why Trades Aren't Showing
If you see orders but no trades:
1. **Check execution engine status** - Must be running
2. **Check order status** - Orders must be "open" (not "complete" or "rejected")
3. **Check quotes service** - Execution engine needs live quotes to execute orders
4. **Check market hours** - Some strategies only run during market hours

## Strategy Logs

### Location
`log/strategies/` directory

### Check Logs
```bash
# List recent log files
Get-ChildItem "log\strategies" -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 10

# View specific log
Get-Content "log\strategies\<strategy_name>_<timestamp>.log" -Tail 50
```

### Empty Logs (0 bytes)
If log files are empty:
1. Strategy process may have crashed
2. Check if strategy is actually running
3. Restart the strategy

## Restart Procedures

### Server Restart
```bash
# Stop server (Ctrl+C in terminal)
# Then start:
python app.py
```

### Strategy Restart
```bash
# Restart all strategies
python restart_strategies.py

# Or via UI: /python -> Restart All Strategies
```

### Full System Restart
1. Stop server (Ctrl+C)
2. Restart server: `python app.py`
3. Wait for execution engine to start (check logs)
4. Restart strategies: `python restart_strategies.py`

## Monitoring

### System Status
```bash
python check_system_status.py
```

Shows:
- Current mode (Analyze/Live)
- Execution engine status
- Order counts (total, open, complete)
- Trade counts (total, today)
- Position counts

### Server Logs
Main log: `log/openalgo_<date>.log`

### Strategy Logs
Individual logs: `log/strategies/<strategy_id>_<timestamp>.log`

## Common Issues

### 1. UI Changes Not Visible
- **Solution**: Enable `FLASK_DEBUG=True` and templates will auto-reload
- **Note**: Still need restart for Python code changes

### 2. No Trades Executing
- **Check**: Execution engine status (`check_system_status.py`)
- **Fix**: Start execution engine via `/settings/services`

### 3. Strategies Not Placing Orders
- **Check**: Strategy logs for errors
- **Check**: API key configuration
- **Check**: Paper trading mode settings (broker auth not needed)

### 4. Empty Strategy Logs
- **Check**: Strategy process status
- **Fix**: Restart the strategy

## Best Practices

1. **Always check execution engine** before expecting trades
2. **Monitor strategy logs** regularly
3. **Use `check_system_status.py`** to diagnose issues
4. **Enable debug mode** during development for auto-reload
5. **Restart server** after Python code changes
6. **Restart strategies** after strategy code changes






