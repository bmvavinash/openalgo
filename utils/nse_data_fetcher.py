"""
NSE Data Fetcher Utility
Fetches historical market data for NSE indices and stocks
"""

import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not available. Install with: pip install yfinance")


def get_nse_data(symbol: str, exchange: str = 'NSE', interval: str = '5m', 
                 period: str = '1d', source: str = 'yfinance') -> pd.DataFrame:
    """
    Fetch historical market data for NSE symbols
    
    Args:
        symbol: Symbol name (e.g., 'NIFTY', 'BANKNIFTY')
        exchange: Exchange name (default: 'NSE')
        interval: Data interval ('1m', '5m', '15m', '1h', '1d', etc.)
        period: Time period ('1d', '5d', '1mo', '3mo', '1y', etc.)
        source: Data source ('yfinance' or 'nse')
    
    Returns:
        pd.DataFrame: DataFrame with columns: timestamp, open, high, low, close, volume
    """
    if not YFINANCE_AVAILABLE:
        logger.error("yfinance not available. Cannot fetch data.")
        return pd.DataFrame()
    
    try:
        # Map NSE indices to yfinance symbols
        symbol_map = {
            'NIFTY': '^NSEI',
            'BANKNIFTY': '^NSEBANK',
            'FINNIFTY': '^NSEFIN',
            'MIDCPNIFTY': '^NSEMIDCP'
        }
        
        yf_symbol = symbol_map.get(symbol.upper(), f"{symbol}.NS")
        
        logger.debug(f"Fetching {interval} data for {symbol} ({yf_symbol}) for period {period}")
        
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            logger.warning(f"No data available for {symbol} ({yf_symbol})")
            return pd.DataFrame()
        
        # Normalize column names to lowercase
        df.columns = [col.lower() for col in df.columns]
        df.reset_index(inplace=True)
        
        # Ensure timestamp column exists
        if 'date' in df.columns:
            df.rename(columns={'date': 'timestamp'}, inplace=True)
        elif 'datetime' in df.columns:
            df.rename(columns={'datetime': 'timestamp'}, inplace=True)
        elif df.index.name in ['Date', 'Datetime']:
            df.reset_index(inplace=True)
            if len(df.columns) > 0:
                df.rename(columns={df.columns[0]: 'timestamp'}, inplace=True)
        
        # Ensure required columns exist
        required_cols = ['close']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"Missing required columns: {missing_cols}")
            return pd.DataFrame()
        
        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        logger.debug(f"Fetched {len(df)} records for {symbol}")
        return df
    
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}", exc_info=True)
        return pd.DataFrame()



