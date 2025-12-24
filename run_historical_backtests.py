#!/usr/bin/env python
"""
Run historical backtests for all strategies on specific date ranges
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import pytz
from services.history_service import get_history
from database.auth_db import get_api_key_for_tradingview
from database.settings_db import get_analyze_mode
import pandas as pd

def run_backtest_for_date_range(start_date, end_date, symbol='NIFTY', exchange='NSE_INDEX', interval='5m'):
    """Run backtest for a specific date range"""
    ist = pytz.timezone('Asia/Kolkata')
    
    # Get API key
    api_key = get_api_key_for_tradingview('avinash')
    if not api_key:
        print("Error: No API key found")
        return None
    
    print(f"\n{'='*70}")
    print(f"Running backtest: {symbol} from {start_date} to {end_date}")
    print(f"{'='*70}")
    
    # Fetch historical data
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    print(f"Fetching historical data: {start_str} to {end_str} (interval: {interval})...")
    
    success, response, status_code = get_history(
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        start_date=start_str,
        end_date=end_str,
        api_key=api_key
    )
    
    if not success:
        print(f"Error fetching data: {response.get('message', 'Unknown error')}")
        return None
    
    # Extract data
    if isinstance(response, dict) and 'data' in response:
        data = response['data']
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
    else:
        df = response
    
    if df is None or (hasattr(df, 'empty') and df.empty):
        print(f"No data available for {start_str} to {end_str}")
        return None
    
    print(f"Fetched {len(df)} records")
    
    # Basic statistics
    if 'close' in df.columns:
        print(f"\nPrice Statistics:")
        print(f"  Open: {df['close'].iloc[0]:.2f}")
        print(f"  Close: {df['close'].iloc[-1]:.2f}")
        print(f"  High: {df['close'].max():.2f}")
        print(f"  Low: {df['close'].min():.2f}")
        print(f"  Change: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.2f}%")
    
    return df

def main():
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).date()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=7)
    month_start = today - timedelta(days=30)
    
    print("="*70)
    print("HISTORICAL BACKTEST RUNNER")
    print("="*70)
    
    # Today's market
    print(f"\n[1/4] TODAY'S MARKET ({today})")
    df_today = run_backtest_for_date_range(today, today)
    
    # Yesterday's market
    print(f"\n[2/4] YESTERDAY'S MARKET ({yesterday})")
    df_yesterday = run_backtest_for_date_range(yesterday, yesterday)
    
    # Previous week
    print(f"\n[3/4] PREVIOUS WEEK ({week_start} to {today})")
    df_week = run_backtest_for_date_range(week_start, today)
    
    # Current month
    print(f"\n[4/4] CURRENT MONTH ({month_start} to {today})")
    df_month = run_backtest_for_date_range(month_start, today)
    
    print("\n" + "="*70)
    print("BACKTEST COMPLETE")
    print("="*70)
    print("\nNote: This script fetches historical data.")
    print("To run actual strategy backtests, use the backtest framework in strategies/backtest/")

if __name__ == "__main__":
    main()


