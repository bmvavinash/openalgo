#!/usr/bin/env python
"""
Multi-Day Historical Backtest Runner
Runs all strategies on historical data for multiple days to confirm performance
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from datetime import datetime, timedelta
import pytz
from database.sandbox_db import SandboxTrades, db_session
from collections import defaultdict
from blueprints.python_strategy import STRATEGY_CONFIGS

def analyze_strategy_performance_for_days(days=7):
    """Analyze strategy performance over the last N days"""
    with app.app_context():
        ist = pytz.timezone('Asia/Kolkata')
        end_date = datetime.now(ist).date()
        start_date = end_date - timedelta(days=days)
        
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=ist)
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=ist)
        
        # Get all trades in the period
        trades = SandboxTrades.query.filter(
            SandboxTrades.trade_timestamp >= start_dt,
            SandboxTrades.trade_timestamp <= end_dt
        ).all()
        
        print("="*70)
        print(f"MULTI-DAY STRATEGY PERFORMANCE ANALYSIS ({days} days)")
        print("="*70)
        print(f"Period: {start_date} to {end_date}")
        print(f"Analysis Date: {datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}")
        print(f"Total trades analyzed: {len(trades)}")
        print("="*70)
        
        if not trades:
            print("\nNo trades found in the specified period.")
            return
        
        # Group by strategy
        strategy_stats = defaultdict(lambda: {
            'trades': 0, 'buy_value': 0, 'sell_value': 0, 'pnl': 0, 
            'buy_count': 0, 'sell_count': 0, 'days_active': set()
        })
        
        for trade in trades:
            strategy = trade.strategy or 'Unknown'
            value = float(trade.price) * trade.quantity
            trade_date = trade.trade_timestamp.date()
            strategy_stats[strategy]['days_active'].add(trade_date)
            
            if trade.action == 'BUY':
                strategy_stats[strategy]['trades'] += 1
                strategy_stats[strategy]['buy_value'] += value
                strategy_stats[strategy]['buy_count'] += 1
            else:  # SELL
                strategy_stats[strategy]['trades'] += 1
                strategy_stats[strategy]['sell_value'] += value
                strategy_stats[strategy]['sell_count'] += 1
        
        # Calculate PnL and convert sets
        for strategy, stats in strategy_stats.items():
            stats['pnl'] = stats['sell_value'] - stats['buy_value']
            stats['pnl_percent'] = (stats['pnl'] / stats['buy_value'] * 100) if stats['buy_value'] > 0 else 0
            stats['days_active'] = len(stats['days_active'])
        
        # Sort by PnL
        sorted_strategies = sorted(strategy_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)
        
        print(f"\n{'Strategy':<40} | {'Type':<10} | {'Days':>4} | {'Trades':>6} | {'PnL':>15} | {'PnL %':>10} | {'Status':>12}")
        print("-" * 110)
        
        profitable = []
        losing = []
        neutral = []
        
        for strategy, data in sorted_strategies:
            # Determine strategy type
            strategy_type = 'Unknown'
            if strategy in STRATEGY_CONFIGS:
                config = STRATEGY_CONFIGS[strategy]
                strategy_type = config.get('strategy_type', 'intraday')
            elif 'Option' in strategy or 'option' in strategy.lower():
                strategy_type = 'options'
            else:
                strategy_type = 'intraday'
            
            status = "PROFITABLE" if data['pnl'] > 0 else ("LOSING" if data['pnl'] < 0 else "NEUTRAL")
            pnl_sign = "+" if data['pnl'] >= 0 else ""
            
            print(f"{strategy:<40} | {strategy_type:<10} | {data['days_active']:>4} | {data['trades']:>6} | {pnl_sign}Rs{data['pnl']:>13.2f} | {pnl_sign}{data['pnl_percent']:>9.2f}% | {status:>12}")
            
            if data['pnl'] > 0:
                profitable.append((strategy, data, strategy_type))
            elif data['pnl'] < 0:
                losing.append((strategy, data, strategy_type))
            else:
                neutral.append((strategy, data, strategy_type))
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Total Strategies: {len(strategy_stats)}")
        print(f"Profitable: {len(profitable)}")
        print(f"Losing: {len(losing)}")
        print(f"Neutral: {len(neutral)}")
        
        # Top performers
        if profitable:
            print("\n" + "-"*70)
            print("TOP PROFITABLE STRATEGIES")
            print("-"*70)
            for strategy, data, stype in sorted(profitable, key=lambda x: x[1]['pnl'], reverse=True)[:10]:
                print(f"  + {strategy:<40} ({stype}): Rs {data['pnl']:>13.2f} ({data['pnl_percent']:>9.2f}%) - {data['trades']} trades over {data['days_active']} days")
        
        # Worst performers
        if losing:
            print("\n" + "-"*70)
            print("LOSING STRATEGIES")
            print("-"*70)
            for strategy, data, stype in sorted(losing, key=lambda x: x[1]['pnl'])[:10]:
                print(f"  - {strategy:<40} ({stype}): Rs {data['pnl']:>13.2f} ({data['pnl_percent']:>9.2f}%) - {data['trades']} trades over {data['days_active']} days")
        
        # Options vs Intraday breakdown
        print("\n" + "="*70)
        print("STRATEGY TYPE BREAKDOWN")
        print("="*70)
        
        options_profitable = [s for s in profitable if s[2] == 'options']
        options_losing = [s for s in losing if s[2] == 'options']
        intraday_profitable = [s for s in profitable if s[2] == 'intraday']
        intraday_losing = [s for s in losing if s[2] == 'intraday']
        
        print(f"\nOptions Strategies:")
        print(f"  Profitable: {len(options_profitable)}")
        print(f"  Losing: {len(options_losing)}")
        
        print(f"\nIntraday Strategies:")
        print(f"  Profitable: {len(intraday_profitable)}")
        print(f"  Losing: {len(intraday_losing)}")
        
        print("\n" + "="*70)
        print("ANALYSIS COMPLETE")
        print("="*70)
        
        return {
            'profitable': profitable,
            'losing': losing,
            'neutral': neutral,
            'options_profitable': options_profitable,
            'options_losing': options_losing,
            'intraday_profitable': intraday_profitable,
            'intraday_losing': intraday_losing
        }

if __name__ == "__main__":
    # Run analysis for different periods
    print("\n" + "="*70)
    print("RUNNING MULTI-DAY BACKTEST ANALYSIS")
    print("="*70)
    
    # Analyze last 7 days
    print("\n>>> Analyzing last 7 days...")
    results_7d = analyze_strategy_performance_for_days(days=7)
    
    # Analyze last 14 days
    print("\n\n>>> Analyzing last 14 days...")
    results_14d = analyze_strategy_performance_for_days(days=14)
    
    # Analyze last 30 days
    print("\n\n>>> Analyzing last 30 days...")
    results_30d = analyze_strategy_performance_for_days(days=30)
    
    print("\n\n" + "="*70)
    print("ALL ANALYSES COMPLETE")
    print("="*70)










