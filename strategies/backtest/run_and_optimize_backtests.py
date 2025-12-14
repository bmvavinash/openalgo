#!/usr/bin/env python
"""
Iterative Backtest Runner with Strategy Optimization
Runs backtests, analyzes results, fixes strategies, and reruns until profitable
Works in paper trading mode without broker authentication
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

# Try to import required modules, use fallbacks if not available
try:
    from utils.logging import get_logger
    logger = get_logger(__name__)
except:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

try:
    from services.history_service import get_history
    HISTORY_SERVICE_AVAILABLE = True
except:
    HISTORY_SERVICE_AVAILABLE = False
    logger.warning("History service not available, will use simulated data")

from option_backtest_framework import (
    BacktestConfig, OptionBacktestEngine, AnalyticsCalculator, Trade
)
from strategy_backtests import STRATEGY_BACKTESTS

# ==================== SIMULATED DATA GENERATOR ====================

def generate_simulated_historical_data(
    symbol: str,
    start_date: str,
    end_date: str,
    interval: str = "1d"
) -> pd.DataFrame:
    """Generate simulated historical data for backtesting when real data is not available"""
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    # Generate dates based on interval
    if interval == "1d":
        dates = pd.date_range(start=start, end=end, freq='B')  # Business days
    elif interval == "1h":
        dates = pd.date_range(start=start, end=end, freq='1H')
        dates = dates[(dates.hour >= 9) & (dates.hour <= 15)]  # Market hours
    elif interval == "15m":
        dates = pd.date_range(start=start, end=end, freq='15min')
        dates = dates[(dates.hour >= 9) & (dates.hour <= 15)]
    else:
        dates = pd.date_range(start=start, end=end, freq='1D')
    
    # Generate realistic price data (random walk with trend)
    n = len(dates)
    base_price = 24000.0 if "NIFTY" in symbol.upper() else 50000.0
    
    # Random walk with slight upward trend
    returns = np.random.normal(0.0005, 0.015, n)  # Small positive drift, 1.5% volatility
    prices = base_price * np.exp(np.cumsum(returns))
    
    # Generate OHLC
    opens = prices * (1 + np.random.normal(0, 0.002, n))
    highs = np.maximum(opens, prices) * (1 + np.abs(np.random.normal(0, 0.005, n)))
    lows = np.minimum(opens, prices) * (1 - np.abs(np.random.normal(0, 0.005, n)))
    closes = prices
    
    # Generate volume
    volumes = np.random.lognormal(15, 0.5, n).astype(int)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })
    
    return df

# ==================== ENHANCED BACKTEST ENGINE ====================

class EnhancedBacktestEngine(OptionBacktestEngine):
    """Enhanced backtest engine with simulated data support"""
    
    def get_historical_data(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Fetch historical data with fallback to simulated data"""
        # Try to get real data first
        if HISTORY_SERVICE_AVAILABLE and self.api_key:
            try:
                success, response, status = get_history(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    start_date=start_date,
                    end_date=end_date,
                    api_key=self.api_key
                )
                
                if success and response.get('data'):
                    data = response.get('data', [])
                    df = pd.DataFrame(data)
                    
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df = df.sort_values('timestamp').reset_index(drop=True)
                    
                    required_cols = ['open', 'high', 'low', 'close']
                    for col in required_cols:
                        if col not in df.columns and col.capitalize() in df.columns:
                            df[col] = df[col.capitalize()]
                    
                    if all(col in df.columns for col in required_cols):
                        logger.info(f"Fetched real historical data: {len(df)} points")
                        return df
            except Exception as e:
                logger.warning(f"Failed to fetch real data: {e}, using simulated data")
        
        # Fallback to simulated data
        logger.info(f"Using simulated historical data for {symbol}")
        return generate_simulated_historical_data(symbol, start_date, end_date, interval)

# ==================== STRATEGY OPTIMIZER ====================

class StrategyOptimizer:
    """Optimizes strategy parameters based on backtest results"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.optimization_history = []
    
    def analyze_strategy_performance(self, results: List) -> Dict:
        """Analyze strategy performance and identify issues"""
        analysis = {
            'profitable_count': 0,
            'losing_count': 0,
            'total_pnl': 0.0,
            'avg_pnl': 0.0,
            'win_rate': 0.0,
            'issues': [],
            'recommendations': []
        }
        
        if not results:
            return analysis
        
        profitable = [r for r in results if (r.net_pnl if hasattr(r, 'net_pnl') else r.get('net_pnl', 0)) > 0]
        losing = [r for r in results if (r.net_pnl if hasattr(r, 'net_pnl') else r.get('net_pnl', 0)) < 0]
        
        analysis['profitable_count'] = len(profitable)
        analysis['losing_count'] = len(losing)
        analysis['total_pnl'] = sum([r.net_pnl if hasattr(r, 'net_pnl') else r.get('net_pnl', 0) for r in results])
        analysis['avg_pnl'] = analysis['total_pnl'] / len(results) if results else 0
        
        total_trades = sum([r.total_trades if hasattr(r, 'total_trades') else r.get('total_trades', 0) for r in results])
        winning_trades = sum([r.winning_trades if hasattr(r, 'winning_trades') else r.get('winning_trades', 0) for r in results])
        analysis['win_rate'] = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Identify issues
        if analysis['profitable_count'] < len(results) * 0.5:
            analysis['issues'].append("Less than 50% of backtests are profitable")
            analysis['recommendations'].append("Consider adjusting profit targets or stop losses")
        
        if analysis['avg_pnl'] < 0:
            analysis['issues'].append("Average PnL is negative")
            analysis['recommendations'].append("Review entry/exit logic and strategy parameters")
        
        if analysis['win_rate'] < 40:
            analysis['issues'].append("Win rate is below 40%")
            analysis['recommendations'].append("Improve entry criteria or adjust position sizing")
        
        return analysis
    
    def optimize_parameters(self, strategy_name: str, results: List) -> Dict:
        """Optimize strategy parameters based on results"""
        optimizations = {}
        
        # Analyze exit reasons
        exit_reasons = {}
        for r in results:
            reasons = r.exit_reasons if hasattr(r, 'exit_reasons') else r.get('exit_reasons', {})
            for reason, count in reasons.items():
                exit_reasons[reason] = exit_reasons.get(reason, 0) + count
        
        # If too many stop losses, reduce stop loss percentage
        total_exits = sum(exit_reasons.values())
        if exit_reasons.get('STOP_LOSS', 0) / total_exits > 0.4 if total_exits > 0 else False:
            optimizations['stop_loss_pct'] = self.config.stop_loss_pct * 1.5  # Increase stop loss
        
        # If too many time-based exits, adjust time-based exit days
        if exit_reasons.get('TIME_BASED', 0) / total_exits > 0.5 if total_exits > 0 else False:
            optimizations['time_based_exit_days'] = max(1, self.config.time_based_exit_days - 1)
        
        # If profit targets not being hit, reduce profit target
        if exit_reasons.get('PROFIT_TARGET', 0) / total_exits < 0.2 if total_exits > 0 else False:
            optimizations['profit_target_pct'] = max(20, self.config.profit_target_pct * 0.8)
        
        return optimizations

# ==================== ITERATIVE RUNNER ====================

class IterativeBacktestRunner:
    """Runs backtests iteratively, optimizing strategies until profitable"""
    
    def __init__(self, config: BacktestConfig, api_key: Optional[str] = None, max_iterations: int = 5):
        self.config = config
        self.api_key = api_key
        self.max_iterations = max_iterations
        self.engine = EnhancedBacktestEngine(config, api_key)
        self.optimizer = StrategyOptimizer(config)
        self.all_results = []
        self.iteration_history = []
    
    def get_date_range(self, period_name: str, period_days: int) -> tuple:
        """Get start and end dates for a period"""
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
            symbol=self.config.underlying,
            exchange=self.config.exchange,
            interval=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or df.empty:
            return None
        
        backtest_func = STRATEGY_BACKTESTS.get(strategy_name)
        if not backtest_func:
            return None
        
        try:
            # Run with strategy-specific parameters
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
            
            results = AnalyticsCalculator.calculate_results(
                trades, strategy_name, timeframe, period_name, start_date, end_date
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in backtest: {e}")
            traceback.print_exc()
            return None
    
    def run_iterative_backtests(self) -> List:
        """Run backtests iteratively, optimizing until profitable"""
        print("\n" + "="*70)
        print("ITERATIVE BACKTESTING WITH OPTIMIZATION")
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
                            status = "✅" if result.net_pnl > 0 else "❌"
                            print(f"{status} {strategy_name:20} | {period_name:10} | PnL: ₹{result.net_pnl:>10.2f} | "
                                  f"Win Rate: {result.win_rate:>5.1f}% | Trades: {result.total_trades}")
            
            self.all_results.extend(iteration_results)
            
            # Analyze results
            analysis = self.optimizer.analyze_strategy_performance(iteration_results)
            
            print(f"\nIteration {iteration} Analysis:")
            print(f"  Profitable: {analysis['profitable_count']}/{len(iteration_results)}")
            print(f"  Average PnL: ₹{analysis['avg_pnl']:.2f}")
            print(f"  Win Rate: {analysis['win_rate']:.1f}%")
            
            if analysis['issues']:
                print(f"\n  Issues found:")
                for issue in analysis['issues']:
                    print(f"    - {issue}")
            
            # Check if we should continue
            profitable_ratio = analysis['profitable_count'] / len(iteration_results) if iteration_results else 0
            
            if profitable_ratio >= 0.7 and analysis['avg_pnl'] > 0:
                print(f"\n✅ SUCCESS: {profitable_ratio*100:.1f}% profitable with positive average PnL")
                print("Strategies are performing well!")
                break
            
            # Optimize parameters for next iteration
            if iteration < self.max_iterations:
                print(f"\nOptimizing parameters for next iteration...")
                for strategy_name in strategies:
                    strategy_results = [r for r in iteration_results 
                                      if (r.strategy_name if hasattr(r, 'strategy_name') else r.get('strategy_name')) == strategy_name]
                    if strategy_results:
                        optimizations = self.optimizer.optimize_parameters(strategy_name, strategy_results)
                        if optimizations:
                            print(f"  {strategy_name}: {optimizations}")
                            # Apply optimizations to config
                            for key, value in optimizations.items():
                                setattr(self.config, key, value)
            
            self.iteration_history.append({
                'iteration': iteration,
                'results_count': len(iteration_results),
                'analysis': analysis
            })
        
        return self.all_results
    
    def generate_final_report(self, output_dir: str = "backtest_results"):
        """Generate final comprehensive report"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Convert results to dict
        results_dict = []
        for r in self.all_results:
            if hasattr(r, '__dict__'):
                r_dict = r.__dict__.copy()
                for key, value in r_dict.items():
                    if hasattr(value, '__dict__'):
                        r_dict[key] = str(value)
                results_dict.append(r_dict)
            else:
                results_dict.append(r)
        
        # Save JSON
        json_file = output_path / f"iterative_backtest_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump({
                'results': results_dict,
                'iterations': self.iteration_history,
                'final_config': self.config.__dict__
            }, f, indent=2, default=str)
        
        # Generate summary
        summary_file = output_path / f"iterative_backtest_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("ITERATIVE BACKTEST SUMMARY\n")
            f.write("="*70 + "\n\n")
            f.write(f"Total Iterations: {len(self.iteration_history)}\n")
            f.write(f"Total Backtests: {len(self.all_results)}\n\n")
            
            for iter_data in self.iteration_history:
                f.write(f"Iteration {iter_data['iteration']}:\n")
                f.write(f"  Results: {iter_data['results_count']}\n")
                f.write(f"  Profitable: {iter_data['analysis']['profitable_count']}\n")
                f.write(f"  Avg PnL: ₹{iter_data['analysis']['avg_pnl']:.2f}\n")
                f.write(f"  Win Rate: {iter_data['analysis']['win_rate']:.1f}%\n\n")
        
        print(f"\n✓ Reports saved to {output_dir}/")
        print(f"  - {json_file.name}")
        print(f"  - {summary_file.name}")

# ==================== MAIN ====================

def main():
    config = BacktestConfig(
        underlying=os.getenv('UNDERLYING', 'NIFTY'),
        exchange=os.getenv('EXCHANGE', 'NSE_INDEX'),
        strike_int=int(os.getenv('STRIKE_INT', '50')),
        lot_size=int(os.getenv('LOT_SIZE', '25')),
        timeframes=['1d'],
        periods={
            "yesterday": 1,
            "1week": 5,
            "1month": 20
        },
        profit_target_pct=float(os.getenv('PROFIT_TARGET_PCT', '50.0')),
        stop_loss_pct=float(os.getenv('STOP_LOSS_PCT', '200.0')),
        time_based_exit_days=int(os.getenv('TIME_BASED_EXIT_DAYS', '1')),
        max_holding_days=int(os.getenv('MAX_HOLDING_DAYS', '30')),
        default_volatility=float(os.getenv('DEFAULT_VOLATILITY', '15.0')),
        interest_rate=float(os.getenv('INTEREST_RATE', '6.5')),
        quantity=int(os.getenv('QUANTITY', '75')),
        product=os.getenv('PRODUCT', 'MIS'),
        slippage_pct=float(os.getenv('SLIPPAGE_PCT', '0.1')),
        use_analyze_mode=True
    )
    
    api_key = os.getenv('OPENALGO_API_KEY', os.getenv('OPENALGO_APIKEY'))
    max_iterations = int(os.getenv('MAX_ITERATIONS', '5'))
    
    runner = IterativeBacktestRunner(config, api_key, max_iterations)
    results = runner.run_iterative_backtests()
    
    if results:
        runner.generate_final_report()
        print(f"\n{'='*70}")
        print("ITERATIVE BACKTESTING COMPLETE")
        print(f"{'='*70}")
        print(f"Total backtests: {len(results)}")
        print(f"Iterations completed: {len(runner.iteration_history)}")
    else:
        print("\n❌ No results generated")

if __name__ == "__main__":
    main()
