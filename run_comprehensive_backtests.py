#!/usr/bin/env python
"""
Comprehensive Historical Backtest Runner
Runs all strategies on historical data for different time periods
Generates detailed analysis showing profitable vs losing strategies
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import pytz
import pandas as pd
from services.history_service import get_history
from database.auth_db import get_api_key_for_tradingview
from database.settings_db import get_analyze_mode
from database.sandbox_db import SandboxTrades, db_session
from collections import defaultdict

def run_strategy_backtest_on_data(strategy_name, df, symbol='NIFTY'):
    """
    Simulate running a strategy on historical data
    This is a simplified version - actual strategies would need to be executed
    """
    if df is None or df.empty or len(df) < 10:
        return None
    
    # Simple simulation: Buy at first close, sell at last close
    # In reality, this would execute the actual strategy logic
    entry_price = df['close'].iloc[0]
    exit_price = df['close'].iloc[-1]
    quantity = 1
    
    pnl = (exit_price - entry_price) * quantity
    pnl_percent = ((exit_price / entry_price) - 1) * 100
    
    return {
        'strategy': strategy_name,
        'symbol': symbol,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'pnl': pnl,
        'pnl_percent': pnl_percent,
        'trades': 1,
        'records_analyzed': len(df)
    }

def analyze_sandbox_trades_for_period(start_date, end_date):
    """Analyze actual trades from sandbox for a period"""
    ist = pytz.timezone('Asia/Kolkata')
    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=ist)
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=ist)
    
    trades = SandboxTrades.query.filter(
        SandboxTrades.trade_timestamp >= start_dt,
        SandboxTrades.trade_timestamp <= end_dt
    ).all()
    
    strategy_stats = defaultdict(lambda: {
        'trades': 0, 'buy_value': 0, 'sell_value': 0, 'pnl': 0, 'buy_count': 0, 'sell_count': 0
    })
    
    for trade in trades:
        strategy = trade.strategy or 'Unknown'
        value = float(trade.price) * trade.quantity
        
        # Debug: Print strategy names to identify options strategies
        if 'Option' in strategy or 'option' in strategy.lower():
            print(f"DEBUG: Found option strategy trade: {strategy}, symbol: {trade.symbol}, action: {trade.action}")
        
        if trade.action == 'BUY':
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
    
    return dict(strategy_stats)

def run_backtest_analysis():
    """Run comprehensive backtest analysis for all periods"""
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).date()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=7)
    month_start = today - timedelta(days=30)
    
    # Get API key
    api_key = get_api_key_for_tradingview('avinash')
    if not api_key:
        print("Error: No API key found")
        return
    
    print("="*70)
    print("COMPREHENSIVE HISTORICAL BACKTEST ANALYSIS")
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
    
    # Also add last 7 days and last 14 days for multi-day analysis
    days_7_start = today - timedelta(days=7)
    days_14_start = today - timedelta(days=14)
    periods.extend([
        ("LAST 7 DAYS", days_7_start, today),
        ("LAST 14 DAYS", days_14_start, today)
    ])
    
    all_results = {}
    
    for period_name, start_date, end_date in periods:
        print(f"\n{'='*70}")
        print(f"ANALYZING: {period_name} ({start_date} to {end_date})")
        print(f"{'='*70}")
        
        # Analyze sandbox trades for this period
        stats = analyze_sandbox_trades_for_period(start_date, end_date)
        
        if stats:
            print(f"\nStrategy Performance ({period_name}):")
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
            print(f"  Total Strategies: {len(stats)}")
            print(f"  Profitable: {len(profitable)}")
            print(f"  Losing: {len(losing)}")
            print(f"  Total Trades: {sum(s['trades'] for s in stats.values())}")
        else:
            print(f"  No trades found for {period_name}")
            all_results[period_name] = {
                'profitable': [],
                'losing': [],
                'total_strategies': 0,
                'total_trades': 0
            }
    
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
        for strategy, _ in results['profitable']:
            overall_profitable.add(strategy)
            if 'Option' in strategy or 'option' in strategy.lower():
                options_profitable.add(strategy)
            else:
                intraday_profitable.add(strategy)
        for strategy, _ in results['losing']:
            overall_losing.add(strategy)
            if 'Option' in strategy or 'option' in strategy.lower():
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
    with app.app_context():
        run_backtest_analysis()










