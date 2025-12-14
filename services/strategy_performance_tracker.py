"""
Strategy Performance Tracker
Tracks live market performance of strategies and updates profitability labels
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')

# Performance thresholds
HIGH_PROFIT_THRESHOLD = 10000  # Rs
HIGH_PROFIT_WIN_RATE = 70  # %
MEDIUM_PROFIT_WIN_RATE = 50  # %

PERFORMANCE_FILE = Path('strategies') / 'strategy_performance.json'

def load_performance_data() -> Dict:
    """Load strategy performance data from file"""
    if PERFORMANCE_FILE.exists():
        try:
            with open(PERFORMANCE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading performance data: {e}")
    return {}

def save_performance_data(data: Dict):
    """Save strategy performance data to file"""
    try:
        PERFORMANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PERFORMANCE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving performance data: {e}")

def update_strategy_performance(
    strategy_id: str,
    pnl: float,
    is_win: bool,
    strategy_type: str = 'intraday'
):
    """Update performance metrics for a strategy"""
    try:
        data = load_performance_data()
        
        if strategy_id not in data:
            data[strategy_id] = {
                'total_pnl': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'strategy_type': strategy_type,
                'last_update': None,
                'daily_pnl': {},
                'trades_history': []
            }
        
        strategy_data = data[strategy_id]
        strategy_data['total_pnl'] += pnl
        strategy_data['total_trades'] += 1
        
        if is_win:
            strategy_data['winning_trades'] += 1
        else:
            strategy_data['losing_trades'] += 1
        
        # Calculate win rate
        if strategy_data['total_trades'] > 0:
            strategy_data['win_rate'] = (strategy_data['winning_trades'] / strategy_data['total_trades']) * 100
        
        # Update daily PnL
        today = datetime.now(IST).strftime('%Y-%m-%d')
        if today not in strategy_data['daily_pnl']:
            strategy_data['daily_pnl'][today] = 0.0
        strategy_data['daily_pnl'][today] += pnl
        
        # Add to trades history (keep last 100)
        strategy_data['trades_history'].append({
            'timestamp': datetime.now(IST).isoformat(),
            'pnl': pnl,
            'is_win': is_win
        })
        if len(strategy_data['trades_history']) > 100:
            strategy_data['trades_history'] = strategy_data['trades_history'][-100:]
        
        strategy_data['last_update'] = datetime.now(IST).isoformat()
        strategy_data['strategy_type'] = strategy_type
        
        save_performance_data(data)
        
        # Update profitability label
        update_profitability_label(strategy_id, strategy_data)
        
        logger.info(f"Updated performance for {strategy_id}: PnL={pnl}, Total={strategy_data['total_pnl']:.2f}, Win Rate={strategy_data['win_rate']:.1f}%")
        
    except Exception as e:
        logger.error(f"Error updating strategy performance: {e}")

def update_profitability_label(strategy_id: str, strategy_data: Dict):
    """Update profitability label based on performance"""
    try:
        from blueprints.python_strategy import STRATEGY_CONFIGS, save_configs
        
        if strategy_id not in STRATEGY_CONFIGS:
            return
        
        total_pnl = strategy_data.get('total_pnl', 0.0)
        win_rate = strategy_data.get('win_rate', 0.0)
        total_trades = strategy_data.get('total_trades', 0)
        
        profitability_label = 'unknown'
        if total_trades > 0:
            if total_pnl > HIGH_PROFIT_THRESHOLD and win_rate >= HIGH_PROFIT_WIN_RATE:
                profitability_label = 'high_profit'
            elif total_pnl > 0 and win_rate >= MEDIUM_PROFIT_WIN_RATE:
                profitability_label = 'medium_profit'
            elif total_pnl > 0:
                profitability_label = 'low_profit'
            else:
                profitability_label = 'losses'
        
        # Update config
        STRATEGY_CONFIGS[strategy_id]['profitability_label'] = profitability_label
        STRATEGY_CONFIGS[strategy_id]['total_pnl'] = total_pnl
        STRATEGY_CONFIGS[strategy_id]['win_rate'] = win_rate
        STRATEGY_CONFIGS[strategy_id]['total_trades'] = total_trades
        STRATEGY_CONFIGS[strategy_id]['winning_trades'] = strategy_data.get('winning_trades', 0)
        STRATEGY_CONFIGS[strategy_id]['losing_trades'] = strategy_data.get('losing_trades', 0)
        STRATEGY_CONFIGS[strategy_id]['last_pnl_update'] = datetime.now(IST).isoformat()
        
        save_configs()
        
    except Exception as e:
        logger.error(f"Error updating profitability label: {e}")

def get_strategy_performance(strategy_id: str) -> Optional[Dict]:
    """Get performance data for a strategy"""
    data = load_performance_data()
    return data.get(strategy_id)

def get_all_performance() -> Dict:
    """Get performance data for all strategies"""
    return load_performance_data()

def get_daily_summary(date: str = None) -> Dict:
    """Get daily performance summary"""
    if date is None:
        date = datetime.now(IST).strftime('%Y-%m-%d')
    
    data = load_performance_data()
    summary = {
        'date': date,
        'total_strategies': 0,
        'profitable': 0,
        'losing': 0,
        'total_pnl': 0.0,
        'strategies': []
    }
    
    for strategy_id, perf_data in data.items():
        daily_pnl = perf_data.get('daily_pnl', {}).get(date, 0.0)
        if daily_pnl != 0:
            summary['total_strategies'] += 1
            summary['total_pnl'] += daily_pnl
            if daily_pnl > 0:
                summary['profitable'] += 1
            else:
                summary['losing'] += 1
            
            summary['strategies'].append({
                'strategy_id': strategy_id,
                'daily_pnl': daily_pnl,
                'total_pnl': perf_data.get('total_pnl', 0.0),
                'win_rate': perf_data.get('win_rate', 0.0),
                'strategy_type': perf_data.get('strategy_type', 'intraday')
            })
    
    return summary

def sync_performance_to_configs():
    """Sync performance data to strategy configs"""
    try:
        from blueprints.python_strategy import STRATEGY_CONFIGS, save_configs
        
        data = load_performance_data()
        
        for strategy_id, perf_data in data.items():
            if strategy_id in STRATEGY_CONFIGS:
                update_profitability_label(strategy_id, perf_data)
        
        logger.info("Synced performance data to strategy configs")
        
    except Exception as e:
        logger.error(f"Error syncing performance data: {e}")
