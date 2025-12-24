#!/usr/bin/env python3
"""
Example: How to integrate Strategy Performance Filter with strategy execution
This shows how to filter strategies before starting them
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from strategy_execution_filter import StrategyExecutionFilter

def start_strategies_by_category(categories=None, actions=None):
    """
    Start strategies filtered by category and/or actions
    
    Args:
        categories: List of categories to include (e.g., ["top_performance"])
                   If None, all categories are included
        actions: List of actions to include (e.g., ["BUY", "SELL"])
                If None, all actions are included
    """
    filter_obj = StrategyExecutionFilter()
    
    # Get filtered strategies
    strategies_to_start = filter_obj.get_strategies_to_start(
        categories=categories,
        actions=actions
    )
    
    if not strategies_to_start:
        print("No strategies match the filter criteria")
        return
    
    print(f"\nStarting {len(strategies_to_start)} strategy(ies):")
    print("="*80)
    
    for strategy_name in strategies_to_start:
        info = filter_obj.get_strategy_execution_info(strategy_name)
        
        print(f"\nStrategy: {strategy_name}")
        print(f"  Category: {info['category']}")
        print(f"  Avg P&L: Rs {info['avg_pnl']:,.2f}")
        print(f"  Allowed Actions: {', '.join(info['allowed_actions'])}")
        if info['restriction_reason']:
            print(f"  Note: {info['restriction_reason']}")
        
        # Here you would actually start the strategy
        # Example: start_strategy_process(strategy_name)
        print(f"  [WOULD START] {strategy_name}")
    
    print("\n" + "="*80)
    print("Strategy execution would happen here")
    print("="*80)

def check_before_order(strategy_name, action):
    """Check if an order can be placed before executing"""
    filter_obj = StrategyExecutionFilter()
    
    if not filter_obj.can_execute_action(strategy_name, action):
        info = filter_obj.get_strategy_execution_info(strategy_name)
        print(f"Cannot execute {action} for {strategy_name}")
        print(f"Reason: {info['restriction_reason']}")
        print(f"Allowed actions: {', '.join(info['allowed_actions'])}")
        return False
    
    print(f"[OK] {action} is allowed for {strategy_name}")
    return True

# Example usage scenarios
if __name__ == "__main__":
    print("\n" + "="*80)
    print("STRATEGY FILTER INTEGRATION EXAMPLES")
    print("="*80)
    
    # Scenario 1: Start only top performers
    print("\n1. Starting TOP PERFORMANCE strategies only:")
    start_strategies_by_category(categories=["top_performance"])
    
    # Scenario 2: Start top and average, skip low
    print("\n2. Starting TOP and AVERAGE performance strategies:")
    start_strategies_by_category(categories=["top_performance", "average_performance"])
    
    # Scenario 3: Start only strategies that can execute BUY
    print("\n3. Starting strategies that can execute BUY:")
    start_strategies_by_category(actions=["BUY"])
    
    # Scenario 4: Top performance with BUY only
    print("\n4. Starting TOP PERFORMANCE strategies with BUY only:")
    start_strategies_by_category(
        categories=["top_performance"],
        actions=["BUY"]
    )
    
    # Scenario 5: Check before placing order
    print("\n5. Checking before placing order:")
    check_before_order("Bear Put Spread", "BUY")
    check_before_order("Bear Put Spread", "SELL")
    check_before_order("Buy Strangle", "BUY")  # This might be restricted

