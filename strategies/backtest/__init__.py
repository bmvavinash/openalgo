"""
Option Strategy Backtesting Framework
Comprehensive backtesting system for option trading strategies.
"""

# Relative imports so package resolves when app runs from project root (openalgo)
from .option_backtest_framework import (
    BacktestConfig,
    OptionBacktestEngine,
    OptionPricer,
    Trade,
    BacktestResults,
    AnalyticsCalculator
)
from .strategy_backtests import STRATEGY_BACKTESTS

__all__ = [
    'BacktestConfig',
    'OptionBacktestEngine',
    'OptionPricer',
    'Trade',
    'BacktestResults',
    'AnalyticsCalculator',
    'STRATEGY_BACKTESTS'
]

