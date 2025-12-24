# Option Trading Strategies

This directory contains comprehensive option trading strategies for OpenAlgo platform. All strategies are designed to run independently and can be executed in parallel.

## Available Strategies

### 1. Straddle Strategy (`option_straddle_strategy.py`)
- **Type**: Volatility / Neutral
- **Description**: Buy ATM Call + Put simultaneously
- **Profit**: Large price movements in either direction
- **Risk**: Limited to premium paid
- **Use Case**: High volatility expectations

### 2. Strangle Strategy (`option_strangle_strategy.py`)
- **Type**: Volatility / Neutral
- **Description**: Buy OTM Call + OTM Put simultaneously
- **Profit**: Large price movements in either direction
- **Risk**: Limited to premium paid (lower than straddle)
- **Use Case**: High volatility expectations with lower cost

### 3. Iron Condor Strategy (`option_iron_condor_strategy.py`)
- **Type**: Neutral / Income
- **Description**: Sell OTM Call + Sell OTM Put, Buy further OTM Call + Buy further OTM Put
- **Profit**: Limited (premium received minus premium paid)
- **Risk**: Limited (difference between strikes)
- **Use Case**: Range-bound markets, income generation

### 4. Iron Butterfly Strategy (`option_iron_butterfly_strategy.py`)
- **Type**: Neutral / Income
- **Description**: Sell ATM Call + Sell ATM Put, Buy OTM Call + Buy OTM Put
- **Profit**: Maximum at ATM (premium received minus premium paid)
- **Risk**: Limited (difference between strikes)
- **Use Case**: Range-bound markets with maximum profit at current price

### 5. Bull Call Spread (`option_bull_call_spread_strategy.py`)
- **Type**: Bullish / Directional
- **Description**: Buy ITM/ATM Call + Sell OTM Call
- **Profit**: Limited (difference between strikes minus net premium)
- **Risk**: Limited to net premium paid
- **Use Case**: Moderately bullish outlook

### 6. Bear Put Spread (`option_bear_put_spread_strategy.py`)
- **Type**: Bearish / Directional
- **Description**: Buy ITM/ATM Put + Sell OTM Put
- **Profit**: Limited (difference between strikes minus net premium)
- **Risk**: Limited to net premium paid
- **Use Case**: Moderately bearish outlook

### 7. Protective Put (`option_protective_put_strategy.py`)
- **Type**: Hedging / Protection
- **Description**: Long underlying + Buy Put option
- **Profit**: Unlimited upside, protected downside
- **Risk**: Limited to put premium
- **Use Case**: Protect existing long positions

### 8. Covered Call (`option_covered_call_strategy.py`)
- **Type**: Income / Neutral-Bullish
- **Description**: Long underlying + Sell Call option
- **Profit**: Limited (call premium + capped upside)
- **Risk**: Unlimited downside (minus premium received)
- **Use Case**: Generate income from existing long positions

### 9. Calendar Spread (`option_calendar_spread_strategy.py`)
- **Type**: Time Decay / Neutral
- **Description**: Sell near-term option + Buy far-term option (same strike)
- **Profit**: Time decay difference
- **Risk**: Limited
- **Use Case**: Time decay arbitrage, volatility plays

## Configuration

All strategies use environment variables for configuration:

### Common Parameters
- `OPENALGO_API_KEY` or `OPENALGO_APIKEY`: Your OpenAlgo API key (required)
- `OPENALGO_HOST`: OpenAlgo host URL (default: `http://127.0.0.1:5000`)
- `UNDERLYING`: Underlying symbol (default: `NIFTY`)
- `EXCHANGE`: Exchange code (default: `NSE_INDEX`)
- `EXPIRY_DATE`: Expiry date in DDMMMYY format (e.g., `28NOV24`)
- `STRIKE_INT`: Strike interval (default: `50` for NIFTY, `100` for BANKNIFTY)
- `QUANTITY`: Order quantity in lots (default: `75`)
- `PRODUCT`: Product type - `MIS` (intraday) or `NRML` (overnight) (default: `MIS`)
- `PRICETYPE`: Order type - `MARKET`, `LIMIT`, `SL`, `SL-M` (default: `MARKET`)

### Strategy-Specific Parameters

#### Straddle / Strangle
- `OTM_LEVEL`: OTM level for strangle (default: `2`)

#### Iron Condor
- `SELL_OTM`: OTM level for short strikes (default: `5`)
- `BUY_OTM`: OTM level for long strikes/wings (default: `10`)

#### Iron Butterfly
- `WING_OTM`: OTM level for long wings (default: `5`)

#### Bull/Bear Spreads
- `BUY_OFFSET`: Strike offset for long leg - `ATM`, `ITM1-ITM50` (default: `ITM2`)
- `SELL_OTM`: OTM level for short leg (default: `5`)

#### Protective Put
- `PUT_OFFSET`: Strike offset for put - `ATM`, `OTM1-OTM50` (default: `OTM2`)

#### Covered Call
- `CALL_OTM`: OTM level for call (default: `2`)

#### Calendar Spread
- `NEAR_EXPIRY`: Near-term expiry date (DDMMMYY format)
- `FAR_EXPIRY`: Far-term expiry date (DDMMMYY format)
- `STRIKE_OFFSET`: Strike offset - `ATM`, `ITM`, `OTM` (default: `ATM`)
- `OPTION_TYPE`: Option type - `CE` or `PE` (default: `CE`)

## Running Strategies

### Single Strategy

```bash
# Set environment variables
export OPENALGO_API_KEY="your_api_key"
export UNDERLYING="NIFTY"
export EXPIRY_DATE="28NOV24"
export QUANTITY=75

# Run strategy
python openalgo/strategies/scripts/option_straddle_strategy.py
```

### Multiple Strategies in Parallel

Strategies can run in parallel since each is an independent process. Use the strategy hosting system at `/python` in OpenAlgo web interface, or run multiple instances:

```bash
# Terminal 1
python openalgo/strategies/scripts/option_straddle_strategy.py

# Terminal 2
python openalgo/strategies/scripts/option_iron_condor_strategy.py

# Terminal 3
python openalgo/strategies/scripts/option_bull_call_spread_strategy.py
```

### Using OpenAlgo Strategy Hosting

1. Navigate to `http://localhost:5000/python`
2. Click "Add Strategy"
3. Upload the strategy script
4. Configure parameters as environment variables
5. Start the strategy
6. Repeat for additional strategies

All strategies will run in parallel, each in its own isolated process.

## Strategy Features

### Parallel Execution
- ✅ Each strategy runs in an independent process
- ✅ No shared state between strategies
- ✅ Can run multiple strategies simultaneously
- ✅ Process isolation prevents crashes from affecting other strategies

### Error Handling
- ✅ Comprehensive error handling and logging
- ✅ Graceful failure recovery
- ✅ Detailed error messages

### Position Tracking
- ✅ Tracks order IDs and symbols
- ✅ Monitors position status
- ✅ Supports position closing

### Exit Logic
- All strategies include placeholder exit logic that can be customized:
  - Profit targets
  - Stop losses
  - Time-based exits
  - Volatility-based exits
  - Market condition exits

## Example Usage

### Example 1: Straddle Strategy

```bash
export OPENALGO_API_KEY="abc123xyz"
export UNDERLYING="NIFTY"
export EXCHANGE="NSE_INDEX"
export EXPIRY_DATE="28NOV24"
export STRIKE_INT=50
export QUANTITY=75
export PRODUCT="MIS"
export PRICETYPE="MARKET"

python openalgo/strategies/scripts/option_straddle_strategy.py
```

### Example 2: Iron Condor Strategy

```bash
export OPENALGO_API_KEY="abc123xyz"
export UNDERLYING="BANKNIFTY"
export EXCHANGE="NSE_INDEX"
export EXPIRY_DATE="28NOV24"
export STRIKE_INT=100
export QUANTITY=45
export SELL_OTM=5
export BUY_OTM=10
export PRODUCT="MIS"

python openalgo/strategies/scripts/option_iron_condor_strategy.py
```

### Example 3: Bull Call Spread

```bash
export OPENALGO_API_KEY="abc123xyz"
export UNDERLYING="NIFTY"
export EXCHANGE="NSE_INDEX"
export EXPIRY_DATE="28NOV24"
export BUY_OFFSET="ITM2"
export SELL_OTM=5
export QUANTITY=75

python openalgo/strategies/scripts/option_bull_call_spread_strategy.py
```

## Notes

1. **Lot Sizes**: Ensure quantity is a multiple of the option's lot size:
   - NIFTY: 25
   - BANKNIFTY: 15
   - FINNIFTY: 25
   - MIDCPNIFTY: 50

2. **Expiry Dates**: Use DDMMMYY format (e.g., `28NOV24` for November 28, 2024)

3. **Analyze Mode**: All strategies work in both Live Mode and Analyze Mode (sandbox). The mode is automatically detected by OpenAlgo.

4. **Margin Requirements**: 
   - Live Mode: Broker's margin requirements apply
   - Analyze Mode: Virtual margin with Rs 1 Crore capital

5. **Order Execution**: 
   - BUY legs execute first, then SELL legs (for margin efficiency in multi-leg strategies)
   - Orders are placed in parallel where possible

6. **Strategy Monitoring**: Add custom exit logic based on:
   - Profit targets
   - Stop losses
   - Time decay
   - Volatility changes
   - Market conditions

## Support

For issues or questions:
- Check OpenAlgo logs for detailed error messages
- Verify API endpoint is accessible
- Ensure master contract data is up to date
- Review API documentation in `docs/` folder

