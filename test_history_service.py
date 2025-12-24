#!/usr/bin/env python
"""Test history service with yfinance"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.history_service import get_history
from database.auth_db import get_api_key_for_tradingview
from datetime import datetime, timedelta

api_key = get_api_key_for_tradingview('avinash')
today = datetime.now().date()
yesterday = today - timedelta(days=1)
week_start = today - timedelta(days=7)

print("Testing history service with yfinance fallback...")
print(f"Today: {today}")
print(f"Yesterday: {yesterday}")
print(f"Week start: {week_start}")
print()

# Test today
print(f"[1/3] Testing today ({today})...")
success, response, status = get_history('NIFTY', 'NSE_INDEX', '5m', str(today), str(today), api_key=api_key)
print(f"  Success: {success}, Status: {status}, Records: {len(response.get('data', []))}")

# Test yesterday
print(f"[2/3] Testing yesterday ({yesterday})...")
success, response, status = get_history('NIFTY', 'NSE_INDEX', '5m', str(yesterday), str(yesterday), api_key=api_key)
print(f"  Success: {success}, Status: {status}, Records: {len(response.get('data', []))}")

# Test week
print(f"[3/3] Testing week ({week_start} to {today})...")
success, response, status = get_history('NIFTY', 'NSE_INDEX', '5m', str(week_start), str(today), api_key=api_key)
print(f"  Success: {success}, Status: {status}, Records: {len(response.get('data', []))}")

print("\nTest complete!")


