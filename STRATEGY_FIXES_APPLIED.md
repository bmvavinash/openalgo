# Strategy Fixes Applied

## Issues Fixed

### 1. ✅ Format Specifier Error in RSI Strategy
**Error**: `ValueError: Invalid format specifier '.2f if signals['rsi'] else 'N/A''`

**Fixed in**: `strategies/scripts/rsi_strategy_20251203094216.py` (Line 163)

**Before**:
```python
logger.debug(f"{symbol} - Position: {current_position}, RSI: {signals['rsi']:.2f if signals['rsi'] else 'N/A'}")
```

**After**:
```python
rsi_display = f"{signals['rsi']:.2f}" if signals['rsi'] is not None else 'N/A'
logger.debug(f"{symbol} - Position: {current_position}, RSI: {rsi_display}")
```

### 2. ⚠️ API Key Issue - Needs Manual Configuration

**Problem**: Strategy is getting "Invalid openalgo apikey" error when placing orders.

**Root Cause**: The strategy reads API key from `OPENALGO_API_KEY` environment variable, but:
- The environment variable might not be set
- The environment variable might have an outdated/wrong API key
- The API key needs to be retrieved from the database

**Solution**: Set the API key in the environment variable or configure it in the Python Strategy system.

## How to Fix API Key for Strategies

### Option 1: Set Environment Variable (For Direct Execution)

1. **Get your API key**:
   - Login: `http://127.0.0.1:5000/auth/login`
   - Go to: `http://127.0.0.1:5000/apikey`
   - Copy your API key

2. **Set environment variable** (Windows PowerShell):
   ```powershell
   $env:OPENALGO_API_KEY="your_api_key_here"
   ```

3. **Restart the strategy** (if running directly)

### Option 2: Configure in Python Strategy System (Recommended)

1. **Login**: `http://127.0.0.1:5000/auth/login`
2. **Go to**: `http://127.0.0.1:5000/python`
3. **Find your strategy** (RSI Strategy)
4. **Click "Edit" or "Configure"**
5. **Add environment variable**:
   - Key: `OPENALGO_API_KEY`
   - Value: Your API key (get it from `/apikey`)
6. **Save and restart the strategy**

### Option 3: Update Strategy File Directly

Edit `strategies/scripts/rsi_strategy_20251203094216.py`:

```python
# Line 56-57
API_KEY = os.getenv('OPENALGO_API_KEY', 'your_api_key_here')  # Replace with your actual key
```

**⚠️ Warning**: This is not recommended as it hardcodes the API key in the file.

## Verification

After setting the API key, you should see in strategy logs:
```
[INFO] API key found: dff4df2521...0cef (length: 64)
[INFO] Order placed: BUY 1 NIFTY - Response: {'status': 'success', 'orderid': 'SB-...'}
```

Instead of:
```
[WARNING] No API key found in OPENALGO_API_KEY environment variable.
[INFO] Order placed: BUY 1 NIFTY - Response: {'status': 'error', 'message': 'Invalid openalgo apikey'}
```

## Orders and Trades Display

### Why No Records Show?

If you see "No records to display" in orderbook/tradebook:

1. **Orders are failing** due to invalid API key → Fix API key (see above)
2. **Orders are being placed** but in sandbox → Check sandbox orders
3. **Orders are successful** but not showing → Check:
   - Are you in paper trading mode? (Check Settings → Analyzer Mode)
   - Are orders being placed in sandbox? (Check `/analyzer` page)
   - Is the API key valid? (Check `/apikey` page)

### Expected Behavior

- **Paper Trading Mode (Analyzer ON)**:
  - Orders go to sandbox
  - Check orderbook/tradebook at `/orders/orderbook` and `/orders/tradebook`
  - Should show sandbox orders if API key is valid

- **Live Trading Mode (Analyzer OFF)**:
  - Orders go to live broker
  - Requires broker authentication
  - Check orderbook/tradebook for live orders

## Next Steps

1. ✅ **Format specifier error** - FIXED
2. ⚠️ **API key configuration** - NEEDS MANUAL SETUP
3. ⚠️ **Verify orders are being placed** - TEST AFTER API KEY IS SET
4. ⚠️ **Check orderbook/tradebook** - VERIFY AFTER ORDERS ARE PLACED

## Testing Checklist

- [ ] API key is set in environment or strategy config
- [ ] Strategy logs show "API key found" message
- [ ] Orders are being placed successfully (check logs)
- [ ] Orderbook shows orders at `/orders/orderbook`
- [ ] Tradebook shows trades at `/orders/tradebook`
- [ ] Positions show at `/orders/positions`

## Current Status

- ✅ Format specifier error: **FIXED**
- ⚠️ API key error: **NEEDS CONFIGURATION** (see instructions above)
- ⚠️ Orders display: **DEPENDS ON API KEY BEING VALID**



