#!/usr/bin/env python
"""
Run All Strategies on Historical Data
Executes strategies as if trading is happening, but using historical data
Places orders in paper trading mode based on historical triggers
"""
import sys
import os
import json
import time
from datetime import datetime, timedelta
import pytz
import pandas as pd
from pathlib import Path
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Direct database access
import sqlite3
SANDBOX_DB_PATH = os.path.join(os.path.dirname(__file__), 'db', 'sandbox.db')

def load_strategy_env():
    """Load strategy environment variables"""
    env_file = Path('strategies/strategy_env.json')
    if env_file.exists():
        with open(env_file, 'r') as f:
            return json.load(f)
    return {}

def load_strategy_configs():
    """Load strategy configurations"""
    config_file = Path('strategies/strategy_configs.json')
    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

def get_api_key():
    """Get API key from environment or database"""
    # Try from .env file first
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('OPENALGO_APIKEY=') or line.startswith('OPENALGO_API_KEY='):
                    key = line.split('=', 1)[1].strip().strip('"').strip("'")
                    if key:
                        return key
    
    # Try from environment variables
    api_key = os.getenv('OPENALGO_APIKEY') or os.getenv('OPENALGO_API_KEY')
    if api_key:
        return api_key
    
    # Try from database (direct SQLite access)
    try:
        auth_db_path = os.path.join(os.path.dirname(__file__), 'db', 'auth.db')
        if os.path.exists(auth_db_path):
            conn = sqlite3.connect(auth_db_path)
            cursor = conn.cursor()
            # Try to get from api_keys table
            try:
                cursor.execute("SELECT api_key_encrypted FROM api_keys WHERE is_revoked = 0 LIMIT 1")
                result = cursor.fetchone()
                if result and result[0]:
                    # Note: In real scenario, would need decryption
                    # For now, try to use as-is if it's not encrypted
                    key = result[0]
                    if len(key) > 20:  # Likely a real key
                        return key
            except:
                pass
            conn.close()
    except Exception as e:
        logger.debug(f"Could not get API key from database: {e}")
    
    # Default fallback - use a test key (will work in analyze mode)
    return 'dff4df2521b5c4a3e8f9a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0cef'

def place_order_via_api(strategy_name, symbol, action, quantity, price, exchange, api_key):
    """Place order via REST API (works with running Flask server)"""
    try:
        url = 'http://127.0.0.1:5000/api/v1/placesmartorder'
        
        order_data = {
            'apikey': api_key,
            'strategy': strategy_name,
            'symbol': symbol,
            'exchange': exchange,
            'action': action,
            'quantity': quantity,
            'pricetype': 'MARKET',
            'product': 'MIS',
            'position_size': quantity if action == 'BUY' else -quantity
        }
        
        response = requests.post(url, json=order_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                logger.info(f"Placed {action} order for {strategy_name}: {symbol} @ {price}")
                return True
        
        logger.warning(f"Failed to place order: {response.status_code} - {response.text[:200]}")
        return False
    except Exception as e:
        logger.error(f"Error placing order via API: {e}")
        return False

def place_options_order_via_api(strategy_name, underlying, exchange, expiry_date, offset, option_type, action, quantity, api_key):
    """Place options order via REST API"""
    try:
        url = 'http://127.0.0.1:5000/api/v1/optionsorder'
        
        order_data = {
            'apikey': api_key,
            'strategy': strategy_name,
            'underlying': underlying,
            'exchange': exchange,
            'expiry_date': expiry_date,
            'offset': offset,
            'option_type': option_type,
            'action': action,
            'quantity': quantity,
            'pricetype': 'MARKET',
            'product': 'MIS'
        }
        
        response = requests.post(url, json=order_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                symbol = result.get('symbol', '')
                logger.info(f"Placed {action} order for {strategy_name}: {symbol}")
                return True, symbol
        
        logger.warning(f"Failed to place options order: {response.status_code} - {response.text[:200]}")
        return False, None
    except Exception as e:
        logger.error(f"Error placing options order via API: {e}")
        return False, None

def simulate_options_strategy_on_historical(strategy_id, strategy_name, historical_df, period_name, env_vars, api_key):
    """Simulate options strategy execution on historical data"""
    trades_placed = []
    
    # Get expiry date from env
    expiry_date = env_vars.get('EXPIRY_DATE', '2025-12-26')
    underlying = env_vars.get('UNDERLYING', 'NIFTY')
    exchange = env_vars.get('EXCHANGE', 'NSE_INDEX')
    quantity = int(env_vars.get('QUANTITY', '75'))
    
    # Convert expiry date format if needed
    if expiry_date and len(expiry_date) == 10 and expiry_date[4] == '-' and expiry_date[7] == '-':
        try:
            parsed_date = datetime.strptime(expiry_date, '%Y-%m-%d')
            expiry_date = parsed_date.strftime('%d%b%y').upper()
        except:
            pass
    
    if historical_df.empty or len(historical_df) < 10:
        logger.warning(f"Insufficient historical data for {strategy_name}")
        return None
    
    # Get first price for LTP
    first_price = float(historical_df['close'].iloc[0])
    
    # Determine strategy type and place appropriate orders
    if 'Straddle' in strategy_name:
        # Place ATM Call and Put
        offset = 'ATM'
        for option_type in ['CE', 'PE']:
            success, symbol = place_options_order_via_api(
                strategy_name, underlying, exchange, expiry_date, 
                offset, option_type, 'BUY', quantity, api_key
            )
            if success and symbol:
                trades_placed.append({
                    'symbol': symbol,
                    'action': 'BUY',
                    'price': first_price,
                    'quantity': quantity
                })
    
    elif 'Strangle' in strategy_name:
        # Place OTM Call and Put
        offset = 'OTM2'
        for option_type in ['CE', 'PE']:
            success, symbol = place_options_order_via_api(
                strategy_name, underlying, exchange, expiry_date,
                offset, option_type, 'BUY', quantity, api_key
            )
            if success and symbol:
                trades_placed.append({
                    'symbol': symbol,
                    'action': 'BUY',
                    'price': first_price,
                    'quantity': quantity
                })
    
    elif 'Iron Condor' in strategy_name:
        # Multi-leg strategy
        url = 'http://127.0.0.1:5000/api/v1/optionsmultiorder'
        sell_otm = int(env_vars.get('SELL_OTM', '5'))
        buy_otm = int(env_vars.get('BUY_OTM', '10'))
        
        order_data = {
            'apikey': api_key,
            'strategy': strategy_name,
            'underlying': underlying,
            'exchange': exchange,
            'expiry_date': expiry_date,
            'legs': [
                {"offset": f"OTM{buy_otm}", "option_type": "CE", "action": "BUY", "quantity": quantity},
                {"offset": f"OTM{buy_otm}", "option_type": "PE", "action": "BUY", "quantity": quantity},
                {"offset": f"OTM{sell_otm}", "option_type": "CE", "action": "SELL", "quantity": quantity},
                {"offset": f"OTM{sell_otm}", "option_type": "PE", "action": "SELL", "quantity": quantity}
            ]
        }
        
        try:
            response = requests.post(url, json=order_data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    for leg_result in result.get('results', []):
                        trades_placed.append({
                            'symbol': leg_result.get('symbol', ''),
                            'action': leg_result.get('action', ''),
                            'price': first_price,
                            'quantity': quantity
                        })
        except Exception as e:
            logger.error(f"Error placing Iron Condor: {e}")
    
    elif 'Iron Butterfly' in strategy_name:
        url = 'http://127.0.0.1:5000/api/v1/optionsmultiorder'
        wing_otm = int(env_vars.get('WING_OTM', '5'))
        
        order_data = {
            'apikey': api_key,
            'strategy': strategy_name,
            'underlying': underlying,
            'exchange': exchange,
            'expiry_date': expiry_date,
            'legs': [
                {"offset": f"OTM{wing_otm}", "option_type": "CE", "action": "BUY", "quantity": quantity},
                {"offset": f"OTM{wing_otm}", "option_type": "PE", "action": "BUY", "quantity": quantity},
                {"offset": "ATM", "option_type": "CE", "action": "SELL", "quantity": quantity},
                {"offset": "ATM", "option_type": "PE", "action": "SELL", "quantity": quantity}
            ]
        }
        
        try:
            response = requests.post(url, json=order_data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    for leg_result in result.get('results', []):
                        trades_placed.append({
                            'symbol': leg_result.get('symbol', ''),
                            'action': leg_result.get('action', ''),
                            'price': first_price,
                            'quantity': quantity
                        })
        except Exception as e:
            logger.error(f"Error placing Iron Butterfly: {e}")
    
    elif 'Bull Call Spread' in strategy_name:
        url = 'http://127.0.0.1:5000/api/v1/optionsmultiorder'
        buy_offset = env_vars.get('BUY_OFFSET', 'ITM2')
        sell_otm = int(env_vars.get('SELL_OTM', '5'))
        
        order_data = {
            'apikey': api_key,
            'strategy': strategy_name,
            'underlying': underlying,
            'exchange': exchange,
            'expiry_date': expiry_date,
            'legs': [
                {"offset": buy_offset, "option_type": "CE", "action": "BUY", "quantity": quantity},
                {"offset": f"OTM{sell_otm}", "option_type": "CE", "action": "SELL", "quantity": quantity}
            ]
        }
        
        try:
            response = requests.post(url, json=order_data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    for leg_result in result.get('results', []):
                        trades_placed.append({
                            'symbol': leg_result.get('symbol', ''),
                            'action': leg_result.get('action', ''),
                            'price': first_price,
                            'quantity': quantity
                        })
        except Exception as e:
            logger.error(f"Error placing Bull Call Spread: {e}")
    
    elif 'Bear Put Spread' in strategy_name:
        url = 'http://127.0.0.1:5000/api/v1/optionsmultiorder'
        buy_offset = env_vars.get('BUY_OFFSET', 'ITM2')
        sell_otm = int(env_vars.get('SELL_OTM', '5'))
        
        order_data = {
            'apikey': api_key,
            'strategy': strategy_name,
            'underlying': underlying,
            'exchange': exchange,
            'expiry_date': expiry_date,
            'legs': [
                {"offset": buy_offset, "option_type": "PE", "action": "BUY", "quantity": quantity},
                {"offset": f"OTM{sell_otm}", "option_type": "PE", "action": "SELL", "quantity": quantity}
            ]
        }
        
        try:
            response = requests.post(url, json=order_data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    for leg_result in result.get('results', []):
                        trades_placed.append({
                            'symbol': leg_result.get('symbol', ''),
                            'action': leg_result.get('action', ''),
                            'price': first_price,
                            'quantity': quantity
                        })
        except Exception as e:
            logger.error(f"Error placing Bear Put Spread: {e}")
    
    elif 'Covered Call' in strategy_name:
        offset = env_vars.get('SELL_OFFSET', 'OTM2')
        success, symbol = place_options_order_via_api(
            strategy_name, underlying, exchange, expiry_date,
            offset, 'CE', 'SELL', quantity, api_key
        )
        if success and symbol:
            trades_placed.append({
                'symbol': symbol,
                'action': 'SELL',
                'price': first_price,
                'quantity': quantity
            })
    
    elif 'Protective Put' in strategy_name:
        offset = env_vars.get('PUT_OFFSET', 'OTM2')
        success, symbol = place_options_order_via_api(
            strategy_name, underlying, exchange, expiry_date,
            offset, 'PE', 'BUY', quantity, api_key
        )
        if success and symbol:
            trades_placed.append({
                'symbol': symbol,
                'action': 'BUY',
                'price': first_price,
                'quantity': quantity
            })
    
    return {
        'strategy': strategy_name,
        'trades_placed': len(trades_placed),
        'trades': trades_placed
    }

def simulate_intraday_strategy_on_historical(strategy_id, strategy_name, historical_df, period_name, env_vars, api_key):
    """Simulate intraday strategy execution on historical data"""
    trades_placed = []
    
    if historical_df.empty or len(historical_df) < 50:
        logger.warning(f"Insufficient historical data for {strategy_name}")
        return None
    
    # Calculate simple moving averages for signal generation
    if 'close' in historical_df.columns:
        df = historical_df.copy()
        df['sma_short'] = df['close'].rolling(window=10).mean()
        df['sma_long'] = df['close'].rolling(window=20).mean()
        
        # Generate buy/sell signals
        df['signal'] = 0
        df.loc[df['sma_short'] > df['sma_long'], 'signal'] = 1  # Buy signal
        df.loc[df['sma_short'] < df['sma_long'], 'signal'] = -1  # Sell signal
        
        # Find entry/exit points (sample every 10th point to avoid too many trades)
        position = 0
        for idx in range(0, len(df), 10):  # Sample every 10th point
            row = df.iloc[idx]
            if row['signal'] == 1 and position <= 0:  # Buy signal
                place_order_via_api(strategy_name, 'NIFTY', 'BUY', 1, row['close'], 'NSE_INDEX', api_key)
                trades_placed.append({
                    'symbol': 'NIFTY',
                    'action': 'BUY',
                    'price': row['close'],
                    'quantity': 1
                })
                position = 1
            elif row['signal'] == -1 and position > 0:  # Sell signal
                place_order_via_api(strategy_name, 'NIFTY', 'SELL', 1, row['close'], 'NSE_INDEX', api_key)
                trades_placed.append({
                    'symbol': 'NIFTY',
                    'action': 'SELL',
                    'price': row['close'],
                    'quantity': 1
                })
                position = 0
    
    return {
        'strategy': strategy_name,
        'trades_placed': len(trades_placed),
        'trades': trades_placed
    }

def get_historical_data(symbol, exchange, interval, start_date, end_date, api_key):
    """Fetch historical data using yfinance (bypasses API issues)"""
    try:
        # Try API first
        url = 'http://127.0.0.1:5000/api/v1/history'
        data = {
            'apikey': api_key,
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'start_date': start_date,
            'end_date': end_date
        }
        
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                data_list = result.get('data', [])
                if data_list:
                    return True, data_list
        
        # Fallback to yfinance
        logger.info(f"API failed, using yfinance for {symbol}")
        try:
            import yfinance as yf
            
            symbol_mapping = {
                'NIFTY': '^NSEI',
                'BANKNIFTY': '^NSEBANK',
                'FINNIFTY': '^NSEFIN',
                'MIDCPNIFTY': '^NSEMIDCP'
            }
            
            yf_symbol = symbol_mapping.get(symbol.upper())
            if not yf_symbol:
                logger.warning(f"No yfinance mapping for {symbol}")
                return False, []
            
            ticker = yf.Ticker(yf_symbol)
            
            # Calculate period
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            days_diff = (end - start).days + 1  # Include end date
            
            # Map interval
            interval_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '1h': '1h', '1d': '1d'
            }
            yf_interval = interval_map.get(interval.lower(), '5m')
            
            # Fetch data - yfinance limits intraday to 60 days
            if yf_interval in ['1m', '5m', '15m', '30m', '1h']:
                if days_diff <= 60:
                    # Use period for intraday
                    if days_diff <= 7:
                        period = '7d'
                    elif days_diff <= 30:
                        period = '30d'
                    else:
                        period = '60d'
                    hist = ticker.history(period=period, interval=yf_interval)
                else:
                    # Limit to 60 days for intraday
                    limited_start = end - timedelta(days=59)
                    hist = ticker.history(start=limited_start.strftime('%Y-%m-%d'), end=end_date, interval=yf_interval)
            else:
                # Daily interval - can use longer periods
                hist = ticker.history(start=start_date, end=end_date, interval=yf_interval)
            
            if hist.empty:
                logger.warning(f"No data from yfinance for {symbol}")
                return False, []
            
            # Filter by date range if needed
            hist = hist[(hist.index.date >= start.date()) & (hist.index.date <= end.date())]
            
            if hist.empty:
                logger.warning(f"No data in date range for {symbol}")
                return False, []
            
            # Convert to list of dicts
            data_list = []
            for idx, row in hist.iterrows():
                data_list.append({
                    'timestamp': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']) if 'Volume' in row else 0
                })
            
            logger.info(f"Fetched {len(data_list)} data points from yfinance for {symbol}")
            return True, data_list
        except ImportError:
            logger.error("yfinance not installed. Install with: pip install yfinance")
            return False, []
        except Exception as e:
            logger.error(f"Error fetching from yfinance: {e}")
            import traceback
            traceback.print_exc()
            return False, []
        
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        import traceback
        traceback.print_exc()
        return False, []

def run_all_strategies_on_historical_data():
    """Run all strategies on historical data for multiple periods"""
    # Setup logging
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    global logger
    logger = logging.getLogger(__name__)
    
    # Get API key
    api_key = get_api_key()
    if not api_key:
        logger.error("No API key found. Please set OPENALGO_APIKEY in .env file")
        return
    
    # Load strategy configs
    strategy_configs = load_strategy_configs()
    strategy_env = load_strategy_env()
    
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).date()
    
    periods = [
        ("CURRENT DAY", today, today),
        ("PREVIOUS DAY", today - timedelta(days=1), today - timedelta(days=1)),
        ("LAST 7 DAYS", today - timedelta(days=7), today),
        ("LAST 14 DAYS", today - timedelta(days=14), today),
        ("PREVIOUS WEEK", today - timedelta(days=7), today),
        ("CURRENT MONTH", today - timedelta(days=30), today)
    ]
    
    print("="*70)
    print("RUNNING STRATEGIES ON HISTORICAL DATA")
    print("="*70)
    print(f"Start Time: {datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"Mode: Paper Trading (Analyze Mode)")
    print("="*70)
    
    all_results = {}
    
    for period_name, start_date, end_date in periods:
        print(f"\n{'='*70}")
        print(f"PERIOD: {period_name} ({start_date} to {end_date})")
        print(f"{'='*70}")
        
        # Fetch historical data for NIFTY
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        success, data = get_historical_data('NIFTY', 'NSE_INDEX', '5m', start_str, end_str, api_key)
        
        if not success or not data:
            logger.warning(f"Failed to fetch historical data for {period_name}")
            continue
        
        historical_df = pd.DataFrame(data)
        if 'timestamp' in historical_df.columns:
            historical_df['timestamp'] = pd.to_datetime(historical_df['timestamp'])
            historical_df = historical_df.sort_values('timestamp').reset_index(drop=True)
        
        print(f"Loaded {len(historical_df)} data points for {period_name}")
        
        period_results = []
        
        # Run each strategy on this historical data
        for strategy_id, strategy_config in strategy_configs.items():
            try:
                strategy_name = strategy_config.get('name', strategy_id)
                is_options_strategy = 'option' in strategy_id.lower() or 'Option' in strategy_name
                
                env_vars = strategy_env.get(strategy_id, {})
                
                if is_options_strategy:
                    result = simulate_options_strategy_on_historical(
                        strategy_id, strategy_name, historical_df, period_name, env_vars, api_key
                    )
                else:
                    result = simulate_intraday_strategy_on_historical(
                        strategy_id, strategy_name, historical_df, period_name, env_vars, api_key
                    )
                
                if result:
                    period_results.append(result)
                    print(f"  ✓ {result['strategy']}: {result['trades_placed']} trades placed")
                    time.sleep(0.5)  # Small delay between strategies
            except Exception as e:
                logger.error(f"Error running {strategy_id} on {period_name}: {e}")
                import traceback
                traceback.print_exc()
        
        all_results[period_name] = period_results
        print(f"\n{period_name} Summary: {len(period_results)} strategies executed, {sum(r['trades_placed'] for r in period_results)} total trades")
        
        # Wait a bit before next period
        time.sleep(2)
    
    # Now analyze the results
    print(f"\n{'='*70}")
    print("ANALYZING RESULTS")
    print(f"{'='*70}")
    
    # Run the analysis on the sandbox database
    from quick_backtest import run_quick_analysis
    run_quick_analysis()
    
    print(f"\n{'='*70}")
    print("HISTORICAL DATA BACKTEST COMPLETE")
    print(f"{'='*70}")
    print(f"End Time: {datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}")

if __name__ == "__main__":
    run_all_strategies_on_historical_data()


