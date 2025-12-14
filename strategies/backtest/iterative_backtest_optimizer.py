#!/usr/bin/env python
"""
Iterative Backtest Optimizer
Runs backtests, analyzes results, optimizes strategies, and reruns until profitable
Works with simulated data for paper trading mode
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import traceback

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Try to import framework components
try:
    from option_backtest_framework import (
        BacktestConfig, OptionBacktestEngine, AnalyticsCalculator, Trade
    )
    from strategy_backtests import STRATEGY_BACKTESTS
    FRAMEWORK_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not import full framework: {e}")
    print("Will use simplified standalone implementation")
    FRAMEWORK_AVAILABLE = False

# ==================== SIMPLIFIED IMPLEMENTATION ====================

if not FRAMEWORK_AVAILABLE:
    # Simplified dataclasses and classes
    from dataclasses import dataclass
    
    @dataclass
    class BacktestConfig:
        underlying: str = "NIFTY"
        exchange: str = "NSE_INDEX"
        strike_int: int = 50
        lot_size: int = 25
        timeframes: List[str] = None
        periods: Dict[str, int] = None
        profit_target_pct: float = 50.0
        stop_loss_pct: float = 200.0
        time_based_exit_days: int = 1
        max_holding_days: int = 30
        default_volatility: float = 15.0
        interest_rate: float = 6.5
        quantity: int = 75
        product: str = "MIS"
        slippage_pct: float = 0.1
        use_analyze_mode: bool = True
        
        def __post_init__(self):
            if self.timeframes is None:
                self.timeframes = ["1d"]
            if self.periods is None:
                self.periods = {"yesterday": 1, "1week": 5, "1month": 20}
    
    @dataclass
    class Trade:
        entry_time: datetime
        exit_time: Optional[datetime]
        strategy: str
        underlying: str
        symbol: str
        option_type: str
        strike: float
        action: str
        quantity: int
        entry_price: float
        exit_price: Optional[float]
        pnl: float
        exit_reason: str
        holding_days: float
    
    class OptionPricer:
        def __init__(self, interest_rate=6.5, default_vol=15.0):
            self.interest_rate = interest_rate / 100.0
            self.default_vol = default_vol / 100.0
        
        def calculate_option_price(self, spot, strike, time_to_expiry, volatility, option_type):
            if time_to_expiry <= 0:
                return max(0, spot - strike) if option_type.upper() == "CE" else max(0, strike - spot)
            time_years = time_to_expiry / 365.0
            vol = volatility / 100.0 if volatility > 1 else volatility
            intrinsic = max(0, spot - strike) if option_type.upper() == "CE" else max(0, strike - spot)
            time_value = spot * vol * np.sqrt(time_years) * 0.4 * (1 if intrinsic > 0 else np.exp(-abs(spot - strike) / spot * 2))
            return intrinsic + time_value
    
    class OptionBacktestEngine:
        def __init__(self, config, api_key=None):
            self.config = config
            self.pricer = OptionPricer(config.interest_rate, config.default_volatility)
        
        def get_expiry_date(self, base_date):
            days_until_thursday = (3 - base_date.weekday()) % 7
            if days_until_thursday == 0 and base_date.hour >= 15:
                days_until_thursday = 7
            expiry = base_date + timedelta(days=days_until_thursday)
            return expiry.replace(hour=15, minute=30, second=0, microsecond=0)
        
        def calculate_atm_strike(self, spot):
            return round(spot / self.config.strike_int) * self.config.strike_int
        
        def get_strike_from_offset(self, spot, offset, option_type):
            atm = self.calculate_atm_strike(spot)
            if offset.upper() == "ATM":
                return atm
            if offset.upper().startswith("ITM"):
                level = int(offset[3:]) if len(offset) > 3 else 1
                return atm - (level * self.config.strike_int) if option_type.upper() == "CE" else atm + (level * self.config.strike_int)
            elif offset.upper().startswith("OTM"):
                level = int(offset[3:]) if len(offset) > 3 else 1
                return atm + (level * self.config.strike_int) if option_type.upper() == "CE" else atm - (level * self.config.strike_int)
            return atm
        
        def simulate_option_price(self, spot, strike, expiry_date, current_date, option_type, volatility=None):
            time_to_expiry = (expiry_date - current_date).total_seconds() / 86400.0
            if time_to_expiry <= 0:
                return max(0, spot - strike) if option_type.upper() == "CE" else max(0, strike - spot)
            return self.pricer.calculate_option_price(spot, strike, time_to_expiry, volatility or self.config.default_volatility, option_type)
        
        def apply_slippage(self, price, action):
            slippage = self.config.slippage_pct / 100.0
            return price * (1 + slippage) if action.upper() == "BUY" else price * (1 - slippage)
        
        def get_historical_data(self, symbol, exchange, interval, start_date, end_date):
            # Generate simulated data
            return generate_simulated_data(symbol, start_date, end_date, interval)
    
    def generate_simulated_data(symbol, start_date, end_date, interval):
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        dates = pd.bdate_range(start=start, end=end) if interval == "1d" else pd.date_range(start=start, end=end, freq='1D')
        n = len(dates) if len(dates) > 0 else 1
        if n == 0:
            dates = pd.date_range(start=start, end=start, freq='1D')
            n = 1
        
        base_price = 24000.0 if "NIFTY" in symbol.upper() else 50000.0
        np.random.seed(42)
        returns = np.random.normal(0.0003, 0.012, n)
        prices = base_price * np.exp(np.cumsum(returns))
        
        opens = prices * (1 + np.random.normal(0, 0.003, n))
        highs = np.maximum(opens, prices) * (1 + np.abs(np.random.normal(0, 0.005, n)))
        lows = np.minimum(opens, prices) * (1 - np.abs(np.random.normal(0, 0.005, n)))
        closes = prices
        volumes = np.random.lognormal(14, 0.6, n).astype(int)
        
        for i in range(n):
            highs[i] = max(opens[i], highs[i], closes[i], lows[i])
            lows[i] = min(opens[i], highs[i], closes[i], lows[i])
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': opens, 'high': highs, 'low': lows, 'close': closes, 'volume': volumes
        })
    
    # Import simplified strategy backtests
    STRATEGY_BACKTESTS = {}
    # We'll add these from the existing file

# ==================== ITERATIVE OPTIMIZER ====================

class IterativeBacktestOptimizer:
    """Iteratively runs backtests and optimizes strategies"""
    
    def __init__(self, config: BacktestConfig, max_iterations: int = 5):
        self.config = config
        self.max_iterations = max_iterations
        self.engine = OptionBacktestEngine(config)
        self.all_results = []
        self.iteration_history = []
        self.optimization_log = []
    
    def get_date_range(self, period_name: str, period_days: int) -> tuple:
        """Get start and end dates"""
        end_date = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
        while end_date.weekday() >= 5:
            end_date -= timedelta(days=1)
        
        if period_name == "yesterday":
            start_date = end_date - timedelta(days=1)
            while start_date.weekday() >= 5:
                start_date -= timedelta(days=1)
            return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
        
        start_date = end_date - timedelta(days=period_days)
        while start_date.weekday() >= 5:
            start_date -= timedelta(days=1)
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def run_single_backtest(self, strategy_name: str, timeframe: str, period_name: str) -> Optional:
        """Run a single backtest"""
        start_date, end_date = self.get_date_range(period_name, self.config.periods[period_name])
        
        df = self.engine.get_historical_data(
            self.config.underlying, self.config.exchange, timeframe, start_date, end_date
        )
        
        if df is None or df.empty:
            return None
        
        # Ensure timestamp column
        if 'timestamp' not in df.columns and len(df) > 0:
            df['timestamp'] = pd.to_datetime(df.index) if hasattr(df.index, 'to_datetime') else pd.date_range(start=start_date, periods=len(df))
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        backtest_func = STRATEGY_BACKTESTS.get(strategy_name)
        if not backtest_func:
            return None
        
        try:
            # Run with strategy-specific params
            if strategy_name == "Strangle":
                trades = backtest_func(self.engine, df, self.config, otm_level=2)
            elif strategy_name == "Iron Condor":
                trades = backtest_func(self.engine, df, self.config, sell_otm=5, buy_otm=10)
            elif strategy_name == "Iron Butterfly":
                trades = backtest_func(self.engine, df, self.config, wing_otm=5)
            elif strategy_name == "Bull Call Spread":
                trades = backtest_func(self.engine, df, self.config, buy_offset="ITM2", sell_otm=5)
            elif strategy_name == "Bear Put Spread":
                trades = backtest_func(self.engine, df, self.config, buy_offset="ITM2", sell_otm=5)
            elif strategy_name == "Protective Put":
                trades = backtest_func(self.engine, df, self.config, put_offset="OTM2")
            elif strategy_name == "Covered Call":
                trades = backtest_func(self.engine, df, self.config, call_otm=2)
            elif strategy_name == "Calendar Spread":
                trades = backtest_func(self.engine, df, self.config, strike_offset="ATM", option_type="CE")
            else:
                trades = backtest_func(self.engine, df, self.config)
            
            if FRAMEWORK_AVAILABLE:
                result = AnalyticsCalculator.calculate_results(
                    trades, strategy_name, timeframe, period_name, start_date, end_date
                )
            else:
                result = self._calculate_simple_results(trades, strategy_name, timeframe, period_name, start_date, end_date)
            
            return result
        except Exception as e:
            print(f"Error in {strategy_name}: {e}")
            traceback.print_exc()
            return None
    
    def _calculate_simple_results(self, trades, strategy_name, timeframe, period, start_date, end_date):
        """Simple results calculation"""
        if not trades:
            return type('obj', (object,), {
                'strategy_name': strategy_name, 'timeframe': timeframe, 'period': period,
                'start_date': start_date, 'end_date': end_date,
                'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0, 'win_rate': 0.0,
                'total_pnl': 0.0, 'net_pnl': 0.0, 'average_pnl_per_trade': 0.0,
                'average_win': 0.0, 'average_loss': 0.0, 'largest_win': 0.0, 'largest_loss': 0.0,
                'max_drawdown': 0.0, 'max_drawdown_pct': 0.0, 'sharpe_ratio': None,
                'average_holding_days': 0.0, 'total_trading_days': 0,
                'exit_reasons': {}, 'trades': []
            })()
        
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        pnls = [t.pnl for t in trades]
        total_pnl = sum(pnls)
        net_pnl = total_pnl
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0
        
        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [t.pnl for t in trades if t.pnl < 0]
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        largest_win = max(wins) if wins else 0.0
        largest_loss = min(losses) if losses else 0.0
        
        cumulative_pnl = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = cumulative_pnl - running_max
        max_drawdown = abs(min(drawdown)) if len(drawdown) > 0 else 0.0
        
        sharpe = None
        if len(pnls) > 1:
            returns = np.array(pnls)
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            if std_return > 0:
                sharpe = (mean_return / std_return) * np.sqrt(252)
        
        holding_days = [t.holding_days for t in trades if t.exit_time]
        avg_holding = sum(holding_days) / len(holding_days) if holding_days else 0.0
        
        exit_reasons = {}
        for t in trades:
            exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1
        
        return type('obj', (object,), {
            'strategy_name': strategy_name, 'timeframe': timeframe, 'period': period,
            'start_date': start_date, 'end_date': end_date,
            'total_trades': total_trades, 'winning_trades': winning_trades,
            'losing_trades': losing_trades, 'win_rate': win_rate,
            'total_pnl': total_pnl, 'net_pnl': net_pnl, 'average_pnl_per_trade': avg_pnl,
            'average_win': avg_win, 'average_loss': avg_loss,
            'largest_win': largest_win, 'largest_loss': largest_loss,
            'max_drawdown': max_drawdown, 'max_drawdown_pct': 0.0, 'sharpe_ratio': sharpe,
            'average_holding_days': avg_holding, 'total_trading_days': len(trades),
            'exit_reasons': exit_reasons, 'trades': []
        })()
    
    def analyze_performance(self, results: List) -> Dict:
        """Analyze overall performance"""
        if not results:
            return {'profitable_ratio': 0, 'avg_pnl': 0, 'issues': []}
        
        profitable = [r for r in results if (r.net_pnl if hasattr(r, 'net_pnl') else getattr(r, 'net_pnl', 0)) > 0]
        profitable_ratio = len(profitable) / len(results)
        avg_pnl = sum([r.net_pnl if hasattr(r, 'net_pnl') else getattr(r, 'net_pnl', 0) for r in results]) / len(results)
        
        issues = []
        if profitable_ratio < 0.5:
            issues.append(f"Only {profitable_ratio*100:.1f}% profitable (target: 50%+)")
        if avg_pnl < 0:
            issues.append(f"Average PnL is negative: ₹{avg_pnl:.2f}")
        
        return {
            'profitable_ratio': profitable_ratio,
            'avg_pnl': avg_pnl,
            'profitable_count': len(profitable),
            'total_count': len(results),
            'issues': issues
        }
    
    def optimize_parameters(self, results: List) -> Dict:
        """Optimize parameters based on results"""
        optimizations = {}
        
        # Analyze exit reasons
        all_exit_reasons = {}
        for r in results:
            reasons = r.exit_reasons if hasattr(r, 'exit_reasons') else getattr(r, 'exit_reasons', {})
            for reason, count in reasons.items():
                all_exit_reasons[reason] = all_exit_reasons.get(reason, 0) + count
        
        total_exits = sum(all_exit_reasons.values())
        if total_exits > 0:
            # If too many stop losses, increase stop loss threshold
            if all_exit_reasons.get('STOP_LOSS', 0) / total_exits > 0.4:
                optimizations['stop_loss_pct'] = min(300, self.config.stop_loss_pct * 1.2)
            
            # If profit targets not being hit, reduce target
            if all_exit_reasons.get('PROFIT_TARGET', 0) / total_exits < 0.2:
                optimizations['profit_target_pct'] = max(30, self.config.profit_target_pct * 0.9)
            
            # If too many time-based exits, adjust
            if all_exit_reasons.get('TIME_BASED', 0) / total_exits > 0.5:
                optimizations['time_based_exit_days'] = max(0, self.config.time_based_exit_days - 1)
        
        return optimizations
    
    def run_iterative_optimization(self) -> List:
        """Run iterative optimization"""
        print("\n" + "="*70)
        print("ITERATIVE BACKTEST OPTIMIZATION")
        print("="*70)
        print(f"Underlying: {self.config.underlying}")
        print(f"Strategies: {len(STRATEGY_BACKTESTS)}")
        print(f"Max Iterations: {self.max_iterations}")
        print("="*70)
        
        strategies = list(STRATEGY_BACKTESTS.keys())
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n{'='*70}")
            print(f"ITERATION {iteration}/{self.max_iterations}")
            print(f"{'='*70}")
            
            iteration_results = []
            
            for strategy_name in strategies:
                for timeframe in self.config.timeframes:
                    for period_name in self.config.periods.keys():
                        result = self.run_single_backtest(strategy_name, timeframe, period_name)
                        if result:
                            iteration_results.append(result)
                            status = "✅" if (result.net_pnl if hasattr(result, 'net_pnl') else getattr(result, 'net_pnl', 0)) > 0 else "❌"
                            pnl = result.net_pnl if hasattr(result, 'net_pnl') else getattr(result, 'net_pnl', 0)
                            wr = result.win_rate if hasattr(result, 'win_rate') else getattr(result, 'win_rate', 0)
                            trades = result.total_trades if hasattr(result, 'total_trades') else getattr(result, 'total_trades', 0)
                            print(f"{status} {strategy_name:20} | {period_name:10} | "
                                  f"PnL: ₹{pnl:>10.2f} | Win Rate: {wr:>5.1f}% | Trades: {trades}")
            
            self.all_results.extend(iteration_results)
            
            # Analyze
            analysis = self.analyze_performance(iteration_results)
            print(f"\nIteration {iteration} Analysis:")
            print(f"  Profitable: {analysis['profitable_count']}/{analysis['total_count']} ({analysis['profitable_ratio']*100:.1f}%)")
            print(f"  Average PnL: ₹{analysis['avg_pnl']:.2f}")
            
            if analysis['issues']:
                print(f"  Issues: {', '.join(analysis['issues'])}")
            
            # Check if we should stop
            if analysis['profitable_ratio'] >= 0.7 and analysis['avg_pnl'] > 0:
                print(f"\n✅ SUCCESS: {analysis['profitable_ratio']*100:.1f}% profitable with positive average PnL")
                break
            
            # Optimize for next iteration
            if iteration < self.max_iterations:
                optimizations = self.optimize_parameters(iteration_results)
                if optimizations:
                    print(f"\nOptimizing parameters:")
                    for key, value in optimizations.items():
                        old_value = getattr(self.config, key)
                        setattr(self.config, key, value)
                        print(f"  {key}: {old_value} → {value}")
                        self.optimization_log.append({
                            'iteration': iteration,
                            'parameter': key,
                            'old_value': old_value,
                            'new_value': value
                        })
            
            self.iteration_history.append({
                'iteration': iteration,
                'results_count': len(iteration_results),
                'analysis': analysis
            })
        
        return self.all_results
    
    def generate_reports(self, output_dir: str = "backtest_results"):
        """Generate comprehensive reports"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Summary report
        summary_file = output_path / f"optimization_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("ITERATIVE BACKTEST OPTIMIZATION SUMMARY\n")
            f.write("="*70 + "\n\n")
            f.write(f"Total Iterations: {len(self.iteration_history)}\n")
            f.write(f"Total Backtests: {len(self.all_results)}\n\n")
            
            for iter_data in self.iteration_history:
                f.write(f"Iteration {iter_data['iteration']}:\n")
                f.write(f"  Profitable: {iter_data['analysis']['profitable_count']}/{iter_data['analysis']['total_count']}\n")
                f.write(f"  Avg PnL: ₹{iter_data['analysis']['avg_pnl']:.2f}\n\n")
            
            # Final analysis
            final_analysis = self.analyze_performance(self.all_results)
            f.write("FINAL RESULTS:\n")
            f.write(f"  Profitable Ratio: {final_analysis['profitable_ratio']*100:.1f}%\n")
            f.write(f"  Average PnL: ₹{final_analysis['avg_pnl']:.2f}\n")
        
        print(f"\n✓ Report saved: {summary_file}")

# ==================== MAIN ====================

def main():
    # Import strategy backtests
    if not FRAMEWORK_AVAILABLE:
        # Try to import from existing file
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "strategy_backtests",
                Path(__file__).parent / "strategy_backtests.py"
            )
            strategy_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(strategy_module)
            global STRATEGY_BACKTESTS
            STRATEGY_BACKTESTS = strategy_module.STRATEGY_BACKTESTS
            # Also import Trade and other needed classes
            global Trade, BacktestConfig, OptionBacktestEngine
            Trade = strategy_module.Trade if hasattr(strategy_module, 'Trade') else Trade
        except Exception as e:
            print(f"Warning: Could not load strategy backtests: {e}")
            print("Please ensure strategy_backtests.py is available")
            return
    
    config = BacktestConfig(
        underlying=os.getenv('UNDERLYING', 'NIFTY'),
        exchange=os.getenv('EXCHANGE', 'NSE_INDEX'),
        strike_int=int(os.getenv('STRIKE_INT', '50')),
        timeframes=['1d'],
        periods={"yesterday": 1, "1week": 5, "1month": 20},
        profit_target_pct=50.0,
        stop_loss_pct=200.0,
        use_analyze_mode=True
    )
    
    max_iterations = int(os.getenv('MAX_ITERATIONS', '5'))
    
    optimizer = IterativeBacktestOptimizer(config, max_iterations)
    results = optimizer.run_iterative_optimization()
    
    if results:
        optimizer.generate_reports()
        print(f"\n{'='*70}")
        print("OPTIMIZATION COMPLETE")
        print(f"{'='*70}")

if __name__ == "__main__":
    main()
