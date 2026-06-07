#!/usr/bin/env python3
"""
Restart All Strategies Script
Stops and starts all strategies to pick up new code changes
"""

# Force unbuffered output for immediate visibility
import sys
import os

# Set Python to unbuffered mode
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

# Print immediately to show script started
print("="*60, flush=True)
print("RESTART STRATEGIES SCRIPT - STARTING", flush=True)
print("="*60, flush=True)
print(f"[INIT] Python version: {sys.version}", flush=True)
print(f"[INIT] Working directory: {os.getcwd()}", flush=True)
sys.stdout.flush()

import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("[INIT] Importing modules...", flush=True)
sys.stdout.flush()

try:
    from blueprints.python_strategy import (
        start_strategy_process, stop_strategy_process,
        STRATEGY_CONFIGS, RUNNING_STRATEGIES, load_configs
    )
    print("[INIT] Strategy module imported successfully", flush=True)
    sys.stdout.flush()
except Exception as e:
    print(f"[ERROR] Failed to import strategy module: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from utils.logging import get_logger
    logger = get_logger(__name__)
    print("[INIT] Logger initialized", flush=True)
    sys.stdout.flush()
except Exception as e:
    print(f"[WARNING] Logger initialization failed: {e}", flush=True)
    import logging
    logger = logging.getLogger(__name__)

def restart_all_strategies():
    """Restart all strategies"""
    start_time = time.time()
    print("\n" + "="*60, flush=True)
    print("RESTARTING ALL STRATEGIES", flush=True)
    print("="*60, flush=True)
    print(f"[INFO] Starting at {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    sys.stdout.flush()
    
    try:
        # Load configs
        print("\n[LOADING] Loading strategy configurations...", flush=True)
        sys.stdout.flush()
        
        try:
            load_configs()
            print("[LOADING] Configs loaded successfully", flush=True)
            sys.stdout.flush()
        except Exception as e:
            print(f"[ERROR] Failed to load configs: {e}", flush=True)
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            raise
        
        total_strategies = len(STRATEGY_CONFIGS)
        print(f"[INFO] Found {total_strategies} strategy configuration(s)", flush=True)
        sys.stdout.flush()
        
        # Step 1: Stop all running strategies
        print("\n[STEP 1] Stopping all running strategies...", flush=True)
        sys.stdout.flush()
        stopped_count = 0
        running_strategies = []
        
        print("[STEP 1] Scanning for running strategies...", flush=True)
        sys.stdout.flush()
        
        # First, identify all running strategies
        for strategy_id, config in STRATEGY_CONFIGS.items():
            is_running = config.get('is_running', False) or strategy_id in RUNNING_STRATEGIES
            if is_running:
                running_strategies.append((strategy_id, config))
        
        print(f"[INFO] Found {len(running_strategies)} running strategy(ies) to stop", flush=True)
        sys.stdout.flush()
        
        if running_strategies:
            for idx, (strategy_id, config) in enumerate(running_strategies, 1):
                strategy_name = config.get('name', strategy_id)
                print(f"   [{idx}/{len(running_strategies)}] Stopping: {strategy_name}...", end='', flush=True)
                sys.stdout.flush()
                try:
                    print(" [processing...]", end='', flush=True)
                    sys.stdout.flush()
                    success, message = stop_strategy_process(strategy_id)
                    if success:
                        print(f" [OK]", flush=True)
                        stopped_count += 1
                    else:
                        print(f" [WARNING: {message}]", flush=True)
                    # Reduced delay - processes should stop quickly
                    if idx < len(running_strategies):
                        time.sleep(0.1)  # Minimal delay between stops
                except Exception as e:
                    print(f" [ERROR: {e}]", flush=True)
                    import traceback
                    traceback.print_exc()
                sys.stdout.flush()
        else:
            print("   [INFO] No running strategies found")
            sys.stdout.flush()
        
        print(f"\n[STATUS] Stopped {stopped_count} strategy(ies)")
        sys.stdout.flush()
        
        # Step 2: Brief wait for processes to fully stop (reduced from 3s to 1s)
        if stopped_count > 0:
            print("\n[STEP 2] Waiting for processes to fully terminate...")
            sys.stdout.flush()
            for i in range(5):  # 5 x 0.2s = 1s total, with progress updates
                time.sleep(0.2)
                if i < 4:  # Don't print on last iteration
                    print(".", end='', flush=True)
            print(" [DONE]")
            sys.stdout.flush()
        else:
            print("\n[STEP 2] Skipping wait (no strategies were stopped)")
            sys.stdout.flush()
        
        # Step 3: Start all strategies
        print("\n[STEP 3] Starting all strategies...")
        sys.stdout.flush()
        started_count = 0
        failed_count = 0
        
        strategies_to_start = list(STRATEGY_CONFIGS.items())
        print(f"[INFO] Starting {len(strategies_to_start)} strategy(ies)")
        sys.stdout.flush()
        
        for idx, (strategy_id, config) in enumerate(strategies_to_start, 1):
            strategy_name = config.get('name', strategy_id)
            print(f"   [{idx}/{len(strategies_to_start)}] Starting: {strategy_name}...", end='', flush=True)
            sys.stdout.flush()
            try:
                print(" [processing...]", end='', flush=True)
                sys.stdout.flush()
                success, message = start_strategy_process(strategy_id)
                if success:
                    print(f" [OK]", flush=True)
                    started_count += 1
                else:
                    print(f" [FAILED: {message}]", flush=True)
                    failed_count += 1
                # Reduced delay between starts
                if idx < len(strategies_to_start):
                    time.sleep(0.2)  # Minimal delay between starts
            except Exception as e:
                print(f" [ERROR: {e}]", flush=True)
                import traceback
                traceback.print_exc()
                failed_count += 1
            sys.stdout.flush()
        
        elapsed_time = time.time() - start_time
        print(f"\n[SUMMARY] Started: {started_count}, Failed: {failed_count}")
        print(f"[INFO] Total time: {elapsed_time:.2f} seconds")
        sys.stdout.flush()
        
        if started_count > 0:
            print("[OK] Strategies restarted successfully!")
            sys.stdout.flush()
            return True
        else:
            print("[WARNING] No strategies were started")
            sys.stdout.flush()
            return False
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n[ERROR] Failed to restart strategies after {elapsed_time:.2f} seconds: {e}")
        sys.stdout.flush()
        raise

if __name__ == '__main__':
    print("[MAIN] Entering main execution block", flush=True)
    sys.stdout.flush()
    
    try:
        print("[MAIN] Calling restart_all_strategies()...", flush=True)
        sys.stdout.flush()
        result = restart_all_strategies()
        print("\n[COMPLETE] Restart script finished", flush=True)
        print(f"[COMPLETE] Exit code: {0 if result else 1}", flush=True)
        sys.stdout.flush()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Restart cancelled by user", flush=True)
        sys.stdout.flush()
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Failed to restart strategies: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        sys.exit(1)

