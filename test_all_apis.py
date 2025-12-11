"""
Test All APIs End-to-End
"""
import sys
from pathlib import Path
import requests
import json

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASE_URL = "http://127.0.0.1:5000"
API_BASE = f"{BASE_URL}/api/v1"

def test_api_endpoint(method, endpoint, data=None, headers=None, description=""):
    """Test a single API endpoint"""
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
        return False, "Connection Error - Server not running?", 0
    except Exception as e:
        return False, str(e)[:100], 0

def test_all_apis():
    """Test all API endpoints"""
    print("="*70)
    print("TESTING ALL API ENDPOINTS")
    print("="*70)
    
    # Test with a sample API key (will fail but shows endpoint exists)
    test_headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': 'test_key_12345'
    }
    
    test_data = {
        'symbol': 'RELIANCE',
        'exchange': 'NSE'
    }
    
    apis_to_test = [
        # Market Data APIs
        ('GET', '/quotes', None, 'Get Quotes'),
        ('POST', '/quotes', test_data, 'Get Quotes (POST)'),
        ('POST', '/multiquotes', {'symbols': ['RELIANCE', 'TCS']}, 'Multi Quotes'),
        ('GET', '/depth', None, 'Market Depth'),
        ('GET', '/history', None, 'Historical Data'),
        ('GET', '/ticker/RELIANCE', None, 'Ticker Data'),
        ('GET', '/symbol', None, 'Symbol Info'),
        ('GET', '/search', None, 'Symbol Search'),
        ('GET', '/expiry', None, 'Expiry Dates'),
        ('GET', '/intervals', None, 'Intervals'),
        
        # Order APIs
        ('GET', '/orderbook', None, 'Orderbook'),
        ('GET', '/tradebook', None, 'Tradebook'),
        ('GET', '/positionbook', None, 'Positionbook'),
        ('GET', '/holdings', None, 'Holdings'),
        ('GET', '/funds', None, 'Funds'),
        ('GET', '/margin', None, 'Margin'),
        ('GET', '/orderstatus', None, 'Order Status'),
        ('GET', '/openposition', None, 'Open Position'),
        
        # Option APIs
        ('GET', '/optionsymbol', None, 'Option Symbol'),
        ('GET', '/optiongreeks', None, 'Option Greeks'),
        
        # Utility APIs
        ('GET', '/ping', None, 'Ping'),
        ('GET', '/instruments', None, 'Instruments'),
    ]
    
    print("\nTesting APIs:\n")
    results = []
    
    for method, endpoint, data, desc in apis_to_test:
        success, result, status = test_api_endpoint(method, endpoint, data, test_headers, desc)
        
        if success:
            print(f"OK   {method:4} {endpoint:30} - {desc} (Status: {status})")
            results.append(('OK', endpoint, desc))
        elif status == 401 or status == 403:
            print(f"AUTH {method:4} {endpoint:30} - {desc} (Status: {status} - Auth Required)")
            results.append(('AUTH', endpoint, desc))
        elif status == 404:
            print(f"404  {method:4} {endpoint:30} - {desc} (Not Found)")
            results.append(('404', endpoint, desc))
        else:
            print(f"FAIL {method:4} {endpoint:30} - {desc} (Status: {status})")
            results.append(('FAIL', endpoint, desc))
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    ok_count = sum(1 for r in results if r[0] == 'OK')
    auth_count = sum(1 for r in results if r[0] == 'AUTH')
    fail_count = sum(1 for r in results if r[0] == 'FAIL')
    not_found_count = sum(1 for r in results if r[0] == '404')
    
    print(f"OK (Working):     {ok_count}")
    print(f"AUTH Required:    {auth_count}")
    print(f"Not Found (404):  {not_found_count}")
    print(f"Failed:           {fail_count}")
    print(f"Total:            {len(results)}")
    
    if not_found_count > 0:
        print("\nMissing APIs (404):")
        for status, endpoint, desc in results:
            if status == '404':
                print(f"  - {endpoint} - {desc}")
    
    return results

def check_market_watch():
    """Check for Market Watch functionality"""
    print("\n" + "="*70)
    print("CHECKING FOR MARKET WATCH")
    print("="*70)
    
    # Check routes
    routes_to_check = [
        '/marketwatch',
        '/market-watch',
        '/market_watch',
        '/watchlist',
        '/quotes',
    ]
    
    print("\nChecking Routes:\n")
    for route in routes_to_check:
        try:
            response = requests.get(f"{BASE_URL}{route}", timeout=5, allow_redirects=False)
            status = response.status_code
            if status == 200:
                print(f"FOUND {route:30} - Status: {status}")
            elif status in [302, 301]:
                loc = response.headers.get('Location', 'N/A')
                print(f"REDIR {route:30} - Status: {status} -> {loc}")
            else:
                print(f"NO    {route:30} - Status: {status}")
        except:
            print(f"NO    {route:30} - Not accessible")

if __name__ == "__main__":
    try:
        test_all_apis()
        check_market_watch()
        print("\n" + "="*70)
        print("TEST COMPLETE")
        print("="*70)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()





