#!/usr/bin/env python
"""
Final Improved Strategies - Balanced Approach
Based on backtest insights: RSI performs well, others need better balance
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from utils.nse_data_fetcher import get_nse_data
except ImportError:
    import yfinance as yf
    
    def get_nse_data(symbol, exchange='NSE', interval='5m', period='1d'):
        symbol_map = {'NIFTY': '^NSEI', 'BANKNIFTY': '^NSEBANK'}
        yf_symbol = symbol_map.get(symbol, f"{symbol}.NS")
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df.columns = [col.lower() for col in df.columns]
        df.reset_index(inplace=True)
        if 'date' in df.columns:
            df.rename(columns={'date': 'timestamp'}, inplace=True)
        elif 'datetime' in df.columns:
            df.rename(columns={'datetime': 'timestamp'}, inplace=True)
        if 'close' not in df.columns and 'Close' in df.columns:
            df.rename(columns={'Close': 'close'}, inplace=True)
        return df

load_dotenv(override=False)
os.environ['STRATEGY_SCALPING_ENABLED'] = 'false'


def calculate_ema(data: pd.DataFrame, period: int) -> pd.Series:
    return data['close'].ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_macd(data: pd.DataFrame, fast=12, slow=26, signal=9):
    ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


# ========== FINAL EMA STRATEGY - Less Restrictive ==========
def backtest_ema_final(df: pd.DataFrame, symbol: str, fast_period=9, slow_period=21,
                       stop_loss_pct=2.0, quantity=1):
    """
    EMA Crossover with:
    - Basic crossover signal
    - RSI confirmation (avoid extreme overbought/oversold only)
    - Stop loss protection
    """
    trades = []
    position = 0
    entry_price = None
    stop_loss_price = None
    
    if len(df) < slow_period + 14:
        return trades
    
    ema_fast = calculate_ema(df, fast_period)
    ema_slow = calculate_ema(df, slow_period)
    rsi = calculate_rsi(df, 14)
    
    for i in range(slow_period + 14, len(df)):
        current_price = df['close'].iloc[i]
        prev_fast = ema_fast.iloc[i-1]
        curr_fast = ema_fast.iloc[i]
        prev_slow = ema_slow.iloc[i-1]
        curr_slow = ema_slow.iloc[i]
        curr_rsi = rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else 50
        
        # Check stop loss
        if position != 0 and stop_loss_price is not None:
            if position > 0 and current_price <= stop_loss_price:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': position, 'action': 'SELL', 'pnl': pnl, 'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
            elif position < 0 and current_price >= stop_loss_price:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': abs(position), 'action': 'BUY', 'pnl': pnl, 'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
        
        # Crossover signals
        buy_crossover = (prev_fast < prev_slow) and (curr_fast > curr_slow)
        sell_crossover = (prev_fast > prev_slow) and (curr_fast < curr_slow)
        
        # RSI filter: Only avoid extreme conditions (not too restrictive)
        rsi_ok_buy = curr_rsi < 75  # Allow more room
        rsi_ok_sell = curr_rsi > 25  # Allow more room
        
        buy_signal = buy_crossover and rsi_ok_buy
        sell_signal = sell_crossover and rsi_ok_sell
        
        if buy_signal and position <= 0:
            if position < 0:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': abs(position), 'action': 'BUY', 'pnl': pnl, 'type': 'CLOSE_SHORT'
                })
            position = quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        
        elif sell_signal and position >= 0:
            if position > 0:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': position, 'action': 'SELL', 'pnl': pnl, 'type': 'CLOSE_LONG'
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
            'symbol': symbol, 'entry_price': entry_price, 'exit_price': final_price,
            'quantity': abs(position), 'action': 'SELL' if position > 0 else 'BUY',
            'pnl': pnl, 'type': 'FINAL_CLOSE'
        })
    
    return trades


# ========== FINAL MACD STRATEGY - Less Restrictive ==========
def backtest_macd_final(df: pd.DataFrame, symbol: str, fast=12, slow=26, signal=9,
                        stop_loss_pct=2.0, quantity=1):
    """
    MACD with:
    - MACD crossover signal
    - RSI confirmation (avoid extreme only)
    - Stop loss protection
    """
    trades = []
    position = 0
    entry_price = None
    stop_loss_price = None
    
    if len(df) < slow + signal + 14:
        return trades
    
    macd_line, signal_line, histogram = calculate_macd(df, fast, slow, signal)
    rsi = calculate_rsi(df, 14)
    
    for i in range(slow + signal + 14, len(df)):
        current_price = df['close'].iloc[i]
        
        # Check stop loss
        if position != 0 and stop_loss_price is not None:
            if position > 0 and current_price <= stop_loss_price:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': position, 'action': 'SELL', 'pnl': pnl, 'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
            elif position < 0 and current_price >= stop_loss_price:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': abs(position), 'action': 'BUY', 'pnl': pnl, 'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
        
        prev_macd = macd_line.iloc[i-1]
        curr_macd = macd_line.iloc[i]
        prev_signal = signal_line.iloc[i-1]
        curr_signal = signal_line.iloc[i]
        curr_rsi = rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else 50
        
        # MACD crossover
        macd_bullish = (prev_macd < prev_signal) and (curr_macd > curr_signal)
        macd_bearish = (prev_macd > prev_signal) and (curr_macd < curr_signal)
        
        # RSI filter: Only avoid extreme
        rsi_ok_buy = curr_rsi < 75
        rsi_ok_sell = curr_rsi > 25
        
        buy_signal = macd_bullish and rsi_ok_buy
        sell_signal = macd_bearish and rsi_ok_sell
        
        if buy_signal and position <= 0:
            if position < 0:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': abs(position), 'action': 'BUY', 'pnl': pnl, 'type': 'CLOSE_SHORT'
                })
            position = quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        
        elif sell_signal and position >= 0:
            if position > 0:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': position, 'action': 'SELL', 'pnl': pnl, 'type': 'CLOSE_LONG'
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
            'symbol': symbol, 'entry_price': entry_price, 'exit_price': final_price,
            'quantity': abs(position), 'action': 'SELL' if position > 0 else 'BUY',
            'pnl': pnl, 'type': 'FINAL_CLOSE'
        })
    
    return trades


# ========== FINAL RSI STRATEGY - Keep What Works ==========
def backtest_rsi_final(df: pd.DataFrame, symbol: str, period=14, oversold=30, overbought=70,
                        stop_loss_pct=2.0, quantity=1):
    """
    RSI Strategy (proven to work) with:
    - RSI oversold/overbought signals
    - Stop loss protection (NEW)
    """
    trades = []
    position = 0
    entry_price = None
    stop_loss_price = None
    
    if len(df) < period + 1:
        return trades
    
    rsi = calculate_rsi(df, period)
    
    for i in range(period, len(df)):
        current_price = df['close'].iloc[i]
        current_rsi = rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else 50
        
        # Check stop loss
        if position != 0 and stop_loss_price is not None:
            if position > 0 and current_price <= stop_loss_price:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': position, 'action': 'SELL', 'pnl': pnl, 'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
            elif position < 0 and current_price >= stop_loss_price:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': abs(position), 'action': 'BUY', 'pnl': pnl, 'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
        
        # RSI signals (original logic that works)
        buy_signal = current_rsi < oversold
        sell_signal = current_rsi > overbought
        
        if buy_signal and position <= 0:
            if position < 0:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': abs(position), 'action': 'BUY', 'pnl': pnl, 'type': 'CLOSE_SHORT'
                })
            position = quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        
        elif sell_signal and position >= 0:
            if position > 0:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': position, 'action': 'SELL', 'pnl': pnl, 'type': 'CLOSE_LONG'
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
            'symbol': symbol, 'entry_price': entry_price, 'exit_price': final_price,
            'quantity': abs(position), 'action': 'SELL' if position > 0 else 'BUY',
            'pnl': pnl, 'type': 'FINAL_CLOSE'
        })
    
    return trades


# ========== FINAL MULTI-INDICATOR - Balanced ==========
def backtest_multi_final(df: pd.DataFrame, symbol: str, stop_loss_pct=2.0,
                         take_profit_pct=4.0, quantity=1):
    """
    Multi-Indicator with:
    - MACD primary signal
    - RSI confirmation (less restrictive)
    - Stop loss and take profit
    """
    trades = []
    position = 0
    entry_price = None
    stop_loss_price = None
    take_profit_price = None
    
    if len(df) < 26 + 14:
        return trades
    
    macd_line, signal_line, histogram = calculate_macd(df, 12, 26, 9)
    rsi = calculate_rsi(df, 14)
    
    for i in range(26 + 14, len(df)):
        current_price = df['close'].iloc[i]
        
        # Check stop loss and take profit
        if position != 0:
            if position > 0:
                if stop_loss_price and current_price <= stop_loss_price:
                    pnl = (current_price - entry_price) * position
                    trades.append({
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                        'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                        'quantity': position, 'action': 'SELL', 'pnl': pnl, 'type': 'STOP_LOSS'
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
                        'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                        'quantity': position, 'action': 'SELL', 'pnl': pnl, 'type': 'TAKE_PROFIT'
                    })
                    position = 0
                    entry_price = None
                    stop_loss_price = None
                    take_profit_price = None
                    continue
            else:
                if stop_loss_price and current_price >= stop_loss_price:
                    pnl = (entry_price - current_price) * abs(position)
                    trades.append({
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                        'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                        'quantity': abs(position), 'action': 'BUY', 'pnl': pnl, 'type': 'STOP_LOSS'
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
                        'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                        'quantity': abs(position), 'action': 'BUY', 'pnl': pnl, 'type': 'TAKE_PROFIT'
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
        curr_rsi = rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else 50
        
        # MACD crossover
        macd_bullish = (prev_macd <= prev_signal) and (curr_macd > curr_signal)
        macd_bearish = (prev_macd >= prev_signal) and (curr_macd < curr_signal)
        
        # RSI filter: Less restrictive
        rsi_ok_buy = curr_rsi < 75
        rsi_ok_sell = curr_rsi > 25
        
        buy_signal = macd_bullish and rsi_ok_buy
        sell_signal = macd_bearish and rsi_ok_sell
        
        if buy_signal and position <= 0:
            if position < 0:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': abs(position), 'action': 'BUY', 'pnl': pnl, 'type': 'CLOSE_SHORT'
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
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': position, 'action': 'SELL', 'pnl': pnl, 'type': 'CLOSE_LONG'
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
            'symbol': symbol, 'entry_price': entry_price, 'exit_price': final_price,
            'quantity': abs(position), 'action': 'SELL' if position > 0 else 'BUY',
            'pnl': pnl, 'type': 'FINAL_CLOSE'
        })
    
    return trades


def analyze_trades(trades, strategy_name, symbol):
    if not trades:
        return {
            'strategy': strategy_name, 'symbol': symbol, 'total_trades': 0,
            'winning_trades': 0, 'losing_trades': 0, 'total_pnl': 0.0,
            'win_rate': 0.0, 'avg_win': 0.0, 'avg_loss': 0.0,
            'max_win': 0.0, 'max_loss': 0.0
        }
    
    closed_trades = [t for t in trades if t['type'] != 'FINAL_CLOSE']
    winning_trades = [t for t in closed_trades if t['pnl'] > 0]
    losing_trades = [t for t in closed_trades if t['pnl'] < 0]
    
    total_pnl = sum(t['pnl'] for t in trades)
    win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0.0
    
    return {
        'strategy': strategy_name, 'symbol': symbol,
        'total_trades': len(closed_trades), 'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades), 'total_pnl': total_pnl,
        'win_rate': win_rate,
        'avg_win': np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0.0,
        'avg_loss': np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0.0,
        'max_win': max([t['pnl'] for t in winning_trades]) if winning_trades else 0.0,
        'max_loss': min([t['pnl'] for t in losing_trades]) if losing_trades else 0.0
    }


def print_results(all_results, period='Today'):
    print("\n" + "="*120)
    print(f"BACKTEST RESULTS - {period.upper()} (FINAL STRATEGIES)")
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
        
        status = "[PROFIT]" if pnl > 0 else "[LOSS]" if pnl < 0 else "[BREAK EVEN]"
        pnl_str = f"Rs +{pnl:,.2f}" if pnl > 0 else f"Rs {pnl:,.2f}"
        win_rate_str = f"{win_rate:.1f}%" if win_rate > 0 else "N/A"
        avg_win_str = f"Rs {avg_win:,.2f}" if avg_win > 0 else "N/A"
        avg_loss_str = f"Rs {avg_loss:,.2f}" if avg_loss < 0 else "N/A"
        
        print(f"{strategy[:33]:<35} {symbol:<15} {trades:<10} {wins:<8} {losses:<8} {win_rate_str:<12} "
              f"{pnl_str:<15} {avg_win_str:<15} {avg_loss_str:<15} {status:<15}")
    
    print("-"*120)
    overall_win_rate = (total_wins_all / total_trades_all * 100) if total_trades_all > 0 else 0.0
    pnl_str = f"Rs +{total_pnl_all:,.2f}" if total_pnl_all > 0 else f"Rs {total_pnl_all:,.2f}"
    print(f"{'SUMMARY':<35} {'':<15} {total_trades_all:<10} {total_wins_all:<8} {total_losses_all:<8} "
          f"{overall_win_rate:.1f}%{'':<8} {pnl_str:<15} {'':<15} {'':<15}")
    print("="*120)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Backtest final improved strategies')
    parser.add_argument('--period', type=str, default='5d', choices=['1d', '5d', '1mo'])
    parser.add_argument('--interval', type=str, default='5m', choices=['1m', '5m', '15m', '1h', '1d'])
    parser.add_argument('--symbols', type=str, nargs='+', default=['NIFTY', 'BANKNIFTY'])
    
    args = parser.parse_args()
    
    print("\n" + "="*120)
    print("BACKTESTING FINAL IMPROVED STRATEGIES")
    print("="*120)
    print(f"\nPeriod: {args.period}, Interval: {args.interval}")
    print(f"Symbols: {', '.join(args.symbols)}")
    print("="*120)
    
    all_results = []
    strategies = [
        ('EMA Final (RSI Filter)', backtest_ema_final),
        ('MACD Final (RSI Filter)', backtest_macd_final),
        ('RSI Final (Stop Loss)', backtest_rsi_final),
        ('Multi-Indicator Final', backtest_multi_final)
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
                
                if 'multi' in strategy_name.lower():
                    trades = backtest_func(df, symbol, stop_loss_pct=2.0, take_profit_pct=4.0)
                else:
                    trades = backtest_func(df, symbol, stop_loss_pct=2.0)
                
                result = analyze_trades(trades, strategy_name, symbol)
                all_results.append(result)
                
                print(f"  Completed: {result['total_trades']} trades, "
                      f"P&L: Rs {result['total_pnl']:,.2f}, "
                      f"Win Rate: {result['win_rate']:.1f}%")
            
            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    if all_results:
        period_map = {'1d': 'Today', '5d': 'Last Week', '1mo': 'Last Month'}
        period_label = period_map.get(args.period, f'Last {args.period}')
        print_results(all_results, period_label)
    else:
        print("\nERROR: No backtest results generated.")


if __name__ == '__main__':
    main()


