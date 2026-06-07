# Backtest Analysis Results Summary

**Analysis Date:** 2025-12-23 21:39:02 IST  
**Mode:** Paper Trading (Analyze Mode)

## Key Findings

### Options Strategies
- **Status:** ❌ **NO TRADES FOUND**
- **Issue:** Options strategies are not placing any orders/trades
- **Action Required:** Investigate why options strategies aren't executing orders

### Intraday Strategies Performance

#### ✅ PROFITABLE STRATEGIES (3)

1. **MACD Strategy**
   - Last 7 Days: +Rs 17,511,024.40 (+1555.51%)
   - Last 14 Days: +Rs 17,392,447.12 (+1397.75%)
   - Current Month: +Rs 17,247,870.22 (+1124.47%)
   - **Status:** TOP PERFORMER ⭐

2. **RSI Strategy**
   - Last 7 Days: +Rs 159,218.30 (+25.02%)
   - Last 14 Days: +Rs 244,318.96 (+35.13%)
   - Current Month: +Rs 218,154.76 (+28.20%)
   - **Status:** CONSISTENTLY PROFITABLE ✅

3. **AUTO_SQUARE_OFF**
   - Last 7 Days: +Rs 14,297.04 (+6.92%)
   - Last 14 Days: +Rs 73,501.79 (+35.60%)
   - Current Month: +Rs 140,193.29 (+54.22%)
   - **Status:** PROFITABLE ✅

#### ❌ LOSING STRATEGIES (4)

1. **EMA Crossover Strategy with Stop Loss**
   - Last 7 Days: -Rs 7,702,844.30 (-58.70%)
   - Last 14 Days: -Rs 7,702,844.30 (-58.70%)
   - Current Month: -Rs 7,539,437.45 (-57.45%)
   - **Status:** CONSISTENTLY LOSING ⚠️

2. **Multi-Indicator Strategy (MACD+EMA+RSI)**
   - Last 7 Days: -Rs 9,984,074.10 (-87.62%)
   - Last 14 Days: -Rs 9,958,066.38 (-87.39%)
   - Current Month: -Rs 10,068,906.48 (-85.80%)
   - **Status:** HEAVILY LOSING ⚠️⚠️

3. **EMA Crossover Strategy**
   - Current Month: -Rs 100.00 (-0.19%)
   - **Status:** MINOR LOSS

4. **TestOrder**
   - Last 14 Days: -Rs 52,067.46 (-100.00%)
   - Current Month: -Rs 52,067.46 (-100.00%)
   - **Status:** TEST ORDER (Ignore)

## Period-Wise Summary

| Period | Total Strategies | Profitable | Losing | Total Trades |
|--------|------------------|------------|--------|--------------|
| CURRENT DAY | 0 | 0 | 0 | 0 |
| PREVIOUS DAY | 0 | 0 | 0 | 0 |
| LAST 7 DAYS | 5 | 3 | 2 | 115 |
| LAST 14 DAYS | 6 | 3 | 3 | 123 |
| PREVIOUS WEEK | 5 | 3 | 2 | 115 |
| CURRENT MONTH | 7 | 3 | 4 | 159 |

## Recommendations

### Immediate Actions

1. **Options Strategies Investigation**
   - Check if options strategies are running
   - Verify expiry date configuration
   - Check option symbol resolution
   - Review strategy logs for errors

2. **Losing Strategies Review**
   - **Multi-Indicator Strategy**: Review and optimize (currently -87% loss)
   - **EMA Crossover Strategy with Stop Loss**: Review stop loss parameters (currently -58% loss)

3. **Top Performers**
   - **MACD Strategy**: Continue monitoring (excellent performance)
   - **RSI Strategy**: Continue monitoring (consistent profits)

### Performance Labels Update

The UI will now show:
- ✅ **PROFITABLE** badge for: MACD Strategy, RSI Strategy, AUTO_SQUARE_OFF
- ❌ **LOSING** badge for: EMA Crossover Strategy with Stop Loss, Multi-Indicator Strategy

## Next Steps

1. Fix options strategies to ensure they place orders
2. Optimize losing strategies based on analysis
3. Continue monitoring top performers
4. Run strategies for multiple days to accumulate more data
5. Re-run analysis periodically to track performance trends










