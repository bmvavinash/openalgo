#!/usr/bin/env python3
"""
Daily Strategy Analyzer
Runs after market closure to analyze today's performance
Updates strategy categories and buy/sell restrictions
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import os

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from comprehensive_options_analysis import analyze_all_strategies, get_period_dates
from strategy_performance_config import StrategyPerformanceConfig

def analyze_today_performance(symbol='NIFTY', exchange='NSE_INDEX', strike_int=50):
    """
    Analyze today's market performance for all strategies
    Updates performance categories and restrictions
    """
    print("\n" + "="*100)
    print("DAILY STRATEGY PERFORMANCE ANALYSIS")
    print("="*100)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get today's date
    today = datetime.now().date()
    
    # Check if market is closed (after 3:30 PM IST)
    current_time = datetime.now().time()
    market_close_time = datetime.strptime("15:30", "%H:%M").time()
    
    if current_time < market_close_time:
        print(f"[WARNING] Market is still open. Current time: {current_time.strftime('%H:%M')}")
        print(f"         Analysis should run after market close (15:30 IST)")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Analysis cancelled.")
            return
    
    # Initialize config
    config = StrategyPerformanceConfig()
    
    # Analyze current day
    print(f"Analyzing strategies for {today}...")
    results = analyze_all_strategies(
        symbol, exchange, today, today,
        strike_int, optimize=False  # Don't optimize during daily analysis
    )
    
    if not results:
        print("[ERROR] No analysis results obtained")
        return
    
    # Process results and update categories
    print("\n" + "="*100)
    print("UPDATING STRATEGY CATEGORIES")
    print("="*100 + "\n")
    
    buy_sell_analysis = {}
    
    for strategy_name, result in results.items():
        pnl = result.get('estimated_pnl', 0)
        scenario = result.get('scenario', 'Unknown')
        
        # Determine if this is a buy or sell strategy
        strategy_lower = strategy_name.lower()
        is_buy = 'buy' in strategy_lower
        is_sell = 'sell' in strategy_lower
        
        # For strategies that can be both buy and sell, analyze separately
        if 'straddle' in strategy_lower or 'strangle' in strategy_lower:
            # These have separate buy/sell versions
            if is_buy:
                if strategy_name not in buy_sell_analysis:
                    buy_sell_analysis[strategy_name.replace('Buy ', '').replace('BUY ', '')] = {}
                buy_sell_analysis[strategy_name.replace('Buy ', '').replace('BUY ', '')]['buy_pnl'] = pnl
                buy_sell_analysis[strategy_name.replace('Buy ', '').replace('BUY ', '')]['buy_win_rate'] = 100.0 if pnl > 0 else 0.0
            elif is_sell:
                base_name = strategy_name.replace('Sell ', '').replace('SELL ', '')
                if base_name not in buy_sell_analysis:
                    buy_sell_analysis[base_name] = {}
                buy_sell_analysis[base_name]['sell_pnl'] = pnl
                buy_sell_analysis[base_name]['sell_win_rate'] = 100.0 if pnl > 0 else 0.0
        
        # Update performance category
        category = config.update_performance_category(
            strategy_name, pnl, 
            win_rate=100.0 if pnl > 0 else 0.0,
            period="current_day"
        )
        
        print(f"{strategy_name:<30} P&L: Rs {pnl:>10,.2f}  Category: {category:<20}")
    
    # Auto-detect buy/sell restrictions
    if buy_sell_analysis:
        print("\n" + "="*100)
        print("AUTO-DETECTING BUY/SELL RESTRICTIONS")
        print("="*100 + "\n")
        
        config.auto_detect_restrictions(buy_sell_analysis)
    
    # Print summary
    print("\n" + "="*100)
    print("UPDATED CATEGORIES")
    print("="*100 + "\n")
    
    categories = config.get_all_categories()
    for category_name, strategies in categories.items():
        if strategies:
            print(f"{category_name.upper().replace('_', ' ')}: {len(strategies)} strategies")
            for strategy in strategies:
                info = config.get_strategy_info(strategy)
                allowed = config.get_allowed_actions(strategy)
                avg_pnl = info.get('avg_pnl', 0)
                print(f"  - {strategy:<30} Avg P&L: Rs {avg_pnl:>10,.2f}  Allowed: {', '.join(allowed)}")
            print()
    
    print("="*100)
    print("Daily analysis complete!")
    print("="*100)

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Daily Strategy Performance Analyzer')
    parser.add_argument('--symbol', type=str, default='NIFTY', help='Underlying symbol')
    parser.add_argument('--exchange', type=str, default='NSE_INDEX', help='Exchange code')
    parser.add_argument('--strike-int', type=int, default=50, help='Strike interval')
    parser.add_argument('--force', action='store_true', help='Force analysis even if market is open')
    
    args = parser.parse_args()
    
    analyze_today_performance(args.symbol, args.exchange, args.strike_int)

if __name__ == "__main__":
    main()

