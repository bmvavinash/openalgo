# Historical Strategy Analysis Guide

## Overview

The `historical_strategy_analysis.py` script analyzes how options trading strategies would have performed using historical market data from yfinance. This is particularly useful for:

- **Options strategies that don't have DB records** (since they may not have been triggered)
- **Backtesting strategies** before deploying them
- **Comparing multiple strategies** on the same historical data
- **Understanding strategy performance** in different market conditions

## Key Features

✅ **Uses yfinance data** (NOT DB trades) - ensures analysis even when no trades were executed  
✅ **Multiple strategies supported**: Bear Put Spread, Iron Condor, Straddle, Bull Call Spread  
✅ **Flexible date ranges**: Yesterday, last week, last month, or custom  
✅ **Command-line interface** for easy customization  
✅ **Performance ranking** to compare strategies  

## Usage

### Basic Usage (All Strategies, Yesterday's Data)

```bash
python historical_strategy_analysis.py
```

### Analyze Specific Strategies

```bash
python historical_strategy_analysis.py --strategies "Bear Put Spread" "Iron Condor"
```

### Analyze Last Week's Data

```bash
python historical_strategy_analysis.py --period last_week
```

### Analyze Different Symbol

```bash
python historical_strategy_analysis.py --symbol BANKNIFTY --strike-int 100
```

### Full Example

```bash
python historical_strategy_analysis.py \
  --period last_week \
  --symbol NIFTY \
  --exchange NSE_INDEX \
  --strategies "Bear Put Spread" "Iron Condor" "Buy Straddle" \
  --strike-int 50
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--period` | Analysis period: `auto`, `yesterday`, `last_week`, `last_month` | `auto` |
| `--symbol` | Underlying symbol (NIFTY, BANKNIFTY, etc.) | `NIFTY` |
| `--exchange` | Exchange code | `NSE_INDEX` |
| `--strategies` | Space-separated list of strategies to analyze | All strategies |
| `--strike-int` | Strike interval (50 for NIFTY, 100 for BANKNIFTY) | `50` |

## Supported Strategies

### 1. Bear Put Spread
- **Configuration**: Buy ITM2 Put, Sell OTM5 Put
- **Best for**: Bearish outlook with limited risk
- **Max Profit**: Spread width - net premium paid
- **Max Loss**: Net premium paid

### 2. Iron Condor
- **Configuration**: Sell OTM1 Call/Put, Buy OTM3 Call/Put
- **Best for**: Neutral outlook, range-bound markets
- **Max Profit**: Net premium received
- **Max Loss**: Spread width - net premium

### 3. Buy Straddle
- **Configuration**: Buy ATM Call + Buy ATM Put
- **Best for**: High volatility expected
- **Max Profit**: Unlimited (if large move)
- **Max Loss**: Premium paid

### 4. Bull Call Spread
- **Configuration**: Buy ITM2 Call, Sell OTM5 Call
- **Best for**: Bullish outlook with limited risk
- **Max Profit**: Spread width - net premium paid
- **Max Loss**: Net premium paid

## Output Explanation

The script provides:

1. **Strategy Analysis**: Detailed breakdown for each strategy including:
   - Entry/exit prices
   - Strike prices used
   - Estimated P&L
   - Scenario (Max Profit, Max Loss, Partial Profit/Loss)

2. **Summary Table**: Quick comparison of all strategies

3. **Performance Ranking**: Best and worst performers

## Important Notes

⚠️ **Simplified Pricing**: Option premiums are estimated (not actual market prices)  
⚠️ **Intrinsic Value Only**: Analysis based on intrinsic value at expiry  
⚠️ **Educational Purpose**: Results are for analysis/education, not actual trading advice  
⚠️ **No Historical Option Chains**: yfinance doesn't provide historical option prices, so we estimate  

## How It Works

1. **Fetches Historical Data**: Uses yfinance to get underlying price history
2. **Calculates Strikes**: Determines option strikes based on offsets (ITM2, OTM5, etc.)
3. **Estimates Premiums**: Uses simplified models to estimate option premiums
4. **Calculates P&L**: Computes strategy P&L based on intrinsic values
5. **Compares Strategies**: Ranks strategies by estimated performance

## Example Output

```
================================================================================
ANALYSIS SUMMARY
================================================================================

Strategy                  Symbol          Key Details                    Estimated P&L      Scenario       
---------------------------------------------------------------------------------------------------------
Bear Put Spread           NIFTY           26300-25950                    Rs       175.00    Partial Profit 
Iron Condor               NIFTY           Call: 26250-26350              Rs        51.65    Partial Loss   
BUY Straddle              NIFTY           Strike: 26200                  Rs      -465.65    Loss           
Bull Call Spread          NIFTY           26100-26450                    Rs      -133.35    Partial Profit 

================================================================================
PERFORMANCE RANKING
================================================================================

Best Performer: Bear Put Spread
  Estimated P&L: Rs       175.00
  Scenario: Partial Profit

Worst Performer: BUY Straddle
  Estimated P&L: Rs      -465.65
  Scenario: Loss
```

## Troubleshooting

### No Data Available
- Check if the date range includes market holidays
- Verify symbol mapping (NIFTY -> ^NSEI, BANKNIFTY -> ^NSEBANK)
- Try a different date range

### Strategy Not Found
- Check spelling (case-insensitive)
- Available strategies: Bear Put Spread, Iron Condor, Buy Straddle, Bull Call Spread

### Incorrect Strikes
- Verify strike interval matches the underlying (50 for NIFTY, 100 for BANKNIFTY)
- Check if offset values are valid (ITM1-ITM50, OTM1-OTM50, ATM)

## Future Enhancements

- [ ] Add more strategies (Strangle, Iron Butterfly, Calendar Spread)
- [ ] Support for historical option chain data (if available)
- [ ] More sophisticated option pricing models
- [ ] Multi-day/week analysis with cumulative P&L
- [ ] Export results to CSV/Excel
- [ ] Visualization charts

## Related Files

- `check_open_positions.py` - Check for open positions and margin issues
- `fix_margin_mismatch.py` - Fix orphaned margin problems
- `analyze_today_trades.py` - Analyze today's trades from DB







