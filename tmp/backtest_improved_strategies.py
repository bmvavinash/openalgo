#!/usr/bin/env python
"""
Comprehensive Backtest Script for Improved Strategies
Tests all strategies on historical data with proper stop-loss
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import data fetcher
try:
    from utils.nse_data_fetcher import get_nse_data
except ImportError:
    print("Warning: nse_data_fetcher not found, using yfinance directly")
    import yfinance as yf
    
    def get_nse_data(symbol, exchange='NSE', interval='5m', period='1d'):
        """Fallback data fetcher using yfinance"""
        try:
            # Map NSE indices
            symbol_map = {
                'NIFTY': '^NSEI',
                'BANKNIFTY': '^NSEBANK'
            }
            yf_symbol = symbol_map.get(symbol, f"{symbol}.NS")
            
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                return pd.DataFrame()
            
            # Normalize column names
            df.columns = [col.lower() for col in df.columns]
            df.reset_index(inplace=True)
            
            # Ensure timestamp column
            if 'date' in df.columns:
                df.rename(columns={'date': 'timestamp'}, inplace=True)
            elif 'datetime' in df.columns:
                df.rename(columns={'datetime': 'timestamp'}, inplace=True)
            elif df.index.name in ['Date', 'Datetime']:
                df.reset_index(inplace=True)
                df.rename(columns={df.columns[0]: 'timestamp'}, inplace=True)
            
            # Ensure required columns
            if 'close' not in df.columns and 'Close' in df.columns:
                df.rename(columns={'Close': 'close'}, inplace=True)
            
            return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

load_dotenv(override=False)

# Disable scalping for backtesting
os.environ['STRATEGY_SCALPING_ENABLED'] = 'false'


def calculate_ema(data: pd.DataFrame, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return data['close'].ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(data: pd.DataFrame, fast=12, slow=26, signal=9):
    """Calculate MACD indicators"""
    ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# ========== IMPROVED EMA CROSSOVER STRATEGY ==========
def backtest_ema_improved(df: pd.DataFrame, symbol: str, fast_period=9, slow_period=21, 
                          trend_period=50, stop_loss_pct=2.0, quantity=1):
    """
    Improved EMA Crossover with:
    - Trend filter (50 EMA)
    - RSI confirmation (avoid extreme conditions)
    - Stop loss protection
    """
    trades = []
    position = 0
    entry_price = None
    stop_loss_price = None
    
    if len(df) < trend_period + 1:
        return trades
    
    ema_fast = calculate_ema(df, fast_period)
    ema_slow = calculate_ema(df, slow_period)
    ema_trend = calculate_ema(df, trend_period)
    rsi = calculate_rsi(df, 14)
    
    for i in range(trend_period, len(df)):
        current_price = df['close'].iloc[i]
        prev_fast = ema_fast.iloc[i-1]
        curr_fast = ema_fast.iloc[i]
        prev_slow = ema_slow.iloc[i-1]
        curr_slow = ema_slow.iloc[i]
        curr_trend = ema_trend.iloc[i]
        curr_rsi = rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else 50
        
        # Check stop loss first
        if position != 0 and stop_loss_price is not None:
            if position > 0 and current_price <= stop_loss_price:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': position,
                    'action': 'SELL',
                    'pnl': pnl,
                    'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
            elif position < 0 and current_price >= stop_loss_price:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': abs(position),
                    'action': 'BUY',
                    'pnl': pnl,
                    'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
        
        # Crossover signals
        buy_crossover = (prev_fast < prev_slow) and (curr_fast > curr_slow)
        sell_crossover = (prev_fast > prev_slow) and (curr_fast < curr_slow)
        
        # Trend filter: Price above trend EMA for buy, below for sell
        uptrend = current_price > curr_trend
        downtrend = current_price < curr_trend
        
        # RSI filter: Avoid extreme conditions
        rsi_ok_buy = curr_rsi < 70  # Not overbought
        rsi_ok_sell = curr_rsi > 30  # Not oversold
        
        # Combined signals
        buy_signal = buy_crossover and uptrend and rsi_ok_buy
        sell_signal = sell_crossover and downtrend and rsi_ok_sell
        
        if buy_signal and position <= 0:
            if position < 0:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': abs(position),
                    'action': 'BUY',
                    'pnl': pnl,
                    'type': 'CLOSE_SHORT'
                })
            position = quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        
        elif sell_signal and position >= 0:
            if position > 0:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': position,
                    'action': 'SELL',
                    'pnl': pnl,
                    'type': 'CLOSE_LONG'
                })
            position = -quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
    
    # Close open position
    if position != 0:
        final_price = df['close'].iloc[-1]
        if position > 0:
            pnl = (final_price - entry_price) * position
            action = 'SELL'
        else:
            pnl = (entry_price - final_price) * abs(position)
            action = 'BUY'
        trades.append({
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else df.index[-1],
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': final_price,
            'quantity': abs(position),
            'action': action,
            'pnl': pnl,
            'type': 'FINAL_CLOSE'
        })
    
    return trades


# ========== IMPROVED MACD STRATEGY ==========
def backtest_macd_improved(df: pd.DataFrame, symbol: str, fast=12, slow=26, signal=9,
                           stop_loss_pct=2.0, quantity=1):
    """
    Improved MACD with:
    - RSI confirmation (avoid extreme conditions)
    - Trend filter (50 EMA)
    - Stop loss protection
    """
    trades = []
    position = 0
    entry_price = None
    stop_loss_price = None
    
    if len(df) < slow + signal + 50:
        return trades
    
    macd_line, signal_line, histogram = calculate_macd(df, fast, slow, signal)
    ema_trend = calculate_ema(df, 50)
    rsi = calculate_rsi(df, 14)
    
    for i in range(slow + signal + 50, len(df)):
        current_price = df['close'].iloc[i]
        
        # Check stop loss first
        if position != 0 and stop_loss_price is not None:
            if position > 0 and current_price <= stop_loss_price:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': position,
                    'action': 'SELL',
                    'pnl': pnl,
                    'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
            elif position < 0 and current_price >= stop_loss_price:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': abs(position),
                    'action': 'BUY',
                    'pnl': pnl,
                    'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
        
        prev_macd = macd_line.iloc[i-1]
        curr_macd = macd_line.iloc[i]
        prev_signal = signal_line.iloc[i-1]
        curr_signal = signal_line.iloc[i]
        curr_trend = ema_trend.iloc[i]
        curr_rsi = rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else 50
        
        # MACD crossover
        macd_bullish = (prev_macd < prev_signal) and (curr_macd > curr_signal)
        macd_bearish = (prev_macd > prev_signal) and (curr_macd < curr_signal)
        
        # Trend filter
        uptrend = current_price > curr_trend
        downtrend = current_price < curr_trend
        
        # RSI filter
        rsi_ok_buy = curr_rsi < 70
        rsi_ok_sell = curr_rsi > 30
        
        # Combined signals
        buy_signal = macd_bullish and uptrend and rsi_ok_buy
        sell_signal = macd_bearish and downtrend and rsi_ok_sell
        
        if buy_signal and position <= 0:
            if position < 0:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': abs(position),
                    'action': 'BUY',
                    'pnl': pnl,
                    'type': 'CLOSE_SHORT'
                })
            position = quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        
        elif sell_signal and position >= 0:
            if position > 0:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': position,
                    'action': 'SELL',
                    'pnl': pnl,
                    'type': 'CLOSE_LONG'
                })
            position = -quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
    
    # Close open position
    if position != 0:
        final_price = df['close'].iloc[-1]
        pnl = (final_price - entry_price) * position if position > 0 else (entry_price - final_price) * abs(position)
        trades.append({
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else df.index[-1],
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': final_price,
            'quantity': abs(position),
            'action': 'SELL' if position > 0 else 'BUY',
            'pnl': pnl,
            'type': 'FINAL_CLOSE'
        })
    
    return trades


# ========== IMPROVED RSI STRATEGY ==========
def backtest_rsi_improved(df: pd.DataFrame, symbol: str, period=14, oversold=30, overbought=70,
                          stop_loss_pct=2.0, quantity=1):
    """
    Improved RSI with:
    - Trend confirmation (50 EMA)
    - Stop loss protection
    """
    trades = []
    position = 0
    entry_price = None
    stop_loss_price = None
    
    if len(df) < max(period, 50) + 1:
        return trades
    
    rsi = calculate_rsi(df, period)
    ema_trend = calculate_ema(df, 50)
    
    for i in range(max(period, 50), len(df)):
        current_price = df['close'].iloc[i]
        current_rsi = rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else 50
        curr_trend = ema_trend.iloc[i]
        
        # Check stop loss first
        if position != 0 and stop_loss_price is not None:
            if position > 0 and current_price <= stop_loss_price:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': position,
                    'action': 'SELL',
                    'pnl': pnl,
                    'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
            elif position < 0 and current_price >= stop_loss_price:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': abs(position),
                    'action': 'BUY',
                    'pnl': pnl,
                    'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
        
        # RSI signals with trend confirmation
        buy_signal = (current_rsi < oversold) and (current_price > curr_trend)  # Oversold + uptrend
        sell_signal = (current_rsi > overbought) and (current_price < curr_trend)  # Overbought + downtrend
        
        if buy_signal and position <= 0:
            if position < 0:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': abs(position),
                    'action': 'BUY',
                    'pnl': pnl,
                    'type': 'CLOSE_SHORT'
                })
            position = quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        
        elif sell_signal and position >= 0:
            if position > 0:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': position,
                    'action': 'SELL',
                    'pnl': pnl,
                    'type': 'CLOSE_LONG'
                })
            position = -quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
    
    # Close open position
    if position != 0:
        final_price = df['close'].iloc[-1]
        pnl = (final_price - entry_price) * position if position > 0 else (entry_price - final_price) * abs(position)
        trades.append({
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else df.index[-1],
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': final_price,
            'quantity': abs(position),
            'action': 'SELL' if position > 0 else 'BUY',
            'pnl': pnl,
            'type': 'FINAL_CLOSE'
        })
    
    return trades


# ========== IMPROVED MULTI-INDICATOR STRATEGY ==========
def backtest_multi_improved(df: pd.DataFrame, symbol: str, stop_loss_pct=2.0, 
                            take_profit_pct=4.0, quantity=1):
    """
    Improved Multi-Indicator with:
    - MACD primary signal
    - EMA trend filter
    - RSI momentum filter
    - Stop loss and take profit
    """
    trades = []
    position = 0
    entry_price = None
    stop_loss_price = None
    take_profit_price = None
    
    if len(df) < 50 + 26:
        return trades
    
    macd_line, signal_line, histogram = calculate_macd(df, 12, 26, 9)
    ema_trend = calculate_ema(df, 50)
    rsi = calculate_rsi(df, 14)
    
    for i in range(50 + 26, len(df)):
        current_price = df['close'].iloc[i]
        
        # Check stop loss and take profit first
        if position != 0:
            if position > 0:  # LONG
                if stop_loss_price and current_price <= stop_loss_price:
                    pnl = (current_price - entry_price) * position
                    trades.append({
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                        'symbol': symbol,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'quantity': position,
                        'action': 'SELL',
                        'pnl': pnl,
                        'type': 'STOP_LOSS'
                    })
                    position = 0
                    entry_price = None
                    stop_loss_price = None
                    take_profit_price = None
                    continue
                elif take_profit_price and current_price >= take_profit_price:
                    pnl = (current_price - entry_price) * position
                    trades.append({
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                        'symbol': symbol,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'quantity': position,
                        'action': 'SELL',
                        'pnl': pnl,
                        'type': 'TAKE_PROFIT'
                    })
                    position = 0
                    entry_price = None
                    stop_loss_price = None
                    take_profit_price = None
                    continue
            else:  # SHORT
                if stop_loss_price and current_price >= stop_loss_price:
                    pnl = (entry_price - current_price) * abs(position)
                    trades.append({
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                        'symbol': symbol,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'quantity': abs(position),
                        'action': 'BUY',
                        'pnl': pnl,
                        'type': 'STOP_LOSS'
                    })
                    position = 0
                    entry_price = None
                    stop_loss_price = None
                    take_profit_price = None
                    continue
                elif take_profit_price and current_price <= take_profit_price:
                    pnl = (entry_price - current_price) * abs(position)
                    trades.append({
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                        'symbol': symbol,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'quantity': abs(position),
                        'action': 'BUY',
                        'pnl': pnl,
                        'type': 'TAKE_PROFIT'
                    })
                    position = 0
                    entry_price = None
                    stop_loss_price = None
                    take_profit_price = None
                    continue
        
        prev_macd = macd_line.iloc[i-1]
        curr_macd = macd_line.iloc[i]
        prev_signal = signal_line.iloc[i-1]
        curr_signal = signal_line.iloc[i]
        curr_trend = ema_trend.iloc[i]
        curr_rsi = rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else 50
        
        # MACD crossover
        macd_bullish = (prev_macd <= prev_signal) and (curr_macd > curr_signal)
        macd_bearish = (prev_macd >= prev_signal) and (curr_macd < curr_signal)
        
        # Trend filter
        uptrend = current_price > curr_trend
        downtrend = current_price < curr_trend
        
        # RSI filter
        rsi_ok_buy = curr_rsi < 65
        rsi_ok_sell = curr_rsi > 35
        
        # Combined signals
        buy_signal = macd_bullish and uptrend and rsi_ok_buy
        sell_signal = macd_bearish and downtrend and rsi_ok_sell
        
        if buy_signal and position <= 0:
            if position < 0:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': abs(position),
                    'action': 'BUY',
                    'pnl': pnl,
                    'type': 'CLOSE_SHORT'
                })
            position = quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
            take_profit_price = entry_price * (1 + take_profit_pct / 100)
        
        elif sell_signal and position >= 0:
            if position > 0:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': position,
                    'action': 'SELL',
                    'pnl': pnl,
                    'type': 'CLOSE_LONG'
                })
            position = -quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
            take_profit_price = entry_price * (1 - take_profit_pct / 100)
    
    # Close open position
    if position != 0:
        final_price = df['close'].iloc[-1]
        pnl = (final_price - entry_price) * position if position > 0 else (entry_price - final_price) * abs(position)
        trades.append({
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else df.index[-1],
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': final_price,
            'quantity': abs(position),
            'action': 'SELL' if position > 0 else 'BUY',
            'pnl': pnl,
            'type': 'FINAL_CLOSE'
        })
    
    return trades


def analyze_trades(trades, strategy_name, symbol):
    """Analyze backtest trades and calculate statistics"""
    if not trades:
        return {
            'strategy': strategy_name,
            'symbol': symbol,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'max_win': 0.0,
            'max_loss': 0.0
        }
    
    closed_trades = [t for t in trades if t['type'] != 'FINAL_CLOSE']
    
    winning_trades = [t for t in closed_trades if t['pnl'] > 0]
    losing_trades = [t for t in closed_trades if t['pnl'] < 0]
    
    total_pnl = sum(t['pnl'] for t in trades)
    win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0.0
    
    avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0.0
    avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0.0
    max_win = max([t['pnl'] for t in winning_trades]) if winning_trades else 0.0
    max_loss = min([t['pnl'] for t in losing_trades]) if losing_trades else 0.0
    
    return {
        'strategy': strategy_name,
        'symbol': symbol,
        'total_trades': len(closed_trades),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_win': max_win,
        'max_loss': max_loss
    }


def print_results(all_results, period='Today'):
    """Print backtest results in a formatted table"""
    print("\n" + "="*120)
    print(f"BACKTEST RESULTS - {period.upper()} (IMPROVED STRATEGIES)")
    print("="*120)
    print(f"\n{'Strategy':<35} {'Symbol':<15} {'Trades':<10} {'Wins':<8} {'Losses':<8} {'Win Rate':<12} "
          f"{'Total P&L':<15} {'Avg Win':<15} {'Avg Loss':<15} {'Status':<15}")
    print("-"*120)
    
    total_pnl_all = 0.0
    total_trades_all = 0
    total_wins_all = 0
    total_losses_all = 0
    
    for result in all_results:
        strategy = result['strategy']
        symbol = result['symbol']
        trades = result['total_trades']
        wins = result['winning_trades']
        losses = result['losing_trades']
        win_rate = result['win_rate']
        pnl = result['total_pnl']
        avg_win = result['avg_win']
        avg_loss = result['avg_loss']
        
        total_pnl_all += pnl
        total_trades_all += trades
        total_wins_all += wins
        total_losses_all += losses
        
        if pnl > 0:
            status = "[PROFIT]"
            pnl_str = f"Rs +{pnl:,.2f}"
        elif pnl < 0:
            status = "[LOSS]"
            pnl_str = f"Rs {pnl:,.2f}"
        else:
            status = "[BREAK EVEN]"
            pnl_str = f"Rs {pnl:,.2f}"
        
        win_rate_str = f"{win_rate:.1f}%" if win_rate > 0 else "N/A"
        avg_win_str = f"Rs {avg_win:,.2f}" if avg_win > 0 else "N/A"
        avg_loss_str = f"Rs {avg_loss:,.2f}" if avg_loss < 0 else "N/A"
        
        print(f"{strategy[:33]:<35} {symbol:<15} {trades:<10} {wins:<8} {losses:<8} {win_rate_str:<12} "
              f"{pnl_str:<15} {avg_win_str:<15} {avg_loss_str:<15} {status:<15}")
    
    print("-"*120)
    
    # Summary
    overall_win_rate = (total_wins_all / total_trades_all * 100) if total_trades_all > 0 else 0.0
    if total_pnl_all > 0:
        pnl_str = f"Rs +{total_pnl_all:,.2f}"
    else:
        pnl_str = f"Rs {total_pnl_all:,.2f}"
    
    print(f"{'SUMMARY':<35} {'':<15} {total_trades_all:<10} {total_wins_all:<8} {total_losses_all:<8} "
          f"{overall_win_rate:.1f}%{'':<8} {pnl_str:<15} {'':<15} {'':<15}")
    print("="*120)


def main():
    """Main backtest function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backtest improved strategies on historical data')
    parser.add_argument('--period', type=str, default='5d',
                       choices=['1d', '5d', '1mo'],
                       help='Time period for backtest (default: 5d)')
    parser.add_argument('--interval', type=str, default='5m',
                       choices=['1m', '5m', '15m', '1h', '1d'],
                       help='Data interval (default: 5m)')
    parser.add_argument('--symbols', type=str, nargs='+',
                       default=['NIFTY', 'BANKNIFTY'],
                       help='Symbols to backtest (default: NIFTY BANKNIFTY)')
    
    args = parser.parse_args()
    
    print("\n" + "="*120)
    print("BACKTESTING IMPROVED STRATEGIES")
    print("="*120)
    print(f"\nPeriod: {args.period}")
    print(f"Interval: {args.interval}")
    print(f"Symbols: {', '.join(args.symbols)}")
    print(f"Scalping: DISABLED")
    print("\n" + "="*120)
    
    all_results = []
    
    strategies = [
        ('EMA Improved (Trend+RSI Filter)', backtest_ema_improved),
        ('MACD Improved (Trend+RSI Filter)', backtest_macd_improved),
        ('RSI Improved (Trend Confirmation)', backtest_rsi_improved),
        ('Multi-Indicator Improved', backtest_multi_improved)
    ]
    
    for strategy_name, backtest_func in strategies:
        print(f"\n{'-'*120}")
        print(f"Backtesting: {strategy_name}")
        print(f"{'-'*120}")
        
        for symbol in args.symbols:
            try:
                print(f"\n  Fetching data for {symbol}...")
                df = get_nse_data(symbol=symbol, exchange='NSE', interval=args.interval, period=args.period)
                
                if df.empty:
                    print(f"  WARNING: No data available for {symbol}")
                    continue
                
                print(f"  Loaded {len(df)} data points")
                if 'timestamp' in df.columns:
                    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
                
                # Run backtest
                if 'multi' in strategy_name.lower():
                    trades = backtest_func(df, symbol, stop_loss_pct=2.0, take_profit_pct=4.0)
                else:
                    trades = backtest_func(df, symbol, stop_loss_pct=2.0)
                
                # Analyze results
                result = analyze_trades(trades, strategy_name, symbol)
                all_results.append(result)
                
                print(f"  Completed: {result['total_trades']} trades, "
                      f"P&L: Rs {result['total_pnl']:,.2f}, "
                      f"Win Rate: {result['win_rate']:.1f}%")
            
            except Exception as e:
                print(f"  ERROR: Error backtesting {symbol}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    # Print summary
    if all_results:
        period_map = {'1d': 'Today', '5d': 'Last Week', '1mo': 'Last Month'}
        period_label = period_map.get(args.period, f'Last {args.period}')
        print_results(all_results, period_label)
    else:
        print("\nERROR: No backtest results generated.")


if __name__ == '__main__':
    main()



