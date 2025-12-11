#!/usr/bin/env python
"""
Continuous Strategy Monitor
Monitors strategies at regular intervals and logs status
"""

import os
import sys
import time
import json
import psutil
from pathlib import Path
from datetime import datetime
import pytz

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

IST = pytz.timezone('Asia/Kolkata')

def check_process_running(pid):
    """Check if a process is running"""
    try:
        process = psutil.Process(pid)
        return process.is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def load_strategy_configs():
    """Load strategy configurations"""
    config_file = Path('strategies') / 'strategy_configs.json'
    if not config_file.exists():
        return {}
    
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {}

def get_strategy_logs(strategy_id, config, lines=10):
    """Get recent log lines for a strategy"""
    try:
        log_dir = Path('log') / 'strategies'
        if not log_dir.exists():
            return []
        
        # Find the most recent log file for this strategy
        log_files = sorted(log_dir.glob(f"{strategy_id}_*.log"), reverse=True)
        if not log_files:
            strategy_name = config.get('name', '').lower().replace(' ', '_')
            log_files = sorted(log_dir.glob(f"*{strategy_name}*.log"), reverse=True)
        
        if log_files:
            with open(log_files[0], 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
        return []
    except Exception as e:
        return []

def check_strategy_status():
    """Check status of all strategies"""
    configs = load_strategy_configs()
    current_time = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')
    
    print(f"\n{'='*80}")
    print(f"Strategy Status Check - {current_time}")
    print(f"{'='*80}\n")
    
    running_count = 0
    stopped_count = 0
    
    for strategy_id, config in configs.items():
        name = config.get('name', 'Unknown')
        pid = config.get('pid')
        is_running = config.get('is_running', False)
        
        # Check if process is actually running
        actually_running = False
        if pid:
            actually_running = check_process_running(pid)
        
        status = "[RUNNING]" if (is_running and actually_running) else "[STOPPED]"
        if is_running and not actually_running:
            status = "[WARNING] MARKED RUNNING BUT PROCESS DEAD"
            stopped_count += 1
        elif is_running and actually_running:
            running_count += 1
        else:
            stopped_count += 1
        
        print(f"{status} - {name}")
        print(f"  ID: {strategy_id}")
        if pid:
            print(f"  PID: {pid} {'(Running)' if actually_running else '(Not Found)'}")
        else:
            print(f"  PID: None")
        
        # Show recent log lines if running
        if actually_running:
            logs = get_strategy_logs(strategy_id, config, lines=3)
            if logs:
                print(f"  Recent Logs:")
                for line in logs[-3:]:
                    line = line.strip()
                    if line:
                        if len(line) > 100:
                            line = line[:97] + "..."
                        print(f"    {line}")
        
        print()
    
    print(f"{'='*80}")
    print(f"Summary: {running_count} Running, {stopped_count} Stopped")
    print(f"{'='*80}\n")

def monitor_loop(interval=60):
    """Monitor strategies at regular intervals"""
    print("Starting Continuous Strategy Monitor")
    print(f"Checking every {interval} seconds")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            check_strategy_status()
            print(f"Next check in {interval} seconds...\n")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\nMonitor stopped by user")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor strategy status and logs')
    parser.add_argument('--interval', type=int, default=60, 
                       help='Check interval in seconds (default: 60)')
    parser.add_argument('--once', action='store_true',
                       help='Check once and exit')
    
    args = parser.parse_args()
    
    if args.once:
        check_strategy_status()
    else:
        monitor_loop(args.interval)


