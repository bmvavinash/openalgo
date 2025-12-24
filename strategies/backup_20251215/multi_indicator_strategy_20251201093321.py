#!/usr/bin/env python
"""
Multi-Indicator Trading Strategy
Combines MACD, EMA, RSI, and Trend Filter with Stop Loss & Take Profit

Strategy Logic:
- Primary Signal: MACD crossover (highest win rate in backtests)
- Trend Filter: 50-day EMA (only trade with trend)
- Momentum Filter: RSI (avoid extreme overbought/oversold)
- Risk Management: 2% Stop Loss, 4% Take Profit
- Entry: MACD bullish + Price above 50 EMA + RSI not overbought
- Exit: MACD bearish OR Stop Loss OR Take Profit
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

log_file = log_dir / f"multi_indicator_{datetime.now().strftime('%Y%m%d')}.log"
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
risk_config = config.get_risk_management_config()

# Strategy parameters
STRATEGY_NAME = "Multi-Indicator Strategy (MACD+EMA+RSI)"
SYMBOLS = trading_config.get('symbols', ['NIFTY', 'BANKNIFTY'])
EXCHANGE = trading_config.get('exchanges', ['NSE'])[0]
PRODUCT = trading_config.get('product_type', 'MIS')
QUANTITY = trading_config.get('quantity', 1)

# Optimal intervals per symbol (based on backtesting)
# Multi-Indicator performs best on NIFTY with 5m (Rs +217.30 profit)
SYMBOL_INTERVALS = {
    'NIFTY': '5m',       # 33.3% win rate, Rs +217.30 profit
    'BANKNIFTY': '5m'   # Still testing, but 5m is default
}

# Indicator parameters (optimized from backtest results)
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
EMA_FAST = 9
EMA_SLOW = 21
EMA_TREND = 50  # Longer trend filter
RSI_PERIOD = 14
RSI_OVERBOUGHT = 65  # More conservative than 70
RSI_OVERSOLD = 35  # More conservative than 30

# Risk management - Stop Loss & Take Profit
# Get from environment variable first (set by strategy system), then config, then default
STOP_LOSS_PCT = float(os.getenv('STRATEGY_STOP_LOSS_PCT', risk_config.get('stop_loss_pct', 2.0) if risk_config else 2.0))
TAKE_PROFIT_PCT = risk_config.get('take_profit_pct', 4.0) if risk_config else 4.0

# API configuration
API_KEY = os.getenv('OPENALGO_API_KEY')
HOST = os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000')

# Initialize OpenAlgo client
client = api(api_key=API_KEY, host=HOST) if API_KEY else None

# Track positions and risk management
positions = {symbol: 0 for symbol in SYMBOLS}
entry_prices = {symbol: None for symbol in SYMBOLS}
stop_loss_prices = {symbol: None for symbol in SYMBOLS}
take_profit_prices = {symbol: None for symbol in SYMBOLS}


def calculate_macd(df: pd.DataFrame) -> tuple:
    """Calculate MACD indicator"""
    ema_fast = df['close'].ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = df['close'].ewm(span=MACD_SLOW, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=MACD_SIGNAL, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram


def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return df['close'].ewm(span=period, adjust=False).mean()


def calculate_rsi(df: pd.DataFrame, period: int = RSI_PERIOD) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_signals(df: pd.DataFrame) -> dict:
    """Calculate multi-indicator signals"""
    try:
        if len(df) < EMA_TREND:
            return {
                'buy': False, 'sell': False,
                'macd': None, 'signal': None, 'rsi': None,
                'ema_fast': None, 'ema_slow': None, 'ema_trend': None,
                'price': None, 'reason': 'Insufficient data'
            }
        
        # Calculate all indicators
        macd, signal, histogram = calculate_macd(df)
        ema_fast = calculate_ema(df, EMA_FAST)
        ema_slow = calculate_ema(df, EMA_SLOW)
        ema_trend = calculate_ema(df, EMA_TREND)
        rsi = calculate_rsi(df)
        
        # Get current and previous values
        curr_macd = macd.iloc[-1]
        prev_macd = macd.iloc[-2] if len(macd) > 1 else curr_macd
        curr_signal = signal.iloc[-1]
        prev_signal = signal.iloc[-2] if len(signal) > 1 else curr_signal
        curr_price = df['close'].iloc[-1]
        curr_rsi = rsi.iloc[-1]
        curr_ema_trend = ema_trend.iloc[-1]
        
        # MACD crossover signals
        macd_bullish = (prev_macd <= prev_signal) and (curr_macd > curr_signal)
        macd_bearish = (prev_macd >= prev_signal) and (curr_macd < curr_signal)
        
        # Trend filter: Price must be above 50 EMA for buy, below for sell
        uptrend = curr_price > curr_ema_trend
        downtrend = curr_price < curr_ema_trend
        
        # RSI filter: Avoid extreme conditions
        rsi_not_overbought = curr_rsi < RSI_OVERBOUGHT
        rsi_not_oversold = curr_rsi > RSI_OVERSOLD
        
        # Combined buy signal: MACD bullish + Uptrend + RSI not overbought
        buy_signal = macd_bullish and uptrend and rsi_not_overbought
        
        # Combined sell signal: MACD bearish + Downtrend + RSI not oversold
        sell_signal = macd_bearish and downtrend and rsi_not_oversold
        
        reason = []
        if buy_signal:
            reason.append("MACD bullish crossover")
            reason.append("Price above 50 EMA (uptrend)")
            reason.append(f"RSI {curr_rsi:.1f} < {RSI_OVERBOUGHT} (not overbought)")
        elif sell_signal:
            reason.append("MACD bearish crossover")
            reason.append("Price below 50 EMA (downtrend)")
            reason.append(f"RSI {curr_rsi:.1f} > {RSI_OVERSOLD} (not oversold)")
        else:
            reason.append("No signal - waiting for confirmation")
        
        return {
            'buy': buy_signal,
            'sell': sell_signal,
            'macd': curr_macd,
            'signal': curr_signal,
            'rsi': curr_rsi,
            'ema_fast': ema_fast.iloc[-1],
            'ema_slow': ema_slow.iloc[-1],
            'ema_trend': curr_ema_trend,
            'price': curr_price,
            'reason': ' | '.join(reason)
        }
    
    except Exception as e:
        logger.error(f"Error calculating signals: {e}")
        return {
            'buy': False, 'sell': False,
            'macd': None, 'signal': None, 'rsi': None,
            'ema_fast': None, 'ema_slow': None, 'ema_trend': None,
            'price': None, 'reason': f'Error: {str(e)}'
        }


def check_risk_management(symbol: str, current_price: float) -> bool:
    """Check stop loss and take profit, exit if hit"""
    current_position = positions[symbol]
    entry_price = entry_prices[symbol]
    stop_loss_price = stop_loss_prices[symbol]
    take_profit_price = take_profit_prices[symbol]
    
    if current_position == 0 or entry_price is None:
        return False
    
    # Check stop loss and take profit for LONG position
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
                take_profit_prices[symbol] = None
                return True
        
        if take_profit_price and current_price >= take_profit_price:
            logger.info(f"TAKE PROFIT HIT for {symbol} LONG!")
            logger.info(f"  Entry: Rs {entry_price:.2f}, Take Profit: Rs {take_profit_price:.2f}, Exit: Rs {current_price:.2f}")
            logger.info(f"  Profit: {((current_price - entry_price) / entry_price) * 100:.2f}%")
            response = place_order(symbol, "SELL", abs(current_position))
            if response.get('status') == 'success':
                positions[symbol] = 0
                entry_prices[symbol] = None
                stop_loss_prices[symbol] = None
                take_profit_prices[symbol] = None
                return True
    
    # Check stop loss and take profit for SHORT position
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
                take_profit_prices[symbol] = None
                return True
        
        if take_profit_price and current_price <= take_profit_price:
            logger.info(f"TAKE PROFIT HIT for {symbol} SHORT!")
            logger.info(f"  Entry: Rs {entry_price:.2f}, Take Profit: Rs {take_profit_price:.2f}, Exit: Rs {current_price:.2f}")
            logger.info(f"  Profit: {((entry_price - current_price) / entry_price) * 100:.2f}%")
            response = place_order(symbol, "BUY", abs(current_position))
            if response.get('status') == 'success':
                positions[symbol] = 0
                entry_prices[symbol] = None
                stop_loss_prices[symbol] = None
                take_profit_prices[symbol] = None
                return True
    
    return False


def fetch_historical_data(symbol: str) -> pd.DataFrame:
    """Fetch historical data for symbol"""
    try:
        from utils.config_loader import get_config
        config = get_config()
        historical_config = config.get_historical_data_config()
        
        period = historical_config.get('period', '5d')  # Use 5d for better intraday data
        # Use optimal interval for this symbol
        interval = SYMBOL_INTERVALS.get(symbol, historical_config.get('interval', '5m'))
        source = historical_config.get('source', 'nse')
        
        # Safety check for yfinance intraday data limitation
        if source == 'yfinance' and interval in ('1m', '5m', '15m', '1h'):
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
    logger.info(f"Indicators: MACD({MACD_FAST}/{MACD_SLOW}/{MACD_SIGNAL}), EMA({EMA_FAST}/{EMA_SLOW}), Trend({EMA_TREND}), RSI({RSI_PERIOD})")
    logger.info(f"Risk Management: Stop Loss {STOP_LOSS_PCT}%, Take Profit {TAKE_PROFIT_PCT}%")
    logger.info(f"RSI Filters: Overbought < {RSI_OVERBOUGHT}, Oversold > {RSI_OVERSOLD}")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info(f"Optimal Intervals: {SYMBOL_INTERVALS}")
    logger.info(f"Note: Multi-Indicator performs best on NIFTY with 5m interval (Rs +217.30 profit in backtests)")
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
                
                # Check risk management first (stop loss / take profit)
                if check_risk_management(symbol, current_price):
                    # Position closed due to stop loss or take profit
                    continue
                
                # Calculate signals
                signals = calculate_signals(df)
                
                current_position = positions[symbol]
                
                # Execute buy order
                if signals['buy'] and current_position <= 0:
                    logger.info(f"BUY SIGNAL for {symbol}")
                    logger.info(f"  MACD: {signals['macd']:.2f}, Signal: {signals['signal']:.2f}")
                    logger.info(f"  RSI: {signals['rsi']:.1f}")
                    logger.info(f"  Price: Rs {signals['price']:.2f}, 50 EMA: Rs {signals['ema_trend']:.2f}")
                    logger.info(f"  Reason: {signals['reason']}")
                    
                    response = place_order(symbol, "BUY", QUANTITY)
                    if response.get('status') == 'success':
                        positions[symbol] = QUANTITY
                        entry_prices[symbol] = signals['price']
                        stop_loss_prices[symbol] = entry_prices[symbol] * (1 - STOP_LOSS_PCT / 100)
                        take_profit_prices[symbol] = entry_prices[symbol] * (1 + TAKE_PROFIT_PCT / 100)
                        logger.info(f"  Entry: Rs {entry_prices[symbol]:.2f}")
                        logger.info(f"  Stop Loss: Rs {stop_loss_prices[symbol]:.2f} ({STOP_LOSS_PCT}% below)")
                        logger.info(f"  Take Profit: Rs {take_profit_prices[symbol]:.2f} ({TAKE_PROFIT_PCT}% above)")
                
                # Execute sell order
                elif signals['sell'] and current_position >= 0:
                    logger.info(f"SELL SIGNAL for {symbol}")
                    logger.info(f"  MACD: {signals['macd']:.2f}, Signal: {signals['signal']:.2f}")
                    logger.info(f"  RSI: {signals['rsi']:.1f}")
                    logger.info(f"  Price: Rs {signals['price']:.2f}, 50 EMA: Rs {signals['ema_trend']:.2f}")
                    logger.info(f"  Reason: {signals['reason']}")
                    
                    response = place_order(symbol, "SELL", QUANTITY)
                    if response.get('status') == 'success':
                        positions[symbol] = -QUANTITY
                        entry_prices[symbol] = signals['price']
                        stop_loss_prices[symbol] = entry_prices[symbol] * (1 + STOP_LOSS_PCT / 100)
                        take_profit_prices[symbol] = entry_prices[symbol] * (1 - TAKE_PROFIT_PCT / 100)
                        logger.info(f"  Entry: Rs {entry_prices[symbol]:.2f}")
                        logger.info(f"  Stop Loss: Rs {stop_loss_prices[symbol]:.2f} ({STOP_LOSS_PCT}% above)")
                        logger.info(f"  Take Profit: Rs {take_profit_prices[symbol]:.2f} ({TAKE_PROFIT_PCT}% below)")
                
                # Log current status
                position_str = f"{current_position} @ Rs {entry_prices[symbol]:.2f}" if entry_prices[symbol] else f"{current_position}"
                stop_loss_str = f"Rs {stop_loss_prices[symbol]:.2f}" if stop_loss_prices[symbol] else 'N/A'
                take_profit_str = f"Rs {take_profit_prices[symbol]:.2f}" if take_profit_prices[symbol] else 'N/A'
                logger.debug(f"{symbol} - Position: {position_str}, SL: {stop_loss_str}, TP: {take_profit_str}, "
                           f"MACD: {signals['macd']:.2f}, RSI: {signals['rsi']:.1f}")
            
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


