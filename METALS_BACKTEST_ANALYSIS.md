# Metals Strategies – Historical Backtest Analysis

Generated from the last run of historical backtests (run via UI or `python run_metals_historical_backtests.py`).

## Summary

| Strategy | Metal | Type | Trades | Win % | P&L | P&L % | Max DD % | Sharpe | Profit Factor | Status |
|----------|-------|------|--------|-------|-----|-------|----------|--------|---------------|--------|
| Metals_GOLD_Default | GOLD | MCX | 15 | 26.7% | -441.32 | -0.44% | 0.91% | -2.71 | 0.67 | completed |
| Metals_SILVER_Default | SILVER | MCX | 27 | 0.0% | -150306.88 | -150.31% | 150.31% | -373.61 | 0.00 | completed |

**Completed:** 2 | **Errors:** 0

## How to run

- **From UI:** Metals → **Backtest Analysis** → set Start/End date and Timeframe → **Run Backtests for All Strategies**. Results appear in the table and on each strategy page.
- **Per strategy:** Open a strategy → **Run Backtest** (custom dates/timeframe).
- **From CLI:** `python run_metals_historical_backtests.py [user_id] [start_date] [end_date]`. Report is written to `METALS_BACKTEST_ANALYSIS.md` after each run.

## Notes

- Backtests use historical data from yfinance (works when market is closed).
- MCX strategies use futures symbols (e.g. GOLDM → GC=F, SILVERM → SI=F); ETF strategies use NSE symbols (e.g. GOLDBEES.NS).
- Win rate, P&L, Sharpe, and Profit Factor help compare strategy performance; consider running over different periods for robustness.
