#!/usr/bin/env python
"""
Option Protective Put Strategy
Long stock/underlying + Buy Put option
Protective strategy to limit downside risk
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
strategy_name = "Protective Put"
underlying = os.getenv('UNDERLYING', 'NIFTY')
exchange = os.getenv('EXCHANGE', 'NSE_INDEX')
expiry_date = os.getenv('EXPIRY_DATE', '')
strike_int = int(os.getenv('STRIKE_INT', '50'))
put_offset = os.getenv('PUT_OFFSET', 'OTM2')  # OTM level for protective put
quantity = int(os.getenv('QUANTITY', '75'))
product = os.getenv('PRODUCT', 'NRML')  # Usually NRML for protective strategies
pricetype = os.getenv('PRICETYPE', 'MARKET')

# Initialize OpenAlgo client
client = api(api_key=api_key, host=os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000'))

# Track position
put_orderid = None
put_symbol = None
position_open = False

def place_protective_put():
    """Place a protective put"""
    try:
        print(f"[{datetime.now()}] Placing {strategy_name} for {underlying}")
        print(f"Buying {put_offset} Put to protect long position")
        
        # Place Put order
        response = client.optionsorder(
            strategy=strategy_name,
            underlying=underlying,
            exchange=exchange,
            expiry_date=expiry_date,
            offset=put_offset,
            option_type="PE",
            action="BUY",
            quantity=quantity,
            pricetype=pricetype,
            product=product
        )
        
        if response.get('status') == 'success':
            global put_orderid, put_symbol, position_open
            put_orderid = response.get('orderid')
            put_symbol = response.get('symbol')
            position_open = True
            print(f"[{datetime.now()}] Protective Put placed: {put_orderid} - {put_symbol}")
            print(f"[{datetime.now()}] {strategy_name} active")
            return True
        else:
            print(f"[{datetime.now()}] Protective Put failed: {response.get('message')}")
            return False
            
    except Exception as e:
        print(f"[{datetime.now()}] Error placing Protective Put: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def close_protective_put():
    """Close the protective put"""
    global position_open, put_symbol
    if not position_open:
        print(f"[{datetime.now()}] No open protective put to close")
        return False
    
    try:
        print(f"[{datetime.now()}] Closing {strategy_name}")
        
        option_exchange = exchange.replace('_INDEX', '') if '_INDEX' in exchange else 'NFO'
        
        if put_symbol:
            close_response = client.placeorder(
                strategy=strategy_name,
                symbol=put_symbol,
                exchange=option_exchange,
                action="SELL",
                quantity=quantity,
                pricetype=pricetype,
                product=product
            )
            print(f"[{datetime.now()}] Protective Put closed: {close_response}")
        
        position_open = False
        return True
        
    except Exception as e:
        print(f"[{datetime.now()}] Error closing Protective Put: {str(e)}")
        return False

def main():
    """Main strategy loop"""
    if not expiry_date:
        print(f"[{datetime.now()}] Missing EXPIRY_DATE configuration. Skipping execution.")
        return
    print(f"Starting {strategy_name} Strategy")
    print(f"Underlying: {underlying}, Exchange: {exchange}")
    print(f"Expiry: {expiry_date}, Put Offset: {put_offset}, Quantity: {quantity}")
    print("Note: This strategy assumes you have a long position in the underlying")
    print("-" * 70)
    
    # Place protective put
    place_protective_put()
    
    try:
        while True:
            time.sleep(60)  # Check every minute
            # Add exit logic here:
            # - Close put if underlying moves significantly up (profit protection)
            # - Roll put if approaching expiry
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Strategy stopped by user")
        if position_open:
            close_protective_put()

if __name__ == "__main__":
    main()

