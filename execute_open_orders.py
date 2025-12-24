#!/usr/bin/env python
"""Execute all open orders in sandbox"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.sandbox_db import SandboxOrders, db_session
from sandbox.execution_engine import ExecutionEngine
from decimal import Decimal
from datetime import datetime
import pytz

def main():
    print(f"[{datetime.now()}] Executing all open orders...")
    
    engine = ExecutionEngine()
    orders = SandboxOrders.query.filter_by(order_status='open').all()
    
    print(f"Found {len(orders)} open orders")
    
    executed = 0
    failed = 0
    
    for order in orders:
        try:
            # Get fallback price from stored order price
            fallback_price = float(order.price) if order.price else None
            
            # Fetch quote with fallback
            quote = engine._fetch_quote(order.symbol, order.exchange, fallback_price)
            
            if quote:
                # Process the order
                engine._process_order(order, quote)
                db_session.commit()
                executed += 1
                print(f"  [OK] Executed order {order.orderid}: {order.symbol} {order.action} {order.quantity}")
            else:
                # If no quote and no fallback, skip
                if not fallback_price:
                    print(f"  [SKIP] Order {order.orderid}: No quote and no fallback price")
                    failed += 1
                else:
                    # Use fallback directly
                    quote = {'ltp': fallback_price, 'bid': fallback_price, 'ask': fallback_price}
                    engine._process_order(order, quote)
                    db_session.commit()
                    executed += 1
                    print(f"  [OK] Executed order {order.orderid} using fallback price {fallback_price}")
        except Exception as e:
            print(f"  [ERROR] Failed to execute order {order.orderid}: {e}")
            failed += 1
            db_session.rollback()
    
    print(f"\n[{datetime.now()}] Execution complete: {executed} executed, {failed} failed")
    
    # Check final status
    final_open = SandboxOrders.query.filter_by(order_status='open').count()
    final_complete = SandboxOrders.query.filter_by(order_status='complete').count()
    print(f"Final status: Open={final_open}, Complete={final_complete}")

if __name__ == "__main__":
    main()


