#!/usr/bin/env python
"""
Run historical backtests for all metals strategies and save results to DB.
Use from UI (Metals > Analysis) or from CLI: python run_metals_historical_backtests.py [user_id]

When market is closed, this uses yfinance historical data to backtest each strategy.
Results are stored in metals_backtests and visible on each strategy's page and Metals > Analysis.
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from app import app


def _symbol_for_strategy(strategy):
    from blueprints.metals import METAL_SYMBOLS, METAL_SYMBOLS_ETF
    instrument_type = getattr(strategy, 'instrument_type', None) or 'MCX'
    if instrument_type == 'ETF':
        return (METAL_SYMBOLS_ETF.get(strategy.metal_type) or ['GOLDBEES'])[0]
    return (METAL_SYMBOLS.get(strategy.metal_type) or ['GOLDM'])[0]


def run_metals_historical_backtests(user_id=None, start_date=None, end_date=None, timeframe='5m'):
    """
    Run backtests for all metals strategies (optionally for one user).
    start_date/end_date: date strings YYYY-MM-DD. Default: last 30 days.
    Returns: list of dicts with strategy_id, strategy_name, backtest_id, status, error, results.
    """
    with app.app_context():
        from database.metals_db import (
            get_user_metals_strategies,
            MetalsStrategy,
            create_metals_backtest,
            update_backtest_results,
        )
        from strategies.backtest.metals_backtest_framework import BacktestConfig, MetalsBacktestEngine
        import json

        end = end_date or datetime.now().strftime('%Y-%m-%d')
        start = start_date or (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        if user_id:
            strategies = get_user_metals_strategies(user_id)
        else:
            strategies = MetalsStrategy.query.all()

        if not strategies:
            return []

        out = []
        for strategy in strategies:
            rec = {
                'strategy_id': strategy.id,
                'strategy_name': strategy.name,
                'metal_type': strategy.metal_type,
                'instrument_type': getattr(strategy, 'instrument_type', 'MCX'),
                'backtest_id': None,
                'status': 'pending',
                'error': None,
                'results': None,
            }
            try:
                symbol = _symbol_for_strategy(strategy)
                config = BacktestConfig(
                    metal_type=strategy.metal_type,
                    symbol=symbol,
                    start_date=start,
                    end_date=end,
                    timeframe=timeframe,
                    stop_loss_type=strategy.stop_loss_type or 'ADAPTIVE',
                    stop_loss_pct=float(strategy.stop_loss_pct or 2.0),
                    take_profit_pct=float(strategy.take_profit_pct or 4.0),
                )
                backtest = create_metals_backtest(
                    strategy_id=strategy.id,
                    start_date=datetime.strptime(start, '%Y-%m-%d'),
                    end_date=datetime.strptime(end, '%Y-%m-%d'),
                    timeframe=timeframe,
                )
                if not backtest:
                    rec['status'] = 'error'
                    rec['error'] = 'Failed to create backtest record'
                    out.append(rec)
                    continue

                rec['backtest_id'] = backtest.id
                engine = MetalsBacktestEngine(config)
                results = engine.run_backtest()

                update_backtest_results(backtest.id, {
                    'total_trades': results.total_trades,
                    'winning_trades': results.winning_trades,
                    'losing_trades': results.losing_trades,
                    'win_rate': results.win_rate,
                    'total_pnl': results.total_pnl,
                    'total_pnl_pct': results.total_pnl_pct,
                    'max_drawdown': results.max_drawdown,
                    'max_drawdown_pct': getattr(results, 'max_drawdown_pct', results.max_drawdown),
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
                        'exit_reason': t.exit_reason,
                    } for t in results.trades]),
                    'equity_curve': json.dumps(results.equity_curve),
                })
                rec['status'] = 'completed'
                rec['results'] = {
                    'total_trades': results.total_trades,
                    'win_rate': results.win_rate,
                    'total_pnl': results.total_pnl,
                    'total_pnl_pct': results.total_pnl_pct,
                    'max_drawdown_pct': getattr(results, 'max_drawdown_pct', results.max_drawdown),
                    'sharpe_ratio': results.sharpe_ratio,
                    'profit_factor': results.profit_factor,
                }
            except Exception as e:
                rec['status'] = 'error'
                rec['error'] = str(e)
            out.append(rec)
        return out


def print_analysis(reports):
    """Print a summary table of backtest results."""
    if not reports:
        print("No backtest reports.")
        return
    print("\n" + "=" * 100)
    print("METALS STRATEGIES – HISTORICAL BACKTEST ANALYSIS")
    print("=" * 100)
    print(f"{'Strategy':<30} | {'Metal':<6} | {'Type':<4} | {'Trades':>6} | {'Win%':>6} | {'P&L':>12} | {'P&L%':>8} | {'MaxDD%':>8} | {'Sharpe':>8} | {'PF':>6} | {'Status':<10}")
    print("-" * 100)
    for r in reports:
        name = (r['strategy_name'] or '')[:28]
        metal = r.get('metal_type', '')
        itype = r.get('instrument_type', 'MCX')
        res = r.get('results') or {}
        trades = res.get('total_trades', 0)
        win = res.get('win_rate', 0)
        pnl = res.get('total_pnl', 0)
        pnlpct = res.get('total_pnl_pct', 0)
        dd = res.get('max_drawdown_pct', 0)
        sharpe = res.get('sharpe_ratio', 0)
        pf = res.get('profit_factor', 0)
        status = r.get('status', '')
        err = r.get('error', '')
        if status == 'error':
            print(f"{name:<30} | {metal:<6} | {itype:<4} | {'—':>6} | {'—':>6} | {'—':>12} | {'—':>8} | {'—':>8} | {'—':>8} | {'—':>6} | ERROR: {err[:40]}")
        else:
            print(f"{name:<30} | {metal:<6} | {itype:<4} | {trades:>6} | {win:>5.1f}% | {pnl:>+11.2f} | {pnlpct:>+6.2f}% | {dd:>7.2f}% | {sharpe:>7.2f} | {pf:>6.2f} | {status:<10}")
    print("=" * 100)
    completed = [r for r in reports if r.get('status') == 'completed']
    errors = [r for r in reports if r.get('status') == 'error']
    print(f"Completed: {len(completed)} | Errors: {len(errors)}")
    print()


def write_analysis_report(reports, filepath=None):
    """Write analysis summary to METALS_BACKTEST_ANALYSIS.md (or given path)."""
    if not reports:
        return
    path = filepath or os.path.join(os.path.dirname(__file__), "METALS_BACKTEST_ANALYSIS.md")
    lines = [
        "# Metals Strategies – Historical Backtest Analysis",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary",
        "",
        "| Strategy | Metal | Type | Trades | Win % | P&L | P&L % | Max DD % | Sharpe | Profit Factor | Status |",
        "|----------|-------|------|--------|-------|-----|-------|----------|--------|---------------|--------|",
    ]
    for r in reports:
        name = (r.get('strategy_name') or '')[:35]
        metal = r.get('metal_type', '')
        itype = r.get('instrument_type', 'MCX')
        res = r.get('results') or {}
        status = r.get('status', '')
        err = r.get('error', '')
        if status == 'error':
            lines.append(f"| {name} | {metal} | {itype} | — | — | — | — | — | — | — | ERROR: {err[:50]} |")
        else:
            trades = res.get('total_trades', 0)
            win = res.get('win_rate', 0)
            pnl = res.get('total_pnl', 0)
            pnlpct = res.get('total_pnl_pct', 0)
            dd = res.get('max_drawdown_pct', 0)
            sharpe = res.get('sharpe_ratio', 0)
            pf = res.get('profit_factor', 0)
            lines.append(f"| {name} | {metal} | {itype} | {trades} | {win:.1f}% | {pnl:+.2f} | {pnlpct:+.2f}% | {dd:.2f}% | {sharpe:.2f} | {pf:.2f} | {status} |")
    completed = len([r for r in reports if r.get('status') == 'completed'])
    errors = len([r for r in reports if r.get('status') == 'error'])
    lines.extend([
        "",
        f"**Completed:** {completed} | **Errors:** {errors}",
        "",
        "## How to run",
        "",
        "- **From UI:** Metals → Backtest Analysis → set dates → **Run Backtests for All Strategies**.",
        "- **Per strategy:** Open a strategy → **Run Backtest** (custom dates/timeframe).",
        "- **From CLI:** `python run_metals_historical_backtests.py [user_id] [start_date] [end_date]`.",
        "",
    ])
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    start = sys.argv[2] if len(sys.argv) > 2 else None
    end = sys.argv[3] if len(sys.argv) > 3 else None
    reports = run_metals_historical_backtests(user_id=user_id, start_date=start, end_date=end)
    print_analysis(reports)
    write_analysis_report(reports)
