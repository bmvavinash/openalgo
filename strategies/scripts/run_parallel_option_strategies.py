#!/usr/bin/env python
"""
Parallel Option Strategy Runner
Runs multiple option strategies in parallel using threading
Each strategy runs in its own thread, allowing true parallel execution
"""
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Add strategies directory to path
strategies_dir = Path(__file__).parent
sys.path.insert(0, str(strategies_dir))

# Import strategy modules
try:
    from option_straddle_strategy import main as straddle_main
    from option_strangle_strategy import main as strangle_main
    from option_iron_condor_strategy import main as iron_condor_main
    from option_iron_butterfly_strategy import main as iron_butterfly_main
    from option_bull_call_spread_strategy import main as bull_call_spread_main
    from option_bear_put_spread_strategy import main as bear_put_spread_main
    from option_protective_put_strategy import main as protective_put_main
    from option_covered_call_strategy import main as covered_call_main
    from option_calendar_spread_strategy import main as calendar_spread_main
except ImportError as e:
    print(f"Error importing strategies: {e}")
    print("Make sure all strategy files are in the same directory")
    sys.exit(1)

# Strategy configuration
STRATEGIES = {
    'straddle': {
        'name': 'Straddle',
        'function': straddle_main,
        'enabled': os.getenv('ENABLE_STRADDLE', 'false').lower() == 'true',
        'thread': None
    },
    'strangle': {
        'name': 'Strangle',
        'function': strangle_main,
        'enabled': os.getenv('ENABLE_STRANGLE', 'false').lower() == 'true',
        'thread': None
    },
    'iron_condor': {
        'name': 'Iron Condor',
        'function': iron_condor_main,
        'enabled': os.getenv('ENABLE_IRON_CONDOR', 'false').lower() == 'true',
        'thread': None
    },
    'iron_butterfly': {
        'name': 'Iron Butterfly',
        'function': iron_butterfly_main,
        'enabled': os.getenv('ENABLE_IRON_BUTTERFLY', 'false').lower() == 'true',
        'thread': None
    },
    'bull_call_spread': {
        'name': 'Bull Call Spread',
        'function': bull_call_spread_main,
        'enabled': os.getenv('ENABLE_BULL_CALL_SPREAD', 'false').lower() == 'true',
        'thread': None
    },
    'bear_put_spread': {
        'name': 'Bear Put Spread',
        'function': bear_put_spread_main,
        'enabled': os.getenv('ENABLE_BEAR_PUT_SPREAD', 'false').lower() == 'true',
        'thread': None
    },
    'protective_put': {
        'name': 'Protective Put',
        'function': protective_put_main,
        'enabled': os.getenv('ENABLE_PROTECTIVE_PUT', 'false').lower() == 'true',
        'thread': None
    },
    'covered_call': {
        'name': 'Covered Call',
        'function': covered_call_main,
        'enabled': os.getenv('ENABLE_COVERED_CALL', 'false').lower() == 'true',
        'thread': None
    },
    'calendar_spread': {
        'name': 'Calendar Spread',
        'function': calendar_spread_main,
        'enabled': os.getenv('ENABLE_CALENDAR_SPREAD', 'false').lower() == 'true',
        'thread': None
    }
}

def run_strategy(strategy_name, strategy_func):
    """Run a strategy in a separate thread"""
    try:
        print(f"[{datetime.now()}] Starting {strategy_name} strategy in thread {threading.current_thread().name}")
        strategy_func()
    except Exception as e:
        print(f"[{datetime.now()}] Error in {strategy_name} strategy: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to run strategies in parallel"""
    print("=" * 70)
    print("PARALLEL OPTION STRATEGY RUNNER")
    print("=" * 70)
    print(f"Start time: {datetime.now()}")
    print()
    
    # Check API key
    api_key = os.getenv('OPENALGO_API_KEY', os.getenv('OPENALGO_APIKEY'))
    if not api_key:
        print("ERROR: OPENALGO_API_KEY environment variable not set")
        print("Please set OPENALGO_API_KEY before running strategies")
        sys.exit(1)
    
    # List enabled strategies
    enabled_strategies = [name for name, config in STRATEGIES.items() if config['enabled']]
    
    if not enabled_strategies:
        print("No strategies enabled!")
        print("\nTo enable strategies, set environment variables:")
        print("  ENABLE_STRADDLE=true")
        print("  ENABLE_STRANGLE=true")
        print("  ENABLE_IRON_CONDOR=true")
        print("  ENABLE_IRON_BUTTERFLY=true")
        print("  ENABLE_BULL_CALL_SPREAD=true")
        print("  ENABLE_BEAR_PUT_SPREAD=true")
        print("  ENABLE_PROTECTIVE_PUT=true")
        print("  ENABLE_COVERED_CALL=true")
        print("  ENABLE_CALENDAR_SPREAD=true")
        sys.exit(1)
    
    print(f"Enabled strategies: {', '.join([STRATEGIES[s]['name'] for s in enabled_strategies])}")
    print(f"Total strategies: {len(enabled_strategies)}")
    print("-" * 70)
    print()
    
    # Start each enabled strategy in its own thread
    threads = []
    for strategy_key, config in STRATEGIES.items():
        if config['enabled']:
            thread = threading.Thread(
                target=run_strategy,
                args=(config['name'], config['function']),
                name=f"Thread-{config['name']}",
                daemon=False
            )
            thread.start()
            threads.append(thread)
            config['thread'] = thread
            print(f"[{datetime.now()}] Started {config['name']} strategy (Thread: {thread.name})")
            time.sleep(1)  # Small delay between starting threads
    
    print()
    print("-" * 70)
    print(f"All strategies started. Running {len(threads)} strategies in parallel.")
    print("Press Ctrl+C to stop all strategies.")
    print("-" * 70)
    print()
    
    # Monitor threads
    try:
        while True:
            time.sleep(10)  # Check every 10 seconds
            
            # Check if any thread has died
            alive_threads = [t for t in threads if t.is_alive()]
            if len(alive_threads) < len(threads):
                dead_threads = [t for t in threads if not t.is_alive()]
                for dead_thread in dead_threads:
                    print(f"[{datetime.now()}] WARNING: Thread {dead_thread.name} has stopped")
            
            # Print status
            if len(alive_threads) == 0:
                print(f"[{datetime.now()}] All strategy threads have stopped")
                break
                
    except KeyboardInterrupt:
        print()
        print("-" * 70)
        print(f"[{datetime.now()}] Stopping all strategies...")
        print("-" * 70)
        
        # Wait for all threads to complete (with timeout)
        for thread in threads:
            if thread.is_alive():
                print(f"[{datetime.now()}] Waiting for {thread.name} to finish...")
                thread.join(timeout=5)
                if thread.is_alive():
                    print(f"[{datetime.now()}] WARNING: {thread.name} did not stop gracefully")
        
        print(f"[{datetime.now()}] All strategies stopped")
        print("=" * 70)

if __name__ == "__main__":
    main()
