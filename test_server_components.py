#!/usr/bin/env python3
"""
Test script to verify all server components are working correctly
"""
import sys
import os
import time
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all critical imports"""
    print("\n" + "="*60)
    print("TESTING IMPORTS")
    print("="*60)
    
    tests = []
    
    # Test core modules
    try:
        from utils.logging import WindowsCompatibleTimedRotatingFileHandler, get_logger
        tests.append(("Windows Log Handler", True, ""))
    except Exception as e:
        tests.append(("Windows Log Handler", False, str(e)))
    
    try:
        from strategy_performance_config import StrategyPerformanceConfig
        tests.append(("Strategy Performance Config", True, ""))
    except Exception as e:
        tests.append(("Strategy Performance Config", False, str(e)))
    
    try:
        from strategy_execution_filter import StrategyExecutionFilter
        tests.append(("Strategy Execution Filter", True, ""))
    except Exception as e:
        tests.append(("Strategy Execution Filter", False, str(e)))
    
    try:
        from daily_strategy_analyzer import analyze_today_performance
        tests.append(("Daily Strategy Analyzer", True, ""))
    except Exception as e:
        tests.append(("Daily Strategy Analyzer", False, str(e)))
    
    try:
        from setup_daily_analysis_scheduler import setup_daily_analysis_scheduler
        tests.append(("Daily Analysis Scheduler", True, ""))
    except Exception as e:
        tests.append(("Daily Analysis Scheduler", False, str(e)))
    
    try:
        from blueprints.strategy_performance import strategy_performance_bp
        tests.append(("Strategy Performance Blueprint", True, ""))
    except Exception as e:
        tests.append(("Strategy Performance Blueprint", False, str(e)))
    
    try:
        from database.settings_db import get_user_setting, set_user_setting
        tests.append(("User Settings Functions", True, ""))
    except Exception as e:
        tests.append(("User Settings Functions", False, str(e)))
    
    # Print results
    all_passed = True
    for name, passed, error in tests:
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {name}")
        if not passed:
            print(f"  Error: {error}")
            all_passed = False
    
    return all_passed

def test_config_files():
    """Test configuration files exist"""
    print("\n" + "="*60)
    print("TESTING CONFIG FILES")
    print("="*60)
    
    config_file = Path("config/strategy_performance.json")
    if config_file.exists():
        print("[OK] strategy_performance.json exists")
        try:
            import json
            with open(config_file) as f:
                data = json.load(f)
            print(f"  Version: {data.get('version', 'N/A')}")
            print(f"  Strategies: {len(data.get('strategies', {}))}")
            return True
        except Exception as e:
            print(f"[FAIL] Error reading config: {e}")
            return False
    else:
        print("[FAIL] strategy_performance.json missing")
        return False

def test_flask_app():
    """Test Flask app initialization"""
    print("\n" + "="*60)
    print("TESTING FLASK APP")
    print("="*60)
    
    try:
        # Set up minimal environment
        os.environ.setdefault('FLASK_HOST_IP', '127.0.0.1')
        os.environ.setdefault('FLASK_PORT', '5000')
        
        from app import create_app
        app = create_app()
        
        # Check if blueprint is registered
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        if 'strategy_performance_bp' in blueprint_names:
            print("[OK] Strategy Performance Blueprint registered")
        else:
            print("[FAIL] Strategy Performance Blueprint NOT registered")
            print(f"  Registered blueprints: {blueprint_names}")
            return False
        
        # Check routes
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        strategy_routes = [r for r in routes if 'strategy-performance' in r]
        if strategy_routes:
            print(f"[OK] Found {len(strategy_routes)} strategy-performance routes")
            for route in strategy_routes[:5]:  # Show first 5
                print(f"  - {route}")
        else:
            print("[FAIL] No strategy-performance routes found")
            return False
        
        print("[OK] Flask app initialized successfully")
        return True
        
    except Exception as e:
        print(f"✗ Flask app initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_server_endpoints(base_url="http://127.0.0.1:5000"):
    """Test server endpoints (if server is running)"""
    print("\n" + "="*60)
    print("TESTING SERVER ENDPOINTS")
    print("="*60)
    
    endpoints = [
        ("/", "Home page"),
        ("/strategy-performance/", "Strategy Performance Dashboard"),
    ]
    
    all_ok = True
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code in [200, 302, 401]:  # 401 is OK (needs auth)
                print(f"[OK] {description}: {response.status_code}")
            else:
                print(f"[FAIL] {description}: {response.status_code}")
                all_ok = False
        except requests.exceptions.ConnectionError:
            print(f"[SKIP] {description}: Server not running (this is OK if testing before start)")
            break
        except Exception as e:
            print(f"[FAIL] {description}: {e}")
            all_ok = False
    
    return all_ok

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SERVER COMPONENT VERIFICATION")
    print("="*60)
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: Config files
    results.append(("Config Files", test_config_files()))
    
    # Test 3: Flask app
    results.append(("Flask App", test_flask_app()))
    
    # Test 4: Server endpoints (optional - only if server is running)
    try:
        results.append(("Server Endpoints", test_server_endpoints()))
    except:
        results.append(("Server Endpoints", None))  # Skip if server not running
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for name, result in results:
        if result is True:
            print(f"[OK] {name}: PASSED")
            passed += 1
        elif result is False:
            print(f"[FAIL] {name}: FAILED")
            failed += 1
        else:
            print(f"[SKIP] {name}: SKIPPED")
            skipped += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0:
        print("\n[OK] All critical tests passed!")
        return 0
    else:
        print("\n[FAIL] Some tests failed. Please review errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

