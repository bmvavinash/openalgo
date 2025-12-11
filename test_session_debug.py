"""
Debug script to test session validation logic
"""
import sys
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set up Flask context for testing
from flask import Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test_key'

with app.app_context():
    from utils.session import is_session_valid, get_session_expiry_time
    from flask import session
    import datetime
    import pytz

    def test_session_validation():
        """Test session validation logic"""
        print("🧪 Testing Session Validation Logic")
        print("="*50)

        # Test 1: Current expiry time calculation
        print("\n1. Current Session Expiry Time:")
        try:
            remaining = get_session_expiry_time()
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.datetime.now(ist)
            expiry_time = now + remaining

            print(f"   Current time (IST): {now.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Next expiry time: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Remaining time: {remaining}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 2: Manual session validation logic
        print("\n2. Manual Session Validation Test:")

        # Simulate a session like what would be set during login
        session.clear()
        session['logged_in'] = True
        session['user'] = 'test_user'

        # Set login time to current time
        from utils.session import set_session_login_time
        set_session_login_time()

        print(f"   Session data: {dict(session)}")

        # Test validation
        try:
            valid = is_session_valid()
            if valid:
                print("   ✅ Session validation passed")
            else:
                print("   ❌ Session validation failed")

            # Check what the expiry calculation gives
            remaining = get_session_expiry_time()
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.datetime.now(ist)
            expiry_time = now + remaining

            print(f"   Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Expiry time: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Is current time > expiry time? {now > expiry_time}")

        except Exception as e:
            print(f"   ❌ Error during validation: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "="*50)
        print("🧪 Test Complete")


    if __name__ == "__main__":
        test_session_validation()




