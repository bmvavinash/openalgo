#!/usr/bin/env python
"""
Option Strangle Strategy
Buy OTM Call + OTM Put simultaneously
Lower cost than straddle, profits from large price movements
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
strategy_name = "Option Strangle"
underlying = os.getenv('UNDERLYING', 'NIFTY')
exchange = os.getenv('EXCHANGE', 'NSE_INDEX')
expiry_date = os.getenv('EXPIRY_DATE', '')
strike_int = int(os.getenv('STRIKE_INT', '50'))
otm_level = int(os.getenv('OTM_LEVEL', '2'))  # OTM level (e.g., 2 = OTM2)
quantity = int(os.getenv('QUANTITY', '75'))
product = os.getenv('PRODUCT', 'MIS')
pricetype = os.getenv('PRICETYPE', 'MARKET')

# Initialize OpenAlgo client
client = api(api_key=api_key, host=os.getenv('OPENALGO_HOST', 'http://127.0.0.1:5000'))

# Track positions
positions = {
    'call_orderid': None,
    'put_orderid': None,
    'call_symbol': None,
    'put_symbol': None,
    'is_open': False
}

def place_strangle():
    """Place a strangle: Buy OTM Call + OTM Put"""
    try:
        print(f"[{datetime.now()}] Placing {strategy_name} for {underlying} (OTM{otm_level})")
        
        # Place Call order
        call_response = client.optionsorder(
            strategy=strategy_name,
            underlying=underlying,
            exchange=exchange,
            expiry_date=expiry_date,
            offset=f"OTM{otm_level}",
            option_type="CE",
            action="BUY",
            quantity=quantity,
            pricetype=pricetype,
            product=product
        )
        
        if call_response.get('status') == 'success':
            positions['call_orderid'] = call_response.get('orderid')
            positions['call_symbol'] = call_response.get('symbol')
            print(f"[{datetime.now()}] Call order placed: {positions['call_orderid']} - {positions['call_symbol']}")
        else:
            print(f"[{datetime.now()}] Call order failed: {call_response.get('message')}")
            return False
        
        # Place Put order
        put_response = client.optionsorder(
            strategy=strategy_name,
            underlying=underlying,
            exchange=exchange,
            expiry_date=expiry_date,
            offset=f"OTM{otm_level}",
            option_type="PE",
            action="BUY",
            quantity=quantity,
            pricetype=pricetype,
            product=product
        )
        
        if put_response.get('status') == 'success':
            positions['put_orderid'] = put_response.get('orderid')
            positions['put_symbol'] = put_response.get('symbol')
            positions['is_open'] = True
            print(f"[{datetime.now()}] Put order placed: {positions['put_orderid']} - {positions['put_symbol']}")
            print(f"[{datetime.now()}] {strategy_name} opened successfully")
            return True
        else:
            print(f"[{datetime.now()}] Put order failed: {put_response.get('message')}")
            return False
            
    except Exception as e:
        print(f"[{datetime.now()}] Error placing strangle: {str(e)}")
        return False

def close_strangle():
    """Close the strangle: Sell both positions"""
    if not positions['is_open']:
        print(f"[{datetime.now()}] No open strangle position to close")
        return False
    
    try:
        print(f"[{datetime.now()}] Closing {strategy_name}")
        
        option_exchange = exchange.replace('_INDEX', '') if '_INDEX' in exchange else 'NFO'
        
        # Close Call
        if positions['call_symbol']:
            call_close = client.placeorder(
                strategy=strategy_name,
                symbol=positions['call_symbol'],
                exchange=option_exchange,
                action="SELL",
                quantity=quantity,
                pricetype=pricetype,
                product=product
            )
            print(f"[{datetime.now()}] Call close: {call_close}")
        
        # Close Put
        if positions['put_symbol']:
            put_close = client.placeorder(
                strategy=strategy_name,
                symbol=positions['put_symbol'],
                exchange=option_exchange,
                action="SELL",
                quantity=quantity,
                pricetype=pricetype,
                product=product
            )
            print(f"[{datetime.now()}] Put close: {put_close}")
        
        positions['is_open'] = False
        print(f"[{datetime.now()}] {strategy_name} closed")
        return True
        
    except Exception as e:
        print(f"[{datetime.now()}] Error closing strangle: {str(e)}")
        return False

def main():
    """Main strategy loop"""
    print(f"Starting {strategy_name} Strategy")
    print(f"Underlying: {underlying}, Exchange: {exchange}")
    print(f"Expiry: {expiry_date}, OTM Level: {otm_level}, Quantity: {quantity}")
    print("-" * 70)
    
    # Place initial strangle
    place_strangle()
    
    try:
        while True:
            time.sleep(60)  # Check every minute
            # Add exit logic here
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Strategy stopped by user")
        if positions['is_open']:
            close_strangle()

if __name__ == "__main__":
    main()
