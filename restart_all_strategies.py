#!/usr/bin/env python
"""
Restart all strategies to apply latest fixes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from blueprints.python_strategy import STRATEGY_CONFIGS, stop_strategy_process, start_strategy_process, RUNNING_STRATEGIES
import time

def restart_all_strategies():
    """Restart all strategies using Flask app context"""
    with app.app_context():
        print("="*70)
        print("RESTARTING ALL STRATEGIES")
        print("="*70)
        
        total = len(STRATEGY_CONFIGS)
        print(f"\nTotal strategies registered: {total}")
        
        # First, stop all running strategies
        stopped = 0
        failed_stop = 0
        
        print("\n" + "-"*70)
        print("STOPPING STRATEGIES")
        print("-"*70)
        
        for strategy_id, config in STRATEGY_CONFIGS.items():
            if config.get('is_running', False) or strategy_id in RUNNING_STRATEGIES:
                print(f"\n[{strategy_id}]")
                success, message = stop_strategy_process(strategy_id)
                if success:
                    stopped += 1
                    print(f"  ✓ Stopped: {message}")
                else:
                    failed_stop += 1
                    print(f"  ✗ Failed to stop: {message}")
                time.sleep(0.5)
        
        # Wait for processes to terminate
        print(f"\nWaiting 2 seconds for processes to terminate...")
        time.sleep(2)
        
        # Then start all strategies
        started = 0
        failed_start = 0
        
        print("\n" + "-"*70)
        print("STARTING STRATEGIES")
        print("-"*70)
        
        for strategy_id, config in STRATEGY_CONFIGS.items():
            # Skip if still running
            if config.get('is_running', False) or strategy_id in RUNNING_STRATEGIES:
                print(f"\n[{strategy_id}]")
                print(f"  ⊘ Skipped (still running)")
                continue
            
            print(f"\n[{strategy_id}]")
            success, message = start_strategy_process(strategy_id)
            if success:
                started += 1
                print(f"  ✓ Started: {message}")
            else:
                failed_start += 1
                print(f"  ✗ Failed to start: {message}")
            time.sleep(0.5)
        
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Total strategies: {total}")
        print(f"Stopped: {stopped} (failed: {failed_stop})")
        print(f"Started: {started} (failed: {failed_start})")
        print("="*70)

if __name__ == "__main__":
    restart_all_strategies()










