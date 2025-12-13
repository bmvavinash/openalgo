#!/usr/bin/env python
"""
Test MACD and Multi-Indicator strategies with different timeframes
to see if performance improves
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
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def backtest_macd_strategy(df: pd.DataFrame, symbol: str, fast=12, slow=26, signal=9,
                            stop_loss_pct=2.0, quantity=1):
    """MACD strategy with RSI filter"""
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
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': position, 'pnl': pnl, 'type': 'STOP_LOSS'
                })
                position = 0
                entry_price = None
                stop_loss_price = None
                continue
            elif position < 0 and current_price >= stop_loss_price:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': abs(position), 'pnl': pnl, 'type': 'STOP_LOSS'
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
        
        macd_bullish = (prev_macd < prev_signal) and (curr_macd > curr_signal)
        macd_bearish = (prev_macd > prev_signal) and (curr_macd < curr_signal)
        
        rsi_ok_buy = curr_rsi < 75
        rsi_ok_sell = curr_rsi > 25
        
        buy_signal = macd_bullish and rsi_ok_buy
        sell_signal = macd_bearish and rsi_ok_sell
        
        if buy_signal and position <= 0:
            if position < 0:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': abs(position), 'pnl': pnl, 'type': 'CLOSE_SHORT'
                })
            position = quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        
        elif sell_signal and position >= 0:
            if position > 0:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': position, 'pnl': pnl, 'type': 'CLOSE_LONG'
                })
            position = -quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
    
    if position != 0:
        final_price = df['close'].iloc[-1]
        pnl = (final_price - entry_price) * position if position > 0 else (entry_price - final_price) * abs(position)
        trades.append({
            'symbol': symbol, 'entry_price': entry_price, 'exit_price': final_price,
            'quantity': abs(position), 'pnl': pnl, 'type': 'FINAL_CLOSE'
        })
    
    return trades


def backtest_multi_strategy(df: pd.DataFrame, symbol: str, stop_loss_pct=2.0,
                            take_profit_pct=4.0, quantity=1):
    """Multi-Indicator strategy"""
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
        
        if position != 0:
            if position > 0:
                if stop_loss_price and current_price <= stop_loss_price:
                    pnl = (current_price - entry_price) * position
                    trades.append({
                        'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                        'quantity': position, 'pnl': pnl, 'type': 'STOP_LOSS'
                    })
                    position = 0
                    entry_price = None
                    stop_loss_price = None
                    take_profit_price = None
                    continue
                elif take_profit_price and current_price >= take_profit_price:
                    pnl = (current_price - entry_price) * position
                    trades.append({
                        'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                        'quantity': position, 'pnl': pnl, 'type': 'TAKE_PROFIT'
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
                        'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                        'quantity': abs(position), 'pnl': pnl, 'type': 'STOP_LOSS'
                    })
                    position = 0
                    entry_price = None
                    stop_loss_price = None
                    take_profit_price = None
                    continue
                elif take_profit_price and current_price <= take_profit_price:
                    pnl = (entry_price - current_price) * abs(position)
                    trades.append({
                        'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                        'quantity': abs(position), 'pnl': pnl, 'type': 'TAKE_PROFIT'
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
        
        macd_bullish = (prev_macd <= prev_signal) and (curr_macd > curr_signal)
        macd_bearish = (prev_macd >= prev_signal) and (curr_macd < curr_signal)
        
        uptrend = current_price > curr_trend
        downtrend = current_price < curr_trend
        
        rsi_not_overbought = curr_rsi < 65
        rsi_not_oversold = curr_rsi > 35
        
        buy_signal = macd_bullish and uptrend and rsi_not_overbought
        sell_signal = macd_bearish and downtrend and rsi_not_oversold
        
        if buy_signal and position <= 0:
            if position < 0:
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': abs(position), 'pnl': pnl, 'type': 'CLOSE_SHORT'
                })
            position = quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
            take_profit_price = entry_price * (1 + take_profit_pct / 100)
        
        elif sell_signal and position >= 0:
            if position > 0:
                pnl = (current_price - entry_price) * position
                trades.append({
                    'symbol': symbol, 'entry_price': entry_price, 'exit_price': current_price,
                    'quantity': position, 'pnl': pnl, 'type': 'CLOSE_LONG'
                })
            position = -quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
            take_profit_price = entry_price * (1 - take_profit_pct / 100)
    
    if position != 0:
        final_price = df['close'].iloc[-1]
        pnl = (final_price - entry_price) * position if position > 0 else (entry_price - final_price) * abs(position)
        trades.append({
            'symbol': symbol, 'entry_price': entry_price, 'exit_price': final_price,
            'quantity': abs(position), 'pnl': pnl, 'type': 'FINAL_CLOSE'
        })
    
    return trades


def analyze_trades(trades, strategy_name, symbol, interval):
    if not trades:
        return {
            'strategy': strategy_name, 'symbol': symbol, 'interval': interval,
            'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
            'total_pnl': 0.0, 'win_rate': 0.0
        }
    
    closed_trades = [t for t in trades if t['type'] != 'FINAL_CLOSE']
    winning_trades = [t for t in closed_trades if t['pnl'] > 0]
    losing_trades = [t for t in closed_trades if t['pnl'] < 0]
    
    total_pnl = sum(t['pnl'] for t in trades)
    win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0.0
    
    return {
        'strategy': strategy_name, 'symbol': symbol, 'interval': interval,
        'total_trades': len(closed_trades), 'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades), 'total_pnl': total_pnl,
        'win_rate': win_rate
    }


def main():
    print("\n" + "="*120)
    print("TESTING MACD AND MULTI-INDICATOR WITH DIFFERENT TIMEFRAMES")
    print("="*120)
    
    intervals = ['5m', '15m', '1h']
    symbols = ['NIFTY', 'BANKNIFTY']
    period = '5d'  # Last 5 days
    
    all_results = []
    
    for interval in intervals:
        print(f"\n{'-'*120}")
        print(f"Testing with {interval} interval")
        print(f"{'-'*120}")
        
        for symbol in symbols:
            try:
                print(f"\n  Fetching {symbol} data ({interval})...")
                df = get_nse_data(symbol=symbol, exchange='NSE', interval=interval, period=period)
                
                if df.empty:
                    print(f"  WARNING: No data for {symbol} at {interval}")
                    continue
                
                print(f"  Loaded {len(df)} data points")
                
                # Test MACD
                macd_trades = backtest_macd_strategy(df, symbol, stop_loss_pct=2.0)
                macd_result = analyze_trades(macd_trades, 'MACD Strategy', symbol, interval)
                all_results.append(macd_result)
                print(f"  MACD: {macd_result['total_trades']} trades, "
                      f"P&L: Rs {macd_result['total_pnl']:,.2f}, "
                      f"Win Rate: {macd_result['win_rate']:.1f}%")
                
                # Test Multi-Indicator
                multi_trades = backtest_multi_strategy(df, symbol, stop_loss_pct=2.0, take_profit_pct=4.0)
                multi_result = analyze_trades(multi_trades, 'Multi-Indicator', symbol, interval)
                all_results.append(multi_result)
                print(f"  Multi: {multi_result['total_trades']} trades, "
                      f"P&L: Rs {multi_result['total_pnl']:,.2f}, "
                      f"Win Rate: {multi_result['win_rate']:.1f}%")
            
            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    # Print summary
    print("\n" + "="*120)
    print("SUMMARY - BEST PERFORMING TIMEFRAME")
    print("="*120)
    print(f"\n{'Strategy':<20} {'Symbol':<15} {'Interval':<10} {'Trades':<10} {'Win Rate':<12} {'Total P&L':<15} {'Status':<15}")
    print("-"*120)
    
    # Group by strategy and symbol, find best interval
    best_results = {}
    for result in all_results:
        key = (result['strategy'], result['symbol'])
        if key not in best_results or result['total_pnl'] > best_results[key]['total_pnl']:
            best_results[key] = result
    
    for (strategy, symbol), result in sorted(best_results.items()):
        status = "[PROFIT]" if result['total_pnl'] > 0 else "[LOSS]" if result['total_pnl'] < 0 else "[BREAK EVEN]"
        pnl_str = f"Rs +{result['total_pnl']:,.2f}" if result['total_pnl'] > 0 else f"Rs {result['total_pnl']:,.2f}"
        win_rate_str = f"{result['win_rate']:.1f}%" if result['win_rate'] > 0 else "N/A"
        
        print(f"{strategy:<20} {symbol:<15} {result['interval']:<10} {result['total_trades']:<10} "
              f"{win_rate_str:<12} {pnl_str:<15} {status:<15}")
    
    print("="*120)
    
    # Recommendation
    profitable = [r for r in best_results.values() if r['total_pnl'] > 0]
    if profitable:
        print(f"\n[SUCCESS] Found {len(profitable)} profitable configurations!")
        print("Recommendation: Use these timeframes for better performance")
        for r in profitable:
            print(f"  - {r['strategy']} on {r['symbol']} with {r['interval']}: Rs {r['total_pnl']:,.2f} profit")
    else:
        print("\n[WARNING] No profitable configurations found with different timeframes")
        print("Recommendation: Consider ignoring MACD and Multi-Indicator strategies")


if __name__ == '__main__':
    main()

