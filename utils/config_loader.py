"""
Configuration Loader for Strategies
Provides centralized configuration management for trading strategies
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=False)


class ConfigLoader:
    """Configuration loader for strategies"""
    
    def __init__(self):
        self.config_file = Path('config') / 'trading_config.json'
        self._config_data = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self._config_data = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
                self._config_data = {}
        else:
            self._config_data = {}
    
    def get_trading_preferences(self) -> Dict[str, Any]:
        """Get trading preferences configuration"""
        return self._config_data.get('trading_preferences', {
            'exchanges': ['NSE'],
            'product_type': 'MIS',
            'quantity': 1
        })
    
    def get_strategy_config(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific strategy"""
        strategies = self._config_data.get('strategies', {})
        return strategies.get(strategy_name)
    
    def get_historical_data_config(self) -> Dict[str, Any]:
        """Get historical data configuration"""
        return self._config_data.get('historical_data', {
            'source': 'yfinance',
            'interval': '5m',
            'lookback_days': 60
        })
    
    def get_risk_management_config(self) -> Dict[str, Any]:
        """Get risk management configuration"""
        return self._config_data.get('risk_management', {
            'stop_loss_pct': 2.0,
            'max_position_size': 10,
            'max_daily_loss': 5000
        })


# Global config instance
_config_instance = None


def get_config() -> ConfigLoader:
    """Get the global configuration loader instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader()
    return _config_instance


