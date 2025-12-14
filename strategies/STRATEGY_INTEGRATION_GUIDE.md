# Strategy Integration Guide

## Overview

This guide explains how to integrate both **Intraday** and **Options** strategies into the OpenAlgo platform with unified management, labeling, and performance tracking.

## Strategy Types

### 1. Intraday Strategies
- **Type**: `intraday`
- **Examples**: EMA Crossover, Scalping, Momentum
- **Location**: `strategies/scripts/intraday_*.py`
- **Product**: Usually `MIS` (intraday)

### 2. Options Strategies
- **Type**: `options`
- **Examples**: Straddle, Strangle, Iron Condor, etc.
- **Location**: `strategies/scripts/option_*.py`
- **Product**: Usually `MIS` or `NRML`

## Automatic Type Detection

Strategies are automatically categorized based on filename:
- Files with `option` in the name → `options` type
- All other files → `intraday` type

## Performance Tracking

### Adding Performance Tracking to Your Strategy

Add this to your strategy script:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def update_performance(pnl, is_win):
    """Update performance metrics"""
    try:
        import requests
        strategy_id = os.getenv('STRATEGY_ID', 'your_strategy_id')
        requests.post(
            f"{os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000')}/python/performance/update",
            json={
                'strategy_id': strategy_id,
                'pnl': pnl,
                'is_win': is_win,
                'strategy_type': 'intraday'  # or 'options'
            },
            timeout=2
        )
    except:
        pass  # Silently fail if tracker unavailable

# Call after each trade
update_performance(trade_pnl, trade_pnl > 0)
```

## Profitability Labels

Strategies are automatically labeled based on performance:

- **High Profit**: Total PnL > Rs 10,000 AND Win Rate >= 70%
- **Medium Profit**: Total PnL > 0 AND Win Rate >= 50%
- **Low Profit**: Total PnL > 0 BUT Win Rate < 50%
- **Losses**: Total PnL < 0
- **Unknown**: No trades yet

## Frontend Features

### Filtering
- Filter by **Type**: All, Intraday, Options
- Filter by **Profitability**: All, High Profit, Medium Profit, Low Profit, Losses, Unknown
- **Sort by**: Name, Total PnL, Win Rate, Type

### Labels Display
- **Type Badge**: Blue for Intraday, Secondary color for Options
- **Profitability Badge**: Color-coded (Green=High, Blue=Medium, Yellow=Low, Red=Losses)
- **Performance Metrics**: Total PnL, Win Rate, Trade Count

## API Endpoints

### Performance Tracking
- `POST /python/performance/update` - Update strategy performance
- `GET /python/performance/<strategy_id>` - Get strategy performance
- `GET /python/performance/daily` - Get daily performance summary

### Analysis
- `GET /python/analysis/daily` - Get daily analysis
- `GET /python/analysis/recommended` - Get recommended strategies
- `GET /python/analysis/report` - Get end-of-day report

## Live Market Analysis

The system automatically:
1. Tracks all trades and PnL
2. Updates profitability labels in real-time
3. Generates daily performance reports
4. Recommends strategies for live trading

## Running Strategies on Monday

### Prerequisites
1. ✅ All strategies committed to `dbf-feature/options` branch
2. ✅ Performance tracking integrated
3. ✅ Labels and filtering enabled
4. ✅ Live market analyzer ready

### Steps
1. **Start OpenAlgo Server**:
   ```bash
   cd openalgo
   python app.py
   ```

2. **Access Frontend**: `http://localhost:5000/python`

3. **Upload Strategies**:
   - Upload intraday strategies (e.g., `intraday_ema_strategy.py`)
   - Upload options strategies (e.g., `option_straddle_strategy.py`)

4. **Configure**:
   - Set environment variables for each strategy
   - Configure strategy-specific parameters

5. **Start Strategies**:
   - Use the frontend to start strategies
   - Or schedule them for automatic start

6. **Monitor Performance**:
   - View real-time performance in the frontend
   - Check profitability labels
   - Filter by type and profitability

7. **End of Day Analysis**:
   - Access `/python/analysis/report` for daily summary
   - Get recommended strategies via `/python/analysis/recommended`

## Broker Integration

### For Live Trading
1. **Configure Broker**: Set up broker credentials in OpenAlgo
2. **API Keys**: Ensure broker API keys are configured
3. **Master Contracts**: Download master contracts
4. **Test in Paper Trading**: Start with analyze mode

### Live Data
- OpenAlgo automatically fetches live data from configured broker
- Historical data available via `client.history()`
- Real-time quotes via broker API

## Notes

- All strategies run in **paper trading mode** by default
- Switch to live trading by configuring broker and disabling analyze mode
- Performance tracking works in both paper and live modes
- Labels update automatically as trades execute
