"""
Metals Backtesting Framework

This framework allows backtesting of gold and silver trading strategies
using historical data with the adaptive stop-loss mechanism.

Features:
1. Multiple strategy support (Gold, Silver, combined)
2. Configurable backtesting parameters
3. Comprehensive analytics and reporting
4. Integration with adaptive stop-loss
5. Visualization support
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path

import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.adaptive_stop_loss_service import (
    AdaptiveStopLossService, StopLossType, TradePosition, StopLossResult
)

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for backtest"""
    # Basic settings
    metal_type: str = "GOLD"  # GOLD, SILVER, or BOTH
    symbol: str = "GOLDM"
    exchange: str = "MCX"
    
    # Time period
    start_date: str = ""
    end_date: str = ""
    timeframe: str = "5m"
    
    # Strategy parameters
    fast_ema: int = 9
    slow_ema: int = 21
    rsi_period: int = 14
    rsi_overbought: float = 70
    rsi_oversold: float = 30
    
    # Risk management
    stop_loss_type: str = "ADAPTIVE"
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 4.0
    trailing_stop_pct: float = 1.5
    
    # Position sizing
    initial_capital: float = 100000
    position_size_pct: float = 10.0  # Percentage of capital per trade
    max_positions: int = 1
    
    # Slippage and costs
    slippage_pct: float = 0.05  # 0.05% slippage
    commission_per_lot: float = 20.0  # Per lot commission
    
    # Filters
    min_signal_strength: float = 50.0
    trading_start_hour: int = 9
    trading_end_hour: int = 23


@dataclass
class BacktestTrade:
    """Record of a single trade in backtest"""
    trade_id: int
    metal_type: str
    symbol: str
    action: str
    quantity: int
    
    entry_time: datetime
    entry_price: float
    entry_signal_strength: float
    
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    
    initial_stop_loss: Optional[float] = None
    final_stop_loss: Optional[float] = None
    take_profit_price: Optional[float] = None
    
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    
    max_favorable_excursion: float = 0.0  # Max profit during trade
    max_adverse_excursion: float = 0.0    # Max loss during trade
    holding_duration_minutes: int = 0


@dataclass
class BacktestResults:
    """Results from a backtest run"""
    config: BacktestConfig
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L metrics
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0
    
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Time metrics
    avg_holding_time_minutes: float = 0.0
    max_holding_time_minutes: float = 0.0
    avg_trades_per_day: float = 0.0
    
    # Exit reason breakdown
    exit_reasons: Dict[str, int] = field(default_factory=dict)
    
    # Detailed data
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    drawdown_curve: List[float] = field(default_factory=list)
    
    # Timestamps
    backtest_start: datetime = None
    backtest_end: datetime = None
    run_duration_seconds: float = 0.0


class MetalsBacktestEngine:
    """
    Backtesting engine for metals trading strategies
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.stop_loss_service = AdaptiveStopLossService()
        
        # State tracking
        self.current_position = 0
        self.entry_price = None
        self.entry_time = None
        self.current_stop_loss = None
        self.take_profit_price = None
        self.highest_price = None
        self.lowest_price = None
        self.entry_signal_strength = None
        
        # Trade tracking
        self.trades: List[BacktestTrade] = []
        self.trade_counter = 0
        
        # Capital tracking
        self.capital = config.initial_capital
        self.peak_capital = config.initial_capital
        self.equity_curve = [config.initial_capital]
        self.drawdown_curve = [0.0]
        
        # Max adverse/favorable excursion for current trade
        self.max_favorable = 0.0
        self.max_adverse = 0.0
    
    def load_historical_data(self) -> pd.DataFrame:
        """Load historical data for backtesting"""
        try:
            # Try to load from database first
            from database.metals_db import get_price_history
            
            start_date = datetime.strptime(self.config.start_date, '%Y-%m-%d') if self.config.start_date else datetime.now() - timedelta(days=30)
            end_date = datetime.strptime(self.config.end_date, '%Y-%m-%d') if self.config.end_date else datetime.now()
            
            history = get_price_history(
                symbol=self.config.symbol,
                timeframe=self.config.timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if history:
                df = pd.DataFrame([{
                    'timestamp': h.timestamp,
                    'open': h.open,
                    'high': h.high,
                    'low': h.low,
                    'close': h.close,
                    'volume': h.volume
                } for h in history])
                df.set_index('timestamp', inplace=True)
                return df
            
            # Fallback to yfinance
            logger.info("Loading data from yfinance...")
            import yfinance as yf
            
            # MCX/commodity futures (yfinance) and NSE ETFs
            symbol_map = {
                'GOLDM': 'GC=F',
                'GOLD': 'GC=F',
                'GOLDPETAL': 'GC=F',
                'SILVERM': 'SI=F',
                'SILVER': 'SI=F',
                'SILVERMIC': 'SI=F',
                'GOLDBEES': 'GOLDBEES.NS',
                'GOLDSHARE': 'GOLDSHARE.NS',
                'SGBS': 'SGBS.NS',
                'SILVERETF': 'SILVERETF.NS',
                'SILVERBEES': 'SILVERBEES.NS',
            }
            ticker = symbol_map.get(
                (self.config.symbol or '').upper(),
                'GC=F' if (self.config.metal_type or '').upper() == 'GOLD' else 'SI=F'
            )
            data = yf.Ticker(ticker)
            
            # Calculate period from dates
            if self.config.start_date and self.config.end_date:
                start = datetime.strptime(self.config.start_date, '%Y-%m-%d')
                end = datetime.strptime(self.config.end_date, '%Y-%m-%d')
                days = (end - start).days
                period = f"{max(days, 1)}d"
            else:
                period = "30d"
            
            df = data.history(period=period, interval=self.config.timeframe)
            
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        # EMA
        df['ema_fast'] = df['close'].ewm(span=self.config.fast_ema, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.config.slow_ema, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high = df['high']
        low = df['low']
        close = df['close']
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = true_range.ewm(span=14, adjust=False).mean()
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Momentum
        df['momentum'] = (df['close'] / df['close'].shift(10) - 1) * 100
        
        # Volume ratio
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals"""
        df['signal'] = 0
        df['signal_strength'] = 0.0
        
        for i in range(max(self.config.slow_ema, 26), len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            signal_score = 0.0
            
            # EMA Crossover
            if prev_row['ema_fast'] <= prev_row['ema_slow'] and row['ema_fast'] > row['ema_slow']:
                signal_score += 0.3
            elif prev_row['ema_fast'] >= prev_row['ema_slow'] and row['ema_fast'] < row['ema_slow']:
                signal_score -= 0.3
            
            # RSI
            if row['rsi'] < self.config.rsi_oversold:
                signal_score += 0.2
            elif row['rsi'] > self.config.rsi_overbought:
                signal_score -= 0.2
            
            # MACD
            if prev_row['macd'] <= prev_row['macd_signal'] and row['macd'] > row['macd_signal']:
                signal_score += 0.25
            elif prev_row['macd'] >= prev_row['macd_signal'] and row['macd'] < row['macd_signal']:
                signal_score -= 0.25
            
            # Momentum
            if row['momentum'] > 1:
                signal_score += 0.15
            elif row['momentum'] < -1:
                signal_score -= 0.15
            
            # Volume confirmation
            if row['volume_ratio'] > 1.5:
                price_change = row['close'] - prev_row['close']
                if price_change > 0:
                    signal_score += 0.1
                else:
                    signal_score -= 0.1
            
            # Convert score to signal
            strength = min(abs(signal_score) * 100, 100)
            
            if signal_score > 0.35:
                df.iloc[i, df.columns.get_loc('signal')] = 1  # Buy
            elif signal_score < -0.35:
                df.iloc[i, df.columns.get_loc('signal')] = -1  # Sell
            
            df.iloc[i, df.columns.get_loc('signal_strength')] = strength
        
        return df
    
    def calculate_stop_loss(self, df_slice: pd.DataFrame, entry_price: float, action: str) -> float:
        """Calculate stop loss for a trade"""
        position = TradePosition(
            entry_price=entry_price,
            current_price=df_slice['close'].iloc[-1],
            action=action,
            entry_time=df_slice.index[-1],
            current_stop_loss=None,
            highest_price=entry_price if action == 'BUY' else None,
            lowest_price=entry_price if action == 'SELL' else None
        )
        
        stop_loss_type = StopLossType(self.config.stop_loss_type)
        
        result = self.stop_loss_service.calculate_stop_loss(
            position=position,
            stop_loss_type=stop_loss_type,
            df=df_slice,
            base_stop_loss_pct=self.config.stop_loss_pct
        )
        
        return result.stop_loss_price
    
    def update_trailing_stop(self, current_price: float, df_slice: pd.DataFrame) -> float:
        """Update trailing stop loss"""
        if self.current_position == 0:
            return self.current_stop_loss
        
        position = TradePosition(
            entry_price=self.entry_price,
            current_price=current_price,
            action='BUY' if self.current_position > 0 else 'SELL',
            entry_time=self.entry_time,
            current_stop_loss=self.current_stop_loss,
            highest_price=self.highest_price,
            lowest_price=self.lowest_price
        )
        
        stop_loss_type = StopLossType(self.config.stop_loss_type)
        
        result = self.stop_loss_service.calculate_stop_loss(
            position=position,
            stop_loss_type=stop_loss_type,
            df=df_slice,
            base_stop_loss_pct=self.config.stop_loss_pct
        )
        
        # Only tighten, never widen
        if self.current_position > 0:
            return max(self.current_stop_loss, result.stop_loss_price)
        else:
            return min(self.current_stop_loss, result.stop_loss_price)
    
    def enter_trade(self, timestamp, price: float, action: str, signal_strength: float, quantity: int):
        """Enter a new trade"""
        self.trade_counter += 1
        self.current_position = quantity if action == 'BUY' else -quantity
        self.entry_price = price * (1 + self.config.slippage_pct / 100 if action == 'BUY' else 1 - self.config.slippage_pct / 100)
        self.entry_time = timestamp
        self.entry_signal_strength = signal_strength
        self.highest_price = self.entry_price
        self.lowest_price = self.entry_price
        self.max_favorable = 0.0
        self.max_adverse = 0.0
        
        # Calculate take profit
        if action == 'BUY':
            self.take_profit_price = self.entry_price * (1 + self.config.take_profit_pct / 100)
        else:
            self.take_profit_price = self.entry_price * (1 - self.config.take_profit_pct / 100)
    
    def exit_trade(self, timestamp, price: float, reason: str) -> BacktestTrade:
        """Exit current trade and record results"""
        exit_price = price * (1 - self.config.slippage_pct / 100 if self.current_position > 0 else 1 + self.config.slippage_pct / 100)
        
        # Calculate P&L
        if self.current_position > 0:
            pnl = (exit_price - self.entry_price) * abs(self.current_position)
        else:
            pnl = (self.entry_price - exit_price) * abs(self.current_position)
        
        pnl_pct = (pnl / self.entry_price) * 100
        commission = self.config.commission_per_lot * abs(self.current_position) * 2  # Entry + exit
        
        # Calculate holding duration
        holding_duration = (timestamp - self.entry_time).total_seconds() / 60
        
        trade = BacktestTrade(
            trade_id=self.trade_counter,
            metal_type=self.config.metal_type,
            symbol=self.config.symbol,
            action='BUY' if self.current_position > 0 else 'SELL',
            quantity=abs(self.current_position),
            entry_time=self.entry_time,
            entry_price=self.entry_price,
            entry_signal_strength=self.entry_signal_strength,
            exit_time=timestamp,
            exit_price=exit_price,
            exit_reason=reason,
            initial_stop_loss=self.current_stop_loss,
            final_stop_loss=self.current_stop_loss,
            take_profit_price=self.take_profit_price,
            pnl=pnl - commission,
            pnl_pct=pnl_pct,
            commission=commission,
            max_favorable_excursion=self.max_favorable,
            max_adverse_excursion=self.max_adverse,
            holding_duration_minutes=int(holding_duration)
        )
        
        self.trades.append(trade)
        
        # Update capital
        self.capital += (pnl - commission)
        self.equity_curve.append(self.capital)
        
        # Update peak and drawdown
        self.peak_capital = max(self.peak_capital, self.capital)
        drawdown = (self.peak_capital - self.capital) / self.peak_capital * 100
        self.drawdown_curve.append(drawdown)
        
        # Reset position
        self.current_position = 0
        self.entry_price = None
        self.entry_time = None
        self.current_stop_loss = None
        self.take_profit_price = None
        self.highest_price = None
        self.lowest_price = None
        
        return trade
    
    def run_backtest(self) -> BacktestResults:
        """Run the backtest"""
        start_time = datetime.now()
        
        # Load and prepare data
        df = self.load_historical_data()
        if df.empty:
            logger.error("No data available for backtest")
            return BacktestResults(config=self.config)
        
        logger.info(f"Loaded {len(df)} data points for backtest")
        
        # Calculate indicators and signals
        df = self.calculate_indicators(df)
        df = self.generate_signals(df)
        
        # Remove NaN rows
        df = df.dropna()
        
        # Calculate position size
        position_size = int((self.config.initial_capital * self.config.position_size_pct / 100) / df['close'].iloc[0])
        position_size = max(position_size, 1)
        
        # Run through data
        for i in range(50, len(df)):
            row = df.iloc[i]
            timestamp = df.index[i]
            current_price = row['close']
            high_price = row['high']
            low_price = row['low']
            
            # Skip if outside trading hours
            if hasattr(timestamp, 'hour'):
                if timestamp.hour < self.config.trading_start_hour or timestamp.hour > self.config.trading_end_hour:
                    continue
            
            # If in position, check for exit conditions
            if self.current_position != 0:
                # Update max favorable/adverse excursion
                if self.current_position > 0:
                    self.highest_price = max(self.highest_price, high_price)
                    self.lowest_price = min(self.lowest_price, low_price)
                    self.max_favorable = max(self.max_favorable, (self.highest_price - self.entry_price) / self.entry_price * 100)
                    self.max_adverse = max(self.max_adverse, (self.entry_price - self.lowest_price) / self.entry_price * 100)
                else:
                    self.lowest_price = min(self.lowest_price, low_price)
                    self.highest_price = max(self.highest_price, high_price)
                    self.max_favorable = max(self.max_favorable, (self.entry_price - self.lowest_price) / self.entry_price * 100)
                    self.max_adverse = max(self.max_adverse, (self.highest_price - self.entry_price) / self.entry_price * 100)
                
                # Update trailing stop
                df_slice = df.iloc[max(0, i-50):i+1]
                self.current_stop_loss = self.update_trailing_stop(current_price, df_slice)
                
                # Check stop loss
                if self.current_position > 0 and low_price <= self.current_stop_loss:
                    self.exit_trade(timestamp, self.current_stop_loss, "STOP_LOSS")
                    continue
                elif self.current_position < 0 and high_price >= self.current_stop_loss:
                    self.exit_trade(timestamp, self.current_stop_loss, "STOP_LOSS")
                    continue
                
                # Check take profit
                if self.current_position > 0 and high_price >= self.take_profit_price:
                    self.exit_trade(timestamp, self.take_profit_price, "TAKE_PROFIT")
                    continue
                elif self.current_position < 0 and low_price <= self.take_profit_price:
                    self.exit_trade(timestamp, self.take_profit_price, "TAKE_PROFIT")
                    continue
                
                # Check signal reversal
                if self.current_position > 0 and row['signal'] == -1 and row['signal_strength'] > 60:
                    self.exit_trade(timestamp, current_price, "SIGNAL_REVERSAL")
                    continue
                elif self.current_position < 0 and row['signal'] == 1 and row['signal_strength'] > 60:
                    self.exit_trade(timestamp, current_price, "SIGNAL_REVERSAL")
                    continue
            
            # Check for entry
            if self.current_position == 0:
                if row['signal'] == 1 and row['signal_strength'] >= self.config.min_signal_strength:
                    self.enter_trade(timestamp, current_price, 'BUY', row['signal_strength'], position_size)
                    df_slice = df.iloc[max(0, i-50):i+1]
                    self.current_stop_loss = self.calculate_stop_loss(df_slice, self.entry_price, 'BUY')
                
                elif row['signal'] == -1 and row['signal_strength'] >= self.config.min_signal_strength:
                    self.enter_trade(timestamp, current_price, 'SELL', row['signal_strength'], position_size)
                    df_slice = df.iloc[max(0, i-50):i+1]
                    self.current_stop_loss = self.calculate_stop_loss(df_slice, self.entry_price, 'SELL')
        
        # Close any open position at end
        if self.current_position != 0:
            self.exit_trade(df.index[-1], df['close'].iloc[-1], "END_OF_DATA")
        
        # Calculate results
        results = self.calculate_results(start_time)
        
        return results
    
    def calculate_results(self, start_time: datetime) -> BacktestResults:
        """Calculate backtest statistics"""
        results = BacktestResults(config=self.config)
        results.backtest_start = start_time
        results.backtest_end = datetime.now()
        results.run_duration_seconds = (results.backtest_end - results.backtest_start).total_seconds()
        
        results.trades = self.trades
        results.equity_curve = self.equity_curve
        results.drawdown_curve = self.drawdown_curve
        
        if not self.trades:
            return results
        
        # Basic statistics
        results.total_trades = len(self.trades)
        results.winning_trades = len([t for t in self.trades if t.pnl > 0])
        results.losing_trades = len([t for t in self.trades if t.pnl <= 0])
        results.win_rate = results.winning_trades / results.total_trades * 100 if results.total_trades > 0 else 0
        
        # P&L metrics
        pnls = [t.pnl for t in self.trades]
        results.total_pnl = sum(pnls)
        results.total_pnl_pct = (results.total_pnl / self.config.initial_capital) * 100
        
        winning_pnls = [t.pnl for t in self.trades if t.pnl > 0]
        losing_pnls = [t.pnl for t in self.trades if t.pnl <= 0]
        
        results.gross_profit = sum(winning_pnls) if winning_pnls else 0
        results.gross_loss = abs(sum(losing_pnls)) if losing_pnls else 0
        results.profit_factor = results.gross_profit / results.gross_loss if results.gross_loss > 0 else float('inf')
        
        results.avg_win = np.mean(winning_pnls) if winning_pnls else 0
        results.avg_loss = abs(np.mean(losing_pnls)) if losing_pnls else 0
        results.avg_trade = np.mean(pnls) if pnls else 0
        results.largest_win = max(pnls) if pnls else 0
        results.largest_loss = min(pnls) if pnls else 0
        
        # Risk metrics
        results.max_drawdown = max(self.drawdown_curve) if self.drawdown_curve else 0
        results.max_drawdown_pct = results.max_drawdown
        
        # Sharpe ratio (assuming 0% risk-free rate)
        daily_returns = pd.Series(pnls)
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            results.sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        
        # Sortino ratio
        negative_returns = daily_returns[daily_returns < 0]
        if len(negative_returns) > 0 and negative_returns.std() > 0:
            results.sortino_ratio = (daily_returns.mean() / negative_returns.std()) * np.sqrt(252)
        
        # Calmar ratio
        if results.max_drawdown > 0:
            annual_return = results.total_pnl_pct  # Simplified
            results.calmar_ratio = annual_return / results.max_drawdown
        
        # Time metrics
        holding_times = [t.holding_duration_minutes for t in self.trades]
        results.avg_holding_time_minutes = np.mean(holding_times) if holding_times else 0
        results.max_holding_time_minutes = max(holding_times) if holding_times else 0
        
        # Exit reasons
        for trade in self.trades:
            reason = trade.exit_reason or "UNKNOWN"
            results.exit_reasons[reason] = results.exit_reasons.get(reason, 0) + 1
        
        return results
    
    def generate_report(self, results: BacktestResults) -> str:
        """Generate a text report of backtest results"""
        report = []
        report.append("=" * 60)
        report.append(f"BACKTEST REPORT - {results.config.metal_type}")
        report.append("=" * 60)
        report.append("")
        
        report.append("CONFIGURATION")
        report.append("-" * 40)
        report.append(f"Symbol: {results.config.symbol}")
        report.append(f"Timeframe: {results.config.timeframe}")
        report.append(f"Stop Loss Type: {results.config.stop_loss_type}")
        report.append(f"Stop Loss %: {results.config.stop_loss_pct}")
        report.append(f"Take Profit %: {results.config.take_profit_pct}")
        report.append(f"Initial Capital: {results.config.initial_capital:,.2f}")
        report.append("")
        
        report.append("TRADE STATISTICS")
        report.append("-" * 40)
        report.append(f"Total Trades: {results.total_trades}")
        report.append(f"Winning Trades: {results.winning_trades}")
        report.append(f"Losing Trades: {results.losing_trades}")
        report.append(f"Win Rate: {results.win_rate:.2f}%")
        report.append("")
        
        report.append("PROFIT & LOSS")
        report.append("-" * 40)
        report.append(f"Total P&L: {results.total_pnl:,.2f} ({results.total_pnl_pct:.2f}%)")
        report.append(f"Gross Profit: {results.gross_profit:,.2f}")
        report.append(f"Gross Loss: {results.gross_loss:,.2f}")
        report.append(f"Profit Factor: {results.profit_factor:.2f}")
        report.append(f"Average Win: {results.avg_win:,.2f}")
        report.append(f"Average Loss: {results.avg_loss:,.2f}")
        report.append(f"Average Trade: {results.avg_trade:,.2f}")
        report.append(f"Largest Win: {results.largest_win:,.2f}")
        report.append(f"Largest Loss: {results.largest_loss:,.2f}")
        report.append("")
        
        report.append("RISK METRICS")
        report.append("-" * 40)
        report.append(f"Max Drawdown: {results.max_drawdown_pct:.2f}%")
        report.append(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
        report.append(f"Sortino Ratio: {results.sortino_ratio:.2f}")
        report.append(f"Calmar Ratio: {results.calmar_ratio:.2f}")
        report.append("")
        
        report.append("TIME METRICS")
        report.append("-" * 40)
        report.append(f"Avg Holding Time: {results.avg_holding_time_minutes:.0f} minutes")
        report.append(f"Max Holding Time: {results.max_holding_time_minutes:.0f} minutes")
        report.append("")
        
        report.append("EXIT REASONS")
        report.append("-" * 40)
        for reason, count in sorted(results.exit_reasons.items(), key=lambda x: x[1], reverse=True):
            pct = count / results.total_trades * 100 if results.total_trades > 0 else 0
            report.append(f"{reason}: {count} ({pct:.1f}%)")
        report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def run_metals_backtest(
    metal_type: str = "GOLD",
    start_date: str = "",
    end_date: str = "",
    stop_loss_type: str = "ADAPTIVE",
    **kwargs
) -> BacktestResults:
    """
    Run a backtest for metals trading strategy
    
    Args:
        metal_type: GOLD, SILVER, or BOTH
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        stop_loss_type: FIXED, TRAILING, ATR_BASED, or ADAPTIVE
        **kwargs: Additional config parameters
    
    Returns:
        BacktestResults object
    """
    # Set defaults based on metal type
    if metal_type == "GOLD":
        symbol = "GOLDM"
        stop_loss_pct = 1.5
        take_profit_pct = 3.0
    elif metal_type == "SILVER":
        symbol = "SILVERM"
        stop_loss_pct = 2.5
        take_profit_pct = 5.0
    else:
        symbol = "GOLDM"
        stop_loss_pct = 2.0
        take_profit_pct = 4.0
    
    config = BacktestConfig(
        metal_type=metal_type,
        symbol=kwargs.get('symbol', symbol),
        start_date=start_date,
        end_date=end_date,
        stop_loss_type=stop_loss_type,
        stop_loss_pct=kwargs.get('stop_loss_pct', stop_loss_pct),
        take_profit_pct=kwargs.get('take_profit_pct', take_profit_pct),
        **{k: v for k, v in kwargs.items() if k not in ['symbol', 'stop_loss_pct', 'take_profit_pct']}
    )
    
    engine = MetalsBacktestEngine(config)
    results = engine.run_backtest()
    
    # Print report
    report = engine.generate_report(results)
    print(report)
    
    return results


if __name__ == "__main__":
    # Run example backtest
    results = run_metals_backtest(
        metal_type="GOLD",
        start_date="2025-01-01",
        end_date="2025-01-30",
        stop_loss_type="ADAPTIVE",
        timeframe="5m"
    )
