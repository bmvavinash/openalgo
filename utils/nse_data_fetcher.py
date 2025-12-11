"""
NSE Data Fetcher
Fetches historical market data for NSE symbols using yfinance
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional
from utils.logging import get_logger

logger = get_logger(__name__)

# Mapping for NSE symbols to yfinance tickers
SYMBOL_MAPPING = {
    'NIFTY': '^NSEI',  # Nifty 50
    'BANKNIFTY': '^NSEBANK',  # Bank Nifty
    'FINNIFTY': '^NSFINITY',  # Fin Nifty
    'MIDCPNIFTY': '^NSEMIDCP',  # Midcap Nifty
}

def get_nse_data(symbol: str, exchange: str = 'NSE', interval: str = '5m', period: str = '1W', **kwargs) -> pd.DataFrame:
    """
    Fetch NSE market data using yfinance
    
    Args:
        symbol: Trading symbol (e.g., 'NIFTY', 'BANKNIFTY', or stock symbol)
        exchange: Exchange name (default: 'NSE')
        interval: Data interval ('1m', '5m', '15m', '1h', '1d')
        period: Time period ('1d', '5d', '1W', '1M', '3M', '6M', '1Y')
    
    Returns:
        pd.DataFrame: Historical data with columns: timestamp, open, high, low, close, volume
    """
    try:
        # Accept and ignore extra kwargs (e.g., source) to stay backward compatible
        _ = kwargs

        # Map symbol to yfinance ticker
        ticker = SYMBOL_MAPPING.get(symbol.upper(), symbol)
        
        # For Indian stocks, add .NS suffix if not already present and not an index
        if ticker not in SYMBOL_MAPPING.values() and not ticker.startswith('^'):
            if not ticker.endswith('.NS'):
                ticker = f"{ticker}.NS"
        
        logger.info(f"Fetching {symbol} data from yfinance (intraday {interval} - using period={period}), interval: {interval}")
        
        # For intraday intervals, yfinance has limitations
        # Max 60 days for 1m, 5m, 15m, 1h intervals
        if interval in ['1m', '5m', '15m', '1h']:
            # Convert period to days for intraday
            period_days_map = {
                '1d': 1,
                '5d': 5,
                '1W': 7,
                '1M': 30,
                '3M': 90,
                '6M': 180,
                '1Y': 365
            }
            days = period_days_map.get(period, 7)
            # Limit to 59 days for intraday (yfinance limitation)
            if days > 59:
                days = 59
                logger.info(f"Using period=59d for intraday data (yfinance limitation: max 60 days for intraday intervals)")
            
            # Use period parameter for intraday
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(period=f"{days}d", interval=interval)
        else:
            # For daily intervals, use period directly
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(period=period, interval=interval)
        
        # Ensure df is a DataFrame (handle dict or other types)
        if not isinstance(df, pd.DataFrame):
            logger.warning(f"History call for {symbol} returned {type(df).__name__} instead of DataFrame; converting to empty DataFrame")
            if isinstance(df, dict):
                logger.warning(f"  Dict keys: {list(df.keys()) if df else 'empty'}")
            return pd.DataFrame()

        if df.empty:
            logger.warning(f"No data returned for {symbol} (ticker: {ticker})")
            return pd.DataFrame()
        
        # Rename columns to standard format
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        # Reset index to get timestamp as column
        df = df.reset_index()
        if 'Date' in df.columns:
            df = df.rename(columns={'Date': 'timestamp'})
        elif 'Datetime' in df.columns:
            df = df.rename(columns={'Datetime': 'timestamp'})
        
        # Ensure timestamp column exists
        if 'timestamp' not in df.columns and df.index.name:
            df = df.reset_index()
            if df.index.name:
                df = df.rename(columns={df.index.name: 'timestamp'})
        
        # Select only required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        available_columns = [col for col in required_columns if col in df.columns]
        df = df[available_columns]
        
        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        logger.info(f"Fetched {len(df)} records for {symbol}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}", exc_info=True)
        return pd.DataFrame()

