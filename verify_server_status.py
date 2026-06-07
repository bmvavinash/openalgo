#!/usr/bin/env python3
"""
Quick verification script to check server status and components
"""
import requests
import sys
import time

def check_server():
    """Check if server is running and components are accessible"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n" + "="*60)
    print("SERVER STATUS CHECK")
    print("="*60)
    
    checks = []
    
    # Check 1: Home page
    try:
        r = requests.get(f"{base_url}/", timeout=5)
        checks.append(("Home Page", r.status_code in [200, 302], r.status_code))
    except Exception as e:
        checks.append(("Home Page", False, str(e)))
    
    # Check 2: Strategy Performance Dashboard (may require auth)
    try:
        r = requests.get(f"{base_url}/strategy-performance/", timeout=5)
        checks.append(("Strategy Performance Dashboard", r.status_code in [200, 302, 401], r.status_code))
    except Exception as e:
        checks.append(("Strategy Performance Dashboard", False, str(e)))
    
    # Check 3: Strategy Performance API (may require auth)
    try:
        r = requests.get(f"{base_url}/strategy-performance/categories", timeout=5)
        checks.append(("Strategy Performance API", r.status_code in [200, 401], r.status_code))
    except Exception as e:
        checks.append(("Strategy Performance API", False, str(e)))
    
    # Print results
    all_ok = True
    for name, ok, status in checks:
        status_text = "[OK]" if ok else "[FAIL]"
        print(f"{status_text} {name}: {status}")
        if not ok:
            all_ok = False
    
    print("\n" + "="*60)
    if all_ok:
        print("[OK] Server is running and components are accessible!")
        print("\nAccess the dashboard at: http://127.0.0.1:5000/strategy-performance/")
    else:
        print("[WARNING] Some checks failed. Server may still be starting...")
        print("Wait a few seconds and try again.")
    
    return all_ok

if __name__ == "__main__":
    # Wait a bit for server to start
    print("Waiting for server to start...")
    time.sleep(3)
    
    if check_server():
        sys.exit(0)
    else:
        sys.exit(1)







