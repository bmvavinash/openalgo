#!/usr/bin/env python3
"""
Strategy Execution Filter
Filters and controls strategy execution based on performance categories and buy/sell restrictions
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from strategy_performance_config import StrategyPerformanceConfig

class StrategyExecutionFilter:
    """Filters strategies based on performance categories and restrictions"""
    
    def __init__(self):
        self.config = StrategyPerformanceConfig()
    
    def filter_strategies(self, 
                         allowed_categories: Optional[List[str]] = None,
                         allowed_actions: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Filter strategies based on categories and actions
        
        Args:
            allowed_categories: List of categories to allow (e.g., ["top_performance"])
                               If None, all categories are allowed
            allowed_actions: List of actions to allow (e.g., ["BUY", "SELL"])
                           If None, all actions are allowed
        
        Returns:
            Dictionary mapping strategy names to whether they should be executed
        """
        all_strategies = self._get_all_strategies()
        filtered = {}
        
        for strategy_name in all_strategies:
            # Check category filter
            if allowed_categories:
                if not self.config.should_start_strategy(strategy_name, allowed_categories):
                    filtered[strategy_name] = False
                    continue
            
            # Check action filter
            if allowed_actions:
                strategy_allowed_actions = self.config.get_allowed_actions(strategy_name)
                # Check if any of the requested actions are allowed for this strategy
                if not any(action.upper() in [a.upper() for a in strategy_allowed_actions] 
                          for action in allowed_actions):
                    filtered[strategy_name] = False
                    continue
            
            filtered[strategy_name] = True
        
        return filtered
    
    def get_strategies_to_start(self, 
                                categories: Optional[List[str]] = None,
                                actions: Optional[List[str]] = None) -> List[str]:
        """
        Get list of strategies that should be started
        
        Args:
            categories: List of categories to include (e.g., ["top_performance", "average_performance"])
            actions: List of actions to include (e.g., ["BUY", "SELL"])
        
        Returns:
            List of strategy names to start
        """
        filtered = self.filter_strategies(categories, actions)
        return [name for name, should_start in filtered.items() if should_start]
    
    def can_execute_action(self, strategy_name: str, action: str) -> bool:
        """
        Check if a specific action can be executed for a strategy
        
        Args:
            strategy_name: Name of the strategy
            action: Action to check ("BUY" or "SELL")
        
        Returns:
            True if action is allowed, False otherwise
        """
        return self.config.is_action_allowed(strategy_name, action)
    
    def get_strategy_execution_info(self, strategy_name: str) -> Dict:
        """
        Get execution information for a strategy
        
        Returns:
            Dictionary with execution info:
            {
                "can_execute": bool,
                "category": str,
                "allowed_actions": List[str],
                "avg_pnl": float,
                "restriction_reason": str (if restricted)
            }
        """
        info = self.config.get_strategy_info(strategy_name)
        allowed_actions = self.config.get_allowed_actions(strategy_name)
        category = info.get("category", "low_performance")
        
        result = {
            "can_execute": True,
            "category": category,
            "allowed_actions": allowed_actions,
            "avg_pnl": info.get("avg_pnl", 0),
            "restriction_reason": None
        }
        
        # Check if restricted
        if len(allowed_actions) < 2:
            result["restriction_reason"] = f"Restricted to {', '.join(allowed_actions)} only"
        
        return result
    
    def _get_all_strategies(self) -> List[str]:
        """Get list of all available strategies"""
        # This should match the strategies in your system
        # You can extend this to read from database or config
        return [
            "Bear Put Spread",
            "Bull Call Spread",
            "Iron Condor",
            "Iron Butterfly",
            "Buy Straddle",
            "Sell Straddle",
            "Buy Strangle",
            "Sell Strangle"
        ]

def main():
    """Example usage"""
    filter_obj = StrategyExecutionFilter()
    
    # Example 1: Get top performance strategies only
    print("Top Performance Strategies:")
    top_strategies = filter_obj.get_strategies_to_start(categories=["top_performance"])
    for strategy in top_strategies:
        info = filter_obj.get_strategy_execution_info(strategy)
        print(f"  {strategy}: {info}")
    
    # Example 2: Get strategies that can execute BUY
    print("\nStrategies that can execute BUY:")
    buy_strategies = filter_obj.get_strategies_to_start(actions=["BUY"])
    for strategy in buy_strategies:
        print(f"  {strategy}")
    
    # Example 3: Check if a specific action is allowed
    print("\nChecking Bear Put Spread:")
    can_buy = filter_obj.can_execute_action("Bear Put Spread", "BUY")
    can_sell = filter_obj.can_execute_action("Bear Put Spread", "SELL")
    print(f"  Can BUY: {can_buy}")
    print(f"  Can SELL: {can_sell}")

if __name__ == "__main__":
    main()







