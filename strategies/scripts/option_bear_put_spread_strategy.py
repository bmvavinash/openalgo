#!/usr/bin/env python
"""
Option Bear Put Spread Strategy
Buy ITM/ATM Put + Sell OTM Put
Bearish strategy with limited risk and limited profit
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
strategy_name = "Bear Put Spread"
underlying = os.getenv('UNDERLYING', 'NIFTY')
exchange = os.getenv('EXCHANGE', 'NSE_INDEX')
expiry_date = os.getenv('EXPIRY_DATE', '')
strike_int = int(os.getenv('STRIKE_INT', '50'))
buy_offset = os.getenv('BUY_OFFSET', 'ITM2')  # ITM/ATM for long put
sell_otm = int(os.getenv('SELL_OTM', '5'))    # OTM level for short put
quantity = int(os.getenv('QUANTITY', '75'))
product = os.getenv('PRODUCT', 'MIS')
pricetype = os.getenv('PRICETYPE', 'MARKET')

# Initialize OpenAlgo client
client = api(api_key=api_key, host=os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000'))

# Track position
position_open = False

def place_bear_put_spread():
    """Place a Bear Put Spread using optionsmultiorder API"""
    try:
        print(f"[{datetime.now()}] Placing {strategy_name} for {underlying}")
        print(f"Buy: {buy_offset} Put, Sell: OTM{sell_otm} Put")
        
        # Bear Put Spread legs:
        # 1. Buy ITM/ATM Put (long leg)
        # 2. Sell OTM Put (short leg)
        
        response = client.optionsmultiorder(
            strategy=strategy_name,
            underlying=underlying,
            exchange=exchange,
            expiry_date=expiry_date,
            legs=[
                {"offset": buy_offset, "option_type": "PE", "action": "BUY", "quantity": quantity},
                {"offset": f"OTM{sell_otm}", "option_type": "PE", "action": "SELL", "quantity": quantity}
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
        print(f"[{datetime.now()}] Error placing Bear Put Spread: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main strategy loop"""
    print(f"Starting {strategy_name} Strategy")
    print(f"Underlying: {underlying}, Exchange: {exchange}")
    print(f"Expiry: {expiry_date}, Quantity: {quantity}, Product: {product}")
    print(f"Buy: {buy_offset}, Sell: OTM{sell_otm}")
    print("-" * 70)
    
    # Place Bear Put Spread
    place_bear_put_spread()
    
    try:
        while True:
            time.sleep(60)  # Check every minute
            # Add exit logic here
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Strategy stopped by user")

if __name__ == "__main__":
    main()

