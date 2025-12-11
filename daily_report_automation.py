"""
Automated daily trading report generation
Runs daily and generates comprehensive trading analysis reports
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import os
import json

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analyze_today_trades import get_today_strategy_analysis
from analyze_trade_details import get_trade_details
from compare_historical_performance import get_strategy_daily_performance

def generate_daily_report():
    """Generate comprehensive daily trading report"""
    
    print("\n" + "="*120)
    print("📊 GENERATING DAILY TRADING REPORT")
    print("="*120)
    
    today = datetime.now()
    report_date = today.strftime('%Y-%m-%d')
    
    # Get today's analysis
    strategy_stats, session_start, current_time = get_today_strategy_analysis()
    trades, positions, _, _ = get_trade_details()
    
    # Create reports directory
    reports_dir = PROJECT_ROOT / 'reports' / 'daily'
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate report data
    report_data = {
        'date': report_date,
        'generated_at': today.strftime('%Y-%m-%d %H:%M:%S'),
        'session_start': session_start.strftime('%Y-%m-%d %H:%M:%S') if session_start else None,
        'strategies': {},
        'summary': {
            'total_pnl': 0.0,
            'total_trades': 0,
            'total_symbols': 0,
            'best_strategy': None,
            'worst_strategy': None
        }
    }
    
    # Process strategy statistics
    total_pnl = 0.0
    best_strategy = None
    worst_strategy = None
    best_pnl = float('-inf')
    worst_pnl = float('inf')
    
    for strategy_name, stats in strategy_stats.items():
        report_data['strategies'][strategy_name] = {
            'total_pnl': stats['total_pnl'],
            'realized_pnl': stats['realized_pnl'],
            'unrealized_pnl': stats['unrealized_pnl'],
            'total_trades': stats['total_trades'],
            'winning_trades': stats['winning_trades'],
            'losing_trades': stats['losing_trades'],
            'win_rate': stats['win_rate'],
            'unique_symbols': stats['unique_symbols'],
            'open_positions': stats['open_positions']
        }
        
        total_pnl += stats['total_pnl']
        
        if stats['total_pnl'] > best_pnl:
            best_pnl = stats['total_pnl']
            best_strategy = strategy_name
        
        if stats['total_pnl'] < worst_pnl:
            worst_pnl = stats['total_pnl']
            worst_strategy = strategy_name
    
    # Update summary
    report_data['summary'] = {
        'total_pnl': total_pnl,
        'total_trades': sum(s['total_trades'] for s in strategy_stats.values()),
        'total_symbols': len(set(
            f"{t.symbol}_{t.exchange}" 
            for stats in strategy_stats.values() 
            for t in stats['trades']
        )),
        'best_strategy': best_strategy,
        'worst_strategy': worst_strategy,
        'best_pnl': best_pnl,
        'worst_pnl': worst_pnl
    }
    
    # Save JSON report
    json_file = reports_dir / f'report_{report_date}.json'
    with open(json_file, 'w') as f:
        json.dump(report_data, f, indent=2, default=str)
    
    print(f"\n✅ JSON Report saved: {json_file}")
    
    # Generate markdown report
    md_file = reports_dir / f'report_{report_date}.md'
    generate_markdown_report(report_data, md_file, trades)
    
    print(f"✅ Markdown Report saved: {md_file}")
    
    # Generate summary email/text format
    summary_file = reports_dir / f'summary_{report_date}.txt'
    generate_summary_report(report_data, summary_file)
    
    print(f"✅ Summary Report saved: {summary_file}")
    
    print(f"\n{'='*120}")
    print("📊 REPORT SUMMARY")
    print(f"{'='*120}")
    print(f"Date: {report_date}")
    print(f"Total P&L: ₹ {total_pnl:,.2f}")
    print(f"Total Trades: {report_data['summary']['total_trades']}")
    print(f"Best Strategy: {best_strategy} (₹ {best_pnl:,.2f})")
    if worst_strategy and worst_pnl < 0:
        print(f"Worst Strategy: {worst_strategy} (₹ {worst_pnl:,.2f})")
    print(f"\nReports saved to: {reports_dir}")
    print(f"{'='*120}\n")
    
    return report_data


def generate_markdown_report(report_data, file_path, trades):
    """Generate markdown format report"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"# Daily Trading Report - {report_data['date']}\n\n")
        f.write(f"**Generated:** {report_data['generated_at']}\n\n")
        f.write("---\n\n")
        
        # Summary
        f.write("## 📊 Executive Summary\n\n")
        summary = report_data['summary']
        f.write(f"- **Total P&L:** ₹ {summary['total_pnl']:,.2f}\n")
        f.write(f"- **Total Trades:** {summary['total_trades']}\n")
        f.write(f"- **Symbols Traded:** {summary['total_symbols']}\n")
        f.write(f"- **Best Strategy:** {summary['best_strategy']} (₹ {summary['best_pnl']:,.2f})\n")
        if summary['worst_strategy']:
            f.write(f"- **Worst Strategy:** {summary['worst_strategy']} (₹ {summary['worst_pnl']:,.2f})\n")
        f.write("\n---\n\n")
        
        # Strategy details
        f.write("## 📈 Strategy Performance\n\n")
        f.write("| Strategy | Total P&L | Realized | Unrealized | Trades | Win Rate | Symbols |\n")
        f.write("|----------|-----------|----------|------------|--------|----------|----------|\n")
        
        for strategy_name, stats in sorted(
            report_data['strategies'].items(), 
            key=lambda x: x[1]['total_pnl'], 
            reverse=True
        ):
            status = "✅" if stats['total_pnl'] > 0 else "❌" if stats['total_pnl'] < 0 else "➖"
            f.write(f"| {status} {strategy_name} | ₹ {stats['total_pnl']:,.2f} | "
                   f"₹ {stats['realized_pnl']:,.2f} | ₹ {stats['unrealized_pnl']:,.2f} | "
                   f"{stats['total_trades']} | {stats['win_rate']:.1f}% | {stats['unique_symbols']} |\n")
        
        f.write("\n---\n\n")
        
        # Trade details
        if trades:
            f.write("## 📋 Trade Details\n\n")
            f.write("| Time | Strategy | Symbol | Action | Qty | Price |\n")
            f.write("|------|----------|--------|--------|-----|-------|\n")
            
            for trade in sorted(trades, key=lambda x: x.trade_timestamp):
                strategy_display = (trade.strategy or "No Strategy")[:20]
                f.write(f"| {trade.trade_timestamp.strftime('%H:%M:%S')} | {strategy_display} | "
                       f"{trade.symbol} | {trade.action} | {trade.quantity} | ₹ {float(trade.price):,.2f} |\n")
        
        f.write("\n---\n\n")
        f.write("*Report generated automatically by OpenAlgo Daily Report System*\n")


def generate_summary_report(report_data, file_path):
    """Generate text summary report"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write(f"DAILY TRADING REPORT - {report_data['date']}\n")
        f.write("="*80 + "\n\n")
        
        summary = report_data['summary']
        f.write(f"Total P&L: ₹ {summary['total_pnl']:,.2f}\n")
        f.write(f"Total Trades: {summary['total_trades']}\n")
        f.write(f"Best Strategy: {summary['best_strategy']} (₹ {summary['best_pnl']:,.2f})\n")
        if summary['worst_strategy']:
            f.write(f"Worst Strategy: {summary['worst_strategy']} (₹ {summary['worst_pnl']:,.2f})\n")
        
        f.write("\n" + "-"*80 + "\n")
        f.write("STRATEGY BREAKDOWN\n")
        f.write("-"*80 + "\n\n")
        
        for strategy_name, stats in sorted(
            report_data['strategies'].items(), 
            key=lambda x: x[1]['total_pnl'], 
            reverse=True
        ):
            f.write(f"{strategy_name}:\n")
            f.write(f"  P&L: ₹ {stats['total_pnl']:,.2f}\n")
            f.write(f"  Trades: {stats['total_trades']}\n")
            f.write(f"  Win Rate: {stats['win_rate']:.1f}%\n\n")


def main():
    """Main function"""
    try:
        report_data = generate_daily_report()
        return report_data
    except Exception as e:
        print(f"\n❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()






