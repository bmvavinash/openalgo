# Data Mode Implementation Summary

## Overview
Implemented a configurable Live/Historical data mode system with UI controls.

## Changes Made

### 1. Database Schema (`database/settings_db.py`)
Added new columns to `Settings` table:
- `data_mode`: 'live' or 'historical' (default: 'live')
- `historical_duration`: Duration for historical mode ('current_day', 'previous_day', 'current_week', 'previous_week', 'current_month', '6_months', '1_year')
- `historical_data_source`: 'yfinance' or 'database' (default: 'yfinance')

Added functions:
- `get_data_mode_settings()`: Get current data mode configuration
- `set_data_mode_settings()`: Update data mode configuration

### 2. History Service (`services/history_service.py`)
Updated to:
- Check data mode settings before fetching data
- Force LIVE mode when `end_date` is today (always use current market data)
- Improved yfinance data fetching:
  - Try `period='5d'` first (most reliable for NIFTY/BANKNIFTY)
  - Fallback to `period='1d'` then `period='1mo'`
  - Use `ticker.info` as final fallback for current price
- Better error handling and logging

### 3. Settings API (`blueprints/settings.py`)
Added new endpoints:
- `GET /settings/data-mode`: Get current data mode settings
- `POST /settings/data-mode`: Update data mode settings

Request body for POST:
```json
{
  "data_mode": "live" | "historical",
  "historical_duration": "current_day" | "previous_day" | "current_week" | "previous_week" | "current_month" | "6_months" | "1_year",
  "historical_data_source": "yfinance" | "database"
}
```

## How It Works

### Live Mode (Default)
- Always fetches current/live market data from yfinance
- When `end_date` is today, forces LIVE mode regardless of setting
- Uses `period='5d'` for intraday data (most reliable)
- Falls back to `ticker.info` if history() fails

### Historical Mode
- Uses configured `historical_duration` to determine date range
- Uses `historical_data_source` to choose:
  - `yfinance`: Fetch from yfinance API
  - `database`: Use trades from database (future implementation)

### Data Source Options

#### yfinance (Default)
- Fetches market data from Yahoo Finance
- Supports: NIFTY (^NSEI), BANKNIFTY (^NSEBANK), FINNIFTY, MIDCPNIFTY
- Also supports stocks with `.NS` suffix

#### database (Future)
- Will use trades stored in `SandboxTrades` table
- Useful for backtesting with actual executed trades

## UI Integration

To add UI controls, create a form in settings page:

```html
<!-- Data Mode Toggle -->
<select id="dataMode">
  <option value="live">Live Data</option>
  <option value="historical">Historical Data</option>
</select>

<!-- Historical Duration (shown when historical selected) -->
<select id="historicalDuration">
  <option value="current_day">Current Day</option>
  <option value="previous_day">Previous Day</option>
  <option value="current_week">Current Week</option>
  <option value="previous_week">Previous Week</option>
  <option value="current_month">Current Month</option>
  <option value="6_months">6 Months</option>
  <option value="1_year">1 Year</option>
</select>

<!-- Data Source (shown when historical selected) -->
<select id="historicalDataSource">
  <option value="yfinance">Yahoo Finance (yfinance)</option>
  <option value="database">Database Trades</option>
</select>
```

JavaScript:
```javascript
// Load current settings
fetch('/settings/data-mode')
  .then(r => r.json())
  .then(data => {
    document.getElementById('dataMode').value = data.data_mode;
    document.getElementById('historicalDuration').value = data.historical_duration;
    document.getElementById('historicalDataSource').value = data.historical_data_source;
  });

// Save settings
function saveDataMode() {
  fetch('/settings/data-mode', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      data_mode: document.getElementById('dataMode').value,
      historical_duration: document.getElementById('historicalDuration').value,
      historical_data_source: document.getElementById('historicalDataSource').value
    })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      alert('Data mode settings saved!');
    }
  });
}
```

## Testing

1. **Test Live Mode**:
   ```bash
   curl -X POST http://localhost:5000/settings/data-mode \
     -H "Content-Type: application/json" \
     -d '{"data_mode": "live"}'
   ```

2. **Test Historical Mode**:
   ```bash
   curl -X POST http://localhost:5000/settings/data-mode \
     -H "Content-Type: application/json" \
     -d '{"data_mode": "historical", "historical_duration": "current_week", "historical_data_source": "yfinance"}'
   ```

3. **Check Current Settings**:
   ```bash
   curl http://localhost:5000/settings/data-mode
   ```

## Notes

- **Default**: System defaults to LIVE mode
- **Auto-override**: When `end_date` is today, LIVE mode is forced (ensures current data)
- **yfinance Reliability**: Using `period='5d'` first improves reliability for NIFTY/BANKNIFTY
- **Future Enhancement**: Database source will use actual executed trades for backtesting






