"""
Comprehensive API Testing Script
Tests all API endpoints and functionality
"""
import sys
from pathlib import Path
import requests
import json
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASE_URL = "http://127.0.0.1:5000"
API_BASE = f"{BASE_URL}/api/v1"

def test_endpoint(method, endpoint, data=None, headers=None, description=""):
    """Test a single endpoint"""
    try:
        url = f"{API_BASE}{endpoint}"
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=5)
        else:
            return False, f"Unsupported method: {method}", 0
        
        status = response.status_code
        success = 200 <= status < 400
        
        try:
            result = response.json()
        except:
            result = response.text[:100]
        
        return success, result, status
    except requests.exceptions.ConnectionError:
        return False, "Connection Error", 0
    except Exception as e:
        return False, str(e)[:100], 0

def test_all_apis():
    """Test all API endpoints"""
    print("="*80)
    print("COMPREHENSIVE API TEST")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    test_headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': 'test_key_12345'
    }
    
    test_data = {
        'symbol': 'RELIANCE',
        'exchange': 'NSE',
        'apikey': 'test_key_12345'
    }
    
    apis = [
        # Market Data APIs
        ('GET', '/ping', None, 'Ping/Health Check'),
        ('POST', '/quotes', test_data, 'Get Quotes'),
        ('POST', '/multiquotes', {'symbols': ['RELIANCE', 'TCS'], 'apikey': 'test'}, 'Multi Quotes'),
        ('POST', '/depth', test_data, 'Market Depth'),
        ('POST', '/history', {**test_data, 'interval': '1min', 'start_date': '2024-01-01', 'end_date': '2024-01-02'}, 'Historical Data'),
        ('GET', '/ticker/RELIANCE', None, 'Ticker Data'),
        ('POST', '/symbol', test_data, 'Symbol Info'),
        ('POST', '/search', {'query': 'RELIANCE', 'apikey': 'test'}, 'Symbol Search'),
        ('POST', '/expiry', test_data, 'Expiry Dates'),
        ('GET', '/intervals', None, 'Intervals'),
        
        # Order Management APIs
        ('GET', '/orderbook', None, 'Orderbook'),
        ('GET', '/tradebook', None, 'Tradebook'),
        ('GET', '/positionbook', None, 'Positionbook'),
        ('GET', '/holdings', None, 'Holdings'),
        ('GET', '/funds', None, 'Funds'),
        ('POST', '/margin', test_data, 'Margin'),
        ('POST', '/orderstatus', test_data, 'Order Status'),
        ('POST', '/openposition', test_data, 'Open Position'),
        
        # Option APIs
        ('POST', '/optionsymbol', test_data, 'Option Symbol'),
        ('POST', '/optiongreeks', test_data, 'Option Greeks'),
        
        # Utility APIs
        ('GET', '/instruments', None, 'Instruments'),
    ]
    
    print("\nTesting APIs:\n")
    results = {'ok': [], 'auth': [], 'error': [], 'not_found': []}
    
    for method, endpoint, data, desc in apis:
        success, result, status = test_endpoint(method, endpoint, data, test_headers, desc)
        
        if success:
            print(f"[OK]   {method:4} {endpoint:35} - {desc} (Status: {status})")
            results['ok'].append((endpoint, desc))
        elif status == 401 or status == 403:
            print(f"[AUTH] {method:4} {endpoint:35} - {desc} (Status: {status} - Auth Required)")
            results['auth'].append((endpoint, desc))
        elif status == 404:
            print(f"[404]  {method:4} {endpoint:35} - {desc} (Not Found)")
            results['not_found'].append((endpoint, desc))
        else:
            print(f"[FAIL] {method:4} {endpoint:35} - {desc} (Status: {status})")
            results['error'].append((endpoint, desc, status))
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"[OK] Working (200-399):     {len(results['ok'])}")
    print(f"[AUTH] Auth Required (401/403): {len(results['auth'])}")
    print(f"[404] Not Found (404):      {len(results['not_found'])}")
    print(f"[FAIL] Errors:               {len(results['error'])}")
    print(f"Total APIs Tested:      {len(apis)}")
    
    if results['not_found']:
        print("\n[WARN] Missing APIs (404):")
        for endpoint, desc in results['not_found']:
            print(f"   - {endpoint} - {desc}")
    
    if results['error']:
        print("\n[ERROR] Failed APIs:")
        for endpoint, desc, status in results['error']:
            print(f"   - {endpoint} - {desc} (Status: {status})")
    
    return results

def test_routes():
    """Test web routes"""
    print("\n" + "="*80)
    print("TESTING WEB ROUTES")
    print("="*80)
    
    routes = [
        ('/auth/login', 'Login Page'),
        ('/dashboard', 'Dashboard'),
        ('/orders/orderbook', 'Orderbook'),
        ('/orders/tradebook', 'Tradebook'),
        ('/orders/positions', 'Positions'),
        ('/orders/holdings', 'Holdings'),
        ('/analyzer', 'API Analyzer'),
        ('/playground', 'Market Watch (Playground)'),
        ('/strategy', 'Strategy Management'),
        ('/platforms', 'Platforms'),
    ]
    
    print("\nTesting Routes:\n")
    for route, desc in routes:
        try:
            response = requests.get(f"{BASE_URL}{route}", timeout=5, allow_redirects=False)
            status = response.status_code
            if status == 200:
                print(f"[OK]   {route:35} - {desc}")
            elif status in [302, 301]:
                loc = response.headers.get('Location', 'N/A')
                print(f"[REDIR] {route:35} - {desc} -> {loc}")
            elif status == 404:
                print(f"[404]  {route:35} - {desc}")
            else:
                print(f"[{status:3}]  {route:35} - {desc}")
        except Exception as e:
            print(f"[ERROR] {route:35} - {desc} - {str(e)[:40]}")

if __name__ == "__main__":
    try:
        test_all_apis()
        test_routes()
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()

