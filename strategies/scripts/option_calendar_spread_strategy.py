#!/usr/bin/env python
"""
Option Calendar Spread Strategy
Sell near-term option + Buy far-term option (same strike)
Time decay strategy - profits from time decay difference
Note: This requires two different expiry dates
"""
from openalgo import api
import os
import time
from datetime import datetime

# Get API key from environment
api_key = os.getenv('OPENALGO_API_KEY', os.getenv('OPENALGO_APIKEY'))
if not api_key:
    print("Error: OPENALGO_API_KEY environment variable not set")
    exit(1)

# Strategy configuration
strategy_name = "Calendar Spread"
underlying = os.getenv('UNDERLYING', 'NIFTY')
exchange = os.getenv('EXCHANGE', 'NSE_INDEX')
near_expiry = os.getenv('NEAR_EXPIRY', '')  # Near-term expiry (DDMMMYY)
far_expiry = os.getenv('FAR_EXPIRY', '')    # Far-term expiry (DDMMMYY)
strike_int = int(os.getenv('STRIKE_INT', '50'))
strike_offset = os.getenv('STRIKE_OFFSET', 'ATM')  # ATM, ITM, or OTM
option_type = os.getenv('OPTION_TYPE', 'CE')  # CE or PE
quantity = int(os.getenv('QUANTITY', '75'))
product = os.getenv('PRODUCT', 'NRML')  # Usually NRML for calendar spreads
pricetype = os.getenv('PRICETYPE', 'MARKET')

# Initialize OpenAlgo client
client = api(api_key=api_key, host=os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000'))

# Track positions
near_orderid = None
far_orderid = None
near_symbol = None
far_symbol = None
position_open = False

def place_calendar_spread():
    """Place a calendar spread"""
    try:
        print(f"[{datetime.now()}] Placing {strategy_name} for {underlying}")
        print(f"Sell {near_expiry} {strike_offset} {option_type}, Buy {far_expiry} {strike_offset} {option_type}")
        
        if not near_expiry or not far_expiry:
            print("Error: Both NEAR_EXPIRY and FAR_EXPIRY must be set")
            return False
        
        # Step 1: Sell near-term option
        near_response = client.optionsorder(
            strategy=strategy_name,
            underlying=underlying,
            exchange=exchange,
            expiry_date=near_expiry,
            offset=strike_offset,
            option_type=option_type,
            action="SELL",
            quantity=quantity,
            pricetype=pricetype,
            product=product
        )
        
        if near_response.get('status') != 'success':
            print(f"[{datetime.now()}] Near-term order failed: {near_response.get('message')}")
            return False
        
        global near_orderid, near_symbol
        near_orderid = near_response.get('orderid')
        near_symbol = near_response.get('symbol')
        print(f"[{datetime.now()}] Near-term {option_type} sold: {near_orderid} - {near_symbol}")
        
        # Step 2: Buy far-term option
        far_response = client.optionsorder(
            strategy=strategy_name,
            underlying=underlying,
            exchange=exchange,
            expiry_date=far_expiry,
            offset=strike_offset,
            option_type=option_type,
            action="BUY",
            quantity=quantity,
            pricetype=pricetype,
            product=product
        )
        
        if far_response.get('status') != 'success':
            print(f"[{datetime.now()}] Far-term order failed: {far_response.get('message')}")
            # Note: In production, you might want to close the near-term position if far-term fails
            return False
        
        global far_orderid, far_symbol, position_open
        far_orderid = far_response.get('orderid')
        far_symbol = far_response.get('symbol')
        position_open = True
        print(f"[{datetime.now()}] Far-term {option_type} bought: {far_orderid} - {far_symbol}")
        print(f"[{datetime.now()}] {strategy_name} opened successfully")
        return True
            
    except Exception as e:
        print(f"[{datetime.now()}] Error placing Calendar Spread: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def close_calendar_spread():
    """Close the calendar spread"""
    if not position_open:
        print(f"[{datetime.now()}] No open calendar spread to close")
        return False
    
    try:
        print(f"[{datetime.now()}] Closing {strategy_name}")
        
        option_exchange = exchange.replace('_INDEX', '') if '_INDEX' in exchange else 'NFO'
        
        # Close near-term (buy back)
        if near_symbol:
            near_close = client.placeorder(
                strategy=strategy_name,
                symbol=near_symbol,
                exchange=option_exchange,
                action="BUY",
                quantity=quantity,
                pricetype=pricetype,
                product=product
            )
            print(f"[{datetime.now()}] Near-term closed: {near_close}")
        
        # Close far-term (sell)
        if far_symbol:
            far_close = client.placeorder(
                strategy=strategy_name,
                symbol=far_symbol,
                exchange=option_exchange,
                action="SELL",
                quantity=quantity,
                pricetype=pricetype,
                product=product
            )
            print(f"[{datetime.now()}] Far-term closed: {far_close}")
        
        global position_open
        position_open = False
        return True
        
    except Exception as e:
        print(f"[{datetime.now()}] Error closing Calendar Spread: {str(e)}")
        return False

def main():
    """Main strategy loop"""
    print(f"Starting {strategy_name} Strategy")
    print(f"Underlying: {underlying}, Exchange: {exchange}")
    print(f"Near Expiry: {near_expiry}, Far Expiry: {far_expiry}")
    print(f"Strike: {strike_offset}, Type: {option_type}, Quantity: {quantity}")
    print("-" * 70)
    
    # Place calendar spread
    place_calendar_spread()
    
    try:
        while True:
            time.sleep(60)  # Check every minute
            # Add exit logic here:
            # - Close when near-term expires
            # - Close if profit target reached
            # - Roll if needed
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Strategy stopped by user")
        if position_open:
            close_calendar_spread()

if __name__ == "__main__":
    main()
