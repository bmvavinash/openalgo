#!/usr/bin/env python
"""Monitor strategies and start them if needed"""
import requests
import time
import json
from pathlib import Path
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"
CONFIG_FILE = Path("strategies/strategy_configs.json")

def check_server():
    """Check if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/python/status", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_all_strategies():
    """Start all strategies via API"""
    try:
        # Use the open endpoint that bypasses session
        response = requests.post(f"{BASE_URL}/python/start-all-open", timeout=30)
        if response.status_code == 200:
            print(f"[{datetime.now()}] Successfully triggered start-all")
            return True
        else:
            print(f"[{datetime.now()}] Failed to start strategies: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[{datetime.now()}] Error starting strategies: {e}")
        return False

def check_strategy_logs():
    """Check recent strategy logs for errors"""
    log_dir = Path("log/strategies")
    if not log_dir.exists():
        return []
    
    errors = []
    today = datetime.now().strftime("%Y%m%d")
    
    for log_file in log_dir.glob(f"*{today}*.log"):
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Check last 20 lines for errors
                for line in lines[-20:]:
                    if any(keyword in line.upper() for keyword in ['ERROR', 'INVALID OPENALGO', 'FAILED', 'TRACEBACK']):
                        errors.append(f"{log_file.name}: {line.strip()}")
        except:
            pass
    
    return errors

def main():
    print(f"[{datetime.now()}] Starting strategy monitor...")
    
    # Wait for server to be ready
    max_wait = 60
    waited = 0
    while not check_server() and waited < max_wait:
        time.sleep(2)
        waited += 2
        print(f"[{datetime.now()}] Waiting for server... ({waited}s)")
    
    if not check_server():
        print(f"[{datetime.now()}] Server not responding after {max_wait}s")
        return
    
    print(f"[{datetime.now()}] Server is running")
    
    # Start all strategies
    print(f"[{datetime.now()}] Triggering start-all strategies...")
    start_all_strategies()
    
    # Wait a bit
    time.sleep(10)
    
    # Check for errors
    print(f"[{datetime.now()}] Checking for errors in logs...")
    errors = check_strategy_logs()
    if errors:
        print(f"[{datetime.now()}] Found {len(errors)} potential errors:")
        for error in errors[:10]:  # Show first 10
            print(f"  - {error}")
    else:
        print(f"[{datetime.now()}] No errors found in recent logs")

if __name__ == "__main__":
    main()


