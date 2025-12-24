#!/usr/bin/env python3
"""
Historical Strategy Analysis using yfinance data
Analyzes how strategies would have performed using historical market data
NOT using DB trades (since options strategies may not have DB records)
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import os

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("ERROR: yfinance not installed. Install with: pip install yfinance")
    sys.exit(1)

def get_historical_data(symbol, exchange, start_date, end_date, interval='5m'):
    """
    Get historical data from yfinance
    
    Args:
        symbol: Trading symbol (e.g., NIFTY, BANKNIFTY)
        exchange: Exchange code (for mapping to yfinance symbols)
        start_date: Start date (datetime or string YYYY-MM-DD)
        end_date: End date (datetime or string YYYY-MM-DD)
        interval: Data interval (1m, 5m, 15m, 1h, 1d)
    
    Returns:
        DataFrame with historical data
    """
    # Map exchange symbols to yfinance symbols
    symbol_mapping = {
        'NIFTY': '^NSEI',
        'BANKNIFTY': '^NSEBANK',
        'FINNIFTY': '^NSEFIN',
        'MIDCPNIFTY': '^NSEMIDCP',
        'SENSEX': '^BSESN',
        'NIFTY50': '^NSEI'
    }
    
    # Convert dates to strings if needed
    if isinstance(start_date, datetime):
        start_date = start_date.strftime('%Y-%m-%d')
    if isinstance(end_date, datetime):
        end_date = end_date.strftime('%Y-%m-%d')
    
    # Get yfinance symbol
    yf_symbol = symbol_mapping.get(symbol.upper(), symbol)
    
    try:
        ticker = yf.Ticker(yf_symbol)
        
        # Map interval
        interval_map = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m',
            '30m': '30m', '1h': '1h', '1d': '1d'
        }
        yf_interval = interval_map.get(interval.lower(), '5m')
        
        # Calculate period
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        days_diff = (end_dt - start_dt).days
        
        # Fetch data
        if yf_interval in ['1m', '3m', '5m', '15m', '30m']:
            if days_diff <= 59:
                hist = ticker.history(period=f'{days_diff + 1}d', interval=yf_interval)
            else:
                limited_start = end_dt - timedelta(days=59)
                hist = ticker.history(interval=yf_interval, start=limited_start.strftime('%Y-%m-%d'), end=end_date)
        else:
            hist = ticker.history(interval=yf_interval, start=start_date, end=end_date)
        
        if hist.empty:
            return None
        
        # Convert to standard format
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
        print(f"Error fetching data for {symbol}: {e}")
        return None

def calculate_strike(ltp, offset, option_type, strike_int):
    """Calculate strike price based on LTP, offset, and option type"""
    atm_strike = round(ltp / strike_int) * strike_int
    offset = offset.upper()
    option_type = option_type.upper()
    
    if offset == "ATM":
        return atm_strike
    elif offset.startswith("ITM"):
        num = int(offset[3:])
        if option_type == "CE":
            return atm_strike - (num * strike_int)
        else:  # PE
            return atm_strike + (num * strike_int)
    elif offset.startswith("OTM"):
        num = int(offset[3:])
        if option_type == "CE":
            return atm_strike + (num * strike_int)
        else:  # PE
            return atm_strike - (num * strike_int)
    else:
        return atm_strike

def analyze_bear_put_spread(symbol, exchange, start_date, end_date, strike_int=50, buy_offset="ITM2", sell_otm=5):
    """Analyze Bear Put Spread strategy performance"""
    print(f"\nAnalyzing Bear Put Spread for {symbol} ({exchange})")
    print(f"Configuration: Buy {buy_offset} Put, Sell OTM{sell_otm} Put")
    print(f"Period: {start_date} to {end_date}")
    
    df = get_historical_data(symbol, exchange, start_date, end_date)
    if df is None or df.empty:
        print(f"  [WARNING] No historical data available for {symbol}")
        return None
    
    print(f"  Found {len(df)} data points")
    
    start_ltp = df['close'].iloc[0]
    end_ltp = df['close'].iloc[-1]
    
    buy_strike = calculate_strike(start_ltp, buy_offset, "PE", strike_int)
    sell_strike = calculate_strike(start_ltp, f"OTM{sell_otm}", "PE", strike_int)
    
    print(f"  Entry LTP: Rs {start_ltp:,.2f}")
    print(f"  Buy Strike (ITM2 Put): Rs {buy_strike:,.2f}")
    print(f"  Sell Strike (OTM{sell_otm} Put): Rs {sell_strike:,.2f}")
    print(f"  Spread Width: Rs {buy_strike - sell_strike:,.2f}")
    
    estimated_net_premium = (buy_strike - sell_strike) * 0.5
    
    if end_ltp <= sell_strike:
        intrinsic_buy = buy_strike - end_ltp
        intrinsic_sell = sell_strike - end_ltp
        pnl = (intrinsic_buy - intrinsic_sell) - estimated_net_premium
        scenario = "Max Profit"
    elif end_ltp >= buy_strike:
        pnl = -estimated_net_premium
        scenario = "Max Loss"
    else:
        intrinsic_buy = buy_strike - end_ltp
        intrinsic_sell = sell_strike - end_ltp
        pnl = (intrinsic_buy - intrinsic_sell) - estimated_net_premium
        scenario = "Partial Profit"
    
    print(f"  Exit LTP: Rs {end_ltp:,.2f}")
    print(f"  Scenario: {scenario}")
    print(f"  Estimated P&L: Rs {pnl:,.2f}")
    
    return {
        'strategy': 'Bear Put Spread',
        'symbol': symbol,
        'exchange': exchange,
        'start_price': float(start_ltp),
        'end_price': float(end_ltp),
        'buy_strike': float(buy_strike),
        'sell_strike': float(sell_strike),
        'spread_width': float(buy_strike - sell_strike),
        'estimated_pnl': float(pnl),
        'scenario': scenario,
        'price_change_pct': float((end_ltp - start_ltp) / start_ltp * 100),
        'start_date': start_date,
        'end_date': end_date
    }

def analyze_iron_condor(symbol, exchange, start_date, end_date, strike_int=50, sell_otm=1, buy_otm=3):
    """
    Analyze Iron Condor strategy performance
    
    Iron Condor:
    - Sell OTM1 Call (lower strike)
    - Sell OTM1 Put (higher strike)
    - Buy OTM3 Call (even higher strike)
    - Buy OTM3 Put (even lower strike)
    - Max Profit: Net Premium Received
    - Max Loss: Spread Width - Net Premium
    """
    print(f"\nAnalyzing Iron Condor for {symbol} ({exchange})")
    print(f"Configuration: Sell OTM{sell_otm} Call/Put, Buy OTM{buy_otm} Call/Put")
    print(f"Period: {start_date} to {end_date}")
    
    df = get_historical_data(symbol, exchange, start_date, end_date)
    if df is None or df.empty:
        print(f"  [WARNING] No historical data available for {symbol}")
        return None
    
    print(f"  Found {len(df)} data points")
    
    start_ltp = df['close'].iloc[0]
    end_ltp = df['close'].iloc[-1]
    
    # Calculate strikes
    sell_call_strike = calculate_strike(start_ltp, f"OTM{sell_otm}", "CE", strike_int)
    buy_call_strike = calculate_strike(start_ltp, f"OTM{buy_otm}", "CE", strike_int)
    sell_put_strike = calculate_strike(start_ltp, f"OTM{sell_otm}", "PE", strike_int)
    buy_put_strike = calculate_strike(start_ltp, f"OTM{buy_otm}", "PE", strike_int)
    
    print(f"  Entry LTP: Rs {start_ltp:,.2f}")
    print(f"  Sell Call Strike (OTM{sell_otm}): Rs {sell_call_strike:,.2f}")
    print(f"  Buy Call Strike (OTM{buy_otm}): Rs {buy_call_strike:,.2f}")
    print(f"  Sell Put Strike (OTM{sell_otm}): Rs {sell_put_strike:,.2f}")
    print(f"  Buy Put Strike (OTM{buy_otm}): Rs {buy_put_strike:,.2f}")
    
    call_spread_width = buy_call_strike - sell_call_strike
    put_spread_width = sell_put_strike - buy_put_strike
    
    # Estimate net premium received (simplified)
    estimated_net_premium = (call_spread_width + put_spread_width) * 0.3
    
    # Calculate P&L based on exit price
    call_pnl = 0.0
    put_pnl = 0.0
    
    # Call side P&L
    if end_ltp <= sell_call_strike:
        # Both calls expire worthless - keep premium
        call_pnl = estimated_net_premium * 0.5
    elif end_ltp >= buy_call_strike:
        # Max loss on call side
        call_pnl = -call_spread_width + (estimated_net_premium * 0.5)
    else:
        # Between strikes - partial loss
        intrinsic_sell = max(0, end_ltp - sell_call_strike)
        intrinsic_buy = max(0, end_ltp - buy_call_strike)
        call_pnl = (estimated_net_premium * 0.5) - (intrinsic_sell - intrinsic_buy)
    
    # Put side P&L
    if end_ltp >= sell_put_strike:
        # Both puts expire worthless - keep premium
        put_pnl = estimated_net_premium * 0.5
    elif end_ltp <= buy_put_strike:
        # Max loss on put side
        put_pnl = -put_spread_width + (estimated_net_premium * 0.5)
    else:
        # Between strikes - partial loss
        intrinsic_sell = max(0, sell_put_strike - end_ltp)
        intrinsic_buy = max(0, buy_put_strike - end_ltp)
        put_pnl = (estimated_net_premium * 0.5) - (intrinsic_sell - intrinsic_buy)
    
    total_pnl = call_pnl + put_pnl
    
    if sell_put_strike <= end_ltp <= sell_call_strike:
        scenario = "Max Profit"
    elif end_ltp < buy_put_strike or end_ltp > buy_call_strike:
        scenario = "Max Loss"
    else:
        scenario = "Partial Loss"
    
    print(f"  Exit LTP: Rs {end_ltp:,.2f}")
    print(f"  Scenario: {scenario}")
    print(f"  Estimated P&L: Rs {total_pnl:,.2f}")
    
    return {
        'strategy': 'Iron Condor',
        'symbol': symbol,
        'exchange': exchange,
        'start_price': float(start_ltp),
        'end_price': float(end_ltp),
        'sell_call_strike': float(sell_call_strike),
        'buy_call_strike': float(buy_call_strike),
        'sell_put_strike': float(sell_put_strike),
        'buy_put_strike': float(buy_put_strike),
        'estimated_pnl': float(total_pnl),
        'scenario': scenario,
        'price_change_pct': float((end_ltp - start_ltp) / start_ltp * 100),
        'start_date': start_date,
        'end_date': end_date
    }

def analyze_straddle(symbol, exchange, start_date, end_date, strike_int=50, action="BUY"):
    """
    Analyze Straddle strategy performance
    
    Straddle:
    - Buy ATM Call + Buy ATM Put (Long Straddle)
    - Sell ATM Call + Sell ATM Put (Short Straddle)
    """
    print(f"\nAnalyzing {action} Straddle for {symbol} ({exchange})")
    print(f"Period: {start_date} to {end_date}")
    
    df = get_historical_data(symbol, exchange, start_date, end_date)
    if df is None or df.empty:
        print(f"  [WARNING] No historical data available for {symbol}")
        return None
    
    print(f"  Found {len(df)} data points")
    
    start_ltp = df['close'].iloc[0]
    end_ltp = df['close'].iloc[-1]
    strike = calculate_strike(start_ltp, "ATM", "CE", strike_int)
    
    print(f"  Entry LTP: Rs {start_ltp:,.2f}")
    print(f"  Strike: Rs {strike:,.2f}")
    
    # Estimate premium paid/received
    estimated_premium = strike * 0.02  # ~2% of strike
    
    # Calculate intrinsic values
    call_intrinsic = max(0, end_ltp - strike)
    put_intrinsic = max(0, strike - end_ltp)
    total_intrinsic = call_intrinsic + put_intrinsic
    
    if action.upper() == "BUY":
        pnl = total_intrinsic - estimated_premium
    else:  # SELL
        pnl = estimated_premium - total_intrinsic
    
    price_move_pct = abs((end_ltp - strike) / strike * 100)
    
    if action.upper() == "BUY":
        if price_move_pct > 2:
            scenario = "Profitable"
        else:
            scenario = "Loss"
    else:  # SELL
        if price_move_pct < 2:
            scenario = "Profitable"
        else:
            scenario = "Loss"
    
    print(f"  Exit LTP: Rs {end_ltp:,.2f}")
    print(f"  Scenario: {scenario}")
    print(f"  Estimated P&L: Rs {pnl:,.2f}")
    
    return {
        'strategy': f'{action} Straddle',
        'symbol': symbol,
        'exchange': exchange,
        'start_price': float(start_ltp),
        'end_price': float(end_ltp),
        'strike': float(strike),
        'estimated_pnl': float(pnl),
        'scenario': scenario,
        'price_change_pct': float((end_ltp - start_ltp) / start_ltp * 100),
        'start_date': start_date,
        'end_date': end_date
    }

def analyze_bull_call_spread(symbol, exchange, start_date, end_date, strike_int=50, buy_offset="ITM2", sell_otm=5):
    """
    Analyze Bull Call Spread strategy performance
    
    Bull Call Spread:
    - Buy ITM2 Call (lower strike)
    - Sell OTM5 Call (higher strike)
    - Max Profit: Spread Width - Net Premium Paid
    - Max Loss: Net Premium Paid
    """
    print(f"\nAnalyzing Bull Call Spread for {symbol} ({exchange})")
    print(f"Configuration: Buy {buy_offset} Call, Sell OTM{sell_otm} Call")
    print(f"Period: {start_date} to {end_date}")
    
    df = get_historical_data(symbol, exchange, start_date, end_date)
    if df is None or df.empty:
        print(f"  [WARNING] No historical data available for {symbol}")
        return None
    
    print(f"  Found {len(df)} data points")
    
    start_ltp = df['close'].iloc[0]
    end_ltp = df['close'].iloc[-1]
    
    buy_strike = calculate_strike(start_ltp, buy_offset, "CE", strike_int)
    sell_strike = calculate_strike(start_ltp, f"OTM{sell_otm}", "CE", strike_int)
    
    print(f"  Entry LTP: Rs {start_ltp:,.2f}")
    print(f"  Buy Strike (ITM2 Call): Rs {buy_strike:,.2f}")
    print(f"  Sell Strike (OTM{sell_otm} Call): Rs {sell_strike:,.2f}")
    print(f"  Spread Width: Rs {sell_strike - buy_strike:,.2f}")
    
    estimated_net_premium = (sell_strike - buy_strike) * 0.5
    
    if end_ltp >= sell_strike:
        intrinsic_buy = end_ltp - buy_strike
        intrinsic_sell = end_ltp - sell_strike
        pnl = (intrinsic_buy - intrinsic_sell) - estimated_net_premium
        scenario = "Max Profit"
    elif end_ltp <= buy_strike:
        pnl = -estimated_net_premium
        scenario = "Max Loss"
    else:
        intrinsic_buy = end_ltp - buy_strike
        pnl = intrinsic_buy - estimated_net_premium
        scenario = "Partial Profit"
    
    print(f"  Exit LTP: Rs {end_ltp:,.2f}")
    print(f"  Scenario: {scenario}")
    print(f"  Estimated P&L: Rs {pnl:,.2f}")
    
    return {
        'strategy': 'Bull Call Spread',
        'symbol': symbol,
        'exchange': exchange,
        'start_price': float(start_ltp),
        'end_price': float(end_ltp),
        'buy_strike': float(buy_strike),
        'sell_strike': float(sell_strike),
        'spread_width': float(sell_strike - buy_strike),
        'estimated_pnl': float(pnl),
        'scenario': scenario,
        'price_change_pct': float((end_ltp - start_ltp) / start_ltp * 100),
        'start_date': start_date,
        'end_date': end_date
    }

def analyze_strategy_performance(strategy_name, symbol, exchange, start_date, end_date, **kwargs):
    """Analyze how a strategy would have performed using historical data"""
    strategy_lower = strategy_name.lower()
    
    if strategy_lower == 'bear put spread':
        return analyze_bear_put_spread(
            symbol, exchange, start_date, end_date,
            strike_int=kwargs.get('strike_int', 50),
            buy_offset=kwargs.get('buy_offset', 'ITM2'),
            sell_otm=kwargs.get('sell_otm', 5)
        )
    elif strategy_lower == 'iron condor':
        return analyze_iron_condor(
            symbol, exchange, start_date, end_date,
            strike_int=kwargs.get('strike_int', 50),
            sell_otm=kwargs.get('sell_otm', 1),
            buy_otm=kwargs.get('buy_otm', 3)
        )
    elif strategy_lower in ['straddle', 'long straddle', 'buy straddle']:
        return analyze_straddle(
            symbol, exchange, start_date, end_date,
            strike_int=kwargs.get('strike_int', 50),
            action="BUY"
        )
    elif strategy_lower in ['short straddle', 'sell straddle']:
        return analyze_straddle(
            symbol, exchange, start_date, end_date,
            strike_int=kwargs.get('strike_int', 50),
            action="SELL"
        )
    elif strategy_lower == 'bull call spread':
        return analyze_bull_call_spread(
            symbol, exchange, start_date, end_date,
            strike_int=kwargs.get('strike_int', 50),
            buy_offset=kwargs.get('buy_offset', 'ITM2'),
            sell_otm=kwargs.get('sell_otm', 5)
        )
    else:
        print(f"\nAnalyzing {strategy_name} for {symbol} ({exchange})")
        print(f"Period: {start_date} to {end_date}")
        
        df = get_historical_data(symbol, exchange, start_date, end_date)
        if df is None or df.empty:
            print(f"  [WARNING] No historical data available for {symbol}")
            return None
        
        print(f"  Found {len(df)} data points")
        
        price_change = df['close'].iloc[-1] - df['close'].iloc[0]
        price_change_pct = (price_change / df['close'].iloc[0]) * 100
        
        return {
            'strategy': strategy_name,
            'symbol': symbol,
            'exchange': exchange,
            'start_price': float(df['close'].iloc[0]),
            'end_price': float(df['close'].iloc[-1]),
            'price_change': float(price_change),
            'price_change_pct': float(price_change_pct),
            'data_points': len(df),
            'start_date': start_date,
            'end_date': end_date
        }

def get_analysis_dates(period="auto"):
    """
    Get dates for analysis:
    - Yesterday (if available and weekday)
    - Previous week in current month (if yesterday not available)
    - Can also specify: "yesterday", "last_week", "last_month"
    """
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    if period == "auto":
        # Check if yesterday is a weekday (Mon-Fri)
        if yesterday.weekday() < 5:  # 0-4 = Mon-Fri
            end_date = yesterday
            start_date = yesterday
            return start_date, end_date, "yesterday"
        else:
            # Yesterday is weekend, use previous week
            days_back = (yesterday.weekday() - 4) % 7
            if days_back == 0:
                days_back = 7
            last_friday = yesterday - timedelta(days=days_back)
            week_start = last_friday - timedelta(days=4)
            week_end = last_friday
            return week_start, week_end, "previous_week"
    
    elif period == "yesterday":
        end_date = yesterday
        start_date = yesterday
        return start_date, end_date, "yesterday"
    
    elif period == "last_week":
        # Find last Friday
        days_back = (yesterday.weekday() - 4) % 7
        if days_back == 0:
            days_back = 7
        last_friday = yesterday - timedelta(days=days_back)
        week_start = last_friday - timedelta(days=4)
        week_end = last_friday
        return week_start, week_end, "last_week"
    
    elif period == "last_month":
        # Get previous month's last trading week
        first_of_month = today.replace(day=1)
        last_of_prev_month = first_of_month - timedelta(days=1)
        # Find last Friday of previous month
        while last_of_prev_month.weekday() != 4:  # 4 = Friday
            last_of_prev_month -= timedelta(days=1)
        week_start = last_of_prev_month - timedelta(days=4)
        week_end = last_of_prev_month
        return week_start, week_end, "last_month"
    
    else:
        # Default to yesterday
        end_date = yesterday
        start_date = yesterday
        return start_date, end_date, "yesterday"

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Historical Strategy Analysis using yfinance')
    parser.add_argument('--period', type=str, default='auto',
                        choices=['auto', 'yesterday', 'last_week', 'last_month'],
                        help='Analysis period (default: auto)')
    parser.add_argument('--symbol', type=str, default='NIFTY',
                        help='Underlying symbol (default: NIFTY)')
    parser.add_argument('--exchange', type=str, default='NSE_INDEX',
                        help='Exchange code (default: NSE_INDEX)')
    parser.add_argument('--strategies', type=str, nargs='+',
                        help='Strategies to analyze (default: all)')
    parser.add_argument('--strike-int', type=int, default=50,
                        help='Strike interval (default: 50)')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("HISTORICAL STRATEGY ANALYSIS USING YFINANCE DATA")
    print("="*80)
    print("\nNote: This analyzes market data, NOT DB trades")
    print("      Use this for options strategies that may not have DB records\n")
    
    # Get analysis dates
    start_date, end_date, period_type = get_analysis_dates(args.period)
    
    print(f"Analysis Period: {period_type}")
    print(f"Start Date: {start_date}")
    print(f"End Date: {end_date}")
    print(f"Symbol: {args.symbol}")
    print(f"Exchange: {args.exchange}\n")
    
    # Get strategies to analyze
    all_strategies = [
        {
            'name': 'Bear Put Spread',
            'symbol': args.symbol,
            'exchange': args.exchange,
            'strike_int': args.strike_int,
            'buy_offset': 'ITM2',
            'sell_otm': 5
        },
        {
            'name': 'Iron Condor',
            'symbol': args.symbol,
            'exchange': args.exchange,
            'strike_int': args.strike_int,
            'sell_otm': 1,
            'buy_otm': 3
        },
        {
            'name': 'Buy Straddle',
            'symbol': args.symbol,
            'exchange': args.exchange,
            'strike_int': args.strike_int
        },
        {
            'name': 'Bull Call Spread',
            'symbol': args.symbol,
            'exchange': args.exchange,
            'strike_int': args.strike_int,
            'buy_offset': 'ITM2',
            'sell_otm': 5
        },
    ]
    
    # Filter strategies if specified
    if args.strategies:
        strategies_to_analyze = [
            s for s in all_strategies 
            if any(name.lower() in s['name'].lower() for name in args.strategies)
        ]
        if not strategies_to_analyze:
            print(f"[WARNING] No matching strategies found for: {args.strategies}")
            print(f"Available strategies: {[s['name'] for s in all_strategies]}")
            return
    else:
        strategies_to_analyze = all_strategies
    
    results = []
    
    for strategy in strategies_to_analyze:
        result = analyze_strategy_performance(
            strategy['name'],
            strategy['symbol'],
            strategy['exchange'],
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            **{k: v for k, v in strategy.items() if k not in ['name', 'symbol', 'exchange']}
        )
        if result:
            results.append(result)
    
    # Print summary
    if results:
        print("\n" + "="*80)
        print("ANALYSIS SUMMARY")
        print("="*80)
        
        # Check if we have Bear Put Spread results
        has_options_strategy = any('estimated_pnl' in r for r in results)
        
        if has_options_strategy:
            # Check strategy type for appropriate display
            print(f"\n{'Strategy':<25} {'Symbol':<15} {'Key Details':<30} {'Estimated P&L':<18} {'Scenario':<15}")
            print("-" * 105)
            
            for result in results:
                if 'estimated_pnl' in result:
                    pnl_str = f"Rs {result['estimated_pnl']:>12,.2f}"
                    strategy = result['strategy']
                    
                    if 'Iron Condor' in strategy:
                        details = f"Call: {result.get('sell_call_strike', 0):.0f}-{result.get('buy_call_strike', 0):.0f}"
                    elif 'Straddle' in strategy:
                        details = f"Strike: {result.get('strike', 0):.0f}"
                    elif 'Spread' in strategy:
                        details = f"{result.get('buy_strike', 0):.0f}-{result.get('sell_strike', 0):.0f}"
                    else:
                        details = "N/A"
                    
                    print(f"{strategy:<25} {result['symbol']:<15} {details:<30} "
                          f"{pnl_str:<18} {result.get('scenario', 'N/A'):<15}")
        else:
            print(f"\n{'Strategy':<25} {'Symbol':<15} {'Start Price':<15} {'End Price':<15} {'Change %':<12}")
            print("-" * 80)
            
            for result in results:
                change_str = f"{result.get('price_change_pct', 0):+.2f}%"
                print(f"{result['strategy']:<25} {result['symbol']:<15} "
                      f"Rs {result['start_price']:>12,.2f} Rs {result['end_price']:>12,.2f} {change_str:<12}")
        
        print("="*80)
        
        # Print best and worst performing strategies
        if len(results) > 1:
            sorted_results = sorted(results, key=lambda x: x.get('estimated_pnl', 0), reverse=True)
            best = sorted_results[0]
            worst = sorted_results[-1]
            
            print(f"\n{'='*80}")
            print("PERFORMANCE RANKING")
            print(f"{'='*80}")
            print(f"\nBest Performer: {best['strategy']}")
            print(f"  Estimated P&L: Rs {best.get('estimated_pnl', 0):>12,.2f}")
            print(f"  Scenario: {best.get('scenario', 'N/A')}")
            
            print(f"\nWorst Performer: {worst['strategy']}")
            print(f"  Estimated P&L: Rs {worst.get('estimated_pnl', 0):>12,.2f}")
            print(f"  Scenario: {worst.get('scenario', 'N/A')}")
        
        print(f"\n{'='*80}")
        print("NOTES")
        print(f"{'='*80}")
        print("  - This analysis uses yfinance historical data for underlying prices")
        print("  - Option P&L is estimated based on intrinsic value at expiry")
        print("  - For accurate option pricing, historical option chain data would be needed")
        print("  - Premium estimates are simplified (actual premiums may vary)")
        print("  - Results are for educational/analysis purposes only")
    else:
        print("\n[WARNING] No analysis results available")
        print("          Check if historical data is available for the symbols")

if __name__ == "__main__":
    main()

