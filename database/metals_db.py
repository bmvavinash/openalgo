"""
Database models and operations for Metals Trading
Supports Gold, Silver, and other precious metals
"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.pool import NullPool
import os
import logging
import json
from datetime import datetime
import enum

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')

# Conditionally create engine based on DB type
if DATABASE_URL and 'sqlite' in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args={'check_same_thread': False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=50,
        max_overflow=100,
        pool_timeout=10
    )

db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


class MetalType(enum.Enum):
    """Supported metal types"""
    GOLD = "GOLD"
    SILVER = "SILVER"
    PLATINUM = "PLATINUM"
    COPPER = "COPPER"
    ALUMINUM = "ALUMINUM"


class StopLossType(enum.Enum):
    """Stop loss types"""
    FIXED = "FIXED"          # Fixed percentage
    TRAILING = "TRAILING"    # Trailing stop loss
    ATR_BASED = "ATR_BASED"  # Based on Average True Range
    ADAPTIVE = "ADAPTIVE"    # Adaptive based on volatility


class MetalsStrategy(Base):
    """Model for metals trading strategies"""
    __tablename__ = 'metals_strategies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    user_id = Column(String(255), nullable=False)
    metal_type = Column(String(20), nullable=False)  # GOLD, SILVER, etc.
    
    # Trading parameters
    is_active = Column(Boolean, default=True)
    trading_mode = Column(String(10), nullable=False, default='LONG')  # LONG, SHORT, BOTH
    exchange = Column(String(10), nullable=False, default='MCX')
    product_type = Column(String(10), nullable=False, default='MIS')  # MIS/NRML
    quantity = Column(Integer, default=1)
    
    # Strategy configuration (JSON)
    strategy_config = Column(Text, default='{}')  # Stores strategy-specific params
    
    # Stop-loss configuration
    stop_loss_type = Column(String(20), default='ADAPTIVE')  # FIXED, TRAILING, ATR_BASED, ADAPTIVE
    stop_loss_pct = Column(Float, default=2.0)  # Base stop loss percentage
    trailing_stop_pct = Column(Float, default=1.0)  # For trailing stop
    atr_multiplier = Column(Float, default=2.0)  # For ATR-based stop
    
    # Take profit
    take_profit_enabled = Column(Boolean, default=True)
    take_profit_pct = Column(Float, default=3.0)
    
    # Risk management
    max_daily_loss_pct = Column(Float, default=5.0)  # Max daily loss percentage
    max_position_size = Column(Integer, default=10)  # Max lots
    
    # Time controls (IST)
    start_time = Column(String(5))  # HH:MM format
    end_time = Column(String(5))  # HH:MM format
    
    # Instrument segment: MCX (commodity, till 23:30) or ETF (NSE, till 15:15)
    instrument_type = Column(String(10), default='MCX')  # MCX, ETF
    
    # Sell before market close (recommended for ETF to avoid auto square-off)
    sell_before_market_close = Column(Boolean, default=False)
    square_off_minutes_before_close = Column(Integer, default=15)  # minutes before end_time
    
    # Notification preferences
    telegram_alerts = Column(Boolean, default=True)
    whatsapp_alerts = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    trades = relationship("MetalsTrade", back_populates="strategy", cascade="all, delete-orphan")
    backtest_results = relationship("MetalsBacktest", back_populates="strategy", cascade="all, delete-orphan")


class MetalsTrade(Base):
    """Model for metals trades"""
    __tablename__ = 'metals_trades'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('metals_strategies.id'), nullable=False)
    
    # Trade details
    metal_type = Column(String(20), nullable=False)
    symbol = Column(String(50), nullable=False)  # e.g., GOLDM, SILVERM
    action = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Integer, nullable=False)
    
    # Entry details
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime(timezone=True), server_default=func.now())
    
    # Exit details
    exit_price = Column(Float)
    exit_time = Column(DateTime(timezone=True))
    exit_reason = Column(String(50))  # STOP_LOSS, TAKE_PROFIT, SIGNAL, MANUAL, SQUAREOFF
    
    # Stop loss tracking
    initial_stop_loss = Column(Float)
    current_stop_loss = Column(Float)
    stop_loss_updates = Column(Text, default='[]')  # JSON array of SL updates
    
    # P&L
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    
    # Status
    is_open = Column(Boolean, default=True)
    
    # Order IDs
    entry_order_id = Column(String(50))
    exit_order_id = Column(String(50))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    strategy = relationship("MetalsStrategy", back_populates="trades")


class MetalsBacktest(Base):
    """Model for metals strategy backtests"""
    __tablename__ = 'metals_backtests'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('metals_strategies.id'), nullable=False)
    
    # Backtest period
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    timeframe = Column(String(10), default='5m')  # 1m, 5m, 15m, 1h, 1d
    
    # Results
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    
    # P&L metrics
    total_pnl = Column(Float, default=0.0)
    total_pnl_pct = Column(Float, default=0.0)
    avg_profit = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    
    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    
    # Detailed results (JSON)
    trades_data = Column(Text, default='[]')  # JSON array of individual trades
    equity_curve = Column(Text, default='[]')  # JSON array of equity values
    
    # Status
    status = Column(String(20), default='PENDING')  # PENDING, RUNNING, COMPLETED, FAILED
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    strategy = relationship("MetalsStrategy", back_populates="backtest_results")


class MetalsPriceHistory(Base):
    """Model for caching metals price history"""
    __tablename__ = 'metals_price_history'
    
    id = Column(Integer, primary_key=True)
    metal_type = Column(String(20), nullable=False)
    symbol = Column(String(50), nullable=False)
    
    # OHLCV data
    timestamp = Column(DateTime(timezone=True), nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, default=0)
    
    # Timeframe
    timeframe = Column(String(10), default='5m')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def _add_metals_strategy_columns_if_missing():
    """Add instrument_type, sell_before_market_close, square_off_minutes_before_close if missing."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if 'metals_strategies' not in inspector.get_table_names():
        return
    cols = {c['name'] for c in inspector.get_columns('metals_strategies')}
    with engine.connect() as conn:
        if 'instrument_type' not in cols:
            conn.execute(text("ALTER TABLE metals_strategies ADD COLUMN instrument_type VARCHAR(10) DEFAULT 'MCX'"))
            conn.commit()
        if 'sell_before_market_close' not in cols:
            conn.execute(text("ALTER TABLE metals_strategies ADD COLUMN sell_before_market_close BOOLEAN DEFAULT 0"))
            conn.commit()
        if 'square_off_minutes_before_close' not in cols:
            conn.execute(text("ALTER TABLE metals_strategies ADD COLUMN square_off_minutes_before_close INTEGER DEFAULT 15"))
            conn.commit()


def init_db():
    """Initialize the database"""
    from database.db_init_helper import init_db_with_logging
    init_db_with_logging(Base, engine, "Metals DB", logger)
    _add_metals_strategy_columns_if_missing()


# ==================== Strategy Operations ====================

def create_metals_strategy(name, user_id, metal_type, **kwargs):
    """Create a new metals trading strategy"""
    try:
        strategy = MetalsStrategy(
            name=name,
            user_id=user_id,
            metal_type=metal_type,
            **kwargs
        )
        db_session.add(strategy)
        db_session.commit()
        logger.info(f"Created metals strategy: {name} for {metal_type}")
        return strategy
    except Exception as e:
        logger.error(f"Error creating metals strategy: {str(e)}")
        db_session.rollback()
        return None


def get_metals_strategy(strategy_id):
    """Get strategy by ID"""
    try:
        return MetalsStrategy.query.get(strategy_id)
    except Exception as e:
        logger.error(f"Error getting metals strategy {strategy_id}: {str(e)}")
        return None


def get_user_metals_strategies(user_id):
    """Get all metals strategies for a user"""
    try:
        return MetalsStrategy.query.filter_by(user_id=user_id).all()
    except Exception as e:
        logger.error(f"Error getting user metals strategies: {str(e)}")
        return []


def get_active_metals_strategies(metal_type=None):
    """Get all active metals strategies, optionally filtered by metal type"""
    try:
        query = MetalsStrategy.query.filter_by(is_active=True)
        if metal_type:
            query = query.filter_by(metal_type=metal_type)
        return query.all()
    except Exception as e:
        logger.error(f"Error getting active metals strategies: {str(e)}")
        return []


def update_metals_strategy(strategy_id, **kwargs):
    """Update a metals strategy"""
    try:
        strategy = get_metals_strategy(strategy_id)
        if not strategy:
            return None
        
        for key, value in kwargs.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)
        
        db_session.commit()
        logger.info(f"Updated metals strategy: {strategy_id}")
        return strategy
    except Exception as e:
        logger.error(f"Error updating metals strategy {strategy_id}: {str(e)}")
        db_session.rollback()
        return None


def delete_metals_strategy(strategy_id):
    """Delete a metals strategy"""
    try:
        strategy = get_metals_strategy(strategy_id)
        if not strategy:
            return False
        
        db_session.delete(strategy)
        db_session.commit()
        logger.info(f"Deleted metals strategy: {strategy_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting metals strategy {strategy_id}: {str(e)}")
        db_session.rollback()
        return False


def toggle_metals_strategy(strategy_id):
    """Toggle strategy active status"""
    try:
        strategy = get_metals_strategy(strategy_id)
        if not strategy:
            return None
        
        strategy.is_active = not strategy.is_active
        db_session.commit()
        return strategy
    except Exception as e:
        logger.error(f"Error toggling metals strategy {strategy_id}: {str(e)}")
        db_session.rollback()
        return None


# ==================== Trade Operations ====================

def create_metals_trade(strategy_id, metal_type, symbol, action, quantity, entry_price, initial_stop_loss=None, entry_order_id=None):
    """Create a new metals trade"""
    try:
        trade = MetalsTrade(
            strategy_id=strategy_id,
            metal_type=metal_type,
            symbol=symbol,
            action=action,
            quantity=quantity,
            entry_price=entry_price,
            initial_stop_loss=initial_stop_loss,
            current_stop_loss=initial_stop_loss,
            entry_order_id=entry_order_id
        )
        db_session.add(trade)
        db_session.commit()
        logger.info(f"Created metals trade: {action} {quantity} {symbol} @ {entry_price}")
        return trade
    except Exception as e:
        logger.error(f"Error creating metals trade: {str(e)}")
        db_session.rollback()
        return None


def get_metals_trade(trade_id):
    """Get trade by ID"""
    try:
        return MetalsTrade.query.get(trade_id)
    except Exception as e:
        logger.error(f"Error getting metals trade {trade_id}: {str(e)}")
        return None


def get_open_metals_trades(strategy_id=None, metal_type=None):
    """Get all open metals trades"""
    try:
        query = MetalsTrade.query.filter_by(is_open=True)
        if strategy_id:
            query = query.filter_by(strategy_id=strategy_id)
        if metal_type:
            query = query.filter_by(metal_type=metal_type)
        return query.all()
    except Exception as e:
        logger.error(f"Error getting open metals trades: {str(e)}")
        return []


def update_trade_stop_loss(trade_id, new_stop_loss):
    """Update trade stop loss"""
    try:
        trade = get_metals_trade(trade_id)
        if not trade:
            return None
        
        # Track stop loss updates
        updates = json.loads(trade.stop_loss_updates or '[]')
        updates.append({
            'timestamp': datetime.now().isoformat(),
            'old_sl': trade.current_stop_loss,
            'new_sl': new_stop_loss
        })
        
        trade.current_stop_loss = new_stop_loss
        trade.stop_loss_updates = json.dumps(updates)
        db_session.commit()
        
        logger.info(f"Updated stop loss for trade {trade_id}: {new_stop_loss}")
        return trade
    except Exception as e:
        logger.error(f"Error updating trade stop loss {trade_id}: {str(e)}")
        db_session.rollback()
        return None


def close_metals_trade(trade_id, exit_price, exit_reason, exit_order_id=None):
    """Close a metals trade"""
    try:
        trade = get_metals_trade(trade_id)
        if not trade or not trade.is_open:
            return None
        
        # Calculate P&L
        if trade.action == 'BUY':
            pnl = (exit_price - trade.entry_price) * trade.quantity
            pnl_pct = ((exit_price - trade.entry_price) / trade.entry_price) * 100
        else:  # SELL
            pnl = (trade.entry_price - exit_price) * trade.quantity
            pnl_pct = ((trade.entry_price - exit_price) / trade.entry_price) * 100
        
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.exit_reason = exit_reason
        trade.pnl = pnl
        trade.pnl_pct = pnl_pct
        trade.is_open = False
        trade.exit_order_id = exit_order_id
        
        db_session.commit()
        logger.info(f"Closed metals trade {trade_id}: PnL={pnl:.2f} ({pnl_pct:.2f}%)")
        return trade
    except Exception as e:
        logger.error(f"Error closing metals trade {trade_id}: {str(e)}")
        db_session.rollback()
        return None


def get_trade_history(strategy_id=None, user_id=None, metal_type=None, start_date=None, end_date=None):
    """Get trade history with filters"""
    try:
        query = MetalsTrade.query
        
        if strategy_id:
            query = query.filter_by(strategy_id=strategy_id)
        if metal_type:
            query = query.filter_by(metal_type=metal_type)
        if start_date:
            query = query.filter(MetalsTrade.entry_time >= start_date)
        if end_date:
            query = query.filter(MetalsTrade.entry_time <= end_date)
        if user_id:
            query = query.join(MetalsStrategy).filter(MetalsStrategy.user_id == user_id)
        
        return query.order_by(MetalsTrade.entry_time.desc()).all()
    except Exception as e:
        logger.error(f"Error getting trade history: {str(e)}")
        return []


# ==================== Backtest Operations ====================

def create_metals_backtest(strategy_id, start_date, end_date, timeframe='5m'):
    """Create a new backtest record"""
    try:
        backtest = MetalsBacktest(
            strategy_id=strategy_id,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            status='PENDING'
        )
        db_session.add(backtest)
        db_session.commit()
        logger.info(f"Created backtest for strategy {strategy_id}")
        return backtest
    except Exception as e:
        logger.error(f"Error creating backtest: {str(e)}")
        db_session.rollback()
        return None


def update_backtest_results(backtest_id, results):
    """Update backtest with results"""
    try:
        backtest = MetalsBacktest.query.get(backtest_id)
        if not backtest:
            return None
        
        for key, value in results.items():
            if hasattr(backtest, key):
                setattr(backtest, key, value)
        
        backtest.status = 'COMPLETED'
        backtest.completed_at = datetime.now()
        db_session.commit()
        
        logger.info(f"Updated backtest {backtest_id} with results")
        return backtest
    except Exception as e:
        logger.error(f"Error updating backtest results {backtest_id}: {str(e)}")
        db_session.rollback()
        return None


def get_strategy_backtests(strategy_id):
    """Get all backtests for a strategy"""
    try:
        return MetalsBacktest.query.filter_by(strategy_id=strategy_id).order_by(MetalsBacktest.created_at.desc()).all()
    except Exception as e:
        logger.error(f"Error getting strategy backtests: {str(e)}")
        return []


# ==================== Price History Operations ====================

def save_price_history(metal_type, symbol, data, timeframe='5m'):
    """Save price history data"""
    try:
        for row in data:
            price = MetalsPriceHistory(
                metal_type=metal_type,
                symbol=symbol,
                timestamp=row['timestamp'],
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row.get('volume', 0),
                timeframe=timeframe
            )
            db_session.merge(price)
        
        db_session.commit()
        logger.info(f"Saved {len(data)} price records for {symbol}")
        return True
    except Exception as e:
        logger.error(f"Error saving price history: {str(e)}")
        db_session.rollback()
        return False


def get_price_history(symbol, timeframe='5m', start_date=None, end_date=None, limit=None):
    """Get price history for a symbol"""
    try:
        query = MetalsPriceHistory.query.filter_by(symbol=symbol, timeframe=timeframe)
        
        if start_date:
            query = query.filter(MetalsPriceHistory.timestamp >= start_date)
        if end_date:
            query = query.filter(MetalsPriceHistory.timestamp <= end_date)
        
        query = query.order_by(MetalsPriceHistory.timestamp.asc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    except Exception as e:
        logger.error(f"Error getting price history: {str(e)}")
        return []
