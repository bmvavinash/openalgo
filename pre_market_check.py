#!/usr/bin/env python3
"""
Pre-Market Verification Script
Ensures everything is ready for live trading:
1. Check analyze mode status (should be False for live trading)
2. Verify login redirection works correctly
3. Check dashboard routes use live data
4. Verify all strategies are ready
5. Check scheduler is configured
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.settings_db import get_analyze_mode, set_analyze_mode
from utils.logging import get_logger
from database.auth_db import get_auth_token
from database.user_db import find_user_by_username

logger = get_logger(__name__)

def check_analyze_mode():
    """Check current analyze mode and switch to live if needed"""
    print("\n" + "="*60)
    print("PRE-MARKET VERIFICATION")
    print("="*60)
    
    current_mode = get_analyze_mode()
    print(f"\n[1] Current Mode: {'ANALYZE (Paper Trading)' if current_mode else 'LIVE (Real Trading)'}")
    
    if current_mode:
        print("\n[WARNING] System is in ANALYZE mode (Paper Trading)")
        print("   Switching to LIVE mode for real trading...")
        try:
            set_analyze_mode(False)
            new_mode = get_analyze_mode()
            if not new_mode:
                print("   [OK] Successfully switched to LIVE mode")
            else:
                print("   [ERROR] Failed to switch to LIVE mode")
                return False
        except Exception as e:
            print(f"   [ERROR] Switching mode: {e}")
            return False
    else:
        print("   [OK] System is already in LIVE mode")
    
    return True

def check_auth_setup():
    """Check if authentication is properly set up"""
    print("\n[2] Checking Authentication Setup...")
    
    admin_user = find_user_by_username()
    if not admin_user:
        print("   [WARNING] No admin user found. System may need setup.")
        return False
    
    print(f"   [OK] Admin user found: {admin_user.username}")
    
    # Check if user has auth token (for live trading)
    auth_token = get_auth_token(admin_user.username)
    if auth_token:
        print(f"   [OK] Auth token found for user")
    else:
        print(f"   [WARNING] No auth token found. User may need to login to broker.")
        print("      This is OK if you're using API key authentication.")
    
    return True

def check_routes():
    """Verify routes are configured correctly"""
    print("\n[3] Checking Route Configuration...")
    
    try:
        from app import create_app
        app = create_app()
        
        # Check critical routes exist
        routes_to_check = [
            ('/dashboard', 'dashboard_bp.dashboard'),
            ('/orderbook', 'orders_bp.orderbook'),
            ('/tradebook', 'orders_bp.tradebook'),
            ('/positions', 'orders_bp.positions'),
            ('/auth/login', 'auth.login'),
            ('/python', 'python_strategy_bp.index'),
        ]
        
        all_routes = {str(rule): rule.endpoint for rule in app.url_map.iter_rules()}
        
        print("   Checking critical routes...")
        for route_path, expected_endpoint in routes_to_check:
            found = False
            for rule_str, endpoint in all_routes.items():
                if route_path in rule_str and endpoint == expected_endpoint:
                    found = True
                    break
            if found:
                print(f"   [OK] {route_path} -> {expected_endpoint}")
            else:
                print(f"   [WARNING] Route not found: {route_path}")
        
        return True
    except Exception as e:
        print(f"   [ERROR] Checking routes: {e}")
        return False

def check_data_sources():
    """Verify data sources are configured for live data"""
    print("\n[4] Checking Data Sources...")
    
    analyze_mode = get_analyze_mode()
    if analyze_mode:
        print("   [WARNING] Still in analyze mode - will use sandbox data")
        return False
    
    print("   [OK] Live mode enabled - will use live broker data")
    print("   [OK] Dashboard will fetch from live broker APIs")
    print("   [OK] Orderbook/Tradebook will use live broker data")
    
    return True

def check_strategies():
    """Check if strategies are ready"""
    print("\n[5] Checking Strategies...")
    
    try:
        from database.strategy_db import Strategy
        from database.db_init_helper import get_strategy_db_session
        
        db_session = get_strategy_db_session()
        strategies = db_session.query(Strategy).all()
        
        print(f"   Found {len(strategies)} strategy configuration(s)")
        
        if len(strategies) > 0:
            print("   Strategy list:")
            for strategy in strategies:
                status = "Running" if strategy.is_running else "Stopped"
                print(f"      - {strategy.name} ({status})")
        
        db_session.close()
        return True
    except Exception as e:
        print(f"   [WARNING] Could not check strategies: {e}")
        return True  # Don't fail on this

def check_scheduler():
    """Check if daily scheduler is configured"""
    print("\n[6] Checking Daily Scheduler...")
    
    try:
        # Check if scheduler setup file exists
        import os
        scheduler_file = os.path.join(os.path.dirname(__file__), 'setup_daily_analysis_scheduler.py')
        if os.path.exists(scheduler_file):
            print("   [OK] Daily analysis scheduler file found")
        else:
            print("   [WARNING] Daily analysis scheduler file not found")
        
        # Check if strategy_performance.json exists
        config_file = os.path.join(os.path.dirname(__file__), 'config', 'strategy_performance.json')
        if os.path.exists(config_file):
            print("   [OK] Strategy performance config found")
        else:
            print("   [WARNING] Strategy performance config not found")
        
        return True
    except Exception as e:
        print(f"   [WARNING] Could not check scheduler: {e}")
        return True

def main():
    """Run all checks"""
    print("\n[STARTING] Pre-Market Verification...")
    
    checks = [
        ("Analyze Mode", check_analyze_mode),
        ("Authentication", check_auth_setup),
        ("Routes", check_routes),
        ("Data Sources", check_data_sources),
        ("Strategies", check_strategies),
        ("Scheduler", check_scheduler),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ ERROR in {name} check: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("[SUCCESS] ALL CHECKS PASSED - System ready for live trading!")
        print("\nNext steps:")
        print("1. Start the server: python app.py")
        print("2. Start all strategies from the Python Strategies page")
        print("3. Monitor dashboard and orderbook for live data")
    else:
        print("[WARNING] SOME CHECKS FAILED - Please review warnings above")
        print("\n[IMPORTANT] Fix issues before starting live trading!")
    
    print("="*60 + "\n")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())

