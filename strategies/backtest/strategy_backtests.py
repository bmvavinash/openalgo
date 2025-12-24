#!/usr/bin/env python
"""
Strategy-specific backtest implementations
Each strategy has its own backtest function
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass

from option_backtest_framework import (
    OptionBacktestEngine, Trade, BacktestConfig
)

# ==================== STRADDLE STRATEGY ====================

def backtest_straddle(
    engine: OptionBacktestEngine,
    df: pd.DataFrame,
    config: BacktestConfig
) -> List[Trade]:
    """Backtest Straddle strategy: Buy ATM Call + Put"""
    trades = []
    
    if len(df) < 10:
        return trades
    
    # Get expiry date
    start_date = df['timestamp'].iloc[0]
    expiry_date = engine.get_expiry_date(start_date)
    
    # Entry: Buy ATM Call and Put at start
    spot = df['close'].iloc[0]
    atm_strike = engine.calculate_atm_strike(spot)
    
    # Calculate entry prices
    call_entry_price = engine.simulate_option_price(
        spot, atm_strike, expiry_date, start_date, "CE"
    )
    put_entry_price = engine.simulate_option_price(
        spot, atm_strike, expiry_date, start_date, "PE"
    )
    
    call_entry_price = engine.apply_slippage(call_entry_price, "BUY")
    put_entry_price = engine.apply_slippage(put_entry_price, "BUY")
    
    total_premium_paid = (call_entry_price + put_entry_price) * config.quantity
    
    # Track positions
    call_position = {
        'strike': atm_strike,
        'entry_price': call_entry_price,
        'entry_time': start_date,
        'quantity': config.quantity
    }
    put_position = {
        'strike': atm_strike,
        'entry_price': put_entry_price,
        'entry_time': start_date,
        'quantity': config.quantity
    }
    
    # Monitor for exit conditions
    for i in range(1, len(df)):
        current_time = df['timestamp'].iloc[i]
        spot = df['close'].iloc[i]
        
        # Calculate current option prices
        call_price = engine.simulate_option_price(
            spot, call_position['strike'], expiry_date, current_time, "CE"
        )
        put_price = engine.simulate_option_price(
            spot, put_position['strike'], expiry_date, current_time, "PE"
        )
        
        current_value = (call_price + put_price) * config.quantity
        current_pnl = current_value - total_premium_paid
        pnl_pct = (current_pnl / total_premium_paid) * 100 if total_premium_paid > 0 else 0
        
        # Check exit conditions
        exit_reason = None
        
        # Profit target
        if pnl_pct >= config.profit_target_pct:
            exit_reason = "PROFIT_TARGET"
        
        # Stop loss
        elif pnl_pct <= -config.stop_loss_pct:
            exit_reason = "STOP_LOSS"
        
        # Time-based exit
        days_to_expiry = (expiry_date - current_time).days
        if days_to_expiry <= config.time_based_exit_days:
            exit_reason = "TIME_BASED"
        
        # Max holding period
        holding_days = (current_time - start_date).days
        if holding_days >= config.max_holding_days:
            exit_reason = "MAX_HOLDING"
        
        # Expiry
        if current_time >= expiry_date:
            exit_reason = "EXPIRY"
        
        if exit_reason:
            # Exit both positions
            call_exit_price = engine.apply_slippage(call_price, "SELL")
            put_exit_price = engine.apply_slippage(put_price, "SELL")
            
            exit_value = (call_exit_price + put_exit_price) * config.quantity
            final_pnl = exit_value - total_premium_paid
            
            # Create trade records
            call_trade = Trade(
                entry_time=call_position['entry_time'],
                exit_time=current_time,
                strategy="Straddle",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(call_position['strike'])}CE",
                option_type="CE",
                strike=call_position['strike'],
                action="BUY",
                quantity=config.quantity,
                entry_price=call_position['entry_price'],
                exit_price=call_exit_price,
                pnl=(call_exit_price - call_position['entry_price']) * config.quantity,
                exit_reason=exit_reason,
                holding_days=holding_days
            )
            
            put_trade = Trade(
                entry_time=put_position['entry_time'],
                exit_time=current_time,
                strategy="Straddle",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(put_position['strike'])}PE",
                option_type="PE",
                strike=put_position['strike'],
                action="BUY",
                quantity=config.quantity,
                entry_price=put_position['entry_price'],
                exit_price=put_exit_price,
                pnl=(put_exit_price - put_position['entry_price']) * config.quantity,
                exit_reason=exit_reason,
                holding_days=holding_days
            )
            
            trades.extend([call_trade, put_trade])
            break
    
    # If still holding at end, close positions
    if not trades and len(df) > 0:
        final_time = df['timestamp'].iloc[-1]
        final_spot = df['close'].iloc[-1]
        
        call_price = engine.simulate_option_price(
            final_spot, call_position['strike'], expiry_date, final_time, "CE"
        )
        put_price = engine.simulate_option_price(
            final_spot, put_position['strike'], expiry_date, final_time, "PE"
        )
        
        call_exit_price = engine.apply_slippage(call_price, "SELL")
        put_exit_price = engine.apply_slippage(put_price, "SELL")
        
        holding_days = (final_time - start_date).days
        
        call_trade = Trade(
            entry_time=call_position['entry_time'],
            exit_time=final_time,
            strategy="Straddle",
            underlying=config.underlying,
            symbol=f"{config.underlying}{int(call_position['strike'])}CE",
            option_type="CE",
            strike=call_position['strike'],
            action="BUY",
            quantity=config.quantity,
            entry_price=call_position['entry_price'],
            exit_price=call_exit_price,
            pnl=(call_exit_price - call_position['entry_price']) * config.quantity,
            exit_reason="END_OF_DATA",
            holding_days=holding_days
        )
        
        put_trade = Trade(
            entry_time=put_position['entry_time'],
            exit_time=final_time,
            strategy="Straddle",
            underlying=config.underlying,
            symbol=f"{config.underlying}{int(put_position['strike'])}PE",
            option_type="PE",
            strike=put_position['strike'],
            action="BUY",
            quantity=config.quantity,
            entry_price=put_position['entry_price'],
            exit_price=put_exit_price,
            pnl=(put_exit_price - put_position['entry_price']) * config.quantity,
            exit_reason="END_OF_DATA",
            holding_days=holding_days
        )
        
        trades.extend([call_trade, put_trade])
    
    return trades

# ==================== STRANGLE STRATEGY ====================

def backtest_strangle(
    engine: OptionBacktestEngine,
    df: pd.DataFrame,
    config: BacktestConfig,
    otm_level: int = 2
) -> List[Trade]:
    """Backtest Strangle strategy: Buy OTM Call + OTM Put"""
    trades = []
    
    if len(df) < 10:
        return trades
    
    start_date = df['timestamp'].iloc[0]
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    
    # Calculate strikes
    call_strike = engine.get_strike_from_offset(spot, f"OTM{otm_level}", "CE")
    put_strike = engine.get_strike_from_offset(spot, f"OTM{otm_level}", "PE")
    
    # Entry prices
    call_entry_price = engine.simulate_option_price(
        spot, call_strike, expiry_date, start_date, "CE"
    )
    put_entry_price = engine.simulate_option_price(
        spot, put_strike, expiry_date, start_date, "PE"
    )
    
    call_entry_price = engine.apply_slippage(call_entry_price, "BUY")
    put_entry_price = engine.apply_slippage(put_entry_price, "BUY")
    
    total_premium_paid = (call_entry_price + put_entry_price) * config.quantity
    
    call_position = {
        'strike': call_strike,
        'entry_price': call_entry_price,
        'entry_time': start_date,
        'quantity': config.quantity
    }
    put_position = {
        'strike': put_strike,
        'entry_price': put_entry_price,
        'entry_time': start_date,
        'quantity': config.quantity
    }
    
    # Monitor for exit
    for i in range(1, len(df)):
        current_time = df['timestamp'].iloc[i]
        spot = df['close'].iloc[i]
        
        call_price = engine.simulate_option_price(
            spot, call_strike, expiry_date, current_time, "CE"
        )
        put_price = engine.simulate_option_price(
            spot, put_strike, expiry_date, current_time, "PE"
        )
        
        current_value = (call_price + put_price) * config.quantity
        current_pnl = current_value - total_premium_paid
        pnl_pct = (current_pnl / total_premium_paid) * 100 if total_premium_paid > 0 else 0
        
        exit_reason = None
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
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
            call_exit_price = engine.apply_slippage(call_price, "SELL")
            put_exit_price = engine.apply_slippage(put_price, "SELL")
            
            call_trade = Trade(
                entry_time=call_position['entry_time'],
                exit_time=current_time,
                strategy="Strangle",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(call_strike)}CE",
                option_type="CE",
                strike=call_strike,
                action="BUY",
                quantity=config.quantity,
                entry_price=call_position['entry_price'],
                exit_price=call_exit_price,
                pnl=(call_exit_price - call_position['entry_price']) * config.quantity,
                exit_reason=exit_reason,
                holding_days=holding_days
            )
            
            put_trade = Trade(
                entry_time=put_position['entry_time'],
                exit_time=current_time,
                strategy="Strangle",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(put_strike)}PE",
                option_type="PE",
                strike=put_strike,
                action="BUY",
                quantity=config.quantity,
                entry_price=put_position['entry_price'],
                exit_price=put_exit_price,
                pnl=(put_exit_price - put_position['entry_price']) * config.quantity,
                exit_reason=exit_reason,
                holding_days=holding_days
            )
            
            trades.extend([call_trade, put_trade])
            break
    
    # Close at end if still open
    if not trades and len(df) > 0:
        final_time = df['timestamp'].iloc[-1]
        final_spot = df['close'].iloc[-1]
        
        call_price = engine.simulate_option_price(
            final_spot, call_strike, expiry_date, final_time, "CE"
        )
        put_price = engine.simulate_option_price(
            final_spot, put_strike, expiry_date, final_time, "PE"
        )
        
        call_exit_price = engine.apply_slippage(call_price, "SELL")
        put_exit_price = engine.apply_slippage(put_price, "SELL")
        holding_days = (final_time - start_date).days
        
        trades.extend([
            Trade(
                entry_time=call_position['entry_time'],
                exit_time=final_time,
                strategy="Strangle",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(call_strike)}CE",
                option_type="CE",
                strike=call_strike,
                action="BUY",
                quantity=config.quantity,
                entry_price=call_position['entry_price'],
                exit_price=call_exit_price,
                pnl=(call_exit_price - call_position['entry_price']) * config.quantity,
                exit_reason="END_OF_DATA",
                holding_days=holding_days
            ),
            Trade(
                entry_time=put_position['entry_time'],
                exit_time=final_time,
                strategy="Strangle",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(put_strike)}PE",
                option_type="PE",
                strike=put_strike,
                action="BUY",
                quantity=config.quantity,
                entry_price=put_position['entry_price'],
                exit_price=put_exit_price,
                pnl=(put_exit_price - put_position['entry_price']) * config.quantity,
                exit_reason="END_OF_DATA",
                holding_days=holding_days
            )
        ])
    
    return trades

# ==================== IRON CONDOR STRATEGY ====================

def backtest_iron_condor(
    engine: OptionBacktestEngine,
    df: pd.DataFrame,
    config: BacktestConfig,
    sell_otm: int = 5,
    buy_otm: int = 10
) -> List[Trade]:
    """Backtest Iron Condor: Sell OTM Call/Put, Buy further OTM Call/Put"""
    trades = []
    
    if len(df) < 10:
        return trades
    
    start_date = df['timestamp'].iloc[0]
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    
    # Calculate strikes
    sell_call_strike = engine.get_strike_from_offset(spot, f"OTM{sell_otm}", "CE")
    sell_put_strike = engine.get_strike_from_offset(spot, f"OTM{sell_otm}", "PE")
    buy_call_strike = engine.get_strike_from_offset(spot, f"OTM{buy_otm}", "CE")
    buy_put_strike = engine.get_strike_from_offset(spot, f"OTM{buy_otm}", "PE")
    
    # Entry prices (sell short strikes, buy long strikes)
    sell_call_price = engine.simulate_option_price(spot, sell_call_strike, expiry_date, start_date, "CE")
    sell_put_price = engine.simulate_option_price(spot, sell_put_strike, expiry_date, start_date, "PE")
    buy_call_price = engine.simulate_option_price(spot, buy_call_strike, expiry_date, start_date, "CE")
    buy_put_price = engine.simulate_option_price(spot, buy_put_strike, expiry_date, start_date, "PE")
    
    sell_call_price = engine.apply_slippage(sell_call_price, "SELL")
    sell_put_price = engine.apply_slippage(sell_put_price, "SELL")
    buy_call_price = engine.apply_slippage(buy_call_price, "BUY")
    buy_put_price = engine.apply_slippage(buy_put_price, "BUY")
    
    # Net premium received (negative means paid)
    net_premium = (sell_call_price + sell_put_price - buy_call_price - buy_put_price) * config.quantity
    
    positions = [
        {'strike': sell_call_strike, 'entry_price': sell_call_price, 'type': 'CE', 'action': 'SELL'},
        {'strike': sell_put_strike, 'entry_price': sell_put_price, 'type': 'PE', 'action': 'SELL'},
        {'strike': buy_call_strike, 'entry_price': buy_call_price, 'type': 'CE', 'action': 'BUY'},
        {'strike': buy_put_strike, 'entry_price': buy_put_price, 'type': 'PE', 'action': 'BUY'},
    ]
    
    # Monitor for exit
    for i in range(1, len(df)):
        current_time = df['timestamp'].iloc[i]
        spot = df['close'].iloc[i]
        
        current_prices = []
        for pos in positions:
            price = engine.simulate_option_price(spot, pos['strike'], expiry_date, current_time, pos['type'])
            if pos['action'] == 'SELL':
                # For short positions, profit when price decreases
                current_prices.append((pos['entry_price'] - price) * config.quantity)
            else:
                # For long positions, profit when price increases
                current_prices.append((price - pos['entry_price']) * config.quantity)
        
        current_pnl = sum(current_prices)
        pnl_pct = (current_pnl / abs(net_premium)) * 100 if net_premium != 0 else 0
        
        exit_reason = None
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
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
            # Close all positions
            for pos in positions:
                price = engine.simulate_option_price(spot, pos['strike'], expiry_date, current_time, pos['type'])
                exit_price = engine.apply_slippage(price, "BUY" if pos['action'] == "SELL" else "SELL")
                
                if pos['action'] == 'SELL':
                    pnl = (pos['entry_price'] - exit_price) * config.quantity
                else:
                    pnl = (exit_price - pos['entry_price']) * config.quantity
                
                trade = Trade(
                    entry_time=start_date,
                    exit_time=current_time,
                    strategy="Iron Condor",
                    underlying=config.underlying,
                    symbol=f"{config.underlying}{int(pos['strike'])}{pos['type']}",
                    option_type=pos['type'],
                    strike=pos['strike'],
                    action=pos['action'],
                    quantity=config.quantity,
                    entry_price=pos['entry_price'],
                    exit_price=exit_price,
                    pnl=pnl,
                    exit_reason=exit_reason,
                    holding_days=holding_days
                )
                trades.append(trade)
            break
    
    # Close at end if still open
    if not trades and len(df) > 0:
        final_time = df['timestamp'].iloc[-1]
        final_spot = df['close'].iloc[-1]
        holding_days = (final_time - start_date).days
        
        for pos in positions:
            price = engine.simulate_option_price(final_spot, pos['strike'], expiry_date, final_time, pos['type'])
            exit_price = engine.apply_slippage(price, "BUY" if pos['action'] == "SELL" else "SELL")
            
            if pos['action'] == 'SELL':
                pnl = (pos['entry_price'] - exit_price) * config.quantity
            else:
                pnl = (exit_price - pos['entry_price']) * config.quantity
            
            trade = Trade(
                entry_time=start_date,
                exit_time=final_time,
                strategy="Iron Condor",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(pos['strike'])}{pos['type']}",
                option_type=pos['type'],
                strike=pos['strike'],
                action=pos['action'],
                quantity=config.quantity,
                entry_price=pos['entry_price'],
                exit_price=exit_price,
                pnl=pnl,
                exit_reason="END_OF_DATA",
                holding_days=holding_days
            )
            trades.append(trade)
    
    return trades

# ==================== BULL CALL SPREAD ====================

def backtest_bull_call_spread(
    engine: OptionBacktestEngine,
    df: pd.DataFrame,
    config: BacktestConfig,
    buy_offset: str = "ITM2",
    sell_otm: int = 5
) -> List[Trade]:
    """Backtest Bull Call Spread: Buy ITM/ATM Call, Sell OTM Call"""
    trades = []
    
    if len(df) < 10:
        return trades
    
    start_date = df['timestamp'].iloc[0]
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    
    buy_strike = engine.get_strike_from_offset(spot, buy_offset, "CE")
    sell_strike = engine.get_strike_from_offset(spot, f"OTM{sell_otm}", "CE")
    
    buy_price = engine.simulate_option_price(spot, buy_strike, expiry_date, start_date, "CE")
    sell_price = engine.simulate_option_price(spot, sell_strike, expiry_date, start_date, "CE")
    
    buy_price = engine.apply_slippage(buy_price, "BUY")
    sell_price = engine.apply_slippage(sell_price, "SELL")
    
    net_premium_paid = (buy_price - sell_price) * config.quantity
    max_profit = ((sell_strike - buy_strike) - (buy_price - sell_price)) * config.quantity
    
    buy_position = {'strike': buy_strike, 'entry_price': buy_price, 'entry_time': start_date}
    sell_position = {'strike': sell_strike, 'entry_price': sell_price, 'entry_time': start_date}
    
    # Monitor for exit
    for i in range(1, len(df)):
        current_time = df['timestamp'].iloc[i]
        spot = df['close'].iloc[i]
        
        buy_current = engine.simulate_option_price(spot, buy_strike, expiry_date, current_time, "CE")
        sell_current = engine.simulate_option_price(spot, sell_strike, expiry_date, current_time, "CE")
        
        current_value = (buy_current - sell_current) * config.quantity
        current_pnl = current_value - net_premium_paid
        pnl_pct = (current_pnl / max_profit) * 100 if max_profit > 0 else 0
        
        exit_reason = None
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
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
            buy_exit = engine.apply_slippage(buy_current, "SELL")
            sell_exit = engine.apply_slippage(sell_current, "BUY")
            
            trades.extend([
                Trade(
                    entry_time=buy_position['entry_time'],
                    exit_time=current_time,
                    strategy="Bull Call Spread",
                    underlying=config.underlying,
                    symbol=f"{config.underlying}{int(buy_strike)}CE",
                    option_type="CE",
                    strike=buy_strike,
                    action="BUY",
                    quantity=config.quantity,
                    entry_price=buy_position['entry_price'],
                    exit_price=buy_exit,
                    pnl=(buy_exit - buy_position['entry_price']) * config.quantity,
                    exit_reason=exit_reason,
                    holding_days=holding_days
                ),
                Trade(
                    entry_time=sell_position['entry_time'],
                    exit_time=current_time,
                    strategy="Bull Call Spread",
                    underlying=config.underlying,
                    symbol=f"{config.underlying}{int(sell_strike)}CE",
                    option_type="CE",
                    strike=sell_strike,
                    action="SELL",
                    quantity=config.quantity,
                    entry_price=sell_position['entry_price'],
                    exit_price=sell_exit,
                    pnl=(sell_position['entry_price'] - sell_exit) * config.quantity,
                    exit_reason=exit_reason,
                    holding_days=holding_days
                )
            ])
            break
    
    # Close at end
    if not trades and len(df) > 0:
        final_time = df['timestamp'].iloc[-1]
        final_spot = df['close'].iloc[-1]
        holding_days = (final_time - start_date).days
        
        buy_current = engine.simulate_option_price(final_spot, buy_strike, expiry_date, final_time, "CE")
        sell_current = engine.simulate_option_price(final_spot, sell_strike, expiry_date, final_time, "CE")
        
        buy_exit = engine.apply_slippage(buy_current, "SELL")
        sell_exit = engine.apply_slippage(sell_current, "BUY")
        
        trades.extend([
            Trade(
                entry_time=buy_position['entry_time'],
                exit_time=final_time,
                strategy="Bull Call Spread",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(buy_strike)}CE",
                option_type="CE",
                strike=buy_strike,
                action="BUY",
                quantity=config.quantity,
                entry_price=buy_position['entry_price'],
                exit_price=buy_exit,
                pnl=(buy_exit - buy_position['entry_price']) * config.quantity,
                exit_reason="END_OF_DATA",
                holding_days=holding_days
            ),
            Trade(
                entry_time=sell_position['entry_time'],
                exit_time=final_time,
                strategy="Bull Call Spread",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(sell_strike)}CE",
                option_type="CE",
                strike=sell_strike,
                action="SELL",
                quantity=config.quantity,
                entry_price=sell_position['entry_price'],
                exit_price=sell_exit,
                pnl=(sell_position['entry_price'] - sell_exit) * config.quantity,
                exit_reason="END_OF_DATA",
                holding_days=holding_days
            )
        ])
    
    return trades

# ==================== BEAR PUT SPREAD ====================

def backtest_bear_put_spread(
    engine: OptionBacktestEngine,
    df: pd.DataFrame,
    config: BacktestConfig,
    buy_offset: str = "ITM2",
    sell_otm: int = 5
) -> List[Trade]:
    """Backtest Bear Put Spread: Buy ITM/ATM Put, Sell OTM Put"""
    trades = []
    
    if len(df) < 10:
        return trades
    
    start_date = df['timestamp'].iloc[0]
    expiry_date = engine.get_expiry_date(start_date)
    spot = df['close'].iloc[0]
    
    buy_strike = engine.get_strike_from_offset(spot, buy_offset, "PE")
    sell_strike = engine.get_strike_from_offset(spot, f"OTM{sell_otm}", "PE")
    
    buy_price = engine.simulate_option_price(spot, buy_strike, expiry_date, start_date, "PE")
    sell_price = engine.simulate_option_price(spot, sell_strike, expiry_date, start_date, "PE")
    
    buy_price = engine.apply_slippage(buy_price, "BUY")
    sell_price = engine.apply_slippage(sell_price, "SELL")
    
    net_premium_paid = (buy_price - sell_price) * config.quantity
    max_profit = ((buy_strike - sell_strike) - (buy_price - sell_price)) * config.quantity
    
    buy_position = {'strike': buy_strike, 'entry_price': buy_price, 'entry_time': start_date}
    sell_position = {'strike': sell_strike, 'entry_price': sell_price, 'entry_time': start_date}
    
    # Monitor for exit
    for i in range(1, len(df)):
        current_time = df['timestamp'].iloc[i]
        spot = df['close'].iloc[i]
        
        buy_current = engine.simulate_option_price(spot, buy_strike, expiry_date, current_time, "PE")
        sell_current = engine.simulate_option_price(spot, sell_strike, expiry_date, current_time, "PE")
        
        current_value = (buy_current - sell_current) * config.quantity
        current_pnl = current_value - net_premium_paid
        pnl_pct = (current_pnl / max_profit) * 100 if max_profit > 0 else 0
        
        exit_reason = None
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
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
            buy_exit = engine.apply_slippage(buy_current, "SELL")
            sell_exit = engine.apply_slippage(sell_current, "BUY")
            
            trades.extend([
                Trade(
                    entry_time=buy_position['entry_time'],
                    exit_time=current_time,
                    strategy="Bear Put Spread",
                    underlying=config.underlying,
                    symbol=f"{config.underlying}{int(buy_strike)}PE",
                    option_type="PE",
                    strike=buy_strike,
                    action="BUY",
                    quantity=config.quantity,
                    entry_price=buy_position['entry_price'],
                    exit_price=buy_exit,
                    pnl=(buy_exit - buy_position['entry_price']) * config.quantity,
                    exit_reason=exit_reason,
                    holding_days=holding_days
                ),
                Trade(
                    entry_time=sell_position['entry_time'],
                    exit_time=current_time,
                    strategy="Bear Put Spread",
                    underlying=config.underlying,
                    symbol=f"{config.underlying}{int(sell_strike)}PE",
                    option_type="PE",
                    strike=sell_strike,
                    action="SELL",
                    quantity=config.quantity,
                    entry_price=sell_position['entry_price'],
                    exit_price=sell_exit,
                    pnl=(sell_position['entry_price'] - sell_exit) * config.quantity,
                    exit_reason=exit_reason,
                    holding_days=holding_days
                )
            ])
            break
    
    # Close at end
    if not trades and len(df) > 0:
        final_time = df['timestamp'].iloc[-1]
        final_spot = df['close'].iloc[-1]
        holding_days = (final_time - start_date).days
        
        buy_current = engine.simulate_option_price(final_spot, buy_strike, expiry_date, final_time, "PE")
        sell_current = engine.simulate_option_price(final_spot, sell_strike, expiry_date, final_time, "PE")
        
        buy_exit = engine.apply_slippage(buy_current, "SELL")
        sell_exit = engine.apply_slippage(sell_current, "BUY")
        
        trades.extend([
            Trade(
                entry_time=buy_position['entry_time'],
                exit_time=final_time,
                strategy="Bear Put Spread",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(buy_strike)}PE",
                option_type="PE",
                strike=buy_strike,
                action="BUY",
                quantity=config.quantity,
                entry_price=buy_position['entry_price'],
                exit_price=buy_exit,
                pnl=(buy_exit - buy_position['entry_price']) * config.quantity,
                exit_reason="END_OF_DATA",
                holding_days=holding_days
            ),
            Trade(
                entry_time=sell_position['entry_time'],
                exit_time=final_time,
                strategy="Bear Put Spread",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(sell_strike)}PE",
                option_type="PE",
                strike=sell_strike,
                action="SELL",
                quantity=config.quantity,
                entry_price=sell_position['entry_price'],
                exit_price=sell_exit,
                pnl=(sell_position['entry_price'] - sell_exit) * config.quantity,
                exit_reason="END_OF_DATA",
                holding_days=holding_days
            )
        ])
    
    return trades

# ==================== IRON BUTTERFLY STRATEGY ====================

def backtest_iron_butterfly(
    engine: OptionBacktestEngine,
    df: pd.DataFrame,
    config: BacktestConfig,
    wing_otm: int = 5
) -> List[Trade]:
    """Backtest Iron Butterfly strategy: Sell ATM Call + Put, Buy OTM Call + Put"""
    trades = []
    
    if len(df) < 10:
        return trades
    
    # Similar to Iron Condor but with ATM short strikes
    # Implementation similar to iron condor but with ATM instead of OTM for shorts
    return backtest_iron_condor(engine, df, config, sell_otm=0, buy_otm=wing_otm)

# ==================== PROTECTIVE PUT STRATEGY ====================

def backtest_protective_put(
    engine: OptionBacktestEngine,
    df: pd.DataFrame,
    config: BacktestConfig,
    put_offset: str = "OTM2"
) -> List[Trade]:
    """Backtest Protective Put strategy: Long underlying + Buy Put"""
    trades = []
    
    if len(df) < 10:
        return trades
    
    # This strategy assumes you already have a long position in underlying
    # We'll simulate buying a put to protect the position
    start_date = df['timestamp'].iloc[0]
    expiry_date = engine.get_expiry_date(start_date)
    
    spot = df['close'].iloc[0]
    put_strike = engine.get_strike_from_offset(spot, put_offset, "PE")
    
    put_entry_price = engine.simulate_option_price(
        spot, put_strike, expiry_date, start_date, "PE"
    )
    put_entry_price = engine.apply_slippage(put_entry_price, "BUY")
    
    # Track position
    put_position = {
        'strike': put_strike,
        'entry_price': put_entry_price,
        'entry_time': start_date,
        'quantity': config.quantity
    }
    
    # Monitor for exit
    for i in range(1, len(df)):
        current_time = df['timestamp'].iloc[i]
        spot = df['close'].iloc[i]
        
        put_price = engine.simulate_option_price(
            spot, put_position['strike'], expiry_date, current_time, "PE"
        )
        
        # Simple exit: close if profitable or at expiry
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
        exit_reason = None
        if current_time >= expiry_date:
            exit_reason = "EXPIRY"
        elif days_to_expiry <= config.time_based_exit_days:
            exit_reason = "TIME_BASED"
        elif holding_days >= config.max_holding_days:
            exit_reason = "MAX_HOLDING"
        
        if exit_reason:
            put_exit_price = engine.apply_slippage(put_price, "SELL")
            
            trade = Trade(
                entry_time=put_position['entry_time'],
                exit_time=current_time,
                strategy="Protective Put",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(put_position['strike'])}PE",
                option_type="PE",
                strike=put_position['strike'],
                action="BUY",
                quantity=config.quantity,
                entry_price=put_position['entry_price'],
                exit_price=put_exit_price,
                pnl=(put_exit_price - put_position['entry_price']) * config.quantity,
                exit_reason=exit_reason,
                holding_days=holding_days
            )
            trades.append(trade)
            break
    
    return trades

# ==================== COVERED CALL STRATEGY ====================

def backtest_covered_call(
    engine: OptionBacktestEngine,
    df: pd.DataFrame,
    config: BacktestConfig,
    call_otm: int = 2
) -> List[Trade]:
    """Backtest Covered Call strategy: Long underlying + Sell Call"""
    trades = []
    
    if len(df) < 10:
        return trades
    
    # This strategy assumes you already have a long position in underlying
    # We'll simulate selling a call against the position
    start_date = df['timestamp'].iloc[0]
    expiry_date = engine.get_expiry_date(start_date)
    
    spot = df['close'].iloc[0]
    call_strike = engine.get_strike_from_offset(spot, f"OTM{call_otm}", "CE")
    
    call_entry_price = engine.simulate_option_price(
        spot, call_strike, expiry_date, start_date, "CE"
    )
    call_entry_price = engine.apply_slippage(call_entry_price, "SELL")
    
    # Track position
    call_position = {
        'strike': call_strike,
        'entry_price': call_entry_price,
        'entry_time': start_date,
        'quantity': config.quantity
    }
    
    # Monitor for exit
    for i in range(1, len(df)):
        current_time = df['timestamp'].iloc[i]
        spot = df['close'].iloc[i]
        
        call_price = engine.simulate_option_price(
            spot, call_position['strike'], expiry_date, current_time, "CE"
        )
        
        days_to_expiry = (expiry_date - current_time).days
        holding_days = (current_time - start_date).days
        
        exit_reason = None
        if current_time >= expiry_date:
            exit_reason = "EXPIRY"
        elif days_to_expiry <= config.time_based_exit_days:
            exit_reason = "TIME_BASED"
        elif holding_days >= config.max_holding_days:
            exit_reason = "MAX_HOLDING"
        
        if exit_reason:
            call_exit_price = engine.apply_slippage(call_price, "BUY")
            
            trade = Trade(
                entry_time=call_position['entry_time'],
                exit_time=current_time,
                strategy="Covered Call",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(call_position['strike'])}CE",
                option_type="CE",
                strike=call_position['strike'],
                action="SELL",
                quantity=config.quantity,
                entry_price=call_position['entry_price'],
                exit_price=call_exit_price,
                pnl=(call_position['entry_price'] - call_exit_price) * config.quantity,  # Reversed for SELL
                exit_reason=exit_reason,
                holding_days=holding_days
            )
            trades.append(trade)
            break
    
    return trades

# ==================== CALENDAR SPREAD STRATEGY ====================

def backtest_calendar_spread(
    engine: OptionBacktestEngine,
    df: pd.DataFrame,
    config: BacktestConfig,
    strike_offset: str = "ATM",
    option_type: str = "CE"
) -> List[Trade]:
    """Backtest Calendar Spread: Sell near-term + Buy far-term"""
    trades = []
    
    if len(df) < 10:
        return trades
    
    # Calendar spread requires two different expiry dates
    # For simplicity, we'll use current expiry and next expiry
    start_date = df['timestamp'].iloc[0]
    near_expiry = engine.get_expiry_date(start_date)
    far_expiry = near_expiry + timedelta(days=7)  # Next week's expiry
    
    spot = df['close'].iloc[0]
    strike = engine.get_strike_from_offset(spot, strike_offset, option_type)
    
    # Sell near-term
    near_entry_price = engine.simulate_option_price(
        spot, strike, near_expiry, start_date, option_type
    )
    near_entry_price = engine.apply_slippage(near_entry_price, "SELL")
    
    # Buy far-term
    far_entry_price = engine.simulate_option_price(
        spot, strike, far_expiry, start_date, option_type
    )
    far_entry_price = engine.apply_slippage(far_entry_price, "BUY")
    
    net_premium = (far_entry_price - near_entry_price) * config.quantity
    
    # Track positions
    near_position = {
        'strike': strike,
        'entry_price': near_entry_price,
        'entry_time': start_date,
        'expiry': near_expiry,
        'quantity': config.quantity
    }
    
    far_position = {
        'strike': strike,
        'entry_price': far_entry_price,
        'entry_time': start_date,
        'expiry': far_expiry,
        'quantity': config.quantity
    }
    
    # Monitor for exit
    for i in range(1, len(df)):
        current_time = df['timestamp'].iloc[i]
        spot = df['close'].iloc[i]
        
        near_price = engine.simulate_option_price(
            spot, strike, near_expiry, current_time, option_type
        )
        far_price = engine.simulate_option_price(
            spot, strike, far_expiry, current_time, option_type
        )
        
        current_value = (far_price - near_price) * config.quantity
        current_pnl = current_value - net_premium
        pnl_pct = (current_pnl / abs(net_premium)) * 100 if net_premium != 0 else 0
        
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
            near_exit_price = engine.apply_slippage(near_price, "BUY")
            far_exit_price = engine.apply_slippage(far_price, "SELL")
            
            near_trade = Trade(
                entry_time=near_position['entry_time'],
                exit_time=current_time,
                strategy="Calendar Spread",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(strike)}{option_type}",
                option_type=option_type,
                strike=strike,
                action="SELL",
                quantity=config.quantity,
                entry_price=near_position['entry_price'],
                exit_price=near_exit_price,
                pnl=(near_position['entry_price'] - near_exit_price) * config.quantity,
                exit_reason=exit_reason,
                holding_days=holding_days
            )
            
            far_trade = Trade(
                entry_time=far_position['entry_time'],
                exit_time=current_time,
                strategy="Calendar Spread",
                underlying=config.underlying,
                symbol=f"{config.underlying}{int(strike)}{option_type}",
                option_type=option_type,
                strike=strike,
                action="BUY",
                quantity=config.quantity,
                entry_price=far_position['entry_price'],
                exit_price=far_exit_price,
                pnl=(far_exit_price - far_position['entry_price']) * config.quantity,
                exit_reason=exit_reason,
                holding_days=holding_days
            )
            
            trades.extend([near_trade, far_trade])
            break
    
    return trades

# Strategy mapping
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

