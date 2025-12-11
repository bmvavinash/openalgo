"""
End-to-end session persistence test
Tests login, session cookie, and navigation to all routes
"""
import sys
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def test_session_persistence():
    """Test session persistence across routes"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    print("="*70)
    print("END-TO-END SESSION PERSISTENCE TEST")
    print("="*70)
    
    # Step 1: Get login page (should get CSRF token)
    print("\n1. Getting login page...")
    try:
        login_get = session.get(f"{base_url}/auth/login", allow_redirects=False)
        print(f"   Status: {login_get.status_code}")
        print(f"   Cookies after GET: {dict(session.cookies)}")
        
        if login_get.status_code == 200:
            # Extract CSRF token from HTML
            import re
            csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', login_get.text)
            if csrf_match:
                csrf_token = csrf_match.group(1)
                print(f"   CSRF token found: {csrf_token[:20]}...")
            else:
                print("   WARNING: CSRF token not found in HTML")
                csrf_token = None
        else:
            print(f"   ERROR: Expected 200, got {login_get.status_code}")
            csrf_token = None
    except Exception as e:
        print(f"   ERROR: {e}")
        return False
    
    # Step 2: Try to login (you'll need to provide credentials)
    print("\n2. Attempting login...")
    print("   NOTE: This test requires valid credentials.")
    print("   Please provide username and password, or skip this step.")
    
    # For now, we'll test with a dummy login to see the response
    # In real testing, you'd use actual credentials
    login_data = {
        'username': 'test_user',  # Replace with actual username
        'password': 'test_pass',   # Replace with actual password
        'csrf_token': csrf_token if csrf_token else ''
    }
    
    try:
        login_post = session.post(
            f"{base_url}/auth/login",
            data=login_data,
            allow_redirects=False,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        print(f"   Status: {login_post.status_code}")
        print(f"   Response: {login_post.text[:200]}")
        print(f"   Cookies after POST: {dict(session.cookies)}")
        
        # Check if session cookie is set
        session_cookie = session.cookies.get('session')
        if session_cookie:
            print(f"   ✅ Session cookie found: {session_cookie[:50]}...")
        else:
            print("   ❌ Session cookie NOT found!")
            print("   This is the problem - session cookie not being set")
            return False
        
    except Exception as e:
        print(f"   ERROR: {e}")
        return False
    
    # Step 3: Test navigation to protected routes
    print("\n3. Testing protected routes...")
    routes_to_test = [
        ('/analyzer', 'Analyzer'),
        ('/orders/orderbook', 'Orderbook'),
        ('/orders/tradebook', 'Tradebook'),
        ('/orders/positions', 'Positions'),
        ('/dashboard', 'Dashboard'),
    ]
    
    all_passed = True
    for route, name in routes_to_test:
        try:
            print(f"\n   Testing {name} ({route})...")
            response = session.get(f"{base_url}{route}", allow_redirects=False)
            print(f"      Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"      ✅ {name} accessible - session working!")
            elif response.status_code == 302:
                location = response.headers.get('Location', '')
                print(f"      ❌ Redirected to: {location}")
                if '/auth/login' in location:
                    print(f"      ❌ Session NOT persisting for {name}!")
                    all_passed = False
                else:
                    print(f"      ⚠️  Redirected (but not to login)")
            else:
                print(f"      ⚠️  Unexpected status: {response.status_code}")
                
        except Exception as e:
            print(f"      ERROR: {e}")
            all_passed = False
    
    # Step 4: Check session cookie attributes
    print("\n4. Checking session cookie attributes...")
    if session_cookie:
        # Get cookie details from session
        for cookie in session.cookies:
            if cookie.name == 'session':
                print(f"   Cookie name: {cookie.name}")
                print(f"   Cookie domain: {cookie.domain}")
                print(f"   Cookie path: {cookie.path}")
                print(f"   Cookie secure: {cookie.secure}")
                print(f"   Cookie httponly: {cookie.has_nonstandard_attr('HttpOnly')}")
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Session persistence working!")
    else:
        print("❌ SOME TESTS FAILED - Session persistence issues detected")
    print("="*70)
    
    return all_passed

if __name__ == "__main__":
    test_session_persistence()




