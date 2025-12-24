# Option Strategy Backtesting Framework

Comprehensive backtesting system for testing option trading strategies on historical data.

## Features

- ✅ **Multiple Strategies**: Straddle, Strangle, Iron Condor, Bull Call Spread, Bear Put Spread
- ✅ **Multiple Timeframes**: 1m, 5m, 15m, 1h, 1d
- ✅ **Multiple Periods**: Yesterday, 1 week, 1 month, 3 months
- ✅ **Comprehensive Analytics**: PnL, Win Rate, Sharpe Ratio, Sortino Ratio, Max Drawdown
- ✅ **Configurable Parameters**: All entry/exit logic is configurable
- ✅ **Paper Trading Mode**: Uses analyze mode (no broker required)
- ✅ **Detailed Reports**: JSON, CSV, and text reports

## Installation

```bash
# Install required dependencies
pip install mibian pandas numpy

# Or if using uv
uv pip install mibian pandas numpy
```

## Configuration

All parameters are configurable via environment variables or code:

```python
from option_backtest_framework import BacktestConfig

config = BacktestConfig(
    underlying="NIFTY",           # Underlying symbol
    exchange="NSE_INDEX",         # Exchange
    strike_int=50,                # Strike interval (50 for NIFTY, 100 for BANKNIFTY)
    timeframes=["1m", "5m", "15m", "1h", "1d"],  # Timeframes to test
    periods={                     # Periods to test
        "yesterday": 1,
        "1week": 5,
        "1month": 20,
        "3months": 60
    },
    profit_target_pct=50.0,       # % of max profit to exit
    stop_loss_pct=200.0,          # % of premium to stop loss
    time_based_exit_days=1,       # Close X days before expiry
    max_holding_days=30,          # Maximum holding period
    default_volatility=15.0,      # Default IV %
    interest_rate=6.5,            # Risk-free rate %
    quantity=75,                  # Number of lots
    slippage_pct=0.1             # Slippage percentage
)
```

## Usage

### Basic Usage

```bash
# Run all backtests with default configuration
python run_option_backtests.py

# With custom parameters
python run_option_backtests.py \
    --underlying NIFTY \
    --exchange NSE_INDEX \
    --timeframes "1m,5m,15m,1h,1d" \
    --output-dir backtest_results
```

### Programmatic Usage

```python
from option_backtest_framework import BacktestConfig, OptionBacktestEngine
from run_option_backtests import BacktestRunner

# Create configuration
config = BacktestConfig(
    underlying="NIFTY",
    timeframes=["5m", "15m", "1h"],
    periods={"1week": 5, "1month": 20}
)

# Run backtests
runner = BacktestRunner(config, api_key="your_api_key")
results = runner.run_all_backtests()

# Generate reports
runner.generate_report(results, output_dir="backtest_results")
```

## Output Reports

The framework generates three types of reports:

### 1. JSON Report (`backtest_results_YYYYMMDD_HHMMSS.json`)
Complete detailed results in JSON format for programmatic analysis.

### 2. Summary Report (`backtest_summary_YYYYMMDD_HHMMSS.txt`)
Human-readable summary with:
- Overall statistics
- Strategy-wise breakdown
- Best and worst performers
- Average metrics

### 3. CSV Report (`backtest_details_YYYYMMDD_HHMMSS.csv`)
Detailed CSV with all metrics for each backtest run, suitable for Excel analysis.

### 4. Analysis Report (`backtest_analysis_YYYYMMDD_HHMMSS.txt`)
Detailed analysis including:
- Best strategies by timeframe
- Best strategies by period
- Strategy rankings
- Profitability analysis

## Analytics Metrics

Each backtest calculates:

### Trade Statistics
- Total trades
- Winning trades
- Losing trades
- Win rate (%)

### PnL Statistics
- Total PnL
- Net PnL
- Average PnL per trade
- Average win
- Average loss
- Largest win
- Largest loss

### Risk Metrics
- Maximum drawdown
- Maximum drawdown %
- Sharpe ratio (annualized)
- Sortino ratio (annualized)

### Time Metrics
- Average holding days
- Total trading days

### Exit Reasons
Breakdown of why trades were closed:
- PROFIT_TARGET
- STOP_LOSS
- TIME_BASED
- MAX_HOLDING
- EXPIRY
- END_OF_DATA

## Strategies Supported

1. **Straddle**: Buy ATM Call + Put
2. **Strangle**: Buy OTM Call + OTM Put
3. **Iron Condor**: Sell OTM Call/Put, Buy further OTM Call/Put
4. **Bull Call Spread**: Buy ITM/ATM Call, Sell OTM Call
5. **Bear Put Spread**: Buy ITM/ATM Put, Sell OTM Put

## Entry/Exit Logic

### Entry
- Strategies enter at the start of the backtest period
- Entry prices include slippage

### Exit Conditions
1. **Profit Target**: Exit when PnL reaches X% of maximum profit
2. **Stop Loss**: Exit when loss reaches X% of premium paid/received
3. **Time-Based**: Exit X days before expiry
4. **Max Holding**: Exit after maximum holding period
5. **Expiry**: Exit at expiry (intrinsic value)

## Configuration Examples

### Conservative Settings
```python
config = BacktestConfig(
    profit_target_pct=30.0,      # Lower profit target
    stop_loss_pct=150.0,         # Tighter stop loss
    time_based_exit_days=3,      # Exit 3 days before expiry
    max_holding_days=20          # Shorter holding period
)
```

### Aggressive Settings
```python
config = BacktestConfig(
    profit_target_pct=80.0,      # Higher profit target
    stop_loss_pct=300.0,         # Wider stop loss
    time_based_exit_days=0,      # Hold until expiry
    max_holding_days=45          # Longer holding period
)
```

## Notes

1. **Historical Data**: Requires access to historical data via OpenAlgo history service
2. **Option Pricing**: Uses Black-Scholes model via mibian library
3. **Volatility**: Uses default volatility if not available from market data
4. **Slippage**: Applied to all orders (configurable)
5. **Paper Trading**: All backtests run in analyze mode (no real orders)

## Troubleshooting

### No Data Available
- Check if historical data is available for the specified period
- Verify underlying symbol and exchange are correct
- Ensure OpenAlgo API key is valid

### Option Pricing Errors
- Install mibian: `pip install mibian`
- Check volatility settings
- Verify strike prices are valid

### Memory Issues
- Reduce number of timeframes or periods
- Process results in batches
- Use longer timeframes (1h, 1d) instead of shorter ones

## Future Enhancements

- [ ] Add more strategies (Iron Butterfly, Calendar Spread, etc.)
- [ ] Real-time volatility from market data
- [ ] Monte Carlo simulation
- [ ] Portfolio-level backtesting
- [ ] Interactive visualization
- [ ] Parameter optimization

