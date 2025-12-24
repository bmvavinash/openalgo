#!/usr/bin/env python
"""
Main Option Strategy Backtest Runner
Runs comprehensive backtests on all option strategies
Tests multiple timeframes and periods
Generates detailed analytics reports
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from option_backtest_framework import (
    BacktestConfig, OptionBacktestEngine, AnalyticsCalculator
)
from strategy_backtests import STRATEGY_BACKTESTS

# ==================== CONFIGURATION ====================

def create_default_config() -> BacktestConfig:
    """Create default backtest configuration"""
    return BacktestConfig(
        underlying=os.getenv('UNDERLYING', 'NIFTY'),
        exchange=os.getenv('EXCHANGE', 'NSE_INDEX'),
        strike_int=int(os.getenv('STRIKE_INT', '50')),
        lot_size=int(os.getenv('LOT_SIZE', '25')),
        timeframes=os.getenv('TIMEFRAMES', '1m,5m,15m,1h,1d').split(','),
        periods={
            "yesterday": 1,
            "1week": 5,
            "1month": 20,
            "3months": 60
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

# ==================== MAIN RUNNER ====================

class BacktestRunner:
    """Main backtest runner"""
    
    def __init__(self, config: BacktestConfig, api_key: Optional[str] = None):
        self.config = config
        self.api_key = api_key or os.getenv('OPENALGO_API_KEY', os.getenv('OPENALGO_APIKEY'))
        self.engine = OptionBacktestEngine(config, self.api_key)
        self.all_results = []
    
    def get_date_range(self, period_name: str, period_days: int) -> tuple:
        """Get start and end dates for a period"""
        end_date = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
        
        # Adjust for weekends
        while end_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            end_date -= timedelta(days=1)
        
        start_date = end_date - timedelta(days=period_days)
        
        # Adjust start date to avoid weekends
        while start_date.weekday() >= 5:
            start_date -= timedelta(days=1)
        
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def run_backtest(
        self,
        strategy_name: str,
        timeframe: str,
        period_name: str,
        start_date: str,
        end_date: str
    ) -> Dict:
        """Run a single backtest"""
        print(f"\n{'='*70}")
        print(f"Running: {strategy_name} | {timeframe} | {period_name}")
        print(f"Period: {start_date} to {end_date}")
        print(f"{'='*70}")
        
        # Get historical data
        df = self.engine.get_historical_data(
            symbol=self.config.underlying,
            exchange=self.config.exchange,
            interval=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or df.empty:
            print(f"  ❌ No data available for {strategy_name} {timeframe} {period_name}")
            return None
        
        print(f"  ✓ Fetched {len(df)} data points")
        
        # Get strategy backtest function
        backtest_func = STRATEGY_BACKTESTS.get(strategy_name)
        if not backtest_func:
            print(f"  ❌ Strategy {strategy_name} not found")
            return None
        
        # Run backtest
        try:
            if strategy_name == "Strangle":
                trades = backtest_func(self.engine, df, self.config, otm_level=2)
            elif strategy_name == "Iron Condor":
                trades = backtest_func(self.engine, df, self.config, sell_otm=5, buy_otm=10)
            elif strategy_name == "Bull Call Spread":
                trades = backtest_func(self.engine, df, self.config, buy_offset="ITM2", sell_otm=5)
            else:
                trades = backtest_func(self.engine, df, self.config)
            
            # Calculate analytics
            results = AnalyticsCalculator.calculate_results(
                trades, strategy_name, timeframe, period_name, start_date, end_date
            )
            
            print(f"  ✓ Completed: {results.total_trades} trades, PnL: ₹{results.net_pnl:.2f}, Win Rate: {results.win_rate:.1f}%")
            
            return results
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_all_backtests(self) -> List[Dict]:
        """Run all backtests for all strategies, timeframes, and periods"""
        all_results = []
        
        strategies = list(STRATEGY_BACKTESTS.keys())
        
        print("\n" + "="*70)
        print("OPTION STRATEGY BACKTESTING")
        print("="*70)
        print(f"Underlying: {self.config.underlying}")
        print(f"Exchange: {self.config.exchange}")
        print(f"Strategies: {', '.join(strategies)}")
        print(f"Timeframes: {', '.join(self.config.timeframes)}")
        print(f"Periods: {', '.join(self.config.periods.keys())}")
        print("="*70)
        
        for strategy_name in strategies:
            for timeframe in self.config.timeframes:
                for period_name, period_days in self.config.periods.items():
                    start_date, end_date = self.get_date_range(period_name, period_days)
                    
                    result = self.run_backtest(
                        strategy_name, timeframe, period_name, start_date, end_date
                    )
                    
                    if result:
                        all_results.append(result)
        
        return all_results
    
    def generate_report(self, results: List[Dict], output_dir: str = "backtest_results"):
        """Generate comprehensive analytics report"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Convert results to dict for JSON
        results_dict = []
        for r in results:
            if hasattr(r, '__dict__'):
                r_dict = r.__dict__.copy()
                # Convert any remaining non-serializable objects
                for key, value in r_dict.items():
                    if hasattr(value, '__dict__'):
                        r_dict[key] = str(value)
                results_dict.append(r_dict)
            else:
                results_dict.append(r)
        
        # Save JSON report
        json_file = output_path / f"backtest_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results_dict, f, indent=2, default=str)
        print(f"\n✓ Saved JSON report: {json_file}")
        
        # Generate summary report
        summary_file = output_path / f"backtest_summary_{timestamp}.txt"
        self._generate_summary_report(results, summary_file)
        print(f"✓ Saved summary report: {summary_file}")
        
        # Generate detailed CSV
        csv_file = output_path / f"backtest_details_{timestamp}.csv"
        self._generate_csv_report(results, csv_file)
        print(f"✓ Saved CSV report: {csv_file}")
        
        # Generate best/worst analysis
        analysis_file = output_path / f"backtest_analysis_{timestamp}.txt"
        self._generate_analysis_report(results, analysis_file)
        print(f"✓ Saved analysis report: {analysis_file}")
    
    def _generate_summary_report(self, results: List, output_file: Path):
        """Generate summary text report"""
        with open(output_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("OPTION STRATEGY BACKTEST SUMMARY\n")
            f.write("="*70 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Backtests: {len(results)}\n\n")
            
            # Group by strategy
            by_strategy = {}
            for r in results:
                strategy = r.strategy_name if hasattr(r, 'strategy_name') else r.get('strategy_name', 'Unknown')
                if strategy not in by_strategy:
                    by_strategy[strategy] = []
                by_strategy[strategy].append(r)
            
            for strategy, strategy_results in by_strategy.items():
                f.write(f"\n{'='*70}\n")
                f.write(f"STRATEGY: {strategy}\n")
                f.write(f"{'='*70}\n\n")
                
                # Calculate averages
                total_pnl = sum([r.net_pnl if hasattr(r, 'net_pnl') else r.get('net_pnl', 0) for r in strategy_results])
                avg_pnl = total_pnl / len(strategy_results) if strategy_results else 0
                avg_win_rate = sum([r.win_rate if hasattr(r, 'win_rate') else r.get('win_rate', 0) for r in strategy_results]) / len(strategy_results) if strategy_results else 0
                total_trades = sum([r.total_trades if hasattr(r, 'total_trades') else r.get('total_trades', 0) for r in strategy_results])
                
                f.write(f"Total Backtests: {len(strategy_results)}\n")
                f.write(f"Average PnL: ₹{avg_pnl:.2f}\n")
                f.write(f"Total PnL: ₹{total_pnl:.2f}\n")
                f.write(f"Average Win Rate: {avg_win_rate:.1f}%\n")
                f.write(f"Total Trades: {total_trades}\n\n")
                
                # Best and worst
                best = max(strategy_results, key=lambda x: x.net_pnl if hasattr(x, 'net_pnl') else x.get('net_pnl', -999999))
                worst = min(strategy_results, key=lambda x: x.net_pnl if hasattr(x, 'net_pnl') else x.get('net_pnl', 999999))
                
                f.write(f"Best: {best.timeframe if hasattr(best, 'timeframe') else best.get('timeframe')} | {best.period if hasattr(best, 'period') else best.get('period')} | PnL: ₹{best.net_pnl if hasattr(best, 'net_pnl') else best.get('net_pnl', 0):.2f}\n")
                f.write(f"Worst: {worst.timeframe if hasattr(worst, 'timeframe') else worst.get('timeframe')} | {worst.period if hasattr(worst, 'period') else worst.get('period')} | PnL: ₹{worst.net_pnl if hasattr(worst, 'net_pnl') else worst.get('net_pnl', 0):.2f}\n")
    
    def _generate_csv_report(self, results: List, output_file: Path):
        """Generate detailed CSV report"""
        rows = []
        for r in results:
            row = {
                'Strategy': r.strategy_name if hasattr(r, 'strategy_name') else r.get('strategy_name'),
                'Timeframe': r.timeframe if hasattr(r, 'timeframe') else r.get('timeframe'),
                'Period': r.period if hasattr(r, 'period') else r.get('period'),
                'Start Date': r.start_date if hasattr(r, 'start_date') else r.get('start_date'),
                'End Date': r.end_date if hasattr(r, 'end_date') else r.get('end_date'),
                'Total Trades': r.total_trades if hasattr(r, 'total_trades') else r.get('total_trades'),
                'Winning Trades': r.winning_trades if hasattr(r, 'winning_trades') else r.get('winning_trades'),
                'Losing Trades': r.losing_trades if hasattr(r, 'losing_trades') else r.get('losing_trades'),
                'Win Rate %': r.win_rate if hasattr(r, 'win_rate') else r.get('win_rate'),
                'Total PnL': r.total_pnl if hasattr(r, 'total_pnl') else r.get('total_pnl'),
                'Net PnL': r.net_pnl if hasattr(r, 'net_pnl') else r.get('net_pnl'),
                'Avg PnL per Trade': r.average_pnl_per_trade if hasattr(r, 'average_pnl_per_trade') else r.get('average_pnl_per_trade'),
                'Average Win': r.average_win if hasattr(r, 'average_win') else r.get('average_win'),
                'Average Loss': r.average_loss if hasattr(r, 'average_loss') else r.get('average_loss'),
                'Largest Win': r.largest_win if hasattr(r, 'largest_win') else r.get('largest_win'),
                'Largest Loss': r.largest_loss if hasattr(r, 'largest_loss') else r.get('largest_loss'),
                'Max Drawdown': r.max_drawdown if hasattr(r, 'max_drawdown') else r.get('max_drawdown'),
                'Max Drawdown %': r.max_drawdown_pct if hasattr(r, 'max_drawdown_pct') else r.get('max_drawdown_pct'),
                'Sharpe Ratio': r.sharpe_ratio if hasattr(r, 'sharpe_ratio') else r.get('sharpe_ratio'),
                'Sortino Ratio': r.sortino_ratio if hasattr(r, 'sortino_ratio') else r.get('sortino_ratio'),
                'Avg Holding Days': r.average_holding_days if hasattr(r, 'average_holding_days') else r.get('average_holding_days'),
                'Total Trading Days': r.total_trading_days if hasattr(r, 'total_trading_days') else r.get('total_trading_days'),
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False)
    
    def _generate_analysis_report(self, results: List, output_file: Path):
        """Generate detailed analysis report"""
        with open(output_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("OPTION STRATEGY BACKTEST ANALYSIS\n")
            f.write("="*70 + "\n\n")
            
            # Overall statistics
            profitable = [r for r in results if (r.net_pnl if hasattr(r, 'net_pnl') else r.get('net_pnl', 0)) > 0]
            losing = [r for r in results if (r.net_pnl if hasattr(r, 'net_pnl') else r.get('net_pnl', 0)) < 0]
            
            f.write(f"Total Backtests: {len(results)}\n")
            f.write(f"Profitable: {len(profitable)} ({len(profitable)/len(results)*100:.1f}%)\n")
            f.write(f"Losing: {len(losing)} ({len(losing)/len(results)*100:.1f}%)\n\n")
            
            # Best strategies by timeframe
            f.write("BEST STRATEGIES BY TIMEFRAME:\n")
            f.write("-"*70 + "\n")
            for timeframe in self.config.timeframes:
                tf_results = [r for r in results if (r.timeframe if hasattr(r, 'timeframe') else r.get('timeframe')) == timeframe]
                if tf_results:
                    best = max(tf_results, key=lambda x: x.net_pnl if hasattr(x, 'net_pnl') else x.get('net_pnl', -999999))
                    f.write(f"{timeframe:>6}: {best.strategy_name if hasattr(best, 'strategy_name') else best.get('strategy_name')} | "
                           f"PnL: ₹{best.net_pnl if hasattr(best, 'net_pnl') else best.get('net_pnl', 0):.2f} | "
                           f"Win Rate: {best.win_rate if hasattr(best, 'win_rate') else best.get('win_rate', 0):.1f}%\n")
            
            f.write("\n")
            
            # Best strategies by period
            f.write("BEST STRATEGIES BY PERIOD:\n")
            f.write("-"*70 + "\n")
            for period in self.config.periods.keys():
                period_results = [r for r in results if (r.period if hasattr(r, 'period') else r.get('period')) == period]
                if period_results:
                    best = max(period_results, key=lambda x: x.net_pnl if hasattr(x, 'net_pnl') else x.get('net_pnl', -999999))
                    f.write(f"{period:>12}: {best.strategy_name if hasattr(best, 'strategy_name') else best.get('strategy_name')} | "
                           f"{best.timeframe if hasattr(best, 'timeframe') else best.get('timeframe')} | "
                           f"PnL: ₹{best.net_pnl if hasattr(best, 'net_pnl') else best.get('net_pnl', 0):.2f}\n")
            
            f.write("\n")
            
            # Strategy rankings
            f.write("STRATEGY RANKINGS (by average PnL):\n")
            f.write("-"*70 + "\n")
            by_strategy = {}
            for r in results:
                strategy = r.strategy_name if hasattr(r, 'strategy_name') else r.get('strategy_name', 'Unknown')
                if strategy not in by_strategy:
                    by_strategy[strategy] = []
                by_strategy[strategy].append(r)
            
            strategy_avg_pnl = []
            for strategy, strategy_results in by_strategy.items():
                avg_pnl = sum([r.net_pnl if hasattr(r, 'net_pnl') else r.get('net_pnl', 0) for r in strategy_results]) / len(strategy_results)
                strategy_avg_pnl.append((strategy, avg_pnl, len(strategy_results)))
            
            strategy_avg_pnl.sort(key=lambda x: x[1], reverse=True)
            
            for i, (strategy, avg_pnl, count) in enumerate(strategy_avg_pnl, 1):
                f.write(f"{i}. {strategy:20} | Avg PnL: ₹{avg_pnl:>10.2f} | Tests: {count}\n")

# ==================== MAIN ====================

def main():
    parser = argparse.ArgumentParser(description='Run option strategy backtests')
    parser.add_argument('--underlying', default='NIFTY', help='Underlying symbol')
    parser.add_argument('--exchange', default='NSE_INDEX', help='Exchange')
    parser.add_argument('--timeframes', default='1m,5m,15m,1h,1d', help='Comma-separated timeframes')
    parser.add_argument('--output-dir', default='backtest_results', help='Output directory')
    parser.add_argument('--api-key', help='OpenAlgo API key')
    
    args = parser.parse_args()
    
    # Create config
    config = create_default_config()
    config.underlying = args.underlying
    config.exchange = args.exchange
    config.timeframes = args.timeframes.split(',')
    
    # Run backtests
    runner = BacktestRunner(config, args.api_key)
    results = runner.run_all_backtests()
    
    # Generate reports
    if results:
        runner.generate_report(results, args.output_dir)
        print(f"\n{'='*70}")
        print("BACKTESTING COMPLETE")
        print(f"{'='*70}")
        print(f"Total backtests completed: {len(results)}")
        print(f"Results saved to: {args.output_dir}")
    else:
        print("\n❌ No results generated. Check data availability and configuration.")

if __name__ == "__main__":
    main()

