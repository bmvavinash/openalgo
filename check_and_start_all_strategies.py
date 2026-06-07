#!/usr/bin/env python3
"""
Check and start all strategies that are not running
"""
import sys
import os
import requests
import json
import time

# Force unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

HOST = os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000')

def check_strategies():
    """Check which strategies are running"""
    try:
        # Get session first (assuming we're logged in)
        session = requests.Session()
        
        # Get strategies list
        r = session.get(f'{HOST}/python/strategies', timeout=10)
        if r.status_code != 200:
            print(f"Error: Failed to get strategies list: {r.status_code}")
            return None
        
        data = r.json()
        strategies = data.get('strategies', [])
        running = [s for s in strategies if s.get('is_running')]
        not_running = [s for s in strategies if not s.get('is_running')]
        
        return {
            'total': len(strategies),
            'running': len(running),
            'not_running': len(not_running),
            'running_list': running,
            'not_running_list': not_running,
            'strategies': strategies
        }
    except Exception as e:
        print(f"Error checking strategies: {e}")
        return None

def start_all_strategies():
    """Start all strategies"""
    try:
        session = requests.Session()
        r = session.post(f'{HOST}/python/start-all', timeout=60)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"Error starting strategies: {r.status_code} - {r.text}")
            return None
    except Exception as e:
        print(f"Error starting strategies: {e}")
        return None

def check_strategy_logs(strategy_id, strategy_name):
    """Check strategy log for errors"""
    try:
        log_dir = os.path.join('log', 'strategies')
        if not os.path.exists(log_dir):
            return None
        
        # Find latest log file for this strategy
        import glob
        pattern = os.path.join(log_dir, f'{strategy_id}_*.log')
        log_files = glob.glob(pattern)
        if not log_files:
            return None
        
        # Get most recent log file
        latest_log = max(log_files, key=os.path.getmtime)
        
        # Read last 20 lines
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            last_lines = lines[-20:] if len(lines) > 20 else lines
        
        return {
            'log_file': latest_log,
            'last_lines': last_lines,
            'has_errors': any('ERROR' in line or 'Error' in line or 'error' in line for line in last_lines)
        }
    except Exception as e:
        return None

def main():
    print("="*70)
    print("CHECKING AND STARTING ALL STRATEGIES")
    print("="*70)
    print()
    
    # Check current status
    print("Step 1: Checking current strategy status...")
    status = check_strategies()
    if not status:
        print("Failed to check strategies. Exiting.")
        return
    
    print(f"Total strategies: {status['total']}")
    print(f"Running: {status['running']}")
    print(f"Not running: {status['not_running']}")
    print()
    
    if status['running'] > 0:
        print("Currently running strategies:")
        for s in status['running_list']:
            print(f"  ✓ {s.get('name', s.get('id'))} ({s.get('id')})")
        print()
    
    if status['not_running'] > 0:
        print("Not running strategies:")
        for s in status['not_running_list']:
            print(f"  ✗ {s.get('name', s.get('id'))} ({s.get('id')})")
        print()
        
        # Check logs for not running strategies
        print("Step 2: Checking logs for not-running strategies...")
        for s in status['not_running_list']:
            log_info = check_strategy_logs(s.get('id'), s.get('name'))
            if log_info:
                if log_info['has_errors']:
                    print(f"  ⚠ {s.get('name')}: Has errors in log")
                    print(f"    Log: {log_info['log_file']}")
                    print(f"    Last lines:")
                    for line in log_info['last_lines'][-5:]:
                        print(f"      {line.rstrip()}")
                else:
                    print(f"  ℹ {s.get('name')}: Log exists, no recent errors")
        print()
        
        # Start all strategies
        print("Step 3: Starting all strategies...")
        result = start_all_strategies()
        if result:
            print(f"Result: {result.get('message', 'Unknown')}")
            if result.get('details'):
                print("\nDetails:")
                for detail in result.get('details', []):
                    print(f"  {detail}")
        else:
            print("Failed to start strategies")
        print()
        
        # Wait and check again
        print("Step 4: Waiting 5 seconds and rechecking...")
        time.sleep(5)
        status2 = check_strategies()
        if status2:
            print(f"After start: Running: {status2['running']}, Not running: {status2['not_running']}")
            if status2['not_running'] > 0:
                print("\nStill not running:")
                for s in status2['not_running_list']:
                    print(f"  ✗ {s.get('name', s.get('id'))} ({s.get('id')})")
                    # Check log again
                    log_info = check_strategy_logs(s.get('id'), s.get('name'))
                    if log_info:
                        print(f"    Latest log entries:")
                        for line in log_info['last_lines'][-3:]:
                            print(f"      {line.rstrip()}")
    else:
        print("All strategies are running!")
    
    print()
    print("="*70)
    print("COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()

