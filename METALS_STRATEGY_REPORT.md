# Metals Trading Strategy Analysis Report

**Generated:** 2026-01-30 21:28:16

**Analysis Period:** Last 60 days (Hourly data)

---

## Executive Summary

### Overall Performance

| Metric | Gold | Silver |
|--------|------|--------|
| Current Price | $5067.50 | $98.50 |
| Trend | BEARISH | BEARISH |
| Volatility | NORMAL | NORMAL |
| Total Trades | 4 | 4 |
| Win Rate | 50.0% | 50.0% |
| Total P&L | $142.50 | $0.14 |
| Return % | 0.14% | 0.00% |
| Profit Factor | 2.90 | 1.05 |
| Max Drawdown | 0.08% | 0.00% |
| Sharpe Ratio | 5.34 | 0.88 |

---

## Gold (GC=F) Strategy Analysis

### Current Market Conditions

- **Price:** $5067.50
- **Trend:** BEARISH
- **Volatility Regime:** NORMAL
- **24h Change:** -2.79%
- **ATR:** $98.54 (1.94%)
- **Recent High:** $5480.20
- **Recent Low:** $4962.70

### Technical Indicators

- **EMA Fast (9):** $5114.17
- **EMA Slow (21):** $5204.13
- **RSI (14):** 29.5
- **MACD:** -89.44
- **MACD Signal:** -75.67
- **Bollinger Position:** 0.21
- **Momentum (10-bar):** -2.78%
- **Volume Ratio:** 1.23x

### Current Signal

- **Signal:** NEUTRAL
- **Strength:** 5.0%
- **Components:** RSI_OVERSOLD(29.5) | MOM_DOWN(-2.8%)

### Strategy Parameters

```
Fast EMA: 9
Slow EMA: 21
RSI Period: 14
RSI Overbought: 70
RSI Oversold: 30
Stop Loss: 1.5%
Take Profit: 3.0%
Trailing Stop: 1.0%
ATR Multiplier: 2.0
```

### Backtest Results (60 days)

- **Total Trades:** 4
- **Winning Trades:** 2
- **Losing Trades:** 2
- **Win Rate:** 50.0%
- **Total P&L:** $142.50 (0.14%)
- **Average Win:** $108.80
- **Average Loss:** $37.55
- **Profit Factor:** 2.90
- **Max Drawdown:** 0.08%
- **Sharpe Ratio:** 5.34

#### Exit Reasons

- STOP_LOSS: 3 (75.0%)
- TAKE_PROFIT: 1 (25.0%)

#### Recent Trades (Last 10)

| Entry Time | Exit Time | Action | Entry | Exit | P&L | Exit Reason |
|------------|-----------|--------|-------|------|-----|-------------|
| 11/23 20:00 | 11/24 10:00 | SELL | $4041.10 | $4089.80 | $-48.70 (-1.2%) | STOP_LOSS |
| 12/03 13:00 | 12/05 01:00 | SELL | $4228.00 | $4254.40 | $-26.40 (-0.6%) | STOP_LOSS |
| 01/04 19:00 | 01/07 01:00 | BUY | $4404.50 | $4454.80 | $50.30 (1.1%) | STOP_LOSS |
| 01/18 23:00 | 01/20 20:00 | BUY | $4671.20 | $4838.50 | $167.30 (3.6%) | TAKE_PROFIT |

---

## Silver (SI=F) Strategy Analysis

### Current Market Conditions

- **Price:** $98.50
- **Trend:** BEARISH
- **Volatility Regime:** NORMAL
- **24h Change:** -10.15%
- **ATR:** $4.16 (4.22%)
- **Recent High:** $118.45
- **Recent Low:** $95.12

### Technical Indicators

- **EMA Fast (8):** $100.85
- **EMA Slow (18):** $104.97
- **RSI (14):** 25.4
- **MACD:** -4.35
- **MACD Signal:** -3.71
- **Bollinger Position:** 0.18
- **Momentum (10-bar):** -10.32%
- **Volume Ratio:** 0.99x

### Current Signal

- **Signal:** NEUTRAL
- **Strength:** 15.0%
- **Components:** MOM_DOWN(-10.3%)

### Strategy Parameters

```
Fast EMA: 8
Slow EMA: 18
RSI Period: 14
RSI Overbought: 75
RSI Oversold: 25
Stop Loss: 2.5%
Take Profit: 5.0%
Trailing Stop: 1.5%
ATR Multiplier: 2.5
```

### Backtest Results (60 days)

- **Total Trades:** 4
- **Winning Trades:** 2
- **Losing Trades:** 2
- **Win Rate:** 50.0%
- **Total P&L:** $0.14 (0.00%)
- **Average Win:** $1.45
- **Average Loss:** $1.38
- **Profit Factor:** 1.05
- **Max Drawdown:** 0.00%
- **Sharpe Ratio:** 0.88

#### Exit Reasons

- STOP_LOSS: 4 (100.0%)

#### Recent Trades (Last 10)

| Entry Time | Exit Time | Action | Entry | Exit | P&L | Exit Reason |
|------------|-----------|--------|-------|------|-----|-------------|
| 11/24 03:00 | 11/25 10:00 | BUY | $49.75 | $51.15 | $1.40 (2.8%) | STOP_LOSS |
| 12/09 00:00 | 12/09 04:00 | SELL | $58.19 | $59.06 | $-0.86 (-1.5%) | STOP_LOSS |
| 01/15 08:00 | 01/15 09:00 | SELL | $88.27 | $90.18 | $-1.91 (-2.2%) | STOP_LOSS |
| 01/27 16:00 | 01/28 03:00 | BUY | $112.35 | $113.86 | $1.51 (1.3%) | STOP_LOSS |

---

## Trading Recommendations

### Gold

- **Bias:** BEARISH - Look for selling opportunities on rallies
- **RSI Alert:** Oversold - Potential bounce expected
- **Strategy Status:** PERFORMING WELL - Continue with current parameters

### Silver

- **Bias:** BEARISH - Silver tends to underperform in bear markets
- **Strategy Status:** NEEDS ADJUSTMENT - Consider wider stops for volatile moves

---

## Risk Management Guidelines


### Position Sizing
- Never risk more than 2% of capital per trade
- For volatile conditions, reduce to 1% risk per trade
- Use lot sizes appropriate for your capital (1 lot Gold Mini = ~Rs 60,000 margin)

### Stop Loss Rules
1. **Initial Stop:** Use ATR-based or percentage-based, whichever is tighter
2. **Trailing Stop:** Move stop to breakeven after 1% profit
3. **Maximum Loss:** Exit if daily loss exceeds 5%

### Best Trading Hours (IST)
- **Gold:** 3:30 PM - 11:30 PM (overlaps with US markets)
- **Silver:** 3:30 PM - 11:30 PM (higher volatility during this window)

### Market Conditions to Avoid
- Major economic data releases (Fed meetings, NFP, etc.)
- First and last 30 minutes of trading session
- When ATR is more than 2x the average (extreme volatility)


---


*Report generated on 2026-01-30 21:28:16*