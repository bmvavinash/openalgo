#!/usr/bin/env python3
"""
Strategy Performance Configuration System
Manages buy/sell restrictions and performance-based categorization
"""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

CONFIG_FILE = Path(__file__).parent / "config" / "strategy_performance.json"

class StrategyPerformanceConfig:
    """Manages strategy performance configuration and restrictions"""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or CONFIG_FILE
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return self._default_config()
        return self._default_config()
    
    def _default_config(self) -> dict:
        """Default configuration structure"""
        return {
            "version": "1.0",
            "last_updated": None,
            "performance_thresholds": {
                "top_performance": 100.0,  # P&L > 100
                "average_performance": 0.0,  # P&L between 0 and 100
                "low_performance": -100.0  # P&L < 0
            },
            "strategies": {},
            "categories": {
                "top_performance": [],
                "average_performance": [],
                "low_performance": []
            }
        }
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def set_buy_sell_restriction(self, strategy_name: str, allowed_actions: List[str]):
        """
        Set buy/sell restrictions for a strategy
        
        Args:
            strategy_name: Name of the strategy
            allowed_actions: List of allowed actions ['BUY', 'SELL'] or ['BUY'] or ['SELL']
        """
        if strategy_name not in self.config["strategies"]:
            self.config["strategies"][strategy_name] = {}
        
        self.config["strategies"][strategy_name]["allowed_actions"] = allowed_actions
        self.config["strategies"][strategy_name]["restriction_type"] = "manual" if len(allowed_actions) < 2 else "none"
        self._save_config()
    
    def get_allowed_actions(self, strategy_name: str) -> List[str]:
        """
        Get allowed actions for a strategy
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            List of allowed actions ['BUY', 'SELL'] by default
        """
        if strategy_name in self.config["strategies"]:
            return self.config["strategies"][strategy_name].get("allowed_actions", ["BUY", "SELL"])
        return ["BUY", "SELL"]  # Default: allow both
    
    def is_action_allowed(self, strategy_name: str, action: str) -> bool:
        """Check if an action is allowed for a strategy"""
        allowed = self.get_allowed_actions(strategy_name)
        return action.upper() in [a.upper() for a in allowed]
    
    def update_performance_category(self, strategy_name: str, pnl: float, 
                                   win_rate: float = None, period: str = "current_day"):
        """
        Update performance category for a strategy based on P&L
        
        Args:
            strategy_name: Name of the strategy
            pnl: Profit and Loss value
            win_rate: Win rate percentage (optional)
            period: Period analyzed (current_day, previous_day, etc.)
        """
        if strategy_name not in self.config["strategies"]:
            self.config["strategies"][strategy_name] = {}
        
        strategy_config = self.config["strategies"][strategy_name]
        
        # Store performance data
        if "performance_history" not in strategy_config:
            strategy_config["performance_history"] = []
        
        strategy_config["performance_history"].append({
            "period": period,
            "pnl": pnl,
            "win_rate": win_rate,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 30 days
        strategy_config["performance_history"] = strategy_config["performance_history"][-30:]
        
        # Calculate average P&L
        recent_pnl = [p["pnl"] for p in strategy_config["performance_history"][-7:]]  # Last 7 days
        avg_pnl = sum(recent_pnl) / len(recent_pnl) if recent_pnl else pnl
        
        # Update category based on thresholds
        thresholds = self.config["performance_thresholds"]
        category = self._categorize_performance(avg_pnl, thresholds)
        
        strategy_config["category"] = category
        strategy_config["avg_pnl"] = avg_pnl
        strategy_config["last_updated"] = datetime.now().isoformat()
        
        # Update category lists
        self._update_category_lists()
        self._save_config()
        
        return category
    
    def _categorize_performance(self, pnl: float, thresholds: dict) -> str:
        """Categorize performance based on P&L thresholds"""
        if pnl >= thresholds["top_performance"]:
            return "top_performance"
        elif pnl >= thresholds["average_performance"]:
            return "average_performance"
        else:
            return "low_performance"
    
    def _update_category_lists(self):
        """Update category lists based on current strategy categories"""
        self.config["categories"] = {
            "top_performance": [],
            "average_performance": [],
            "low_performance": []
        }
        
        for strategy_name, strategy_config in self.config["strategies"].items():
            category = strategy_config.get("category", "low_performance")
            if category in self.config["categories"]:
                self.config["categories"][category].append(strategy_name)
    
    def get_strategies_by_category(self, category: str) -> List[str]:
        """Get list of strategies in a specific category"""
        return self.config["categories"].get(category, [])
    
    def get_all_categories(self) -> Dict[str, List[str]]:
        """Get all strategies categorized"""
        return self.config["categories"].copy()
    
    def auto_detect_restrictions(self, analysis_results: Dict[str, Dict]):
        """
        Automatically detect and set buy/sell restrictions based on analysis
        
        Args:
            analysis_results: Dictionary with strategy names as keys and analysis results as values
                Example: {
                    "Bear Put Spread": {
                        "buy_pnl": 100.0,
                        "sell_pnl": -50.0,
                        "buy_win_rate": 80.0,
                        "sell_win_rate": 20.0
                    }
                }
        """
        for strategy_name, results in analysis_results.items():
            buy_pnl = results.get("buy_pnl", 0)
            sell_pnl = results.get("sell_pnl", 0)
            buy_win_rate = results.get("buy_win_rate", 0)
            sell_win_rate = results.get("sell_win_rate", 0)
            
            # Determine restrictions based on performance
            # If buy is profitable and sell is not, restrict to BUY
            # If sell is profitable and buy is not, restrict to SELL
            # If both are profitable or both are losing, allow both
            
            if buy_pnl > 0 and sell_pnl < 0 and buy_win_rate > 50:
                self.set_buy_sell_restriction(strategy_name, ["BUY"])
                print(f"Auto-restricted {strategy_name} to BUY only (Buy P&L: {buy_pnl}, Sell P&L: {sell_pnl})")
            elif sell_pnl > 0 and buy_pnl < 0 and sell_win_rate > 50:
                self.set_buy_sell_restriction(strategy_name, ["SELL"])
                print(f"Auto-restricted {strategy_name} to SELL only (Buy P&L: {buy_pnl}, Sell P&L: {sell_pnl})")
            else:
                # Allow both or keep existing restriction
                current_allowed = self.get_allowed_actions(strategy_name)
                if len(current_allowed) < 2:
                    # If previously restricted but now both are OK, allow both
                    self.set_buy_sell_restriction(strategy_name, ["BUY", "SELL"])
                    print(f"Auto-allowed both BUY and SELL for {strategy_name}")
    
    def set_performance_thresholds(self, top: float = None, average: float = None, low: float = None):
        """Update performance thresholds"""
        if top is not None:
            self.config["performance_thresholds"]["top_performance"] = top
        if average is not None:
            self.config["performance_thresholds"]["average_performance"] = average
        if low is not None:
            self.config["performance_thresholds"]["low_performance"] = low
        self._save_config()
    
    def get_performance_thresholds(self) -> dict:
        """Get current performance thresholds"""
        return self.config["performance_thresholds"].copy()
    
    def get_strategy_info(self, strategy_name: str) -> dict:
        """Get complete information about a strategy"""
        if strategy_name in self.config["strategies"]:
            return self.config["strategies"][strategy_name].copy()
        return {}
    
    def should_start_strategy(self, strategy_name: str, allowed_categories: List[str] = None) -> bool:
        """
        Check if a strategy should be started based on category filters
        
        Args:
            strategy_name: Name of the strategy
            allowed_categories: List of categories to allow (e.g., ["top_performance"])
                              If None, all categories are allowed
        """
        if allowed_categories is None or len(allowed_categories) == 0:
            return True  # No filter, allow all
        
        strategy_config = self.config["strategies"].get(strategy_name, {})
        category = strategy_config.get("category", "low_performance")
        
        return category in allowed_categories







