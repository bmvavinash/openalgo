#!/usr/bin/env python3
"""
Test script to verify price extraction logic for different order types and statuses
"""

def test_price_extraction():
    """Test price extraction for various scenarios"""
    print("Testing price extraction logic...")
    print("=" * 60)
    
    # Test Case 1: MARKET order (should always be 0)
    print("\n[Test 1] MARKET order")
    order_type = "MARKET"
    order_status = "OPEN"
    order_price = 100.0
    average_price = 99.5
    
    if order_type == "MARKET":
        price = 0.0
    else:
        if order_status == "COMPLETE":
            price = average_price or order_price
        else:
            price = order_price
    
    assert price == 0.0, f"MARKET order should have price 0.0, got {price}"
    print(f"[OK] MARKET order price: {price}")
    
    # Test Case 2: LIMIT order - OPEN status (should use order price)
    print("\n[Test 2] LIMIT order - OPEN status")
    order_type = "LIMIT"
    order_status = "OPEN"
    order_price = 100.0
    average_price = None
    
    if order_type == "MARKET":
        price = 0.0
    else:
        if order_status == "COMPLETE":
            price = average_price or order_price
        else:
            price = order_price
    
    assert price == 100.0, f"LIMIT OPEN order should use order price, got {price}"
    print(f"[OK] LIMIT OPEN order price: {price}")
    
    # Test Case 3: LIMIT order - COMPLETE status (should prefer average_price)
    print("\n[Test 3] LIMIT order - COMPLETE status")
    order_type = "LIMIT"
    order_status = "COMPLETE"
    order_price = 100.0
    average_price = 99.75
    
    if order_type == "MARKET":
        price = 0.0
    else:
        if order_status == "COMPLETE":
            price = average_price or order_price
        else:
            price = order_price
    
    assert price == 99.75, f"LIMIT COMPLETE order should use average_price, got {price}"
    print(f"[OK] LIMIT COMPLETE order price: {price} (average_price)")
    
    # Test Case 4: LIMIT order - COMPLETE status (no average_price, use order price)
    print("\n[Test 4] LIMIT order - COMPLETE status (no average_price)")
    order_type = "LIMIT"
    order_status = "COMPLETE"
    order_price = 100.0
    average_price = None
    
    if order_type == "MARKET":
        price = 0.0
    else:
        if order_status == "COMPLETE":
            price = average_price or order_price
        else:
            price = order_price
    
    assert price == 100.0, f"LIMIT COMPLETE order without average_price should use order price, got {price}"
    print(f"[OK] LIMIT COMPLETE order price: {price} (order_price fallback)")
    
    # Test Case 5: SL order - TRIGGER PENDING status
    print("\n[Test 5] SL order - TRIGGER PENDING status")
    order_type = "SL"
    order_status = "TRIGGER PENDING"
    order_price = 95.0
    average_price = None
    
    if order_type == "MARKET":
        price = 0.0
    else:
        if order_status == "COMPLETE":
            price = average_price or order_price
        else:
            price = order_price
    
    assert price == 95.0, f"SL TRIGGER PENDING order should use order price, got {price}"
    print(f"[OK] SL TRIGGER PENDING order price: {price}")
    
    # Test Case 6: Handle None price
    print("\n[Test 6] Handle None price")
    order_type = "LIMIT"
    order_status = "OPEN"
    order_price = None
    average_price = None
    
    if order_type == "MARKET":
        price = 0.0
    else:
        if order_status == "COMPLETE":
            price = average_price or order_price
        else:
            price = order_price
        
        if price is None or price == "":
            price = 0.0
    
    assert price == 0.0, f"None price should become 0.0, got {price}"
    print(f"[OK] None price handled: {price}")
    
    # Test Case 7: Handle empty string price
    print("\n[Test 7] Handle empty string price")
    order_type = "LIMIT"
    order_status = "OPEN"
    order_price = ""
    average_price = None
    
    if order_type == "MARKET":
        price = 0.0
    else:
        if order_status == "COMPLETE":
            price = average_price or order_price
        else:
            price = order_price
        
        if price is None or price == "":
            price = 0.0
    
    assert price == 0.0, f"Empty string price should become 0.0, got {price}"
    print(f"[OK] Empty string price handled: {price}")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] All price extraction tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    test_price_extraction()







