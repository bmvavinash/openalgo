from typing import Tuple, Dict, Any, Optional
from database.auth_db import get_auth_token_broker
from utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

def ping_with_auth(auth_token: str, broker: str) -> Tuple[bool, Dict[str, Any], int]:
    """
    Validate auth token and return pong response.
    
    Args:
        auth_token: Authentication token for the broker API
        broker: Name of the broker
        
    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    # Since we've already validated the auth_token by getting here,
    # we can simply return a pong response
    return True, {
        'status': 'success',
        'data': {
            'message': 'pong',
            'broker': broker
        }
    }, 200

def get_ping(api_key: Optional[str] = None, auth_token: Optional[str] = None, broker: Optional[str] = None) -> Tuple[bool, Dict[str, Any], int]:
    """
    Ping endpoint to check API connectivity and authentication.
    Supports both API-based authentication and direct internal calls.
    
    Args:
        api_key: OpenAlgo API key (for API-based calls)
        auth_token: Direct broker authentication token (for internal calls)
        broker: Direct broker name (for internal calls)
        
    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    # Case 1: API-based authentication
    if api_key and not (auth_token and broker):
        # Check if in analyze/paper trading mode - allow without broker auth
        analyze_mode = get_analyze_mode()
        
        if analyze_mode:
            # In paper trading mode, verify API key but don't require broker auth
            from database.auth_db import verify_api_key
            user_id = verify_api_key(api_key)
            if not user_id:
                error_response = {
                    'status': 'error',
                    'message': 'Invalid openalgo apikey'
                }
                return False, error_response, 403
            
            # API key is valid - route to sandbox or return success for paper trading
            logger.info(f"Paper trading mode: API key valid for user_id={user_id}")
            # For order placement services, route to sandbox
            # For read-only services, return empty/sandbox data
            # This will be handled by individual service implementations
        
        # Live trading mode - require broker authentication
        AUTH_TOKEN, broker_name = get_auth_token_broker(api_key)
        if AUTH_TOKEN is None:
            return False, {
                'status': 'error',
                'message': 'Invalid openalgo apikey'
            }, 403
        return ping_with_auth(AUTH_TOKEN, broker_name)
    
    # Case 2: Direct internal call with auth_token and broker
    elif auth_token and broker:
        return ping_with_auth(auth_token, broker)
    
    # Case 3: Invalid parameters
    else:
        return False, {
            'status': 'error',
            'message': 'Either api_key or both auth_token and broker must be provided'
        }, 400