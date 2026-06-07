# blueprints/settings.py

from flask import Blueprint, jsonify, request
from database.settings_db import (
    get_analyze_mode, set_analyze_mode,
    get_data_mode_settings, set_data_mode_settings
)
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

@settings_bp.route('/data-mode', methods=['GET'])
@check_session_validity
def get_data_mode():
    """Get current data mode settings"""
    try:
        settings = get_data_mode_settings()
        return jsonify({
            'success': True,
            'data_mode': settings.get('data_mode', 'live'),
            'historical_duration': settings.get('historical_duration', 'current_day'),
            'historical_data_source': settings.get('historical_data_source', 'yfinance')
        })
    except Exception as e:
        logger.error(f"Error getting data mode: {str(e)}")
        return jsonify({'error': 'Failed to get data mode'}), 500

@settings_bp.route('/data-mode', methods=['POST'])
@check_session_validity
def set_data_mode():
    """Set data mode configuration"""
    try:
        data = request.get_json()
        data_mode = data.get('data_mode', 'live')
        historical_duration = data.get('historical_duration', 'current_day')
        historical_data_source = data.get('historical_data_source', 'yfinance')
        
        # Validate values
        if data_mode not in ['live', 'historical']:
            return jsonify({'error': 'Invalid data_mode. Must be "live" or "historical"'}), 400
        
        valid_durations = ['current_day', 'previous_day', 'current_week', 'previous_week', 
                          'current_month', '6_months', '1_year']
        if historical_duration not in valid_durations:
            return jsonify({'error': f'Invalid historical_duration. Must be one of: {", ".join(valid_durations)}'}), 400
        
        if historical_data_source not in ['yfinance', 'database']:
            return jsonify({'error': 'Invalid historical_data_source. Must be "yfinance" or "database"'}), 400
        
        set_data_mode_settings(
            data_mode=data_mode,
            historical_duration=historical_duration,
            historical_data_source=historical_data_source
        )
        
        logger.info(f"Data mode updated: mode={data_mode}, duration={historical_duration}, source={historical_data_source}")
        
        return jsonify({
            'success': True,
            'message': 'Data mode settings updated successfully',
            'data_mode': data_mode,
            'historical_duration': historical_duration,
            'historical_data_source': historical_data_source
        })
    except Exception as e:
        logger.error(f"Error setting data mode: {str(e)}")
        return jsonify({'error': 'Failed to set data mode'}), 500
