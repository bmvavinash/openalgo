# database/settings_db.py

from sqlalchemy import create_engine, Column, Integer, String, Boolean, MetaData, Text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
import os
from utils.logging import get_logger
from cryptography.fernet import Fernet
import base64

logger = get_logger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')

# Conditionally create engine based on DB type
if DATABASE_URL and 'sqlite' in DATABASE_URL:
    # SQLite: Use NullPool to prevent connection pool exhaustion
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args={'check_same_thread': False}
    )
else:
    # For other databases like PostgreSQL, use connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=50,
        max_overflow=100,
        pool_timeout=10
    )

db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

class Settings(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    analyze_mode = Column(Boolean, default=False)  # Default to Live Mode

    # Data Mode Configuration
    data_mode = Column(String(20), default='live')  # 'live' or 'historical'
    historical_duration = Column(String(50), nullable=True)  # 'current_day', 'previous_day', 'current_week', 'previous_week', 'current_month', '6_months', '1_year'
    historical_data_source = Column(String(20), default='yfinance')  # 'yfinance' or 'database'

    # SMTP Configuration
    smtp_server = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_username = Column(String(255), nullable=True)
    smtp_password_encrypted = Column(Text, nullable=True)  # Encrypted SMTP password
    smtp_use_tls = Column(Boolean, default=True)
    smtp_from_email = Column(String(255), nullable=True)
    smtp_helo_hostname = Column(String(255), nullable=True)  # HELO/EHLO hostname

    # Security Settings
    security_404_threshold = Column(Integer, default=20)  # 404 errors per day before ban
    security_404_ban_duration = Column(Integer, default=24)  # Ban duration in hours
    security_api_threshold = Column(Integer, default=10)  # Invalid API attempts before ban
    security_api_ban_duration = Column(Integer, default=48)  # Ban duration in hours
    security_repeat_offender_limit = Column(Integer, default=3)  # Bans before permanent ban

def init_db():
    """Initialize the settings database"""
    from database.db_init_helper import init_db_with_logging
    init_db_with_logging(Base, engine, "Settings DB", logger)

    # Create default settings only if no settings exist (with race condition protection)
    try:
        if not Settings.query.first():
            logger.info("Settings DB: Creating default configuration (Live Mode)")
            default_settings = Settings(analyze_mode=False)
            db_session.add(default_settings)
            db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.debug(f"Settings DB: Default config may already exist (race condition): {e}")

def get_analyze_mode():
    """Get current analyze mode setting"""
    settings = Settings.query.first()
    if not settings:
        settings = Settings(analyze_mode=False)  # Default to Live Mode
        db_session.add(settings)
        db_session.commit()
    return settings.analyze_mode

def set_analyze_mode(mode: bool):
    """Set analyze mode setting"""
    settings = Settings.query.first()
    if not settings:
        settings = Settings(analyze_mode=mode)
        db_session.add(settings)
    else:
        settings.analyze_mode = mode
    db_session.commit()

def _get_encryption_key():
    """Get or create encryption key for SMTP password"""
    # Use API_KEY_PEPPER as the base for encryption key
    pepper = os.getenv('API_KEY_PEPPER', 'default-pepper-key')
    # Create a stable key from the pepper
    key = base64.urlsafe_b64encode(pepper.ljust(32)[:32].encode())
    return key

def _encrypt_password(password: str) -> str:
    """Encrypt SMTP password"""
    if not password:
        return None
    key = _get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(password.encode())
    return encrypted.decode()

def _decrypt_password(encrypted_password: str) -> str:
    """Decrypt SMTP password"""
    if not encrypted_password:
        return None
    key = _get_encryption_key()
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_password.encode())
    return decrypted.decode()

def get_smtp_settings():
    """Get SMTP configuration"""
    settings = Settings.query.first()
    if not settings:
        return None
    
    return {
        'smtp_server': settings.smtp_server,
        'smtp_port': settings.smtp_port,
        'smtp_username': settings.smtp_username,
        'smtp_password': _decrypt_password(settings.smtp_password_encrypted) if settings.smtp_password_encrypted else None,
        'smtp_use_tls': settings.smtp_use_tls,
        'smtp_from_email': settings.smtp_from_email,
        'smtp_helo_hostname': settings.smtp_helo_hostname
    }

def set_smtp_settings(smtp_server=None, smtp_port=None, smtp_username=None, 
                     smtp_password=None, smtp_use_tls=True, smtp_from_email=None, smtp_helo_hostname=None):
    """Set SMTP configuration"""
    settings = Settings.query.first()
    if not settings:
        settings = Settings(analyze_mode=False)
        db_session.add(settings)
    
    if smtp_server is not None:
        settings.smtp_server = smtp_server
    if smtp_port is not None:
        settings.smtp_port = smtp_port
    if smtp_username is not None:
        settings.smtp_username = smtp_username
    if smtp_password is not None:
        settings.smtp_password_encrypted = _encrypt_password(smtp_password)
    if smtp_use_tls is not None:
        settings.smtp_use_tls = smtp_use_tls
    if smtp_from_email is not None:
        settings.smtp_from_email = smtp_from_email
    if smtp_helo_hostname is not None:
        settings.smtp_helo_hostname = smtp_helo_hostname
    
    db_session.commit()
    logger.info("SMTP settings updated successfully")

def get_security_settings():
    """Get security configuration"""
    settings = Settings.query.first()
    if not settings:
        # Create with defaults
        settings = Settings(
            analyze_mode=False,
            security_404_threshold=20,
            security_404_ban_duration=24,
            security_api_threshold=10,
            security_api_ban_duration=48,
            security_repeat_offender_limit=3
        )
        db_session.add(settings)
        db_session.commit()

    return {
        '404_threshold': settings.security_404_threshold or 20,
        '404_ban_duration': settings.security_404_ban_duration or 24,
        'api_threshold': settings.security_api_threshold or 10,
        'api_ban_duration': settings.security_api_ban_duration or 48,
        'repeat_offender_limit': settings.security_repeat_offender_limit or 3
    }

def set_security_settings(threshold_404=None, ban_duration_404=None,
                         threshold_api=None, ban_duration_api=None,
                         repeat_offender_limit=None):
    """Set security configuration"""
    settings = Settings.query.first()
    if not settings:
        settings = Settings(analyze_mode=False)
        db_session.add(settings)

    if threshold_404 is not None:
        settings.security_404_threshold = threshold_404
    if ban_duration_404 is not None:
        settings.security_404_ban_duration = ban_duration_404
    if threshold_api is not None:
        settings.security_api_threshold = threshold_api
    if ban_duration_api is not None:
        settings.security_api_ban_duration = ban_duration_api
    if repeat_offender_limit is not None:
        settings.security_repeat_offender_limit = repeat_offender_limit

    db_session.commit()
    logger.info("Security settings updated successfully")

# User-specific settings (stored as JSON in a simple key-value format)
# For now, we'll use a simple approach - can be enhanced later with a proper UserSettings table

_user_settings_cache = {}  # In-memory cache: {user_id: {key: value}}

def get_user_setting(user_id: str, key: str, default=None):
    """
    Get user-specific setting
    
    Args:
        user_id: User ID
        key: Setting key
        default: Default value if not found
    
    Returns:
        Setting value or default
    """
    try:
        # Check cache first
        if user_id in _user_settings_cache and key in _user_settings_cache[user_id]:
            return _user_settings_cache[user_id][key]
        
        # For now, return default (can be enhanced with database table later)
        return default
    except Exception as e:
        logger.warning(f"Error getting user setting {key} for user {user_id}: {e}")
        return default

def get_data_mode_settings():
    """Get data mode configuration"""
    settings = Settings.query.first()
    if not settings:
        settings = Settings(analyze_mode=False, data_mode='live', historical_data_source='yfinance')
        db_session.add(settings)
        db_session.commit()
    
    return {
        'data_mode': settings.data_mode or 'live',
        'historical_duration': settings.historical_duration or 'current_day',
        'historical_data_source': settings.historical_data_source or 'yfinance'
    }

def set_data_mode_settings(data_mode=None, historical_duration=None, historical_data_source=None):
    """Set data mode configuration"""
    settings = Settings.query.first()
    if not settings:
        settings = Settings(analyze_mode=False)
        db_session.add(settings)
    
    if data_mode is not None:
        settings.data_mode = data_mode
    if historical_duration is not None:
        settings.historical_duration = historical_duration
    if historical_data_source is not None:
        settings.historical_data_source = historical_data_source
    
    db_session.commit()
    logger.info(f"Data mode settings updated: mode={data_mode}, duration={historical_duration}, source={historical_data_source}")

def set_user_setting(user_id: str, key: str, value):
    """
    Set user-specific setting
    
    Args:
        user_id: User ID
        key: Setting key
        value: Setting value (will be JSON serialized if not string)
    """
    try:
        import json
        
        # Initialize cache for user if needed
        if user_id not in _user_settings_cache:
            _user_settings_cache[user_id] = {}
        
        # Store in cache
        _user_settings_cache[user_id][key] = value
        
        # TODO: Can be enhanced to store in database table for persistence
        # For now, cache is sufficient as it's per-session
        
        logger.debug(f"User setting {key} set for user {user_id}")
    except Exception as e:
        logger.warning(f"Error setting user setting {key} for user {user_id}: {e}")