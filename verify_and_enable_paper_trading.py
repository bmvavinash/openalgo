#!/usr/bin/env python3
"""Verify and enable paper trading mode"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.settings_db import get_analyze_mode, set_analyze_mode
from app import create_app

app = create_app()
with app.app_context():
    analyze_mode = get_analyze_mode()
    if not analyze_mode:
        print('Setting analyze_mode to True (Paper Trading)...')
        set_analyze_mode(True)
        analyze_mode = get_analyze_mode()
    
    if analyze_mode:
        print('OK - Paper Trading Mode is ENABLED')
        sys.exit(0)
    else:
        print('ERROR - Failed to enable Paper Trading Mode')
        sys.exit(1)












