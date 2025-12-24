# Option Strategy Backtesting

This directory contains a comprehensive backtesting framework for all option trading strategies.

## Quick Start

### Run Backtests

```bash
# Simple backtest runner (yesterday, 1 week, 1 month)
python strategies/backtest/run_option_backtests_simple.py

# Full backtest runner (all timeframes and periods)
python strategies/backtest/run_option_backtests.py
```

### Configuration

Set environment variables:

```bash
export UNDERLYING="NIFTY"  # or BANKNIFTY
export EXCHANGE="NSE_INDEX"
export STRIKE_INT=50  # 50 for NIFTY, 100 for BANKNIFTY
export OPENALGO_API_KEY="your_api_key"  # Optional for paper trading
```

### Command Line Options

```bash
python strategies/backtest/run_option_backtests_simple.py \
    --underlying NIFTY \
    --exchange NSE_INDEX \
    --output-dir backtest_results
```

## Backtested Strategies

1. **Straddle** - Buy ATM Call + Put
2. **Strangle** - Buy OTM Call + OTM Put
3. **Iron Condor** - Sell OTM Call + Put, Buy further OTM Call + Put
4. **Iron Butterfly** - Sell ATM Call + Put, Buy OTM Call + Put
5. **Bull Call Spread** - Buy ITM/ATM Call, Sell OTM Call
6. **Bear Put Spread** - Buy ITM/ATM Put, Sell OTM Put
7. **Protective Put** - Long underlying + Buy Put
8. **Covered Call** - Long underlying + Sell Call
9. **Calendar Spread** - Sell near-term, Buy far-term

## Output Reports

The backtest generates several reports:

1. **JSON Report** - Complete results in JSON format
2. **Summary Report** - Text summary by strategy
3. **CSV Report** - Detailed results in CSV format
4. **Analysis Report** - Profitable vs losing strategies analysis

## Paper Trading Mode

All backtests run in **paper trading mode** by default (`use_analyze_mode=True`). No broker connection is required.

To switch to live trading mode later, set `use_analyze_mode=False` in the configuration.

## Analytics Metrics

Each backtest calculates:

- **Trade Statistics**: Total trades, winning/losing trades, win rate
- **PnL Metrics**: Total PnL, net PnL, average PnL per trade
- **Risk Metrics**: Max drawdown, Sharpe ratio, Sortino ratio
- **Time Metrics**: Average holding days, total trading days
- **Exit Reasons**: Breakdown of why trades were closed

## Periods Tested

- **Yesterday**: Last trading day
- **1 Week**: Last 5 trading days
- **1 Month**: Last 20 trading days

## Results Analysis

The analysis report categorizes strategies as:

- ✅ **Profitable**: Strategies with positive net PnL
- ❌ **Losing**: Strategies with negative net PnL

Results are ranked by:
- Average PnL per strategy
- Performance by period
- Performance by timeframe

