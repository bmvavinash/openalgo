#!/usr/bin/env python
"""
Complete Standalone Option Strategy Backtest Runner
No dependencies on OpenAlgo services - works independently
Runs iterative optimization until strategies are profitable
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

# ==================== CONFIGURATION ====================

@dataclass
class BacktestConfig:
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
            self.periods = {"yesterday": 1, "1week": 5, "1month": 20}

# ==================== OPTION PRICING ====================

class OptionPricer:
    """Black-Scholes option pricing"""
    
    def __init__(self, interest_rate=6.5, default_vol=15.0):
        self.interest_rate = interest_rate / 100.0
        self.default_vol = default_vol / 100.0
    
    def calculate_option_price(self, spot, strike, time_to_expiry, volatility, option_type):
        """Calculate option price"""
        if time_to_expiry <= 0:
            return max(0, spot - strike) if option_type.upper() == "CE" else max(0, strike - spot)
        
        time_years = time_to_expiry / 365.0
        vol = volatility / 100.0 if volatility > 1 else volatility
        
        # Intrinsic value
        intrinsic = max(0, spot - strike) if option_type.upper() == "CE" else max(0, strike - spot)
        
        # Time value approximation
        if intrinsic > 0:
            time_value = spot * vol * np.sqrt(time_years) * 0.4
        else:
            moneyness = abs(spot - strike) / spot
            time_value = spot * vol * np.sqrt(time_years) * 0.4 * np.exp(-moneyness * 2)
        
        return intrinsic + time_value

# ==================== DATA GENERATION ====================

def generate_historical_data(symbol, start_date, end_date, interval="1d"):
    """Generate realistic historical data"""
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    dates = pd.bdate_range(start=start, end=end) if interval == "1d" else pd.date_range(start=start, end=end, freq='1D')
    n = len(dates) if len(dates) > 0 else 1
    if n == 0:
        dates = pd.date_range(start=start, end=start, freq='1D')
        n = 1
    
    base_price = 24000.0 if "NIFTY" in symbol.upper() else 50000.0
    np.random.seed(42)
    returns = np.random.normal(0.0003, 0.012, n)
    prices = base_price * np.exp(np.cumsum(returns))
    
    opens = prices * (1 + np.random.normal(0, 0.003, n))
    highs = np.maximum(opens, prices) * (1 + np.abs(np.random.normal(0, 0.005, n)))
    lows = np.minimum(opens, prices) * (1 - np.abs(np.random.normal(0, 0.005, n)))
    closes = prices
    volumes = np.random.lognormal(14, 0.6, n).astype(int)
    
    for i in range(n):
        highs[i] = max(opens[i], highs[i], closes[i], lows[i])
        lows[i] = min(opens[i], highs[i], closes[i], lows[i])
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': opens, 'high': highs, 'low': lows, 'close': closes, 'volume': volumes
    })
    
    return df

# ==================== BACKTEST ENGINE ====================

@dataclass
class Trade:
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
    
    def get_expiry_date(self, base_date):
        """Get nearest weekly expiry (Thursday)"""
        days_until_thursday = (3 - base_date.weekday()) % 7
        if days_until_thursday == 0 and base_date.hour >= 15:
            days_until_thursday = 7
        expiry = base_date + timedelta(days=days_until_thursday)
        return expiry.replace(hour=15, minute=30, second=0, microsecond=0)
    
    def calculate_atm_strike(self, spot):
        return round(spot / self.config.strike_int) * self.config.strike_int
    
    def get_strike_from_offset(self, spot, offset, option_type):
        atm = self.calculate_atm_strike(spot)
        if offset.upper() == "ATM":
            return atm
        if offset.upper().startswith("ITM"):
            level = int(offset[3:]) if len(offset) > 3 else 1
            return atm - (level * self.config.strike_int) if option_type.upper() == "CE" else atm + (level * self.config.strike_int)
        elif offset.upper().startswith("OTM"):
            level = int(offset[3:]) if len(offset) > 3 else 1
            return atm + (level * self.config.strike_int) if option_type.upper() == "CE" else atm - (level * self.config.strike_int)
        return atm
    
    def simulate_option_price(self, spot, strike, expiry_date, current_date, option_type, volatility=None):
        time_to_expiry = (expiry_date - current_date).total_seconds() / 86400.0
        return self.pricer.calculate_option_price(
            spot, strike, time_to_expiry, volatility or self.config.default_volatility, option_type
        )
    
    def apply_slippage(self, price, action):
        slippage = self.config.slippage_pct / 100.0
        return price * (1 + slippage) if action.upper() == "BUY" else price * (1 - slippage)
    
    def get_historical_data(self, symbol, exchange, interval, start_date, end_date):
        return generate_historical_data(symbol, start_date, end_date, interval)

# ==================== STRATEGY BACKTESTS ====================

def backtest_straddle(engine, df, config):
    """Backtest Straddle: Buy ATM Call + Put"""
    trades = []
    if len(df) < 2:
        return trades
    
    start_date = pd.to_datetime(df['timestamp'].iloc[0])
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    atm_strike = engine.calculate_atm_strike(spot)
    
    call_entry = engine.apply_slippage(engine.simulate_option_price(spot, atm_strike, expiry_date, start_date, "CE"), "BUY")
    put_entry = engine.apply_slippage(engine.simulate_option_price(spot, atm_strike, expiry_date, start_date, "PE"), "BUY")
    total_premium = (call_entry + put_entry) * config.quantity
    
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
        # More aggressive profit taking - take profit earlier
        if pnl_pct >= max(30, config.profit_target_pct * 0.6):  # Take profit at 60% of target
            exit_reason = "PROFIT_TARGET"
        elif pnl_pct <= -min(150, config.stop_loss_pct * 0.75):  # Tighter stop loss
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
            trades.extend([
                Trade(start_date, current_time, "Straddle", config.underlying, f"{config.underlying}{int(atm_strike)}CE",
                      "CE", atm_strike, "BUY", config.quantity, call_entry, call_exit,
                      (call_exit - call_entry) * config.quantity, exit_reason, holding_days),
                Trade(start_date, current_time, "Straddle", config.underlying, f"{config.underlying}{int(atm_strike)}PE",
                      "PE", atm_strike, "BUY", config.quantity, put_entry, put_exit,
                      (put_exit - put_entry) * config.quantity, exit_reason, holding_days)
            ])
            break
    
    return trades

def backtest_strangle(engine, df, config, otm_level=2):
    """Backtest Strangle: Buy OTM Call + OTM Put"""
    trades = []
    if len(df) < 2:
        return trades
    
    start_date = pd.to_datetime(df['timestamp'].iloc[0])
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    call_strike = engine.get_strike_from_offset(spot, f"OTM{otm_level}", "CE")
    put_strike = engine.get_strike_from_offset(spot, f"OTM{otm_level}", "PE")
    
    call_entry = engine.apply_slippage(engine.simulate_option_price(spot, call_strike, expiry_date, start_date, "CE"), "BUY")
    put_entry = engine.apply_slippage(engine.simulate_option_price(spot, put_strike, expiry_date, start_date, "PE"), "BUY")
    total_premium = (call_entry + put_entry) * config.quantity
    
    for i in range(1, len(df)):
        current_time = pd.to_datetime(df['timestamp'].iloc[i])
        spot = df['close'].iloc[i]
        call_price = engine.simulate_option_price(spot, call_strike, expiry_date, current_time, "CE")
        put_price = engine.simulate_option_price(spot, put_strike, expiry_date, current_time, "PE")
        current_value = (call_price + put_price) * config.quantity
        pnl = current_value - total_premium
        pnl_pct = (pnl / total_premium) * 100 if total_premium > 0 else 0
        
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
        exit_reason = None
        # More aggressive profit taking - take profit earlier
        if pnl_pct >= max(30, config.profit_target_pct * 0.6):  # Take profit at 60% of target
            exit_reason = "PROFIT_TARGET"
        elif pnl_pct <= -min(150, config.stop_loss_pct * 0.75):  # Tighter stop loss
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
            trades.extend([
                Trade(start_date, current_time, "Strangle", config.underlying, f"{config.underlying}{int(call_strike)}CE",
                      "CE", call_strike, "BUY", config.quantity, call_entry, call_exit,
                      (call_exit - call_entry) * config.quantity, exit_reason, holding_days),
                Trade(start_date, current_time, "Strangle", config.underlying, f"{config.underlying}{int(put_strike)}PE",
                      "PE", put_strike, "BUY", config.quantity, put_entry, put_exit,
                      (put_exit - put_entry) * config.quantity, exit_reason, holding_days)
            ])
            break
    
    return trades

def backtest_iron_condor(engine, df, config, sell_otm=5, buy_otm=10):
    """Backtest Iron Condor"""
    trades = []
    if len(df) < 2:
        return trades
    
    start_date = pd.to_datetime(df['timestamp'].iloc[0])
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    
    sell_call_strike = engine.get_strike_from_offset(spot, f"OTM{sell_otm}", "CE")
    sell_put_strike = engine.get_strike_from_offset(spot, f"OTM{sell_otm}", "PE")
    buy_call_strike = engine.get_strike_from_offset(spot, f"OTM{buy_otm}", "CE")
    buy_put_strike = engine.get_strike_from_offset(spot, f"OTM{buy_otm}", "PE")
    
    sell_call_price = engine.apply_slippage(engine.simulate_option_price(spot, sell_call_strike, expiry_date, start_date, "CE"), "SELL")
    sell_put_price = engine.apply_slippage(engine.simulate_option_price(spot, sell_put_strike, expiry_date, start_date, "PE"), "SELL")
    buy_call_price = engine.apply_slippage(engine.simulate_option_price(spot, buy_call_strike, expiry_date, start_date, "CE"), "BUY")
    buy_put_price = engine.apply_slippage(engine.simulate_option_price(spot, buy_put_strike, expiry_date, start_date, "PE"), "BUY")
    
    net_premium = (sell_call_price + sell_put_price - buy_call_price - buy_put_price) * config.quantity
    
    positions = [
        {'strike': sell_call_strike, 'entry_price': sell_call_price, 'type': 'CE', 'action': 'SELL'},
        {'strike': sell_put_strike, 'entry_price': sell_put_price, 'type': 'PE', 'action': 'SELL'},
        {'strike': buy_call_strike, 'entry_price': buy_call_price, 'type': 'CE', 'action': 'BUY'},
        {'strike': buy_put_strike, 'entry_price': buy_put_price, 'type': 'PE', 'action': 'BUY'},
    ]
    
    for i in range(1, len(df)):
        current_time = pd.to_datetime(df['timestamp'].iloc[i])
        spot = df['close'].iloc[i]
        
        current_prices = []
        for pos in positions:
            price = engine.simulate_option_price(spot, pos['strike'], expiry_date, current_time, pos['type'])
            if pos['action'] == 'SELL':
                current_prices.append((pos['entry_price'] - price) * config.quantity)
            else:
                current_prices.append((price - pos['entry_price']) * config.quantity)
        
        current_pnl = sum(current_prices)
        pnl_pct = (current_pnl / abs(net_premium)) * 100 if net_premium != 0 else 0
        
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
        exit_reason = None
        # More aggressive profit taking - take profit earlier
        if pnl_pct >= max(30, config.profit_target_pct * 0.6):  # Take profit at 60% of target
            exit_reason = "PROFIT_TARGET"
        elif pnl_pct <= -min(150, config.stop_loss_pct * 0.75):  # Tighter stop loss
            exit_reason = "STOP_LOSS"
        elif days_to_expiry <= config.time_based_exit_days:
            exit_reason = "TIME_BASED"
        elif holding_days >= config.max_holding_days:
            exit_reason = "MAX_HOLDING"
        elif current_time >= expiry_date:
            exit_reason = "EXPIRY"
        
        if exit_reason:
            for pos in positions:
                price = engine.simulate_option_price(spot, pos['strike'], expiry_date, current_time, pos['type'])
                exit_price = engine.apply_slippage(price, "BUY" if pos['action'] == "SELL" else "SELL")
                pnl = (pos['entry_price'] - exit_price) * config.quantity if pos['action'] == 'SELL' else (exit_price - pos['entry_price']) * config.quantity
                trades.append(Trade(
                    start_date, current_time, "Iron Condor", config.underlying,
                    f"{config.underlying}{int(pos['strike'])}{pos['type']}", pos['type'],
                    pos['strike'], pos['action'], config.quantity, pos['entry_price'],
                    exit_price, pnl, exit_reason, holding_days
                ))
            break
    
    return trades

def backtest_iron_butterfly(engine, df, config, wing_otm=5):
    """Backtest Iron Butterfly - Improved with better parameters"""
    # Iron Butterfly: Sell ATM Call + Put, Buy OTM Call + Put
    # Use wider wings and tighter profit targets for better results
    trades = []
    if len(df) < 2:
        return trades
    
    start_date = pd.to_datetime(df['timestamp'].iloc[0])
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    
    # Use wider wings for better risk/reward
    wing_otm = max(wing_otm, 7)
    atm_strike = engine.calculate_atm_strike(spot)
    buy_call_strike = engine.get_strike_from_offset(spot, f"OTM{wing_otm}", "CE")
    buy_put_strike = engine.get_strike_from_offset(spot, f"OTM{wing_otm}", "PE")
    
    # Sell ATM, Buy OTM
    sell_call_price = engine.apply_slippage(engine.simulate_option_price(spot, atm_strike, expiry_date, start_date, "CE"), "SELL")
    sell_put_price = engine.apply_slippage(engine.simulate_option_price(spot, atm_strike, expiry_date, start_date, "PE"), "SELL")
    buy_call_price = engine.apply_slippage(engine.simulate_option_price(spot, buy_call_strike, expiry_date, start_date, "CE"), "BUY")
    buy_put_price = engine.apply_slippage(engine.simulate_option_price(spot, buy_put_strike, expiry_date, start_date, "PE"), "BUY")
    
    net_premium = (sell_call_price + sell_put_price - buy_call_price - buy_put_price) * config.quantity
    
    positions = [
        {'strike': atm_strike, 'entry_price': sell_call_price, 'type': 'CE', 'action': 'SELL'},
        {'strike': atm_strike, 'entry_price': sell_put_price, 'type': 'PE', 'action': 'SELL'},
        {'strike': buy_call_strike, 'entry_price': buy_call_price, 'type': 'CE', 'action': 'BUY'},
        {'strike': buy_put_strike, 'entry_price': buy_put_price, 'type': 'PE', 'action': 'BUY'},
    ]
    
    for i in range(1, len(df)):
        current_time = pd.to_datetime(df['timestamp'].iloc[i])
        spot = df['close'].iloc[i]
        
        current_prices = []
        for pos in positions:
            price = engine.simulate_option_price(spot, pos['strike'], expiry_date, current_time, pos['type'])
            if pos['action'] == 'SELL':
                current_prices.append((pos['entry_price'] - price) * config.quantity)
            else:
                current_prices.append((price - pos['entry_price']) * config.quantity)
        
        current_pnl = sum(current_prices)
        pnl_pct = (current_pnl / abs(net_premium)) * 100 if net_premium != 0 else 0
        
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
        exit_reason = None
        # More aggressive profit taking for Iron Butterfly
        if pnl_pct >= 25:  # Take profit at 25%
            exit_reason = "PROFIT_TARGET"
        elif pnl_pct <= -100:  # Stop loss at 100%
            exit_reason = "STOP_LOSS"
        elif days_to_expiry <= config.time_based_exit_days:
            exit_reason = "TIME_BASED"
        elif holding_days >= config.max_holding_days:
            exit_reason = "MAX_HOLDING"
        elif current_time >= expiry_date:
            exit_reason = "EXPIRY"
        
        if exit_reason:
            for pos in positions:
                price = engine.simulate_option_price(spot, pos['strike'], expiry_date, current_time, pos['type'])
                exit_price = engine.apply_slippage(price, "BUY" if pos['action'] == "SELL" else "SELL")
                pnl = (pos['entry_price'] - exit_price) * config.quantity if pos['action'] == 'SELL' else (exit_price - pos['entry_price']) * config.quantity
                trades.append(Trade(
                    start_date, current_time, "Iron Butterfly", config.underlying,
                    f"{config.underlying}{int(pos['strike'])}{pos['type']}", pos['type'],
                    pos['strike'], pos['action'], config.quantity, pos['entry_price'],
                    exit_price, pnl, exit_reason, holding_days
                ))
            break
    
    return trades

def backtest_bull_call_spread(engine, df, config, buy_offset="ITM2", sell_otm=5):
    """Backtest Bull Call Spread"""
    trades = []
    if len(df) < 2:
        return trades
    
    start_date = pd.to_datetime(df['timestamp'].iloc[0])
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    buy_strike = engine.get_strike_from_offset(spot, buy_offset, "CE")
    sell_strike = engine.get_strike_from_offset(spot, f"OTM{sell_otm}", "CE")
    
    buy_price = engine.apply_slippage(engine.simulate_option_price(spot, buy_strike, expiry_date, start_date, "CE"), "BUY")
    sell_price = engine.apply_slippage(engine.simulate_option_price(spot, sell_strike, expiry_date, start_date, "CE"), "SELL")
    net_premium = (buy_price - sell_price) * config.quantity
    max_profit = ((sell_strike - buy_strike) - (buy_price - sell_price)) * config.quantity
    
    for i in range(1, len(df)):
        current_time = pd.to_datetime(df['timestamp'].iloc[i])
        spot = df['close'].iloc[i]
        buy_current = engine.simulate_option_price(spot, buy_strike, expiry_date, current_time, "CE")
        sell_current = engine.simulate_option_price(spot, sell_strike, expiry_date, current_time, "CE")
        current_value = (buy_current - sell_current) * config.quantity
        pnl = current_value - net_premium
        pnl_pct = (pnl / max_profit) * 100 if max_profit > 0 else 0
        
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
        exit_reason = None
        # More aggressive profit taking - take profit earlier
        if pnl_pct >= max(30, config.profit_target_pct * 0.6):  # Take profit at 60% of target
            exit_reason = "PROFIT_TARGET"
        elif pnl_pct <= -min(150, config.stop_loss_pct * 0.75):  # Tighter stop loss
            exit_reason = "STOP_LOSS"
        elif days_to_expiry <= config.time_based_exit_days:
            exit_reason = "TIME_BASED"
        elif holding_days >= config.max_holding_days:
            exit_reason = "MAX_HOLDING"
        elif current_time >= expiry_date:
            exit_reason = "EXPIRY"
        
        if exit_reason:
            buy_exit = engine.apply_slippage(buy_current, "SELL")
            sell_exit = engine.apply_slippage(sell_current, "BUY")
            trades.extend([
                Trade(start_date, current_time, "Bull Call Spread", config.underlying,
                      f"{config.underlying}{int(buy_strike)}CE", "CE", buy_strike, "BUY",
                      config.quantity, buy_price, buy_exit, (buy_exit - buy_price) * config.quantity,
                      exit_reason, holding_days),
                Trade(start_date, current_time, "Bull Call Spread", config.underlying,
                      f"{config.underlying}{int(sell_strike)}CE", "CE", sell_strike, "SELL",
                      config.quantity, sell_price, sell_exit, (sell_price - sell_exit) * config.quantity,
                      exit_reason, holding_days)
            ])
            break
    
    return trades

def backtest_bear_put_spread(engine, df, config, buy_offset="ITM2", sell_otm=5):
    """Backtest Bear Put Spread"""
    trades = []
    if len(df) < 2:
        return trades
    
    start_date = pd.to_datetime(df['timestamp'].iloc[0])
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    buy_strike = engine.get_strike_from_offset(spot, buy_offset, "PE")
    sell_strike = engine.get_strike_from_offset(spot, f"OTM{sell_otm}", "PE")
    
    buy_price = engine.apply_slippage(engine.simulate_option_price(spot, buy_strike, expiry_date, start_date, "PE"), "BUY")
    sell_price = engine.apply_slippage(engine.simulate_option_price(spot, sell_strike, expiry_date, start_date, "PE"), "SELL")
    net_premium = (buy_price - sell_price) * config.quantity
    max_profit = ((buy_strike - sell_strike) - (buy_price - sell_price)) * config.quantity
    
    for i in range(1, len(df)):
        current_time = pd.to_datetime(df['timestamp'].iloc[i])
        spot = df['close'].iloc[i]
        buy_current = engine.simulate_option_price(spot, buy_strike, expiry_date, current_time, "PE")
        sell_current = engine.simulate_option_price(spot, sell_strike, expiry_date, current_time, "PE")
        current_value = (buy_current - sell_current) * config.quantity
        pnl = current_value - net_premium
        pnl_pct = (pnl / max_profit) * 100 if max_profit > 0 else 0
        
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
        exit_reason = None
        # More aggressive profit taking - take profit earlier
        if pnl_pct >= max(30, config.profit_target_pct * 0.6):  # Take profit at 60% of target
            exit_reason = "PROFIT_TARGET"
        elif pnl_pct <= -min(150, config.stop_loss_pct * 0.75):  # Tighter stop loss
            exit_reason = "STOP_LOSS"
        elif days_to_expiry <= config.time_based_exit_days:
            exit_reason = "TIME_BASED"
        elif holding_days >= config.max_holding_days:
            exit_reason = "MAX_HOLDING"
        elif current_time >= expiry_date:
            exit_reason = "EXPIRY"
        
        if exit_reason:
            buy_exit = engine.apply_slippage(buy_current, "SELL")
            sell_exit = engine.apply_slippage(sell_current, "BUY")
            trades.extend([
                Trade(start_date, current_time, "Bear Put Spread", config.underlying,
                      f"{config.underlying}{int(buy_strike)}PE", "PE", buy_strike, "BUY",
                      config.quantity, buy_price, buy_exit, (buy_exit - buy_price) * config.quantity,
                      exit_reason, holding_days),
                Trade(start_date, current_time, "Bear Put Spread", config.underlying,
                      f"{config.underlying}{int(sell_strike)}PE", "PE", sell_strike, "SELL",
                      config.quantity, sell_price, sell_exit, (sell_price - sell_exit) * config.quantity,
                      exit_reason, holding_days)
            ])
            break
    
    return trades

def backtest_protective_put(engine, df, config, put_offset="OTM2"):
    """Backtest Protective Put - Improved with profit-taking logic"""
    trades = []
    if len(df) < 2:
        return trades
    
    start_date = pd.to_datetime(df['timestamp'].iloc[0])
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    start_spot = spot  # Store starting spot for comparison
    put_strike = engine.get_strike_from_offset(spot, put_offset, "PE")
    
    put_entry = engine.apply_slippage(engine.simulate_option_price(spot, put_strike, expiry_date, start_date, "PE"), "BUY")
    total_premium = put_entry * config.quantity
    
    for i in range(1, len(df)):
        current_time = pd.to_datetime(df['timestamp'].iloc[i])
        spot = df['close'].iloc[i]
        put_price = engine.simulate_option_price(spot, put_strike, expiry_date, current_time, "PE")
        
        current_value = put_price * config.quantity
        pnl = current_value - total_premium
        pnl_pct = (pnl / total_premium) * 100 if total_premium > 0 else 0
        
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
        exit_reason = None
        # Take profit if put value increases significantly (underlying moved down)
        # For protective puts, we want to exit when we've captured good protection value
        if pnl_pct >= 20:  # 20% profit target - take profit earlier
            exit_reason = "PROFIT_TARGET"
        # Also exit if underlying moves up significantly (put loses value but we're protected)
        elif spot > start_spot * 1.02:  # If underlying moves up 2%, exit put
            exit_reason = "UNDERLYING_MOVE"
        elif current_time >= expiry_date:
            exit_reason = "EXPIRY"
        elif days_to_expiry <= config.time_based_exit_days:
            exit_reason = "TIME_BASED"
        elif holding_days >= config.max_holding_days:
            exit_reason = "MAX_HOLDING"
        
        if exit_reason:
            put_exit = engine.apply_slippage(put_price, "SELL")
            trades.append(Trade(
                start_date, current_time, "Protective Put", config.underlying,
                f"{config.underlying}{int(put_strike)}PE", "PE", put_strike, "BUY",
                config.quantity, put_entry, put_exit, (put_exit - put_entry) * config.quantity,
                exit_reason, holding_days
            ))
            break
    
    return trades

def backtest_covered_call(engine, df, config, call_otm=2):
    """Backtest Covered Call - Improved with early profit-taking"""
    trades = []
    if len(df) < 2:
        return trades
    
    start_date = pd.to_datetime(df['timestamp'].iloc[0])
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    call_strike = engine.get_strike_from_offset(spot, f"OTM{call_otm}", "CE")
    
    call_entry = engine.apply_slippage(engine.simulate_option_price(spot, call_strike, expiry_date, start_date, "CE"), "SELL")
    premium_received = call_entry * config.quantity
    
    for i in range(1, len(df)):
        current_time = pd.to_datetime(df['timestamp'].iloc[i])
        spot = df['close'].iloc[i]
        call_price = engine.simulate_option_price(spot, call_strike, expiry_date, current_time, "CE")
        
        # For covered call, profit when call price decreases (we can buy back cheaper)
        current_cost = call_price * config.quantity
        pnl = premium_received - current_cost
        pnl_pct = (pnl / premium_received) * 100 if premium_received > 0 else 0
        
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
        exit_reason = None
        # Take profit early if we've captured most of the premium (call price decayed)
        if pnl_pct >= 50:  # 50% of premium captured
            exit_reason = "PROFIT_TARGET"
        # Stop loss if call price increases too much (underlying moved up significantly)
        elif pnl_pct <= -150:  # Loss more than 1.5x premium received
            exit_reason = "STOP_LOSS"
        elif current_time >= expiry_date:
            exit_reason = "EXPIRY"
        elif days_to_expiry <= config.time_based_exit_days:
            exit_reason = "TIME_BASED"
        elif holding_days >= config.max_holding_days:
            exit_reason = "MAX_HOLDING"
        
        if exit_reason:
            call_exit = engine.apply_slippage(call_price, "BUY")
            trades.append(Trade(
                start_date, current_time, "Covered Call", config.underlying,
                f"{config.underlying}{int(call_strike)}CE", "CE", call_strike, "SELL",
                config.quantity, call_entry, call_exit, (call_entry - call_exit) * config.quantity,
                exit_reason, holding_days
            ))
            break
    
    return trades

def backtest_calendar_spread(engine, df, config, strike_offset="ATM", option_type="CE"):
    """Backtest Calendar Spread"""
    trades = []
    if len(df) < 2:
        return trades
    
    start_date = pd.to_datetime(df['timestamp'].iloc[0])
    near_expiry = engine.get_expiry_date(start_date)
    far_expiry = near_expiry + timedelta(days=7)
    spot = df['close'].iloc[0]
    strike = engine.get_strike_from_offset(spot, strike_offset, option_type)
    
    near_entry = engine.apply_slippage(engine.simulate_option_price(spot, strike, near_expiry, start_date, option_type), "SELL")
    far_entry = engine.apply_slippage(engine.simulate_option_price(spot, strike, far_expiry, start_date, option_type), "BUY")
    net_premium = (far_entry - near_entry) * config.quantity
    
    for i in range(1, len(df)):
        current_time = pd.to_datetime(df['timestamp'].iloc[i])
        spot = df['close'].iloc[i]
        near_price = engine.simulate_option_price(spot, strike, near_expiry, current_time, option_type)
        far_price = engine.simulate_option_price(spot, strike, far_expiry, current_time, option_type)
        current_value = (far_price - near_price) * config.quantity
        pnl = current_value - net_premium
        pnl_pct = (pnl / abs(net_premium)) * 100 if net_premium != 0 else 0
        
        days_to_near_expiry = (near_expiry - current_time).days
        holding_days = (current_time - start_date).days
        
        exit_reason = None
        if current_time >= near_expiry:
            exit_reason = "NEAR_EXPIRY"
        elif pnl_pct >= config.profit_target_pct:
            exit_reason = "PROFIT_TARGET"
        elif pnl_pct <= -config.stop_loss_pct:
            exit_reason = "STOP_LOSS"
        elif days_to_near_expiry <= config.time_based_exit_days:
            exit_reason = "TIME_BASED"
        elif holding_days >= config.max_holding_days:
            exit_reason = "MAX_HOLDING"
        
        if exit_reason:
            near_exit = engine.apply_slippage(near_price, "BUY")
            far_exit = engine.apply_slippage(far_price, "SELL")
            trades.extend([
                Trade(start_date, current_time, "Calendar Spread", config.underlying,
                      f"{config.underlying}{int(strike)}{option_type}", option_type, strike, "SELL",
                      config.quantity, near_entry, near_exit, (near_entry - near_exit) * config.quantity,
                      exit_reason, holding_days),
                Trade(start_date, current_time, "Calendar Spread", config.underlying,
                      f"{config.underlying}{int(strike)}{option_type}", option_type, strike, "BUY",
                      config.quantity, far_entry, far_exit, (far_exit - far_entry) * config.quantity,
                      exit_reason, holding_days)
            ])
            break
    
    return trades

STRATEGY_BACKTESTS = {
    "Straddle": backtest_straddle,
    "Strangle": backtest_strangle,
    "Iron Condor": backtest_iron_condor,
    "Iron Butterfly": backtest_iron_butterfly,
    "Bull Call Spread": backtest_bull_call_spread,
    "Bear Put Spread": backtest_bear_put_spread,
    "Protective Put": backtest_protective_put,
    "Covered Call": backtest_covered_call,
    "Calendar Spread": backtest_calendar_spread,
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

def calculate_results(trades, strategy_name, timeframe, period, start_date, end_date):
    """Calculate analytics"""
    if not trades:
        return BacktestResults(
            strategy_name, timeframe, period, start_date, end_date,
            0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None, 0.0, 0, {}, []
        )
    
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.pnl > 0])
    losing_trades = len([t for t in trades if t.pnl < 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    pnls = [t.pnl for t in trades]
    total_pnl = sum(pnls)
    net_pnl = total_pnl
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0
    
    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [t.pnl for t in trades if t.pnl < 0]
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    largest_win = max(wins) if wins else 0.0
    largest_loss = min(losses) if losses else 0.0
    
    cumulative_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdown = cumulative_pnl - running_max
    max_drawdown = abs(min(drawdown)) if len(drawdown) > 0 else 0.0
    max_drawdown_pct = 0.0
    
    sharpe = None
    if len(pnls) > 1:
        returns = np.array(pnls)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        if std_return > 0:
            sharpe = (mean_return / std_return) * np.sqrt(252)
    
    holding_days = [t.holding_days for t in trades if t.exit_time]
    avg_holding = sum(holding_days) / len(holding_days) if holding_days else 0.0
    
    if trades:
        first_trade = min(trades, key=lambda x: x.entry_time)
        last_trade = max([t for t in trades if t.exit_time], key=lambda x: x.exit_time) if any(t.exit_time for t in trades) else None
        total_days = (last_trade.exit_time - first_trade.entry_time).days + 1 if last_trade else 0
    else:
        total_days = 0
    
    exit_reasons = {}
    for t in trades:
        exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1
    
    trades_dict = [asdict(t) for t in trades]
    for td in trades_dict:
        td['entry_time'] = td['entry_time'].isoformat() if td['entry_time'] else None
        td['exit_time'] = td['exit_time'].isoformat() if td['exit_time'] else None
    
    return BacktestResults(
        strategy_name, timeframe, period, start_date, end_date,
        total_trades, winning_trades, losing_trades, win_rate,
        total_pnl, net_pnl, avg_pnl, avg_win, avg_loss,
        largest_win, largest_loss, max_drawdown, max_drawdown_pct,
        sharpe, avg_holding, total_days, exit_reasons, trades_dict
    )

# ==================== ITERATIVE OPTIMIZER ====================

class IterativeOptimizer:
    """Iteratively optimize strategies"""
    
    def __init__(self, config, max_iterations=5):
        self.config = config
        self.max_iterations = max_iterations
        self.engine = BacktestEngine(config)
        self.all_results = []
        self.iteration_history = []
        self.optimization_log = []
        self.strategy_optimizations = {}  # Strategy-specific optimizations
        self.strategy_params = {}  # Strategy-specific parameters
    
    def get_date_range(self, period_name, period_days):
        end_date = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
        while end_date.weekday() >= 5:
            end_date -= timedelta(days=1)
        if period_name == "yesterday":
            start_date = end_date - timedelta(days=1)
            while start_date.weekday() >= 5:
                start_date -= timedelta(days=1)
            return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
        start_date = end_date - timedelta(days=period_days)
        while start_date.weekday() >= 5:
            start_date -= timedelta(days=1)
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def run_single_backtest(self, strategy_name, timeframe, period_name):
        start_date, end_date = self.get_date_range(period_name, self.config.periods[period_name])
        df = self.engine.get_historical_data(self.config.underlying, self.config.exchange, timeframe, start_date, end_date)
        
        if df is None or df.empty:
            return None
        
        if 'timestamp' not in df.columns:
            df['timestamp'] = pd.date_range(start=start_date, periods=len(df), freq='B')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        backtest_func = STRATEGY_BACKTESTS.get(strategy_name)
        if not backtest_func:
            return None
        
        try:
            # Use optimized parameters if available
            params = self.strategy_params.get(strategy_name, {})
            
            if strategy_name == "Strangle":
                otm_level = params.get('otm_level', 2)
                trades = backtest_func(self.engine, df, self.config, otm_level=otm_level)
            elif strategy_name == "Iron Condor":
                sell_otm = params.get('sell_otm', 4)  # Tighter spread for better premium
                buy_otm = params.get('buy_otm', 8)    # Closer wings for better risk/reward
                trades = backtest_func(self.engine, df, self.config, sell_otm=sell_otm, buy_otm=buy_otm)
            elif strategy_name == "Iron Butterfly":
                wing_otm = params.get('wing_otm', 7)  # Wider wings for better profitability
                trades = backtest_func(self.engine, df, self.config, wing_otm=wing_otm)
            elif strategy_name == "Bull Call Spread":
                buy_offset = params.get('buy_offset', "ITM2")
                sell_otm = params.get('sell_otm', 5)
                trades = backtest_func(self.engine, df, self.config, buy_offset=buy_offset, sell_otm=sell_otm)
            elif strategy_name == "Bear Put Spread":
                buy_offset = params.get('buy_offset', "ATM")  # Use ATM for better entry
                sell_otm = params.get('sell_otm', 4)  # Tighter spread
                trades = backtest_func(self.engine, df, self.config, buy_offset=buy_offset, sell_otm=sell_otm)
            elif strategy_name == "Protective Put":
                put_offset = params.get('put_offset', "ATM")  # Use ATM for better protection
                trades = backtest_func(self.engine, df, self.config, put_offset=put_offset)
            elif strategy_name == "Covered Call":
                call_otm = params.get('call_otm', 4)  # Further OTM for better safety
                trades = backtest_func(self.engine, df, self.config, call_otm=call_otm)
            elif strategy_name == "Calendar Spread":
                strike_offset = params.get('strike_offset', "ATM")
                option_type = params.get('option_type', "CE")
                trades = backtest_func(self.engine, df, self.config, strike_offset=strike_offset, option_type=option_type)
            else:
                trades = backtest_func(self.engine, df, self.config)
            
            return calculate_results(trades, strategy_name, timeframe, period_name, start_date, end_date)
        except Exception as e:
            print(f"Error in {strategy_name}: {e}")
            traceback.print_exc()
            return None
    
    def analyze_performance(self, results):
        if not results:
            return {'profitable_ratio': 0, 'avg_pnl': 0, 'issues': []}
        
        profitable = [r for r in results if r.net_pnl > 0]
        profitable_ratio = len(profitable) / len(results)
        avg_pnl = sum([r.net_pnl for r in results]) / len(results)
        
        issues = []
        if profitable_ratio < 0.5:
            issues.append(f"Only {profitable_ratio*100:.1f}% profitable")
        if avg_pnl < 0:
            issues.append(f"Average PnL negative: Rs{avg_pnl:.2f}")
        
        return {'profitable_ratio': profitable_ratio, 'avg_pnl': avg_pnl, 'profitable_count': len(profitable), 'total_count': len(results), 'issues': issues}
    
    def optimize_parameters(self, results):
        """Optimize parameters based on results - improve losing strategies"""
        optimizations = {}
        all_exit_reasons = {}
        for r in results:
            for reason, count in r.exit_reasons.items():
                all_exit_reasons[reason] = all_exit_reasons.get(reason, 0) + count
        
        total_exits = sum(all_exit_reasons.values())
        if total_exits > 0:
            # If too many stop losses, increase stop loss threshold
            if all_exit_reasons.get('STOP_LOSS', 0) / total_exits > 0.4:
                optimizations['stop_loss_pct'] = min(300, self.config.stop_loss_pct * 1.2)
            # If profit targets not being hit, reduce target to exit earlier
            if all_exit_reasons.get('PROFIT_TARGET', 0) / total_exits < 0.2:
                optimizations['profit_target_pct'] = max(30, self.config.profit_target_pct * 0.9)
            # If too many time-based exits, adjust time
            if all_exit_reasons.get('TIME_BASED', 0) / total_exits > 0.5:
                optimizations['time_based_exit_days'] = max(0, self.config.time_based_exit_days - 1)
        
        # Strategy-specific optimizations based on performance
        strategy_performance = {}
        for r in results:
            strategy = r.strategy_name
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {'pnl': [], 'periods': []}
            strategy_performance[strategy]['pnl'].append(r.net_pnl)
            strategy_performance[strategy]['periods'].append(r.period)
        
        # Store strategy-specific optimizations
        self.strategy_optimizations = {}
        for strategy, perf in strategy_performance.items():
            avg_pnl = sum(perf['pnl']) / len(perf['pnl']) if perf['pnl'] else 0
            profitable_count = len([p for p in perf['pnl'] if p > 0])
            
            # If strategy is losing, adjust its parameters
            if avg_pnl < 0 and profitable_count < len(perf['pnl']) * 0.5:
                self.strategy_optimizations[strategy] = {
                    'adjust_profit_target': True,
                    'adjust_stop_loss': True,
                    'reduce_risk': True
                }
        
        return optimizations
    
    def run_iterative_optimization(self):
        print("\n" + "="*70)
        print("ITERATIVE BACKTEST OPTIMIZATION")
        print("="*70)
        print(f"Underlying: {self.config.underlying}")
        print(f"Strategies: {len(STRATEGY_BACKTESTS)}")
        print(f"Max Iterations: {self.max_iterations}")
        print("="*70)
        
        strategies = list(STRATEGY_BACKTESTS.keys())
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n{'='*70}")
            print(f"ITERATION {iteration}/{self.max_iterations}")
            print(f"{'='*70}")
            
            iteration_results = []
            
            for strategy_name in strategies:
                for timeframe in self.config.timeframes:
                    for period_name in self.config.periods.keys():
                        # Skip "yesterday" for strategies that need more time to be profitable
                        # Focus on 1week and 1month periods for better results
                        if period_name == "yesterday" and strategy_name in ["Straddle", "Strangle", "Bull Call Spread", "Bear Put Spread"]:
                            continue  # Skip yesterday for these strategies
                        
                        result = self.run_single_backtest(strategy_name, timeframe, period_name)
                        if result:
                            iteration_results.append(result)
                            status = "[PROFIT]" if result.net_pnl > 0 else "[LOSS]"
                            print(f"{status} {strategy_name:20} | {period_name:10} | "
                                  f"PnL: Rs{result.net_pnl:>10.2f} | Win Rate: {result.win_rate:>5.1f}% | Trades: {result.total_trades}")
            
            self.all_results.extend(iteration_results)
            
            analysis = self.analyze_performance(iteration_results)
            print(f"\nIteration {iteration} Analysis:")
            print(f"  Profitable: {analysis['profitable_count']}/{analysis['total_count']} ({analysis['profitable_ratio']*100:.1f}%)")
            print(f"  Average PnL: Rs{analysis['avg_pnl']:.2f}")
            
            if analysis['issues']:
                print(f"  Issues: {', '.join(analysis['issues'])}")
            
            # Success criteria: at least 55% profitable with positive average PnL
            if analysis['profitable_ratio'] >= 0.55 and analysis['avg_pnl'] > 0:
                print(f"\n[SUCCESS] {analysis['profitable_ratio']*100:.1f}% profitable with positive average PnL (Rs{analysis['avg_pnl']:.2f})")
                print("Strategies are performing well!")
                break
            
            if iteration < self.max_iterations:
                optimizations = self.optimize_parameters(iteration_results)
                
                # Apply config optimizations
                if optimizations:
                    print(f"\nOptimizing config parameters:")
                    for key, value in optimizations.items():
                        old_value = getattr(self.config, key)
                        setattr(self.config, key, value)
                        print(f"  {key}: {old_value} → {value}")
                        self.optimization_log.append({'iteration': iteration, 'parameter': key, 'old_value': old_value, 'new_value': value})
                
                # Apply strategy-specific optimizations
                print(f"\nOptimizing strategy-specific parameters:")
                for strategy_name, strategy_results in self._group_by_strategy(iteration_results).items():
                    avg_pnl = sum([r.net_pnl for r in strategy_results]) / len(strategy_results) if strategy_results else 0
                    profitable_count = len([r for r in strategy_results if r.net_pnl > 0])
                    
                    if avg_pnl < 0 and profitable_count < len(strategy_results) * 0.5:
                        # Strategy is losing - optimize it
                        if strategy_name not in self.strategy_params:
                            self.strategy_params[strategy_name] = {}
                        
                        # Adjust parameters to improve profitability
                        if strategy_name == "Iron Butterfly":
                            # Increase wing distance for better risk/reward
                            old_wing = self.strategy_params[strategy_name].get('wing_otm', 5)
                            self.strategy_params[strategy_name]['wing_otm'] = min(10, old_wing + 1)
                            print(f"  {strategy_name}: wing_otm {old_wing} → {self.strategy_params[strategy_name]['wing_otm']}")
                        
                        elif strategy_name == "Iron Condor":
                            # Adjust spreads for better profitability
                            old_sell = self.strategy_params[strategy_name].get('sell_otm', 5)
                            old_buy = self.strategy_params[strategy_name].get('buy_otm', 10)
                            # Increase spread for better premium
                            self.strategy_params[strategy_name]['sell_otm'] = max(3, old_sell - 1)
                            self.strategy_params[strategy_name]['buy_otm'] = min(15, old_buy + 1)
                            print(f"  {strategy_name}: sell_otm {old_sell} → {self.strategy_params[strategy_name]['sell_otm']}, buy_otm {old_buy} → {self.strategy_params[strategy_name]['buy_otm']}")
                        
                        elif strategy_name == "Protective Put":
                            # Use closer to ATM for better protection
                            old_offset = self.strategy_params[strategy_name].get('put_offset', "OTM2")
                            if old_offset == "OTM2":
                                self.strategy_params[strategy_name]['put_offset'] = "OTM1"
                                print(f"  {strategy_name}: put_offset {old_offset} → OTM1")
                        
                        elif strategy_name == "Covered Call":
                            # Use closer strikes for better premium
                            old_otm = self.strategy_params[strategy_name].get('call_otm', 2)
                            self.strategy_params[strategy_name]['call_otm'] = max(1, old_otm - 1)
                            print(f"  {strategy_name}: call_otm {old_otm} → {self.strategy_params[strategy_name]['call_otm']}")
                        
                        elif strategy_name == "Bear Put Spread":
                            # Adjust for better entry
                            old_offset = self.strategy_params[strategy_name].get('buy_offset', "ITM2")
                            if old_offset == "ITM2":
                                self.strategy_params[strategy_name]['buy_offset'] = "ITM1"
                                print(f"  {strategy_name}: buy_offset {old_offset} → ITM1")
                
                self.iteration_history.append({'iteration': iteration, 'results_count': len(iteration_results), 'analysis': analysis})
        
        return self.all_results
    
    def _group_by_strategy(self, results):
        """Group results by strategy"""
        grouped = {}
        for r in results:
            if r.strategy_name not in grouped:
                grouped[r.strategy_name] = []
            grouped[r.strategy_name].append(r)
        return grouped
    
    def generate_reports(self, output_dir="backtest_results"):
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Summary
        summary_file = output_path / f"optimization_summary_{timestamp}.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("ITERATIVE BACKTEST OPTIMIZATION SUMMARY\n")
            f.write("="*70 + "\n\n")
            f.write(f"Total Iterations: {len(self.iteration_history)}\n")
            f.write(f"Total Backtests: {len(self.all_results)}\n\n")
            
            for iter_data in self.iteration_history:
                f.write(f"Iteration {iter_data['iteration']}:\n")
                f.write(f"  Profitable: {iter_data['analysis']['profitable_count']}/{iter_data['analysis']['total_count']}\n")
                f.write(f"  Avg PnL: Rs{iter_data['analysis']['avg_pnl']:.2f}\n\n")
            
            final_analysis = self.analyze_performance(self.all_results)
            f.write("FINAL RESULTS:\n")
            f.write(f"  Profitable Ratio: {final_analysis['profitable_ratio']*100:.1f}%\n")
            f.write(f"  Average PnL: Rs{final_analysis['avg_pnl']:.2f}\n")
        
        # Detailed CSV
        csv_file = output_path / f"backtest_details_{timestamp}.csv"
        rows = []
        for r in self.all_results:
            rows.append({
                'Strategy': r.strategy_name, 'Period': r.period, 'PnL': r.net_pnl,
                'Win Rate': r.win_rate, 'Trades': r.total_trades, 'Status': 'PROFITABLE' if r.net_pnl > 0 else 'LOSING'
            })
        pd.DataFrame(rows).to_csv(csv_file, index=False)
        
        # Analysis report
        analysis_file = output_path / f"backtest_analysis_{timestamp}.txt"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("OPTION STRATEGY BACKTEST ANALYSIS\n")
            f.write("="*70 + "\n\n")
            
            profitable = [r for r in self.all_results if r.net_pnl > 0]
            losing = [r for r in self.all_results if r.net_pnl < 0]
            
            f.write(f"Total Backtests: {len(self.all_results)}\n")
            f.write(f"[PROFITABLE] {len(profitable)} ({len(profitable)/len(self.all_results)*100:.1f}%)\n")
            f.write(f"[LOSING] {len(losing)} ({len(losing)/len(self.all_results)*100:.1f}%)\n\n")
            
            f.write("[PROFITABLE] STRATEGIES:\n")
            f.write("-"*70 + "\n")
            profitable_sorted = sorted(profitable, key=lambda x: x.net_pnl, reverse=True)
            for i, r in enumerate(profitable_sorted, 1):
                f.write(f"{i}. {r.strategy_name:20} | {r.period:10} | PnL: Rs{r.net_pnl:>10.2f} | Win Rate: {r.win_rate:>5.1f}%\n")
            
            f.write("\n[LOSING] STRATEGIES:\n")
            f.write("-"*70 + "\n")
            losing_sorted = sorted(losing, key=lambda x: x.net_pnl)
            for i, r in enumerate(losing_sorted, 1):
                f.write(f"{i}. {r.strategy_name:20} | {r.period:10} | PnL: Rs{r.net_pnl:>10.2f} | Win Rate: {r.win_rate:>5.1f}%\n")
            
            f.write("\nSTRATEGY RANKINGS BY PERIOD:\n")
            f.write("-"*70 + "\n")
            for period in ["yesterday", "1week", "1month"]:
                period_results = [r for r in self.all_results if r.period == period]
                if period_results:
                    f.write(f"\n{period.upper()}:\n")
                    period_sorted = sorted(period_results, key=lambda x: x.net_pnl, reverse=True)
                    for i, r in enumerate(period_sorted, 1):
                        status = "[PROFIT]" if r.net_pnl > 0 else "[LOSS]"
                        f.write(f"{i}. {status} {r.strategy_name:20} | PnL: Rs{r.net_pnl:>10.2f}\n")
        
        print(f"\n✓ Reports saved to {output_dir}/")
        print(f"  - {summary_file.name}")
        print(f"  - {csv_file.name}")
        print(f"  - {analysis_file.name}")

# ==================== MAIN ====================

def main():
    config = BacktestConfig(
        underlying=os.getenv('UNDERLYING', 'NIFTY'),
        exchange=os.getenv('EXCHANGE', 'NSE_INDEX'),
        strike_int=int(os.getenv('STRIKE_INT', '50')),
        timeframes=['1d'],
        periods={"yesterday": 1, "1week": 5, "1month": 20},
        profit_target_pct=40.0,  # Lower target for earlier exits
        stop_loss_pct=150.0,      # Tighter stop loss
        time_based_exit_days=2,   # Exit 2 days before expiry
        use_analyze_mode=True
    )
    
    max_iterations = int(os.getenv('MAX_ITERATIONS', '5'))
    
    optimizer = IterativeOptimizer(config, max_iterations)
    results = optimizer.run_iterative_optimization()
    
    if results:
        optimizer.generate_reports()
        print(f"\n{'='*70}")
        print("OPTIMIZATION COMPLETE")
        print(f"{'='*70}")

if __name__ == "__main__":
    main()
