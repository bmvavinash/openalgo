import importlib
import traceback
from typing import Tuple, Dict, Any, Optional, Union
from database.auth_db import get_auth_token_broker
from database.settings_db import get_analyze_mode
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

def get_quotes_with_auth(auth_token: str, feed_token: Optional[str], broker: str, symbol: str, exchange: str) -> Tuple[bool, Dict[str, Any], int]:
    """
    Get real-time quotes for a symbol using provided auth tokens.
    
    Args:
        auth_token: Authentication token for the broker API
        feed_token: Feed token for market data (if required by broker)
        broker: Name of the broker
        symbol: Trading symbol
        exchange: Exchange (e.g., NSE, BSE)
        
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
            
        quotes = data_handler.get_quotes(symbol, exchange)
        
        if quotes is None:
            return False, {
                'status': 'error',
                'message': 'Failed to fetch quotes'
            }, 500

        return True, {
            'status': 'success',
            'data': quotes
        }, 200
    except Exception as e:
        # Check if this is a permission error
        error_msg = str(e)
        if 'permission' in error_msg.lower() or 'insufficient' in error_msg.lower():
            # Log at debug level for permission errors (common with personal APIs)
            logger.debug(f"Quote fetch permission denied: {error_msg}")
        else:
            # Log other errors normally
            logger.error(f"Error in broker_module.get_quotes: {e}")
            traceback.print_exc()

        return False, {
            'status': 'error',
            'message': str(e)
        }, 500

def get_quotes(
    symbol: str, 
    exchange: str, 
    api_key: Optional[str] = None, 
    auth_token: Optional[str] = None, 
    feed_token: Optional[str] = None, 
    broker: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Get real-time quotes for a symbol.
    Supports both API-based authentication and direct internal calls.
    
    Args:
        symbol: Trading symbol
        exchange: Exchange (e.g., NSE, BSE)
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
        # If in analyze/paper mode, bypass broker and fetch via sandbox/yfinance
        try:
            if get_analyze_mode():
                success, data, status = _get_sandbox_quote(symbol, exchange)
                return success, data, status
        except Exception:
            # Fallback silently to broker path if any error in analyze mode detection
            pass

        AUTH_TOKEN, FEED_TOKEN, broker_name = get_auth_token_broker(api_key, include_feed_token=True)
        if AUTH_TOKEN is None:
            return False, {
                'status': 'error',
                'message': 'Invalid openalgo apikey'
            }, 403
        return get_quotes_with_auth(AUTH_TOKEN, FEED_TOKEN, broker_name, symbol, exchange)
    
    # Case 2: Direct internal call with auth_token and broker
    elif auth_token and broker:
        return get_quotes_with_auth(auth_token, feed_token, broker, symbol, exchange)
    
    # Case 3: Invalid parameters
    else:
        return False, {
            'status': 'error',
            'message': 'Either api_key or both auth_token and broker must be provided'
        }, 400


def _get_sandbox_quote(symbol: str, exchange: str) -> Tuple[bool, Dict[str, Any], int]:
    """
    Fetch quotes in analyze/paper mode without requiring a broker token.
    Uses yfinance-backed NSE data fetcher as a lightweight source.
    """
    try:
        from utils.nse_data_fetcher import get_nse_data
        import pandas as pd

        # Fetch recent intraday data (1m if available, else 5m)
        df = get_nse_data(symbol, interval='1m', period='1d')
        if not isinstance(df, pd.DataFrame) or df.empty:
            df = get_nse_data(symbol, interval='5m', period='5d')

        if not isinstance(df, pd.DataFrame) or df.empty:
            return False, {
                'status': 'error',
                'message': f'No market data for {symbol}'
            }, 404

        last_row = df.iloc[-1]
        ltp = float(last_row['close'])
        ohlc = {
            'open': float(last_row['open']),
            'high': float(last_row['high']),
            'low': float(last_row['low']),
            'close': float(last_row['close']),
            'prev_close': float(df.iloc[-2]['close']) if len(df) > 1 else float(last_row['close']),
            'volume': float(last_row['volume']) if 'volume' in last_row else 0.0
        }

        quote = {
            'symbol': symbol,
            'exchange': exchange,
            'ltp': ltp,
            'bid': 0,
            'ask': 0,
            **ohlc
        }

        return True, {
            'status': 'success',
            'data': quote
        }, 200
    except Exception as e:
        logger.error(f"Sandbox quote fetch failed for {symbol}: {e}")
        return False, {
            'status': 'error',
            'message': f'Failed to fetch sandbox quote: {str(e)}'
        }, 500

def get_multiquotes_with_auth(auth_token: str, feed_token: Optional[str], broker: str, symbols: list) -> Tuple[bool, Dict[str, Any], int]:
    """
    Get real-time quotes for multiple symbols using provided auth tokens.

    Args:
        auth_token: Authentication token for the broker API
        feed_token: Feed token for market data (if required by broker)
        broker: Name of the broker
        symbols: List of dicts with 'symbol' and 'exchange' keys

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

        # Check if broker supports multiquotes
        if not hasattr(data_handler, 'get_multiquotes'):
            # Fallback: fetch quotes one by one
            logger.debug(f"Broker {broker} doesn't support multiquotes, falling back to individual quotes")
            results = []
            for item in symbols:
                try:
                    quote = data_handler.get_quotes(item['symbol'], item['exchange'])
                    results.append({
                        'symbol': item['symbol'],
                        'exchange': item['exchange'],
                        'data': quote
                    })
                except Exception as e:
                    logger.error(f"Error fetching quote for {item['exchange']}:{item['symbol']}: {e}")
                    results.append({
                        'symbol': item['symbol'],
                        'exchange': item['exchange'],
                        'error': str(e)
                    })

            return True, {
                'status': 'success',
                'results': results
            }, 200

        # Use broker's native multiquotes method
        multiquotes = data_handler.get_multiquotes(symbols)

        if multiquotes is None:
            return False, {
                'status': 'error',
                'message': 'Failed to fetch multiquotes'
            }, 500

        return True, {
            'status': 'success',
            'results': multiquotes
        }, 200
    except Exception as e:
        # Check if this is a permission error
        error_msg = str(e)
        if 'permission' in error_msg.lower() or 'insufficient' in error_msg.lower():
            # Log at debug level for permission errors (common with personal APIs)
            logger.debug(f"Multiquote fetch permission denied: {error_msg}")
        else:
            # Log other errors normally
            logger.error(f"Error in broker_module.get_multiquotes: {e}")
            traceback.print_exc()

        return False, {
            'status': 'error',
            'message': str(e)
        }, 500

def get_multiquotes(
    symbols: list,
    api_key: Optional[str] = None,
    auth_token: Optional[str] = None,
    feed_token: Optional[str] = None,
    broker: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Get real-time quotes for multiple symbols.
    Supports both API-based authentication and direct internal calls.

    Args:
        symbols: List of dicts with 'symbol' and 'exchange' keys
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
        AUTH_TOKEN, FEED_TOKEN, broker_name = get_auth_token_broker(api_key, include_feed_token=True)
        if AUTH_TOKEN is None:
            return False, {
                'status': 'error',
                'message': 'Invalid openalgo apikey'
            }, 403
        return get_multiquotes_with_auth(AUTH_TOKEN, FEED_TOKEN, broker_name, symbols)

    # Case 2: Direct internal call with auth_token and broker
    elif auth_token and broker:
        return get_multiquotes_with_auth(auth_token, feed_token, broker, symbols)

    # Case 3: Invalid parameters
    else:
        return False, {
            'status': 'error',
            'message': 'Either api_key or both auth_token and broker must be provided'
        }, 400
