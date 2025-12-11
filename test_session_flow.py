"""
Test Session Flow
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask
from app import app

def test_session_logic():
    """Test session validation logic"""
    print("="*70)
    print("TESTING SESSION LOGIC")
    print("="*70)
    
    from utils.session import is_session_valid, set_session_login_time
    from flask import session
    
    with app.test_client() as client:
        # Simulate login
        with client.session_transaction() as sess:
            sess['user'] = 'test_user'
            sess['logged_in'] = True
            sess.permanent = True
            set_session_login_time()
            sess.modified = True
        
        print("\n1. Session after login:")
        print(f"   logged_in: {session.get('logged_in')}")
        print(f"   user: {session.get('user')}")
        print(f"   login_time: {session.get('login_time')}")
        print(f"   is_valid: {is_session_valid()}")
        
        # Test session validity
        result = is_session_valid()
        print(f"\n2. Session validity check: {result}")
        
        if not result:
            print("\n   ERROR: Session is invalid after login!")
            print("   This is the problem!")

if __name__ == "__main__":
    test_session_logic()





