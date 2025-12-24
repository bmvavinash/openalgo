"""
Strategy Performance Management Blueprint
API endpoints for managing strategy performance categories and restrictions
"""
from flask import Blueprint, render_template, request, jsonify, session
from utils.session import check_session_validity
from strategy_performance_config import StrategyPerformanceConfig
from strategy_execution_filter import StrategyExecutionFilter
from utils.logging import get_logger
try:
    from database.settings_db import set_user_setting, get_user_setting
except ImportError:
    # Fallback if functions don't exist yet
    def get_user_setting(user_id, key, default=None):
        return default
    def set_user_setting(user_id, key, value):
        pass
import json

logger = get_logger(__name__)

strategy_performance_bp = Blueprint('strategy_performance_bp', __name__, url_prefix='/strategy-performance')

@strategy_performance_bp.route('/categories', methods=['GET'])
@check_session_validity
def get_categories():
    """Get all strategies categorized by performance"""
    try:
        config = StrategyPerformanceConfig()
        categories = config.get_all_categories()
        
        # Get detailed info for each strategy
        detailed_categories = {}
        for category_name, strategies in categories.items():
            detailed_categories[category_name] = []
            for strategy_name in strategies:
                info = config.get_strategy_info(strategy_name)
                detailed_categories[category_name].append({
                    'name': strategy_name,
                    'avg_pnl': info.get('avg_pnl', 0),
                    'allowed_actions': config.get_allowed_actions(strategy_name),
                    'restriction_type': info.get('restriction_type', 'none'),
                    'last_updated': info.get('last_updated')
                })
        
        return jsonify({
            'success': True,
            'categories': detailed_categories,
            'thresholds': config.get_performance_thresholds()
        })
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@strategy_performance_bp.route('/strategy/<strategy_name>', methods=['GET'])
@check_session_validity
def get_strategy_info(strategy_name):
    """Get detailed information about a strategy"""
    try:
        filter_obj = StrategyExecutionFilter()
        info = filter_obj.get_strategy_execution_info(strategy_name)
        
        return jsonify({
            'success': True,
            'strategy': strategy_name,
            'info': info
        })
    except Exception as e:
        logger.error(f"Error getting strategy info: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@strategy_performance_bp.route('/restriction', methods=['POST'])
@check_session_validity
def set_restriction():
    """Set buy/sell restriction for a strategy"""
    try:
        data = request.get_json()
        strategy_name = data.get('strategy_name')
        allowed_actions = data.get('allowed_actions', [])
        
        if not strategy_name:
            return jsonify({'success': False, 'message': 'strategy_name is required'}), 400
        
        if not allowed_actions or not isinstance(allowed_actions, list):
            return jsonify({'success': False, 'message': 'allowed_actions must be a list'}), 400
        
        # Validate actions
        valid_actions = ['BUY', 'SELL']
        if not all(action.upper() in valid_actions for action in allowed_actions):
            return jsonify({'success': False, 'message': 'Invalid actions. Must be BUY and/or SELL'}), 400
        
        config = StrategyPerformanceConfig()
        config.set_buy_sell_restriction(strategy_name, [a.upper() for a in allowed_actions])
        
        return jsonify({
            'success': True,
            'message': f'Restriction set for {strategy_name}',
            'allowed_actions': config.get_allowed_actions(strategy_name)
        })
    except Exception as e:
        logger.error(f"Error setting restriction: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@strategy_performance_bp.route('/thresholds', methods=['GET', 'POST'])
@check_session_validity
def manage_thresholds():
    """Get or update performance thresholds"""
    try:
        config = StrategyPerformanceConfig()
        
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'thresholds': config.get_performance_thresholds()
            })
        else:
            # POST - Update thresholds
            data = request.get_json()
            top = data.get('top_performance')
            average = data.get('average_performance')
            low = data.get('low_performance')
            
            config.set_performance_thresholds(top=top, average=average, low=low)
            
            return jsonify({
                'success': True,
                'message': 'Thresholds updated',
                'thresholds': config.get_performance_thresholds()
            })
    except Exception as e:
        logger.error(f"Error managing thresholds: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@strategy_performance_bp.route('/user-preferences', methods=['GET', 'POST'])
@check_session_validity
def user_preferences():
    """Get or set user's category preferences for strategy execution"""
    try:
        user_id = session.get('user')
        if not user_id:
            return jsonify({'success': False, 'message': 'Session expired'}), 401
        
        if request.method == 'GET':
            # Get user preferences
            preferences = get_user_setting(user_id, 'strategy_allowed_categories')
            if preferences:
                preferences = json.loads(preferences) if isinstance(preferences, str) else preferences
            else:
                preferences = None  # None means all categories allowed
            
            return jsonify({
                'success': True,
                'allowed_categories': preferences
            })
        else:
            # POST - Set user preferences
            data = request.get_json()
            allowed_categories = data.get('allowed_categories')
            
            # Validate categories
            valid_categories = ['top_performance', 'average_performance', 'low_performance']
            if allowed_categories is not None:
                if not isinstance(allowed_categories, list):
                    return jsonify({'success': False, 'message': 'allowed_categories must be a list'}), 400
                if not all(cat in valid_categories for cat in allowed_categories):
                    return jsonify({'success': False, 'message': f'Invalid categories. Must be from: {valid_categories}'}), 400
            
            # Save preferences
            if allowed_categories:
                set_user_setting(user_id, 'strategy_allowed_categories', json.dumps(allowed_categories))
            else:
                # Remove setting to allow all
                set_user_setting(user_id, 'strategy_allowed_categories', None)
            
            return jsonify({
                'success': True,
                'message': 'Preferences updated',
                'allowed_categories': allowed_categories
            })
    except Exception as e:
        logger.error(f"Error managing user preferences: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@strategy_performance_bp.route('/filter', methods=['POST'])
@check_session_validity
def filter_strategies():
    """Filter strategies based on categories and actions"""
    try:
        data = request.get_json()
        categories = data.get('categories')  # Optional list
        actions = data.get('actions')  # Optional list
        
        filter_obj = StrategyExecutionFilter()
        strategies = filter_obj.get_strategies_to_start(categories=categories, actions=actions)
        
        # Get detailed info
        detailed_strategies = []
        for strategy_name in strategies:
            info = filter_obj.get_strategy_execution_info(strategy_name)
            detailed_strategies.append({
                'name': strategy_name,
                **info
            })
        
        return jsonify({
            'success': True,
            'strategies': detailed_strategies,
            'count': len(strategies)
        })
    except Exception as e:
        logger.error(f"Error filtering strategies: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@strategy_performance_bp.route('/run-analysis', methods=['POST'])
@check_session_validity
def run_analysis():
    """Trigger daily analysis manually"""
    try:
        import threading
        from daily_strategy_analyzer import analyze_today_performance
        
        # Run in background thread
        def run_analysis_thread():
            try:
                analyze_today_performance()
            except Exception as e:
                logger.error(f"Error in analysis thread: {e}")
        
        thread = threading.Thread(target=run_analysis_thread, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Analysis started in background. Check logs for progress.'
        })
    except Exception as e:
        logger.error(f"Error starting analysis: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@strategy_performance_bp.route('/')
@check_session_validity
def index():
    """Strategy Performance Management Dashboard"""
    try:
        config = StrategyPerformanceConfig()
        categories = config.get_all_categories()
        thresholds = config.get_performance_thresholds()
        
        # Get user preferences
        user_id = session.get('user')
        user_preferences = None
        if user_id:
            prefs = get_user_setting(user_id, 'strategy_allowed_categories')
            if prefs:
                user_preferences = json.loads(prefs) if isinstance(prefs, str) else prefs
        
        return render_template('strategy_performance/index.html', 
                             categories=categories,
                             thresholds=thresholds,
                             user_preferences=user_preferences)
    except Exception as e:
        logger.error(f"Error rendering performance dashboard: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

