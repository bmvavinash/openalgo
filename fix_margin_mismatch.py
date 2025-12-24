#!/usr/bin/env python3
"""
Fix margin mismatch by releasing margin from closed positions
"""
import sys
from pathlib import Path
from decimal import Decimal

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.sandbox_db import SandboxPositions, SandboxFunds, db_session
from database.auth_db import verify_api_key
from sandbox.fund_manager import FundManager

def fix_margin_mismatch(user_id=None, api_key=None, dry_run=True):
    """Fix margin mismatch by releasing margin from closed positions"""
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
        print(f"FIXING MARGIN MISMATCH FOR USER: {user_id}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE FIX'}")
        print(f"{'='*80}\n")
        
        # Get positions with zero quantity but margin still blocked
        zero_qty_positions = SandboxPositions.query.filter(
            SandboxPositions.user_id == user_id,
            SandboxPositions.quantity == 0,
            SandboxPositions.margin_blocked > 0
        ).all()
        
        # Check for orphaned margin (margin in funds but not in positions)
        all_positions = SandboxPositions.query.filter(
            SandboxPositions.user_id == user_id
        ).all()
        
        total_position_margin = sum(
            (pos.margin_blocked or Decimal('0.00')) 
            for pos in all_positions
        )
        
        funds = SandboxFunds.query.filter_by(user_id=user_id).first()
        if funds:
            orphaned_margin = funds.used_margin - total_position_margin
            if orphaned_margin > Decimal('0.01'):
                print(f"[WARNING] Found orphaned margin: Rs {float(orphaned_margin):,.2f}")
                print(f"   Funds.used_margin:     Rs {float(funds.used_margin):>15,.2f}")
                print(f"   Sum of position margins: Rs {float(total_position_margin):>15,.2f}")
                print(f"   Orphaned margin:        Rs {float(orphaned_margin):>15,.2f}\n")
        
        if not zero_qty_positions and orphaned_margin <= Decimal('0.01'):
            print("[OK] No margin issues found")
            return
        
        print(f"Found {len(zero_qty_positions)} position(s) with zero quantity but margin still blocked:\n")
        print(f"{'Symbol':<25} {'Exchange':<10} {'Product':<8} {'Margin Blocked':<18}")
        print("-" * 65)
        
        total_margin_to_release = Decimal('0.00')
        for pos in zero_qty_positions:
            margin = pos.margin_blocked or Decimal('0.00')
            total_margin_to_release += margin
            print(f"{pos.symbol:<25} {pos.exchange:<10} {pos.product:<8} Rs{float(margin):>15,.2f}")
        
        print("-" * 65)
        print(f"{'TOTAL MARGIN TO RELEASE':<25} {'':<10} {'':<8} Rs{float(total_margin_to_release):>15,.2f}\n")
        
        # Get current fund status and check for orphaned margin
        funds = SandboxFunds.query.filter_by(user_id=user_id).first()
        orphaned_margin = Decimal('0.00')
        if funds:
            all_positions = SandboxPositions.query.filter(
                SandboxPositions.user_id == user_id
            ).all()
            total_position_margin = sum(
                (pos.margin_blocked or Decimal('0.00')) 
                for pos in all_positions
            )
            orphaned_margin = funds.used_margin - total_position_margin
            
            print(f"Current Used Margin:    Rs {float(funds.used_margin):>15,.2f}")
            print(f"Sum of Position Margins: Rs {float(total_position_margin):>15,.2f}")
            print(f"Orphaned Margin:         Rs {float(orphaned_margin):>15,.2f}")
            if zero_qty_positions:
                print(f"Zero-Qty Margin:        Rs {float(total_margin_to_release):>15,.2f}")
            print(f"Expected Used Margin:    Rs {float(total_position_margin):>15,.2f}\n")
        
        if dry_run:
            print("[DRY RUN] No changes made. Run with dry_run=False to apply fixes.")
            return
        
        # Apply fixes
        print("Applying fixes...")
        fund_manager = FundManager(user_id)
        
        # Fix zero-qty positions with margin
        for pos in zero_qty_positions:
            margin_to_release = pos.margin_blocked or Decimal('0.00')
            if margin_to_release > 0:
                # Release margin
                success, message = fund_manager.release_margin(margin_to_release, Decimal('0.00'))
                if success:
                    # Clear margin_blocked from position
                    pos.margin_blocked = Decimal('0.00')
                    print(f"[OK] Released Rs {float(margin_to_release):,.2f} margin from {pos.symbol} {pos.exchange} {pos.product}")
                else:
                    print(f"[ERROR] Failed to release margin from {pos.symbol}: {message}")
        
        # Fix orphaned margin (margin in funds but not tied to any position)
        if funds and orphaned_margin > Decimal('0.01'):
            print(f"\nReleasing orphaned margin: Rs {float(orphaned_margin):,.2f}")
            # Use fund_manager to properly release margin
            success, message = fund_manager.release_margin(orphaned_margin, Decimal('0.00'), "Orphaned margin cleanup")
            if success:
                print(f"[OK] Released orphaned margin: Rs {float(orphaned_margin):,.2f}")
            else:
                print(f"[ERROR] Failed to release orphaned margin: {message}")
                # Fallback: direct release
                funds.used_margin -= orphaned_margin
                funds.available_balance += orphaned_margin
                db_session.commit()
                print(f"[OK] Released orphaned margin directly: Rs {float(orphaned_margin):,.2f}")
        
        # Commit changes
        db_session.commit()
        
        # Verify fix
        funds = SandboxFunds.query.filter_by(user_id=user_id).first()
        remaining_zero_positions = SandboxPositions.query.filter(
            SandboxPositions.user_id == user_id,
            SandboxPositions.quantity == 0,
            SandboxPositions.margin_blocked > 0
        ).count()
        
        print(f"\n{'='*80}")
        print("VERIFICATION")
        print(f"{'='*80}")
        print(f"Remaining zero-qty positions with margin: {remaining_zero_positions}")
        if funds:
            print(f"Current Used Margin:    Rs {float(funds.used_margin):>15,.2f}")
            print(f"Available Balance:     Rs {float(funds.available_balance):>15,.2f}")
        
        if remaining_zero_positions == 0:
            print("\n[SUCCESS] All margin mismatches fixed!")
        else:
            print(f"\n[WARNING] Still {remaining_zero_positions} positions with margin issues")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db_session.rollback()
    finally:
        db_session.remove()

if __name__ == "__main__":
    import os
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix margin mismatch')
    parser.add_argument('--user-id', type=str, help='User ID')
    parser.add_argument('--api-key', type=str, help='API Key')
    parser.add_argument('--apply', action='store_true', help='Apply fixes (default is dry run)')
    
    args = parser.parse_args()
    
    user_id = args.user_id or os.getenv('USER_ID', 'avinash')
    api_key = args.api_key or os.getenv('API_KEY')
    dry_run = not args.apply
    
    fix_margin_mismatch(user_id=user_id, api_key=api_key, dry_run=dry_run)

