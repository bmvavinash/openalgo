#!/usr/bin/env python3
"""
System Status Checker
Checks server, strategies, execution engine, and trades
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.sandbox_db import SandboxOrders, SandboxTrades, SandboxPositions, db_session
from sandbox.execution_thread import is_execution_engine_running, get_execution_engine_status
from database.settings_db import get_analyze_mode
from datetime import datetime, timedelta
import pytz

def check_system_status():
    """Comprehensive system status check"""
    print("\n" + "="*60)
    print("SYSTEM STATUS CHECK")
    print("="*60)
    
    # 1. Check mode
    analyze_mode = get_analyze_mode()
    print(f"\n[1] Mode: {'ANALYZE/PAPER TRADING' if analyze_mode else 'LIVE TRADING'}")
    
    # 2. Check execution engine
    print("\n[2] Execution Engine:")
    exec_status = get_execution_engine_status()
    print(f"    Running: {exec_status['running']}")
    print(f"    Check Interval: {exec_status['check_interval']} seconds")
    
    # 3. Check orders
    print("\n[3] Orders:")
    total_orders = SandboxOrders.query.count()
    open_orders = SandboxOrders.query.filter_by(order_status='open').count()
    complete_orders = SandboxOrders.query.filter_by(order_status='complete').count()
    print(f"    Total Orders: {total_orders}")
    print(f"    Open Orders: {open_orders}")
    print(f"    Complete Orders: {complete_orders}")
    
    # 4. Check trades
    print("\n[4] Trades:")
    total_trades = SandboxTrades.query.count()
    today = datetime.now(pytz.timezone('Asia/Kolkata')).date()
    today_trades = SandboxTrades.query.filter(
        SandboxTrades.trade_timestamp >= datetime.combine(today, datetime.min.time()).replace(tzinfo=pytz.timezone('Asia/Kolkata'))
    ).count()
    print(f"    Total Trades: {total_trades}")
    print(f"    Today's Trades: {today_trades}")
    
    if today_trades > 0:
        recent_trades = SandboxTrades.query.filter(
            SandboxTrades.trade_timestamp >= datetime.combine(today, datetime.min.time()).replace(tzinfo=pytz.timezone('Asia/Kolkata'))
        ).order_by(SandboxTrades.trade_timestamp.desc()).limit(5).all()
        print(f"\n    Recent Trades (last 5):")
        for trade in recent_trades:
            print(f"      - {trade.symbol} {trade.action} {trade.quantity} @ {trade.price} ({trade.trade_timestamp.strftime('%H:%M:%S')})")
    
    # 5. Check positions
    print("\n[5] Positions:")
    total_positions = SandboxPositions.query.count()
    open_positions = SandboxPositions.query.filter(SandboxPositions.quantity != 0).count()
    print(f"    Total Positions: {total_positions}")
    print(f"    Open Positions: {open_positions}")
    
    # 6. Check pending orders details
    if open_orders > 0:
        print("\n[6] Pending Orders Details:")
        pending = SandboxOrders.query.filter_by(order_status='open').limit(10).all()
        for order in pending:
            print(f"      - {order.symbol} {order.action} {order.quantity} {order.price_type} @ {order.price} (Status: {order.order_status})")
    
    print("\n" + "="*60)
    print("STATUS CHECK COMPLETE")
    print("="*60 + "\n")
    
    return {
        'execution_engine_running': exec_status['running'],
        'open_orders': open_orders,
        'today_trades': today_trades,
        'open_positions': open_positions
    }

if __name__ == '__main__':
    try:
        status = check_system_status()
        
        # Recommendations
        if not status['execution_engine_running']:
            print("[WARNING] Execution engine is NOT running! Orders will not execute.")
            print("          Start it via: /settings/services")
        
        if status['open_orders'] > 0 and status['today_trades'] == 0:
            print("[WARNING] There are open orders but no trades today!")
            print("          Check execution engine and quotes service.")
        
    except Exception as e:
        print(f"\n[ERROR] Status check failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)






