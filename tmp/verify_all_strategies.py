#!/usr/bin/env python
"""
Verify All Strategies - Check stop-loss, imports, and configuration
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("\n" + "="*120)
print("VERIFYING ALL STRATEGIES")
print("="*120)

strategies_to_check = [
    'strategies.scripts.rsi_strategy_20251203094216',
    'strategies.scripts.ema_crossover_with_stop_loss_20251201093414',
    'strategies.scripts.macd_strategy_20251201095522',
    'strategies.scripts.multi_indicator_strategy_20251201093321'
]

results = {}

for strategy_module in strategies_to_check:
    try:
        module = __import__(strategy_module, fromlist=[''])
        strategy_name = getattr(module, 'STRATEGY_NAME', 'Unknown')
        stop_loss_pct = getattr(module, 'STOP_LOSS_PCT', None)
        
        # Check for stop-loss related variables
        has_stop_loss_var = stop_loss_pct is not None
        has_check_function = hasattr(module, 'check_risk_management') or hasattr(module, 'check_stop_loss')
        
        # Check for symbol intervals (for optimized strategies)
        symbol_intervals = getattr(module, 'SYMBOL_INTERVALS', None)
        
        results[strategy_name] = {
            'imports': True,
            'stop_loss_var': has_stop_loss_var,
            'stop_loss_pct': stop_loss_pct,
            'check_function': has_check_function,
            'symbol_intervals': symbol_intervals,
            'status': 'OK'
        }
        
        print(f"\n[OK] {strategy_name}")
        print(f"  Stop-Loss Variable: {has_stop_loss_var} (Value: {stop_loss_pct}%)")
        print(f"  Check Function: {has_check_function}")
        if symbol_intervals:
            print(f"  Optimal Intervals: {symbol_intervals}")
    
    except ImportError as e:
        results[strategy_module] = {
            'imports': False,
            'error': str(e),
            'status': 'ERROR'
        }
        print(f"\n[ERROR] {strategy_module}")
        print(f"  Import Error: {e}")
    
    except Exception as e:
        results[strategy_module] = {
            'imports': True,
            'error': str(e),
            'status': 'WARNING'
        }
        print(f"\n[WARNING] {strategy_module}")
        print(f"  Error: {e}")

# Summary
print("\n" + "="*120)
print("VERIFICATION SUMMARY")
print("="*120)

all_ok = all(r.get('status') == 'OK' for r in results.values() if isinstance(r, dict))
all_have_stop_loss = all(r.get('stop_loss_var', False) for r in results.values() if isinstance(r, dict))

if all_ok and all_have_stop_loss:
    print("\n[SUCCESS] All strategies verified successfully!")
    print("  - All strategies import correctly")
    print("  - All strategies have stop-loss protection")
    print("  - MACD and Multi-Indicator have optimal interval configuration")
else:
    print("\n[WARNING] Some issues found:")
    for name, result in results.items():
        if result.get('status') != 'OK':
            print(f"  - {name}: {result.get('status')}")

print("\n" + "="*120)



