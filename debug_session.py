"""
Debug Session Issues
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, session, request
from app import app

def test_session_persistence():
    """Test if session persists between requests"""
    print("="*70)
    print("TESTING SESSION PERSISTENCE")
    print("="*70)
    
    with app.test_client() as client:
        # Simulate login POST
        print("\n1. Simulating login POST...")
        with client.session_transaction() as sess:
            sess['user'] = 'test_user'
            sess['logged_in'] = True
            sess['paper_trading_mode'] = True
            sess.permanent = True
            
            from utils.session import set_session_login_time
            set_session_login_time()
            sess.modified = True
        
        print(f"   Session after login: {dict(sess)}")
        
        # Make a GET request to orderbook
        print("\n2. Making GET request to /orders/orderbook...")
        response = client.get('/orders/orderbook', follow_redirects=False)
        print(f"   Status: {response.status_code}")
        print(f"   Location: {response.headers.get('Location', 'None')}")
        
        # Check if session cookie is in response
        cookies = response.headers.getlist('Set-Cookie')
        print(f"   Cookies set: {len(cookies)}")
        for cookie in cookies:
            print(f"     {cookie[:100]}")

if __name__ == "__main__":
    test_session_persistence()





