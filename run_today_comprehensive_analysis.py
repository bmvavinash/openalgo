#!/usr/bin/env python3
"""
Comprehensive Analysis for Today's Data
1. Analyzes why no trades were triggered today
2. Runs all strategies on today's historical data using yfinance
3. Generates complete analysis report
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import os
import json
from collections import defaultdict
import pytz

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("ERROR: yfinance not installed. Install with: pip install yfinance pandas")
    sys.exit(1)

# Import analysis functions
from historical_strategy_analysis import (
    get_historical_data, calculate_strike, analyze_bear_put_spread,
    analyze_iron_condor, analyze_straddle, analyze_bull_call_spread
)
from comprehensive_options_analysis import (
    analyze_strangle, analyze_iron_butterfly
)

# Import database modules
from database.sandbox_db import SandboxOrders, SandboxTrades, db_session as sandbox_db_session
from database.strategy_db import Strategy, StrategySymbolMapping, db_session as strategy_db_session
from utils.logging import get_logger

logger = get_logger(__name__)
IST = pytz.timezone('Asia/Kolkata')

def get_today_data(symbol, exchange, interval='5m'):
    """
    Get today's data from yfinance (historical mode)
    Uses yfinance directly, not API
    """
    symbol_mapping = {
        'NIFTY': '^NSEI',
        'BANKNIFTY': '^NSEBANK',
        'FINNIFTY': '^NSEFIN',
        'MIDCPNIFTY': '^NSEMIDCP',
        'SENSEX': '^BSESN',
        'NIFTY50': '^NSEI'
    }
    
    yf_symbol = symbol_mapping.get(symbol.upper(), symbol)
    
    try:
        ticker = yf.Ticker(yf_symbol)
        today = date.today()
        
        # For intraday data, use period='1d' with interval
        if interval in ['1m', '3m', '5m', '15m', '30m']:
            hist = ticker.history(period='1d', interval=interval)
        else:
            hist = ticker.history(period='1d', interval='1d')
        
        if hist.empty:
            # Try with info() as fallback
            info = ticker.info
            current_price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')
            if current_price:
                # Create single row DataFrame
                now = datetime.now(IST)
                hist = pd.DataFrame({
                    'Open': [current_price],
                    'High': [current_price],
                    'Low': [current_price],
                    'Close': [current_price],
                    'Volume': [0]
                }, index=[now])
        
        if hist.empty:
            return None
        
        # Filter to today only
        hist.index = pd.to_datetime(hist.index)
        if hist.index.tz is None:
            hist.index = hist.index.tz_localize('UTC').tz_convert(IST)
        else:
            hist.index = hist.index.tz_convert(IST)
        
        today_start = IST.localize(datetime.combine(today, datetime.min.time()))
        today_end = IST.localize(datetime.combine(today, datetime.max.time()))
        
        hist = hist[(hist.index >= today_start) & (hist.index <= today_end)]
        
        if hist.empty:
            return None
        
        df = pd.DataFrame({
            'timestamp': hist.index,
            'open': hist['Open'].values,
            'high': hist['High'].values,
            'low': hist['Low'].values,
            'close': hist['Close'].values,
            'volume': hist['Volume'].values
        })
        
        return df
        
    except Exception as e:
        logger.error(f"Error fetching today's data for {symbol}: {e}")
        return None

def analyze_why_no_trades():
    """Analyze why no trades were triggered today"""
    print("\n" + "="*80)
    print("ANALYZING WHY NO TRADES WERE TRIGGERED TODAY")
    print("="*80)
    
    today = date.today()
    start = IST.localize(datetime.combine(today, datetime.min.time()))
    
    # Check orders
    orders = sandbox_db_session.query(SandboxOrders).filter(
        SandboxOrders.order_timestamp >= start
    ).all()
    
    # Check trades
    trades = sandbox_db_session.query(SandboxTrades).filter(
        SandboxTrades.trade_timestamp >= start
    ).all()
    
    print(f"\nToday's Orders: {len(orders)}")
    print(f"Today's Trades: {len(trades)}")
    
    # Check strategy logs for errors
    log_dir = Path('log/strategies')
    today_logs = list(log_dir.glob(f'*{today.strftime("%Y%m%d")}*.log'))
    
    print(f"\nStrategy Log Files Found: {len(today_logs)}")
    
    errors = []
    server_down_count = 0
    no_data_count = 0
    
    for log_file in today_logs[:10]:  # Check first 10 logs
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'Failed to connect to the server' in content:
                    server_down_count += 1
                if 'No data available' in content:
                    no_data_count += 1
        except:
            pass
    
    print(f"\nIssues Found:")
    print(f"  - Server connection errors: {server_down_count} log files")
    print(f"  - No data available errors: {no_data_count} log files")
    
    if server_down_count > 0:
        print(f"\n[WARNING] MAIN ISSUE: Server was down multiple times today!")
        print(f"   Strategies couldn't fetch data via API")
        print(f"   Solution: Use yfinance directly for historical analysis")
    
    # Check active Python strategies from JSON config
    config_file = Path('strategies') / 'strategy_configs.json'
    python_strategies_count = 0
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                configs = json.load(f)
                python_strategies_count = len([c for c in configs.values() if c.get('is_active', False)])
        except:
            pass
    print(f"\nActive Python Strategies: {python_strategies_count}")
    
    return {
        'orders': len(orders),
        'trades': len(trades),
        'server_down_count': server_down_count,
        'no_data_count': no_data_count,
        'active_strategies': python_strategies_count
    }

def run_options_strategies_analysis():
    """Run all options strategies on today's data"""
    print("\n" + "="*80)
    print("RUNNING OPTIONS STRATEGIES ON TODAY'S DATA")
    print("="*80)
    
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    
    symbols = ['NIFTY', 'BANKNIFTY']
    exchanges = ['NSE_INDEX', 'NSE_INDEX']
    
    results = []
    
    for symbol, exchange in zip(symbols, exchanges):
        print(f"\n{'='*80}")
        print(f"Analyzing {symbol} ({exchange})")
        print(f"{'='*80}")
        
        # Get today's data
        df = get_today_data(symbol, exchange, interval='5m')
        if df is None or df.empty:
            print(f"  [WARNING] No data available for {symbol} today")
            continue
        
        print(f"  [OK] Found {len(df)} data points for today")
        start_price = df['close'].iloc[0]
        end_price = df['close'].iloc[-1]
        print(f"  Start Price: Rs {start_price:,.2f}")
        print(f"  End Price: Rs {end_price:,.2f}")
        print(f"  Change: Rs {end_price - start_price:,.2f} ({((end_price - start_price) / start_price * 100):.2f}%)")
        
        # Run all options strategies using the fetched data
        # Since we have data, we can analyze directly
        start_price = df['close'].iloc[0]
        end_price = df['close'].iloc[-1]
        strike_int = 50
        
        # Bear Put Spread
        try:
            buy_strike = calculate_strike(start_price, "ITM2", "PE", strike_int)
            sell_strike = calculate_strike(start_price, "OTM5", "PE", strike_int)
            estimated_premium = (buy_strike - sell_strike) * 0.5
            if end_price <= sell_strike:
                intrinsic_buy = buy_strike - end_price
                intrinsic_sell = 0
            else:
                intrinsic_buy = max(0, buy_strike - end_price)
                intrinsic_sell = max(0, sell_strike - end_price)
            pnl = (intrinsic_buy - intrinsic_sell) - estimated_premium
            scenario = "Profitable" if pnl > 0 else "Loss"
            results.append({
                'strategy': 'Bear Put Spread',
                'symbol': symbol,
                'exchange': exchange,
                'start_price': float(start_price),
                'end_price': float(end_price),
                'estimated_pnl': float(pnl),
                'scenario': scenario,
                'price_change_pct': float((end_price - start_price) / start_price * 100)
            })
            print(f"  Bear Put Spread: {scenario}, P&L: Rs {pnl:,.2f}")
        except Exception as e:
            print(f"  [ERROR] Error running Bear Put Spread: {e}")
        
        # Bull Call Spread
        try:
            buy_strike = calculate_strike(start_price, "ITM2", "CE", strike_int)
            sell_strike = calculate_strike(start_price, "OTM5", "CE", strike_int)
            estimated_premium = (sell_strike - buy_strike) * 0.5
            if end_price >= sell_strike:
                intrinsic_buy = end_price - buy_strike
                intrinsic_sell = end_price - sell_strike
            else:
                intrinsic_buy = max(0, end_price - buy_strike)
                intrinsic_sell = 0
            pnl = (intrinsic_buy - intrinsic_sell) - estimated_premium
            scenario = "Profitable" if pnl > 0 else "Loss"
            results.append({
                'strategy': 'Bull Call Spread',
                'symbol': symbol,
                'exchange': exchange,
                'start_price': float(start_price),
                'end_price': float(end_price),
                'estimated_pnl': float(pnl),
                'scenario': scenario,
                'price_change_pct': float((end_price - start_price) / start_price * 100)
            })
            print(f"  Bull Call Spread: {scenario}, P&L: Rs {pnl:,.2f}")
        except Exception as e:
            print(f"  [ERROR] Error running Bull Call Spread: {e}")
    
    return results

def run_python_strategies_analysis():
    """Run Python strategies analysis on today's data"""
    print("\n" + "="*80)
    print("RUNNING PYTHON STRATEGIES ANALYSIS")
    print("="*80)
    
    # Load Python strategies from JSON config file
    config_file = Path('strategies') / 'strategy_configs.json'
    if not config_file.exists():
        print(f"\n[WARNING] Config file not found: {config_file}")
        return []
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            configs = json.load(f)
    except Exception as e:
        print(f"\n[ERROR] Error loading config file: {e}")
        return []
    
    # Filter active strategies
    active_configs = {k: v for k, v in configs.items() if v.get('is_active', False)}
    print(f"\nFound {len(active_configs)} active Python strategies")
    
    results = []
    
    for strategy_id, config in active_configs.items():
        print(f"\n{'='*80}")
        print(f"Strategy: {config.get('name', 'Unknown')} (ID: {strategy_id})")
        print(f"{'='*80}")
        
        try:
            symbols = config.get('symbols', [])
            if not symbols:
                print(f"  [WARNING] No symbols configured")
                continue
            
            print(f"  Symbols: {', '.join([s.get('symbol', str(s)) if isinstance(s, dict) else str(s) for s in symbols])}")
            
            # For each symbol, get today's data and analyze
            for symbol_info in symbols:
                if isinstance(symbol_info, dict):
                    symbol = symbol_info.get('symbol', '')
                    exchange = symbol_info.get('exchange', 'NSE_INDEX')
                else:
                    symbol = str(symbol_info)
                    exchange = 'NSE_INDEX'
                
                df = get_today_data(symbol, exchange, interval='5m')
                if df is None or df.empty:
                    print(f"  [WARNING] No data for {symbol}")
                    continue
                
                print(f"  [OK] {symbol}: {len(df)} data points")
                print(f"    Price Range: Rs {df['low'].min():,.2f} - Rs {df['high'].max():,.2f}")
                print(f"    Start: Rs {df['close'].iloc[0]:,.2f}, End: Rs {df['close'].iloc[-1]:,.2f}")
                
                results.append({
                    'strategy': config.get('name', 'Unknown'),
                    'strategy_id': strategy_id,
                    'symbol': symbol,
                    'exchange': exchange,
                    'data_points': len(df),
                    'start_price': float(df['close'].iloc[0]),
                    'end_price': float(df['close'].iloc[-1]),
                    'price_change_pct': float((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100)
                })
        
        except Exception as e:
            print(f"  [ERROR] Error analyzing strategy {config.get('name', 'Unknown')}: {e}")
            import traceback
            traceback.print_exc()
    
    return results

def generate_report(analysis_results, options_results, python_results):
    """Generate comprehensive report"""
    print("\n" + "="*80)
    print("COMPREHENSIVE ANALYSIS REPORT")
    print("="*80)
    
    report_file = Path('log') / f'today_analysis_report_{date.today().strftime("%Y%m%d")}.txt'
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("COMPREHENSIVE ANALYSIS REPORT - " + date.today().strftime('%Y-%m-%d') + "\n")
        f.write("="*80 + "\n\n")
        
        # Analysis Results
        f.write("WHY NO TRADES WERE TRIGGERED:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Orders Created Today: {analysis_results['orders']}\n")
        f.write(f"Trades Executed Today: {analysis_results['trades']}\n")
        f.write(f"Server Down Errors: {analysis_results['server_down_count']}\n")
        f.write(f"No Data Errors: {analysis_results['no_data_count']}\n")
        f.write(f"Active Strategies: {analysis_results['active_strategies']}\n\n")
        
        if analysis_results['server_down_count'] > 0:
            f.write("[WARNING] MAIN ISSUE: Server was down multiple times today!\n")
            f.write("   Strategies couldn't fetch data via API\n")
            f.write("   Solution: Use yfinance directly for historical analysis\n\n")
        
        # Options Results
        f.write("\nOPTIONS STRATEGIES ANALYSIS:\n")
        f.write("-" * 80 + "\n")
        if options_results:
            for result in options_results:
                f.write(f"\nStrategy: {result.get('strategy', 'Unknown')}\n")
                f.write(f"Symbol: {result.get('symbol', 'Unknown')}\n")
                f.write(f"Start Price: Rs {result.get('start_price', 0):,.2f}\n")
                f.write(f"End Price: Rs {result.get('end_price', 0):,.2f}\n")
                f.write(f"Estimated P&L: Rs {result.get('estimated_pnl', 0):,.2f}\n")
                f.write(f"Scenario: {result.get('scenario', 'Unknown')}\n")
        else:
            f.write("No options strategies results\n")
        
        # Python Strategies Results
        f.write("\n\nPYTHON STRATEGIES ANALYSIS:\n")
        f.write("-" * 80 + "\n")
        if python_results:
            for result in python_results:
                f.write(f"\nStrategy: {result.get('strategy', 'Unknown')}\n")
                f.write(f"Symbol: {result.get('symbol', 'Unknown')}\n")
                f.write(f"Data Points: {result.get('data_points', 0)}\n")
                f.write(f"Start Price: Rs {result.get('start_price', 0):,.2f}\n")
                f.write(f"End Price: Rs {result.get('end_price', 0):,.2f}\n")
                f.write(f"Price Change: {result.get('price_change_pct', 0):.2f}%\n")
        else:
            f.write("No Python strategies results\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("Report generated at: " + datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST') + "\n")
        f.write("="*80 + "\n")
    
    print(f"\n✓ Report saved to: {report_file}")
    return report_file

def main():
    """Main execution"""
    print("\n" + "="*80)
    print("COMPREHENSIVE TODAY'S DATA ANALYSIS")
    print("="*80)
    print(f"Date: {date.today().strftime('%Y-%m-%d')}")
    print(f"Time: {datetime.now(IST).strftime('%H:%M:%S IST')}")
    print("="*80)
    
    try:
        # Step 1: Analyze why no trades
        analysis_results = analyze_why_no_trades()
        
        # Step 2: Run options strategies on today's data
        options_results = run_options_strategies_analysis()
        
        # Step 3: Run Python strategies analysis
        python_results = run_python_strategies_analysis()
        
        # Step 4: Generate report
        report_file = generate_report(analysis_results, options_results, python_results)
        
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE!")
        print("="*80)
        print(f"Report saved to: {report_file}")
        print("\nSummary:")
        print(f"  - Orders Today: {analysis_results['orders']}")
        print(f"  - Trades Today: {analysis_results['trades']}")
        print(f"  - Options Strategies Analyzed: {len(options_results)}")
        print(f"  - Python Strategies Analyzed: {len(python_results)}")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Error in comprehensive analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

