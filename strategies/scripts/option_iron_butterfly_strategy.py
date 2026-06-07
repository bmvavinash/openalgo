#!/usr/bin/env python
"""
Option Iron Butterfly Strategy
Sell ATM Call + Sell ATM Put, Buy OTM Call + Buy OTM Put
Neutral strategy with maximum profit at ATM
Uses optionsmultiorder API for efficient execution
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
strategy_name = "Iron Butterfly"
underlying = os.getenv('UNDERLYING', 'NIFTY')
exchange = os.getenv('EXCHANGE', 'NSE_INDEX')
expiry_date = os.getenv('EXPIRY_DATE', '')
strike_int = int(os.getenv('STRIKE_INT', '50'))
wing_otm = int(os.getenv('WING_OTM', '5'))  # OTM level for long wings
quantity = int(os.getenv('QUANTITY', '75'))
product = os.getenv('PRODUCT', 'MIS')
pricetype = os.getenv('PRICETYPE', 'MARKET')

# Initialize OpenAlgo client
client = api(api_key=api_key, host=os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000'))

# Track position
position_open = False

def place_iron_butterfly():
    """Place an Iron Butterfly using optionsmultiorder API"""
    try:
        print(f"[{datetime.now()}] Placing {strategy_name} for {underlying}")
        print(f"Short strikes: ATM, Long strikes (wings): OTM{wing_otm}")
        
        # Iron Butterfly legs:
        # 1. Buy OTM Call (upper wing)
        # 2. Buy OTM Put (lower wing)
        # 3. Sell ATM Call
        # 4. Sell ATM Put
        
        response = client.optionsmultiorder(
            strategy=strategy_name,
            underlying=underlying,
            exchange=exchange,
            expiry_date=expiry_date,
            legs=[
                {"offset": f"OTM{wing_otm}", "option_type": "CE", "action": "BUY", "quantity": quantity},
                {"offset": f"OTM{wing_otm}", "option_type": "PE", "action": "BUY", "quantity": quantity},
                {"offset": "ATM", "option_type": "CE", "action": "SELL", "quantity": quantity},
                {"offset": "ATM", "option_type": "PE", "action": "SELL", "quantity": quantity}
            ]
        )
        
        if response.get('status') == 'success':
            global position_open
            position_open = True
            print(f"[{datetime.now()}] {strategy_name} opened successfully")
            print(f"Results: {len(response.get('results', []))} legs executed")
                        for leg in response.get('results', []):
                leg_status = leg.get('status', 'unknown')
                leg_orderid = leg.get('orderid', 'N/A')
                leg_message = leg.get('message', '')
                if leg_status == 'success':
                    print(f"  Leg {leg.get('leg')}: {leg.get('action')} {leg.get('option_type')} "
                          f"{leg.get('offset')} - {leg_status} - OrderID: {leg_orderid}")
                else:
                    error_msg = leg_message or 'Unknown error'
                    print(f"  Leg {leg.get('leg')}: {leg.get('action')} {leg.get('option_type')} "
                          f"{leg.get('offset')} - {leg_status} - Error: {error_msg}")
            return True
        else:
            print(f"[{datetime.now()}] {strategy_name} failed: {response.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"[{datetime.now()}] Error placing Iron Butterfly: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main strategy loop"""
    print(f"Starting {strategy_name} Strategy")
    print(f"Underlying: {underlying}, Exchange: {exchange}")
    print(f"Expiry: {expiry_date}, Quantity: {quantity}, Product: {product}")
    print(f"Wing OTM: {wing_otm}")
    print("-" * 70)
    
    # Place Iron Butterfly
    place_iron_butterfly()
    
    try:
        while True:
            time.sleep(60)  # Check every minute
            # Add exit logic here
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Strategy stopped by user")

if __name__ == "__main__":
    main()

