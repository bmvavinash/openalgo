# Git Branching Strategy for Scalping + Options

## Current Branch Structure

### Base Branches (Backups)
1. **`feature/scalping-toggle`** 
   - Contains: Scalping/intraday strategies only
   - Purpose: Backup for intraday strategies
   - Status: ✅ Stable base

2. **`dbf-feature/options`**
   - Contains: Scalping + Options strategies
   - Purpose: Combined branch for testing
   - Status: ✅ Has all features

## Recommended Approach

### Option 1: Use Existing Structure (Recommended)
- **`feature/scalping-toggle`** = Backup for scalping/intraday
- **`dbf-feature/options`** = Combined branch (scalping + options) for testing
- **Advantage**: Already set up, no merge needed
- **Use**: `dbf-feature/options` for all testing

### Option 2: Create Explicit Combined Branch
- **`feature/scalping-toggle`** = Backup for scalping/intraday
- **`dbf-feature/options`** = Backup for options only
- **`dbf-feature/scalping-options`** = Combined branch for testing
- **Advantage**: Clear separation, explicit combined branch
- **Use**: `dbf-feature/scalping-options` for testing

## Recommendation: Option 1

Since `dbf-feature/options` was created from `feature/scalping-toggle`, it already contains:
- ✅ All scalping/intraday strategies
- ✅ All option strategies
- ✅ All backtesting framework
- ✅ Can run both in parallel

**Use `dbf-feature/options` branch for testing** - it has everything!

## Branch Usage

```bash
# For testing (has everything)
git checkout dbf-feature/options

# For scalping-only backup
git checkout feature/scalping-toggle

# To create explicit combined branch (if needed)
git checkout feature/scalping-toggle
git checkout -b dbf-feature/scalping-options
git merge dbf-feature/options
```

## Strategy Files

### Intraday Strategies (from scalping branch)
- `ema_crossover_strategy.py`
- `ema_crossover_strategy_20251126224414.py`
- `macd_strategy_20251201095522.py`
- `rsi_strategy_20251203094216.py`
- `multi_indicator_strategy_20251201093321.py`

### Option Strategies (from options branch)
- `option_straddle_strategy.py`
- `option_strangle_strategy.py`
- `option_iron_condor_strategy.py`
- `option_iron_butterfly_strategy.py`
- `option_bull_call_spread_strategy.py`
- `option_bear_put_spread_strategy.py`
- `option_protective_put_strategy.py`
- `option_covered_call_strategy.py`
- `option_calendar_spread_strategy.py`

## Parallel Execution

Both strategy types can run in parallel:
- Intraday strategies: Use OpenAlgo strategy hosting at `/python`
- Option strategies: Use OpenAlgo strategy hosting at `/python`
- All strategies run in isolated processes

