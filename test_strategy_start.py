#!/usr/bin/env python
"""Test script to verify strategy can start in analysis mode"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app import app
from blueprints.python_strategy import check_master_contract_ready
from database.settings_db import get_analyze_mode

with app.app_context():
    print("=" * 60)
    print("Testing Master Contract Check in Analysis Mode")
    print("=" * 60)
    
    # Check analysis mode
    analyze_mode = get_analyze_mode()
    print(f"\n1. Analysis Mode Status: {analyze_mode}")
    
    # Test master contract check
    print("\n2. Testing check_master_contract_ready()...")
    contracts_ready, message = check_master_contract_ready()
    print(f"   Result: {contracts_ready}")
    print(f"   Message: {message}")
    
    if contracts_ready:
        print("\n✅ SUCCESS: Master contract check passed (should skip in analysis mode)")
    else:
        print("\n❌ FAILED: Master contract check failed")
        print(f"   Error: {message}")
    
    print("\n" + "=" * 60)


