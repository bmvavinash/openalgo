#!/usr/bin/env python
"""
Start all strategies using Flask app context
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from blueprints.python_strategy import STRATEGY_CONFIGS, start_strategy_process
import time

def start_all_strategies_with_context():
    """Start all strategies using Flask app context"""
    with app.app_context():
        print("="*70)
        print("STARTING ALL STRATEGIES (with Flask app context)")
        print("="*70)
        
        total = len(STRATEGY_CONFIGS)
        print(f"\nTotal strategies registered: {total}")
        
        started = 0
        failed = 0
        skipped = 0
        
        for strategy_id, config in STRATEGY_CONFIGS.items():
            # Skip if already running
            if config.get('is_running', False):
                skipped += 1
                print(f"  [SKIP] {config.get('name', strategy_id)} - already running")
                continue
            
            try:
                success, message = start_strategy_process(strategy_id)
                if success:
                    print(f"  [OK] {config.get('name', strategy_id)}: {message}")
                    started += 1
                else:
                    print(f"  [FAIL] {config.get('name', strategy_id)}: {message}")
                    failed += 1
                time.sleep(0.5)  # Small delay between starts
            except Exception as e:
                print(f"  [ERROR] {strategy_id}: {e}")
                failed += 1
        
        print(f"\n{'='*70}")
        print(f"SUMMARY: Started {started}, Failed {failed}, Skipped {skipped}, Total {total}")
        print(f"{'='*70}")

if __name__ == "__main__":
    start_all_strategies_with_context()


