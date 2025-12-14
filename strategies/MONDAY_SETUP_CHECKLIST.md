# Monday Setup Checklist

## Pre-Market Setup (Before 9:15 AM IST)

### 1. Server Setup ✅
- [x] All code committed to `dbf-feature/options` branch
- [x] Code pushed to remote repository
- [ ] Start OpenAlgo server: `python app.py` (port 5000)
- [ ] Verify server is running: `http://localhost:5000`

### 2. Broker Configuration
- [ ] Login to OpenAlgo web interface
- [ ] Configure broker credentials (if using live trading)
- [ ] Download master contracts (required for options)
- [ ] Verify broker connection

### 3. Strategy Upload
- [ ] Upload intraday strategies:
  - `intraday_ema_strategy.py`
  - Any other intraday strategies
- [ ] Upload options strategies:
  - `option_straddle_strategy.py`
  - `option_strangle_strategy.py`
  - `option_iron_condor_strategy.py`
  - `option_iron_butterfly_strategy.py`
  - `option_bull_call_spread_strategy.py`
  - `option_bear_put_spread_strategy.py`
  - `option_protective_put_strategy.py`
  - `option_covered_call_strategy.py`
  - `option_calendar_spread_strategy.py`

### 4. Strategy Configuration
- [ ] Set environment variables for each strategy:
  - `OPENALGO_API_KEY` or `OPENALGO_APIKEY`
  - Strategy-specific parameters (UNDERLYING, EXPIRY_DATE, etc.)
- [ ] Configure strategy type (auto-detected from filename)
- [ ] Set up scheduling if needed

### 5. Paper Trading Mode
- [ ] Verify analyze mode is enabled (default)
- [ ] Test strategies in paper trading first
- [ ] Monitor initial trades

## During Market Hours

### 6. Strategy Monitoring
- [ ] Access frontend: `http://localhost:5000/python`
- [ ] Monitor running strategies
- [ ] Check profitability labels (updates automatically)
- [ ] Filter strategies by type and profitability
- [ ] Review real-time performance metrics

### 7. Performance Tracking
- [ ] Strategies automatically track PnL
- [ ] Labels update in real-time:
  - High Profit (Green)
  - Medium Profit (Blue)
  - Low Profit (Yellow)
  - Losses (Red)
- [ ] View performance via `/python/performance/<strategy_id>`

## End of Day

### 8. Daily Analysis
- [ ] Access daily report: `http://localhost:5000/python/analysis/report`
- [ ] Review recommended strategies: `/python/analysis/recommended`
- [ ] Check daily summary: `/python/analysis/daily`
- [ ] Identify profitable vs losing strategies

### 9. Decision Making
- [ ] Review high profit strategies → Ready for live trading
- [ ] Review medium profit strategies → Monitor further
- [ ] Review low profit/losses → Optimize or disable
- [ ] Plan next day's strategy selection

## Features Available

### Frontend Features
- ✅ **Type Filtering**: Filter by Intraday or Options
- ✅ **Profitability Filtering**: Filter by High/Medium/Low Profit or Losses
- ✅ **Sorting**: Sort by Name, PnL, Win Rate, Type
- ✅ **Labels**: Visual badges for type and profitability
- ✅ **Performance Metrics**: Real-time PnL, Win Rate, Trade Count

### API Endpoints
- ✅ `/python/performance/<strategy_id>` - Get strategy performance
- ✅ `/python/performance/daily` - Daily performance summary
- ✅ `/python/performance/update` - Update performance (called by strategies)
- ✅ `/python/analysis/daily` - Daily analysis
- ✅ `/python/analysis/recommended` - Recommended strategies
- ✅ `/python/analysis/report` - End-of-day report

### Backend Services
- ✅ `strategy_performance_tracker.py` - Tracks all trades and PnL
- ✅ `live_market_analyzer.py` - Analyzes and categorizes strategies
- ✅ Automatic label updates based on performance
- ✅ Daily performance reports

## Broker Integration

### For Live Data
- OpenAlgo uses configured broker's API
- Historical data: `client.history()` (via broker API)
- Real-time quotes: Broker's quote API
- Order placement: Broker's order API

### Paper Trading (Current)
- Uses simulated data
- Virtual capital: Rs 1 Crore
- No real broker connection needed
- Perfect for testing

### Switching to Live Trading
1. Configure broker credentials in OpenAlgo
2. Disable analyze mode
3. Start with small positions
4. Monitor closely

## Troubleshooting

### If strategies don't appear:
- Check file uploads in `/python` interface
- Verify files are in `strategies/scripts/` directory
- Check file permissions

### If performance not tracking:
- Verify `STRATEGY_ID` environment variable is set
- Check network connectivity to OpenAlgo server
- Review strategy logs for errors

### If labels not updating:
- Performance tracker requires at least 1 trade
- Check `/python/performance/<strategy_id>` endpoint
- Verify performance data file exists

## Quick Start Commands

```bash
# Start server
cd openalgo
python app.py

# Access frontend
# Open browser: http://localhost:5000/python

# Check status
curl http://localhost:5000/python/status

# Get daily analysis
curl http://localhost:5000/python/analysis/daily
```

## Notes

- All strategies are in **paper trading mode** by default
- Performance tracking works automatically
- Labels update in real-time as trades execute
- Both intraday and options strategies are supported
- Frontend provides comprehensive filtering and sorting
