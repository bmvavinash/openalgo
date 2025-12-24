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

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from blueprints.python_strategy import STRATEGY_CONFIGS
from services.history_service import get_history
from database.auth_db import get_api_key_for_tradingview
from database.settings_db import get_analyze_mode, set_analyze_mode
from database.sandbox_db import SandboxTrades, SandboxOrders, db_session
from utils.logging import get_logger

logger = get_logger(__name__)

def load_strategy_env():
    """Load strategy environment variables"""
    env_file = Path('strategies/strategy_env.json')
    if env_file.exists():
        with open(env_file, 'r') as f:
            return json.load(f)
    return {}

def simulate_strategy_on_historical_data(strategy_id, strategy_config, historical_df, period_name, api_key):
    """
    Simulate running a strategy on historical data
    This executes the strategy logic on each historical data point
    """
    strategy_name = strategy_config.get('name', strategy_id)
    file_path = strategy_config.get('file_path', '')
    
    if not file_path or not Path(file_path).exists():
        logger.warning(f"Strategy file not found: {file_path}")
        return None
    
    logger.info(f"Running {strategy_name} on historical data for {period_name}")
    
    # Load strategy environment
    strategy_env = load_strategy_env()
    env_vars = strategy_env.get(strategy_id, {})
    
    # Set up environment for strategy execution
    import subprocess
    import tempfile
    
    # Create a temporary script that will run the strategy on historical data
    # For now, we'll use a simplified approach: execute the strategy with historical data
    
    # Check if this is an options strategy
    is_options_strategy = 'option' in strategy_id.lower() or 'Option' in strategy_name
    
    if is_options_strategy:
        # For options strategies, we need to simulate option order placement
        return simulate_options_strategy_on_historical(strategy_id, strategy_name, historical_df, period_name, env_vars, api_key)
    else:
        # For intraday strategies, simulate regular order placement
        return simulate_intraday_strategy_on_historical(strategy_id, strategy_name, historical_df, period_name, env_vars, api_key)

def simulate_options_strategy_on_historical(strategy_id, strategy_name, historical_df, period_name, env_vars, api_key):
    """Simulate options strategy execution on historical data"""
    from services.option_symbol_service import get_option_symbol
    from services.place_options_order_service import place_options_order
    
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
    
    # Simulate strategy execution at key points in historical data
    # For options, we'll place orders at the start and check exit conditions
    
    if historical_df.empty or len(historical_df) < 10:
        logger.warning(f"Insufficient historical data for {strategy_name}")
        return None
    
    # Get first and last prices
    first_price = float(historical_df['close'].iloc[0])
    last_price = float(historical_df['close'].iloc[-1])
    
    # Determine strategy type and place appropriate orders
    if 'Straddle' in strategy_name:
        # Place ATM Call and Put
        offset = 'ATM'
        for option_type in ['CE', 'PE']:
            success, response, status = get_option_symbol(
                underlying=underlying,
                exchange=exchange,
                expiry_date=expiry_date,
                strike_int=50,
                offset=offset,
                option_type=option_type,
                api_key=api_key,
                underlying_ltp=first_price
            )
            if success:
                symbol = response.get('symbol')
                # Place order in sandbox
                place_order_in_sandbox(strategy_name, symbol, 'BUY', quantity, first_price, historical_df.index[0])
                trades_placed.append({
                    'symbol': symbol,
                    'action': 'BUY',
                    'price': first_price,
                    'quantity': quantity
                })
    
    elif 'Strangle' in strategy_name:
        # Place OTM Call and Put
        for option_type in ['CE', 'PE']:
            offset = 'OTM2'  # Default OTM level
            success, response, status = get_option_symbol(
                underlying=underlying,
                exchange=exchange,
                expiry_date=expiry_date,
                strike_int=50,
                offset=offset,
                option_type=option_type,
                api_key=api_key,
                underlying_ltp=first_price
            )
            if success:
                symbol = response.get('symbol')
                options_exchange = response.get('exchange', 'NFO')
                place_order_in_sandbox(strategy_name, symbol, 'BUY', quantity, first_price, historical_df.index[0], exchange=options_exchange, api_key=api_key)
                trades_placed.append({
                    'symbol': symbol,
                    'action': 'BUY',
                    'price': first_price,
                    'quantity': quantity
                })
    
    elif 'Iron Condor' in strategy_name or 'Iron Butterfly' in strategy_name:
        # Multi-leg strategies - use optionsmultiorder
        from services.options_multiorder_service import place_options_multiorder
        
        legs = []
        if 'Iron Condor' in strategy_name:
            sell_otm = int(env_vars.get('SELL_OTM', '5'))
            buy_otm = int(env_vars.get('BUY_OTM', '10'))
            legs = [
                {"offset": f"OTM{buy_otm}", "option_type": "CE", "action": "BUY", "quantity": quantity},
                {"offset": f"OTM{buy_otm}", "option_type": "PE", "action": "BUY", "quantity": quantity},
                {"offset": f"OTM{sell_otm}", "option_type": "CE", "action": "SELL", "quantity": quantity},
                {"offset": f"OTM{sell_otm}", "option_type": "PE", "action": "SELL", "quantity": quantity}
            ]
        elif 'Iron Butterfly' in strategy_name:
            wing_otm = int(env_vars.get('WING_OTM', '5'))
            legs = [
                {"offset": f"OTM{wing_otm}", "option_type": "CE", "action": "BUY", "quantity": quantity},
                {"offset": f"OTM{wing_otm}", "option_type": "PE", "action": "BUY", "quantity": quantity},
                {"offset": "ATM", "option_type": "CE", "action": "SELL", "quantity": quantity},
                {"offset": "ATM", "option_type": "PE", "action": "SELL", "quantity": quantity}
            ]
        
        if legs:
            multiorder_data = {
                'strategy': strategy_name,
                'underlying': underlying,
                'exchange': exchange,
                'expiry_date': expiry_date,
                'legs': legs
            }
            success, response, status = place_options_multiorder(multiorder_data, api_key)
            if success:
                for leg_result in response.get('results', []):
                    trades_placed.append({
                        'symbol': leg_result.get('symbol'),
                        'action': leg_result.get('action'),
                        'price': first_price,  # Approximate
                        'quantity': quantity
                    })
    
    elif 'Bull Call Spread' in strategy_name or 'Bear Put Spread' in strategy_name:
        # Spread strategies
        from services.options_multiorder_service import place_options_multiorder
        
        if 'Bull Call Spread' in strategy_name:
            buy_offset = env_vars.get('BUY_OFFSET', 'ITM2')
            sell_otm = int(env_vars.get('SELL_OTM', '5'))
            legs = [
                {"offset": buy_offset, "option_type": "CE", "action": "BUY", "quantity": quantity},
                {"offset": f"OTM{sell_otm}", "option_type": "CE", "action": "SELL", "quantity": quantity}
            ]
        else:  # Bear Put Spread
            buy_offset = env_vars.get('BUY_OFFSET', 'ITM2')
            sell_otm = int(env_vars.get('SELL_OTM', '5'))
            legs = [
                {"offset": buy_offset, "option_type": "PE", "action": "BUY", "quantity": quantity},
                {"offset": f"OTM{sell_otm}", "option_type": "PE", "action": "SELL", "quantity": quantity}
            ]
        
        multiorder_data = {
            'strategy': strategy_name,
            'underlying': underlying,
            'exchange': exchange,
            'expiry_date': expiry_date,
            'legs': legs
        }
        success, response, status = place_options_multiorder(multiorder_data, api_key)
        if success:
            for leg_result in response.get('results', []):
                trades_placed.append({
                    'symbol': leg_result.get('symbol'),
                    'action': leg_result.get('action'),
                    'price': first_price,
                    'quantity': quantity
                })
    
    elif 'Covered Call' in strategy_name or 'Protective Put' in strategy_name:
        # Single leg strategies
        if 'Covered Call' in strategy_name:
            offset = env_vars.get('SELL_OFFSET', 'OTM2')
            option_type = 'CE'
            action = 'SELL'
        else:  # Protective Put
            offset = env_vars.get('PUT_OFFSET', 'OTM2')
            option_type = 'PE'
            action = 'BUY'
        
        success, response, status = get_option_symbol(
            underlying=underlying,
            exchange=exchange,
            expiry_date=expiry_date,
            strike_int=50,
            offset=offset,
            option_type=option_type,
            api_key=api_key,
            underlying_ltp=first_price
        )
        if success:
            symbol = response.get('symbol')
            place_order_in_sandbox(strategy_name, symbol, action, quantity, first_price, historical_df.index[0])
            trades_placed.append({
                'symbol': symbol,
                'action': action,
                'price': first_price,
                'quantity': quantity
            })
    
    elif 'Calendar Spread' in strategy_name:
        # Calendar spread needs two different expiry dates
        # For now, use same expiry but different strikes
        logger.warning(f"Calendar Spread simulation not fully implemented for {strategy_name}")
        return None
    
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
    
    # Simple simulation: Check for buy/sell signals based on price movement
    # In reality, this would execute the actual strategy logic (EMA, MACD, RSI, etc.)
    
    # Calculate simple moving averages for signal generation
    if 'close' in historical_df.columns:
        df = historical_df.copy()
        df['sma_short'] = df['close'].rolling(window=10).mean()
        df['sma_long'] = df['close'].rolling(window=20).mean()
        
        # Generate buy/sell signals
        df['signal'] = 0
        df.loc[df['sma_short'] > df['sma_long'], 'signal'] = 1  # Buy signal
        df.loc[df['sma_short'] < df['sma_long'], 'signal'] = -1  # Sell signal
        
        # Find entry/exit points
        position = 0
        for idx, row in df.iterrows():
            if row['signal'] == 1 and position <= 0:  # Buy signal
                place_order_in_sandbox(strategy_name, 'NIFTY', 'BUY', 1, row['close'], idx, exchange='NSE_INDEX', api_key=api_key)
                trades_placed.append({
                    'symbol': 'NIFTY',
                    'action': 'BUY',
                    'price': row['close'],
                    'quantity': 1
                })
                position = 1
            elif row['signal'] == -1 and position > 0:  # Sell signal
                place_order_in_sandbox(strategy_name, 'NIFTY', 'SELL', 1, row['close'], idx, exchange='NSE_INDEX', api_key=api_key)
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

def place_order_in_sandbox(strategy_name, symbol, action, quantity, price, timestamp_idx, exchange='NFO', api_key=None):
    """Place an order in the sandbox (paper trading) using order manager"""
    try:
        from sandbox.order_manager import OrderManager
        from database.auth_db import get_user_id_from_apikey
        
        # Get user ID from API key
        if api_key:
            user_id = get_user_id_from_apikey(api_key)
        else:
            # Use default user
            user_id = 'avinash'
        
        if not user_id:
            logger.warning(f"Could not get user_id for API key, using default")
            user_id = 'avinash'
        
        # Create order manager
        order_manager = OrderManager(user_id)
        
        # Prepare order data
        order_data = {
            'symbol': symbol,
            'exchange': exchange,
            'action': action,
            'quantity': quantity,
            'price': float(price),
            'price_type': 'MARKET',
            'product': 'MIS',
            'strategy': strategy_name
        }
        
        # Place order using order manager
        success, response, status_code = order_manager.place_order(order_data)
        
        if success:
            logger.info(f"Placed {action} order for {strategy_name}: {symbol} @ {price}")
            return True
        else:
            logger.warning(f"Failed to place {action} order for {strategy_name}: {symbol} - {response.get('message', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"Error placing order in sandbox: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_strategies_on_historical_data():
    """Run all strategies on historical data for multiple periods"""
    with app.app_context():
        # Ensure analyze mode is enabled
        set_analyze_mode(True)
        
        # Get API key
        api_key = get_api_key_for_tradingview('avinash')
        if not api_key:
            logger.error("No API key found")
            return
        
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
            
            # Fetch historical data for NIFTY (most strategies use this)
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            success, response, status = get_history(
                symbol='NIFTY',
                exchange='NSE_INDEX',
                interval='5m',  # 5-minute candles
                start_date=start_str,
                end_date=end_str,
                api_key=api_key
            )
            
            if not success:
                logger.warning(f"Failed to fetch historical data for {period_name}: {response.get('message')}")
                continue
            
            data = response.get('data', [])
            if not data:
                logger.warning(f"No historical data for {period_name}")
                continue
            
            historical_df = pd.DataFrame(data)
            if 'timestamp' in historical_df.columns:
                historical_df['timestamp'] = pd.to_datetime(historical_df['timestamp'])
                historical_df = historical_df.sort_values('timestamp').reset_index(drop=True)
            
            print(f"Loaded {len(historical_df)} data points for {period_name}")
            
            period_results = []
            
            # Run each strategy on this historical data
            for strategy_id, strategy_config in STRATEGY_CONFIGS.items():
                try:
                    result = simulate_strategy_on_historical_data(
                        strategy_id, strategy_config, historical_df, period_name, api_key
                    )
                    if result:
                        period_results.append(result)
                        print(f"  ✓ {result['strategy']}: {result['trades_placed']} trades placed")
                except Exception as e:
                    logger.error(f"Error running {strategy_id} on {period_name}: {e}")
                    import traceback
                    traceback.print_exc()
            
            all_results[period_name] = period_results
            print(f"\n{period_name} Summary: {len(period_results)} strategies executed, {sum(r['trades_placed'] for r in period_results)} total trades")
        
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


