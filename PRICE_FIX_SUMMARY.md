# Price Extraction Fix Summary

## Issue
Orderbook was showing prices as 0 for LIMIT orders, even when they should display the order price or average execution price.

## Root Cause
The price extraction logic in broker mapping functions was not properly handling:
1. Different order types (MARKET vs LIMIT/SL)
2. Different order statuses (OPEN vs COMPLETE)
3. Preference for average_price over order price for completed orders

## Changes Made

### 1. Enhanced Price Extraction Logic
Updated price extraction in all broker mappings to:
- **MARKET orders**: Always show 0.0 (correct behavior)
- **LIMIT/SL orders - COMPLETE status**: Prefer `average_price` (execution price) over `order_price`
- **LIMIT/SL orders - OPEN/PENDING status**: Use `order_price`
- **Handle edge cases**: None, empty strings, type conversion errors

### 2. Files Modified
- `openalgo/broker/zerodha/mapping/order_data.py`
- `openalgo/broker/upstox/mapping/order_data.py`
- `openalgo/broker/wisdom/mapping/order_data.py`
- `openalgo/broker/zebu/mapping/order_data.py`

### 3. Price Logic Flow

```
IF order_type == "MARKET":
    price = 0.0
ELSE:
    IF order_status == "COMPLETE":
        price = average_price OR order_price  # Prefer average_price
    ELSE:
        price = order_price  # Use order price for open/pending orders
    
    # Handle None/empty/type errors
    IF price is None OR price == "":
        price = 0.0
    ELSE:
        price = float(price)  # Convert with error handling
```

## Impact

### Immediate Effect
- **Server restart required**: Yes, changes take effect after server restart
- **Existing orders**: Will show correct prices after server restart
- **New orders**: Will automatically use the new logic

### Behavior Changes
1. **MARKET orders**: Continue to show 0.00 (correct)
2. **LIMIT orders - OPEN**: Now show order price (was showing 0)
3. **LIMIT orders - COMPLETE**: Show average execution price (was showing 0 or order price)
4. **SL orders**: Show trigger price correctly

## Testing

### Test Results
All price extraction scenarios tested and verified:
- ✅ MARKET orders → 0.0
- ✅ LIMIT OPEN orders → order price
- ✅ LIMIT COMPLETE orders → average_price (preferred)
- ✅ SL orders → order/trigger price
- ✅ None/empty price handling
- ✅ Type conversion error handling

### Server Status
- ✅ Server restarted with new code
- ✅ Dashboard endpoint working (Status 200)
- ✅ No linter errors

## Next Steps

1. **Monitor orderbook**: Check if prices are now displaying correctly
2. **Check logs**: If prices still show 0, check debug logs for "Zero price detected" messages
3. **Verify broker API**: Ensure broker API is returning price fields correctly

## Debugging

If prices still show as 0:
1. Check server logs for "Zero price detected" debug messages
2. Verify broker API response includes `price` and `average_price` fields
3. Check order status - REJECTED/CANCELLED orders may legitimately have 0 price
4. Verify order type - MARKET orders correctly show 0

## Notes

- The fix applies to **all future order fetches** after server restart
- Existing orders in the database will show correct prices on next refresh
- The template already handles displaying "-" for missing prices (except MARKET orders)

