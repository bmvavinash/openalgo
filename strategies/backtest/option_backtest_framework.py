#!/usr/bin/env python
"""
Comprehensive Option Strategy Backtesting Framework
Tests option strategies on historical data with configurable parameters
Supports multiple timeframes, periods, and comprehensive analytics
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
import traceback

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import mibian
    MIBIAN_AVAILABLE = True
except ImportError:
    MIBIAN_AVAILABLE = False
    print("Warning: mibian not available. Install with: pip install mibian")

from utils.logging import get_logger
from services.history_service import get_history
from services.option_symbol_service import get_option_symbol
from services.quotes_service import get_quotes

logger = get_logger(__name__)

# ==================== CONFIGURATION ====================

@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    # Data parameters
    underlying: str = "NIFTY"
    exchange: str = "NSE_INDEX"
    strike_int: int = 50  # 50 for NIFTY, 100 for BANKNIFTY
    lot_size: int = 25  # Lot size for the underlying
    
    # Timeframe options to test
    timeframes: List[str] = None  # ["1m", "5m", "15m", "1h", "1d"]
    
    # Period options
    periods: Dict[str, int] = None  # {"yesterday": 1, "1week": 5, "1month": 20, "3months": 60}
    
    # Entry/Exit parameters
    profit_target_pct: float = 50.0  # % of max profit to exit
    stop_loss_pct: float = 200.0  # % of premium paid/received to stop loss
    time_based_exit_days: int = 1  # Close X days before expiry
    max_holding_days: int = 30  # Maximum holding period
    
    # Volatility parameters
    default_volatility: float = 15.0  # Default IV % if not available
    interest_rate: float = 6.5  # Risk-free rate %
    
    # Trading parameters
    quantity: int = 75  # Number of lots
    product: str = "MIS"  # MIS or NRML
    slippage_pct: float = 0.1  # Slippage percentage
    
    # Analytics parameters
    calculate_sharpe: bool = True
    calculate_sortino: bool = True
    calculate_max_drawdown: bool = True
    
    # Mode
    use_analyze_mode: bool = True  # Paper trading mode
    
    def __post_init__(self):
        if self.timeframes is None:
            self.timeframes = ["1m", "5m", "15m", "1h", "1d"]
        if self.periods is None:
            self.periods = {
                "yesterday": 1,
                "1week": 5,
                "1month": 20,
                "3months": 60
            }

# ==================== OPTION PRICING ====================

class OptionPricer:
    """Calculate option prices using Black-Scholes model"""
    
    def __init__(self, interest_rate: float = 6.5, default_vol: float = 15.0):
        self.interest_rate = interest_rate
        self.default_vol = default_vol
        if not MIBIAN_AVAILABLE:
            logger.warning("mibian not available. Option pricing will be limited.")
    
    def calculate_option_price(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,  # in days
        volatility: float,
        option_type: str  # "CE" or "PE"
    ) -> float:
        """Calculate option price using Black-Scholes"""
        if not MIBIAN_AVAILABLE:
            # Simple approximation if mibian not available
            return self._simple_option_price(spot, strike, time_to_expiry, volatility, option_type)
        
        try:
            # Convert time to years
            time_years = time_to_expiry / 365.0
            
            # Create BS model
            bs = mibian.BS(
                [spot, strike, self.interest_rate, time_years],
                volatility=volatility
            )
            
            if option_type.upper() == "CE":
                return bs.callPrice
            else:
                return bs.putPrice
        except Exception as e:
            logger.error(f"Error calculating option price: {e}")
            return self._simple_option_price(spot, strike, time_to_expiry, volatility, option_type)
    
    def _simple_option_price(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        option_type: str
    ) -> float:
        """Simple option price approximation"""
        time_years = time_to_expiry / 365.0
        intrinsic = max(0, spot - strike) if option_type.upper() == "CE" else max(0, strike - spot)
        time_value = spot * volatility / 100 * np.sqrt(time_years) * 0.4  # Rough approximation
        return intrinsic + time_value
    
    def calculate_implied_volatility(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        option_price: float,
        option_type: str
    ) -> float:
        """Calculate implied volatility from option price"""
        if not MIBIAN_AVAILABLE:
            return self.default_vol
        
        try:
            time_years = time_to_expiry / 365.0
            if option_type.upper() == "CE":
                bs = mibian.BS(
                    [spot, strike, self.interest_rate, time_years],
                    callPrice=option_price
                )
            else:
                bs = mibian.BS(
                    [spot, strike, self.interest_rate, time_years],
                    putPrice=option_price
                )
            return bs.impliedVolatility
        except:
            return self.default_vol

# ==================== BACKTEST ENGINE ====================

class OptionBacktestEngine:
    """Main backtesting engine for option strategies"""
    
    def __init__(self, config: BacktestConfig, api_key: Optional[str] = None):
        self.config = config
        self.api_key = api_key
        self.pricer = OptionPricer(config.interest_rate, config.default_volatility)
        self.results = []
    
    def get_historical_data(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Fetch historical data"""
        try:
            success, response, status = get_history(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                api_key=self.api_key
            )
            
            if not success:
                logger.error(f"Failed to fetch historical data: {response.get('message')}")
                return None
            
            data = response.get('data', [])
            if not data:
                return None
            
            df = pd.DataFrame(data)
            
            # Ensure timestamp column exists
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp').reset_index(drop=True)
            elif 'date' in df.columns:
                df['timestamp'] = pd.to_datetime(df['date'])
                df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Ensure OHLC columns exist
            required_cols = ['open', 'high', 'low', 'close']
            for col in required_cols:
                if col not in df.columns and col.capitalize() in df.columns:
                    df[col] = df[col.capitalize()]
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            traceback.print_exc()
            return None
    
    def get_expiry_date(self, base_date: datetime) -> datetime:
        """Get nearest weekly expiry (Thursday)"""
        # NSE F&O expires on Thursday
        days_until_thursday = (3 - base_date.weekday()) % 7
        if days_until_thursday == 0 and base_date.hour >= 15:  # After market close
            days_until_thursday = 7
        expiry = base_date + timedelta(days=days_until_thursday)
        expiry = expiry.replace(hour=15, minute=30, second=0, microsecond=0)
        return expiry
    
    def calculate_atm_strike(self, spot: float) -> float:
        """Calculate ATM strike based on strike interval"""
        return round(spot / self.config.strike_int) * self.config.strike_int
    
    def get_strike_from_offset(
        self,
        spot: float,
        offset: str,
        option_type: str
    ) -> float:
        """Get strike price from offset (ATM, ITM1-50, OTM1-50)"""
        atm = self.calculate_atm_strike(spot)
        
        if offset.upper() == "ATM":
            return atm
        
        # Parse ITM/OTM offset
        if offset.upper().startswith("ITM"):
            level = int(offset[3:]) if len(offset) > 3 else 1
            if option_type.upper() == "CE":
                return atm - (level * self.config.strike_int)
            else:  # PE
                return atm + (level * self.config.strike_int)
        elif offset.upper().startswith("OTM"):
            level = int(offset[3:]) if len(offset) > 3 else 1
            if option_type.upper() == "CE":
                return atm + (level * self.config.strike_int)
            else:  # PE
                return atm - (level * self.config.strike_int)
        
        return atm
    
    def simulate_option_price(
        self,
        spot: float,
        strike: float,
        expiry_date: datetime,
        current_date: datetime,
        option_type: str,
        volatility: Optional[float] = None
    ) -> float:
        """Simulate option price at a given point in time"""
        time_to_expiry = (expiry_date - current_date).total_seconds() / 86400.0  # days
        
        if time_to_expiry <= 0:
            # Option expired, return intrinsic value
            if option_type.upper() == "CE":
                return max(0, spot - strike)
            else:
                return max(0, strike - spot)
        
        if volatility is None:
            volatility = self.config.default_volatility
        
        return self.pricer.calculate_option_price(
            spot, strike, time_to_expiry, volatility, option_type
        )
    
    def apply_slippage(self, price: float, action: str) -> float:
        """Apply slippage to order price"""
        slippage = self.config.slippage_pct / 100.0
        if action.upper() == "BUY":
            return price * (1 + slippage)
        else:  # SELL
            return price * (1 - slippage)

# ==================== ANALYTICS ====================

@dataclass
class Trade:
    """Represents a single trade"""
    entry_time: datetime
    exit_time: Optional[datetime]
    strategy: str
    underlying: str
    symbol: str
    option_type: str
    strike: float
    action: str  # BUY or SELL
    quantity: int
    entry_price: float
    exit_price: Optional[float]
    pnl: float
    exit_reason: str  # PROFIT_TARGET, STOP_LOSS, TIME_BASED, EXPIRY, etc.
    holding_days: float

@dataclass
class BacktestResults:
    """Results from a backtest run"""
    strategy_name: str
    timeframe: str
    period: str
    start_date: str
    end_date: str
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # PnL statistics
    total_pnl: float
    total_premium_paid: float
    total_premium_received: float
    net_pnl: float
    average_pnl_per_trade: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    
    # Risk metrics
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    
    # Time metrics
    average_holding_days: float
    total_trading_days: int
    
    # Exit reason breakdown
    exit_reasons: Dict[str, int]
    
    # Trades list
    trades: List[Dict]

class AnalyticsCalculator:
    """Calculate comprehensive analytics from trades"""
    
    @staticmethod
    def calculate_results(trades: List[Trade], strategy_name: str, timeframe: str, 
                         period: str, start_date: str, end_date: str) -> BacktestResults:
        """Calculate comprehensive analytics from trades"""
        
        if not trades:
            return BacktestResults(
                strategy_name=strategy_name,
                timeframe=timeframe,
                period=period,
                start_date=start_date,
                end_date=end_date,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_premium_paid=0.0,
                total_premium_received=0.0,
                net_pnl=0.0,
                average_pnl_per_trade=0.0,
                average_win=0.0,
                average_loss=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                max_drawdown=0.0,
                max_drawdown_pct=0.0,
                sharpe_ratio=None,
                sortino_ratio=None,
                average_holding_days=0.0,
                total_trading_days=0,
                exit_reasons={},
                trades=[]
            )
        
        # Basic statistics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        # PnL statistics
        pnls = [t.pnl for t in trades]
        total_pnl = sum(pnls)
        average_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0.0
        
        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [t.pnl for t in trades if t.pnl < 0]
        average_win = sum(wins) / len(wins) if wins else 0.0
        average_loss = sum(losses) / len(losses) if losses else 0.0
        largest_win = max(wins) if wins else 0.0
        largest_loss = min(losses) if losses else 0.0
        
        # Premium calculations
        total_premium_paid = sum([t.entry_price * t.quantity for t in trades if t.action == "BUY"])
        total_premium_received = sum([t.entry_price * t.quantity for t in trades if t.action == "SELL"])
        net_pnl = total_pnl
        
        # Drawdown calculation
        cumulative_pnl = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = cumulative_pnl - running_max
        max_drawdown = abs(min(drawdown)) if len(drawdown) > 0 else 0.0
        max_drawdown_pct = (max_drawdown / abs(total_premium_paid)) * 100 if total_premium_paid > 0 else 0.0
        
        # Sharpe and Sortino ratios
        sharpe_ratio = None
        sortino_ratio = None
        if len(pnls) > 1:
            returns = np.array(pnls)
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return > 0:
                sharpe_ratio = (mean_return / std_return) * np.sqrt(252)  # Annualized
            
            # Sortino (only downside deviation)
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0:
                downside_std = np.std(downside_returns)
                if downside_std > 0:
                    sortino_ratio = (mean_return / downside_std) * np.sqrt(252)
        
        # Time metrics
        holding_days = [t.holding_days for t in trades if t.exit_time]
        average_holding_days = sum(holding_days) / len(holding_days) if holding_days else 0.0
        
        if trades:
            first_trade = min(trades, key=lambda x: x.entry_time)
            last_trade = max([t for t in trades if t.exit_time], key=lambda x: x.exit_time) if any(t.exit_time for t in trades) else None
            if last_trade:
                total_trading_days = (last_trade.exit_time - first_trade.entry_time).days + 1
            else:
                total_trading_days = 0
        else:
            total_trading_days = 0
        
        # Exit reasons
        exit_reasons = {}
        for trade in trades:
            reason = trade.exit_reason
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        # Convert trades to dict for JSON serialization
        trades_dict = [asdict(t) for t in trades]
        for td in trades_dict:
            td['entry_time'] = td['entry_time'].isoformat() if td['entry_time'] else None
            td['exit_time'] = td['exit_time'].isoformat() if td['exit_time'] else None
        
        return BacktestResults(
            strategy_name=strategy_name,
            timeframe=timeframe,
            period=period,
            start_date=start_date,
            end_date=end_date,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_premium_paid=total_premium_paid,
            total_premium_received=total_premium_received,
            net_pnl=net_pnl,
            average_pnl_per_trade=average_pnl_per_trade,
            average_win=average_win,
            average_loss=average_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            average_holding_days=average_holding_days,
            total_trading_days=total_trading_days,
            exit_reasons=exit_reasons,
            trades=trades_dict
        )
