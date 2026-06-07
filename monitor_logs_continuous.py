#!/usr/bin/env python3
"""
Continuous Log Monitor for Paper Trading
Monitors strategy logs continuously and displays recent activity
"""
import sys
import os
import time
from pathlib import Path
from datetime import datetime
import pytz

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

IST = pytz.timezone('Asia/Kolkata')

def get_recent_logs(log_dir, max_files=10, lines_per_file=10):
    """Get recent log entries from strategy log files"""
    if not log_dir.exists():
        return []
    
    today_str = datetime.now(IST).strftime('%Y%m%d')
    log_files = list(log_dir.glob(f'*{today_str}*.log'))
    
    if not log_files:
        return []
    
    # Sort by modification time (most recent first)
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    recent_logs = []
    for log_file in log_files[:max_files]:
        try:
            stat = log_file.stat()
            if stat.st_size > 0:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    file_lines = f.readlines()
                    if file_lines:
                        recent_logs.append({
                            'file': log_file.name,
                            'path': str(log_file),
                            'size': stat.st_size,
                            'updated': datetime.fromtimestamp(stat.st_mtime, IST),
                            'last_lines': file_lines[-lines_per_file:] if len(file_lines) > lines_per_file else file_lines
                        })
        except Exception as e:
            continue
    
    return recent_logs

def check_for_errors(log_dir):
    """Check for errors in recent logs"""
    errors = []
    today_str = datetime.now(IST).strftime('%Y%m%d')
    log_files = list(log_dir.glob(f'*{today_str}*.log'))
    
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Check last 50 lines for errors
                for line in lines[-50:]:
                    line_upper = line.upper()
                    if any(keyword in line_upper for keyword in ['ERROR', 'FAILED', 'TRACEBACK', 'EXCEPTION', 'CRITICAL']):
                        errors.append({
                            'file': log_file.name,
                            'line': line.strip(),
                            'timestamp': line.split(']')[0] if ']' in line else 'Unknown'
                        })
        except:
            pass
    
    return errors

def print_log_report(log_dir, refresh_interval=10):
    """Print continuous log monitoring report"""
    print("\n" + "="*80)
    print("CONTINUOUS LOG MONITOR - PAPER TRADING MODE")
    print("="*80)
    print(f"Started at: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"Refresh interval: {refresh_interval} seconds")
    print("Press Ctrl+C to stop monitoring")
    print("="*80 + "\n")
    
    try:
        while True:
            # Clear screen (works on Windows and Unix)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            current_time = datetime.now(IST)
            print("\n" + "="*80)
            print(f"LOG MONITOR - {current_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
            print("="*80)
            
            # Get recent logs
            recent_logs = get_recent_logs(log_dir, max_files=10, lines_per_file=5)
            
            if recent_logs:
                print(f"\n[ACTIVE LOGS] Found {len(recent_logs)} active strategy log files\n")
                
                for i, log_info in enumerate(recent_logs, 1):
                    print(f"[{i}] {log_info['file']}")
                    print(f"    Updated: {log_info['updated'].strftime('%H:%M:%S IST')} | Size: {log_info['size']} bytes")
                    print(f"    Last {len(log_info['last_lines'])} lines:")
                    for line in log_info['last_lines']:
                        line_stripped = line.strip()
                        if line_stripped:
                            # Color code errors
                            if any(keyword in line_stripped.upper() for keyword in ['ERROR', 'FAILED', 'EXCEPTION']):
                                print(f"      [ERROR] {line_stripped[:100]}")
                            elif 'WARNING' in line_stripped.upper():
                                print(f"      [WARN]  {line_stripped[:100]}")
                            else:
                                print(f"      {line_stripped[:100]}")
                    print()
            else:
                print("\n[INFO] No strategy log files found for today")
                print(f"       Looking in: {log_dir}")
                print(f"       Pattern: *{datetime.now(IST).strftime('%Y%m%d')}*.log")
            
            # Check for errors
            errors = check_for_errors(log_dir)
            if errors:
                print(f"\n[ERRORS DETECTED] Found {len(errors)} error(s) in recent logs:")
                for error in errors[:5]:  # Show first 5 errors
                    print(f"  [{error['timestamp']}] {error['file']}: {error['line'][:80]}")
            else:
                print(f"\n[STATUS] No errors detected in recent logs")
            
            print("\n" + "="*80)
            print(f"Refreshing in {refresh_interval} seconds... (Ctrl+C to stop)")
            print("="*80)
            
            time.sleep(refresh_interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        print(f"Stopped at: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    except Exception as e:
        print(f"\n[ERROR] Monitoring error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Continuous Log Monitor for Paper Trading')
    parser.add_argument('--interval', type=int, default=10, help='Refresh interval in seconds (default: 10)')
    parser.add_argument('--log-dir', type=str, default=None, help='Log directory path (default: log/strategies)')
    
    args = parser.parse_args()
    
    # Determine log directory
    if args.log_dir:
        log_dir = Path(args.log_dir)
    else:
        log_dir = PROJECT_ROOT / 'log' / 'strategies'
    
    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Monitoring logs in: {log_dir}")
    print_log_report(log_dir, refresh_interval=args.interval)












