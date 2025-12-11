"""
Schedule daily automated tasks for trading analysis
Run this script to set up daily reports and alerts
"""
import sys
from pathlib import Path
from datetime import datetime, time
import schedule
import time as time_module

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from daily_report_automation import generate_daily_report
from strategy_performance_alerts import check_strategy_alerts, save_alerts, print_alerts

def run_daily_tasks():
    """Run all daily tasks"""
    print(f"\n{'='*120}")
    print(f"🔄 RUNNING DAILY AUTOMATED TASKS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*120}")
    
    try:
        # Generate daily report
        print("\n📊 Generating daily report...")
        report_data = generate_daily_report()
        
        # Check alerts
        print("\n🔔 Checking strategy alerts...")
        alerts = check_strategy_alerts()
        save_alerts(alerts)
        print_alerts(alerts)
        
        print(f"\n✅ Daily tasks completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running daily tasks: {e}")
        import traceback
        traceback.print_exc()


def schedule_daily_tasks():
    """Schedule daily tasks to run automatically"""
    
    # Schedule to run at 3:45 PM IST (15 minutes after market close)
    schedule.every().day.at("15:45").do(run_daily_tasks)
    
    print("\n" + "="*120)
    print("⏰ DAILY TASKS SCHEDULER")
    print("="*120)
    print("\nScheduled Tasks:")
    print("  📊 Daily Report: 3:45 PM IST (after market close)")
    print("  🔔 Strategy Alerts: 3:45 PM IST")
    print("\nTasks will run automatically. Press Ctrl+C to stop.")
    print("="*120 + "\n")
    
    # Run immediately if it's after market hours
    current_time = datetime.now().time()
    if current_time >= time(15, 30):  # After market close
        print("Market is closed. Running tasks now...\n")
        run_daily_tasks()
    
    # Keep running
    while True:
        schedule.run_pending()
        time_module.sleep(60)  # Check every minute


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Schedule or run daily trading tasks')
    parser.add_argument('--run-now', action='store_true', help='Run tasks immediately instead of scheduling')
    
    args = parser.parse_args()
    
    if args.run_now:
        run_daily_tasks()
    else:
        schedule_daily_tasks()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Scheduler stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()






