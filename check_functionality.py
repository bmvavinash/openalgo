"""
Simple End-to-End Functionality Check
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, url_for
from app import app

def check_routes():
    """Check critical routes"""
    print("="*70)
    print("CHECKING CRITICAL ROUTES")
    print("="*70)
    
    routes_to_check = {
        '/auth/login': 'Login page',
        '/dashboard': 'Dashboard',
        '/orders/orderbook': 'Orderbook',
        '/orders/tradebook': 'Tradebook',
        '/orders/positions': 'Positions',
        '/analyzer': 'API Analyzer',
    }
    
    with app.test_client() as client:
        for route, desc in routes_to_check.items():
            try:
                resp = client.get(route, follow_redirects=False)
                status = resp.status_code
                if status == 200:
                    print(f"OK   {route:30} - {desc}")
                elif status in [302, 301]:
                    loc = resp.headers.get('Location', 'N/A')
                    print(f"REDIR {route:30} - {desc} -> {loc}")
                elif status in [401, 403]:
                    print(f"AUTH  {route:30} - {desc} (requires login)")
                else:
                    print(f"WARN  {route:30} - {desc} (status: {status})")
            except Exception as e:
                print(f"ERROR {route:30} - {desc} - {str(e)[:40]}")

def check_url_generation():
    """Check URL generation"""
    print("\n" + "="*70)
    print("CHECKING URL GENERATION")
    print("="*70)
    
    with app.app_context():
        tests = [
            ('orders_bp.orderbook', '/orders/orderbook'),
            ('orders_bp.tradebook', '/orders/tradebook'),
            ('orders_bp.positions', '/orders/positions'),
            ('dashboard_bp.dashboard', '/dashboard'),
            ('auth.login', '/auth/login'),
            ('analyzer_bp.analyzer', '/analyzer'),
        ]
        
        for endpoint, expected in tests:
            try:
                generated = url_for(endpoint)
                if generated == expected:
                    print(f"OK   {endpoint:30} -> {generated}")
                else:
                    print(f"FAIL {endpoint:30} -> Expected: {expected}, Got: {generated}")
            except Exception as e:
                print(f"ERROR {endpoint:30} - {str(e)[:50]}")

def check_blueprints():
    """Check blueprint registration"""
    print("\n" + "="*70)
    print("CHECKING BLUEPRINT REGISTRATION")
    print("="*70)
    
    critical = ['auth', 'dashboard_bp', 'orders_bp', 'analyzer_bp']
    
    for name, bp in app.blueprints.items():
        prefix = bp.url_prefix or '(None)'
        status = "CRITICAL" if name in critical else "OK"
        print(f"{status:8} {name:25} prefix: {prefix}")

def check_imports():
    """Check critical imports"""
    print("\n" + "="*70)
    print("CHECKING CRITICAL IMPORTS")
    print("="*70)
    
    imports = [
        'utils.session',
        'utils.market_hours',
        'database.settings_db',
        'database.auth_db',
        'services.orderbook_service',
        'services.tradebook_service',
        'services.positionbook_service',
    ]
    
    for mod_name in imports:
        try:
            __import__(mod_name)
            print(f"OK   {mod_name}")
        except Exception as e:
            print(f"ERROR {mod_name} - {str(e)[:50]}")

def check_session_config():
    """Check session configuration"""
    print("\n" + "="*70)
    print("CHECKING SESSION CONFIGURATION")
    print("="*70)
    
    checks = [
        ('SESSION_COOKIE_NAME', app.config.get('SESSION_COOKIE_NAME')),
        ('SESSION_COOKIE_PATH', app.config.get('SESSION_COOKIE_PATH')),
        ('SESSION_COOKIE_HTTPONLY', app.config.get('SESSION_COOKIE_HTTPONLY')),
        ('Secret Key Set', bool(app.secret_key)),
    ]
    
    for name, value in checks:
        status = "OK" if value else "WARN"
        print(f"{status:8} {name:30} = {value}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("END-TO-END FUNCTIONALITY CHECK")
    print("="*70)
    print(f"App: {app.name}")
    print(f"Debug: {app.debug}")
    print("="*70)
    
    try:
        check_blueprints()
        check_routes()
        check_url_generation()
        check_imports()
        check_session_config()
        
        print("\n" + "="*70)
        print("CHECK COMPLETE")
        print("="*70)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()





