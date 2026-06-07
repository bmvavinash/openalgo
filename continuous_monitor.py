#!/usr/bin/env python3
"""
Continuous System Monitor
Monitors server, execution engine, strategies, orders, and trades
Runs continuously and reports activity every 5-10 minutes
"""
import sys
import time
from pathlib import Path
from datetime import datetime, date, timedelta
import pytz
import json

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.sandbox_db import SandboxOrders, SandboxTrades, db_session as sandbox_db_session
from database.settings_db import get_analyze_mode, get_data_mode_settings
from utils.logging import get_logger

logger = get_logger(__name__)
IST = pytz.timezone('Asia/Kolkata')

class SystemMonitor:
    def __init__(self, check_interval=300):  # 5 minutes default
        self.check_interval = check_interval
        self.start_time = datetime.now(IST)
        self.last_order_count = 0
        self.last_trade_count = 0
        self.check_count = 0
        self.errors_found = []
        
    def check_server_status(self):
        """Check if server is responding"""
        try:
            import requests
            response = requests.get('http://127.0.0.1:5000/', timeout=5)
            return response.status_code == 200, f"Server OK (HTTP {response.status_code})"
        except Exception as e:
            return False, f"Server Error: {str(e)}"
    
    def check_execution_engine(self):
        """Check execution engine status from logs"""
        try:
            log_file = Path('log') / f"openalgo_{date.today().strftime('%Y-%m-%d')}.log"
            if not log_file.exists():
                return False, "Log file not found"
            
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if "Sandbox Execution Engine thread started" in content:
                    # Check if there are recent execution logs (within last 10 minutes)
                    lines = content.split('\n')
                    recent_lines = [l for l in lines[-100:] if "execution" in l.lower() or "Execution" in l]
                    if recent_lines:
                        return True, "Execution engine running (recent activity found)"
                    return True, "Execution engine started (no recent activity)"
                return False, "Execution engine not found in logs"
        except Exception as e:
            return False, f"Error checking logs: {str(e)}"
    
    def get_today_stats(self):
        """Get today's orders and trades"""
        try:
            today = date.today()
            start = IST.localize(datetime.combine(today, datetime.min.time()))
            
            orders = sandbox_db_session.query(SandboxOrders).filter(
                SandboxOrders.order_timestamp >= start
            ).all()
            
            trades = sandbox_db_session.query(SandboxTrades).filter(
                SandboxTrades.trade_timestamp >= start
            ).all()
            
            # Get recent orders (last 10 minutes)
            recent_threshold = datetime.now(IST) - timedelta(minutes=10)
            recent_orders = [o for o in orders if o.order_timestamp >= recent_threshold]
            recent_trades = [t for t in trades if t.trade_timestamp >= recent_threshold]
            
            return {
                'total_orders': len(orders),
                'total_trades': len(trades),
                'recent_orders': len(recent_orders),
                'recent_trades': len(recent_trades),
                'new_orders': len(orders) - self.last_order_count,
                'new_trades': len(trades) - self.last_trade_count,
                'orders': orders[-5:] if orders else [],  # Last 5 orders
                'trades': trades[-5:] if trades else []   # Last 5 trades
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_orders': 0,
                'total_trades': 0,
                'recent_orders': 0,
                'recent_trades': 0,
                'new_orders': 0,
                'new_trades': 0,
                'orders': [],
                'trades': []
            }
    
    def check_strategy_logs(self):
        """Check latest strategy logs for activity"""
        try:
            log_dir = Path('log') / 'strategies'
            if not log_dir.exists():
                return [], "No strategy log directory"
            
            today_str = date.today().strftime('%Y%m%d')
            log_files = list(log_dir.glob(f'*{today_str}*.log'))
            
            if not log_files:
                return [], "No strategy logs found for today"
            
            # Get most recently updated logs
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            recent_logs = []
            
            for log_file in log_files[:5]:  # Check top 5 most recent
                try:
                    stat = log_file.stat()
                    if stat.st_size > 0:
                        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            if lines:
                                last_line = lines[-1].strip()
                                recent_logs.append({
                                    'file': log_file.name,
                                    'last_line': last_line,
                                    'size': stat.st_size,
                                    'updated': datetime.fromtimestamp(stat.st_mtime, IST)
                                })
                except Exception as e:
                    continue
            
            return recent_logs, f"Found {len(recent_logs)} active strategy logs"
        except Exception as e:
            return [], f"Error checking logs: {str(e)}"
    
    def check_for_errors(self):
        """Check logs for errors"""
        try:
            log_file = Path('log') / f"openalgo_{date.today().strftime('%Y-%m-%d')}.log"
            if not log_file.exists():
                return []
            
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Check last 200 lines for errors
                recent_lines = lines[-200:]
                errors = []
                for i, line in enumerate(recent_lines):
                    if 'ERROR' in line or 'CRITICAL' in line:
                        # Get context (2 lines before and after)
                        start = max(0, i - 2)
                        end = min(len(recent_lines), i + 3)
                        context = ''.join(recent_lines[start:end])
                        errors.append({
                            'line': line.strip(),
                            'context': context,
                            'timestamp': line.split(']')[0] if ']' in line else 'Unknown'
                        })
                
                return errors[-10:]  # Last 10 errors
        except Exception as e:
            return []
    
    def check_strategy_configs(self):
        """Check active strategies"""
        try:
            config_file = Path('strategies') / 'strategy_configs.json'
            if not config_file.exists():
                return [], "Config file not found"
            
            with open(config_file, 'r', encoding='utf-8') as f:
                configs = json.load(f)
            
            active = {k: v for k, v in configs.items() if v.get('is_running', False)}
            return list(active.items()), f"{len(active)} active strategies"
        except Exception as e:
            return [], f"Error: {str(e)}"
    
    def print_report(self):
        """Print monitoring report"""
        current_time = datetime.now(IST)
        uptime = current_time - self.start_time
        
        print("\n" + "="*80)
        print(f"SYSTEM MONITORING REPORT - {current_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
        print(f"Uptime: {uptime}")
        print(f"Check #{self.check_count}")
        print("="*80)
        
        # Server Status
        server_ok, server_msg = self.check_server_status()
        print(f"\n[1] Server Status: {'[OK]' if server_ok else '[ERROR]'} {server_msg}")
        
        # Execution Engine
        engine_ok, engine_msg = self.check_execution_engine()
        print(f"[2] Execution Engine: {'[OK]' if engine_ok else '[WARNING]'} {engine_msg}")
        
        # Settings
        analyze_mode = get_analyze_mode()
        data_settings = get_data_mode_settings()
        print(f"[3] Mode: {'[PAPER TRADING]' if analyze_mode else '[LIVE]'} | Data: {data_settings.get('data_mode', 'live')}")
        
        # Today's Stats
        stats = self.get_today_stats()
        print(f"\n[4] Today's Activity:")
        print(f"    Total Orders: {stats['total_orders']} (+{stats['new_orders']} new)")
        print(f"    Total Trades: {stats['total_trades']} (+{stats['new_trades']} new)")
        print(f"    Recent (10min): {stats['recent_orders']} orders, {stats['recent_trades']} trades")
        
        # Recent Orders
        if stats['orders']:
            print(f"\n[5] Recent Orders (Last 5):")
            for order in stats['orders']:
                print(f"    {order.order_timestamp.strftime('%H:%M:%S')} - {order.symbol} {order.action} {order.quantity} @ {order.price or 'MARKET'} - Status: {order.order_status}")
        
        # Recent Trades
        if stats['trades']:
            print(f"\n[6] Recent Trades (Last 5):")
            for trade in stats['trades']:
                print(f"    {trade.trade_timestamp.strftime('%H:%M:%S')} - {trade.symbol} {trade.action} {trade.quantity} @ {trade.price}")
        
        # Strategy Logs
        strategy_logs, log_msg = self.check_strategy_logs()
        print(f"\n[7] Strategy Logs: {log_msg}")
        if strategy_logs:
            print(f"    Most Recent Activity:")
            for log_info in strategy_logs[:3]:
                time_str = log_info['updated'].strftime('%H:%M:%S')
                print(f"    [{time_str}] {log_info['file']}: {log_info['last_line'][:80]}")
        
        # Active Strategies
        active_strategies, strat_msg = self.check_strategy_configs()
        print(f"\n[8] Active Strategies: {strat_msg}")
        if active_strategies:
            options_count = sum(1 for _, v in active_strategies if v.get('strategy_type') == 'options')
            intraday_count = sum(1 for _, v in active_strategies if v.get('strategy_type') == 'intraday')
            print(f"    Options: {options_count} | Intraday: {intraday_count} | Others: {len(active_strategies) - options_count - intraday_count}")
        
        # Errors
        errors = self.check_for_errors()
        if errors:
            print(f"\n[9] Recent Errors: {len(errors)} found")
            for error in errors[-3:]:  # Show last 3 errors
                print(f"    [{error['timestamp']}] {error['line'][:100]}")
        else:
            print(f"\n[9] Errors: None found")
        
        print("\n" + "="*80)
        print(f"Next check in {self.check_interval} seconds ({self.check_interval//60} minutes)")
        print("="*80 + "\n")
        
        # Update counters
        self.last_order_count = stats['total_orders']
        self.last_trade_count = stats['total_trades']
        self.check_count += 1
    
    def run(self):
        """Run continuous monitoring"""
        print("\n" + "="*80)
        print("CONTINUOUS SYSTEM MONITOR STARTED")
        print(f"Check Interval: {self.check_interval} seconds ({self.check_interval//60} minutes)")
        print(f"Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
        print("="*80)
        print("\nPress Ctrl+C to stop monitoring\n")
        
        try:
            while True:
                self.print_report()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
            print(f"Total checks performed: {self.check_count}")
            print(f"Monitoring duration: {datetime.now(IST) - self.start_time}")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Continuous System Monitor')
    parser.add_argument('--interval', type=int, default=300, help='Check interval in seconds (default: 300 = 5 minutes)')
    parser.add_argument('--once', action='store_true', help='Run once and exit (for testing)')
    
    args = parser.parse_args()
    
    monitor = SystemMonitor(check_interval=args.interval)
    
    if args.once:
        monitor.print_report()
    else:
        monitor.run()
