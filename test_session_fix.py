"""
Test script to verify session expiry fix
"""
import sys
from pathlib import Path
from datetime import datetime, time
import os

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.session import is_session_valid, get_session_expiry_time
import pytz

def test_session_logic():
    """Test the session expiry logic"""
    print("🧪 Testing Session Expiry Logic Fix")
    print("="*50)

    # Test 1: Check current session expiry calculation
    print("\n1. Current Session Expiry Time:")
    try:
        remaining = get_session_expiry_time()
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        expiry_time = now + remaining

        print(f"   Current time (IST): {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Next expiry time: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Remaining time: {remaining}")

        # Check if expiry is at 3:00 AM next day
        if expiry_time.hour == 3 and expiry_time.minute == 0:
            print("   ✅ Correctly set to 3:00 AM")
        else:
            print(f"   ❌ Incorrect expiry time: {expiry_time.hour}:{expiry_time.minute}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: Session validity logic
    print("\n2. Session Validity Test:")
    print("   (Note: This test assumes no active session)")

    try:
        valid = is_session_valid()
        if valid:
            print("   ✅ Session is valid (unexpected for test)")
        else:
            print("   ✅ Session is invalid (expected for test - no active session)")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Expiry time scenarios
    print("\n3. Expiry Time Scenarios:")

    # Scenario 1: Before 3:00 AM
    print("\n   Scenario 1: Current time before 3:00 AM")
    print("   Expected: Expiry should be today's 3:00 AM")

    # Scenario 2: After 3:00 AM
    print("\n   Scenario 2: Current time after 3:00 AM")
    print("   Expected: Expiry should be tomorrow's 3:00 AM")

    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    expiry_today = now.replace(hour=3, minute=0, second=0, microsecond=0)

    if now < expiry_today:
        print("   📅 Currently BEFORE 3:00 AM - expiry should be today")
        expected_expiry = expiry_today
    else:
        print("   📅 Currently AFTER 3:00 AM - expiry should be tomorrow")
        expected_expiry = expiry_today.replace(day=expiry_today.day + 1)

    print(f"   Expected expiry: {expected_expiry.strftime('%Y-%m-%d %H:%M:%S')}")

    # Test the actual calculation
    try:
        remaining = get_session_expiry_time()
        calculated_expiry = now + remaining

        if abs((calculated_expiry - expected_expiry).total_seconds()) < 60:  # Within 1 minute
            print("   ✅ Calculated expiry matches expected expiry")
        else:
            print(f"   ❌ Mismatch - calculated: {calculated_expiry}, expected: {expected_expiry}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "="*50)
    print("🧪 Test Complete")
    print("="*50)


if __name__ == "__main__":
    test_session_logic()





