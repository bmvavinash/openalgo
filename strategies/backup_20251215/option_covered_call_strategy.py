#!/usr/bin/env python
"""
Option Covered Call Strategy
Long stock/underlying + Sell Call option
Income generation strategy
Note: This assumes you already have a long position in the underlying
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
strategy_name = "Covered Call"
underlying = os.getenv('UNDERLYING', 'NIFTY')
exchange = os.getenv('EXCHANGE', 'NSE_INDEX')
expiry_date = os.getenv('EXPIRY_DATE', '')
strike_int = int(os.getenv('STRIKE_INT', '50'))
call_otm = int(os.getenv('CALL_OTM', '2'))  # OTM level for covered call
quantity = int(os.getenv('QUANTITY', '75'))
product = os.getenv('PRODUCT', 'NRML')  # Usually NRML for covered strategies
pricetype = os.getenv('PRICETYPE', 'MARKET')

# Initialize OpenAlgo client
client = api(api_key=api_key, host=os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000'))

# Track position
call_orderid = None
call_symbol = None
position_open = False

def place_covered_call():
    """Place a covered call (sell call)"""
    try:
        print(f"[{datetime.now()}] Placing {strategy_name} for {underlying}")
        print(f"Selling OTM{call_otm} Call against long position")
        
        # Place Call order (SELL)
        response = client.optionsorder(
            strategy=strategy_name,
            underlying=underlying,
            exchange=exchange,
            expiry_date=expiry_date,
            offset=f"OTM{call_otm}",
            option_type="CE",
            action="SELL",
            quantity=quantity,
            pricetype=pricetype,
            product=product
        )
        
        if response.get('status') == 'success':
            global call_orderid, call_symbol, position_open
            call_orderid = response.get('orderid')
            call_symbol = response.get('symbol')
            position_open = True
            print(f"[{datetime.now()}] Covered Call placed: {call_orderid} - {call_symbol}")
            print(f"[{datetime.now()}] {strategy_name} active")
            return True
        else:
            print(f"[{datetime.now()}] Covered Call failed: {response.get('message')}")
            return False
            
    except Exception as e:
        print(f"[{datetime.now()}] Error placing Covered Call: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def close_covered_call():
    """Close the covered call (buy back the call)"""
    global position_open, call_symbol
    if not position_open:
        print(f"[{datetime.now()}] No open covered call to close")
        return False
    
    try:
        print(f"[{datetime.now()}] Closing {strategy_name}")
        
        option_exchange = exchange.replace('_INDEX', '') if '_INDEX' in exchange else 'NFO'
        
        if call_symbol:
            close_response = client.placeorder(
                strategy=strategy_name,
                symbol=call_symbol,
                exchange=option_exchange,
                action="BUY",  # Buy back to close
                quantity=quantity,
                pricetype=pricetype,
                product=product
            )
            print(f"[{datetime.now()}] Covered Call closed: {close_response}")
        
        position_open = False
        return True
        
    except Exception as e:
        print(f"[{datetime.now()}] Error closing Covered Call: {str(e)}")
        return False

def main():
    """Main strategy loop"""
    if not expiry_date:
        print(f"[{datetime.now()}] Missing EXPIRY_DATE configuration. Skipping execution.")
        return
    print(f"Starting {strategy_name} Strategy")
    print(f"Underlying: {underlying}, Exchange: {exchange}")
    print(f"Expiry: {expiry_date}, Call OTM: {call_otm}, Quantity: {quantity}")
    print("Note: This strategy assumes you have a long position in the underlying")
    print("-" * 70)
    
    # Place covered call
    place_covered_call()
    
    try:
        while True:
            time.sleep(60)  # Check every minute
            # Add exit logic here:
            # - Close call if underlying moves significantly (roll or exit)
            # - Close call if approaching expiry and profitable
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Strategy stopped by user")
        if position_open:
            close_covered_call()

if __name__ == "__main__":
    main()

