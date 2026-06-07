"""
Adaptive Stop Loss Service for Metals Trading

This service implements multiple stop-loss mechanisms:
1. Fixed Stop Loss - Simple percentage-based
2. Trailing Stop Loss - Moves with price in favorable direction
3. ATR-Based Stop Loss - Based on market volatility (Average True Range)
4. Adaptive Stop Loss - Combines ATR with volatility regime detection

The adaptive mechanism adjusts stop-loss based on:
- Current market volatility
- Price momentum
- Support/resistance levels
- Time of day patterns
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class StopLossType(Enum):
    FIXED = "FIXED"
    TRAILING = "TRAILING"
    ATR_BASED = "ATR_BASED"
    ADAPTIVE = "ADAPTIVE"


class VolatilityRegime(Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


@dataclass
class StopLossResult:
    """Result of stop-loss calculation"""
    stop_loss_price: float
    stop_loss_type: str
    distance_pct: float
    volatility_regime: str
    atr_value: Optional[float] = None
    notes: str = ""


@dataclass
class TradePosition:
    """Current trade position"""
    entry_price: float
    current_price: float
    action: str  # BUY or SELL
    entry_time: datetime
    current_stop_loss: Optional[float] = None
    highest_price: Optional[float] = None  # For trailing stops on LONG
    lowest_price: Optional[float] = None   # For trailing stops on SHORT


class AdaptiveStopLossService:
    """
    Adaptive Stop Loss Service
    
    Implements intelligent stop-loss management that adapts to market conditions.
    """
    
    def __init__(self):
        # Default configuration
        self.default_fixed_pct = 2.0
        self.default_trailing_pct = 1.5
        self.default_atr_multiplier = 2.0
        
        # Volatility regime thresholds (based on ATR percentile)
        self.volatility_thresholds = {
            'low': 25,      # Below 25th percentile
            'normal': 75,   # 25th to 75th percentile
            'high': 90,     # 75th to 90th percentile
            'extreme': 100  # Above 90th percentile
        }
        
        # Adaptive multipliers by volatility regime
        self.regime_multipliers = {
            VolatilityRegime.LOW: 1.0,
            VolatilityRegime.NORMAL: 1.5,
            VolatilityRegime.HIGH: 2.0,
            VolatilityRegime.EXTREME: 2.5
        }
        
        # Time-based adjustments (IST)
        self.time_adjustments = {
            'market_open': 1.5,    # 9:00-9:30 - Higher volatility
            'morning': 1.2,        # 9:30-12:00
            'midday': 1.0,         # 12:00-14:00
            'afternoon': 1.1,      # 14:00-15:30
            'pre_close': 1.3,      # 15:30-16:00 - Can be volatile
            'after_hours': 1.0     # Extended hours
        }
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR)
        
        ATR = Average of True Range over N periods
        True Range = max(H-L, |H-Pc|, |L-Pc|)
        where Pc = Previous Close
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate ATR using EMA
        atr = true_range.ewm(span=period, adjust=False).mean()
        
        return atr
    
    def calculate_volatility_percentile(self, atr_series: pd.Series, lookback: int = 100) -> float:
        """Calculate where current ATR falls in historical distribution"""
        if len(atr_series) < lookback:
            lookback = len(atr_series)
        
        current_atr = atr_series.iloc[-1]
        historical_atr = atr_series.iloc[-lookback:]
        
        percentile = (historical_atr < current_atr).sum() / len(historical_atr) * 100
        return percentile
    
    def detect_volatility_regime(self, atr_percentile: float) -> VolatilityRegime:
        """Determine volatility regime based on ATR percentile"""
        if atr_percentile < self.volatility_thresholds['low']:
            return VolatilityRegime.LOW
        elif atr_percentile < self.volatility_thresholds['normal']:
            return VolatilityRegime.NORMAL
        elif atr_percentile < self.volatility_thresholds['high']:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME
    
    def get_time_adjustment(self) -> float:
        """Get time-based stop-loss adjustment factor"""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        current_time = hour + minute / 60
        
        if 9.0 <= current_time < 9.5:
            return self.time_adjustments['market_open']
        elif 9.5 <= current_time < 12.0:
            return self.time_adjustments['morning']
        elif 12.0 <= current_time < 14.0:
            return self.time_adjustments['midday']
        elif 14.0 <= current_time < 15.5:
            return self.time_adjustments['afternoon']
        elif 15.5 <= current_time < 16.0:
            return self.time_adjustments['pre_close']
        else:
            return self.time_adjustments['after_hours']
    
    def calculate_support_resistance(self, df: pd.DataFrame, lookback: int = 50) -> Tuple[List[float], List[float]]:
        """
        Calculate support and resistance levels using pivot points
        """
        recent_df = df.tail(lookback)
        
        # Identify pivot highs and lows
        pivot_highs = []
        pivot_lows = []
        
        for i in range(2, len(recent_df) - 2):
            high = recent_df['high'].iloc[i]
            low = recent_df['low'].iloc[i]
            
            # Pivot high
            if (high > recent_df['high'].iloc[i-1] and 
                high > recent_df['high'].iloc[i-2] and
                high > recent_df['high'].iloc[i+1] and 
                high > recent_df['high'].iloc[i+2]):
                pivot_highs.append(high)
            
            # Pivot low
            if (low < recent_df['low'].iloc[i-1] and 
                low < recent_df['low'].iloc[i-2] and
                low < recent_df['low'].iloc[i+1] and 
                low < recent_df['low'].iloc[i+2]):
                pivot_lows.append(low)
        
        return pivot_lows, pivot_highs  # Support, Resistance
    
    def calculate_fixed_stop_loss(
        self, 
        position: TradePosition, 
        stop_loss_pct: float = None
    ) -> StopLossResult:
        """
        Calculate fixed percentage stop loss
        """
        pct = stop_loss_pct or self.default_fixed_pct
        
        if position.action == 'BUY':
            stop_price = position.entry_price * (1 - pct / 100)
        else:  # SELL
            stop_price = position.entry_price * (1 + pct / 100)
        
        return StopLossResult(
            stop_loss_price=stop_price,
            stop_loss_type=StopLossType.FIXED.value,
            distance_pct=pct,
            volatility_regime=VolatilityRegime.NORMAL.value,
            notes=f"Fixed {pct}% stop loss from entry"
        )
    
    def calculate_trailing_stop_loss(
        self,
        position: TradePosition,
        trailing_pct: float = None
    ) -> StopLossResult:
        """
        Calculate trailing stop loss
        
        For LONG: Stop trails below the highest price reached
        For SHORT: Stop trails above the lowest price reached
        """
        pct = trailing_pct or self.default_trailing_pct
        
        if position.action == 'BUY':
            # Use highest price since entry
            high_watermark = position.highest_price or max(position.entry_price, position.current_price)
            stop_price = high_watermark * (1 - pct / 100)
            
            # Don't lower the stop loss
            if position.current_stop_loss and stop_price < position.current_stop_loss:
                stop_price = position.current_stop_loss
                
        else:  # SELL
            # Use lowest price since entry
            low_watermark = position.lowest_price or min(position.entry_price, position.current_price)
            stop_price = low_watermark * (1 + pct / 100)
            
            # Don't raise the stop loss
            if position.current_stop_loss and stop_price > position.current_stop_loss:
                stop_price = position.current_stop_loss
        
        return StopLossResult(
            stop_loss_price=stop_price,
            stop_loss_type=StopLossType.TRAILING.value,
            distance_pct=pct,
            volatility_regime=VolatilityRegime.NORMAL.value,
            notes=f"Trailing {pct}% stop loss"
        )
    
    def calculate_atr_stop_loss(
        self,
        position: TradePosition,
        df: pd.DataFrame,
        atr_multiplier: float = None,
        atr_period: int = 14
    ) -> StopLossResult:
        """
        Calculate ATR-based stop loss
        
        Stop Loss = Entry Price +/- (ATR * Multiplier)
        """
        multiplier = atr_multiplier or self.default_atr_multiplier
        
        # Calculate ATR
        atr = self.calculate_atr(df, atr_period)
        current_atr = atr.iloc[-1]
        
        # Calculate volatility regime
        atr_percentile = self.calculate_volatility_percentile(atr)
        volatility_regime = self.detect_volatility_regime(atr_percentile)
        
        if position.action == 'BUY':
            stop_price = position.entry_price - (current_atr * multiplier)
        else:  # SELL
            stop_price = position.entry_price + (current_atr * multiplier)
        
        distance_pct = abs(position.entry_price - stop_price) / position.entry_price * 100
        
        return StopLossResult(
            stop_loss_price=stop_price,
            stop_loss_type=StopLossType.ATR_BASED.value,
            distance_pct=distance_pct,
            volatility_regime=volatility_regime.value,
            atr_value=current_atr,
            notes=f"ATR-based stop: ATR={current_atr:.2f}, Multiplier={multiplier}"
        )
    
    def calculate_adaptive_stop_loss(
        self,
        position: TradePosition,
        df: pd.DataFrame,
        base_stop_loss_pct: float = None,
        atr_period: int = 14,
        include_support_resistance: bool = True
    ) -> StopLossResult:
        """
        Calculate adaptive stop loss
        
        This is the most sophisticated stop-loss mechanism that combines:
        1. ATR-based volatility adjustment
        2. Volatility regime detection
        3. Time-of-day adjustments
        4. Support/resistance awareness (optional)
        5. Trailing functionality
        """
        base_pct = base_stop_loss_pct or self.default_fixed_pct
        
        # Calculate ATR and volatility metrics
        atr = self.calculate_atr(df, atr_period)
        current_atr = atr.iloc[-1]
        atr_percentile = self.calculate_volatility_percentile(atr)
        volatility_regime = self.detect_volatility_regime(atr_percentile)
        
        # Get regime multiplier
        regime_multiplier = self.regime_multipliers[volatility_regime]
        
        # Get time adjustment
        time_adjustment = self.get_time_adjustment()
        
        # Calculate base ATR stop
        atr_based_stop_distance = current_atr * self.default_atr_multiplier
        
        # Calculate percentage-based stop distance
        pct_based_stop_distance = position.entry_price * (base_pct / 100)
        
        # Use the larger of ATR-based or percentage-based
        base_stop_distance = max(atr_based_stop_distance, pct_based_stop_distance)
        
        # Apply regime and time adjustments
        adjusted_stop_distance = base_stop_distance * regime_multiplier * time_adjustment
        
        # Calculate initial stop price
        if position.action == 'BUY':
            stop_price = position.entry_price - adjusted_stop_distance
        else:  # SELL
            stop_price = position.entry_price + adjusted_stop_distance
        
        # Apply trailing logic
        if position.current_stop_loss:
            if position.action == 'BUY':
                # Calculate potential new trailing stop
                high_watermark = position.highest_price or max(position.entry_price, position.current_price)
                trailing_stop = high_watermark - adjusted_stop_distance
                
                # Use the higher of current stop or new trailing stop
                stop_price = max(position.current_stop_loss, trailing_stop)
            else:  # SELL
                # Calculate potential new trailing stop
                low_watermark = position.lowest_price or min(position.entry_price, position.current_price)
                trailing_stop = low_watermark + adjusted_stop_distance
                
                # Use the lower of current stop or new trailing stop
                stop_price = min(position.current_stop_loss, trailing_stop)
        
        # Optional: Adjust to support/resistance levels
        if include_support_resistance and len(df) > 50:
            supports, resistances = self.calculate_support_resistance(df)
            stop_price = self._adjust_to_levels(
                stop_price, position, supports, resistances
            )
        
        # Calculate final distance percentage
        distance_pct = abs(position.entry_price - stop_price) / position.entry_price * 100
        
        notes = [
            f"Adaptive stop loss",
            f"Regime: {volatility_regime.value} ({regime_multiplier}x)",
            f"Time adj: {time_adjustment}x",
            f"ATR: {current_atr:.2f}"
        ]
        
        return StopLossResult(
            stop_loss_price=round(stop_price, 2),
            stop_loss_type=StopLossType.ADAPTIVE.value,
            distance_pct=round(distance_pct, 2),
            volatility_regime=volatility_regime.value,
            atr_value=current_atr,
            notes=" | ".join(notes)
        )
    
    def _adjust_to_levels(
        self,
        stop_price: float,
        position: TradePosition,
        supports: List[float],
        resistances: List[float]
    ) -> float:
        """
        Adjust stop price to nearby support/resistance levels
        
        For LONG: Place stop just below support
        For SHORT: Place stop just above resistance
        """
        buffer = 0.001  # 0.1% buffer from level
        
        if position.action == 'BUY':
            # Find nearest support below stop price
            nearby_supports = [s for s in supports if s < stop_price * 1.02]
            if nearby_supports:
                nearest_support = max(nearby_supports)
                # Place stop just below support
                adjusted_stop = nearest_support * (1 - buffer)
                
                # Only use if not too far from original stop
                if abs(adjusted_stop - stop_price) / stop_price < 0.01:  # Within 1%
                    return adjusted_stop
        else:  # SELL
            # Find nearest resistance above stop price
            nearby_resistances = [r for r in resistances if r > stop_price * 0.98]
            if nearby_resistances:
                nearest_resistance = min(nearby_resistances)
                # Place stop just above resistance
                adjusted_stop = nearest_resistance * (1 + buffer)
                
                # Only use if not too far from original stop
                if abs(adjusted_stop - stop_price) / stop_price < 0.01:
                    return adjusted_stop
        
        return stop_price
    
    def calculate_stop_loss(
        self,
        position: TradePosition,
        stop_loss_type: StopLossType,
        df: pd.DataFrame = None,
        **kwargs
    ) -> StopLossResult:
        """
        Main entry point for stop loss calculation
        
        Args:
            position: Current trade position
            stop_loss_type: Type of stop loss to calculate
            df: Historical price data (required for ATR and adaptive)
            **kwargs: Additional parameters for specific stop loss types
        """
        if stop_loss_type == StopLossType.FIXED:
            return self.calculate_fixed_stop_loss(position, kwargs.get('stop_loss_pct'))
        
        elif stop_loss_type == StopLossType.TRAILING:
            return self.calculate_trailing_stop_loss(position, kwargs.get('trailing_pct'))
        
        elif stop_loss_type == StopLossType.ATR_BASED:
            if df is None or df.empty:
                logger.warning("No price data provided for ATR stop loss, using fixed")
                return self.calculate_fixed_stop_loss(position)
            return self.calculate_atr_stop_loss(
                position, df,
                kwargs.get('atr_multiplier'),
                kwargs.get('atr_period', 14)
            )
        
        elif stop_loss_type == StopLossType.ADAPTIVE:
            if df is None or df.empty:
                logger.warning("No price data provided for adaptive stop loss, using fixed")
                return self.calculate_fixed_stop_loss(position)
            return self.calculate_adaptive_stop_loss(
                position, df,
                kwargs.get('base_stop_loss_pct'),
                kwargs.get('atr_period', 14),
                kwargs.get('include_support_resistance', True)
            )
        
        else:
            logger.warning(f"Unknown stop loss type: {stop_loss_type}, using fixed")
            return self.calculate_fixed_stop_loss(position)
    
    def should_update_stop_loss(
        self,
        position: TradePosition,
        new_stop_result: StopLossResult
    ) -> bool:
        """
        Determine if stop loss should be updated
        
        Rules:
        - Never move stop loss in unfavorable direction
        - Minimum movement threshold to avoid excessive updates
        """
        if position.current_stop_loss is None:
            return True
        
        min_change_pct = 0.1  # Minimum 0.1% change to update
        
        if position.action == 'BUY':
            # For long, only tighten (raise) stop loss
            if new_stop_result.stop_loss_price > position.current_stop_loss:
                change_pct = abs(new_stop_result.stop_loss_price - position.current_stop_loss) / position.current_stop_loss * 100
                return change_pct >= min_change_pct
            return False
        
        else:  # SELL
            # For short, only tighten (lower) stop loss
            if new_stop_result.stop_loss_price < position.current_stop_loss:
                change_pct = abs(new_stop_result.stop_loss_price - position.current_stop_loss) / position.current_stop_loss * 100
                return change_pct >= min_change_pct
            return False
    
    def check_stop_loss_hit(
        self,
        position: TradePosition,
        current_price: float = None
    ) -> Tuple[bool, str]:
        """
        Check if current price has hit stop loss
        
        Returns:
            Tuple of (is_hit, reason)
        """
        price = current_price or position.current_price
        
        if position.current_stop_loss is None:
            return False, ""
        
        if position.action == 'BUY':
            if price <= position.current_stop_loss:
                return True, f"STOP_LOSS: Price {price} <= SL {position.current_stop_loss}"
        else:  # SELL
            if price >= position.current_stop_loss:
                return True, f"STOP_LOSS: Price {price} >= SL {position.current_stop_loss}"
        
        return False, ""


# Global instance
adaptive_stop_loss_service = AdaptiveStopLossService()
