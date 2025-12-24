#!/usr/bin/env python3
"""
Comprehensive Options Strategy Analysis
Analyzes ALL options strategies across multiple time periods
Automatically optimizes poorly performing strategies
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import os
import json
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("ERROR: yfinance not installed. Install with: pip install yfinance pandas")
    sys.exit(1)

# Import analysis functions from historical_strategy_analysis
from historical_strategy_analysis import (
    get_historical_data, calculate_strike, analyze_bear_put_spread,
    analyze_iron_condor, analyze_straddle, analyze_bull_call_spread
)

def analyze_strangle(symbol, exchange, start_date, end_date, strike_int=50, otm_level=2, action="BUY"):
    """Analyze Strangle strategy performance"""
    print(f"\nAnalyzing {action} Strangle for {symbol} ({exchange})")
    print(f"Configuration: {action} OTM{otm_level} Call + {action} OTM{otm_level} Put")
    print(f"Period: {start_date} to {end_date}")
    
    df = get_historical_data(symbol, exchange, start_date, end_date)
    if df is None or df.empty:
        print(f"  [WARNING] No historical data available for {symbol}")
        return None
    
    print(f"  Found {len(df)} data points")
    
    start_ltp = df['close'].iloc[0]
    end_ltp = df['close'].iloc[-1]
    
    call_strike = calculate_strike(start_ltp, f"OTM{otm_level}", "CE", strike_int)
    put_strike = calculate_strike(start_ltp, f"OTM{otm_level}", "PE", strike_int)
    
    print(f"  Entry LTP: Rs {start_ltp:,.2f}")
    print(f"  Call Strike (OTM{otm_level}): Rs {call_strike:,.2f}")
    print(f"  Put Strike (OTM{otm_level}): Rs {put_strike:,.2f}")
    
    estimated_premium = (call_strike + put_strike) * 0.015  # Lower than straddle
    
    call_intrinsic = max(0, end_ltp - call_strike)
    put_intrinsic = max(0, put_strike - end_ltp)
    total_intrinsic = call_intrinsic + put_intrinsic
    
    if action.upper() == "BUY":
        pnl = total_intrinsic - estimated_premium
    else:  # SELL
        pnl = estimated_premium - total_intrinsic
    
    price_move_pct = max(abs((end_ltp - call_strike) / call_strike * 100),
                        abs((end_ltp - put_strike) / put_strike * 100))
    
    if action.upper() == "BUY":
        if price_move_pct > 1.5:
            scenario = "Profitable"
        else:
            scenario = "Loss"
    else:  # SELL
        if price_move_pct < 1.5:
            scenario = "Profitable"
        else:
            scenario = "Loss"
    
    print(f"  Exit LTP: Rs {end_ltp:,.2f}")
    print(f"  Scenario: {scenario}")
    print(f"  Estimated P&L: Rs {pnl:,.2f}")
    
    return {
        'strategy': f'{action} Strangle',
        'symbol': symbol,
        'exchange': exchange,
        'start_price': float(start_ltp),
        'end_price': float(end_ltp),
        'call_strike': float(call_strike),
        'put_strike': float(put_strike),
        'estimated_pnl': float(pnl),
        'scenario': scenario,
        'price_change_pct': float((end_ltp - start_ltp) / start_ltp * 100),
        'start_date': start_date,
        'end_date': end_date
    }

def analyze_iron_butterfly(symbol, exchange, start_date, end_date, strike_int=50, wing_otm=5):
    """Analyze Iron Butterfly strategy performance"""
    print(f"\nAnalyzing Iron Butterfly for {symbol} ({exchange})")
    print(f"Configuration: Sell ATM Call/Put, Buy OTM{wing_otm} Call/Put")
    print(f"Period: {start_date} to {end_date}")
    
    df = get_historical_data(symbol, exchange, start_date, end_date)
    if df is None or df.empty:
        print(f"  [WARNING] No historical data available for {symbol}")
        return None
    
    print(f"  Found {len(df)} data points")
    
    start_ltp = df['close'].iloc[0]
    end_ltp = df['close'].iloc[-1]
    
    atm_strike = calculate_strike(start_ltp, "ATM", "CE", strike_int)
    call_wing = calculate_strike(start_ltp, f"OTM{wing_otm}", "CE", strike_int)
    put_wing = calculate_strike(start_ltp, f"OTM{wing_otm}", "PE", strike_int)
    
    print(f"  Entry LTP: Rs {start_ltp:,.2f}")
    print(f"  ATM Strike: Rs {atm_strike:,.2f}")
    print(f"  Call Wing (OTM{wing_otm}): Rs {call_wing:,.2f}")
    print(f"  Put Wing (OTM{wing_otm}): Rs {put_wing:,.2f}")
    
    spread_width = call_wing - atm_strike
    estimated_net_premium = spread_width * 0.4
    
    # Calculate P&L
    if end_ltp == atm_strike:
        pnl = estimated_net_premium
        scenario = "Max Profit"
    elif end_ltp <= put_wing or end_ltp >= call_wing:
        pnl = -spread_width + estimated_net_premium
        scenario = "Max Loss"
    else:
        # Partial P&L
        if end_ltp < atm_strike:
            intrinsic_put = atm_strike - end_ltp
            pnl = estimated_net_premium - intrinsic_put
        else:
            intrinsic_call = end_ltp - atm_strike
            pnl = estimated_net_premium - intrinsic_call
        scenario = "Partial Loss"
    
    print(f"  Exit LTP: Rs {end_ltp:,.2f}")
    print(f"  Scenario: {scenario}")
    print(f"  Estimated P&L: Rs {pnl:,.2f}")
    
    return {
        'strategy': 'Iron Butterfly',
        'symbol': symbol,
        'exchange': exchange,
        'start_price': float(start_ltp),
        'end_price': float(end_ltp),
        'atm_strike': float(atm_strike),
        'call_wing': float(call_wing),
        'put_wing': float(put_wing),
        'estimated_pnl': float(pnl),
        'scenario': scenario,
        'price_change_pct': float((end_ltp - start_ltp) / start_ltp * 100),
        'start_date': start_date,
        'end_date': end_date
    }

def get_period_dates(period_name, today=None):
    """Get start and end dates for different periods"""
    if today is None:
        today = datetime.now().date()
    
    if period_name == "current_day":
        return today, today, "Current Day"
    
    elif period_name == "previous_day":
        prev_day = today - timedelta(days=1)
        # Skip weekends
        while prev_day.weekday() >= 5:
            prev_day -= timedelta(days=1)
        return prev_day, prev_day, "Previous Day"
    
    elif period_name == "current_week":
        # Get Monday of current week
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        # If today is weekend, use previous week
        if today.weekday() >= 5:
            week_start = today - timedelta(days=today.weekday() + 2)
        week_end = min(today, week_start + timedelta(days=4))
        return week_start, week_end, "Current Week"
    
    elif period_name == "previous_week":
        # Find last Friday
        days_back = (today.weekday() - 4) % 7
        if days_back == 0:
            days_back = 7
        last_friday = today - timedelta(days=days_back)
        week_start = last_friday - timedelta(days=4)
        week_end = last_friday
        return week_start, week_end, "Previous Week"
    
    elif period_name == "current_month":
        month_start = today.replace(day=1)
        month_end = today
        return month_start, month_end, "Current Month"
    
    elif period_name == "six_months":
        six_months_ago = today - timedelta(days=180)
        return six_months_ago, today, "6 Months"
    
    else:
        return today, today, "Unknown"

def optimize_strategy(strategy_name, symbol, exchange, start_date, end_date, 
                     initial_result, strike_int=50, max_iterations=5):
    """
    Optimize a strategy by adjusting parameters if it's losing money
    Iterates multiple times until profitable or max iterations reached
    Returns optimized result and parameters
    """
    if initial_result is None or initial_result.get('estimated_pnl', 0) >= 0:
        return initial_result, None
    
    # Convert dates to strings if needed
    if isinstance(start_date, (datetime, type(datetime.now().date()))):
        start_date_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)
    else:
        start_date_str = str(start_date)
    
    if isinstance(end_date, (datetime, type(datetime.now().date()))):
        end_date_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)
    else:
        end_date_str = str(end_date)
    
    print(f"\n{'='*80}")
    print(f"OPTIMIZING {strategy_name.upper()}")
    print(f"{'='*80}")
    print(f"Initial P&L: Rs {initial_result.get('estimated_pnl', 0):,.2f}")
    
    strategy_lower = strategy_name.lower()
    best_result = initial_result
    best_params = None
    iteration = 0
    
    # Strategy-specific optimization with iteration
    while iteration < max_iterations and best_result.get('estimated_pnl', 0) < 0:
        iteration += 1
        print(f"\n  Iteration {iteration}/{max_iterations}:")
        
        if 'straddle' in strategy_lower and 'buy' in strategy_lower:
            # Try Sell Straddle instead
            print("    Trying Sell Straddle instead...")
            result = analyze_straddle(symbol, exchange, start_date_str, end_date_str, strike_int, "SELL")
            if result and result.get('estimated_pnl', 0) > best_result.get('estimated_pnl', 0):
                print(f"    [IMPROVED] P&L: Rs {best_result.get('estimated_pnl', 0):,.2f} -> Rs {result.get('estimated_pnl', 0):,.2f}")
                best_result = result
                best_params = {'action': 'SELL'}
                if result.get('estimated_pnl', 0) >= 0:
                    print(f"    [SUCCESS] Strategy is now profitable!")
                    break
        
        elif 'strangle' in strategy_lower and 'buy' in strategy_lower:
            # Try Sell Strangle instead
            print("    Trying Sell Strangle instead...")
            result = analyze_strangle(symbol, exchange, start_date_str, end_date_str, strike_int, 2, "SELL")
            if result and result.get('estimated_pnl', 0) > best_result.get('estimated_pnl', 0):
                print(f"    [IMPROVED] P&L: Rs {best_result.get('estimated_pnl', 0):,.2f} -> Rs {result.get('estimated_pnl', 0):,.2f}")
                best_result = result
                best_params = {'action': 'SELL'}
                if result.get('estimated_pnl', 0) >= 0:
                    print(f"    [SUCCESS] Strategy is now profitable!")
                    break
        
        elif 'bull call spread' in strategy_lower:
            # Try different offsets
            improvements_found = False
            for buy_offset in ['ITM1', 'ATM', 'OTM1']:
                for sell_otm in [3, 4, 6]:
                    print(f"    Trying Buy {buy_offset} Call, Sell OTM{sell_otm} Call...")
                    try:
                        result = analyze_bull_call_spread(symbol, exchange, start_date_str, end_date_str,
                                                          strike_int, buy_offset, sell_otm)
                        if result and result.get('estimated_pnl', 0) > best_result.get('estimated_pnl', 0):
                            print(f"    [IMPROVED] P&L: Rs {best_result.get('estimated_pnl', 0):,.2f} -> Rs {result.get('estimated_pnl', 0):,.2f}")
                            best_result = result
                            best_params = {'buy_offset': buy_offset, 'sell_otm': sell_otm}
                            improvements_found = True
                            if result.get('estimated_pnl', 0) >= 0:
                                print(f"    [SUCCESS] Strategy is now profitable!")
                                break
                    except:
                        pass
                if best_result.get('estimated_pnl', 0) >= 0:
                    break
            if not improvements_found:
                break
        
        elif 'iron condor' in strategy_lower:
            # Try different OTM levels
            improvements_found = False
            for sell_otm in [2, 3, 4]:
                for buy_otm in [5, 7, 10]:
                    print(f"    Trying Sell OTM{sell_otm}, Buy OTM{buy_otm}...")
                    try:
                        result = analyze_iron_condor(symbol, exchange, start_date_str, end_date_str,
                                                    strike_int, sell_otm, buy_otm)
                        if result and result.get('estimated_pnl', 0) > best_result.get('estimated_pnl', 0):
                            print(f"    [IMPROVED] P&L: Rs {best_result.get('estimated_pnl', 0):,.2f} -> Rs {result.get('estimated_pnl', 0):,.2f}")
                            best_result = result
                            best_params = {'sell_otm': sell_otm, 'buy_otm': buy_otm}
                            improvements_found = True
                            if result.get('estimated_pnl', 0) >= 0:
                                print(f"    [SUCCESS] Strategy is now profitable!")
                                break
                    except:
                        pass
                if best_result.get('estimated_pnl', 0) >= 0:
                    break
            if not improvements_found:
                break
        
        else:
            # No optimization available for this strategy type
            break
    
    if best_result.get('estimated_pnl', 0) >= 0:
        print(f"\n  [SUCCESS] Optimized {strategy_name} to profitable: Rs {best_result.get('estimated_pnl', 0):,.2f}")
    elif best_result != initial_result:
        print(f"\n  [PARTIAL] Improved {strategy_name} but still negative: Rs {best_result.get('estimated_pnl', 0):,.2f}")
    else:
        print(f"\n  [INFO] Could not optimize {strategy_name} further")
    
    return best_result, best_params

def analyze_all_strategies(symbol, exchange, start_date, end_date, strike_int=50, optimize=True):
    """Analyze all options strategies"""
    results = {}
    
    strategies = [
        {
            'name': 'Bear Put Spread',
            'func': analyze_bear_put_spread,
            'params': {'strike_int': strike_int, 'buy_offset': 'ITM2', 'sell_otm': 5}
        },
        {
            'name': 'Bull Call Spread',
            'func': analyze_bull_call_spread,
            'params': {'strike_int': strike_int, 'buy_offset': 'ITM2', 'sell_otm': 5}
        },
        {
            'name': 'Iron Condor',
            'func': analyze_iron_condor,
            'params': {'strike_int': strike_int, 'sell_otm': 1, 'buy_otm': 3}
        },
        {
            'name': 'Iron Butterfly',
            'func': analyze_iron_butterfly,
            'params': {'strike_int': strike_int, 'wing_otm': 5}
        },
        {
            'name': 'Buy Straddle',
            'func': analyze_straddle,
            'params': {'strike_int': strike_int, 'action': 'BUY'}
        },
        {
            'name': 'Sell Straddle',
            'func': analyze_straddle,
            'params': {'strike_int': strike_int, 'action': 'SELL'}
        },
        {
            'name': 'Buy Strangle',
            'func': analyze_strangle,
            'params': {'strike_int': strike_int, 'otm_level': 2, 'action': 'BUY'}
        },
        {
            'name': 'Sell Strangle',
            'func': analyze_strangle,
            'params': {'strike_int': strike_int, 'otm_level': 2, 'action': 'SELL'}
        },
    ]
    
    for strategy in strategies:
        try:
            result = strategy['func'](
                symbol, exchange,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                **strategy['params']
            )
            
            if result:
                # Optimize if losing money
                if optimize and result.get('estimated_pnl', 0) < 0:
                    optimized_result, optimized_params = optimize_strategy(
                        strategy['name'], symbol, exchange, start_date, end_date,
                        result, strike_int
                    )
                    if optimized_result != result:
                        result = optimized_result
                        result['optimized'] = True
                        result['optimized_params'] = optimized_params
                    else:
                        result['optimized'] = False
                else:
                    result['optimized'] = False
                
                results[strategy['name']] = result
        except Exception as e:
            print(f"  [ERROR] Failed to analyze {strategy['name']}: {e}")
            import traceback
            traceback.print_exc()
    
    return results

def generate_report(all_results, output_file="options_analysis_report.txt"):
    """Generate comprehensive analysis report"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("COMPREHENSIVE OPTIONS STRATEGY ANALYSIS REPORT\n")
        f.write("="*100 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Summary by period
        f.write("="*100 + "\n")
        f.write("SUMMARY BY PERIOD\n")
        f.write("="*100 + "\n\n")
        
        for period_name, results in all_results.items():
            f.write(f"\n{period_name.upper().replace('_', ' ')}\n")
            f.write("-" * 100 + "\n")
            
            if not results:
                f.write("  No data available\n\n")
                continue
            
            # Sort by P&L
            sorted_results = sorted(results.items(), 
                                  key=lambda x: x[1].get('estimated_pnl', 0), 
                                  reverse=True)
            
            f.write(f"{'Strategy':<30} {'P&L':<15} {'Scenario':<20} {'Optimized':<10}\n")
            f.write("-" * 100 + "\n")
            
            total_pnl = 0
            profitable_count = 0
            
            for strategy_name, result in sorted_results:
                pnl = result.get('estimated_pnl', 0)
                scenario = result.get('scenario', 'N/A')
                optimized = 'Yes' if result.get('optimized', False) else 'No'
                total_pnl += pnl
                if pnl > 0:
                    profitable_count += 1
                
                f.write(f"{strategy_name:<30} Rs {pnl:>12,.2f} {scenario:<20} {optimized:<10}\n")
            
            f.write("-" * 100 + "\n")
            f.write(f"Total P&L: Rs {total_pnl:>12,.2f}\n")
            f.write(f"Profitable Strategies: {profitable_count}/{len(results)}\n")
            f.write(f"Win Rate: {profitable_count/len(results)*100:.1f}%\n\n")
        
        # Overall statistics
        f.write("\n" + "="*100 + "\n")
        f.write("OVERALL STATISTICS\n")
        f.write("="*100 + "\n\n")
        
        strategy_totals = defaultdict(float)
        strategy_counts = defaultdict(int)
        strategy_wins = defaultdict(int)
        
        for period_results in all_results.values():
            for strategy_name, result in period_results.items():
                pnl = result.get('estimated_pnl', 0)
                strategy_totals[strategy_name] += pnl
                strategy_counts[strategy_name] += 1
                if pnl > 0:
                    strategy_wins[strategy_name] += 1
        
        f.write(f"{'Strategy':<30} {'Total P&L':<15} {'Avg P&L':<15} {'Win Rate':<15}\n")
        f.write("-" * 100 + "\n")
        
        sorted_strategies = sorted(strategy_totals.items(), key=lambda x: x[1], reverse=True)
        
        for strategy_name, total_pnl in sorted_strategies:
            count = strategy_counts[strategy_name]
            wins = strategy_wins[strategy_name]
            avg_pnl = total_pnl / count if count > 0 else 0
            win_rate = (wins / count * 100) if count > 0 else 0
            
            f.write(f"{strategy_name:<30} Rs {total_pnl:>12,.2f} Rs {avg_pnl:>12,.2f} {win_rate:>13.1f}%\n")
    
    print(f"\n[SUCCESS] Report saved to {output_file}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive Options Strategy Analysis')
    parser.add_argument('--symbol', type=str, default='NIFTY', help='Underlying symbol')
    parser.add_argument('--exchange', type=str, default='NSE_INDEX', help='Exchange code')
    parser.add_argument('--strike-int', type=int, default=50, help='Strike interval')
    parser.add_argument('--no-optimize', action='store_true', help='Disable optimization')
    parser.add_argument('--periods', type=str, nargs='+',
                        default=['current_day', 'previous_day', 'current_week', 'previous_week', 
                                'current_month', 'six_months'],
                        help='Periods to analyze')
    
    args = parser.parse_args()
    
    print("\n" + "="*100)
    print("COMPREHENSIVE OPTIONS STRATEGY ANALYSIS")
    print("="*100)
    print(f"\nSymbol: {args.symbol}")
    print(f"Exchange: {args.exchange}")
    print(f"Strike Interval: {args.strike_int}")
    print(f"Optimization: {'Enabled' if not args.no_optimize else 'Disabled'}")
    print(f"Periods: {', '.join(args.periods)}\n")
    
    all_results = {}
    
    for period_name in args.periods:
        print(f"\n{'='*100}")
        print(f"ANALYZING: {period_name.upper().replace('_', ' ')}")
        print(f"{'='*100}\n")
        
        start_date, end_date, period_label = get_period_dates(period_name)
        print(f"Period: {period_label}")
        print(f"Start Date: {start_date}")
        print(f"End Date: {end_date}\n")
        
        results = analyze_all_strategies(
            args.symbol, args.exchange, start_date, end_date,
            args.strike_int, optimize=not args.no_optimize
        )
        
        all_results[period_name] = results
        
        # Print summary for this period
        if results:
            print(f"\n{period_label} Summary:")
            sorted_results = sorted(results.items(), 
                                  key=lambda x: x[1].get('estimated_pnl', 0), 
                                  reverse=True)
            for strategy_name, result in sorted_results[:3]:  # Top 3
                pnl = result.get('estimated_pnl', 0)
                print(f"  {strategy_name}: Rs {pnl:,.2f}")
    
    # Generate comprehensive report
    print(f"\n{'='*100}")
    print("GENERATING COMPREHENSIVE REPORT")
    print(f"{'='*100}\n")
    
    generate_report(all_results)
    
    print("\n" + "="*100)
    print("ANALYSIS COMPLETE")
    print("="*100)

if __name__ == "__main__":
    main()

