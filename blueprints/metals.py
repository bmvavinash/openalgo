"""
Metals Trading Blueprint

Routes and views for metals trading management including:
- Strategy management (Gold, Silver)
- Real-time positions
- Trade history
- Backtesting interface
- Notification settings
"""

from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for, abort
from database.metals_db import (
    MetalsStrategy, MetalsTrade, MetalsBacktest,
    create_metals_strategy, get_metals_strategy, get_user_metals_strategies,
    get_active_metals_strategies, update_metals_strategy, delete_metals_strategy,
    toggle_metals_strategy, create_metals_trade, get_open_metals_trades,
    get_trade_history, create_metals_backtest, update_backtest_results,
    get_strategy_backtests, close_metals_trade, update_trade_stop_loss
)
from database.auth_db import get_api_key_for_tradingview
from utils.session import check_session_validity, is_session_valid
from limiter import limiter
from utils.logging import get_logger
import json
from datetime import datetime, timedelta
import pytz
import os

logger = get_logger(__name__)

metals_bp = Blueprint('metals_bp', __name__, url_prefix='/metals')

# Rate limiting
METALS_RATE_LIMIT = os.getenv("METALS_RATE_LIMIT", "100 per minute")

# Valid metal types
VALID_METALS = ['GOLD', 'SILVER', 'PLATINUM', 'COPPER']

# MCX symbols for metals (commodity, trade till 23:30 IST)
METAL_SYMBOLS = {
    'GOLD': ['GOLDM', 'GOLD', 'GOLDPETAL'],
    'SILVER': ['SILVERM', 'SILVER', 'SILVERMIC'],
    'PLATINUM': ['PLATINUM'],
    'COPPER': ['COPPER']
}

# NSE ETF symbols (trade till 15:15 IST)
METAL_SYMBOLS_ETF = {
    'GOLD': ['GOLDBEES', 'GOLDSHARE', 'SGBS'],
    'SILVER': ['SILVERETF', 'SILVERBEES'],
    'PLATINUM': [],
    'COPPER': []
}

# Market close times (IST) by instrument type
MARKET_END_TIME_MCX = '23:30'
MARKET_END_TIME_ETF = '15:15'

# Stop loss types
STOP_LOSS_TYPES = ['FIXED', 'TRAILING', 'ATR_BASED', 'ADAPTIVE']


@metals_bp.route('/')
def index():
    """Metals trading dashboard"""
    if not is_session_valid():
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user')
    if not user_id:
        flash('Please login to continue', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        # Get user's strategies
        strategies = get_user_metals_strategies(user_id)
        
        # Get open trades
        open_trades = get_open_metals_trades()
        
        # Get recent trade history
        recent_trades = get_trade_history(user_id=user_id)[:10]
        
        # Calculate summary stats
        gold_strategies = [s for s in strategies if s.metal_type == 'GOLD']
        silver_strategies = [s for s in strategies if s.metal_type == 'SILVER']
        
        return render_template('metals/index.html',
                             strategies=strategies,
                             open_trades=open_trades,
                             recent_trades=recent_trades,
                             gold_count=len(gold_strategies),
                             silver_count=len(silver_strategies),
                             valid_metals=VALID_METALS,
                             stop_loss_types=STOP_LOSS_TYPES)
    except Exception as e:
        logger.error(f"Error loading metals dashboard: {str(e)}")
        flash('Error loading metals dashboard', 'error')
        return redirect(url_for('dashboard_bp.index'))


@metals_bp.route('/strategy/new', methods=['GET', 'POST'])
@check_session_validity
@limiter.limit(METALS_RATE_LIMIT)
def new_strategy():
    """Create new metals strategy"""
    if request.method == 'POST':
        try:
            user_id = session.get('user')
            if not user_id:
                flash('Session expired. Please login again.', 'error')
                return redirect(url_for('auth.login'))
            
            # Get form data
            name = request.form.get('name', '').strip()
            metal_type = request.form.get('metal_type', 'GOLD')
            instrument_type = request.form.get('instrument_type', 'MCX')
            exchange = 'NSE' if instrument_type == 'ETF' else request.form.get('exchange', 'MCX')
            symbol = request.form.get('symbol', '')
            product_type = request.form.get('product_type', 'MIS')
            quantity = int(request.form.get('quantity', 1))
            trading_mode = request.form.get('trading_mode', 'LONG')
            
            # Stop loss settings
            stop_loss_type = request.form.get('stop_loss_type', 'ADAPTIVE')
            stop_loss_pct = float(request.form.get('stop_loss_pct', 2.0))
            trailing_stop_pct = float(request.form.get('trailing_stop_pct', 1.0))
            atr_multiplier = float(request.form.get('atr_multiplier', 2.0))
            
            # Take profit
            take_profit_enabled = request.form.get('take_profit_enabled') == 'on'
            take_profit_pct = float(request.form.get('take_profit_pct', 3.0))
            
            # Time settings
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            
            # Sell before market close (instrument_type already set above)
            sell_before_market_close = request.form.get('sell_before_market_close') == 'on'
            square_off_minutes_before_close = int(request.form.get('square_off_minutes_before_close', 15) or 15)
            
            # Notification settings
            telegram_alerts = request.form.get('telegram_alerts') == 'on'
            whatsapp_alerts = request.form.get('whatsapp_alerts') == 'on'
            
            # Validate
            if not name:
                flash('Strategy name is required', 'error')
                return redirect(url_for('metals_bp.new_strategy'))
            
            if metal_type not in VALID_METALS:
                flash('Invalid metal type', 'error')
                return redirect(url_for('metals_bp.new_strategy'))
            
            # Create strategy
            strategy = create_metals_strategy(
                name=f"Metals_{metal_type}_{name}",
                user_id=user_id,
                metal_type=metal_type,
                exchange=exchange,
                product_type=product_type,
                quantity=quantity,
                trading_mode=trading_mode,
                stop_loss_type=stop_loss_type,
                stop_loss_pct=stop_loss_pct,
                trailing_stop_pct=trailing_stop_pct,
                atr_multiplier=atr_multiplier,
                take_profit_enabled=take_profit_enabled,
                take_profit_pct=take_profit_pct,
                start_time=start_time,
                end_time=end_time,
                instrument_type=instrument_type,
                sell_before_market_close=sell_before_market_close,
                square_off_minutes_before_close=square_off_minutes_before_close,
                telegram_alerts=telegram_alerts,
                whatsapp_alerts=whatsapp_alerts
            )
            
            if strategy:
                flash('Strategy created successfully!', 'success')
                return redirect(url_for('metals_bp.view_strategy', strategy_id=strategy.id))
            else:
                flash('Error creating strategy', 'error')
                return redirect(url_for('metals_bp.new_strategy'))
                
        except Exception as e:
            logger.error(f'Error creating metals strategy: {str(e)}')
            flash('Error creating strategy', 'error')
            return redirect(url_for('metals_bp.new_strategy'))
    
    return render_template('metals/new_strategy.html',
                         valid_metals=VALID_METALS,
                         metal_symbols=METAL_SYMBOLS,
                         metal_symbols_etf=METAL_SYMBOLS_ETF,
                         stop_loss_types=STOP_LOSS_TYPES,
                         market_end_time_etf=MARKET_END_TIME_ETF,
                         market_end_time_mcx=MARKET_END_TIME_MCX)


@metals_bp.route('/strategy/<int:strategy_id>')
def view_strategy(strategy_id):
    """View strategy details"""
    if not is_session_valid():
        return redirect(url_for('auth.login'))
    
    strategy = get_metals_strategy(strategy_id)
    if not strategy:
        flash('Strategy not found', 'error')
        return redirect(url_for('metals_bp.index'))
    
    if strategy.user_id != session.get('user'):
        flash('Unauthorized access', 'error')
        return redirect(url_for('metals_bp.index'))
    
    # Get open trades for this strategy
    open_trades = get_open_metals_trades(strategy_id=strategy_id)
    
    # Get trade history
    trades = get_trade_history(strategy_id=strategy_id)[:20]
    
    # Get backtests
    backtests = get_strategy_backtests(strategy_id)[:5]
    
    # Calculate performance metrics
    all_trades = get_trade_history(strategy_id=strategy_id)
    total_trades = len(all_trades)
    winning_trades = len([t for t in all_trades if t.pnl and t.pnl > 0])
    total_pnl = sum([t.pnl or 0 for t in all_trades])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    return render_template('metals/view_strategy.html',
                         strategy=strategy,
                         open_trades=open_trades,
                         trades=trades,
                         backtests=backtests,
                         total_trades=total_trades,
                         winning_trades=winning_trades,
                         total_pnl=total_pnl,
                         win_rate=win_rate)


@metals_bp.route('/strategy/<int:strategy_id>/toggle', methods=['POST'])
@check_session_validity
def toggle_strategy_route(strategy_id):
    """Toggle strategy active status"""
    try:
        strategy = toggle_metals_strategy(strategy_id)
        if strategy:
            status = 'activated' if strategy.is_active else 'deactivated'
            flash(f'Strategy {status} successfully', 'success')
        else:
            flash('Error toggling strategy', 'error')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('metals_bp.view_strategy', strategy_id=strategy_id))


@metals_bp.route('/strategy/<int:strategy_id>/delete', methods=['POST'])
@check_session_validity
@limiter.limit(METALS_RATE_LIMIT)
def delete_strategy_route(strategy_id):
    """Delete strategy"""
    user_id = session.get('user')
    strategy = get_metals_strategy(strategy_id)
    
    if not strategy:
        return jsonify({'status': 'error', 'error': 'Strategy not found'}), 404
    
    if strategy.user_id != user_id:
        return jsonify({'status': 'error', 'error': 'Unauthorized'}), 403
    
    try:
        if delete_metals_strategy(strategy_id):
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'error': 'Failed to delete strategy'}), 500
    except Exception as e:
        logger.error(f'Error deleting metals strategy {strategy_id}: {str(e)}')
        return jsonify({'status': 'error', 'error': str(e)}), 500


@metals_bp.route('/analysis')
@check_session_validity
def analysis():
    """Backtest analysis: summary of all strategies' latest backtests; run historical backtests from here."""
    user_id = session.get('user')
    if not user_id:
        flash('Please login to continue', 'error')
        return redirect(url_for('auth.login'))
    strategies = get_user_metals_strategies(user_id)
    # Latest backtest per strategy
    strategy_backtests = {}
    for s in strategies:
        backtests = get_strategy_backtests(s.id)
        latest = backtests[0] if backtests else None
        strategy_backtests[s.id] = {'strategy': s, 'latest_backtest': latest}
    now = datetime.now().strftime('%Y-%m-%d')
    backtest_range = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    return render_template('metals/analysis.html',
                          strategies=strategies,
                          strategy_backtests=strategy_backtests,
                          now=now,
                          backtest_range=backtest_range)


@metals_bp.route('/analysis/run', methods=['POST'])
@check_session_validity
@limiter.limit(METALS_RATE_LIMIT)
def run_historical_backtests():
    """Run historical backtests for current user's metals strategies (backend); results saved to DB and visible in UI."""
    user_id = session.get('user')
    if not user_id:
        flash('Please login to continue', 'error')
        return redirect(url_for('metals_bp.index'))
    try:
        from run_metals_historical_backtests import run_metals_historical_backtests
        start = request.form.get('start_date') or (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        end = request.form.get('end_date') or datetime.now().strftime('%Y-%m-%d')
        timeframe = request.form.get('timeframe', '5m')
        reports = run_metals_historical_backtests(user_id=user_id, start_date=start, end_date=end, timeframe=timeframe)
        completed = len([r for r in reports if r.get('status') == 'completed'])
        errors = len([r for r in reports if r.get('status') == 'error'])
        flash(f'Historical backtests finished: {completed} completed, {errors} errors. Check strategy pages and Analysis.', 'success')
    except Exception as e:
        logger.error(f'Error running historical backtests: {str(e)}')
        flash(f'Error running backtests: {str(e)}', 'error')
    return redirect(url_for('metals_bp.analysis'))


@metals_bp.route('/strategy/<int:strategy_id>/backtest', methods=['GET', 'POST'])
@check_session_validity
@limiter.limit(METALS_RATE_LIMIT)
def run_backtest(strategy_id):
    """Run backtest for strategy"""
    strategy = get_metals_strategy(strategy_id)
    if not strategy:
        flash('Strategy not found', 'error')
        return redirect(url_for('metals_bp.index'))
    
    if strategy.user_id != session.get('user'):
        flash('Unauthorized access', 'error')
        return redirect(url_for('metals_bp.index'))
    
    if request.method == 'POST':
        try:
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            timeframe = request.form.get('timeframe', '5m')
            
            # Create backtest record
            backtest = create_metals_backtest(
                strategy_id=strategy_id,
                start_date=datetime.strptime(start_date, '%Y-%m-%d'),
                end_date=datetime.strptime(end_date, '%Y-%m-%d'),
                timeframe=timeframe
            )
            
            if backtest:
                from strategies.backtest.metals_backtest_framework import BacktestConfig
                # Symbol: use strategy's instrument_type (MCX vs ETF)
                instrument_type = getattr(strategy, 'instrument_type', None) or 'MCX'
                if instrument_type == 'ETF':
                    symbol = (METAL_SYMBOLS_ETF.get(strategy.metal_type) or ['GOLDBEES'])[0]
                else:
                    symbol = (METAL_SYMBOLS.get(strategy.metal_type) or ['GOLDM'])[0]
                config = BacktestConfig(
                    metal_type=strategy.metal_type,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe=timeframe,
                    stop_loss_type=strategy.stop_loss_type,
                    stop_loss_pct=float(strategy.stop_loss_pct or 2.0),
                    take_profit_pct=float(strategy.take_profit_pct or 4.0)
                )
                
                # Run backtest
                from strategies.backtest.metals_backtest_framework import MetalsBacktestEngine
                engine = MetalsBacktestEngine(config)
                results = engine.run_backtest()
                
                # Update backtest record
                update_backtest_results(backtest.id, {
                    'total_trades': results.total_trades,
                    'winning_trades': results.winning_trades,
                    'losing_trades': results.losing_trades,
                    'win_rate': results.win_rate,
                    'total_pnl': results.total_pnl,
                    'total_pnl_pct': results.total_pnl_pct,
                    'max_drawdown': results.max_drawdown,
                    'max_drawdown_pct': results.max_drawdown_pct,
                    'sharpe_ratio': results.sharpe_ratio,
                    'sortino_ratio': results.sortino_ratio,
                    'profit_factor': results.profit_factor,
                    'trades_data': json.dumps([{
                        'entry_time': str(t.entry_time),
                        'exit_time': str(t.exit_time),
                        'action': t.action,
                        'entry_price': t.entry_price,
                        'exit_price': t.exit_price,
                        'pnl': t.pnl,
                        'exit_reason': t.exit_reason
                    } for t in results.trades]),
                    'equity_curve': json.dumps(results.equity_curve)
                })
                
                flash('Backtest completed successfully!', 'success')
            else:
                flash('Error creating backtest', 'error')
                
        except Exception as e:
            logger.error(f'Error running backtest: {str(e)}')
            flash(f'Error running backtest: {str(e)}', 'error')
        
        return redirect(url_for('metals_bp.view_strategy', strategy_id=strategy_id))
    
    # Default dates
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    return render_template('metals/backtest.html',
                         strategy=strategy,
                         start_date=start_date,
                         end_date=end_date)


@metals_bp.route('/trades')
def trade_history():
    """View all metals trade history"""
    if not is_session_valid():
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user')
    
    # Get filter parameters
    metal_type = request.args.get('metal_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    trades = get_trade_history(
        user_id=user_id,
        metal_type=metal_type,
        start_date=datetime.strptime(start_date, '%Y-%m-%d') if start_date else None,
        end_date=datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
    )
    
    # Calculate summary
    total_pnl = sum([t.pnl or 0 for t in trades])
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.pnl and t.pnl > 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    return render_template('metals/trades.html',
                         trades=trades,
                         total_pnl=total_pnl,
                         total_trades=total_trades,
                         winning_trades=winning_trades,
                         win_rate=win_rate,
                         valid_metals=VALID_METALS)


@metals_bp.route('/positions')
def open_positions():
    """View open positions"""
    if not is_session_valid():
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user')
    
    # Get user's strategies to filter positions
    strategies = get_user_metals_strategies(user_id)
    strategy_ids = [s.id for s in strategies]
    
    # Get open trades
    all_open_trades = []
    for strategy_id in strategy_ids:
        trades = get_open_metals_trades(strategy_id=strategy_id)
        all_open_trades.extend(trades)
    
    return render_template('metals/positions.html',
                         open_trades=all_open_trades,
                         valid_metals=VALID_METALS)


# API endpoints for strategy execution

@metals_bp.route('/api/quote/<metal_type>')
@check_session_validity
def get_metal_quote(metal_type):
    """Get real-time quote for metal"""
    try:
        from services.quotes_service import get_quotes
        
        symbols = METAL_SYMBOLS.get(metal_type.upper(), [])
        if not symbols:
            return jsonify({'error': 'Invalid metal type'}), 400
        
        quotes = {}
        for symbol in symbols:
            try:
                quote = get_quotes(symbol=symbol, exchange='MCX')
                if quote:
                    quotes[symbol] = quote
            except Exception as e:
                logger.warning(f"Could not get quote for {symbol}: {e}")
        
        return jsonify(quotes)
        
    except Exception as e:
        logger.error(f"Error getting metal quote: {e}")
        return jsonify({'error': str(e)}), 500


@metals_bp.route('/api/strategy/<int:strategy_id>/start', methods=['POST'])
@check_session_validity
def start_strategy(strategy_id):
    """Start a metals strategy"""
    try:
        strategy = get_metals_strategy(strategy_id)
        if not strategy:
            return jsonify({'error': 'Strategy not found'}), 404
        
        if strategy.user_id != session.get('user'):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Activate strategy
        update_metals_strategy(strategy_id, is_active=True)
        
        # Send notification
        from services.metals_alert_service import metals_alert_service
        api_key = get_api_key_for_tradingview(strategy.user_id)
        
        metals_alert_service.send_strategy_started_alert(
            metal_type=strategy.metal_type,
            strategy_name=strategy.name,
            symbol=METAL_SYMBOLS.get(strategy.metal_type, ['GOLDM'])[0],
            exchange=strategy.exchange,
            stop_loss_type=strategy.stop_loss_type,
            api_key=api_key
        )
        
        return jsonify({'status': 'success', 'message': 'Strategy started'})
        
    except Exception as e:
        logger.error(f"Error starting strategy: {e}")
        return jsonify({'error': str(e)}), 500


@metals_bp.route('/api/strategy/<int:strategy_id>/stop', methods=['POST'])
@check_session_validity
def stop_strategy(strategy_id):
    """Stop a metals strategy"""
    try:
        strategy = get_metals_strategy(strategy_id)
        if not strategy:
            return jsonify({'error': 'Strategy not found'}), 404
        
        if strategy.user_id != session.get('user'):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Deactivate strategy
        update_metals_strategy(strategy_id, is_active=False)
        
        # Send notification
        from services.metals_alert_service import metals_alert_service
        api_key = get_api_key_for_tradingview(strategy.user_id)
        
        metals_alert_service.send_strategy_stopped_alert(
            metal_type=strategy.metal_type,
            strategy_name=strategy.name,
            reason='Manual stop',
            api_key=api_key
        )
        
        return jsonify({'status': 'success', 'message': 'Strategy stopped'})
        
    except Exception as e:
        logger.error(f"Error stopping strategy: {e}")
        return jsonify({'error': str(e)}), 500
