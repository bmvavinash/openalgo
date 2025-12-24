#!/usr/bin/env python
"""
EMA Crossover Trading Strategy
Buy when fast EMA crosses above slow EMA, Sell when it crosses below
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

# Configure logging
log_dir = Path(__file__).parent.parent.parent / 'log' / 'strategies'
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / f"ema_crossover_{datetime.now().strftime('%Y%m%d')}.log"
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
strategy_config = config.get_strategy_config('ema_crossover')
historical_config = config.get_historical_data_config()
risk_config = config.get_risk_management_config()

# Strategy parameters
STRATEGY_NAME = "EMA Crossover Strategy"
FAST_PERIOD = strategy_config.get('fast_period', 9) if strategy_config else 9
SLOW_PERIOD = strategy_config.get('slow_period', 21) if strategy_config else 21
SYMBOLS = strategy_config.get('symbols', ['NIFTY', 'BANKNIFTY']) if strategy_config else ['NIFTY', 'BANKNIFTY']
EXCHANGE = trading_config.get('exchanges', ['NSE'])[0]
PRODUCT = trading_config.get('product_type', 'MIS')
QUANTITY = trading_config.get('quantity', 1)

# API configuration
API_KEY = os.getenv('OPENALGO_API_KEY', '4cc7880936b3c43a73c1d01dc0e2a94a1cd5a765dd2e842de5a55bfda29eac47')
HOST = os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000')

# Initialize OpenAlgo client
client = api(api_key=API_KEY, host=HOST) if API_KEY else None

# Track positions
positions = {symbol: 0 for symbol in SYMBOLS}


def calculate_ema(data: pd.DataFrame, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return data['close'].ewm(span=period, adjust=False).mean()


def calculate_signals(df: pd.DataFrame) -> dict:
    """Calculate EMA crossover signals"""
    try:
        if len(df) < SLOW_PERIOD:
            return {'buy': False, 'sell': False, 'fast_ema': None, 'slow_ema': None}
        
        # Calculate EMAs
        ema_fast = calculate_ema(df, FAST_PERIOD)
        ema_slow = calculate_ema(df, SLOW_PERIOD)
        
        # Get current and previous values
        curr_fast = ema_fast.iloc[-1]
        prev_fast = ema_fast.iloc[-2] if len(ema_fast) > 1 else curr_fast
        curr_slow = ema_slow.iloc[-1]
        prev_slow = ema_slow.iloc[-2] if len(ema_slow) > 1 else curr_slow
        
        # Crossover signals
        buy_signal = (prev_fast < prev_slow) and (curr_fast > curr_slow)
        sell_signal = (prev_fast > prev_slow) and (curr_fast < curr_slow)
        
        return {
            'buy': buy_signal,
            'sell': sell_signal,
            'fast_ema': curr_fast,
            'slow_ema': curr_slow,
            'price': df['close'].iloc[-1]
        }
    
    except Exception as e:
        logger.error(f"Error calculating signals: {e}")
        return {'buy': False, 'sell': False, 'fast_ema': None, 'slow_ema': None}


def fetch_historical_data(symbol: str) -> pd.DataFrame:
    """Fetch historical data for backtesting/training"""
    try:
        period = historical_config.get('period', '1Y')
        interval = historical_config.get('interval', '5m')
        source = historical_config.get('source', 'nse')
        
        # Safety check: Yahoo Finance only supports ~60 days of 5-minute data
        # Auto-adjust if incompatible period/interval combination detected
        if source == 'nse' and interval in ('5m', '1m', '15m'):
            # Check if period is too long for intraday intervals
            period_days = {
                '1Y': 365, '6M': 180, '3M': 90, '2M': 60, '1M': 30, '1W': 7,
                '60d': 60, '30d': 30, '7d': 7
            }
            days = period_days.get(period, 365)
            if days > 60:
                logger.warning(f"Period '{period}' ({days} days) too long for {interval} interval. "
                             f"Yahoo Finance only supports ~60 days for intraday data. Auto-adjusting to '60d'.")
                period = '60d'
        
        # Use NSE data fetcher for free data
        if source == 'nse':
            df = get_nse_data(
                symbol=symbol,
                exchange=EXCHANGE,
                interval=interval,
                period=period,
                source='yfinance'  # Use yfinance as it's more reliable
            )
        else:
            # Use OpenAlgo API if available
            if client:
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
                df = client.history(
                    symbol=symbol,
                    exchange=EXCHANGE,
                    interval=interval,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                df = pd.DataFrame()
        
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
                
                # Execute sell order
                elif signals['sell'] and current_position >= 0:
                    logger.info(f"SELL SIGNAL for {symbol}")
                    logger.info(f"  Fast EMA: {signals['fast_ema']:.2f}, Slow EMA: {signals['slow_ema']:.2f}")
                    logger.info(f"  Current Price: {signals['price']:.2f}")
                    
                    response = place_order(symbol, "SELL", QUANTITY)
                    if response.get('status') == 'success':
                        positions[symbol] = -QUANTITY
                
                # Log current status
                fast_ema_str = f"{signals['fast_ema']:.2f}" if signals['fast_ema'] is not None else 'N/A'
                slow_ema_str = f"{signals['slow_ema']:.2f}" if signals['slow_ema'] is not None else 'N/A'
                logger.debug(f"{symbol} - Position: {current_position}, Fast EMA: {fast_ema_str}, Slow EMA: {slow_ema_str}")
            
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


