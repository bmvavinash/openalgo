#!/usr/bin/env python3
"""
Check for open positions and verify margin calculation
"""
import sys
from pathlib import Path
from decimal import Decimal

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.sandbox_db import SandboxPositions, SandboxFunds, db_session
from database.auth_db import verify_api_key
from sqlalchemy import func

def check_open_positions(user_id=None, api_key=None):
    """Check open positions and margin calculation"""
    try:
        # Get user_id from api_key if provided
        if api_key and not user_id:
            user_id = verify_api_key(api_key)
            if not user_id:
                print(f"ERROR: Invalid API key")
                return
        
        if not user_id:
            print("ERROR: Either user_id or api_key must be provided")
            return
        
        print(f"\n{'='*80}")
        print(f"CHECKING OPEN POSITIONS FOR USER: {user_id}")
        print(f"{'='*80}\n")
        
        # Get all positions with non-zero quantity
        open_positions = SandboxPositions.query.filter(
            SandboxPositions.user_id == user_id,
            SandboxPositions.quantity != 0
        ).all()
        
        if not open_positions:
            print("[OK] No open positions found")
        else:
            print(f"Found {len(open_positions)} open position(s):\n")
            print(f"{'Symbol':<20} {'Exchange':<10} {'Product':<8} {'Qty':<10} {'Avg Price':<15} {'Margin Blocked':<18} {'P&L':<15}")
            print("-" * 100)
            
            total_margin_blocked = Decimal('0.00')
            total_unrealized_pnl = Decimal('0.00')
            
            for pos in open_positions:
                margin = pos.margin_blocked or Decimal('0.00')
                pnl = pos.pnl or Decimal('0.00')
                total_margin_blocked += margin
                total_unrealized_pnl += pnl
                
                print(f"{pos.symbol:<20} {pos.exchange:<10} {pos.product:<8} {pos.quantity:<10} "
                      f"Rs{float(pos.average_price):>12,.2f} Rs{float(margin):>15,.2f} Rs{float(pnl):>12,.2f}")
            
            print("-" * 100)
            print(f"{'TOTAL':<20} {'':<10} {'':<8} {'':<10} {'':<15} "
                  f"Rs{float(total_margin_blocked):>15,.2f} Rs{float(total_unrealized_pnl):>12,.2f}")
        
        # Get fund data
        funds = SandboxFunds.query.filter_by(user_id=user_id).first()
        if funds:
            print(f"\n{'='*80}")
            print("FUND SUMMARY")
            print(f"{'='*80}")
            print(f"Available Balance:    Rs {float(funds.available_balance):>15,.2f}")
            print(f"Used Margin:          Rs {float(funds.used_margin):>15,.2f}")
            print(f"Realized P&L:         Rs {float(funds.realized_pnl):>15,.2f}")
            print(f"Unrealized P&L:       Rs {float(funds.unrealized_pnl):>15,.2f}")
            print(f"Total P&L:            Rs {float(funds.total_pnl):>15,.2f}")
            
            # Check for mismatch
            calculated_margin = sum(
                (pos.margin_blocked or Decimal('0.00')) 
                for pos in open_positions
            )
            
            margin_diff = funds.used_margin - calculated_margin
            
            print(f"\n{'='*80}")
            print("MARGIN VERIFICATION")
            print(f"{'='*80}")
            print(f"Funds.used_margin:     Rs {float(funds.used_margin):>15,.2f}")
            print(f"Sum of positions:      Rs {float(calculated_margin):>15,.2f}")
            print(f"Difference:            Rs {float(margin_diff):>15,.2f}")
            
            if abs(margin_diff) > Decimal('0.01'):
                print(f"\n[WARNING] Margin mismatch detected!")
                print(f"   This could indicate:")
                print(f"   1. Positions not properly closed")
                print(f"   2. Margin not released when positions closed")
                print(f"   3. Orphaned margin records")
            else:
                print(f"\n[OK] Margin calculation matches")
        
        # Check for positions with zero quantity but margin still blocked
        zero_qty_positions = SandboxPositions.query.filter(
            SandboxPositions.user_id == user_id,
            SandboxPositions.quantity == 0,
            SandboxPositions.margin_blocked > 0
        ).all()
        
        if zero_qty_positions:
            print(f"\n{'='*80}")
            print(f"[WARNING] FOUND {len(zero_qty_positions)} POSITION(S) WITH ZERO QUANTITY BUT MARGIN STILL BLOCKED")
            print(f"{'='*80}\n")
            print(f"{'Symbol':<20} {'Exchange':<10} {'Product':<8} {'Margin Blocked':<18}")
            print("-" * 60)
            for pos in zero_qty_positions:
                print(f"{pos.symbol:<20} {pos.exchange:<10} {pos.product:<8} Rs{float(pos.margin_blocked):>15,.2f}")
            print(f"\nThese positions should have their margin released!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.remove()

if __name__ == "__main__":
    import os
    # Try to get user_id from environment or use default
    user_id = os.getenv('USER_ID', 'avinash')  # Default to 'avinash' based on logs
    api_key = os.getenv('API_KEY')
    
    check_open_positions(user_id=user_id, api_key=api_key)

