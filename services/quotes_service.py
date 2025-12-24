import importlib
import traceback
from typing import Tuple, Dict, Any, Optional, Union
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
        # In analyze mode, allow quotes to proceed even if API key validation fails
        # This enables paper trading without valid broker credentials
        from database.settings_db import get_analyze_mode
        analyze_mode = get_analyze_mode()
        
        AUTH_TOKEN, FEED_TOKEN, broker_name = get_auth_token_broker(api_key, include_feed_token=True)
        if AUTH_TOKEN is None:
            if analyze_mode:
                # In analyze mode, try to fetch real quotes using a public market data source
                # Only use synthetic quote as last resort if real quote fetch fails
                try:
                    # Try to use yfinance or other public APIs for live prices
                    import yfinance as yf
                    import pandas as pd
                    
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
                        info = ticker.history(period='1d', interval='1m')
                        if not info.empty:
                            latest_price = float(info['Close'].iloc[-1])
                            if latest_price > 0:
                                logger.info(f"Fetched live quote for {symbol} via yfinance: LTP={latest_price}")
                                return True, {
                                    'status': 'success',
                                    'data': {
                                        'ltp': latest_price,
                                        'symbol': symbol,
                                        'exchange': exchange,
                                        'bid': latest_price * 0.9999,  # Approximate bid
                                        'ask': latest_price * 1.0001,  # Approximate ask
                                        'high': float(info['High'].iloc[-1]) if 'High' in info.columns else latest_price,
                                        'low': float(info['Low'].iloc[-1]) if 'Low' in info.columns else latest_price,
                                        'open': float(info['Open'].iloc[-1]) if 'Open' in info.columns else latest_price,
                                        'prev_close': float(info['Close'].iloc[-2]) if len(info) > 1 else latest_price,
                                        'volume': int(info['Volume'].iloc[-1]) if 'Volume' in info.columns else 0
                                    }
                                }, 200
                except ImportError:
                    logger.debug("yfinance not available, skipping live quote fetch")
                except Exception as e:
                    logger.debug(f"Failed to fetch live quote via yfinance for {symbol}: {e}")
                
                # Fallback to synthetic quote only if real quote fetch failed
                logger.warning(f"Using synthetic quote for {symbol} in analyze mode (real quote fetch failed)")
                return True, {
                    'status': 'success',
                    'data': {
                        'ltp': 25000.0 if 'NIFTY' in symbol.upper() else (55000.0 if 'BANKNIFTY' in symbol.upper() else 100.0),
                        'symbol': symbol,
                        'exchange': exchange
                    }
                }, 200
            else:
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
