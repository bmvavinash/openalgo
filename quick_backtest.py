#!/usr/bin/env python
"""
Quick Backtest - Direct database query
Works without Flask app context by directly accessing SQLite
"""
import sys
import os
import sqlite3
from datetime import datetime, timedelta
import pytz
from collections import defaultdict

# Direct path to sandbox database
SANDBOX_DB_PATH = os.path.join(os.path.dirname(__file__), 'db', 'sandbox.db')

def run_quick_analysis():
    """Run analysis by directly querying SQLite database"""
    if not os.path.exists(SANDBOX_DB_PATH):
        print(f"ERROR: Sandbox database not found at {SANDBOX_DB_PATH}")
        return
    
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).date()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=7)
    month_start = today - timedelta(days=30)
    days_7_start = today - timedelta(days=7)
    days_14_start = today - timedelta(days=14)
    
    print("="*70)
    print("COMPREHENSIVE HISTORICAL BACKTEST ANALYSIS")
    print("="*70)
    print(f"Analysis Date: {datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"Mode: Paper Trading (Analyze Mode)")
    print("="*70)
    
    periods = [
        ("CURRENT DAY", today, today),
        ("PREVIOUS DAY", yesterday, yesterday),
        ("LAST 7 DAYS", days_7_start, today),
        ("LAST 14 DAYS", days_14_start, today),
        ("PREVIOUS WEEK", week_start, today),
        ("CURRENT MONTH", month_start, today)
    ]
    
    conn = sqlite3.connect(SANDBOX_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    all_results = {}
    
    for period_name, start_date, end_date in periods:
        print(f"\n{'='*70}")
        print(f"ANALYZING: {period_name} ({start_date} to {end_date})")
        print(f"{'='*70}")
        
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=ist)
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=ist)
        
        # Query trades
        cursor.execute("""
            SELECT strategy, action, price, quantity, symbol, trade_timestamp
            FROM sandbox_trades
            WHERE trade_timestamp >= ? AND trade_timestamp <= ?
            ORDER BY trade_timestamp
        """, (start_dt.isoformat(), end_dt.isoformat()))
        
        trades = cursor.fetchall()
        print(f"Found {len(trades)} trades in this period")
        
        if not trades:
            print(f"  No trades found for {period_name}")
            all_results[period_name] = {
                'profitable': [],
                'losing': [],
                'total_strategies': 0,
                'total_trades': 0
            }
            continue
        
        strategy_stats = defaultdict(lambda: {
            'trades': 0, 'buy_value': 0, 'sell_value': 0, 'pnl': 0, 
            'buy_count': 0, 'sell_count': 0, 'symbols': set()
        })
        
        for trade in trades:
            strategy = trade['strategy'] or 'Unknown'
            value = float(trade['price']) * trade['quantity']
            strategy_stats[strategy]['symbols'].add(trade['symbol'] or '')
            
            if trade['action'] == 'BUY':
                strategy_stats[strategy]['trades'] += 1
                strategy_stats[strategy]['buy_value'] += value
                strategy_stats[strategy]['buy_count'] += 1
            else:  # SELL
                strategy_stats[strategy]['trades'] += 1
                strategy_stats[strategy]['sell_value'] += value
                strategy_stats[strategy]['sell_count'] += 1
        
        # Calculate PnL
        for strategy, stats in strategy_stats.items():
            stats['pnl'] = stats['sell_value'] - stats['buy_value']
            stats['pnl_percent'] = (stats['pnl'] / stats['buy_value'] * 100) if stats['buy_value'] > 0 else 0
            stats['symbols'] = list(stats['symbols'])
        
        if strategy_stats:
            print(f"\nStrategy Performance ({period_name}):")
            print("-" * 100)
            print(f"{'Strategy':<40} | {'Type':<10} | {'Trades':>6} | {'PnL':>15} | {'PnL %':>10} | {'Status':>12}")
            print("-" * 100)
            
            sorted_stats = sorted(strategy_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)
            
            profitable = []
            losing = []
            
            for strategy, data in sorted_stats:
                # Determine strategy type
                strategy_type = 'INTRADAY'
                if 'Option' in strategy or 'option' in strategy.lower():
                    strategy_type = 'OPTIONS'
                elif data['symbols']:
                    for sym in data['symbols']:
                        if sym and (sym.endswith('CE') or sym.endswith('PE')):
                            strategy_type = 'OPTIONS'
                            break
                
                status = "PROFITABLE" if data['pnl'] > 0 else "LOSING"
                pnl_sign = "+" if data['pnl'] >= 0 else ""
                print(f"{strategy:<40} | {strategy_type:<10} | {data['trades']:>6} | {pnl_sign}Rs{data['pnl']:>13.2f} | {pnl_sign}{data['pnl_percent']:>9.2f}% | {status:>12}")
                
                if data['pnl'] > 0:
                    profitable.append((strategy, data, strategy_type))
                else:
                    losing.append((strategy, data, strategy_type))
            
            all_results[period_name] = {
                'profitable': profitable,
                'losing': losing,
                'total_strategies': len(strategy_stats),
                'total_trades': sum(s['trades'] for s in strategy_stats.values())
            }
            
            print(f"\nSummary:")
            print(f"  Total Strategies: {len(strategy_stats)}")
            print(f"  Profitable: {len(profitable)}")
            print(f"  Losing: {len(losing)}")
            print(f"  Total Trades: {sum(s['trades'] for s in strategy_stats.values())}")
        else:
            all_results[period_name] = {
                'profitable': [],
                'losing': [],
                'total_strategies': 0,
                'total_trades': 0
            }
    
    conn.close()
    
    # Overall Summary
    print(f"\n{'='*70}")
    print("OVERALL SUMMARY")
    print(f"{'='*70}")
    
    overall_profitable = set()
    overall_losing = set()
    options_profitable = set()
    options_losing = set()
    intraday_profitable = set()
    intraday_losing = set()
    
    for period_name, results in all_results.items():
        for strategy, data, stype in results['profitable']:
            overall_profitable.add(strategy)
            if stype == 'OPTIONS':
                options_profitable.add(strategy)
            else:
                intraday_profitable.add(strategy)
        for strategy, data, stype in results['losing']:
            overall_losing.add(strategy)
            if stype == 'OPTIONS':
                options_losing.add(strategy)
            else:
                intraday_losing.add(strategy)
    
    print(f"\nAll Strategies - Profitable in at least one period: {len(overall_profitable)}")
    for strategy in sorted(overall_profitable):
        strategy_type = "OPTIONS" if ('Option' in strategy or 'option' in strategy.lower()) else "INTRADAY"
        print(f"  + [{strategy_type}] {strategy}")
    
    print(f"\nAll Strategies - Losing in at least one period: {len(overall_losing)}")
    for strategy in sorted(overall_losing):
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
    
    # Period-wise summary
    print(f"\n{'='*70}")
    print("PERIOD-WISE SUMMARY")
    print(f"{'='*70}")
    print(f"{'Period':<20} | {'Total':>6} | {'Profitable':>10} | {'Losing':>8} | {'Trades':>8}")
    print("-" * 70)
    for period_name, results in all_results.items():
        print(f"{period_name:<20} | {results['total_strategies']:>6} | {len(results['profitable']):>10} | {len(results['losing']):>8} | {results['total_trades']:>8}")
    
    print(f"\n{'='*70}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*70}")

if __name__ == "__main__":
    run_quick_analysis()










