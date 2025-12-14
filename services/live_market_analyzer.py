"""
Live Market Performance Analyzer
Analyzes strategy performance in real-time and generates reports
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')

ANALYSIS_FILE = Path('strategies') / 'live_market_analysis.json'

def load_analysis_data() -> Dict:
    """Load live market analysis data"""
    if ANALYSIS_FILE.exists():
        try:
            with open(ANALYSIS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading analysis data: {e}")
    return {}

def save_analysis_data(data: Dict):
    """Save live market analysis data"""
    try:
        ANALYSIS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving analysis data: {e}")

def analyze_daily_performance(date: str = None) -> Dict:
    """Analyze daily performance and categorize strategies"""
    if date is None:
        date = datetime.now(IST).strftime('%Y-%m-%d')
    
    try:
        from services.strategy_performance_tracker import get_all_performance
        from blueprints.python_strategy import STRATEGY_CONFIGS
        
        perf_data = get_all_performance()
        
        analysis = {
            'date': date,
            'timestamp': datetime.now(IST).isoformat(),
            'strategies': {
                'high_profit': [],
                'medium_profit': [],
                'low_profit': [],
                'losses': [],
                'unknown': []
            },
            'summary': {
                'total_strategies': 0,
                'profitable': 0,
                'losing': 0,
                'total_pnl': 0.0,
                'intraday_count': 0,
                'options_count': 0,
                'intraday_pnl': 0.0,
                'options_pnl': 0.0
            }
        }
        
        for strategy_id, config in STRATEGY_CONFIGS.items():
            strategy_type = config.get('strategy_type', 'intraday')
            perf = perf_data.get(strategy_id, {})
            
            daily_pnl = perf.get('daily_pnl', {}).get(date, 0.0)
            total_pnl = perf.get('total_pnl', 0.0)
            win_rate = perf.get('win_rate', 0.0)
            total_trades = perf.get('total_trades', 0)
            
            strategy_info = {
                'strategy_id': strategy_id,
                'name': config.get('name', 'Unnamed'),
                'type': strategy_type,
                'daily_pnl': daily_pnl,
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'total_trades': total_trades
            }
            
            # Categorize based on total performance
            if total_trades > 0:
                if total_pnl > 10000 and win_rate >= 70:
                    category = 'high_profit'
                elif total_pnl > 0 and win_rate >= 50:
                    category = 'medium_profit'
                elif total_pnl > 0:
                    category = 'low_profit'
                else:
                    category = 'losses'
            else:
                category = 'unknown'
            
            analysis['strategies'][category].append(strategy_info)
            
            # Update summary
            analysis['summary']['total_strategies'] += 1
            analysis['summary']['total_pnl'] += total_pnl
            if total_pnl > 0:
                analysis['summary']['profitable'] += 1
            elif total_pnl < 0:
                analysis['summary']['losing'] += 1
            
            if strategy_type == 'intraday':
                analysis['summary']['intraday_count'] += 1
                analysis['summary']['intraday_pnl'] += total_pnl
            else:
                analysis['summary']['options_count'] += 1
                analysis['summary']['options_pnl'] += total_pnl
        
        save_analysis_data(analysis)
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing daily performance: {e}")
        return {}

def get_recommended_strategies() -> Dict:
    """Get recommended strategies for live trading"""
    try:
        from services.strategy_performance_tracker import get_all_performance
        from blueprints.python_strategy import STRATEGY_CONFIGS
        
        perf_data = get_all_performance()
        recommended = {
            'high_profit': [],
            'medium_profit': [],
            'ready_for_live': []
        }
        
        for strategy_id, config in STRATEGY_CONFIGS.items():
            perf = perf_data.get(strategy_id, {})
            total_pnl = perf.get('total_pnl', 0.0)
            win_rate = perf.get('win_rate', 0.0)
            total_trades = perf.get('total_trades', 0)
            
            if total_trades >= 10:  # Minimum trades for recommendation
                if total_pnl > 10000 and win_rate >= 70:
                    recommended['high_profit'].append({
                        'strategy_id': strategy_id,
                        'name': config.get('name'),
                        'type': config.get('strategy_type', 'intraday'),
                        'pnl': total_pnl,
                        'win_rate': win_rate
                    })
                elif total_pnl > 0 and win_rate >= 50:
                    recommended['medium_profit'].append({
                        'strategy_id': strategy_id,
                        'name': config.get('name'),
                        'type': config.get('strategy_type', 'intraday'),
                        'pnl': total_pnl,
                        'win_rate': win_rate
                    })
        
        # Ready for live = high profit strategies
        recommended['ready_for_live'] = recommended['high_profit'].copy()
        
        return recommended
        
    except Exception as e:
        logger.error(f"Error getting recommended strategies: {e}")
        return {'high_profit': [], 'medium_profit': [], 'ready_for_live': []}

def generate_end_of_day_report() -> str:
    """Generate end-of-day performance report"""
    analysis = analyze_daily_performance()
    
    if not analysis:
        return "No data available"
    
    report = f"""
{'='*70}
LIVE MARKET PERFORMANCE REPORT
{'='*70}
Date: {analysis['date']}
Generated: {analysis['timestamp']}

SUMMARY:
  Total Strategies: {analysis['summary']['total_strategies']}
  Profitable: {analysis['summary']['profitable']}
  Losing: {analysis['summary']['losing']}
  Total PnL: Rs {analysis['summary']['total_pnl']:.2f}
  
  Intraday Strategies: {analysis['summary']['intraday_count']} (PnL: Rs {analysis['summary']['intraday_pnl']:.2f})
  Options Strategies: {analysis['summary']['options_count']} (PnL: Rs {analysis['summary']['options_pnl']:.2f})

HIGH PROFIT STRATEGIES ({len(analysis['strategies']['high_profit'])}):
"""
    
    for s in analysis['strategies']['high_profit']:
        report += f"  - {s['name']} ({s['type']}): Rs {s['total_pnl']:.2f}, Win Rate: {s['win_rate']:.1f}%\n"
    
    report += f"\nMEDIUM PROFIT STRATEGIES ({len(analysis['strategies']['medium_profit'])}):\n"
    for s in analysis['strategies']['medium_profit']:
        report += f"  - {s['name']} ({s['type']}): Rs {s['total_pnl']:.2f}, Win Rate: {s['win_rate']:.1f}%\n"
    
    report += f"\nLOW PROFIT STRATEGIES ({len(analysis['strategies']['low_profit'])}):\n"
    for s in analysis['strategies']['low_profit']:
        report += f"  - {s['name']} ({s['type']}): Rs {s['total_pnl']:.2f}, Win Rate: {s['win_rate']:.1f}%\n"
    
    report += f"\nLOSING STRATEGIES ({len(analysis['strategies']['losses'])}):\n"
    for s in analysis['strategies']['losses']:
        report += f"  - {s['name']} ({s['type']}): Rs {s['total_pnl']:.2f}, Win Rate: {s['win_rate']:.1f}%\n"
    
    report += f"\n{'='*70}\n"
    
    return report
