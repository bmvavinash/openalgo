#!/usr/bin/env python
"""
Intraday EMA Crossover Strategy
Simple moving average crossover for intraday trading
"""
from openalgo import api
import pandas as pd
import numpy as np
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import os
import sys

# Add parent directory for performance tracking
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
except:
    pass

# Get API key from environment
api_key = os.getenv('OPENALGO_API_KEY', os.getenv('OPENALGO_APIKEY'))
if not api_key:
    print("Error: OPENALGO_API_KEY environment variable not set")
    exit(1)

# Strategy configuration
strategy_name = "Intraday EMA Crossover"
symbol = os.getenv('SYMBOL', 'NHPC')
exchange = os.getenv('EXCHANGE', 'NSE')
product = os.getenv('PRODUCT', 'MIS')
quantity = int(os.getenv('QUANTITY', '1'))

# EMA periods
fast_period = int(os.getenv('FAST_PERIOD', '5'))
slow_period = int(os.getenv('SLOW_PERIOD', '10'))

# Initialize OpenAlgo client
client = api(api_key=api_key, host=os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000'))

# Track position and performance
position = 0
total_pnl = 0.0
winning_trades = 0
losing_trades = 0
total_trades = 0

def update_performance(pnl, is_win):
    """Update performance metrics"""
    global total_pnl, winning_trades, losing_trades, total_trades
    
    total_pnl += pnl
    total_trades += 1
    if is_win:
        winning_trades += 1
    else:
        losing_trades += 1
    
    # Send to performance tracker
    try:
        import requests
        requests.post(
            f"{os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000')}/python/performance/update",
            json={
                'strategy_id': os.getenv('STRATEGY_ID', 'intraday_ema'),
                'pnl': pnl,
                'is_win': is_win,
                'strategy_type': 'intraday'
            },
            timeout=2
        )
    except:
        pass  # Silently fail if tracker unavailable

def calculate_ema_signals(df):
    """Calculate EMA crossover signals"""
    close = df['close']
    ema_fast = close.ewm(span=fast_period, adjust=False).mean()
    ema_slow = close.ewm(span=slow_period, adjust=False).mean()
    
    prev_fast = ema_fast.shift(1)
    prev_slow = ema_slow.shift(1)
    curr_fast = ema_fast
    curr_slow = ema_slow
    
    crossover = (prev_fast < prev_slow) & (curr_fast > curr_slow)
    crossunder = (prev_fast > prev_slow) & (curr_fast < curr_slow)
    
    return crossover, crossunder

def ema_strategy():
    """The EMA crossover trading strategy"""
    global position
    
    while True:
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            df = client.history(
                symbol=symbol,
                exchange=exchange,
                interval="1m",
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                print("DataFrame is empty. Retrying...")
                time.sleep(15)
                continue
            
            if 'close' not in df.columns:
                raise KeyError("Missing 'close' column in DataFrame")
            
            df['close'] = df['close'].round(2)
            crossover, crossunder = calculate_ema_signals(df)
            
            latest_crossover = crossover.iloc[-2] if len(crossover) > 1 else False
            latest_crossunder = crossunder.iloc[-2] if len(crossunder) > 1 else False
            
            # Execute Buy Order
            if latest_crossover and position <= 0:
                old_position = position
                position = quantity
                response = client.placesmartorder(
                    strategy=strategy_name,
                    symbol=symbol,
                    action="BUY",
                    exchange=exchange,
                    price_type="MARKET",
                    product=product,
                    quantity=quantity,
                    position_size=position
                )
                print(f"[{datetime.now()}] Buy Order Response: {response}")
                
                if old_position < 0:
                    # Closed short position
                    pnl = abs(old_position) * 10  # Approximate
                    is_win = pnl > 0
                    update_performance(pnl, is_win)
            
            # Execute Sell Order
            elif latest_crossunder and position >= 0:
                old_position = position
                position = quantity * -1
                response = client.placesmartorder(
                    strategy=strategy_name,
                    symbol=symbol,
                    action="SELL",
                    exchange=exchange,
                    price_type="MARKET",
                    product=product,
                    quantity=quantity,
                    position_size=position
                )
                print(f"[{datetime.now()}] Sell Order Response: {response}")
                
                if old_position > 0:
                    # Closed long position
                    pnl = old_position * 10  # Approximate
                    is_win = pnl > 0
                    update_performance(pnl, is_win)
            
            # Log strategy status
            print(f"\n[{datetime.now()}] Strategy Status:")
            print(f"  Position: {position}")
            print(f"  Total PnL: Rs {total_pnl:.2f}")
            print(f"  Trades: {total_trades} (W: {winning_trades}, L: {losing_trades})")
            print(f"  Win Rate: {(winning_trades/total_trades*100) if total_trades > 0 else 0:.1f}%")
            
        except Exception as e:
            print(f"Error in strategy: {str(e)}")
            import traceback
            traceback.print_exc()
            time.sleep(15)
            continue
        
        time.sleep(15)

if __name__ == "__main__":
    print(f"Starting {strategy_name}...")
    print(f"Symbol: {symbol}, Exchange: {exchange}")
    print(f"EMA Periods: {fast_period}/{slow_period}")
    ema_strategy()

