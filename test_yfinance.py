#!/usr/bin/env python3
"""Test yfinance data fetching"""

import yfinance as yf
import pandas as pd
from datetime import datetime, date

print("="*60)
print("TESTING YFINANCE DATA FETCH")
print("="*60)

symbols = ['^NSEI', '^NSEBANK', 'NIFTY', 'BANKNIFTY']

for symbol in symbols:
    print(f"\n[TESTING] {symbol}")
    print("-" * 60)
    
    try:
        ticker = yf.Ticker(symbol)
        
        # Method 1: Try info()
        try:
            info = ticker.info
            current_price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')
            print(f"  [INFO] Current Price: {current_price}")
            print(f"  [INFO] Regular Market Price: {info.get('regularMarketPrice')}")
            print(f"  [INFO] Previous Close: {info.get('previousClose')}")
        except Exception as e:
            print(f"  [ERROR] info() failed: {e}")
            current_price = None
        
        # Method 2: Try history with different periods
        for period in ['1d', '5d', '1mo']:
            try:
                hist = ticker.history(period=period, interval='5m')
                if not hist.empty:
                    print(f"  [OK] history(period='{period}', interval='5m'): {len(hist)} rows")
                    print(f"       Latest Close: {hist['Close'].iloc[-1]}")
                    print(f"       Latest Time: {hist.index[-1]}")
                    break
                else:
                    print(f"  [WARNING] history(period='{period}', interval='5m'): Empty")
            except Exception as e:
                print(f"  [ERROR] history(period='{period}') failed: {e}")
        
        # Method 3: Try daily data
        try:
            hist_daily = ticker.history(period='5d', interval='1d')
            if not hist_daily.empty:
                print(f"  [OK] Daily data: {len(hist_daily)} rows")
                print(f"       Latest Close: {hist_daily['Close'].iloc[-1]}")
        except Exception as e:
            print(f"  [ERROR] Daily data failed: {e}")
            
    except Exception as e:
        print(f"  [ERROR] Ticker creation failed: {e}")

print("\n" + "="*60)






