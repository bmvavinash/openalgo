"""
Market Watch Blueprint - Live position tracking with real-time P&L updates
"""
from flask import Blueprint, render_template, session, redirect, url_for, flash
from database.auth_db import get_api_key_for_tradingview, get_auth_token
from database.settings_db import get_analyze_mode
from services.positionbook_service import get_positionbook
from utils.session import check_session_validity
from utils.logging import get_logger
from limiter import limiter
import os

logger = get_logger(__name__)

API_RATE_LIMIT = os.getenv("API_RATE_LIMIT", "50 per second")

marketwatch_bp = Blueprint('marketwatch_bp', __name__, url_prefix='/marketwatch')

@marketwatch_bp.route('/')
@check_session_validity
@limiter.limit(API_RATE_LIMIT)
def marketwatch():
    """Market Watch - Live position tracking with real-time P&L"""
    login_username = session['user']

    # Check if in analyze mode or paper trading mode
    analyze_mode = get_analyze_mode()
    paper_trading = session.get('paper_trading_mode', False)

    if analyze_mode or paper_trading:
        # Get API key for sandbox/paper trading mode
        api_key = get_api_key_for_tradingview(login_username)
        logger.info(f"Market Watch - API key retrieval for user {login_username}: {'Found' if api_key else 'NOT FOUND'}, length: {len(api_key) if api_key else 0}")
        if api_key:
            logger.debug(f"Market Watch - API key first 10 chars: {api_key[:10]}... (last 4: ...{api_key[-4:]})")
            success, response, status_code = get_positionbook(api_key=api_key)
        else:
            logger.error(f"Market Watch - No API key found for user {login_username} in analyze/paper trading mode")
            flash('API key required for paper trading mode. Please generate an API key in Settings → API Keys.', 'error')
            return redirect(url_for('api_key_bp.manage_api_key'))
    else:
        # Live broker mode - check for auth token and broker
        auth_token = get_auth_token(login_username)
        if auth_token is None:
            logger.warning(f"Market Watch - No auth token found for user {login_username}")
            return redirect(url_for('auth.logout'))
        broker = session.get('broker')
        if not broker:
            logger.error("Market Watch - Broker not set in session")
            return "Broker not set in session", 400
        success, response, status_code = get_positionbook(auth_token=auth_token, broker=broker)

    if not success:
        logger.error(f"Market Watch - Failed to get positions data: {response.get('message', 'Unknown error')}")
        if status_code == 404:
            return "Failed to import broker module", 500
        # Don't redirect to logout if it's an API key issue - show error instead
        if 'Invalid openalgo apikey' in str(response.get('message', '')):
            flash('Invalid API key. Please generate a new API key in Settings → API Keys.', 'error')
            return redirect(url_for('api_key_bp.manage_api_key'))
        return redirect(url_for('auth.logout'))

    positions_data = response.get('data', [])

    return render_template('marketwatch.html', positions_data=positions_data)

