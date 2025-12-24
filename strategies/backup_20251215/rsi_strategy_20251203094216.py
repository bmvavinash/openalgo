#!/usr/bin/env python
"""
RSI (Relative Strength Index) Trading Strategy
Buy when RSI < 30 (oversold), Sell when RSI > 70 (overbought)
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openalgo import api
import pandas as pd
import numpy as np
from utils.config_loader import get_config
from utils.nse_data_fetcher import get_nse_data

# Try to import fetch_strategy_data if available (optional)
try:
    from utils.strategy_data_fetcher import fetch_strategy_data
except ImportError:
    fetch_strategy_data = None  # Will use get_nse_data instead

# Configure logging
log_dir = Path(__file__).parent.parent.parent / 'log' / 'strategies'
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / f"rsi_strategy_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Get configuration
config = get_config()
trading_config = config.get_trading_preferences()
strategy_config = config.get_strategy_config('rsi_strategy')
historical_config = config.get_historical_data_config()
risk_config = config.get_risk_management_config()

# Strategy parameters
STRATEGY_NAME = "RSI Strategy"
RSI_PERIOD = strategy_config.get('rsi_period', 14) if strategy_config else 14
OVERSOLD = strategy_config.get('oversold', 30) if strategy_config else 30
OVERBOUGHT = strategy_config.get('overbought', 70) if strategy_config else 70
SYMBOLS = strategy_config.get('symbols', ['NIFTY', 'BANKNIFTY']) if strategy_config else ['NIFTY', 'BANKNIFTY']
EXCHANGE = trading_config.get('exchanges', ['NSE'])[0]
PRODUCT = trading_config.get('product_type', 'MIS')
QUANTITY = trading_config.get('quantity', 1)

# Risk management - Stop Loss
# Get from environment variable first (set by strategy system), then config, then default
STOP_LOSS_PCT = float(os.getenv('STRATEGY_STOP_LOSS_PCT', risk_config.get('stop_loss_pct', 2.0) if risk_config else 2.0))

# API configuration
# Get API key from environment variable
# NOTE: For strategies run through the Python Strategy system, the API key should be set
# in the strategy environment variables. For direct execution, set OPENALGO_API_KEY env var.
API_KEY = os.getenv('OPENALGO_API_KEY', '')
HOST = os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000')

# Initialize OpenAlgo client
client = api(api_key=API_KEY, host=HOST) if API_KEY else None

if not API_KEY:
    logger.warning("No API key found in OPENALGO_API_KEY environment variable.")
    logger.warning("Strategy will run in paper trade mode (orders will be logged but not placed).")
    logger.warning("To enable order placement:")
    logger.warning("  1. Get your API key from: http://127.0.0.1:5000/apikey (after login)")
    logger.warning("  2. Set environment variable: OPENALGO_API_KEY=your_api_key_here")
    logger.warning("  3. Or configure it in the Python Strategy system at: http://127.0.0.1:5000/python")
else:
    logger.info(f"API key found: {API_KEY[:10]}...{API_KEY[-4:]} (length: {len(API_KEY)})")

# Track positions and risk management
positions = {symbol: 0 for symbol in SYMBOLS}
entry_prices = {symbol: None for symbol in SYMBOLS}
stop_loss_prices = {symbol: None for symbol in SYMBOLS}


def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_signals(df: pd.DataFrame) -> dict:
    """Calculate RSI signals"""
    try:
        if len(df) < RSI_PERIOD + 1:
            return {'buy': False, 'sell': False, 'rsi': None}
        
        # Calculate RSI
        rsi = calculate_rsi(df, RSI_PERIOD)
        current_rsi = rsi.iloc[-1]
        
        # Generate signals
        buy_signal = current_rsi < OVERSOLD
        sell_signal = current_rsi > OVERBOUGHT
        
        return {
            'buy': buy_signal,
            'sell': sell_signal,
            'rsi': current_rsi,
            'price': df['close'].iloc[-1]
        }
    
    except Exception as e:
        logger.error(f"Error calculating signals: {e}")
        return {'buy': False, 'sell': False, 'rsi': None}


# Data fetching now uses centralized utility (respects STRATEGY_DATA_MODE env variable)


def check_risk_management(symbol: str, current_price: float) -> bool:
    """Check stop loss, exit if hit"""
    current_position = positions[symbol]
    entry_price = entry_prices[symbol]
    stop_loss_price = stop_loss_prices[symbol]
    
    if current_position == 0 or entry_price is None:
        return False
    
    # Check stop loss for LONG position
    if current_position > 0:  # LONG position
        if stop_loss_price and current_price <= stop_loss_price:
            logger.warning(f"STOP LOSS HIT for {symbol} LONG!")
            logger.warning(f"  Entry: Rs {entry_price:.2f}, Stop Loss: Rs {stop_loss_price:.2f}, Exit: Rs {current_price:.2f}")
            logger.warning(f"  Loss: {((current_price - entry_price) / entry_price) * 100:.2f}%")
            response = place_order(symbol, "SELL", abs(current_position))
            if response.get('status') == 'success':
                positions[symbol] = 0
                entry_prices[symbol] = None
                stop_loss_prices[symbol] = None
                return True
    
    # Check stop loss for SHORT position
    elif current_position < 0:  # SHORT position
        if stop_loss_price and current_price >= stop_loss_price:
            logger.warning(f"STOP LOSS HIT for {symbol} SHORT!")
            logger.warning(f"  Entry: Rs {entry_price:.2f}, Stop Loss: Rs {stop_loss_price:.2f}, Exit: Rs {current_price:.2f}")
            logger.warning(f"  Loss: {((entry_price - current_price) / entry_price) * 100:.2f}%")
            response = place_order(symbol, "BUY", abs(current_position))
            if response.get('status') == 'success':
                positions[symbol] = 0
                entry_prices[symbol] = None
                stop_loss_prices[symbol] = None
                return True
    
    return False


def place_order(symbol: str, action: str, quantity: int):
    """Place order via OpenAlgo API"""
    try:
        if not client:
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
    logger.info(f"Parameters: RSI Period={RSI_PERIOD}, Oversold={OVERSOLD}, Overbought={OVERBOUGHT}")
    logger.info(f"Risk Management: Stop Loss {STOP_LOSS_PCT}%")
    logger.info(f"Symbols: {SYMBOLS}")
    
    while True:
        try:
            for symbol in SYMBOLS:
                # Fetch data - use get_nse_data directly for reliability
                from utils.config_loader import get_config
                config = get_config()
                historical_config = config.get_historical_data_config()
                period = historical_config.get('period', '5d')
                interval = historical_config.get('interval', '5m')
                source = historical_config.get('source', 'nse')
                df = get_nse_data(symbol=symbol, interval=interval, period=period, source=source)
                
                if df.empty:
                    continue
                
                # Get current price
                current_price = df['close'].iloc[-1]
                
                # Check risk management first (stop loss)
                if check_risk_management(symbol, current_price):
                    # Position closed due to stop loss
                    continue
                
                signals = calculate_signals(df)
                current_position = positions[symbol]
                
                if signals['buy'] and current_position <= 0:
                    logger.info(f"BUY SIGNAL for {symbol} - RSI: {signals['rsi']:.2f} (Oversold)")
                    response = place_order(symbol, "BUY", QUANTITY)
                    if response.get('status') == 'success':
                        positions[symbol] = QUANTITY
                        entry_prices[symbol] = signals['price']
                        stop_loss_prices[symbol] = entry_prices[symbol] * (1 - STOP_LOSS_PCT / 100)
                        logger.info(f"  Entry: Rs {entry_prices[symbol]:.2f}")
                        logger.info(f"  Stop Loss: Rs {stop_loss_prices[symbol]:.2f} ({STOP_LOSS_PCT}% below)")
                
                elif signals['sell'] and current_position >= 0:
                    logger.info(f"SELL SIGNAL for {symbol} - RSI: {signals['rsi']:.2f} (Overbought)")
                    response = place_order(symbol, "SELL", QUANTITY)
                    if response.get('status') == 'success':
                        positions[symbol] = -QUANTITY
                        entry_prices[symbol] = signals['price']
                        stop_loss_prices[symbol] = entry_prices[symbol] * (1 + STOP_LOSS_PCT / 100)
                        logger.info(f"  Entry: Rs {entry_prices[symbol]:.2f}")
                        logger.info(f"  Stop Loss: Rs {stop_loss_prices[symbol]:.2f} ({STOP_LOSS_PCT}% above)")
                
                position_str = f"{current_position} @ Rs {entry_prices[symbol]:.2f}" if entry_prices[symbol] else f"{current_position}"
                stop_loss_str = f"Rs {stop_loss_prices[symbol]:.2f}" if stop_loss_prices[symbol] else 'N/A'
                rsi_display = f"{signals['rsi']:.2f}" if signals['rsi'] is not None else 'N/A'
                logger.debug(f"{symbol} - Position: {position_str}, SL: {stop_loss_str}, RSI: {rsi_display}")
            
            time.sleep(60)
        
        except KeyboardInterrupt:
            logger.info("Strategy stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in strategy loop: {e}", exc_info=True)
            time.sleep(30)


if __name__ == "__main__":
    run_strategy()



