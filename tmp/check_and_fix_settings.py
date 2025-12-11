#!/usr/bin/env python3
"""
Check and fix settings: Ensure analyze mode is ON and data mode is Live
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.settings_db import get_analyze_mode, set_analyze_mode, get_use_historical_data, set_use_historical_data
from flask import Flask
from app import create_app

app = create_app()

with app.app_context():
    # Check current settings
    analyze_mode = get_analyze_mode()
    data_mode = get_use_historical_data()
    
    print(f"Current Settings:")
    print(f"  Analyze Mode (Paper Trading): {'ON' if analyze_mode else 'OFF'}")
    print(f"  Data Mode: {'Historical' if data_mode else 'Live'}")
    print()
    
    changes_made = False
    
    # Ensure analyze mode is ON (paper trading)
    if not analyze_mode:
        print("⚠️  Analyze mode is OFF - enabling for paper trading...")
        set_analyze_mode(True)
        changes_made = True
        print("✅ Analyze mode set to ON")
    else:
        print("✅ Analyze mode is already ON")
    
    # Ensure data mode is Live (not Historical)
    if data_mode:
        print("⚠️  Data mode is Historical - switching to Live...")
        set_use_historical_data(False)
        changes_made = True
        print("✅ Data mode set to Live")
    else:
        print("✅ Data mode is already Live")
    
    print()
    if changes_made:
        print("✅ Settings updated successfully!")
        print("   Configuration: Paper Trading (Analyze Mode ON) + Live Data")
    else:
        print("✅ All settings are correct!")
        print("   Configuration: Paper Trading (Analyze Mode ON) + Live Data")

