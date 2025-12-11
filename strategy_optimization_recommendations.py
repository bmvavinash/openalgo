"""
Generate strategy optimization recommendations based on today's and historical performance
"""
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
import os
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.sandbox_db import SandboxPositions, SandboxTrades, db_session
from analyze_today_trades import get_today_strategy_analysis

def analyze_strategy_performance(strategy_stats):
    """Analyze strategy performance and identify issues"""
    recommendations = []
    
    for strategy_name, stats in strategy_stats.items():
        strategy_recs = {
            'strategy': strategy_name,
            'current_pnl': stats['total_pnl'],
            'trades': stats['total_trades'],
            'win_rate': stats['win_rate'],
            'recommendations': []
        }
        
        # Analyze performance
        if stats['total_pnl'] < 0:
            strategy_recs['recommendations'].append({
                'priority': 'HIGH',
                'issue': 'Negative P&L',
                'recommendation': 'Review entry/exit criteria. Consider adding stop loss if not present.',
                'action': 'Add 2% stop loss to limit losses'
            })
        
        if stats['total_trades'] == 0:
            strategy_recs['recommendations'].append({
                'priority': 'MEDIUM',
                'issue': 'No trading activity',
                'recommendation': 'Strategy may not be generating signals. Review signal parameters.',
                'action': 'Check if market conditions match strategy requirements'
            })
        
        if stats['total_trades'] > 10:
            strategy_recs['recommendations'].append({
                'priority': 'MEDIUM',
                'issue': 'High trade frequency',
                'recommendation': 'May be overtrading. Consider adding filters to reduce false signals.',
                'action': 'Add trend filter or increase signal confirmation requirements'
            })
        
        if stats['win_rate'] > 0 and stats['win_rate'] < 30:
            strategy_recs['recommendations'].append({
                'priority': 'HIGH',
                'issue': 'Low win rate',
                'recommendation': f'Win rate of {stats["win_rate"]:.1f}% is below optimal. Review entry criteria.',
                'action': 'Improve entry signal quality or add confirmation indicators'
            })
        
        if stats['unique_symbols'] == 1:
            strategy_recs['recommendations'].append({
                'priority': 'LOW',
                'issue': 'Limited diversification',
                'recommendation': 'Trading only one symbol. Consider adding more symbols for diversification.',
                'action': 'Add additional symbols to strategy configuration'
            })
        
        recommendations.append(strategy_recs)
    
    return recommendations


def generate_optimization_recommendations():
    """Generate comprehensive optimization recommendations"""
    
    print("\n" + "="*120)
    print("🎯 STRATEGY OPTIMIZATION RECOMMENDATIONS")
    print("="*120)
    
    # Get today's performance
    today_stats, session_start, current_time = get_today_strategy_analysis()
    
    if not today_stats:
        print("\n❌ No trading data available for analysis.")
        return
    
    # Analyze each strategy
    recommendations = analyze_strategy_performance(today_stats)
    
    # Sort by priority and P&L
    high_priority = []
    medium_priority = []
    low_priority = []
    
    for rec in recommendations:
        has_high = any(r['priority'] == 'HIGH' for r in rec['recommendations'])
        has_medium = any(r['priority'] == 'MEDIUM' for r in rec['recommendations'])
        
        if has_high:
            high_priority.append(rec)
        elif has_medium:
            medium_priority.append(rec)
        else:
            low_priority.append(rec)
    
    # Print recommendations
    print("\n" + "="*120)
    print("🔴 HIGH PRIORITY RECOMMENDATIONS")
    print("="*120)
    
    if high_priority:
        for rec in high_priority:
            print(f"\n📌 Strategy: {rec['strategy']}")
            print(f"   Current P&L: ₹ {rec['current_pnl']:,.2f}")
            print(f"   Total Trades: {rec['trades']}")
            
            for r in rec['recommendations']:
                if r['priority'] == 'HIGH':
                    print(f"\n   ⚠️  Issue: {r['issue']}")
                    print(f"   💡 Recommendation: {r['recommendation']}")
                    print(f"   ✅ Action: {r['action']}")
    else:
        print("\n✅ No high priority issues found!")
    
    print("\n" + "="*120)
    print("🟡 MEDIUM PRIORITY RECOMMENDATIONS")
    print("="*120)
    
    if medium_priority:
        for rec in medium_priority:
            print(f"\n📌 Strategy: {rec['strategy']}")
            print(f"   Current P&L: ₹ {rec['current_pnl']:,.2f}")
            
            for r in rec['recommendations']:
                if r['priority'] == 'MEDIUM':
                    print(f"\n   ⚠️  Issue: {r['issue']}")
                    print(f"   💡 Recommendation: {r['recommendation']}")
                    print(f"   ✅ Action: {r['action']}")
    else:
        print("\n✅ No medium priority issues found!")
    
    print("\n" + "="*120)
    print("🟢 LOW PRIORITY RECOMMENDATIONS")
    print("="*120)
    
    if low_priority:
        for rec in low_priority:
            print(f"\n📌 Strategy: {rec['strategy']}")
            
            for r in rec['recommendations']:
                if r['priority'] == 'LOW':
                    print(f"\n   💡 Suggestion: {r['recommendation']}")
                    print(f"   ✅ Action: {r['action']}")
    else:
        print("\n✅ No low priority suggestions!")
    
    # Best practices recommendations
    print("\n" + "="*120)
    print("📚 BEST PRACTICES RECOMMENDATIONS")
    print("="*120)
    
    # Find best and worst strategies
    sorted_strategies = sorted(today_stats.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
    
    if len(sorted_strategies) > 0:
        best_strategy = sorted_strategies[0]
        worst_strategy = sorted_strategies[-1] if sorted_strategies[-1][1]['total_pnl'] < 0 else None
        
        print(f"\n🏆 Best Performing Strategy: {best_strategy[0]}")
        print(f"   P&L: ₹ {best_strategy[1]['total_pnl']:,.2f}")
        print(f"   ✅ Continue using this strategy")
        print(f"   ✅ Consider increasing position size if risk allows")
        print(f"   ✅ Monitor for consistency")
        
        if worst_strategy:
            print(f"\n⚠️  Underperforming Strategy: {worst_strategy[0]}")
            print(f"   P&L: ₹ {worst_strategy[1]['total_pnl']:,.2f}")
            print(f"   ❌ Review strategy parameters")
            print(f"   ❌ Consider pausing until optimized")
            print(f"   ❌ Analyze losing trades for patterns")
    
    # General recommendations
    print(f"\n{'─'*120}")
    print("💡 GENERAL OPTIMIZATION TIPS")
    print(f"{'─'*120}")
    
    total_pnl = sum(s['total_pnl'] for s in today_stats.values())
    total_trades = sum(s['total_trades'] for s in today_stats.values())
    
    print(f"\n1. Risk Management:")
    print(f"   - All strategies should have stop loss (2-3% recommended)")
    print(f"   - Set take profit targets (4-5% recommended)")
    print(f"   - Never risk more than 1-2% of capital per trade")
    
    print(f"\n2. Position Sizing:")
    print(f"   - Current total trades: {total_trades}")
    if total_trades > 20:
        print(f"   - ⚠️  High trade frequency - consider reducing position sizes")
    elif total_trades < 5:
        print(f"   - ✅ Low trade frequency - good for quality over quantity")
    
    print(f"\n3. Strategy Diversification:")
    print(f"   - Currently running {len(today_stats)} strategies")
    print(f"   - ✅ Good diversification across strategies")
    print(f"   - Consider diversifying across different timeframes")
    
    print(f"\n4. Performance Monitoring:")
    print(f"   - Today's Total P&L: ₹ {total_pnl:,.2f}")
    if total_pnl > 0:
        print(f"   - ✅ Profitable day - maintain current approach")
    else:
        print(f"   - ⚠️  Review all strategies for improvement")
    
    print(f"\n5. Entry/Exit Optimization:")
    print(f"   - Use multiple confirmation signals before entry")
    print(f"   - Avoid trading during low volatility periods")
    print(f"   - Set clear exit rules (stop loss, take profit, time-based)")
    
    # Specific strategy recommendations based on today's data
    print(f"\n{'='*120}")
    print("🎯 STRATEGY-SPECIFIC RECOMMENDATIONS")
    print(f"{'='*120}")
    
    for strategy_name, stats in sorted(today_stats.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
        print(f"\n📊 {strategy_name}")
        print(f"{'─'*80}")
        print(f"P&L: ₹ {stats['total_pnl']:,.2f} | Trades: {stats['total_trades']} | Win Rate: {stats['win_rate']:.1f}%")
        
        if stats['total_pnl'] > 500:
            print(f"✅ EXCELLENT PERFORMANCE")
            print(f"   - Continue with current settings")
            print(f"   - Consider scaling up position size gradually")
            print(f"   - Monitor for consistency over next few days")
        
        elif stats['total_pnl'] > 0:
            print(f"✅ GOOD PERFORMANCE")
            print(f"   - Strategy is working well")
            print(f"   - Fine-tune entry/exit for better results")
            print(f"   - Consider adding more symbols")
        
        elif stats['total_pnl'] == 0:
            print(f"➖ NEUTRAL PERFORMANCE")
            print(f"   - Strategy needs optimization")
            print(f"   - Review signal generation logic")
            print(f"   - Check if market conditions match strategy")
        
        else:
            print(f"❌ NEEDS IMPROVEMENT")
            print(f"   - Review all trades for patterns")
            print(f"   - Add stop loss if missing")
            print(f"   - Consider pausing until optimized")
            print(f"   - Analyze why losses occurred")
        
        if stats['total_trades'] == 0:
            print(f"   ⚠️  No trades executed - check signal generation")
        elif stats['total_trades'] > 5:
            print(f"   ⚠️  High trade frequency - consider adding filters")
        
        if stats['win_rate'] > 0 and stats['win_rate'] < 40:
            print(f"   ⚠️  Low win rate ({stats['win_rate']:.1f}%) - improve entry quality")


def main():
    """Main function"""
    generate_optimization_recommendations()
    
    print("\n" + "="*120)
    print("✅ Optimization Recommendations Complete")
    print("="*120 + "\n")


if __name__ == "__main__":
    main()






