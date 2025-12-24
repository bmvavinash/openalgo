#!/usr/bin/env python
"""
Options Strategies Historical Backtest Runner
Specifically runs options strategies on historical data
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import pytz
from database.sandbox_db import SandboxTrades, db_session
from collections import defaultdict

def analyze_options_strategies_for_period(start_date, end_date):
    """Analyze options strategies trades from sandbox for a period"""
    ist = pytz.timezone('Asia/Kolkata')
    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=ist)
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=ist)
    
    # Get all trades in the period
    trades = SandboxTrades.query.filter(
        SandboxTrades.trade_timestamp >= start_dt,
        SandboxTrades.trade_timestamp <= end_dt
    ).all()
    
    # Filter for options strategies (check strategy name or symbol)
    options_strategies = [
        'Option Straddle', 'Option Strangle', 'Option Iron Condor', 'Option Iron Butterfly',
        'Option Bull Call Spread', 'Option Bear Put Spread', 'Option Calendar Spread',
        'Option Covered Call', 'Option Protective Put'
    ]
    
    strategy_stats = defaultdict(lambda: {
        'trades': 0, 'buy_value': 0, 'sell_value': 0, 'pnl': 0, 'buy_count': 0, 'sell_count': 0,
        'symbols': set()
    })
    
    options_trades_found = 0
    
    for trade in trades:
        strategy = trade.strategy or 'Unknown'
        
        # Check if this is an options strategy
        is_options_strategy = False
        if strategy in options_strategies:
            is_options_strategy = True
        elif 'Option' in strategy or 'option' in strategy.lower():
            is_options_strategy = True
        elif trade.symbol and (trade.symbol.endswith('CE') or trade.symbol.endswith('PE')):
            is_options_strategy = True
        
        if is_options_strategy:
            options_trades_found += 1
            value = float(trade.price) * trade.quantity
            strategy_stats[strategy]['symbols'].add(trade.symbol)
            
            if trade.action == 'BUY':
                strategy_stats[strategy]['trades'] += 1
                strategy_stats[strategy]['buy_value'] += value
                strategy_stats[strategy]['buy_count'] += 1
            else:  # SELL
                strategy_stats[strategy]['trades'] += 1
                strategy_stats[strategy]['sell_value'] += value
                strategy_stats[strategy]['sell_count'] += 1
    
    # Convert sets to lists for JSON serialization
    for strategy in strategy_stats:
        strategy_stats[strategy]['symbols'] = list(strategy_stats[strategy]['symbols'])
    
    # Calculate PnL
    for strategy, stats in strategy_stats.items():
        stats['pnl'] = stats['sell_value'] - stats['buy_value']
        stats['pnl_percent'] = (stats['pnl'] / stats['buy_value'] * 100) if stats['buy_value'] > 0 else 0
    
    print(f"DEBUG: Found {options_trades_found} options strategy trades")
    print(f"DEBUG: Options strategies found: {list(strategy_stats.keys())}")
    
    return dict(strategy_stats)

def run_options_backtest_analysis():
    """Run comprehensive backtest analysis for options strategies"""
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).date()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=7)
    month_start = today - timedelta(days=30)
    
    print("="*70)
    print("OPTIONS STRATEGIES HISTORICAL BACKTEST ANALYSIS")
    print("="*70)
    print(f"Analysis Date: {datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"Mode: Paper Trading (Analyze Mode)")
    print("="*70)
    
    periods = [
        ("CURRENT DAY", today, today),
        ("PREVIOUS DAY", yesterday, yesterday),
        ("PREVIOUS WEEK", week_start, today),
        ("CURRENT MONTH", month_start, today)
    ]
    
    all_results = {}
    
    for period_name, start_date, end_date in periods:
        print(f"\n{'='*70}")
        print(f"ANALYZING OPTIONS STRATEGIES: {period_name} ({start_date} to {end_date})")
        print(f"{'='*70}")
        
        # Analyze options strategies trades for this period
        stats = analyze_options_strategies_for_period(start_date, end_date)
        
        if stats:
            print(f"\nOptions Strategy Performance ({period_name}):")
            print("-" * 70)
            print(f"{'Strategy':<40} | {'Trades':>6} | {'PnL':>15} | {'PnL %':>10} | {'Status':>12}")
            print("-" * 70)
            
            # Sort by PnL
            sorted_stats = sorted(stats.items(), key=lambda x: x[1]['pnl'], reverse=True)
            
            profitable = []
            losing = []
            
            for strategy, data in sorted_stats:
                status = "PROFITABLE" if data['pnl'] > 0 else "LOSING"
                pnl_sign = "+" if data['pnl'] >= 0 else ""
                print(f"{strategy:<40} | {data['trades']:>6} | {pnl_sign}Rs{data['pnl']:>13.2f} | {pnl_sign}{data['pnl_percent']:>9.2f}% | {status:>12}")
                
                if data['pnl'] > 0:
                    profitable.append((strategy, data))
                else:
                    losing.append((strategy, data))
            
            all_results[period_name] = {
                'profitable': profitable,
                'losing': losing,
                'total_strategies': len(stats),
                'total_trades': sum(s['trades'] for s in stats.values())
            }
            
            print(f"\nSummary:")
            print(f"  Total Options Strategies: {len(stats)}")
            print(f"  Profitable: {len(profitable)}")
            print(f"  Losing: {len(losing)}")
            print(f"  Total Trades: {sum(s['trades'] for s in stats.values())}")
        else:
            print(f"  No options strategy trades found for {period_name}")
            all_results[period_name] = {
                'profitable': [],
                'losing': [],
                'total_strategies': 0,
                'total_trades': 0
            }
    
    # Overall Summary
    print(f"\n{'='*70}")
    print("OVERALL OPTIONS STRATEGIES SUMMARY")
    print(f"{'='*70}")
    
    overall_profitable = set()
    overall_losing = set()
    
    for period_name, results in all_results.items():
        for strategy, _ in results['profitable']:
            overall_profitable.add(strategy)
        for strategy, _ in results['losing']:
            overall_losing.add(strategy)
    
    print(f"\nOptions strategies that were profitable in at least one period: {len(overall_profitable)}")
    for strategy in sorted(overall_profitable):
        print(f"  + {strategy}")
    
    print(f"\nOptions strategies that were losing in at least one period: {len(overall_losing)}")
    for strategy in sorted(overall_losing):
        print(f"  - {strategy}")
    
    # Period-wise summary
    print(f"\n{'='*70}")
    print("PERIOD-WISE OPTIONS STRATEGIES SUMMARY")
    print(f"{'='*70}")
    print(f"{'Period':<20} | {'Total':>6} | {'Profitable':>10} | {'Losing':>8} | {'Trades':>8}")
    print("-" * 70)
    for period_name, results in all_results.items():
        print(f"{period_name:<20} | {results['total_strategies']:>6} | {len(results['profitable']):>10} | {len(results['losing']):>8} | {results['total_trades']:>8}")
    
    print(f"\n{'='*70}")
    print("OPTIONS STRATEGIES ANALYSIS COMPLETE")
    print(f"{'='*70}")

if __name__ == "__main__":
    with app.app_context():
        run_options_backtest_analysis()


