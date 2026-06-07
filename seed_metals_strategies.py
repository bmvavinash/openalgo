#!/usr/bin/env python3
"""
Seed default metals strategies (Gold & Silver) for all existing users.
Run from openalgo directory: python seed_metals_strategies.py

Adds 2 sample strategies per user if they have none, so they can view Metals in the UI.
"""

import sys
import os

# Load .env before any database imports that use DATABASE_URL
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from database.user_db import User, db_session as user_session
from database.metals_db import (
    init_db as init_metals_db,
    create_metals_strategy,
    get_user_metals_strategies,
)


# MCX: commodity, trade till 23:30 IST. ETF: NSE, trade till 15:15 IST.
DEFAULT_STRATEGIES = [
    # MCX Gold
    {
        "name": "Metals_GOLD_MCX",
        "metal_type": "GOLD",
        "exchange": "MCX",
        "instrument_type": "MCX",
        "product_type": "MIS",
        "quantity": 1,
        "trading_mode": "LONG",
        "stop_loss_type": "ADAPTIVE",
        "stop_loss_pct": 1.8,
        "trailing_stop_pct": 1.0,
        "atr_multiplier": 2.0,
        "take_profit_enabled": True,
        "take_profit_pct": 3.0,
        "start_time": "09:00",
        "end_time": "23:30",
        "sell_before_market_close": False,
        "square_off_minutes_before_close": 15,
        "telegram_alerts": True,
        "whatsapp_alerts": False,
        "is_active": False,
    },
    # MCX Silver
    {
        "name": "Metals_SILVER_MCX",
        "metal_type": "SILVER",
        "exchange": "MCX",
        "instrument_type": "MCX",
        "product_type": "MIS",
        "quantity": 1,
        "trading_mode": "LONG",
        "stop_loss_type": "ADAPTIVE",
        "stop_loss_pct": 2.2,
        "trailing_stop_pct": 1.2,
        "atr_multiplier": 2.0,
        "take_profit_enabled": True,
        "take_profit_pct": 3.5,
        "start_time": "09:00",
        "end_time": "23:30",
        "sell_before_market_close": False,
        "square_off_minutes_before_close": 15,
        "telegram_alerts": True,
        "whatsapp_alerts": False,
        "is_active": False,
    },
    # ETF Gold — market closes 3:15 PM; recommend sell before close
    {
        "name": "Metals_GOLD_ETF",
        "metal_type": "GOLD",
        "exchange": "NSE",
        "instrument_type": "ETF",
        "product_type": "MIS",
        "quantity": 1,
        "trading_mode": "LONG",
        "stop_loss_type": "ADAPTIVE",
        "stop_loss_pct": 1.5,
        "trailing_stop_pct": 1.0,
        "atr_multiplier": 2.0,
        "take_profit_enabled": True,
        "take_profit_pct": 2.5,
        "start_time": "09:15",
        "end_time": "15:15",
        "sell_before_market_close": True,
        "square_off_minutes_before_close": 15,
        "telegram_alerts": True,
        "whatsapp_alerts": False,
        "is_active": False,
    },
    # ETF Silver — market closes 3:15 PM; recommend sell before close
    {
        "name": "Metals_SILVER_ETF",
        "metal_type": "SILVER",
        "exchange": "NSE",
        "instrument_type": "ETF",
        "product_type": "MIS",
        "quantity": 1,
        "trading_mode": "LONG",
        "stop_loss_type": "ADAPTIVE",
        "stop_loss_pct": 2.0,
        "trailing_stop_pct": 1.2,
        "atr_multiplier": 2.0,
        "take_profit_enabled": True,
        "take_profit_pct": 3.0,
        "start_time": "09:15",
        "end_time": "15:15",
        "sell_before_market_close": True,
        "square_off_minutes_before_close": 15,
        "telegram_alerts": True,
        "whatsapp_alerts": False,
        "is_active": False,
    },
]


def seed_metals_strategies():
    """Create default Gold and Silver strategies for every user who has none."""
    init_metals_db()

    users = User.query.all()
    if not users:
        print("No users found in the database. Create a user by signing up first, then run this script again.")
        return

    created = 0
    for user in users:
        username = user.username
        existing = get_user_metals_strategies(username)
        if existing:
            print(f"User '{username}' already has {len(existing)} metals strategy(ies). Skipping.")
            continue

        for opts in DEFAULT_STRATEGIES:
            opts = dict(opts)
            name = opts.pop("name")
            metal_type = opts.pop("metal_type")
            strategy = create_metals_strategy(
                name=name,
                user_id=username,
                metal_type=metal_type,
                **opts
            )
            if strategy:
                created += 1
                print(f"Created: {name} for user '{username}' (metal={metal_type})")

    print(f"Done. Created {created} metals strategy(ies) for {len(users)} user(s).")
    print("Refresh the Metals page in the UI to see them.")


if __name__ == "__main__":
    seed_metals_strategies()
