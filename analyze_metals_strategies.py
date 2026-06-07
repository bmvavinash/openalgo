#!/usr/bin/env python
"""
Metals Strategy Analysis Script

Comprehensive analysis of Gold and Silver trading strategies
with historical data, backtesting, and performance metrics.

This script generates a detailed markdown report.
"""

import os
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np

print("=" * 70)
print("METALS STRATEGY ANALYSIS - GOLD & SILVER")
print("=" * 70)
print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()


class MetalsAnalyzer:
    """
    Comprehensive analyzer for Gold and Silver trading strategies
    """
    
    def __init__(self):
        self.results = {}
        self.gold_data = None
        self.silver_data = None
        
    def fetch_data(self, symbol: str, period: str = "60d") -> pd.DataFrame:
        """Fetch historical data using yfinance"""
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval="1h")
            
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
                print(f"  Fetched {len(df)} records for {symbol}")
            return df
            
        except Exception as e:
            print(f"  Error fetching {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate all technical indicators"""
        if df.empty:
            return df
        
        # EMAs
        df['ema_fast'] = df['close'].ewm(span=params['fast_ema'], adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=params['slow_ema'], adjust=False).mean()
        df['ema_trend'] = df['close'].ewm(span=params.get('trend_ema', 50), adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=params['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=params['rsi_period']).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=params['macd_fast'], adjust=False).mean()
        exp2 = df['close'].ewm(span=params['macd_slow'], adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=params['macd_signal'], adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # ATR for volatility
        high = df['high']
        low = df['low']
        close = df['close']
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = true_range.ewm(span=14, adjust=False).mean()
        df['atr_pct'] = (df['atr'] / df['close']) * 100
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (2 * bb_std)
        df['bb_lower'] = df['bb_middle'] - (2 * bb_std)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Momentum
        df['momentum'] = (df['close'] / df['close'].shift(10) - 1) * 100
        df['roc'] = ((df['close'] - df['close'].shift(12)) / df['close'].shift(12)) * 100
        
        # Volume analysis
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Price change
        df['price_change'] = df['close'].pct_change() * 100
        df['price_change_5'] = df['close'].pct_change(5) * 100
        
        return df
    
    def generate_signals(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Generate trading signals"""
        if df.empty:
            return df
        
        df['signal'] = 0
        df['signal_strength'] = 0.0
        df['signal_components'] = ''
        
        for i in range(max(params['slow_ema'], 26), len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            components = []
            signal_score = 0.0
            
            # 1. EMA Crossover (30% weight)
            if prev_row['ema_fast'] <= prev_row['ema_slow'] and row['ema_fast'] > row['ema_slow']:
                signal_score += 0.30
                components.append('EMA_BUY')
            elif prev_row['ema_fast'] >= prev_row['ema_slow'] and row['ema_fast'] < row['ema_slow']:
                signal_score -= 0.30
                components.append('EMA_SELL')
            
            # 2. RSI (20% weight)
            if row['rsi'] < params['rsi_oversold']:
                signal_score += 0.20
                components.append(f'RSI_OVERSOLD({row["rsi"]:.1f})')
            elif row['rsi'] > params['rsi_overbought']:
                signal_score -= 0.20
                components.append(f'RSI_OVERBOUGHT({row["rsi"]:.1f})')
            
            # 3. MACD (25% weight)
            if prev_row['macd'] <= prev_row['macd_signal'] and row['macd'] > row['macd_signal']:
                signal_score += 0.25
                components.append('MACD_BUY')
            elif prev_row['macd'] >= prev_row['macd_signal'] and row['macd'] < row['macd_signal']:
                signal_score -= 0.25
                components.append('MACD_SELL')
            
            # 4. Momentum (15% weight)
            if row['momentum'] > 1.5:
                signal_score += 0.15
                components.append(f'MOM_UP({row["momentum"]:.1f}%)')
            elif row['momentum'] < -1.5:
                signal_score -= 0.15
                components.append(f'MOM_DOWN({row["momentum"]:.1f}%)')
            
            # 5. Volume confirmation (10% weight)
            if row['volume_ratio'] > 1.5:
                price_change = row['close'] - prev_row['close']
                if price_change > 0:
                    signal_score += 0.10
                    components.append('VOL_CONFIRM_UP')
                else:
                    signal_score -= 0.10
                    components.append('VOL_CONFIRM_DOWN')
            
            # Calculate final signal
            strength = min(abs(signal_score) * 100, 100)
            
            if signal_score > params['signal_threshold']:
                df.iloc[i, df.columns.get_loc('signal')] = 1
            elif signal_score < -params['signal_threshold']:
                df.iloc[i, df.columns.get_loc('signal')] = -1
            
            df.iloc[i, df.columns.get_loc('signal_strength')] = strength
            df.iloc[i, df.columns.get_loc('signal_components')] = ' | '.join(components)
        
        return df
    
    def backtest_strategy(self, df: pd.DataFrame, params: Dict) -> Dict:
        """Run backtest on the strategy"""
        if df.empty:
            return {}
        
        trades = []
        position = 0
        entry_price = None
        entry_time = None
        entry_idx = None
        stop_loss = None
        take_profit = None
        highest_price = None
        lowest_price = None
        
        capital = 100000
        initial_capital = capital
        equity_curve = [capital]
        
        for i in range(len(df)):
            row = df.iloc[i]
            current_price = row['close']
            current_time = df.index[i]
            
            if position != 0:
                # Update trailing stop for adaptive SL
                if position > 0:
                    highest_price = max(highest_price, current_price)
                    # Adaptive: tighten stop as price moves favorably
                    new_stop = highest_price * (1 - params['trailing_stop_pct'] / 100)
                    if new_stop > stop_loss:
                        stop_loss = new_stop
                else:
                    lowest_price = min(lowest_price, current_price)
                    new_stop = lowest_price * (1 + params['trailing_stop_pct'] / 100)
                    if new_stop < stop_loss:
                        stop_loss = new_stop
                
                # Check exit conditions
                exit_reason = None
                
                if position > 0:
                    if current_price <= stop_loss:
                        exit_reason = 'STOP_LOSS'
                    elif current_price >= take_profit:
                        exit_reason = 'TAKE_PROFIT'
                    elif row['signal'] == -1 and row['signal_strength'] > 60:
                        exit_reason = 'SIGNAL_REVERSAL'
                else:
                    if current_price >= stop_loss:
                        exit_reason = 'STOP_LOSS'
                    elif current_price <= take_profit:
                        exit_reason = 'TAKE_PROFIT'
                    elif row['signal'] == 1 and row['signal_strength'] > 60:
                        exit_reason = 'SIGNAL_REVERSAL'
                
                if exit_reason:
                    # Close position
                    if position > 0:
                        pnl = (current_price - entry_price) * position
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    else:
                        pnl = (entry_price - current_price) * abs(position)
                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                    
                    capital += pnl
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'action': 'BUY' if position > 0 else 'SELL',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'exit_reason': exit_reason,
                        'holding_bars': i - entry_idx
                    })
                    
                    position = 0
                    entry_price = None
                    entry_time = None
                    stop_loss = None
                    take_profit = None
            
            # Check entry conditions
            if position == 0:
                if row['signal'] == 1 and row['signal_strength'] >= params['min_signal_strength']:
                    # Long entry
                    position = 1
                    entry_price = current_price
                    entry_time = current_time
                    entry_idx = i
                    highest_price = current_price
                    
                    # Calculate initial stop loss using ATR
                    atr_stop = current_price - (row['atr'] * params['atr_multiplier'])
                    pct_stop = current_price * (1 - params['stop_loss_pct'] / 100)
                    stop_loss = max(atr_stop, pct_stop)  # Use tighter of the two
                    
                    take_profit = current_price * (1 + params['take_profit_pct'] / 100)
                    
                elif row['signal'] == -1 and row['signal_strength'] >= params['min_signal_strength']:
                    # Short entry
                    position = -1
                    entry_price = current_price
                    entry_time = current_time
                    entry_idx = i
                    lowest_price = current_price
                    
                    atr_stop = current_price + (row['atr'] * params['atr_multiplier'])
                    pct_stop = current_price * (1 + params['stop_loss_pct'] / 100)
                    stop_loss = min(atr_stop, pct_stop)
                    
                    take_profit = current_price * (1 - params['take_profit_pct'] / 100)
            
            equity_curve.append(capital)
        
        # Close any open position at end
        if position != 0:
            current_price = df['close'].iloc[-1]
            if position > 0:
                pnl = (current_price - entry_price) * position
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl = (entry_price - current_price) * abs(position)
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            capital += pnl
            trades.append({
                'entry_time': entry_time,
                'exit_time': df.index[-1],
                'action': 'BUY' if position > 0 else 'SELL',
                'entry_price': entry_price,
                'exit_price': current_price,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'exit_reason': 'END_OF_DATA',
                'holding_bars': len(df) - entry_idx
            })
        
        # Calculate metrics
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'total_pnl_pct': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'trades': [],
                'equity_curve': equity_curve
            }
        
        winning = [t for t in trades if t['pnl'] > 0]
        losing = [t for t in trades if t['pnl'] <= 0]
        
        total_pnl = sum(t['pnl'] for t in trades)
        gross_profit = sum(t['pnl'] for t in winning) if winning else 0
        gross_loss = abs(sum(t['pnl'] for t in losing)) if losing else 0
        
        # Calculate max drawdown
        peak = equity_curve[0]
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            max_dd = max(max_dd, dd)
        
        # Sharpe ratio (simplified)
        returns = pd.Series([t['pnl_pct'] for t in trades])
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': len(winning) / len(trades) * 100 if trades else 0,
            'total_pnl': total_pnl,
            'total_pnl_pct': (total_pnl / initial_capital) * 100,
            'avg_win': np.mean([t['pnl'] for t in winning]) if winning else 0,
            'avg_loss': abs(np.mean([t['pnl'] for t in losing])) if losing else 0,
            'profit_factor': gross_profit / gross_loss if gross_loss > 0 else float('inf'),
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe,
            'exit_reasons': {
                'STOP_LOSS': len([t for t in trades if t['exit_reason'] == 'STOP_LOSS']),
                'TAKE_PROFIT': len([t for t in trades if t['exit_reason'] == 'TAKE_PROFIT']),
                'SIGNAL_REVERSAL': len([t for t in trades if t['exit_reason'] == 'SIGNAL_REVERSAL']),
                'END_OF_DATA': len([t for t in trades if t['exit_reason'] == 'END_OF_DATA'])
            },
            'trades': trades,
            'equity_curve': equity_curve
        }
    
    def analyze_market_conditions(self, df: pd.DataFrame) -> Dict:
        """Analyze current market conditions"""
        if df.empty:
            return {}
        
        recent = df.tail(20)  # Last 20 bars
        
        # Trend analysis
        current_price = df['close'].iloc[-1]
        ema_fast = df['ema_fast'].iloc[-1]
        ema_slow = df['ema_slow'].iloc[-1]
        ema_trend = df['ema_trend'].iloc[-1]
        
        if current_price > ema_trend and ema_fast > ema_slow:
            trend = 'BULLISH'
        elif current_price < ema_trend and ema_fast < ema_slow:
            trend = 'BEARISH'
        else:
            trend = 'SIDEWAYS'
        
        # Volatility regime
        avg_atr_pct = df['atr_pct'].iloc[-20:].mean()
        current_atr_pct = df['atr_pct'].iloc[-1]
        
        if current_atr_pct > avg_atr_pct * 1.5:
            volatility = 'HIGH'
        elif current_atr_pct < avg_atr_pct * 0.7:
            volatility = 'LOW'
        else:
            volatility = 'NORMAL'
        
        # Support/Resistance
        recent_high = recent['high'].max()
        recent_low = recent['low'].min()
        
        return {
            'trend': trend,
            'volatility': volatility,
            'current_price': current_price,
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'rsi': df['rsi'].iloc[-1],
            'macd': df['macd'].iloc[-1],
            'macd_signal': df['macd_signal'].iloc[-1],
            'atr': df['atr'].iloc[-1],
            'atr_pct': current_atr_pct,
            'avg_atr_pct': avg_atr_pct,
            'recent_high': recent_high,
            'recent_low': recent_low,
            'bb_position': df['bb_position'].iloc[-1],
            'momentum': df['momentum'].iloc[-1],
            'volume_ratio': df['volume_ratio'].iloc[-1],
            'price_change_24h': df['close'].iloc[-1] / df['close'].iloc[-24] - 1 if len(df) > 24 else 0,
            'last_signal': df['signal'].iloc[-1],
            'last_signal_strength': df['signal_strength'].iloc[-1],
            'last_signal_components': df['signal_components'].iloc[-1]
        }
    
    def run_analysis(self):
        """Run complete analysis for Gold and Silver"""
        
        # Gold parameters (less volatile)
        gold_params = {
            'fast_ema': 9,
            'slow_ema': 21,
            'trend_ema': 50,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'signal_threshold': 0.30,
            'min_signal_strength': 50,
            'stop_loss_pct': 1.5,
            'take_profit_pct': 3.0,
            'trailing_stop_pct': 1.0,
            'atr_multiplier': 2.0
        }
        
        # Silver parameters (more volatile)
        silver_params = {
            'fast_ema': 8,
            'slow_ema': 18,
            'trend_ema': 50,
            'rsi_period': 14,
            'rsi_overbought': 75,
            'rsi_oversold': 25,
            'macd_fast': 10,
            'macd_slow': 22,
            'macd_signal': 8,
            'signal_threshold': 0.35,
            'min_signal_strength': 55,
            'stop_loss_pct': 2.5,
            'take_profit_pct': 5.0,
            'trailing_stop_pct': 1.5,
            'atr_multiplier': 2.5
        }
        
        print("\n" + "=" * 70)
        print("FETCHING HISTORICAL DATA")
        print("=" * 70)
        
        # Fetch data
        print("\nFetching Gold (GC=F) data...")
        self.gold_data = self.fetch_data("GC=F", "60d")
        
        print("Fetching Silver (SI=F) data...")
        self.silver_data = self.fetch_data("SI=F", "60d")
        
        # Analyze Gold
        print("\n" + "=" * 70)
        print("ANALYZING GOLD STRATEGY")
        print("=" * 70)
        
        if not self.gold_data.empty:
            self.gold_data = self.calculate_indicators(self.gold_data, gold_params)
            self.gold_data = self.generate_signals(self.gold_data, gold_params)
            
            gold_backtest = self.backtest_strategy(self.gold_data, gold_params)
            gold_market = self.analyze_market_conditions(self.gold_data)
            
            self.results['gold'] = {
                'params': gold_params,
                'backtest': gold_backtest,
                'market': gold_market,
                'data': self.gold_data
            }
            
            print(f"\n  Current Price: ${gold_market['current_price']:.2f}")
            print(f"  Trend: {gold_market['trend']}")
            print(f"  Volatility: {gold_market['volatility']}")
            print(f"  RSI: {gold_market['rsi']:.1f}")
            print(f"  Last Signal: {'BUY' if gold_market['last_signal'] == 1 else 'SELL' if gold_market['last_signal'] == -1 else 'NEUTRAL'}")
            print(f"  Signal Strength: {gold_market['last_signal_strength']:.1f}%")
            
            print(f"\n  Backtest Results (60 days):")
            print(f"  - Total Trades: {gold_backtest['total_trades']}")
            print(f"  - Win Rate: {gold_backtest['win_rate']:.1f}%")
            print(f"  - Total P&L: ${gold_backtest['total_pnl']:.2f} ({gold_backtest['total_pnl_pct']:.2f}%)")
            print(f"  - Profit Factor: {gold_backtest['profit_factor']:.2f}")
            print(f"  - Max Drawdown: {gold_backtest['max_drawdown']:.2f}%")
        
        # Analyze Silver
        print("\n" + "=" * 70)
        print("ANALYZING SILVER STRATEGY")
        print("=" * 70)
        
        if not self.silver_data.empty:
            self.silver_data = self.calculate_indicators(self.silver_data, silver_params)
            self.silver_data = self.generate_signals(self.silver_data, silver_params)
            
            silver_backtest = self.backtest_strategy(self.silver_data, silver_params)
            silver_market = self.analyze_market_conditions(self.silver_data)
            
            self.results['silver'] = {
                'params': silver_params,
                'backtest': silver_backtest,
                'market': silver_market,
                'data': self.silver_data
            }
            
            print(f"\n  Current Price: ${silver_market['current_price']:.2f}")
            print(f"  Trend: {silver_market['trend']}")
            print(f"  Volatility: {silver_market['volatility']}")
            print(f"  RSI: {silver_market['rsi']:.1f}")
            print(f"  Last Signal: {'BUY' if silver_market['last_signal'] == 1 else 'SELL' if silver_market['last_signal'] == -1 else 'NEUTRAL'}")
            print(f"  Signal Strength: {silver_market['last_signal_strength']:.1f}%")
            
            print(f"\n  Backtest Results (60 days):")
            print(f"  - Total Trades: {silver_backtest['total_trades']}")
            print(f"  - Win Rate: {silver_backtest['win_rate']:.1f}%")
            print(f"  - Total P&L: ${silver_backtest['total_pnl']:.2f} ({silver_backtest['total_pnl_pct']:.2f}%)")
            print(f"  - Profit Factor: {silver_backtest['profit_factor']:.2f}")
            print(f"  - Max Drawdown: {silver_backtest['max_drawdown']:.2f}%")
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate comprehensive markdown report"""
        report = []
        
        report.append("# Metals Trading Strategy Analysis Report")
        report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\n**Analysis Period:** Last 60 days (Hourly data)")
        report.append("\n---\n")
        
        # Executive Summary
        report.append("## Executive Summary\n")
        
        if 'gold' in self.results and 'silver' in self.results:
            gold = self.results['gold']
            silver = self.results['silver']
            
            report.append("### Overall Performance\n")
            report.append("| Metric | Gold | Silver |")
            report.append("|--------|------|--------|")
            report.append(f"| Current Price | ${gold['market']['current_price']:.2f} | ${silver['market']['current_price']:.2f} |")
            report.append(f"| Trend | {gold['market']['trend']} | {silver['market']['trend']} |")
            report.append(f"| Volatility | {gold['market']['volatility']} | {silver['market']['volatility']} |")
            report.append(f"| Total Trades | {gold['backtest']['total_trades']} | {silver['backtest']['total_trades']} |")
            report.append(f"| Win Rate | {gold['backtest']['win_rate']:.1f}% | {silver['backtest']['win_rate']:.1f}% |")
            report.append(f"| Total P&L | ${gold['backtest']['total_pnl']:.2f} | ${silver['backtest']['total_pnl']:.2f} |")
            report.append(f"| Return % | {gold['backtest']['total_pnl_pct']:.2f}% | {silver['backtest']['total_pnl_pct']:.2f}% |")
            report.append(f"| Profit Factor | {gold['backtest']['profit_factor']:.2f} | {silver['backtest']['profit_factor']:.2f} |")
            report.append(f"| Max Drawdown | {gold['backtest']['max_drawdown']:.2f}% | {silver['backtest']['max_drawdown']:.2f}% |")
            report.append(f"| Sharpe Ratio | {gold['backtest']['sharpe_ratio']:.2f} | {silver['backtest']['sharpe_ratio']:.2f} |")
        
        report.append("\n---\n")
        
        # Gold Section
        if 'gold' in self.results:
            gold = self.results['gold']
            report.append("## Gold (GC=F) Strategy Analysis\n")
            
            report.append("### Current Market Conditions\n")
            report.append(f"- **Price:** ${gold['market']['current_price']:.2f}")
            report.append(f"- **Trend:** {gold['market']['trend']}")
            report.append(f"- **Volatility Regime:** {gold['market']['volatility']}")
            report.append(f"- **24h Change:** {gold['market']['price_change_24h']*100:.2f}%")
            report.append(f"- **ATR:** ${gold['market']['atr']:.2f} ({gold['market']['atr_pct']:.2f}%)")
            report.append(f"- **Recent High:** ${gold['market']['recent_high']:.2f}")
            report.append(f"- **Recent Low:** ${gold['market']['recent_low']:.2f}")
            
            report.append("\n### Technical Indicators\n")
            report.append(f"- **EMA Fast (9):** ${gold['market']['ema_fast']:.2f}")
            report.append(f"- **EMA Slow (21):** ${gold['market']['ema_slow']:.2f}")
            report.append(f"- **RSI (14):** {gold['market']['rsi']:.1f}")
            report.append(f"- **MACD:** {gold['market']['macd']:.2f}")
            report.append(f"- **MACD Signal:** {gold['market']['macd_signal']:.2f}")
            report.append(f"- **Bollinger Position:** {gold['market']['bb_position']:.2f}")
            report.append(f"- **Momentum (10-bar):** {gold['market']['momentum']:.2f}%")
            report.append(f"- **Volume Ratio:** {gold['market']['volume_ratio']:.2f}x")
            
            report.append("\n### Current Signal\n")
            signal_text = 'BUY' if gold['market']['last_signal'] == 1 else 'SELL' if gold['market']['last_signal'] == -1 else 'NEUTRAL'
            report.append(f"- **Signal:** {signal_text}")
            report.append(f"- **Strength:** {gold['market']['last_signal_strength']:.1f}%")
            report.append(f"- **Components:** {gold['market']['last_signal_components'] or 'None'}")
            
            report.append("\n### Strategy Parameters\n")
            report.append("```")
            report.append(f"Fast EMA: {gold['params']['fast_ema']}")
            report.append(f"Slow EMA: {gold['params']['slow_ema']}")
            report.append(f"RSI Period: {gold['params']['rsi_period']}")
            report.append(f"RSI Overbought: {gold['params']['rsi_overbought']}")
            report.append(f"RSI Oversold: {gold['params']['rsi_oversold']}")
            report.append(f"Stop Loss: {gold['params']['stop_loss_pct']}%")
            report.append(f"Take Profit: {gold['params']['take_profit_pct']}%")
            report.append(f"Trailing Stop: {gold['params']['trailing_stop_pct']}%")
            report.append(f"ATR Multiplier: {gold['params']['atr_multiplier']}")
            report.append("```")
            
            report.append("\n### Backtest Results (60 days)\n")
            bt = gold['backtest']
            report.append(f"- **Total Trades:** {bt['total_trades']}")
            report.append(f"- **Winning Trades:** {bt['winning_trades']}")
            report.append(f"- **Losing Trades:** {bt['losing_trades']}")
            report.append(f"- **Win Rate:** {bt['win_rate']:.1f}%")
            report.append(f"- **Total P&L:** ${bt['total_pnl']:.2f} ({bt['total_pnl_pct']:.2f}%)")
            report.append(f"- **Average Win:** ${bt['avg_win']:.2f}")
            report.append(f"- **Average Loss:** ${bt['avg_loss']:.2f}")
            report.append(f"- **Profit Factor:** {bt['profit_factor']:.2f}")
            report.append(f"- **Max Drawdown:** {bt['max_drawdown']:.2f}%")
            report.append(f"- **Sharpe Ratio:** {bt['sharpe_ratio']:.2f}")
            
            report.append("\n#### Exit Reasons\n")
            for reason, count in bt['exit_reasons'].items():
                if count > 0:
                    report.append(f"- {reason}: {count} ({count/bt['total_trades']*100:.1f}%)" if bt['total_trades'] > 0 else f"- {reason}: {count}")
            
            # Recent trades
            if bt['trades']:
                report.append("\n#### Recent Trades (Last 10)\n")
                report.append("| Entry Time | Exit Time | Action | Entry | Exit | P&L | Exit Reason |")
                report.append("|------------|-----------|--------|-------|------|-----|-------------|")
                for trade in bt['trades'][-10:]:
                    entry_str = trade['entry_time'].strftime('%m/%d %H:%M') if hasattr(trade['entry_time'], 'strftime') else str(trade['entry_time'])[:16]
                    exit_str = trade['exit_time'].strftime('%m/%d %H:%M') if hasattr(trade['exit_time'], 'strftime') else str(trade['exit_time'])[:16]
                    report.append(f"| {entry_str} | {exit_str} | {trade['action']} | ${trade['entry_price']:.2f} | ${trade['exit_price']:.2f} | ${trade['pnl']:.2f} ({trade['pnl_pct']:.1f}%) | {trade['exit_reason']} |")
        
        report.append("\n---\n")
        
        # Silver Section
        if 'silver' in self.results:
            silver = self.results['silver']
            report.append("## Silver (SI=F) Strategy Analysis\n")
            
            report.append("### Current Market Conditions\n")
            report.append(f"- **Price:** ${silver['market']['current_price']:.2f}")
            report.append(f"- **Trend:** {silver['market']['trend']}")
            report.append(f"- **Volatility Regime:** {silver['market']['volatility']}")
            report.append(f"- **24h Change:** {silver['market']['price_change_24h']*100:.2f}%")
            report.append(f"- **ATR:** ${silver['market']['atr']:.2f} ({silver['market']['atr_pct']:.2f}%)")
            report.append(f"- **Recent High:** ${silver['market']['recent_high']:.2f}")
            report.append(f"- **Recent Low:** ${silver['market']['recent_low']:.2f}")
            
            report.append("\n### Technical Indicators\n")
            report.append(f"- **EMA Fast (8):** ${silver['market']['ema_fast']:.2f}")
            report.append(f"- **EMA Slow (18):** ${silver['market']['ema_slow']:.2f}")
            report.append(f"- **RSI (14):** {silver['market']['rsi']:.1f}")
            report.append(f"- **MACD:** {silver['market']['macd']:.2f}")
            report.append(f"- **MACD Signal:** {silver['market']['macd_signal']:.2f}")
            report.append(f"- **Bollinger Position:** {silver['market']['bb_position']:.2f}")
            report.append(f"- **Momentum (10-bar):** {silver['market']['momentum']:.2f}%")
            report.append(f"- **Volume Ratio:** {silver['market']['volume_ratio']:.2f}x")
            
            report.append("\n### Current Signal\n")
            signal_text = 'BUY' if silver['market']['last_signal'] == 1 else 'SELL' if silver['market']['last_signal'] == -1 else 'NEUTRAL'
            report.append(f"- **Signal:** {signal_text}")
            report.append(f"- **Strength:** {silver['market']['last_signal_strength']:.1f}%")
            report.append(f"- **Components:** {silver['market']['last_signal_components'] or 'None'}")
            
            report.append("\n### Strategy Parameters\n")
            report.append("```")
            report.append(f"Fast EMA: {silver['params']['fast_ema']}")
            report.append(f"Slow EMA: {silver['params']['slow_ema']}")
            report.append(f"RSI Period: {silver['params']['rsi_period']}")
            report.append(f"RSI Overbought: {silver['params']['rsi_overbought']}")
            report.append(f"RSI Oversold: {silver['params']['rsi_oversold']}")
            report.append(f"Stop Loss: {silver['params']['stop_loss_pct']}%")
            report.append(f"Take Profit: {silver['params']['take_profit_pct']}%")
            report.append(f"Trailing Stop: {silver['params']['trailing_stop_pct']}%")
            report.append(f"ATR Multiplier: {silver['params']['atr_multiplier']}")
            report.append("```")
            
            report.append("\n### Backtest Results (60 days)\n")
            bt = silver['backtest']
            report.append(f"- **Total Trades:** {bt['total_trades']}")
            report.append(f"- **Winning Trades:** {bt['winning_trades']}")
            report.append(f"- **Losing Trades:** {bt['losing_trades']}")
            report.append(f"- **Win Rate:** {bt['win_rate']:.1f}%")
            report.append(f"- **Total P&L:** ${bt['total_pnl']:.2f} ({bt['total_pnl_pct']:.2f}%)")
            report.append(f"- **Average Win:** ${bt['avg_win']:.2f}")
            report.append(f"- **Average Loss:** ${bt['avg_loss']:.2f}")
            report.append(f"- **Profit Factor:** {bt['profit_factor']:.2f}")
            report.append(f"- **Max Drawdown:** {bt['max_drawdown']:.2f}%")
            report.append(f"- **Sharpe Ratio:** {bt['sharpe_ratio']:.2f}")
            
            report.append("\n#### Exit Reasons\n")
            for reason, count in bt['exit_reasons'].items():
                if count > 0:
                    report.append(f"- {reason}: {count} ({count/bt['total_trades']*100:.1f}%)" if bt['total_trades'] > 0 else f"- {reason}: {count}")
            
            # Recent trades
            if bt['trades']:
                report.append("\n#### Recent Trades (Last 10)\n")
                report.append("| Entry Time | Exit Time | Action | Entry | Exit | P&L | Exit Reason |")
                report.append("|------------|-----------|--------|-------|------|-----|-------------|")
                for trade in bt['trades'][-10:]:
                    entry_str = trade['entry_time'].strftime('%m/%d %H:%M') if hasattr(trade['entry_time'], 'strftime') else str(trade['entry_time'])[:16]
                    exit_str = trade['exit_time'].strftime('%m/%d %H:%M') if hasattr(trade['exit_time'], 'strftime') else str(trade['exit_time'])[:16]
                    report.append(f"| {entry_str} | {exit_str} | {trade['action']} | ${trade['entry_price']:.2f} | ${trade['exit_price']:.2f} | ${trade['pnl']:.2f} ({trade['pnl_pct']:.1f}%) | {trade['exit_reason']} |")
        
        report.append("\n---\n")
        
        # Recommendations
        report.append("## Trading Recommendations\n")
        
        if 'gold' in self.results:
            gold = self.results['gold']
            report.append("### Gold\n")
            
            if gold['market']['trend'] == 'BULLISH':
                report.append("- **Bias:** BULLISH - Look for buying opportunities on pullbacks")
            elif gold['market']['trend'] == 'BEARISH':
                report.append("- **Bias:** BEARISH - Look for selling opportunities on rallies")
            else:
                report.append("- **Bias:** NEUTRAL - Wait for clear direction")
            
            if gold['market']['volatility'] == 'HIGH':
                report.append("- **Risk:** Use wider stops (2-2.5%) due to high volatility")
            elif gold['market']['volatility'] == 'LOW':
                report.append("- **Risk:** Can use tighter stops (1-1.5%) in low volatility")
            
            if gold['market']['rsi'] < 30:
                report.append("- **RSI Alert:** Oversold - Potential bounce expected")
            elif gold['market']['rsi'] > 70:
                report.append("- **RSI Alert:** Overbought - Potential pullback expected")
            
            if gold['backtest']['win_rate'] >= 50 and gold['backtest']['profit_factor'] >= 1.5:
                report.append("- **Strategy Status:** PERFORMING WELL - Continue with current parameters")
            else:
                report.append("- **Strategy Status:** NEEDS ADJUSTMENT - Consider tightening stops or filtering trades")
        
        if 'silver' in self.results:
            silver = self.results['silver']
            report.append("\n### Silver\n")
            
            if silver['market']['trend'] == 'BULLISH':
                report.append("- **Bias:** BULLISH - Silver tends to outperform gold in bull markets")
            elif silver['market']['trend'] == 'BEARISH':
                report.append("- **Bias:** BEARISH - Silver tends to underperform in bear markets")
            else:
                report.append("- **Bias:** NEUTRAL - Wait for clear direction")
            
            if silver['market']['volatility'] == 'HIGH':
                report.append("- **Risk:** Use wider stops (3-3.5%) - Silver is more volatile")
            elif silver['market']['volatility'] == 'LOW':
                report.append("- **Risk:** Can use tighter stops (2-2.5%) in low volatility")
            
            if silver['market']['rsi'] < 25:
                report.append("- **RSI Alert:** Oversold - Potential strong bounce expected")
            elif silver['market']['rsi'] > 75:
                report.append("- **RSI Alert:** Overbought - Potential pullback expected")
            
            if silver['backtest']['win_rate'] >= 50 and silver['backtest']['profit_factor'] >= 1.5:
                report.append("- **Strategy Status:** PERFORMING WELL - Continue with current parameters")
            else:
                report.append("- **Strategy Status:** NEEDS ADJUSTMENT - Consider wider stops for volatile moves")
        
        report.append("\n---\n")
        
        # Risk Management Guidelines
        report.append("## Risk Management Guidelines\n")
        report.append("""
### Position Sizing
- Never risk more than 2% of capital per trade
- For volatile conditions, reduce to 1% risk per trade
- Use lot sizes appropriate for your capital (1 lot Gold Mini = ~Rs 60,000 margin)

### Stop Loss Rules
1. **Initial Stop:** Use ATR-based or percentage-based, whichever is tighter
2. **Trailing Stop:** Move stop to breakeven after 1% profit
3. **Maximum Loss:** Exit if daily loss exceeds 5%

### Best Trading Hours (IST)
- **Gold:** 3:30 PM - 11:30 PM (overlaps with US markets)
- **Silver:** 3:30 PM - 11:30 PM (higher volatility during this window)

### Market Conditions to Avoid
- Major economic data releases (Fed meetings, NFP, etc.)
- First and last 30 minutes of trading session
- When ATR is more than 2x the average (extreme volatility)
""")
        
        report.append("\n---\n")
        report.append(f"\n*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return '\n'.join(report)


def main():
    analyzer = MetalsAnalyzer()
    
    # Run analysis
    results = analyzer.run_analysis()
    
    # Generate report
    print("\n" + "=" * 70)
    print("GENERATING REPORT")
    print("=" * 70)
    
    report = analyzer.generate_report()
    
    # Save report
    report_path = Path(__file__).parent / "METALS_STRATEGY_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_path}")
    
    return analyzer


if __name__ == "__main__":
    analyzer = main()
