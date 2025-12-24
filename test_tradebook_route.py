#!/usr/bin/env python
"""Test tradebook route to verify no redirects"""
import requests
import sys

def test_tradebook_route():
    """Test tradebook route without session"""
    try:
        # Test without session (should return 200 with empty data, not redirect)
        response = requests.get('http://127.0.0.1:5000/tradebook', allow_redirects=False)
        print(f"Status Code: {response.status_code}")
        print(f"Headers Location: {response.headers.get('Location', 'None')}")
        print(f"Content Length: {len(response.content)}")
        
        if response.status_code == 302:
            print("ERROR: Route is redirecting!")
            print(f"Redirects to: {response.headers.get('Location')}")
            return False
        elif response.status_code == 200:
            print("SUCCESS: Route returns 200 (no redirect)")
            return True
        else:
            print(f"Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error testing route: {e}")
        return False

if __name__ == "__main__":
    success = test_tradebook_route()
    sys.exit(0 if success else 1)




