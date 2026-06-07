#!/usr/bin/env python3
"""
Start all strategies and check their logs
"""
import sys
import os
import time
from pathlib import Path

# Force unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from blueprints.python_strategy import (
    STRATEGY_CONFIGS, RUNNING_STRATEGIES, load_configs, 
    start_strategy_process, LOGS_DIR
)

def check_strategy_log(strategy_id, max_lines=20):
    """Check strategy log file"""
    try:
        # Find latest log file
        log_pattern = f"{strategy_id}_*_IST.log"
        log_files = list(LOGS_DIR.glob(log_pattern))
        if not log_files:
            return None
        
        latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            return {
                'file': str(latest_log),
                'lines': lines[-max_lines:] if len(lines) > max_lines else lines,
                'has_errors': any('ERROR' in line.upper() or 'Error' in line or 'Traceback' in line for line in lines[-max_lines:])
            }
    except Exception as e:
        return None

def main():
    print("="*70)
    print("STARTING ALL STRATEGIES AND CHECKING LOGS")
    print("="*70)
    print()
    
    # Load configs
    load_configs()
    print(f"Loaded {len(STRATEGY_CONFIGS)} strategy configurations")
    print()
    
    # Check current status
    all_strategies = list(STRATEGY_CONFIGS.keys())
    running_strategies = list(RUNNING_STRATEGIES.keys())
    not_running = [s for s in all_strategies if s not in running_strategies]
    
    print(f"Total strategies: {len(all_strategies)}")
    print(f"Currently running: {len(running_strategies)}")
    print(f"Not running: {len(not_running)}")
    print()
    
    if running_strategies:
        print("Already running:")
        for sid in running_strategies:
            config = STRATEGY_CONFIGS.get(sid, {})
            print(f"  ✓ {config.get('name', sid)} ({sid})")
        print()
    
    if not_running:
        print("Starting not-running strategies:")
        print("-" * 70)
        
        started = []
        failed = []
        
        for sid in not_running:
            config = STRATEGY_CONFIGS.get(sid, {})
            name = config.get('name', sid)
            print(f"\n[{len(started) + len(failed) + 1}/{len(not_running)}] Starting: {name} ({sid})")
            
            success, message = start_strategy_process(sid)
            if success:
                print(f"  ✓ Started: {message}")
                started.append((sid, name))
            else:
                print(f"  ✗ Failed: {message}")
                failed.append((sid, name, message))
            
            time.sleep(0.5)  # Small delay between starts
        
        print()
        print("="*70)
        print("STARTUP SUMMARY")
        print("="*70)
        print(f"Successfully started: {len(started)}")
        print(f"Failed to start: {len(failed)}")
        print()
        
        if started:
            print("Successfully started strategies:")
            for sid, name in started:
                print(f"  ✓ {name} ({sid})")
            print()
        
        if failed:
            print("Failed to start strategies:")
            for sid, name, msg in failed:
                print(f"  ✗ {name} ({sid})")
                print(f"    Error: {msg}")
            print()
        
        # Wait a bit for strategies to initialize
        print("Waiting 3 seconds for strategies to initialize...")
        time.sleep(3)
        
        # Check logs for all strategies (including newly started)
        print()
        print("="*70)
        print("CHECKING STRATEGY LOGS")
        print("="*70)
        print()
        
        for sid in all_strategies:
            config = STRATEGY_CONFIGS.get(sid, {})
            name = config.get('name', sid)
            is_running = sid in RUNNING_STRATEGIES
            
            status = "RUNNING" if is_running else "NOT RUNNING"
            print(f"\n{name} ({sid}) - {status}")
            
            log_info = check_strategy_log(sid)
            if log_info:
                print(f"  Log: {Path(log_info['file']).name}")
                if log_info['has_errors']:
                    print("  ⚠ Has errors in recent log entries:")
                    for line in log_info['lines'][-5:]:
                        if 'ERROR' in line.upper() or 'Error' in line or 'Traceback' in line:
                            print(f"    {line.rstrip()}")
                else:
                    print("  ✓ No recent errors")
                    if log_info['lines']:
                        print("  Latest log entry:")
                        print(f"    {log_info['lines'][-1].rstrip()}")
            else:
                print("  ℹ No log file found")
        
        print()
        print("="*70)
        print("FINAL STATUS")
        print("="*70)
        load_configs()  # Reload to get updated status
        final_running = len(RUNNING_STRATEGIES)
        final_not_running = len(all_strategies) - final_running
        print(f"Running: {final_running}/{len(all_strategies)}")
        print(f"Not running: {final_not_running}/{len(all_strategies)}")
        
        if final_not_running > 0:
            print("\nStill not running:")
            for sid in all_strategies:
                if sid not in RUNNING_STRATEGIES:
                    config = STRATEGY_CONFIGS.get(sid, {})
                    print(f"  ✗ {config.get('name', sid)} ({sid})")
    else:
        print("All strategies are already running!")
        print()
        print("Checking logs for all running strategies...")
        for sid in running_strategies:
            config = STRATEGY_CONFIGS.get(sid, {})
            name = config.get('name', sid)
            print(f"\n{name} ({sid})")
            log_info = check_strategy_log(sid)
            if log_info and log_info['has_errors']:
                print("  ⚠ Has errors:")
                for line in log_info['lines'][-3:]:
                    if 'ERROR' in line.upper() or 'Error' in line:
                        print(f"    {line.rstrip()}")
    
    print()
    print("="*70)
    print("COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()
