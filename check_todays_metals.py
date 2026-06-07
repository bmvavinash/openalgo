#!/usr/bin/env python3
"""
Quick script to check today's metals-related details.
Run: python check_todays_metals.py
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from database.metals_db import (
    init_db,
    MetalsStrategy,
    MetalsTrade,
    MetalsBacktest,
    get_user_metals_strategies,
    get_open_metals_trades,
    get_trade_history,
)
from database.user_db import User


def main():
    init_db()
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    today_str = ist.strftime('%Y-%m-%d')
    
    print("=" * 60)
    print(f"METALS SUMMARY - {today_str} ({ist.strftime('%A')})")
    print("=" * 60)
    
    # Get all users
    users = User.query.all()
    if not users:
        print("No users found.")
        return
    
    for user in users:
        user_id = user.username
        print(f"\n--- User: {user_id} ---")
        
        strategies = get_user_metals_strategies(user_id)
        print(f"  Strategies: {len(strategies)}")
        
        for s in strategies:
            status = "ACTIVE" if s.is_active else "Inactive"
            inst = getattr(s, 'instrument_type', None) or 'MCX'
            print(f"    - {s.name} | {s.metal_type} | {inst} | {status}")
        
        # Open trades
        open_trades = []
        for s in strategies:
            for t in get_open_metals_trades(strategy_id=s.id):
                open_trades.append(t)
        print(f"  Open Positions: {len(open_trades)}")
        for t in open_trades:
            sl = getattr(t, 'current_stop_loss', None) or getattr(t, 'initial_stop_loss', '-')
            print(f"    - {t.metal_type} {t.action} @ {t.entry_price} (SL: {sl})")
        
        # Today's trades
        today_start = datetime.strptime(today_str, '%Y-%m-%d')
        today_end = today_start + timedelta(days=1)
        today_trades = get_trade_history(user_id=user_id, start_date=today_start, end_date=today_end)
        print(f"  Today's Trades: {len(today_trades)}")
        for t in today_trades[:10]:
            exit_str = str(t.exit_time)[:19] if t.exit_time else '-'
            exit_price = t.exit_price if t.exit_price is not None else '-'
            pnl_str = f"P&L: {t.pnl:.2f}" if t.pnl is not None else ""
            print(f"    - {t.metal_type} {t.action} Entry:{t.entry_price} Exit:{exit_price} {pnl_str} | {exit_str}")
        if len(today_trades) > 10:
            print(f"    ... and {len(today_trades) - 10} more")
    
    print("\n" + "=" * 60)
    print("Note: Today is Sunday - Indian markets (NSE, MCX) are closed.")
    print("Live quotes/signals will not update until market opens.")
    print("=" * 60)


if __name__ == "__main__":
    main()
