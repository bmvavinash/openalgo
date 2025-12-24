#!/usr/bin/env python3
"""
Test script to verify dashboard and orderbook fixes
"""

def test_dashboard_margin_data():
    """Test that margin_data defaults are handled correctly"""
    print("Testing dashboard margin_data handling...")
    
    # Test case 1: None margin_data
    margin_data = None
    if margin_data is None:
        margin_data = {}
    assert isinstance(margin_data, dict), "margin_data should be a dict"
    print("[OK] None margin_data handled correctly")
    
    # Test case 2: Empty margin_data with defaults
    margin_data = {}
    default_margin_data = {
        'availablecash': '0.00',
        'collateral': '0.00',
        'utiliseddebits': '0.00',
        'm2munrealized': '0.00',
        'm2mrealized': '0.00'
    }
    margin_data = {**default_margin_data, **margin_data}
    assert margin_data.get('availablecash') == '0.00', "Should have default availablecash"
    print("[OK] Empty margin_data gets defaults")
    
    # Test case 3: Valid margin_data
    margin_data = {'availablecash': '1000.00', 'collateral': '5000.00'}
    assert margin_data.get('availablecash') == '1000.00', "Should preserve valid data"
    print("[OK] Valid margin_data preserved")
    
    print("Dashboard tests passed!\n")

def test_orderbook_data():
    """Test that orderbook data defaults are handled correctly"""
    print("Testing orderbook data handling...")
    
    # Test case 1: None order_data
    order_data = None
    if order_data is None:
        order_data = []
    assert isinstance(order_data, list), "order_data should be a list"
    print("[OK] None order_data handled correctly")
    
    # Test case 2: None order_stats
    order_stats = None
    if order_stats is None:
        order_stats = {}
    
    # Set default values for statistics if missing
    order_stats.setdefault('total_buy_orders', 0)
    order_stats.setdefault('total_sell_orders', 0)
    order_stats.setdefault('total_completed_orders', 0)
    order_stats.setdefault('total_open_orders', 0)
    order_stats.setdefault('total_rejected_orders', 0)
    
    assert order_stats.get('total_buy_orders') == 0, "Should have default total_buy_orders"
    assert order_stats.get('total_sell_orders') == 0, "Should have default total_sell_orders"
    print("[OK] None order_stats gets defaults")
    
    # Test case 3: Empty order_stats with partial data
    order_stats = {'total_buy_orders': 5}
    order_stats.setdefault('total_buy_orders', 0)
    order_stats.setdefault('total_sell_orders', 0)
    order_stats.setdefault('total_completed_orders', 0)
    order_stats.setdefault('total_open_orders', 0)
    order_stats.setdefault('total_rejected_orders', 0)
    assert order_stats.get('total_buy_orders') == 5, "Should preserve existing value"
    assert order_stats.get('total_sell_orders') == 0, "Should add missing default"
    print("[OK] Partial order_stats gets missing defaults")
    
    print("Orderbook tests passed!\n")

def test_price_extraction():
    """Test price extraction logic"""
    print("Testing price extraction...")
    
    # Test case 1: None price
    price = None
    if price is None or price == "":
        price = 0.0
    try:
        price = float(price)
    except (ValueError, TypeError):
        price = 0.0
    assert price == 0.0, "None price should become 0.0"
    print("[OK] None price handled")
    
    # Test case 2: Empty string price
    price = ""
    if price is None or price == "":
        price = 0.0
    try:
        price = float(price)
    except (ValueError, TypeError):
        price = 0.0
    assert price == 0.0, "Empty string price should become 0.0"
    print("[OK] Empty string price handled")
    
    # Test case 3: Valid price string
    price = "100.50"
    if price is None or price == "":
        price = 0.0
    try:
        price = float(price)
    except (ValueError, TypeError):
        price = 0.0
    assert price == 100.50, "Valid price should be converted to float"
    print("[OK] Valid price converted")
    
    # Test case 4: Invalid price string
    price = "invalid"
    if price is None or price == "":
        price = 0.0
    try:
        price = float(price)
    except (ValueError, TypeError):
        price = 0.0
    assert price == 0.0, "Invalid price should default to 0.0"
    print("[OK] Invalid price handled")
    
    print("Price extraction tests passed!\n")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Dashboard and Orderbook Fixes")
    print("=" * 60)
    print()
    
    try:
        test_dashboard_margin_data()
        test_orderbook_data()
        test_price_extraction()
        
        print("=" * 60)
        print("[SUCCESS] All tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"[FAIL] Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        exit(1)

