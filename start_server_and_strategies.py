#!/usr/bin/env python3
"""
Start Server and All Strategies Script
Checks if server is running, starts it if needed, then starts all strategies
"""

import sys
import os
import time
import requests
import subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logging import get_logger

logger = get_logger(__name__)

def check_server_running():
    """Check if server is running on port 5000"""
    try:
        response = requests.get('http://127.0.0.1:5000/', timeout=2)
        return response.status_code == 200
    except:
        return False

def start_server():
    """Start the Flask server in background"""
    print("\n[STARTING] Flask server...")
    
    # Check if already running
    if check_server_running():
        print("[OK] Server is already running")
        return True
    
    # Start server in background
    try:
        if os.name == 'nt':  # Windows
            # Use PowerShell to start in background
            script_dir = os.path.dirname(os.path.abspath(__file__))
            venv_activate = os.path.join(script_dir, 'venv', 'Scripts', 'Activate.ps1')
            app_file = os.path.join(script_dir, 'app.py')
            
            # Start server in background using PowerShell
            import subprocess
            startup_cmd = f'cd "{script_dir}"; if (Test-Path "{venv_activate}") {{ . "{venv_activate}" }}; python "{app_file}"'
            
            # Create a new process group for Windows
            process = subprocess.Popen(
                ['powershell', '-Command', startup_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
            
            print(f"[OK] Server process started (PID: {process.pid})")
            print("[WAIT] Waiting for server to initialize...")
            
            # Wait for server to start (max 30 seconds)
            for i in range(30):
                time.sleep(1)
                if check_server_running():
                    print("[OK] Server is now running and responding")
                    return True
                if i % 5 == 0:
                    print(f"   Still waiting... ({i+1}/30)")
            
            print("[WARNING] Server started but not responding yet. It may still be initializing.")
            return True
            
        else:  # Linux/Mac
            script_dir = os.path.dirname(os.path.abspath(__file__))
            app_file = os.path.join(script_dir, 'app.py')
            process = subprocess.Popen(
                [sys.executable, app_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            print(f"[OK] Server process started (PID: {process.pid})")
            
            # Wait for server to start
            for i in range(30):
                time.sleep(1)
                if check_server_running():
                    print("[OK] Server is now running and responding")
                    return True
            
            print("[WARNING] Server started but not responding yet")
            return True
            
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        return False

def start_all_strategies():
    """Start all strategies via API"""
    print("\n[CHECKING] Strategies status...")
    
    try:
        # First, we need to login or use session
        # For now, let's try to call the start-all endpoint
        # But we need authentication, so we'll use the internal function
        
        from blueprints.python_strategy import start_strategy_process, STRATEGY_CONFIGS, RUNNING_STRATEGIES
        
        # Load configs
        from blueprints.python_strategy import load_configs
        load_configs()
        
        strategies_to_start = []
        running_count = 0
        
        # Check all strategies
        for strategy_id, config in STRATEGY_CONFIGS.items():
            is_running = config.get('is_running', False) or strategy_id in RUNNING_STRATEGIES
            
            if is_running:
                running_count += 1
                print(f"   [RUNNING] {config.get('name', strategy_id)}")
            else:
                strategies_to_start.append((strategy_id, config.get('name', strategy_id)))
        
        print(f"\n[STATUS] {running_count} strategy(ies) already running")
        print(f"[STATUS] {len(strategies_to_start)} strategy(ies) need to be started")
        
        if not strategies_to_start:
            print("[OK] All strategies are already running!")
            return True
        
        # Start each strategy
        print("\n[STARTING] Strategies...")
        started_count = 0
        failed_count = 0
        
        for strategy_id, strategy_name in strategies_to_start:
            print(f"   Starting: {strategy_name}...")
            try:
                success, message = start_strategy_process(strategy_id)
                if success:
                    print(f"   [OK] {strategy_name}: {message}")
                    started_count += 1
                else:
                    print(f"   [FAILED] {strategy_name}: {message}")
                    failed_count += 1
                time.sleep(1)  # Small delay between starts
            except Exception as e:
                print(f"   [ERROR] {strategy_name}: {e}")
                failed_count += 1
        
        print(f"\n[SUMMARY] Started: {started_count}, Failed: {failed_count}")
        
        if started_count > 0:
            print("[OK] Strategies started successfully!")
            return True
        elif failed_count > 0:
            print("[WARNING] Some strategies failed to start")
            return False
        else:
            return True
            
    except Exception as e:
        print(f"[ERROR] Failed to start strategies: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("="*60)
    print("START SERVER AND STRATEGIES")
    print("="*60)
    
    # Step 1: Start server
    if not start_server():
        print("\n[ERROR] Failed to start server. Please check manually.")
        return 1
    
    # Step 2: Wait a bit for server to fully initialize
    print("\n[WAIT] Waiting for server to fully initialize...")
    time.sleep(5)
    
    # Step 3: Start all strategies
    if not start_all_strategies():
        print("\n[WARNING] Some strategies may not have started. Please check manually.")
        return 1
    
    print("\n" + "="*60)
    print("[SUCCESS] Server and strategies are running!")
    print("="*60)
    print("\nAccess the application at: http://127.0.0.1:5000")
    print("Monitor strategies at: http://127.0.0.1:5000/python")
    print("\n")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())






