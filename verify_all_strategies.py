"""
Comprehensive Strategy Verification Script
Checks server status, strategy status, and logs for all strategies
"""
import os
import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

def check_server_status():
    """Check if Flask server is running"""
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_strategy_configs():
    """Get all strategy configurations"""
    try:
        from blueprints.python_strategy import STRATEGY_CONFIGS
        return STRATEGY_CONFIGS
    except Exception as e:
        print(f"Error loading strategy configs: {e}")
        return {}

def get_strategy_logs(strategy_id, lines=50):
    """Get recent logs for a strategy"""
    log_dir = Path("strategies/logs")
    log_file = log_dir / f"{strategy_id}.log"
    
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except Exception as e:
        print(f"Error reading log for {strategy_id}: {e}")
        return []

def check_strategy_errors(logs):
    """Check logs for errors"""
    errors = []
    warnings = []
    
    for line in logs:
        line_lower = line.lower()
        if 'error' in line_lower or 'failed' in line_lower or 'exception' in line_lower:
            errors.append(line.strip())
        elif 'warning' in line_lower:
            warnings.append(line.strip())
    
    return errors, warnings

def main():
    print("=" * 80)
    print("COMPREHENSIVE STRATEGY VERIFICATION")
    print("=" * 80)
    print()
    
    # Step 1: Check server status
    print("Step 1: Checking Flask server status...")
    if check_server_status():
        print("[OK] Server is running")
    else:
        print("[ERROR] Server is NOT running - please start it first")
        return
    print()
    
    # Step 2: Get all strategies
    print("Step 2: Loading strategy configurations...")
    strategies = get_strategy_configs()
    print(f"Found {len(strategies)} strategies")
    print()
    
    if not strategies:
        print("No strategies found. Please create strategies first.")
        return
    
    # Step 3: Check each strategy
    print("Step 3: Checking strategy logs and status...")
    print("-" * 80)
    
    all_errors = []
    all_warnings = []
    running_count = 0
    error_count = 0
    
    for strategy_id, config in strategies.items():
        strategy_name = config.get('name', strategy_id)
        print(f"\nStrategy: {strategy_name} ({strategy_id})")
        print(f"  Type: {config.get('type', 'Unknown')}")
        
        # Check if strategy is running (check for process)
        log_dir = Path("strategies/logs")
        log_file = log_dir / f"{strategy_id}.log"
        
        if log_file.exists():
            # Check last log entry time
            try:
                stat = log_file.stat()
                last_modified = datetime.fromtimestamp(stat.st_mtime)
                time_diff = (datetime.now() - last_modified).total_seconds()
                
                if time_diff < 300:  # Modified in last 5 minutes
                    print(f"  Status: [RUNNING] Likely running (log updated {int(time_diff)}s ago)")
                    running_count += 1
                else:
                    print(f"  Status: [WARNING] Possibly stopped (log not updated in {int(time_diff)}s)")
            except:
                print(f"  Status: [UNKNOWN] Unknown")
        else:
            print(f"  Status: [STOPPED] No log file found")
        
        # Check logs for errors
        logs = get_strategy_logs(strategy_id, lines=100)
        if logs:
            errors, warnings = check_strategy_errors(logs)
            
            if errors:
                print(f"  Errors: {len(errors)} found")
                for error in errors[-3:]:  # Show last 3 errors
                    print(f"    - {error[:100]}")
                all_errors.extend([(strategy_id, strategy_name, e) for e in errors])
                error_count += 1
            else:
                print(f"  Errors: None")
            
            if warnings:
                print(f"  Warnings: {len(warnings)} found")
                all_warnings.extend([(strategy_id, strategy_name, w) for w in warnings])
            
            # Show last few log lines
            print(f"  Recent logs (last 3 lines):")
            for line in logs[-3:]:
                print(f"    {line.strip()[:100]}")
        else:
            print(f"  Logs: No logs available")
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total strategies: {len(strategies)}")
    print(f"Likely running: {running_count}")
    print(f"Strategies with errors: {error_count}")
    print(f"Total errors found: {len(all_errors)}")
    print(f"Total warnings found: {len(all_warnings)}")
    print()
    
    if all_errors:
        print("ERRORS FOUND:")
        print("-" * 80)
        for strategy_id, strategy_name, error in all_errors[-10:]:  # Show last 10 errors
            print(f"[{strategy_name}] {error[:150]}")
        print()
    
    if error_count > 0:
        print("[WARNING] Some strategies have errors. Review the logs above.")
        return False
    else:
        print("[SUCCESS] All strategies appear to be running without errors!")
        return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during verification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

