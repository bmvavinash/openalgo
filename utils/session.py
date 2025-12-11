from datetime import datetime, timedelta
import pytz
from functools import wraps
from flask import session, redirect, url_for, request
from utils.logging import get_logger
import os

logger = get_logger(__name__)

def get_session_expiry_time():
    """Get session expiry time set to 3 AM IST next day"""
    now_utc = datetime.now(pytz.timezone('UTC'))
    now_ist = now_utc.astimezone(pytz.timezone('Asia/Kolkata'))
    
    # Get configured expiry time or default to 3 AM
    expiry_time = os.getenv('SESSION_EXPIRY_TIME', '03:00')
    hour, minute = map(int, expiry_time.split(':'))
    
    target_time_ist = now_ist.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If current time is past target time, set expiry to next day
    if now_ist > target_time_ist:
        target_time_ist += timedelta(days=1)
    
    remaining_time = target_time_ist - now_ist
    logger.debug(f"Session expiry time set to: {target_time_ist}")
    return remaining_time

def set_session_login_time():
    """Set the session login time in IST"""
    now_utc = datetime.now(pytz.timezone('UTC'))
    now_ist = now_utc.astimezone(pytz.timezone('Asia/Kolkata'))
    # Store as ISO format string with timezone info
    session['login_time'] = now_ist.isoformat()
    session.modified = True  # Mark session as modified to ensure it's saved
    logger.info(f"Session login time set to: {now_ist.isoformat()}")

def is_session_valid():
    """Check if the current session is valid"""
    # CRITICAL: Ensure session is loaded by accessing it
    # Sometimes Flask doesn't load the session until it's accessed
    try:
        _ = dict(session)  # Force session load
    except Exception as e:
        logger.error(f"Error accessing session: {e}")
        return False
    
    logger.debug(f"Checking session validity. Session data: {dict(session)}")

    if not session.get('logged_in'):
        logger.warning(f"Session invalid: 'logged_in' flag not set. Session keys: {list(session.keys())}")
        return False
    
    # If no login time is set, consider session invalid
    if 'login_time' not in session:
        logger.warning(f"Session invalid: 'login_time' not in session. Session keys: {list(session.keys())}")
        return False
        
    now_utc = datetime.now(pytz.timezone('UTC'))
    now_ist = now_utc.astimezone(pytz.timezone('Asia/Kolkata'))

    # Parse login time - handle both timezone-aware and naive datetimes
    login_time_str = session['login_time']
    try:
        if isinstance(login_time_str, str):
            login_time = datetime.fromisoformat(login_time_str)
            # If timezone-naive, assume IST
            if login_time.tzinfo is None:
                login_time = pytz.timezone('Asia/Kolkata').localize(login_time)
            # Convert to IST if needed
            if login_time.tzinfo != pytz.timezone('Asia/Kolkata'):
                login_time = login_time.astimezone(pytz.timezone('Asia/Kolkata'))
        else:
            login_time = login_time_str
            if login_time.tzinfo is None:
                login_time = pytz.timezone('Asia/Kolkata').localize(login_time)
            if login_time.tzinfo != pytz.timezone('Asia/Kolkata'):
                login_time = login_time.astimezone(pytz.timezone('Asia/Kolkata'))
    except Exception as e:
        logger.error(f"Error parsing login_time: {e}, value: {login_time_str}")
        return False

    # Calculate session expiry time (same logic as get_session_expiry_time)
    expiry_time = os.getenv('SESSION_EXPIRY_TIME', '03:00')
    hour, minute = map(int, expiry_time.split(':'))

    # Calculate expiry time for the day of login
    login_date = login_time.date()
    session_expiry = pytz.timezone('Asia/Kolkata').localize(
        datetime.combine(login_date, datetime.min.time().replace(hour=hour, minute=minute))
    )
    
    # If login time is past expiry time on login day, expiry is next day
    if login_time > session_expiry:
        session_expiry += timedelta(days=1)

    logger.debug(f"Session check: Current={now_ist}, Login={login_time}, Expiry={session_expiry}, IsExpired={now_ist >= session_expiry}")

    # Check if session has expired (current time >= expiry time)
    if now_ist >= session_expiry:
        logger.info(f"Session expired at {session_expiry} IST (current: {now_ist})")
        return False
    
    logger.debug(f"Session valid. Current time: {now_ist}, Login time: {login_time}, Session expiry: {session_expiry}")
    return True

def revoke_user_tokens():
    """Revoke auth tokens for the current user when session expires"""
    if 'user' in session:
        username = session.get('user')
        try:
            from database.auth_db import upsert_auth, auth_cache, feed_token_cache
            
            # Clear cache entries first to prevent stale data access
            cache_key_auth = f"auth-{username}"
            cache_key_feed = f"feed-{username}"
            if cache_key_auth in auth_cache:
                del auth_cache[cache_key_auth]
            if cache_key_feed in feed_token_cache:
                del feed_token_cache[cache_key_feed]
            
            # Clear symbol cache on logout/session expiry
            try:
                from database.master_contract_cache_hook import clear_cache_on_logout
                clear_cache_on_logout()
            except Exception as cache_error:
                logger.error(f"Error clearing symbol cache: {cache_error}")
            
            # Revoke the auth token in database
            inserted_id = upsert_auth(username, "", "", revoke=True)
            if inserted_id is not None:
                logger.info(f"Auto-expiry: Revoked auth tokens for user: {username}")
            else:
                logger.error(f"Auto-expiry: Failed to revoke auth tokens for user: {username}")
        except Exception as e:
            logger.error(f"Error revoking tokens during auto-expiry for user {username}: {e}")

def check_session_validity(f):
    """Decorator to check session validity before executing route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # CRITICAL: Force Flask to load session from cookie before checking
        # Sometimes Flask doesn't load the session until it's accessed
        try:
            # Access session to force load
            _ = dict(session)
            # Mark as modified to ensure it's saved if changed
            session.modified = True
        except Exception as e:
            logger.error(f"Error accessing session in check_session_validity: {e}")
        
        # Debug: Log session state
        logger.debug(f"check_session_validity: Route={request.endpoint}, Session keys: {list(session.keys())}, logged_in: {session.get('logged_in')}, login_time: {session.get('login_time')}")
        
        if not is_session_valid():
            # Log why session is invalid
            logger.warning(f"Session invalid for route {request.endpoint}. Session data: {dict(session)}")
            # Revoke tokens before clearing session
            revoke_user_tokens()
            session.clear()
            logger.info("Invalid session detected - redirecting to login")
            return redirect(url_for('auth.login'))
        logger.debug(f"Session validated successfully for route {request.endpoint}")
        return f(*args, **kwargs)
    return decorated_function

def invalidate_session_if_invalid(f):
    """Decorator to invalidate session if invalid without redirecting"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_session_valid():
            logger.info("Invalid session detected - clearing session")
            # Revoke tokens before clearing session
            revoke_user_tokens()
            session.clear()
        return f(*args, **kwargs)
    return decorated_function
