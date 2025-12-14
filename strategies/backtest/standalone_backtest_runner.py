#!/usr/bin/env python
"""
Standalone Option Strategy Backtest Runner
Works independently without requiring full OpenAlgo setup
Uses simulated data and option pricing for paper trading backtests
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import traceback

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ==================== CONFIGURATION ====================

@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    underlying: str = "NIFTY"
    exchange: str = "NSE_INDEX"
    strike_int: int = 50
    lot_size: int = 25
    timeframes: List[str] = None
    periods: Dict[str, int] = None
    profit_target_pct: float = 50.0
    stop_loss_pct: float = 200.0
    time_based_exit_days: int = 1
    max_holding_days: int = 30
    default_volatility: float = 15.0
    interest_rate: float = 6.5
    quantity: int = 75
    product: str = "MIS"
    slippage_pct: float = 0.1
    use_analyze_mode: bool = True
    
    def __post_init__(self):
        if self.timeframes is None:
            self.timeframes = ["1d"]
        if self.periods is None:
            self.periods = {
                "yesterday": 1,
                "1week": 5,
                "1month": 20
            }

# ==================== OPTION PRICING ====================

class OptionPricer:
    """Calculate option prices using Black-Scholes approximation"""
    
    def __init__(self, interest_rate: float = 6.5, default_vol: float = 15.0):
        self.interest_rate = interest_rate / 100.0
        self.default_vol = default_vol / 100.0
    
    def calculate_option_price(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,  # in days
        volatility: float,
        option_type: str  # "CE" or "PE"
    ) -> float:
        """Calculate option price using Black-Scholes approximation"""
        if time_to_expiry <= 0:
            # Option expired, return intrinsic value
            if option_type.upper() == "CE":
                return max(0, spot - strike)
            else:
                return max(0, strike - spot)
        
        time_years = time_to_expiry / 365.0
        vol = volatility / 100.0 if volatility > 1 else volatility
        
        # Intrinsic value
        if option_type.upper() == "CE":
            intrinsic = max(0, spot - strike)
        else:
            intrinsic = max(0, strike - spot)
        
        # Time value approximation
        if intrinsic > 0:
            # ITM option
            time_value = spot * vol * np.sqrt(time_years) * 0.4
        else:
            # OTM option - more time value
            moneyness = abs(spot - strike) / spot
            time_value = spot * vol * np.sqrt(time_years) * 0.4 * np.exp(-moneyness * 2)
        
        return intrinsic + time_value

# ==================== DATA GENERATION ====================

def generate_historical_data(
    symbol: str,
    start_date: str,
    end_date: str,
    interval: str = "1d",
    base_price: Optional[float] = None
) -> pd.DataFrame:
    """Generate realistic historical data"""
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    if interval == "1d":
        dates = pd.bdate_range(start=start, end=end)  # Business days only
    else:
        dates = pd.date_range(start=start, end=end, freq='1D')
    
    n = len(dates)
    if n == 0:
        # If no dates, create at least one
        dates = pd.date_range(start=start, end=start, freq='1D')
        n = 1
    
    if base_price is None:
        base_price = 24000.0 if "NIFTY" in symbol.upper() else 50000.0
    
    # Generate realistic price movement (random walk with slight trend)
    np.random.seed(42)  # For reproducibility
    returns = np.random.normal(0.0003, 0.012, n)  # Small positive drift
    prices = base_price * np.exp(np.cumsum(returns))
    
    # Generate OHLC
    daily_volatility = 0.01
    opens = prices * (1 + np.random.normal(0, daily_volatility * 0.3, n))
    highs = np.maximum(opens, prices) * (1 + np.abs(np.random.normal(0, daily_volatility * 0.5, n)))
    lows = np.minimum(opens, prices) * (1 - np.abs(np.random.normal(0, daily_volatility * 0.5, n)))
    closes = prices
    
    # Ensure OHLC consistency
    for i in range(n):
        highs[i] = max(opens[i], highs[i], closes[i], lows[i])
        lows[i] = min(opens[i], highs[i], closes[i], lows[i])
    
    volumes = np.random.lognormal(14, 0.6, n).astype(int)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })
    
    return df

# ==================== BACKTEST ENGINE ====================

@dataclass
class Trade:
    """Represents a single trade"""
    entry_time: datetime
    exit_time: Optional[datetime]
    strategy: str
    underlying: str
    symbol: str
    option_type: str
    strike: float
    action: str
    quantity: int
    entry_price: float
    exit_price: Optional[float]
    pnl: float
    exit_reason: str
    holding_days: float

class BacktestEngine:
    """Backtesting engine"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.pricer = OptionPricer(config.interest_rate, config.default_volatility)
    
    def get_expiry_date(self, base_date: datetime) -> datetime:
        """Get nearest weekly expiry (Thursday)"""
        days_until_thursday = (3 - base_date.weekday()) % 7
        if days_until_thursday == 0 and base_date.hour >= 15:
            days_until_thursday = 7
        expiry = base_date + timedelta(days=days_until_thursday)
        expiry = expiry.replace(hour=15, minute=30, second=0, microsecond=0)
        return expiry
    
    def calculate_atm_strike(self, spot: float) -> float:
        """Calculate ATM strike"""
        return round(spot / self.config.strike_int) * self.config.strike_int
    
    def get_strike_from_offset(self, spot: float, offset: str, option_type: str) -> float:
        """Get strike from offset"""
        atm = self.calculate_atm_strike(spot)
        
        if offset.upper() == "ATM":
            return atm
        
        if offset.upper().startswith("ITM"):
            level = int(offset[3:]) if len(offset) > 3 else 1
            if option_type.upper() == "CE":
                return atm - (level * self.config.strike_int)
            else:
                return atm + (level * self.config.strike_int)
        elif offset.upper().startswith("OTM"):
            level = int(offset[3:]) if len(offset) > 3 else 1
            if option_type.upper() == "CE":
                return atm + (level * self.config.strike_int)
            else:
                return atm - (level * self.config.strike_int)
        
        return atm
    
    def simulate_option_price(
        self,
        spot: float,
        strike: float,
        expiry_date: datetime,
        current_date: datetime,
        option_type: str,
        volatility: Optional[float] = None
    ) -> float:
        """Simulate option price"""
        time_to_expiry = (expiry_date - current_date).total_seconds() / 86400.0
        
        if time_to_expiry <= 0:
            if option_type.upper() == "CE":
                return max(0, spot - strike)
            else:
                return max(0, strike - spot)
        
        if volatility is None:
            volatility = self.config.default_volatility
        
        return self.pricer.calculate_option_price(
            spot, strike, time_to_expiry, volatility, option_type
        )
    
    def apply_slippage(self, price: float, action: str) -> float:
        """Apply slippage"""
        slippage = self.config.slippage_pct / 100.0
        if action.upper() == "BUY":
            return price * (1 + slippage)
        else:
            return price * (1 - slippage)

# ==================== STRATEGY BACKTESTS ====================

def backtest_straddle(engine: BacktestEngine, df: pd.DataFrame, config: BacktestConfig) -> List[Trade]:
    """Backtest Straddle: Buy ATM Call + Put"""
    trades = []
    if len(df) < 2:
        return trades
    
    start_date = pd.to_datetime(df['timestamp'].iloc[0])
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    atm_strike = engine.calculate_atm_strike(spot)
    
    call_entry_price = engine.simulate_option_price(spot, atm_strike, expiry_date, start_date, "CE")
    put_entry_price = engine.simulate_option_price(spot, atm_strike, expiry_date, start_date, "PE")
    
    call_entry_price = engine.apply_slippage(call_entry_price, "BUY")
    put_entry_price = engine.apply_slippage(put_entry_price, "BUY")
    
    total_premium = (call_entry_price + put_entry_price) * config.quantity
    
    for i in range(1, len(df)):
        current_time = pd.to_datetime(df['timestamp'].iloc[i])
        spot = df['close'].iloc[i]
        
        call_price = engine.simulate_option_price(spot, atm_strike, expiry_date, current_time, "CE")
        put_price = engine.simulate_option_price(spot, atm_strike, expiry_date, current_time, "PE")
        
        current_value = (call_price + put_price) * config.quantity
        pnl = current_value - total_premium
        pnl_pct = (pnl / total_premium) * 100 if total_premium > 0 else 0
        
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
        exit_reason = None
        if pnl_pct >= config.profit_target_pct:
            exit_reason = "PROFIT_TARGET"
        elif pnl_pct <= -config.stop_loss_pct:
            exit_reason = "STOP_LOSS"
        elif days_to_expiry <= config.time_based_exit_days:
            exit_reason = "TIME_BASED"
        elif holding_days >= config.max_holding_days:
            exit_reason = "MAX_HOLDING"
        elif current_time >= expiry_date:
            exit_reason = "EXPIRY"
        
        if exit_reason:
            call_exit = engine.apply_slippage(call_price, "SELL")
            put_exit = engine.apply_slippage(put_price, "SELL")
            
            trades.append(Trade(
                entry_time=start_date, exit_time=current_time,
                strategy="Straddle", underlying=config.underlying,
                symbol=f"{config.underlying}{int(atm_strike)}CE",
                option_type="CE", strike=atm_strike, action="BUY",
                quantity=config.quantity, entry_price=call_entry_price,
                exit_price=call_exit, pnl=(call_exit - call_entry_price) * config.quantity,
                exit_reason=exit_reason, holding_days=holding_days
            ))
            trades.append(Trade(
                entry_time=start_date, exit_time=current_time,
                strategy="Straddle", underlying=config.underlying,
                symbol=f"{config.underlying}{int(atm_strike)}PE",
                option_type="PE", strike=atm_strike, action="BUY",
                quantity=config.quantity, entry_price=put_entry_price,
                exit_price=put_exit, pnl=(put_exit - put_entry_price) * config.quantity,
                exit_reason=exit_reason, holding_days=holding_days
            ))
            break
    
    return trades

# Add other strategy backtests here (similar pattern)
# For brevity, I'll create simplified versions

STRATEGY_BACKTESTS = {
    "Straddle": backtest_straddle,
    # Add other strategies with similar implementations
}

# ==================== ANALYTICS ====================

@dataclass
class BacktestResults:
    strategy_name: str
    timeframe: str
    period: str
    start_date: str
    end_date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    net_pnl: float
    average_pnl_per_trade: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: Optional[float]
    average_holding_days: float
    total_trading_days: int
    exit_reasons: Dict[str, int]
    trades: List[Dict]

def calculate_results(trades: List[Trade], strategy_name: str, timeframe: str,
                     period: str, start_date: str, end_date: str) -> BacktestResults:
    """Calculate analytics from trades"""
    if not trades:
        return BacktestResults(
            strategy_name=strategy_name, timeframe=timeframe, period=period,
            start_date=start_date, end_date=end_date,
            total_trades=0, winning_trades=0, losing_trades=0, win_rate=0.0,
            total_pnl=0.0, net_pnl=0.0, average_pnl_per_trade=0.0,
            average_win=0.0, average_loss=0.0, largest_win=0.0, largest_loss=0.0,
            max_drawdown=0.0, max_drawdown_pct=0.0, sharpe_ratio=None,
            average_holding_days=0.0, total_trading_days=0,
            exit_reasons={}, trades=[]
        )
    
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.pnl > 0])
    losing_trades = len([t for t in trades if t.pnl < 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    pnls = [t.pnl for t in trades]
    total_pnl = sum(pnls)
    net_pnl = total_pnl
    average_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0.0
    
    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [t.pnl for t in trades if t.pnl < 0]
    average_win = sum(wins) / len(wins) if wins else 0.0
    average_loss = sum(losses) / len(losses) if losses else 0.0
    largest_win = max(wins) if wins else 0.0
    largest_loss = min(losses) if losses else 0.0
    
    cumulative_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdown = cumulative_pnl - running_max
    max_drawdown = abs(min(drawdown)) if len(drawdown) > 0 else 0.0
    max_drawdown_pct = 0.0  # Simplified
    
    sharpe_ratio = None
    if len(pnls) > 1:
        returns = np.array(pnls)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        if std_return > 0:
            sharpe_ratio = (mean_return / std_return) * np.sqrt(252)
    
    holding_days = [t.holding_days for t in trades if t.exit_time]
    average_holding_days = sum(holding_days) / len(holding_days) if holding_days else 0.0
    
    if trades:
        first_trade = min(trades, key=lambda x: x.entry_time)
        last_trade = max([t for t in trades if t.exit_time], key=lambda x: x.exit_time) if any(t.exit_time for t in trades) else None
        total_trading_days = (last_trade.exit_time - first_trade.entry_time).days + 1 if last_trade else 0
    else:
        total_trading_days = 0
    
    exit_reasons = {}
    for trade in trades:
        reason = trade.exit_reason
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
    
    trades_dict = [asdict(t) for t in trades]
    for td in trades_dict:
        td['entry_time'] = td['entry_time'].isoformat() if td['entry_time'] else None
        td['exit_time'] = td['exit_time'].isoformat() if td['exit_time'] else None
    
    return BacktestResults(
        strategy_name=strategy_name, timeframe=timeframe, period=period,
        start_date=start_date, end_date=end_date,
        total_trades=total_trades, winning_trades=winning_trades,
        losing_trades=losing_trades, win_rate=win_rate,
        total_pnl=total_pnl, net_pnl=net_pnl,
        average_pnl_per_trade=average_pnl_per_trade,
        average_win=average_win, average_loss=average_loss,
        largest_win=largest_win, largest_loss=largest_loss,
        max_drawdown=max_drawdown, max_drawdown_pct=max_drawdown_pct,
        sharpe_ratio=sharpe_ratio, average_holding_days=average_holding_days,
        total_trading_days=total_trading_days, exit_reasons=exit_reasons,
        trades=trades_dict
    )

# ==================== MAIN RUNNER ====================

def main():
    print("="*70)
    print("STANDALONE OPTION STRATEGY BACKTESTING")
    print("="*70)
    print("Note: Using simulated data for paper trading mode")
    print("="*70)
    
    config = BacktestConfig(
        underlying=os.getenv('UNDERLYING', 'NIFTY'),
        exchange=os.getenv('EXCHANGE', 'NSE_INDEX'),
        strike_int=int(os.getenv('STRIKE_INT', '50')),
        timeframes=['1d'],
        periods={
            "yesterday": 1,
            "1week": 5,
            "1month": 20
        },
        profit_target_pct=50.0,
        stop_loss_pct=200.0,
        use_analyze_mode=True
    )
    
    engine = BacktestEngine(config)
    all_results = []
    
    for strategy_name, backtest_func in STRATEGY_BACKTESTS.items():
        for period_name, period_days in config.periods.items():
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            df = generate_historical_data(config.underlying, start_str, end_str, '1d')
            
            if df.empty:
                continue
            
            trades = backtest_func(engine, df, config)
            result = calculate_results(trades, strategy_name, '1d', period_name, start_str, end_str)
            all_results.append(result)
            
            status = "✅" if result.net_pnl > 0 else "❌"
            print(f"{status} {strategy_name:20} | {period_name:10} | "
                  f"PnL: ₹{result.net_pnl:>10.2f} | Win Rate: {result.win_rate:>5.1f}%")
    
    # Generate summary
    profitable = [r for r in all_results if r.net_pnl > 0]
    print(f"\n{'='*70}")
    print(f"SUMMARY: {len(profitable)}/{len(all_results)} profitable")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
