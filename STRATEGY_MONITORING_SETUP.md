# Strategy Monitoring Setup

## ✅ Completed Actions

1. **Fixed Session Error**: Fixed `NameError: name 'daily_expiry' is not defined` in `utils/session.py`
2. **Started Flask Server**: Server is running in background
3. **Checked Strategy Status**: Found 5 configured strategies
4. **Started All Strategies**: 
   - EMA Crossover NIFTY
   - Multi Indicator Strategy
   - EMA SL Crossover (was already running)
   - Macd
   - RSI strategy

## 📊 Current Status

### Strategies Running:
- **EMA SL Crossover** (PID: 16496) - Running
- **EMA Crossover NIFTY** (PID: 7548) - Just started
- **Multi Indicator Strategy** (PID: 20964) - Just started
- **Macd** (PID: 18540) - Just started
- **RSI strategy** (PID: 21344) - Just started

### Monitoring:
- **Continuous Monitor**: Running in background (checks every 30 seconds)
- **Monitor Script**: `continuous_monitor.py` - Monitors strategy status and logs

## 🔧 Scripts Created

### 1. `monitor_strategies.py`
- Check strategy status once or continuously
- Shows running/stopped status
- Displays recent log lines
- Usage:
  ```bash
  python monitor_strategies.py --once          # Check once
  python monitor_strategies.py --interval 60   # Check every 60 seconds
  ```

### 2. `start_all_strategies.py`
- Checks all strategies
- Starts any that aren't running
- Updates strategy configs
- Usage:
  ```bash
  python start_all_strategies.py
  ```

### 3. `continuous_monitor.py`
- Continuous monitoring with regular intervals
- Shows strategy status and recent logs
- Usage:
  ```bash
  python continuous_monitor.py --interval 30  # Check every 30 seconds
  python continuous_monitor.py --once          # Check once
  ```

## 📝 Monitoring Commands

### Check Strategy Status:
```bash
cd "F:\2nd Income\Stock Market\Code\openalgo"
. venv\Scripts\Activate.ps1
python monitor_strategies.py --once
```

### Start All Strategies:
```bash
cd "F:\2nd Income\Stock Market\Code\openalgo"
. venv\Scripts\Activate.ps1
python start_all_strategies.py
```

### Continuous Monitoring:
```bash
cd "F:\2nd Income\Stock Market\Code\openalgo"
. venv\Scripts\Activate.ps1
python continuous_monitor.py --interval 30
```

## 📍 Log Files Location

Strategy logs are stored in:
```
log/strategies/
```

Each strategy creates a new log file with timestamp:
- Format: `{strategy_id}_{YYYYMMDD}_{HHMMSS}_IST.log`
- Example: `rsi_strategy_20251203094216_20251209_092546_IST.log`

## ⚠️ Important Notes

1. **Server Must Be Running**: Strategies need the Flask server to be running for API calls
2. **API Key Required**: Strategies need `OPENALGO_API_KEY` environment variable set
3. **Python Path**: Strategies are started with correct PYTHONPATH to find modules
4. **Process Monitoring**: Monitor checks if processes are actually running (not just marked as running)

## 🔍 Troubleshooting

### If strategies keep crashing:
1. Check log files in `log/strategies/`
2. Verify server is running: `Get-Process python`
3. Check API key is set: `echo $env:OPENALGO_API_KEY`
4. Verify Python path is correct

### If strategies show as running but aren't:
- The monitor script will detect dead processes
- Run `start_all_strategies.py` to restart them

### To view logs:
```bash
Get-Content "log\strategies\{strategy_id}_*.log" -Tail 50
```

## 📊 Next Steps

1. ✅ Server is running
2. ✅ Strategies are started
3. ✅ Monitoring is active
4. ⏳ Monitor logs for any errors
5. ⏳ Verify strategies are placing orders (if API key is configured)


