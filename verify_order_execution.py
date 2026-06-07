#!/usr/bin/env python3
"""
Order Execution Verification
Monitors orders and verifies they execute correctly
Checks order status, execution time, and trade creation
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.sandbox_db import SandboxOrders, SandboxTrades, db_session
from utils.logging import get_logger

logger = get_logger(__name__)
IST = pytz.timezone('Asia/Kolkata')

def verify_order_execution(order_id=None, symbol=None, check_recent_minutes=10):
    """
    Verify order execution
    
    Args:
        order_id: Specific order ID to check (optional)
        symbol: Symbol to check (optional)
        check_recent_minutes: Check orders from last N minutes
    
    Returns:
        dict with verification results
    """
    results = {
        'timestamp': datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST'),
        'orders_checked': 0,
        'orders_pending': 0,
        'orders_executed': 0,
        'orders_cancelled': 0,
        'execution_issues': [],
        'recent_orders': [],
        'execution_times': []
    }
    
    try:
        # Build query
        query = db_session.query(SandboxOrders)
        
        if order_id:
            query = query.filter(SandboxOrders.orderid == order_id)
        elif symbol:
            query = query.filter(SandboxOrders.symbol == symbol)
        
        # Check recent orders
        if not order_id:
            recent_threshold = datetime.now(IST) - timedelta(minutes=check_recent_minutes)
            query = query.filter(SandboxOrders.order_timestamp >= recent_threshold)
        
        orders = query.order_by(SandboxOrders.order_timestamp.desc()).limit(50).all()
        results['orders_checked'] = len(orders)
        
        for order in orders:
            order_info = {
                'orderid': order.orderid,
                'symbol': order.symbol,
                'action': order.action,
                'quantity': order.quantity,
                'price_type': order.price_type,
                'status': order.order_status,
                'created': order.order_timestamp.strftime('%H:%M:%S'),
                'strategy': order.strategy
            }
            
            results['recent_orders'].append(order_info)
            
            # Count by status
            if order.order_status == 'open':
                results['orders_pending'] += 1
                
                # Check if order has been pending too long (more than 5 minutes for MARKET orders)
                if order.price_type == 'MARKET':
                    pending_time = datetime.now(IST) - order.order_timestamp.replace(tzinfo=None)
                    if pending_time > timedelta(minutes=5):
                        results['execution_issues'].append({
                            'orderid': order.orderid,
                            'issue': f'MARKET order pending for {pending_time.total_seconds()/60:.1f} minutes',
                            'symbol': order.symbol
                        })
            elif order.order_status == 'complete':
                results['orders_executed'] += 1
                
                # Verify trade was created
                trade = db_session.query(SandboxTrades).filter_by(orderid=order.orderid).first()
                if trade:
                    execution_time = trade.trade_timestamp - order.order_timestamp.replace(tzinfo=None)
                    results['execution_times'].append({
                        'orderid': order.orderid,
                        'execution_time_seconds': execution_time.total_seconds(),
                        'symbol': order.symbol
                    })
                else:
                    results['execution_issues'].append({
                        'orderid': order.orderid,
                        'issue': 'Order marked complete but no trade found',
                        'symbol': order.symbol
                    })
            elif order.order_status == 'cancelled':
                results['orders_cancelled'] += 1
        
        return results
        
    except Exception as e:
        logger.error(f"Error verifying orders: {e}")
        results['error'] = str(e)
        return results

def print_verification_report(results):
    """Print verification report"""
    print("\n" + "="*80)
    print(f"ORDER EXECUTION VERIFICATION - {results['timestamp']}")
    print("="*80)
    
    print(f"\nOrders Checked: {results['orders_checked']}")
    print(f"  - Pending: {results['orders_pending']}")
    print(f"  - Executed: {results['orders_executed']}")
    print(f"  - Cancelled: {results['orders_cancelled']}")
    
    if results['execution_times']:
        avg_time = sum(t['execution_time_seconds'] for t in results['execution_times']) / len(results['execution_times'])
        print(f"\nExecution Times:")
        print(f"  - Average: {avg_time:.2f} seconds")
        print(f"  - Fastest: {min(t['execution_time_seconds'] for t in results['execution_times']):.2f} seconds")
        print(f"  - Slowest: {max(t['execution_time_seconds'] for t in results['execution_times']):.2f} seconds")
    
    if results['execution_issues']:
        print(f"\n[WARNING] Execution Issues Found: {len(results['execution_issues'])}")
        for issue in results['execution_issues']:
            print(f"  - {issue['orderid']} ({issue['symbol']}): {issue['issue']}")
    else:
        print(f"\n[OK] No execution issues found")
    
    if results['recent_orders']:
        print(f"\nRecent Orders (Last 10):")
        for order in results['recent_orders'][:10]:
            print(f"  [{order['created']}] {order['symbol']} {order['action']} {order['quantity']} ({order['price_type']}) - Status: {order['status']}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify Order Execution')
    parser.add_argument('--order-id', type=str, help='Check specific order ID')
    parser.add_argument('--symbol', type=str, help='Check orders for specific symbol')
    parser.add_argument('--minutes', type=int, default=10, help='Check orders from last N minutes (default: 10)')
    
    args = parser.parse_args()
    
    results = verify_order_execution(
        order_id=args.order_id,
        symbol=args.symbol,
        check_recent_minutes=args.minutes
    )
    
    print_verification_report(results)




