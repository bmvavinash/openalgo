# Strategy Performance Management System

## Overview

This system provides:
1. **Buy/Sell Restrictions** - Configurable restrictions at strategy level
2. **Performance Categorization** - Automatic categorization (Top/Average/Low)
3. **Category-based Execution** - Start strategies based on performance categories
4. **Daily Analysis** - Automatic analysis after market closure

## Components

### 1. Strategy Performance Config (`strategy_performance_config.py`)

Manages strategy configuration, restrictions, and categories.

**Key Features:**
- Set buy/sell restrictions per strategy
- Auto-detect restrictions from analysis results
- Update performance categories based on P&L
- Store performance history

**Usage:**
```python
from strategy_performance_config import StrategyPerformanceConfig

config = StrategyPerformanceConfig()

# Set restriction manually
config.set_buy_sell_restriction("Bear Put Spread", ["BUY"])

# Get allowed actions
allowed = config.get_allowed_actions("Bear Put Spread")  # Returns ["BUY"]

# Update category
config.update_performance_category("Bear Put Spread", pnl=150.0, period="current_day")

# Get strategies by category
top_strategies = config.get_strategies_by_category("top_performance")
```

### 2. Daily Strategy Analyzer (`daily_strategy_analyzer.py`)

Runs after market closure to analyze today's performance and update categories.

**Usage:**
```bash
# Run daily analysis (should run after 3:30 PM IST)
python daily_strategy_analyzer.py

# With custom parameters
python daily_strategy_analyzer.py --symbol BANKNIFTY --strike-int 100
```

**What it does:**
1. Analyzes all strategies for current day
2. Updates performance categories
3. Auto-detects buy/sell restrictions
4. Updates configuration file

### 3. Strategy Execution Filter (`strategy_execution_filter.py`)

Filters strategies based on categories and restrictions before execution.

**Usage:**
```python
from strategy_execution_filter import StrategyExecutionFilter

filter_obj = StrategyExecutionFilter()

# Get top performance strategies only
top_strategies = filter_obj.get_strategies_to_start(categories=["top_performance"])

# Get strategies that can execute BUY
buy_strategies = filter_obj.get_strategies_to_start(actions=["BUY"])

# Check if action is allowed
can_buy = filter_obj.can_execute_action("Bear Put Spread", "BUY")
```

## Configuration

### Performance Thresholds

Edit `config/strategy_performance.json`:

```json
{
  "performance_thresholds": {
    "top_performance": 100.0,    // P&L >= 100
    "average_performance": 0.0,   // 0 <= P&L < 100
    "low_performance": -100.0     // P&L < 0
  }
}
```

### Strategy Restrictions

**Manual Configuration:**
```python
config.set_buy_sell_restriction("Buy Strangle", ["SELL"])  # Restrict to SELL only
config.set_buy_sell_restriction("Bear Put Spread", ["BUY", "SELL"])  # Allow both
```

**Auto-Detection:**
The system automatically detects restrictions based on analysis results:
- If BUY is profitable and SELL is not → Restrict to BUY
- If SELL is profitable and BUY is not → Restrict to SELL
- If both are profitable or both losing → Allow both

## Integration with Strategy Execution

### Option 1: Filter Before Starting Strategies

```python
from strategy_execution_filter import StrategyExecutionFilter

filter_obj = StrategyExecutionFilter()

# Get strategies to start based on category
strategies_to_start = filter_obj.get_strategies_to_start(
    categories=["top_performance", "average_performance"]
)

# Start only filtered strategies
for strategy_name in strategies_to_start:
    start_strategy(strategy_name)
```

### Option 2: Check Before Each Order

```python
from strategy_execution_filter import StrategyExecutionFilter

filter_obj = StrategyExecutionFilter()

# Before placing order
if filter_obj.can_execute_action(strategy_name, "BUY"):
    place_order(strategy_name, action="BUY")
else:
    print(f"BUY not allowed for {strategy_name}")
```

## Daily Workflow

1. **Market Hours**: Strategies execute normally
2. **After Market Close (3:30 PM IST)**:
   - Run `daily_strategy_analyzer.py`
   - System analyzes today's performance
   - Updates categories and restrictions
3. **Next Day**: Strategies use updated categories and restrictions

## Automation Setup

### Cron Job (Linux/Mac)

```bash
# Run daily analysis at 3:35 PM IST (after market close)
35 15 * * 1-5 cd /path/to/openalgo && python daily_strategy_analyzer.py
```

### Windows Task Scheduler

1. Create task to run at 3:35 PM IST
2. Action: Run `python daily_strategy_analyzer.py`
3. Working directory: `F:\2nd Income\Stock Market\Code\openalgo`

### Python Scheduler (APScheduler)

```python
from apscheduler.schedulers.background import BackgroundScheduler
from daily_strategy_analyzer import analyze_today_performance

scheduler = BackgroundScheduler()
scheduler.add_job(
    analyze_today_performance,
    'cron',
    day_of_week='mon-fri',
    hour=15,
    minute=35,
    timezone='Asia/Kolkata'
)
scheduler.start()
```

## Example Scenarios

### Scenario 1: Start Only Top Performers

```python
from strategy_execution_filter import StrategyExecutionFilter

filter_obj = StrategyExecutionFilter()
top_strategies = filter_obj.get_strategies_to_start(categories=["top_performance"])

print(f"Starting {len(top_strategies)} top performance strategies:")
for strategy in top_strategies:
    print(f"  - {strategy}")
    start_strategy(strategy)
```

### Scenario 2: Start Top and Average, Skip Low

```python
strategies = filter_obj.get_strategies_to_start(
    categories=["top_performance", "average_performance"]
)
```

### Scenario 3: Only BUY Orders

```python
buy_strategies = filter_obj.get_strategies_to_start(actions=["BUY"])
```

### Scenario 4: Top Performance with BUY Only

```python
strategies = filter_obj.get_strategies_to_start(
    categories=["top_performance"],
    actions=["BUY"]
)
```

## Configuration File Structure

```json
{
  "version": "1.0",
  "last_updated": "2025-12-24T21:00:00",
  "performance_thresholds": {
    "top_performance": 100.0,
    "average_performance": 0.0,
    "low_performance": -100.0
  },
  "strategies": {
    "Bear Put Spread": {
      "allowed_actions": ["BUY", "SELL"],
      "restriction_type": "none",
      "category": "top_performance",
      "avg_pnl": 175.0,
      "performance_history": [
        {
          "period": "current_day",
          "pnl": 175.0,
          "win_rate": 100.0,
          "timestamp": "2025-12-24T21:00:00"
        }
      ],
      "last_updated": "2025-12-24T21:00:00"
    },
    "Buy Strangle": {
      "allowed_actions": ["SELL"],
      "restriction_type": "auto",
      "category": "low_performance",
      "avg_pnl": -786.0,
      "last_updated": "2025-12-24T21:00:00"
    }
  },
  "categories": {
    "top_performance": ["Bear Put Spread", "Sell Strangle"],
    "average_performance": ["Iron Condor"],
    "low_performance": ["Buy Strangle", "Iron Butterfly"]
  }
}
```

## Next Steps

1. **Integrate with Strategy Execution**: Modify strategy execution code to use the filter
2. **Add UI/Dashboard**: Create interface to view and modify categories/restrictions
3. **Add Notifications**: Alert when categories change significantly
4. **Historical Analysis**: Use historical data to improve categorization
5. **Backtesting Integration**: Use backtest results to set initial categories

## Files

- `strategy_performance_config.py` - Core configuration management
- `daily_strategy_analyzer.py` - Daily analysis runner
- `strategy_execution_filter.py` - Execution filtering
- `config/strategy_performance.json` - Configuration file







