#!/usr/bin/env python3
"""
Setup Daily Analysis Scheduler
Integrates daily strategy analysis with Flask app scheduler
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from utils.logging import get_logger

logger = get_logger(__name__)

def setup_daily_analysis_scheduler(scheduler=None):
    """
    Setup daily analysis job to run after market closure
    
    Args:
        scheduler: Existing BackgroundScheduler instance (optional)
                   If None, creates a new one
    
    Returns:
        BackgroundScheduler instance
    """
    if scheduler is None:
        scheduler = BackgroundScheduler(
            timezone=pytz.timezone('Asia/Kolkata'),
            job_defaults={
                'coalesce': True,
                'misfire_grace_time': 300,
                'max_instances': 1
            }
        )
    
    def run_daily_analysis():
        """Run daily strategy analysis"""
        try:
            logger.info("Starting daily strategy performance analysis...")
            
            # Import here to avoid circular imports
            from daily_strategy_analyzer import analyze_today_performance
            
            # Run analysis
            analyze_today_performance(
                symbol='NIFTY',
                exchange='NSE_INDEX',
                strike_int=50
            )
            
            logger.info("Daily strategy performance analysis completed")
        except Exception as e:
            logger.error(f"Error running daily analysis: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Schedule job to run at 3:35 PM IST (after market close at 3:30 PM)
    # Runs Monday to Friday only
    scheduler.add_job(
        run_daily_analysis,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=15,
            minute=35,
            timezone='Asia/Kolkata'
        ),
        id='daily_strategy_analysis',
        name='Daily Strategy Performance Analysis',
        replace_existing=True
    )
    
    logger.info("Daily analysis scheduler configured: Runs at 3:35 PM IST (Mon-Fri)")
    
    return scheduler

if __name__ == "__main__":
    # Test scheduler setup
    scheduler = setup_daily_analysis_scheduler()
    scheduler.start()
    
    print("Scheduler started. Press Ctrl+C to stop.")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("Scheduler stopped.")

