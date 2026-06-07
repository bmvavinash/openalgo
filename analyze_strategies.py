#!/usr/bin/env python
"""Analyze strategy performance from sandbox trades"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from database.sandbox_db import SandboxTrades, SandboxPositions, db_session
from datetime import datetime, timedelta
import pytz
from collections import defaultdict

def analyze_strategy_performance(start_date, end_date, strategy_name=None):
    """Analyze strategy performance for a date range"""
    ist = pytz.timezone('Asia/Kolkata')
    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=ist)
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=ist)
    
    query = SandboxTrades.query.filter(
        SandboxTrades.trade_timestamp >= start_dt,
        SandboxTrades.trade_timestamp <= end_dt
    )
    
    if strategy_name:
        query = query.filter(SandboxTrades.strategy == strategy_name)
    
    trades = query.all()
    
    # Group by strategy
    strategy_stats = defaultdict(lambda: {'trades': 0, 'buy_value': 0, 'sell_value': 0, 'pnl': 0})
    
    for trade in trades:
        strategy = trade.strategy or 'Unknown'
        value = float(trade.price) * trade.quantity
        
        if trade.action == 'BUY':
            strategy_stats[strategy]['trades'] += 1
            strategy_stats[strategy]['buy_value'] += value
        else:  # SELL
            strategy_stats[strategy]['trades'] += 1
            strategy_stats[strategy]['sell_value'] += value
    
    # Calculate PnL
    for strategy, stats in strategy_stats.items():
        stats['pnl'] = stats['sell_value'] - stats['buy_value']
        stats['pnl_percent'] = (stats['pnl'] / stats['buy_value'] * 100) if stats['buy_value'] > 0 else 0
    
    return dict(strategy_stats)

def main():
    with app.app_context():
        ist = pytz.timezone('Asia/Kolkata')
        today = datetime.now(ist).date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        days_14_ago = today - timedelta(days=14)
        
        print("=" * 70)
        print("COMPREHENSIVE STRATEGY PERFORMANCE ANALYSIS")
        print("=" * 70)
        print(f"Analysis Date: {datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}")
        print("=" * 70)
        
        periods = [
            ("CURRENT DAY", today, today),
            ("PREVIOUS DAY", yesterday, yesterday),
            ("LAST 7 DAYS", week_ago, today),
            ("LAST 14 DAYS", days_14_ago, today),
            ("LAST MONTH", month_ago, today)
        ]
        
        all_profitable = set()
        all_losing = set()
        options_profitable = set()
        options_losing = set()
        intraday_profitable = set()
        intraday_losing = set()
        
        for period_name, start_date, end_date in periods:
            print(f"\n{'='*70}")
            print(f"{period_name} ({start_date} to {end_date})")
            print("-" * 70)
            
            stats = analyze_strategy_performance(start_date, end_date)
            
            if stats:
                print(f"{'Strategy':<40} | {'Type':<10} | {'Trades':>6} | {'PnL':>15} | {'PnL %':>10} | {'Status':>12}")
                print("-" * 100)
                
                for strategy, data in sorted(stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
                    # Determine strategy type
                    strategy_type = 'INTRADAY'
                    if 'Option' in strategy or 'option' in strategy.lower():
                        strategy_type = 'OPTIONS'
                    
                    status = "PROFITABLE" if data['pnl'] > 0 else "LOSING"
                    pnl_sign = '+' if data['pnl'] >= 0 else ''
                    print(f"{strategy:<40} | {strategy_type:<10} | {data['trades']:>6} | {pnl_sign}Rs{data['pnl']:>13.2f} | {pnl_sign}{data['pnl_percent']:>9.2f}% | {status:>12}")
                    
                    if data['pnl'] > 0:
                        all_profitable.add(strategy)
                        if strategy_type == 'OPTIONS':
                            options_profitable.add(strategy)
                        else:
                            intraday_profitable.add(strategy)
                    else:
                        all_losing.add(strategy)
                        if strategy_type == 'OPTIONS':
                            options_losing.add(strategy)
                        else:
                            intraday_losing.add(strategy)
                
                print(f"\nSummary: {len(stats)} strategies, {len([s for s in stats.values() if s['pnl'] > 0])} profitable, {len([s for s in stats.values() if s['pnl'] < 0])} losing")
            else:
                print("  No trades found")
        
        # Overall Summary
        print(f"\n{'='*70}")
        print("OVERALL SUMMARY")
        print(f"{'='*70}")
        
        print(f"\nAll Strategies - Profitable in at least one period: {len(all_profitable)}")
        for strategy in sorted(all_profitable):
            strategy_type = "OPTIONS" if ('Option' in strategy or 'option' in strategy.lower()) else "INTRADAY"
            print(f"  + [{strategy_type}] {strategy}")
        
        print(f"\nAll Strategies - Losing in at least one period: {len(all_losing)}")
        for strategy in sorted(all_losing):
            strategy_type = "OPTIONS" if ('Option' in strategy or 'option' in strategy.lower()) else "INTRADAY"
            print(f"  - [{strategy_type}] {strategy}")
        
        print(f"\n{'='*70}")
        print("STRATEGY TYPE BREAKDOWN")
        print(f"{'='*70}")
        print(f"\nOptions Strategies:")
        print(f"  Profitable: {len(options_profitable)}")
        if options_profitable:
            for strategy in sorted(options_profitable):
                print(f"    + {strategy}")
        print(f"  Losing: {len(options_losing)}")
        if options_losing:
            for strategy in sorted(options_losing):
                print(f"    - {strategy}")
        
        print(f"\nIntraday Strategies:")
        print(f"  Profitable: {len(intraday_profitable)}")
        if intraday_profitable:
            for strategy in sorted(intraday_profitable):
                print(f"    + {strategy}")
        print(f"  Losing: {len(intraday_losing)}")
        if intraday_losing:
            for strategy in sorted(intraday_losing):
                print(f"    - {strategy}")
        
        print("\n" + "=" * 70)
        print("ANALYSIS COMPLETE")
        print("=" * 70)

if __name__ == "__main__":
    main()












