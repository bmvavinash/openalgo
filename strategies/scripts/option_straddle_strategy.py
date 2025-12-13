#!/usr/bin/env python
"""
Option Straddle Strategy
Buy ATM Call + Put simultaneously
Profits from large price movements in either direction
"""
from openalgo import api
import os
import time
from datetime import datetime
import threading

# Get API key from environment
api_key = os.getenv('OPENALGO_API_KEY', os.getenv('OPENALGO_APIKEY'))
if not api_key:
    print("Error: OPENALGO_API_KEY environment variable not set")
    exit(1)

# Strategy configuration
strategy_name = "Option Straddle"
underlying = os.getenv('UNDERLYING', 'NIFTY')
exchange = os.getenv('EXCHANGE', 'NSE_INDEX')
expiry_date = os.getenv('EXPIRY_DATE', '')  # Format: DDMMMYY (e.g., 28NOV24)
strike_int = int(os.getenv('STRIKE_INT', '50'))  # 50 for NIFTY, 100 for BANKNIFTY
quantity = int(os.getenv('QUANTITY', '75'))  # Lot size * number of lots
product = os.getenv('PRODUCT', 'MIS')  # MIS or NRML
pricetype = os.getenv('PRICETYPE', 'MARKET')  # MARKET, LIMIT, SL, SL-M

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

def place_straddle():
    """Place a straddle: Buy ATM Call + Put"""
    try:
        print(f"[{datetime.now()}] Placing {strategy_name} for {underlying}")
        
        # Place Call order
        call_response = client.optionsorder(
            strategy=strategy_name,
            underlying=underlying,
            exchange=exchange,
            expiry_date=expiry_date,
            offset="ATM",
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
            offset="ATM",
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
        print(f"[{datetime.now()}] Error placing straddle: {str(e)}")
        return False

def close_straddle():
    """Close the straddle: Sell both positions"""
    if not positions['is_open']:
        print(f"[{datetime.now()}] No open straddle position to close")
        return False
    
    try:
        print(f"[{datetime.now()}] Closing {strategy_name}")
        
        # Close Call
        if positions['call_symbol']:
            call_close = client.placeorder(
                strategy=strategy_name,
                symbol=positions['call_symbol'],
                exchange=exchange.replace('_INDEX', '') if '_INDEX' in exchange else 'NFO',
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
                exchange=exchange.replace('_INDEX', '') if '_INDEX' in exchange else 'NFO',
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
        print(f"[{datetime.now()}] Error closing straddle: {str(e)}")
        return False

def main():
    """Main strategy loop"""
    print(f"Starting {strategy_name} Strategy")
    print(f"Underlying: {underlying}, Exchange: {exchange}")
    print(f"Expiry: {expiry_date}, Quantity: {quantity}, Product: {product}")
    print("-" * 70)
    
    # Place initial straddle
    place_straddle()
    
    # Strategy monitoring loop
    # In a real implementation, you would add exit logic based on:
    # - Profit target
    # - Stop loss
    # - Time decay
    # - Volatility changes
    # - Market conditions
    
    try:
        while True:
            time.sleep(60)  # Check every minute
            # Add your exit logic here
            # Example: if profit_target_reached() or stop_loss_hit():
            #     close_straddle()
            #     break
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Strategy stopped by user")
        if positions['is_open']:
            close_straddle()

if __name__ == "__main__":
    main()
