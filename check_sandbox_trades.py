#!/usr/bin/env python
"""
Check Sandbox Trades
Quick script to see what trades exist in the sandbox database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from database.sandbox_db import SandboxTrades, db_session
from datetime import datetime, timedelta
import pytz
from collections import defaultdict

def check_sandbox_trades():
    """Check all trades in sandbox database"""
    with app.app_context():
        ist = pytz.timezone('Asia/Kolkata')
        
        # Get all trades
        all_trades = SandboxTrades.query.order_by(SandboxTrades.trade_timestamp.desc()).all()
        
        print("="*70)
        print("SANDBOX TRADES ANALYSIS")
        print("="*70)
        print(f"Total trades in database: {len(all_trades)}")
        print(f"Analysis time: {datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}")
        print("="*70)
        
        if not all_trades:
            print("\nNo trades found in sandbox database.")
            return
        
        # Group by strategy
        strategy_trades = defaultdict(list)
        for trade in all_trades:
            strategy = trade.strategy or 'Unknown'
            strategy_trades[strategy].append(trade)
        
        print(f"\nStrategies with trades: {len(strategy_trades)}")
        print("-" * 70)
        print(f"{'Strategy':<40} | {'Trades':>6} | {'First Trade':>20} | {'Last Trade':>20}")
        print("-" * 70)
        
        for strategy, trades in sorted(strategy_trades.items(), key=lambda x: len(x[1]), reverse=True):
            first_trade = min(trades, key=lambda t: t.trade_timestamp)
            last_trade = max(trades, key=lambda t: t.trade_timestamp)
            print(f"{strategy:<40} | {len(trades):>6} | {first_trade.trade_timestamp.strftime('%Y-%m-%d %H:%M:%S'):>20} | {last_trade.trade_timestamp.strftime('%Y-%m-%d %H:%M:%S'):>20}")
        
        # Check for options strategies
        print("\n" + "="*70)
        print("OPTIONS STRATEGIES CHECK")
        print("="*70)
        
        options_strategies = []
        options_trades = []
        
        for strategy, trades in strategy_trades.items():
            if 'Option' in strategy or 'option' in strategy.lower():
                options_strategies.append(strategy)
                options_trades.extend(trades)
        
        if options_strategies:
            print(f"\nFound {len(options_strategies)} options strategies:")
            for strategy in options_strategies:
                print(f"  - {strategy}: {len(strategy_trades[strategy])} trades")
        else:
            print("\nNo options strategies found in trades.")
            print("Checking for option symbols (CE/PE)...")
            
            option_symbol_trades = [t for t in all_trades if t.symbol and (t.symbol.endswith('CE') or t.symbol.endswith('PE'))]
            if option_symbol_trades:
                print(f"Found {len(option_symbol_trades)} trades with option symbols (CE/PE)")
                symbol_strategies = defaultdict(int)
                for trade in option_symbol_trades:
                    strategy = trade.strategy or 'Unknown'
                    symbol_strategies[strategy] += 1
                
                print("\nStrategies trading option symbols:")
                for strategy, count in sorted(symbol_strategies.items(), key=lambda x: x[1], reverse=True):
                    print(f"  - {strategy}: {count} trades")
            else:
                print("No trades with option symbols found.")
        
        # Recent trades (last 7 days)
        print("\n" + "="*70)
        print("RECENT TRADES (Last 7 days)")
        print("="*70)
        
        week_ago = datetime.now(ist) - timedelta(days=7)
        recent_trades = [t for t in all_trades if t.trade_timestamp >= week_ago]
        
        if recent_trades:
            recent_by_strategy = defaultdict(int)
            for trade in recent_trades:
                strategy = trade.strategy or 'Unknown'
                recent_by_strategy[strategy] += 1
            
            print(f"\nTotal recent trades: {len(recent_trades)}")
            for strategy, count in sorted(recent_by_strategy.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {strategy}: {count} trades")
        else:
            print("\nNo trades in the last 7 days.")
        
        print("\n" + "="*70)
        print("ANALYSIS COMPLETE")
        print("="*70)

if __name__ == "__main__":
    check_sandbox_trades()










