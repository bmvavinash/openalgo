#!/usr/bin/env python
"""
EMA Crossover Trading Strategy WITH STOP LOSS
Buy when fast EMA crosses above slow EMA, Sell when it crosses below
Includes 2% stop loss protection
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openalgo import api
import pandas as pd
import numpy as np
from utils.config_loader import get_config
from utils.nse_data_fetcher import get_nse_data

# Configure logging
log_dir = Path(__file__).parent.parent.parent / 'log' / 'strategies'
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / f"ema_crossover_stop_loss_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables from project .env (if available)
load_dotenv(override=False)

# Get configuration
config = get_config()
trading_config = config.get_trading_preferences()
strategy_config = config.get_strategy_config('ema_crossover')
historical_config = config.get_historical_data_config()
risk_config = config.get_risk_management_config()

# Strategy parameters
STRATEGY_NAME = "EMA Crossover Strategy with Stop Loss"
FAST_PERIOD = strategy_config.get('fast_period', 9) if strategy_config else 9
SLOW_PERIOD = strategy_config.get('slow_period', 21) if strategy_config else 21
SYMBOLS = strategy_config.get('symbols', ['NIFTY', 'BANKNIFTY']) if strategy_config else ['NIFTY', 'BANKNIFTY']
EXCHANGE = trading_config.get('exchanges', ['NSE'])[0]
PRODUCT = trading_config.get('product_type', 'MIS')
QUANTITY = trading_config.get('quantity', 1)

# Risk management - Stop Loss and Scalping
# Get from environment variable first (set by strategy system), then config, then default
STOP_LOSS_PCT = float(os.getenv('STRATEGY_STOP_LOSS_PCT', risk_config.get('stop_loss_pct', 2.0) if risk_config else 2.0))
SCALPING_ENABLED = os.getenv('STRATEGY_SCALPING_ENABLED', 'false').lower() == 'true'
SCALPING_PROFIT_TARGET = 0.3  # 0.3% profit target for scalping (can be adjusted)

# API configuration
API_KEY = os.getenv('OPENALGO_API_KEY')
HOST = os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000')

# Initialize OpenAlgo client
client = api(api_key=API_KEY, host=HOST) if API_KEY else None

# Track positions and stop loss levels
positions = {symbol: 0 for symbol in SYMBOLS}
entry_prices = {symbol: None for symbol in SYMBOLS}  # Track entry price for stop loss
stop_loss_prices = {symbol: None for symbol in SYMBOLS}  # Track stop loss price
profit_targets = {symbol: None for symbol in SYMBOLS}  # Track profit target for scalping


def calculate_ema(data: pd.DataFrame, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return data['close'].ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_signals(df: pd.DataFrame) -> dict:
    """Calculate EMA crossover signals"""
    try:
        if len(df) < SLOW_PERIOD:
            return {'buy': False, 'sell': False, 'fast_ema': None, 'slow_ema': None, 'price': None}
        
        # Calculate EMAs
        ema_fast = calculate_ema(df, FAST_PERIOD)
        ema_slow = calculate_ema(df, SLOW_PERIOD)
        
        # Get current and previous values
        curr_fast = ema_fast.iloc[-1]
        prev_fast = ema_fast.iloc[-2] if len(ema_fast) > 1 else curr_fast
        curr_slow = ema_slow.iloc[-1]
        prev_slow = ema_slow.iloc[-2] if len(ema_slow) > 1 else curr_slow
        
        # Crossover signals
        buy_crossover = (prev_fast < prev_slow) and (curr_fast > curr_slow)
        sell_crossover = (prev_fast > prev_slow) and (curr_fast < curr_slow)
        
        # RSI filter to avoid extreme conditions (less restrictive)
        rsi = calculate_rsi(df, 14)
        curr_rsi = rsi.iloc[-1] if len(rsi) > 0 and not pd.isna(rsi.iloc[-1]) else 50
        rsi_ok_buy = curr_rsi < 75  # Allow more room, avoid only extreme overbought
        rsi_ok_sell = curr_rsi > 25  # Allow more room, avoid only extreme oversold
        
        # Combined signals with RSI filter
        buy_signal = buy_crossover and rsi_ok_buy
        sell_signal = sell_crossover and rsi_ok_sell
        
        return {
            'buy': buy_signal,
            'sell': sell_signal,
            'fast_ema': curr_fast,
            'slow_ema': curr_slow,
            'price': df['close'].iloc[-1],
            'rsi': curr_rsi
        }
    
    except Exception as e:
        logger.error(f"Error calculating signals: {e}")
        return {'buy': False, 'sell': False, 'fast_ema': None, 'slow_ema': None, 'price': None}


def check_stop_loss(symbol: str, current_price: float) -> bool:
    """Check if stop loss is hit and exit position if needed"""
    current_position = positions[symbol]
    entry_price = entry_prices[symbol]
    stop_loss_price = stop_loss_prices[symbol]
    
    if current_position == 0 or entry_price is None or stop_loss_price is None:
        return False
    
    # Check stop loss for LONG position
    if current_position > 0:  # LONG position
        if current_price <= stop_loss_price:
            logger.warning(f"STOP LOSS HIT for {symbol} LONG position!")
            logger.warning(f"  Entry Price: {entry_price:.2f}")
            logger.warning(f"  Stop Loss: {stop_loss_price:.2f}")
            logger.warning(f"  Current Price: {current_price:.2f}")
            logger.warning(f"  Loss: {((current_price - entry_price) / entry_price) * 100:.2f}%")
            
            # Exit position
            response = place_order(symbol, "SELL", abs(current_position))
            if response.get('status') == 'success':
                positions[symbol] = 0
                entry_prices[symbol] = None
                stop_loss_prices[symbol] = None
                profit_targets[symbol] = None
                logger.info(f"Exited {symbol} position due to stop loss")
                return True
    
    # Check stop loss for SHORT position
    elif current_position < 0:  # SHORT position
        if current_price >= stop_loss_price:
            logger.warning(f"STOP LOSS HIT for {symbol} SHORT position!")
            logger.warning(f"  Entry Price: {entry_price:.2f}")
            logger.warning(f"  Stop Loss: {stop_loss_price:.2f}")
            logger.warning(f"  Current Price: {current_price:.2f}")
            logger.warning(f"  Loss: {((entry_price - current_price) / entry_price) * 100:.2f}%")
            
            # Exit position
            response = place_order(symbol, "BUY", abs(current_position))
            if response.get('status') == 'success':
                positions[symbol] = 0
                entry_prices[symbol] = None
                stop_loss_prices[symbol] = None
                profit_targets[symbol] = None
                logger.info(f"Exited {symbol} position due to stop loss")
                return True
    
    return False


def check_scalping_profit(symbol: str, current_price: float) -> bool:
    """Check if scalping profit target is reached and exit position if needed"""
    if not SCALPING_ENABLED:
        return False
    
    current_position = positions[symbol]
    entry_price = entry_prices[symbol]
    profit_target = profit_targets[symbol]
    
    if current_position == 0 or entry_price is None or profit_target is None:
        return False
    
    # Check profit target for LONG position
    if current_position > 0:  # LONG position
        if current_price >= profit_target:
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            logger.info(f"SCALPING PROFIT TARGET REACHED for {symbol} LONG position!")
            logger.info(f"  Entry Price: {entry_price:.2f}")
            logger.info(f"  Profit Target: {profit_target:.2f}")
            logger.info(f"  Current Price: {current_price:.2f}")
            logger.info(f"  Profit: {profit_pct:.2f}%")
            
            # Exit position
            response = place_order(symbol, "SELL", abs(current_position))
            if response.get('status') == 'success':
                positions[symbol] = 0
                entry_prices[symbol] = None
                stop_loss_prices[symbol] = None
                profit_targets[symbol] = None
                logger.info(f"Exited {symbol} position due to scalping profit target")
                return True
    
    # Check profit target for SHORT position
    elif current_position < 0:  # SHORT position
        if current_price <= profit_target:
            profit_pct = ((entry_price - current_price) / entry_price) * 100
            logger.info(f"SCALPING PROFIT TARGET REACHED for {symbol} SHORT position!")
            logger.info(f"  Entry Price: {entry_price:.2f}")
            logger.info(f"  Profit Target: {profit_target:.2f}")
            logger.info(f"  Current Price: {current_price:.2f}")
            logger.info(f"  Profit: {profit_pct:.2f}%")
            
            # Exit position
            response = place_order(symbol, "BUY", abs(current_position))
            if response.get('status') == 'success':
                positions[symbol] = 0
                entry_prices[symbol] = None
                stop_loss_prices[symbol] = None
                profit_targets[symbol] = None
                logger.info(f"Exited {symbol} position due to scalping profit target")
                return True
    
    return False


def fetch_historical_data(symbol: str) -> pd.DataFrame:
    """Fetch historical data for symbol"""
    try:
        period = historical_config.get('period', '1Y')
        interval = historical_config.get('interval', '5m')
        source = historical_config.get('source', 'nse')
        
        # Safety check for yfinance intraday data limitation
        if source == 'yfinance' and interval in ('1m', '5m', '15m', '1h'):
            # If period is longer than ~60 days, force it to 59d for intraday
            if period not in ('59d', '60d', '2M', '1M', '1W', '7d', '30d'):
                logger.warning(f"yfinance limitation: Intraday interval {interval} with period {period} is too long. Adjusting to '59d'.")
                period = '59d'
        
        df = get_nse_data(symbol=symbol, interval=interval, period=period, source=source)
        
        if df.empty:
            logger.warning(f"No historical data available for {symbol}")
            return pd.DataFrame()
        
        logger.info(f"Fetched {len(df)} records for {symbol}")
        return df
    
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}")
        return pd.DataFrame()


def place_order(symbol: str, action: str, quantity: int):
    """Place order via OpenAlgo API"""
    try:
        if not client:
            logger.warning("OpenAlgo client not initialized. Running in paper trading mode.")
            logger.info(f"PAPER TRADE: {action} {quantity} {symbol} at MARKET")
            return {'status': 'success', 'message': 'Paper trade logged'}
        
        response = client.placesmartorder(
            strategy=STRATEGY_NAME,
            symbol=symbol,
            action=action,
            exchange=EXCHANGE,
            price_type="MARKET",
            product=PRODUCT,
            quantity=quantity,
            position_size=quantity if action == "BUY" else -quantity
        )
        
        logger.info(f"Order placed: {action} {quantity} {symbol} - Response: {response}")
        return response
    
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return {'status': 'error', 'message': str(e)}


def run_strategy():
    """Main strategy loop"""
    logger.info(f"Starting {STRATEGY_NAME}")
    logger.info(f"Parameters: Fast EMA={FAST_PERIOD}, Slow EMA={SLOW_PERIOD}")
    logger.info(f"Stop Loss: {STOP_LOSS_PCT}%")
    logger.info(f"Scalping Enabled: {SCALPING_ENABLED}")
    if SCALPING_ENABLED:
        logger.info(f"Scalping Profit Target: {SCALPING_PROFIT_TARGET}%")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info(f"Exchange: {EXCHANGE}, Product: {PRODUCT}, Quantity: {QUANTITY}")
    
    while True:
        try:
            for symbol in SYMBOLS:
                # Fetch historical data
                df = fetch_historical_data(symbol)
                
                if df.empty:
                    logger.warning(f"Skipping {symbol} - no data available")
                    continue
                
                # Get current price
                current_price = df['close'].iloc[-1]
                
                # Check stop loss first (before checking new signals)
                if check_stop_loss(symbol, current_price):
                    # Stop loss was hit, position closed
                    continue
                
                # Check scalping profit target (if scalping enabled)
                if check_scalping_profit(symbol, current_price):
                    # Profit target reached, position closed
                    continue
                
                # Calculate signals
                signals = calculate_signals(df)
                
                current_position = positions[symbol]
                
                # Execute buy order
                if signals['buy'] and current_position <= 0:
                    logger.info(f"BUY SIGNAL for {symbol}")
                    logger.info(f"  Fast EMA: {signals['fast_ema']:.2f}, Slow EMA: {signals['slow_ema']:.2f}")
                    logger.info(f"  Current Price: {signals['price']:.2f}")
                    
                    response = place_order(symbol, "BUY", QUANTITY)
                    if response.get('status') == 'success':
                        positions[symbol] = QUANTITY
                        entry_prices[symbol] = signals['price']
                        # Set stop loss below entry price for LONG
                        stop_loss_prices[symbol] = entry_prices[symbol] * (1 - STOP_LOSS_PCT / 100)
                        # Set profit target for scalping (if enabled)
                        if SCALPING_ENABLED:
                            profit_targets[symbol] = entry_prices[symbol] * (1 + SCALPING_PROFIT_TARGET / 100)
                        logger.info(f"  Entry Price: {entry_prices[symbol]:.2f}")
                        logger.info(f"  Stop Loss Set: {stop_loss_prices[symbol]:.2f} ({STOP_LOSS_PCT}% below entry)")
                        if SCALPING_ENABLED:
                            logger.info(f"  Profit Target Set: {profit_targets[symbol]:.2f} ({SCALPING_PROFIT_TARGET}% above entry)")
                
                # Execute sell order
                elif signals['sell'] and current_position >= 0:
                    logger.info(f"SELL SIGNAL for {symbol}")
                    logger.info(f"  Fast EMA: {signals['fast_ema']:.2f}, Slow EMA: {signals['slow_ema']:.2f}")
                    logger.info(f"  Current Price: {signals['price']:.2f}")
                    
                    response = place_order(symbol, "SELL", QUANTITY)
                    if response.get('status') == 'success':
                        positions[symbol] = -QUANTITY
                        entry_prices[symbol] = signals['price']
                        # Set stop loss above entry price for SHORT
                        stop_loss_prices[symbol] = entry_prices[symbol] * (1 + STOP_LOSS_PCT / 100)
                        # Set profit target for scalping (if enabled)
                        if SCALPING_ENABLED:
                            profit_targets[symbol] = entry_prices[symbol] * (1 - SCALPING_PROFIT_TARGET / 100)
                        logger.info(f"  Entry Price: {entry_prices[symbol]:.2f}")
                        logger.info(f"  Stop Loss Set: {stop_loss_prices[symbol]:.2f} ({STOP_LOSS_PCT}% above entry)")
                        if SCALPING_ENABLED:
                            logger.info(f"  Profit Target Set: {profit_targets[symbol]:.2f} ({SCALPING_PROFIT_TARGET}% below entry)")
                
                # Log current status
                fast_ema_str = f"{signals['fast_ema']:.2f}" if signals['fast_ema'] is not None else 'N/A'
                slow_ema_str = f"{signals['slow_ema']:.2f}" if signals['slow_ema'] is not None else 'N/A'
                position_str = f"{current_position} @ {entry_prices[symbol]:.2f}" if entry_prices[symbol] else f"{current_position}"
                stop_loss_str = f"{stop_loss_prices[symbol]:.2f}" if stop_loss_prices[symbol] else 'N/A'
                logger.debug(f"{symbol} - Position: {position_str}, Stop Loss: {stop_loss_str}, Fast EMA: {fast_ema_str}, Slow EMA: {slow_ema_str}")
            
            # Wait before next iteration
            time.sleep(60)  # Check every minute
        
        except KeyboardInterrupt:
            logger.info("Strategy stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in strategy loop: {e}", exc_info=True)
            time.sleep(30)  # Wait before retrying


if __name__ == "__main__":
    run_strategy()


