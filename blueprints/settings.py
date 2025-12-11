# blueprints/settings.py

from flask import Blueprint, jsonify, request
from database.settings_db import get_analyze_mode, set_analyze_mode, get_use_historical_data, set_use_historical_data
from utils.session import check_session_validity
from utils.logging import get_logger
from sandbox.execution_thread import start_execution_engine, stop_execution_engine

logger = get_logger(__name__)

settings_bp = Blueprint('settings_bp', __name__, url_prefix='/settings')

@settings_bp.route('/analyze-mode')
@check_session_validity
def get_mode():
    """Get current analyze mode setting"""
    try:
        return jsonify({'analyze_mode': get_analyze_mode()})
    except Exception as e:
        logger.error(f"Error getting analyze mode: {str(e)}")
        return jsonify({'error': 'Failed to get analyze mode'}), 500

@settings_bp.route('/analyze-mode/<int:mode>', methods=['POST'])
@check_session_validity
def set_mode(mode):
    """Set analyze mode setting and manage execution engine thread"""
    try:
        set_analyze_mode(bool(mode))
        mode_name = 'Analyze' if mode else 'Live'

        # Start or stop execution engine based on mode
        if mode:
            # Starting Analyze mode - start execution engine
            success, message = start_execution_engine()
            if success:
                logger.info("Execution engine started for Analyze mode")
            else:
                logger.warning(f"Failed to start execution engine: {message}")
        else:
            # Switching to Live mode - stop execution engine
            success, message = stop_execution_engine()
            if success:
                logger.info("Execution engine stopped for Live mode")
            else:
                logger.warning(f"Failed to stop execution engine: {message}")

        return jsonify({
            'success': True,
            'analyze_mode': bool(mode),
            'message': f'Switched to {mode_name} Mode'
        })
    except Exception as e:
        logger.error(f"Error setting analyze mode: {str(e)}")
        return jsonify({'error': 'Failed to set analyze mode'}), 500

@settings_bp.route('/data-mode')
@check_session_validity
def get_data_mode():
    """Get current data mode setting (live vs historical)"""
    try:
        return jsonify({'use_historical_data': get_use_historical_data()})
    except Exception as e:
        logger.error(f"Error getting data mode: {str(e)}")
        return jsonify({'error': 'Failed to get data mode'}), 500

@settings_bp.route('/data-mode/<int:mode>', methods=['POST'])
@check_session_validity
def set_data_mode(mode):
    """Set data mode setting (0 = live data, 1 = historical data)"""
    try:
        use_historical = bool(mode)
        set_use_historical_data(use_historical)
        mode_name = 'Historical' if use_historical else 'Live'
        
        logger.info(f"Data mode switched to: {mode_name}")

        return jsonify({
            'success': True,
            'use_historical_data': use_historical,
            'message': f'Switched to {mode_name} Data Mode'
        })
    except Exception as e:
        logger.error(f"Error setting data mode: {str(e)}")
        return jsonify({'error': 'Failed to set data mode'}), 500
