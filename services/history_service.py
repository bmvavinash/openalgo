import importlib
import traceback
import pandas as pd
from typing import Tuple, Dict, Any, Optional, List, Union
from database.auth_db import get_auth_token_broker
from utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

def import_broker_module(broker_name: str) -> Optional[Any]:
    """
    Dynamically import the broker-specific data module.
    
    Args:
        broker_name: Name of the broker
        
    Returns:
        The imported module or None if import fails
    """
    try:
        module_path = f'broker.{broker_name}.api.data'
        broker_module = importlib.import_module(module_path)
        return broker_module
    except ImportError as error:
        logger.error(f"Error importing broker module '{module_path}': {error}")
        return None

def get_history_with_auth(
    auth_token: str, 
    feed_token: Optional[str], 
    broker: str, 
    symbol: str, 
    exchange: str, 
    interval: str, 
    start_date: str, 
    end_date: str
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Get historical data for a symbol using provided auth tokens.
    
    Args:
        auth_token: Authentication token for the broker API
        feed_token: Feed token for market data (if required by broker)
        broker: Name of the broker
        symbol: Trading symbol
        exchange: Exchange (e.g., NSE, BSE)
        interval: Time interval (e.g., 1m, 5m, 15m, 1h, 1d)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        include_oi: Whether to include Open Interest data (if supported by broker)
        
    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    broker_module = import_broker_module(broker)
    if broker_module is None:
        return False, {
            'status': 'error',
            'message': 'Broker-specific module not found'
        }, 404

    try:
        # Initialize broker's data handler based on broker's requirements
        if hasattr(broker_module.BrokerData.__init__, '__code__'):
            # Check number of parameters the broker's __init__ accepts
            param_count = broker_module.BrokerData.__init__.__code__.co_argcount
            if param_count > 2:  # More than self and auth_token
                data_handler = broker_module.BrokerData(auth_token, feed_token)
            else:
                data_handler = broker_module.BrokerData(auth_token)
        else:
            # Fallback to just auth token if we can't inspect
            data_handler = broker_module.BrokerData(auth_token)

        # Call the broker's get_history method
        df = data_handler.get_history(
            symbol,
            exchange,
            interval,
            start_date,
            end_date
        )
        
        if not isinstance(df, pd.DataFrame):
            raise ValueError("Invalid data format returned from broker")
            
        # Ensure all responses include 'oi' field, set to 0 if not present
        if 'oi' not in df.columns:
            df['oi'] = 0
            
        return True, {
            'status': 'success',
            'data': df.to_dict(orient='records')
        }, 200
    except Exception as e:
        logger.error(f"Error in broker_module.get_history: {e}")
        traceback.print_exc()
        return False, {
            'status': 'error',
            'message': str(e)
        }, 500

def get_history(
    symbol: str, 
    exchange: str, 
    interval: str, 
    start_date: str, 
    end_date: str,
    api_key: Optional[str] = None, 
    auth_token: Optional[str] = None, 
    feed_token: Optional[str] = None, 
    broker: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Get historical data for a symbol.
    Supports both API-based authentication and direct internal calls.
    
    Args:
        symbol: Trading symbol
        exchange: Exchange (e.g., NSE, BSE)
        interval: Time interval (e.g., 1m, 5m, 15m, 1h, 1d)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        api_key: OpenAlgo API key (for API-based calls)
        auth_token: Direct broker authentication token (for internal calls)
        feed_token: Direct broker feed token (for internal calls)
        broker: Direct broker name (for internal calls)
        
    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    # Case 1: API-based authentication
    if api_key and not (auth_token and broker):
        # In analyze mode, allow history to proceed even if API key validation fails
        # This enables paper trading without valid broker credentials
        from database.settings_db import get_analyze_mode
        analyze_mode = get_analyze_mode()
        
        AUTH_TOKEN, FEED_TOKEN, broker_name = get_auth_token_broker(api_key, include_feed_token=True)
        if AUTH_TOKEN is None:
            if analyze_mode:
                # In analyze mode, try to fetch historical data using yfinance
                try:
                    import yfinance as yf
                    import pandas as pd
                    from datetime import datetime
                    
                    # Map exchange codes to yfinance symbols
                    symbol_mapping = {
                        'NIFTY': '^NSEI',
                        'BANKNIFTY': '^NSEBANK',
                        'FINNIFTY': '^NSEFIN',
                        'MIDCPNIFTY': '^NSEMIDCP'
                    }
                    
                    yf_symbol = symbol_mapping.get(symbol.upper())
                    if yf_symbol:
                        ticker = yf.Ticker(yf_symbol)
                        
                        # Convert interval to yfinance format
                        interval_map = {
                            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m',
                            '30m': '30m', '1h': '1h', '1d': '1d'
                        }
                        yf_interval = interval_map.get(interval.lower(), '5m')
                        
                        # Calculate period from dates - handle both string and date objects
                        if isinstance(start_date, str):
                            start = datetime.strptime(start_date, '%Y-%m-%d')
                        else:
                            # Already a date/datetime object
                            start = datetime.combine(start_date, datetime.min.time()) if hasattr(start_date, 'date') else start_date
                        
                        if isinstance(end_date, str):
                            end = datetime.strptime(end_date, '%Y-%m-%d')
                        else:
                            # Already a date/datetime object
                            end = datetime.combine(end_date, datetime.min.time()) if hasattr(end_date, 'date') else end_date
                        
                        days_diff = (end - start).days
                        
                        # yfinance: use either period OR start/end, not both
                        # For intraday intervals, limit to 59 days max
                        if yf_interval in ['1m', '3m', '5m', '15m', '30m']:
                            if days_diff <= 59:
                                # Use period for short ranges
                                hist = ticker.history(period=f'{days_diff + 1}d', interval=yf_interval)
                            else:
                                # For longer ranges, use start/end but limit to 59 days
                                limited_start = end - timedelta(days=59)
                                end_date_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)
                                hist = ticker.history(interval=yf_interval, start=limited_start.strftime('%Y-%m-%d'), end=end_date_str)
                        else:
                            # For daily intervals, use start/end
                            start_date_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)
                            end_date_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)
                            hist = ticker.history(interval=yf_interval, start=start_date_str, end=end_date_str)
                        
                        if not hist.empty:
                            # Convert to expected format
                            df = pd.DataFrame({
                                'timestamp': hist.index,
                                'open': hist['Open'].values,
                                'high': hist['High'].values,
                                'low': hist['Low'].values,
                                'close': hist['Close'].values,
                                'volume': hist['Volume'].values,
                                'oi': [0] * len(hist)
                            })
                            
                            logger.info(f"Fetched historical data for {symbol} via yfinance: {len(df)} records")
                            return True, {
                                'status': 'success',
                                'data': df.to_dict(orient='records')
                            }, 200
                except ImportError:
                    logger.warning("yfinance not available, skipping historical data fetch")
                except Exception as e:
                    logger.warning(f"Failed to fetch historical data via yfinance for {symbol}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                
                # Fallback: return empty DataFrame structure
                logger.warning(f"Using empty historical data for {symbol} in analyze mode")
                return True, {
                    'status': 'success',
                    'data': []
                }, 200
            else:
                return False, {
                    'status': 'error',
                    'message': 'Invalid openalgo apikey'
                }, 403
        return get_history_with_auth(
            AUTH_TOKEN, 
            FEED_TOKEN, 
            broker_name, 
            symbol, 
            exchange, 
            interval, 
            start_date, 
            end_date
        )
    
    # Case 2: Direct internal call with auth_token and broker
    elif auth_token and broker:
        return get_history_with_auth(
            auth_token, 
            feed_token, 
            broker, 
            symbol, 
            exchange, 
            interval, 
            start_date, 
            end_date
        )
    
    # Case 3: Invalid parameters
    else:
        return False, {
            'status': 'error',
            'message': 'Either api_key or both auth_token and broker must be provided'
        }, 400
