# How to Restart Strategies

## Option 1: Via UI (Easiest)
1. Open browser and go to: `http://127.0.0.1:5000/python`
2. Click the **"Restart All Strategies"** button
3. Wait for all strategies to restart
4. Check the logs to verify they're using the new code

## Option 2: Restart Flask Server
If you restart the Flask server, all strategies will automatically restart with the new code:
1. Stop the Flask server (Ctrl+C in the terminal where it's running)
2. Start it again: `python app.py` or `flask run`
3. All strategies will restart automatically

## What the Fixes Do
After restart, the strategies will:
- ✅ Use fallback LTP in analyze mode (even with invalid API key)
- ✅ Generate synthetic strikes automatically for paper trading
- ✅ Place orders successfully in paper trading mode

## Verify It's Working
After restart, check the logs:
```powershell
Get-ChildItem -Path "log\strategies" -Filter "option_*_strategy_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 3 | ForEach-Object { Write-Host "`n=== $($_.Name) ==="; Get-Content $_.FullName -Tail 30 }
```

You should see:
- No more "Invalid openalgo apikey" errors (or they're handled gracefully)
- Synthetic strikes being generated
- Orders being placed successfully


