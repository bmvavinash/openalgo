#!/usr/bin/env python3
"""
Continuous monitoring script - checks server, settings, and strategies at regular intervals
"""
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def get_ist_time():
    return datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')

def check_server_status():
    """Check if server is responding"""
    try:
        import requests
        response = requests.get('http://127.0.0.1:5000/', timeout=5)
        return response.status_code == 200 or response.status_code == 302
    except:
        return False

def check_settings():
    """Check current settings"""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from database.settings_db import get_analyze_mode, get_use_historical_data
        from flask import Flask
        from app import create_app
        
        app = create_app()
        with app.app_context():
            analyze_mode = get_analyze_mode()
            data_mode = get_use_historical_data()
            return analyze_mode, data_mode
    except Exception as e:
        print(f"  ❌ Error checking settings: {e}")
        return None, None

def check_strategies():
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

def monitor_loop(interval=60):
    """Monitor everything at regular intervals"""
    print("="*80)
    print("Continuous Monitoring Started")
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
            
            # Check server
            print("1. Server Status:")
            server_ok = check_server_status()
            if server_ok:
                print("   ✅ Server is running and responding")
            else:
                print("   ❌ Server is NOT responding")
            print()
            
            # Check settings
            print("2. Settings:")
            analyze_mode, data_mode = check_settings()
            if analyze_mode is not None:
                print(f"   Analyze Mode (Paper Trading): {'ON ✅' if analyze_mode else 'OFF ❌'}")
                print(f"   Data Mode: {'Historical ❌' if data_mode else 'Live ✅'}")
                
                if not analyze_mode:
                    print("   ⚠️  WARNING: Analyze mode should be ON for paper trading!")
                if data_mode:
                    print("   ⚠️  WARNING: Data mode should be Live (not Historical)!")
            else:
                print("   ❌ Could not check settings")
            print()
            
            # Check strategies
            print("3. Strategy Status:")
            strategy_output = check_strategies()
            print(strategy_output)
            
            print(f"\n{'='*80}")
            print(f"Next check in {interval} seconds...")
            print(f"{'='*80}\n")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        print("="*80)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Continuous monitoring of server, settings, and strategies')
    parser.add_argument('--interval', type=int, default=60, 
                       help='Check interval in seconds (default: 60)')
    
    args = parser.parse_args()
    
    monitor_loop(args.interval)

