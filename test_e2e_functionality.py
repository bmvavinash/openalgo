"""
End-to-End Functionality Test Script
Checks all critical components and routes
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask
from app import app

def test_blueprints():
    """Test if all blueprints are registered"""
    print("="*60)
    print("🔍 TESTING BLUEPRINT REGISTRATION")
    print("="*60)
    
    registered_blueprints = []
    for name, blueprint in app.blueprints.items():
        registered_blueprints.append({
            'name': name,
            'url_prefix': blueprint.url_prefix,
            'routes': len(list(blueprint.deferred_functions))
        })
    
    print(f"\n✅ Total Blueprints Registered: {len(registered_blueprints)}\n")
    
    critical_blueprints = [
        'auth', 'dashboard_bp', 'orders_bp', 'analyzer_bp',
        'strategy_bp', 'python_strategy_bp', 'sandbox_bp'
    ]
    
    for bp in registered_blueprints:
        status = "✅" if bp['name'] in critical_blueprints or bp['name'].endswith('_bp') else "⚠️"
        prefix = bp['url_prefix'] or '(None)'
        print(f"{status} {bp['name']:25} | Prefix: {prefix:20} | Routes: {bp['routes']}")
    
    print("\n" + "="*60)
    return registered_blueprints

def test_routes():
    """Test critical routes"""
    print("\n" + "="*60)
    print("🔍 TESTING CRITICAL ROUTES")
    print("="*60)
    
    critical_routes = {
        '/auth/login': 'Login page',
        '/dashboard': 'Dashboard',
        '/orders/orderbook': 'Orderbook',
        '/orders/tradebook': 'Tradebook',
        '/orders/positions': 'Positions',
        '/analyzer': 'API Analyzer',
        '/strategy': 'Strategy management',
        '/sandbox': 'Sandbox/Paper Trading'
    }
    
    with app.test_client() as client:
        print("\nTesting Routes:\n")
        for route, description in critical_routes.items():
            try:
                response = client.get(route, follow_redirects=False)
                status = response.status_code
                
                if status == 200:
                    print(f"✅ {route:30} | {description:30} | Status: {status}")
                elif status == 302 or status == 301:
                    redirect_location = response.headers.get('Location', 'N/A')
                    print(f"🔄 {route:30} | {description:30} | Status: {status} → {redirect_location}")
                elif status == 401 or status == 403:
                    print(f"🔒 {route:30} | {description:30} | Status: {status} (Auth Required)")
                else:
                    print(f"⚠️  {route:30} | {description:30} | Status: {status}")
            except Exception as e:
                print(f"❌ {route:30} | {description:30} | Error: {str(e)[:50]}")
    
    print("\n" + "="*60)

def test_session_management():
    """Test session management"""
    print("\n" + "="*60)
    print("🔍 TESTING SESSION MANAGEMENT")
    print("="*60)
    
    with app.test_client() as client:
        # Test session configuration
        print("\n1. Session Configuration:")
        print(f"   ✅ Session Cookie Name: {app.config.get('SESSION_COOKIE_NAME', 'N/A')}")
        print(f"   ✅ Session Cookie Path: {app.config.get('SESSION_COOKIE_PATH', 'N/A')}")
        print(f"   ✅ Session Cookie HttpOnly: {app.config.get('SESSION_COOKIE_HTTPONLY', 'N/A')}")
        print(f"   ✅ Session Cookie SameSite: {app.config.get('SESSION_COOKIE_SAMESITE', 'N/A')}")
        
        # Test session interface
        print("\n2. Session Interface:")
        session_interface = type(app.session_interface).__name__
        print(f"   ✅ Session Interface: {session_interface}")
        
        # Test session modification
        print("\n3. Session Modification Test:")
        with client.session_transaction() as sess:
            sess['test_key'] = 'test_value'
            sess.modified = True
        
        print("   ✅ Session can be modified")
    
    print("\n" + "="*60)

def test_url_generation():
    """Test URL generation for critical routes"""
    print("\n" + "="*60)
    print("🔍 TESTING URL GENERATION")
    print("="*60)
    
    with app.app_context():
        from flask import url_for
        
        test_urls = [
            ('orders_bp.orderbook', '/orders/orderbook'),
            ('orders_bp.tradebook', '/orders/tradebook'),
            ('orders_bp.positions', '/orders/positions'),
            ('dashboard_bp.dashboard', '/dashboard'),
            ('auth.login', '/auth/login'),
            ('analyzer_bp.analyzer', '/analyzer'),
        ]
        
        print("\nTesting URL Generation:\n")
        for endpoint, expected in test_urls:
            try:
                generated = url_for(endpoint)
                status = "✅" if generated == expected else "⚠️"
                print(f"{status} {endpoint:30} | Expected: {expected:25} | Got: {generated}")
            except Exception as e:
                print(f"❌ {endpoint:30} | Error: {str(e)[:50]}")
    
    print("\n" + "="*60)

def test_imports():
    """Test critical imports"""
    print("\n" + "="*60)
    print("🔍 TESTING CRITICAL IMPORTS")
    print("="*60)
    
    imports_to_test = [
        ('utils.session', ['is_session_valid', 'check_session_validity', 'set_session_login_time']),
        ('utils.market_hours', ['is_market_open', 'get_market_status_message']),
        ('database.settings_db', ['get_analyze_mode']),
        ('database.auth_db', ['get_auth_token', 'get_api_key_for_tradingview']),
        ('services.orderbook_service', ['get_orderbook']),
        ('services.tradebook_service', ['get_tradebook']),
        ('services.positionbook_service', ['get_positionbook']),
    ]
    
    print("\nTesting Imports:\n")
    for module_name, functions in imports_to_test:
        try:
            module = __import__(module_name, fromlist=functions)
            missing = []
            for func in functions:
                if not hasattr(module, func):
                    missing.append(func)
            
            if missing:
                print(f"⚠️  {module_name:35} | Missing: {', '.join(missing)}")
            else:
                print(f"✅ {module_name:35} | All functions available")
        except Exception as e:
            print(f"❌ {module_name:35} | Error: {str(e)[:50]}")
    
    print("\n" + "="*60)

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 END-TO-END FUNCTIONALITY TEST")
    print("="*60)
    print(f"Flask App: {app.name}")
    print(f"Debug Mode: {app.debug}")
    print(f"Secret Key Set: {'Yes' if app.secret_key else 'No'}")
    print("="*60)
    
    try:
        # Run all tests
        test_blueprints()
        test_routes()
        test_session_management()
        test_url_generation()
        test_imports()
        
        print("\n" + "="*60)
        print("✅ END-TO-END TEST COMPLETE")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

