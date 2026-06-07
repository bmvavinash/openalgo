"""
Pricing Configuration for Trade Value Limits
Supports global and strategy-level limits
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from decimal import Decimal
from utils.logging import get_logger

logger = get_logger(__name__)

# Default configuration
DEFAULT_MAX_TRADE_VALUE = Decimal('5000.00')  # Default: ₹5000 per trade

# Configuration file path
CONFIG_DIR = Path('config')
CONFIG_FILE = CONFIG_DIR / 'pricing_config.json'


class PricingConfig:
    """Manages pricing/trade value limits"""
    
    def __init__(self):
        self._config_data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Convert string values to Decimal
                    if 'global_max_trade_value' in config:
                        config['global_max_trade_value'] = Decimal(str(config['global_max_trade_value']))
                    if 'strategy_limits' in config:
                        for strategy_id, limit in config['strategy_limits'].items():
                            config['strategy_limits'][strategy_id] = Decimal(str(limit))
                    return config
            else:
                # Create default config
                default_config = {
                    'global_max_trade_value': float(DEFAULT_MAX_TRADE_VALUE),
                    'strategy_limits': {}
                }
                self._save_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"Error loading pricing config: {e}")
            return {
                'global_max_trade_value': float(DEFAULT_MAX_TRADE_VALUE),
                'strategy_limits': {}
            }
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file"""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            # Convert Decimal to float for JSON serialization
            save_config = config.copy()
            if 'global_max_trade_value' in save_config and isinstance(save_config['global_max_trade_value'], Decimal):
                save_config['global_max_trade_value'] = float(save_config['global_max_trade_value'])
            if 'strategy_limits' in save_config:
                save_config['strategy_limits'] = {
                    k: float(v) if isinstance(v, Decimal) else v
                    for k, v in save_config['strategy_limits'].items()
                }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(save_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving pricing config: {e}")
    
    def get_max_trade_value(self, strategy_id: Optional[str] = None) -> Decimal:
        """
        Get maximum trade value limit for a strategy
        
        Args:
            strategy_id: Optional strategy ID. If provided, checks for strategy-specific limit.
                        If not found, returns global limit.
        
        Returns:
            Maximum trade value (quantity * price) allowed
        """
        # Check for strategy-specific limit first
        if strategy_id and strategy_id in self._config_data.get('strategy_limits', {}):
            limit = Decimal(str(self._config_data['strategy_limits'][strategy_id]))
            logger.debug(f"Using strategy-specific limit for {strategy_id}: ₹{limit}")
            return limit
        
        # Return global limit
        global_limit = Decimal(str(self._config_data.get('global_max_trade_value', DEFAULT_MAX_TRADE_VALUE)))
        return global_limit
    
    def set_global_limit(self, max_value: Decimal):
        """Set global maximum trade value limit"""
        self._config_data['global_max_trade_value'] = float(max_value)
        self._save_config(self._config_data)
        logger.info(f"Global max trade value set to ₹{max_value}")
    
    def set_strategy_limit(self, strategy_id: str, max_value: Decimal):
        """Set strategy-specific maximum trade value limit"""
        if 'strategy_limits' not in self._config_data:
            self._config_data['strategy_limits'] = {}
        self._config_data['strategy_limits'][strategy_id] = float(max_value)
        self._save_config(self._config_data)
        logger.info(f"Strategy {strategy_id} max trade value set to ₹{max_value}")
    
    def remove_strategy_limit(self, strategy_id: str):
        """Remove strategy-specific limit (falls back to global)"""
        if 'strategy_limits' in self._config_data and strategy_id in self._config_data['strategy_limits']:
            del self._config_data['strategy_limits'][strategy_id]
            self._save_config(self._config_data)
            logger.info(f"Removed strategy-specific limit for {strategy_id}")


# Global instance
_pricing_config_instance = None


def get_pricing_config() -> PricingConfig:
    """Get the global pricing configuration instance"""
    global _pricing_config_instance
    if _pricing_config_instance is None:
        _pricing_config_instance = PricingConfig()
    return _pricing_config_instance



