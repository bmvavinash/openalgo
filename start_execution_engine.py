#!/usr/bin/env python3
"""
Start Execution Engine Script
Manually starts the execution engine if it's not running
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from app import create_app
from sandbox.execution_thread import start_execution_engine, is_execution_engine_running, get_execution_engine_status
from database.settings_db import get_analyze_mode
from utils.logging import get_logger

logger = get_logger(__name__)

def main():
    print("\n" + "="*60)
    print("STARTING EXECUTION ENGINE")
    print("="*60)
    
    # Create app context
    app = create_app()
    
    with app.app_context():
        # Check mode
        analyze_mode = get_analyze_mode()
        print(f"\n[1] Mode: {'ANALYZE/PAPER TRADING' if analyze_mode else 'LIVE TRADING'}")
        
        if not analyze_mode:
            print("\n[WARNING] Analyze mode is OFF. Execution engine only runs in analyze mode.")
            print("          Enable analyze mode first via /settings")
            return False
        
        # Check current status
        is_running = is_execution_engine_running()
        print(f"\n[2] Current Status: {'RUNNING' if is_running else 'NOT RUNNING'}")
        
        if is_running:
            print("\n[INFO] Execution engine is already running!")
            status = get_execution_engine_status()
            print(f"       Thread: {status.get('thread_name', 'N/A')}")
            print(f"       Check Interval: {status.get('check_interval', 'N/A')} seconds")
            return True
        
        # Start execution engine
        print("\n[3] Starting execution engine...")
        success, message = start_execution_engine()
        
        if success:
            print(f"[OK] {message}")
            print("\n[INFO] Execution engine started successfully!")
            print("       It will now monitor and execute pending orders every 5 seconds.")
            return True
        else:
            print(f"[ERROR] {message}")
            return False

if __name__ == '__main__':
    try:
        result = main()
        print("\n" + "="*60)
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n[ERROR] Failed to start execution engine: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)






