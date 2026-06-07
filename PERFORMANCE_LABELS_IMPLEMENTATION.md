# Performance Labels Implementation Summary

## Overview
This document summarizes the implementation of performance labels and tracking system for trading strategies in the OpenAlgo platform.

## Features Implemented

### 1. Performance Labels in UI
- **Location**: Strategy cards in `/python` route
- **Labels Displayed**:
  - `PROFITABLE` (green badge) - Strategies with positive PnL
  - `LOSING` (red badge) - Strategies with negative PnL
  - `NEUTRAL` (yellow badge) - Strategies with zero PnL
  - Strategy Type badges: `OPTIONS` or `INTRADAY`

### 2. Performance Metrics Display
Each strategy card now shows:
- **PnL**: Total profit/loss in last 30 days
- **PnL %**: Percentage profit/loss
- **Total Trades**: Number of trades executed
- **Performance Status**: Visual badge indicating profitability

### 3. Performance Calculation
- **Function**: `get_strategy_performance(strategy_name, days=30)`
- **Location**: `blueprints/python_strategy.py`
- **Data Source**: `SandboxTrades` table
- **Calculation Method**:
  - Queries all trades for the strategy in the specified period
  - Calculates buy_value and sell_value
  - PnL = sell_value - buy_value
  - PnL % = (PnL / buy_value) * 100

### 4. Enhanced Backtest Analysis
- **Script**: `run_comprehensive_backtests.py`
- **Features**:
  - Analyzes strategies for multiple periods (current day, previous day, week, month, 7 days, 14 days)
  - Identifies options vs intraday strategies
  - Shows separate breakdown for options and intraday strategies
  - Debug logging to identify options strategies

### 5. Options Strategies Analysis
- **Script**: `run_options_backtests.py`
- **Purpose**: Specifically analyzes options strategies
- **Features**:
  - Filters trades by strategy name containing "Option"
  - Filters trades by option symbols (CE/PE)
  - Provides detailed options strategy performance breakdown

## How It Works

### Performance Calculation Flow
1. User visits `/python` route
2. For each strategy in `STRATEGY_CONFIGS`:
   - Extract strategy name from config
   - Call `get_strategy_performance(strategy_name, days=30)`
   - Query `SandboxTrades` for trades matching strategy name
   - Calculate PnL metrics
   - Determine profitability label
3. Pass performance data to template
4. Template displays labels and metrics on strategy cards

### Strategy Name Matching
- Performance is calculated based on the `strategy` field in `SandboxTrades`
- Strategy name must match exactly between:
  - `STRATEGY_CONFIGS[ strategy_id ]['name']`
  - `SandboxTrades.strategy`
- Options strategies use names like "Option Straddle", "Option Strangle", etc.

## Files Modified

1. **`blueprints/python_strategy.py`**:
   - Added `get_strategy_performance()` function
   - Added `_calculate_performance()` helper function
   - Updated `index()` route to include performance data
   - Added `strategy_type` to strategy info

2. **`templates/python_strategy/index.html`**:
   - Added performance labels (PROFITABLE/LOSING/NEUTRAL badges)
   - Added strategy type badges (OPTIONS/INTRADAY)
   - Added performance metrics section showing PnL, PnL%, and total trades

3. **`run_comprehensive_backtests.py`**:
   - Added debug logging for options strategies
   - Enhanced summary to show options vs intraday breakdown
   - Added analysis for 7-day and 14-day periods

4. **`run_options_backtests.py`** (NEW):
   - Dedicated script for options strategies analysis
   - Filters and analyzes only options-related trades

## Usage

### Viewing Performance Labels
1. Navigate to `/python` route
2. Performance labels appear automatically on each strategy card
3. Labels update based on trades in the last 30 days

### Running Backtest Analysis
```bash
# Run comprehensive analysis (all strategies)
python run_comprehensive_backtests.py

# Run options-specific analysis
python run_options_backtests.py
```

### Performance Updates
- Performance labels update automatically when:
  - New trades are executed
  - User refreshes the `/python` page
  - Performance is calculated on each page load (last 30 days)

## Notes

1. **Strategy Name Consistency**: 
   - Ensure strategy names in `strategy_configs.json` match the `strategy` field used when placing orders
   - Options strategies should use names like "Option Straddle", "Option Strangle", etc.

2. **Options Strategies Identification**:
   - Strategies are identified as "options" if:
     - `strategy_type` field in config is "options"
     - Strategy name contains "Option" or "option"
   - Trades are identified as options if:
     - Strategy name contains "Option"
     - Symbol ends with "CE" or "PE"

3. **Performance Period**:
   - Default period is 30 days
   - Can be adjusted by modifying `days` parameter in `get_strategy_performance()`

4. **Flask Context**:
   - Performance calculation requires Flask app context
   - Handled automatically in the route handler
   - Scripts need to use `app.app_context()` when running standalone

## Next Steps

1. **Run strategies for multiple days** to accumulate trade data
2. **Monitor performance labels** to see which strategies are profitable
3. **Run backtest analysis** periodically to track performance trends
4. **Adjust strategies** based on performance data

## Troubleshooting

### No Performance Labels Showing
- Check if strategies have trades in the last 30 days
- Verify strategy names match between config and trades
- Check Flask app context is available

### Options Strategies Not Appearing
- Verify options strategies are placing orders with correct strategy name
- Check if trades are being created in SandboxTrades
- Run `run_options_backtests.py` to see debug output

### Performance Not Updating
- Ensure new trades are being executed
- Check that strategy names in orders match config names
- Verify SandboxTrades table has recent entries










