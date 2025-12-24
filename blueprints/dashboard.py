from flask import Blueprint, render_template, session, redirect, url_for
from database.auth_db import get_auth_token, get_api_key_for_tradingview
from database.settings_db import get_analyze_mode
from services.funds_service import get_funds
from utils.logging import get_logger

logger = get_logger(__name__)

dashboard_bp = Blueprint('dashboard_bp', __name__, url_prefix='/')
scalper_process = None

@dashboard_bp.route('/dashboard')
def dashboard():
    logger.info("Dashboard route called - checking analyze mode")
    # Check if analyze mode is enabled (paper trading) - allow access even without session
    analyze_mode = get_analyze_mode()
    paper_trading = session.get('paper_trading_mode', False)
    logger.info(f"Dashboard: analyze_mode={analyze_mode}, paper_trading={paper_trading}, session_keys={list(session.keys())}")
    
    # In analyze/paper trading mode, allow access without full session
    if analyze_mode or paper_trading:
        login_username = session.get('user', 'guest')  # Use 'guest' as fallback
        logger.info(f"Dashboard accessed in paper trading mode for user: {login_username}")
        
        # Get API key for sandbox mode (if user exists)
        if login_username != 'guest':
            api_key = get_api_key_for_tradingview(login_username)
            if api_key:
                logger.info(f"Calling get_funds with API key for user {login_username}")
                success, response, status_code = get_funds(api_key=api_key)
                logger.info(f"get_funds response: success={success}, status_code={status_code}, has_data={bool(response.get('data'))}")
                if success:
                    margin_data = response.get('data', {})
                    # Ensure margin_data is a dict (not None)
                    if margin_data is None:
                        margin_data = {}
                    logger.info(f"Rendering dashboard with margin_data: {margin_data}")
                    return render_template('dashboard.html', margin_data=margin_data)
                else:
                    logger.warning(f"get_funds failed: {response.get('message', 'Unknown error')}")
        
        # Still render dashboard with empty data in paper trading mode
        logger.info("Rendering dashboard with empty data for paper trading mode")
        # Ensure margin_data has default values for template
        margin_data = {
            'availablecash': '0.00',
            'collateral': '0.00',
            'utiliseddebits': '0.00',
            'm2munrealized': '0.00',
            'm2mrealized': '0.00'
        }
        return render_template('dashboard.html', margin_data=margin_data)
    
    # Live broker mode - require full session validation
    from utils.session import is_session_valid
    if not session.get('logged_in') or not is_session_valid():
        logger.warning("No valid session for dashboard - redirecting to login")
        return redirect(url_for('auth.login'))
    
    login_username = session.get('user')
    if not login_username:
        logger.warning("No user in session for dashboard - redirecting to login")
        return redirect(url_for('auth.login'))
    
    # Live broker mode - require broker
    AUTH_TOKEN = get_auth_token(login_username)
    if AUTH_TOKEN is None:
        logger.warning(f"No auth token found for user {login_username}")
        return redirect(url_for('auth.logout'))

    broker = session.get('broker')
    if not broker:
        logger.error("Broker not set in session for live trading")
        return redirect(url_for('auth.broker_login'))
    
    # Use live broker
    success, response, status_code = get_funds(auth_token=AUTH_TOKEN, broker=broker)
    
    if not success:
        logger.error(f"Failed to get funds data: {response.get('message', 'Unknown error')}")
        if status_code == 404:
            return "Failed to import broker module", 500
        return redirect(url_for('auth.logout'))
    
    margin_data = response.get('data', {})
    
    # Ensure margin_data is a dict (not None)
    if margin_data is None:
        margin_data = {}
    
    # Check if margin_data is empty (authentication failed)
    if not margin_data:
        logger.error(f"Failed to get margin data for user {login_username} - authentication may have expired")
        return redirect(url_for('auth.logout'))
    
    # Check if all values are zero (but don't log warning during known service hours)
    if (margin_data.get('availablecash') == '0.00' and 
        margin_data.get('collateral') == '0.00' and
        margin_data.get('utiliseddebits') == '0.00'):
        # This could be service hours or authentication issue
        # The service already logs the appropriate message
        logger.debug(f"All margin data values are zero for user {login_username}")
    
    return render_template('dashboard.html', margin_data=margin_data)
