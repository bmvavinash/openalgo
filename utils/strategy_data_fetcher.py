"""
Strategy Data Fetcher
Unified data fetching utility for trading strategies
Supports both live and historical data modes
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from utils.nse_data_fetcher import get_nse_data
from utils.logging import get_logger

logger = get_logger(__name__)

# Get data mode from environment
STRATEGY_DATA_MODE = os.getenv('STRATEGY_DATA_MODE', 'live')  # 'live' or 'historical'


def fetch_strategy_data(symbol: str, exchange: str, lookback_period: int, client=None):
    """
    Fetch data for strategy based on STRATEGY_DATA_MODE

    Args:
        symbol: Trading symbol (e.g., 'NIFTY', 'BANKNIFTY')
        exchange: Exchange name (e.g., 'NSE')
        lookback_period: Number of data points to fetch
        client: OpenAlgo client for live data

    Returns:
        pd.DataFrame: Historical data with OHLCV columns
    """
    try:
        if STRATEGY_DATA_MODE.lower() == 'historical':
            # Use historical data for backtesting/testing
            logger.debug(f"Fetching historical data for {symbol} (period: 1W, interval: 5m)")
            df = get_nse_data(
                symbol=symbol,
                exchange=exchange,
                interval='5m',
                period='1W'  # Last week for historical mode
            )

            if df.empty:
                logger.warning(f"No historical data available for {symbol}")
                return pd.DataFrame()

            # Ensure we have enough data points
            if len(df) < lookback_period:
                logger.warning(f"Insufficient historical data for {symbol}: got {len(df)}, need {lookback_period}")
                return pd.DataFrame()

            # Sort by timestamp and return last N points
            df = df.sort_values('timestamp', ascending=False).head(lookback_period)
            df = df.sort_values('timestamp', ascending=True)  # Re-sort for analysis

            logger.debug(f"Fetched {len(df)} historical records for {symbol}")
            return df

        elif STRATEGY_DATA_MODE.lower() == 'live':
            # Use live data for actual trading
            if not client:
                logger.warning("OpenAlgo client not available for live data. Switching to historical mode.")
                return fetch_strategy_data(symbol, exchange, lookback_period, None)

            try:
                # Get real-time quotes from OpenAlgo
                logger.debug(f"Fetching live data for {symbol}")

                # Use the quotes API to get live data
                # For now, fall back to recent historical data as proxy for live
                df = get_nse_data(
                    symbol=symbol,
                    exchange=exchange,
                    interval='5m',
                    period='1D'  # Last day for live mode
                )

                if df.empty:
                    logger.warning(f"No live data available for {symbol}")
                    return pd.DataFrame()

                # Sort by timestamp and return recent data
                df = df.sort_values('timestamp', ascending=False).head(min(lookback_period, 50))  # Max 50 points for live
                df = df.sort_values('timestamp', ascending=True)

                logger.debug(f"Fetched {len(df)} live records for {symbol}")
                return df

            except Exception as e:
                logger.error(f"Error fetching live data for {symbol}: {e}")
                logger.info("Falling back to historical data mode")
                return fetch_strategy_data(symbol, exchange, lookback_period, None)

        else:
            logger.error(f"Invalid STRATEGY_DATA_MODE: {STRATEGY_DATA_MODE}. Use 'live' or 'historical'")
            return pd.DataFrame()

    except Exception as e:
        logger.error(f"Error in fetch_strategy_data for {symbol}: {e}")
        return pd.DataFrame()


def get_historical_data(symbol: str, exchange: str = 'NSE', period: str = '1W', interval: str = '5m'):
    """
    Get historical data with standardized interface

    Args:
        symbol: Trading symbol
        exchange: Exchange name
        period: Time period (1D, 1W, 1M, 3M, 6M, 1Y)
        interval: Data interval (1m, 5m, 15m, 1h, 1d)

    Returns:
        pd.DataFrame: Historical data
    """
    try:
        logger.debug(f"Fetching historical data: {symbol} {exchange} {period} {interval}")
        df = get_nse_data(symbol=symbol, exchange=exchange, interval=interval, period=period)

        if df.empty:
            logger.warning(f"No historical data for {symbol}")
            return pd.DataFrame()

        logger.debug(f"Retrieved {len(df)} records for {symbol}")
        return df

    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}")
        return pd.DataFrame()


def validate_data_quality(df: pd.DataFrame, symbol: str) -> bool:
    """
    Validate data quality and completeness

    Args:
        df: DataFrame to validate
        symbol: Symbol name for logging

    Returns:
        bool: True if data is valid
    """
    if df.empty:
        logger.warning(f"Empty data for {symbol}")
        return False

    required_columns = ['open', 'high', 'low', 'close']
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        logger.error(f"Missing required columns for {symbol}: {missing_columns}")
        return False

    # Check for NaN values
    nan_count = df[required_columns].isna().sum().sum()
    if nan_count > 0:
        logger.warning(f"Found {nan_count} NaN values in {symbol} data")

    # Check for reasonable price ranges
    if df['low'].min() <= 0 or df['high'].max() <= 0:
        logger.warning(f"Invalid price data for {symbol} (prices <= 0)")
        return False

    return True


def get_realtime_quote(symbol: str, exchange: str, client=None):
    """
    Get real-time quote for a symbol

    Args:
        symbol: Trading symbol
        exchange: Exchange name
        client: OpenAlgo client

    Returns:
        dict: Quote data or None
    """
    try:
        if not client:
            logger.warning("No OpenAlgo client available for real-time quotes")
            return None

        # This would use OpenAlgo's quotes API
        # For now, return None to indicate not implemented
        logger.debug(f"Real-time quote requested for {symbol} but not implemented")
        return None

    except Exception as e:
        logger.error(f"Error getting real-time quote for {symbol}: {e}")
        return None






