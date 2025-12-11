"""
Strategy performance alert system
Monitors strategy performance and sends alerts for significant events
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
from utils.logging import get_logger

logger = get_logger(__name__)

# Alert thresholds
ALERT_THRESHOLDS = {
    'loss_threshold': -500.0,  # Alert if strategy loses more than ₹500
    'profit_threshold': 1000.0,  # Alert if strategy profits more than ₹1000
    'trade_count_threshold': 20,  # Alert if more than 20 trades in a day
    'win_rate_threshold': 30.0,  # Alert if win rate below 30%
    'daily_loss_threshold': -1000.0,  # Alert if total daily loss exceeds ₹1000
}


def check_strategy_alerts():
    """Check for alert conditions and generate alerts"""
    
    alerts = []
    
    try:
        # Get today's performance
        strategy_stats, session_start, current_time = get_today_strategy_analysis()
        
        if not strategy_stats:
            return alerts
        
        total_pnl = sum(s['total_pnl'] for s in strategy_stats.values())
        
        # Check total daily loss
        if total_pnl < ALERT_THRESHOLDS['daily_loss_threshold']:
            alerts.append({
                'type': 'CRITICAL',
                'title': 'High Daily Loss',
                'message': f'Total daily P&L is ₹ {total_pnl:,.2f}, exceeding threshold of ₹ {ALERT_THRESHOLDS["daily_loss_threshold"]:,.2f}',
                'timestamp': datetime.now().isoformat()
            })
        
        # Check each strategy
        for strategy_name, stats in strategy_stats.items():
            # Check for significant loss
            if stats['total_pnl'] < ALERT_THRESHOLDS['loss_threshold']:
                alerts.append({
                    'type': 'WARNING',
                    'title': f'Strategy Loss Alert: {strategy_name}',
                    'message': f'{strategy_name} has lost ₹ {stats["total_pnl"]:,.2f} today. Consider reviewing or pausing.',
                    'strategy': strategy_name,
                    'pnl': stats['total_pnl'],
                    'timestamp': datetime.now().isoformat()
                })
            
            # Check for significant profit
            if stats['total_pnl'] > ALERT_THRESHOLDS['profit_threshold']:
                alerts.append({
                    'type': 'SUCCESS',
                    'title': f'Strategy Profit Alert: {strategy_name}',
                    'message': f'{strategy_name} has profited ₹ {stats["total_pnl"]:,.2f} today! Excellent performance.',
                    'strategy': strategy_name,
                    'pnl': stats['total_pnl'],
                    'timestamp': datetime.now().isoformat()
                })
            
            # Check trade count
            if stats['total_trades'] > ALERT_THRESHOLDS['trade_count_threshold']:
                alerts.append({
                    'type': 'INFO',
                    'title': f'High Trade Frequency: {strategy_name}',
                    'message': f'{strategy_name} has executed {stats["total_trades"]} trades today. Consider reviewing for overtrading.',
                    'strategy': strategy_name,
                    'trade_count': stats['total_trades'],
                    'timestamp': datetime.now().isoformat()
                })
            
            # Check win rate
            if stats['win_rate'] > 0 and stats['win_rate'] < ALERT_THRESHOLDS['win_rate_threshold']:
                alerts.append({
                    'type': 'WARNING',
                    'title': f'Low Win Rate: {strategy_name}',
                    'message': f'{strategy_name} has a win rate of {stats["win_rate"]:.1f}%. Consider optimizing entry criteria.',
                    'strategy': strategy_name,
                    'win_rate': stats['win_rate'],
                    'timestamp': datetime.now().isoformat()
                })
        
        return alerts
    
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")
        return alerts


def save_alerts(alerts):
    """Save alerts to file"""
    
    if not alerts:
        return
    
    alerts_dir = PROJECT_ROOT / 'reports' / 'alerts'
    alerts_dir.mkdir(parents=True, exist_ok=True)
    
    today = datetime.now().strftime('%Y-%m-%d')
    alerts_file = alerts_dir / f'alerts_{today}.json'
    
    # Load existing alerts
    existing_alerts = []
    if alerts_file.exists():
        try:
            with open(alerts_file, 'r') as f:
                existing_alerts = json.load(f)
        except:
            pass
    
    # Append new alerts
    existing_alerts.extend(alerts)
    
    # Save
    with open(alerts_file, 'w') as f:
        json.dump(existing_alerts, f, indent=2)
    
    logger.info(f"Saved {len(alerts)} alerts to {alerts_file}")


def print_alerts(alerts):
    """Print alerts to console"""
    
    if not alerts:
        print("\n✅ No alerts generated - all strategies performing within normal parameters")
        return
    
    print("\n" + "="*120)
    print("🚨 STRATEGY PERFORMANCE ALERTS")
    print("="*120)
    
    # Group by type
    critical = [a for a in alerts if a['type'] == 'CRITICAL']
    warnings = [a for a in alerts if a['type'] == 'WARNING']
    success = [a for a in alerts if a['type'] == 'SUCCESS']
    info = [a for a in alerts if a['type'] == 'INFO']
    
    if critical:
        print("\n🔴 CRITICAL ALERTS:")
        for alert in critical:
            print(f"  ⚠️  {alert['title']}")
            print(f"     {alert['message']}")
    
    if warnings:
        print("\n🟡 WARNINGS:")
        for alert in warnings:
            print(f"  ⚠️  {alert['title']}")
            print(f"     {alert['message']}")
    
    if success:
        print("\n🟢 SUCCESS ALERTS:")
        for alert in success:
            print(f"  ✅ {alert['title']}")
            print(f"     {alert['message']}")
    
    if info:
        print("\n🔵 INFO:")
        for alert in info:
            print(f"  ℹ️  {alert['title']}")
            print(f"     {alert['message']}")
    
    print(f"\n{'='*120}\n")


def main():
    """Main function"""
    print("\n" + "="*120)
    print("🔔 CHECKING STRATEGY PERFORMANCE ALERTS")
    print("="*120)
    
    alerts = check_strategy_alerts()
    save_alerts(alerts)
    print_alerts(alerts)
    
    return alerts


if __name__ == "__main__":
    main()






