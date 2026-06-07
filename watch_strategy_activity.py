#!/usr/bin/env python3
"""
Watch Strategy Activity
Monitors strategy logs for activity, order placement, and errors
"""
import sys
import time
from pathlib import Path
from datetime import datetime, date
import pytz

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.logging import get_logger

logger = get_logger(__name__)
IST = pytz.timezone('Asia/Kolkata')

def watch_strategy_logs(watch_interval=60):
    """
    Watch strategy logs for activity
    
    Args:
        watch_interval: Check logs every N seconds
    """
    log_dir = Path('log') / 'strategies'
    today_str = date.today().strftime('%Y%m%d')
    
    # Track which logs we've seen
    seen_logs = set()
    last_positions = {}  # Track file positions to detect new content
    
    print("\n" + "="*80)
    print("STRATEGY ACTIVITY WATCHER")
    print(f"Watching logs in: {log_dir}")
    print(f"Check interval: {watch_interval} seconds")
    print("Press Ctrl+C to stop")
    print("="*80 + "\n")
    
    try:
        while True:
            # Find today's log files
            log_files = list(log_dir.glob(f'*{today_str}*.log'))
            
            if not log_files:
                print(f"[{datetime.now(IST).strftime('%H:%M:%S')}] No strategy logs found for today")
                time.sleep(watch_interval)
                continue
            
            # Check each log file for new content
            for log_file in log_files:
                try:
                    if not log_file.exists() or log_file.stat().st_size == 0:
                        continue
                    
                    # Get current position
                    current_pos = log_file.stat().st_size
                    last_pos = last_positions.get(log_file.name, 0)
                    
                    # If file has grown, read new content
                    if current_pos > last_pos:
                        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                            f.seek(last_pos)
                            new_lines = f.readlines()
                            
                            if new_lines:
                                print(f"\n[{datetime.now(IST).strftime('%H:%M:%S')}] === {log_file.name} ===")
                                for line in new_lines:
                                    line = line.strip()
                                    if line:
                                        # Highlight important events
                                        if 'ERROR' in line or 'FAILED' in line:
                                            print(f"  [ERROR] {line}")
                                        elif 'order' in line.lower() or 'Order' in line:
                                            print(f"  [ORDER] {line}")
                                        elif 'trade' in line.lower() or 'Trade' in line:
                                            print(f"  [TRADE] {line}")
                                        elif 'Placing' in line or 'placed' in line.lower():
                                            print(f"  [ACTION] {line}")
                                        else:
                                            print(f"  {line}")
                        
                        last_positions[log_file.name] = current_pos
                        seen_logs.add(log_file.name)
                
                except Exception as e:
                    logger.debug(f"Error reading {log_file.name}: {e}")
                    continue
            
            # Show summary every 5 checks
            if len(seen_logs) > 0:
                print(f"\n[{datetime.now(IST).strftime('%H:%M:%S')}] Monitoring {len(seen_logs)} strategy log files...")
            
            time.sleep(watch_interval)
    
    except KeyboardInterrupt:
        print("\n\nWatcher stopped by user")
        print(f"Monitored {len(seen_logs)} log files")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Watch Strategy Activity')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds (default: 60)')
    
    args = parser.parse_args()
    
    watch_strategy_logs(watch_interval=args.interval)




