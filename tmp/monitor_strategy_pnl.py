#!/usr/bin/env python3
"""
Monitor strategy P&L, orders, and API key status at regular intervals
"""
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
import pytz
import re

IST = pytz.timezone('Asia/Kolkata')

def get_ist_time():
    return datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')

def check_api_key_in_logs():
    """Check if API key is found in strategy logs"""
    log_dir = Path('log') / 'strategies'
    if not log_dir.exists():
        return None, "No log directory found"
    
    # Find most recent log files
    log_files = sorted(log_dir.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
    
    api_key_found = False
    api_key_missing = False
    order_errors = []
    order_success = []
    pnl_info = []
    
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[-50:]  # Last 50 lines
                
            for line in lines:
                # Check API key status
                if 'API key found' in line or 'OPENALGO_API_KEY' in line:
                    api_key_found = True
                if 'No API key found' in line or 'PAPER TRADE' in line:
                    api_key_missing = True
                
                # Check order placement
                if 'Order placed successfully' in line or '✅ Order placed' in line:
                    order_success.append(line.strip())
                if 'Order placement failed' in line or '❌ Order' in line or 'Invalid openalgo apikey' in line:
                    order_errors.append(line.strip())
                
                # Check P&L information
                if 'Position Status' in line or 'P&L:' in line or 'PROFIT' in line or 'LOSS' in line:
                    pnl_info.append(line.strip())
                    
        except Exception as e:
            continue
    
    return {
        'api_key_found': api_key_found,
        'api_key_missing': api_key_missing,
        'order_success': order_success[-5:],  # Last 5 successes
        'order_errors': order_errors[-5:],  # Last 5 errors
        'pnl_info': pnl_info[-10:]  # Last 10 P&L entries
    }

def check_strategy_status():
    """Check strategy status"""
    try:
        result = subprocess.run(
            [sys.executable, 'monitor_strategies.py', '--once'],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout
    except Exception as e:
        return f"Error checking strategies: {e}"

def monitor_loop(interval=120):
    """Monitor everything at regular intervals"""
    print("="*80)
    print("Strategy P&L and Order Monitoring")
    print(f"Checking every {interval} seconds")
    print("Press Ctrl+C to stop")
    print("="*80)
    print()
    
    iteration = 0
    try:
        while True:
            iteration += 1
            current_time = get_ist_time()
            
            print(f"\n{'='*80}")
            print(f"Monitor Check #{iteration} - {current_time}")
            print(f"{'='*80}\n")
            
            # Check API key and orders
            print("1. API Key & Order Status:")
            log_info = check_api_key_in_logs()
            if log_info:
                if log_info['api_key_found']:
                    print("   ✅ API key found in strategies")
                elif log_info['api_key_missing']:
                    print("   ⚠️  API key missing - strategies running in paper trade mode")
                else:
                    print("   ⚠️  API key status unknown")
                
                if log_info['order_success']:
                    print(f"\n   ✅ Recent Successful Orders ({len(log_info['order_success'])}):")
                    for order in log_info['order_success'][-3:]:
                        print(f"      {order}")
                
                if log_info['order_errors']:
                    print(f"\n   ❌ Recent Order Errors ({len(log_info['order_errors'])}):")
                    for error in log_info['order_errors'][-3:]:
                        print(f"      {error}")
                else:
                    print("   ✅ No recent order errors")
            print()
            
            # Check P&L information
            print("2. Position & P&L Status:")
            if log_info and log_info['pnl_info']:
                print("   Recent P&L Updates:")
                for pnl in log_info['pnl_info'][-5:]:
                    # Extract key information
                    if 'Position Status' in pnl:
                        print(f"      {pnl}")
                    elif 'P&L:' in pnl or 'PROFIT' in pnl or 'LOSS' in pnl:
                        print(f"      {pnl}")
            else:
                print("   No open positions or P&L data found")
            print()
            
            # Check strategy status
            print("3. Strategy Status:")
            strategy_output = check_strategy_status()
            # Extract just the summary
            lines = strategy_output.split('\n')
            for line in lines:
                if 'Summary:' in line or '[RUNNING]' in line or '[STOPPED]' in line:
                    print(f"   {line}")
            print()
            
            print(f"{'='*80}")
            print(f"Next check in {interval} seconds...")
            print(f"{'='*80}\n")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        print("="*80)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor strategy P&L and orders')
    parser.add_argument('--interval', type=int, default=120, 
                       help='Check interval in seconds (default: 120)')
    
    args = parser.parse_args()
    
    monitor_loop(args.interval)

