#!/usr/bin/env python3
"""
Enhance strategies with P&L tracking functionality
Adds function to display current price, profit/loss, and stop-loss info
"""
import sys
from pathlib import Path

# This script will be used to add P&L tracking to strategies
# We'll create a utility function that strategies can use

P&L_TRACKING_CODE = '''
def display_position_status(symbol: str, current_price: float):
    """Display current position status with P&L information"""
    current_position = positions[symbol]
    entry_price = entry_prices[symbol]
    stop_loss_price = stop_loss_prices[symbol]
    
    if current_position == 0:
        logger.info(f"{symbol}: No open position")
        return
    
    # Calculate P&L
    if current_position > 0:  # LONG position
        pnl = current_price - entry_price
        pnl_pct = (pnl / entry_price) * 100
        position_type = "LONG"
    else:  # SHORT position
        pnl = entry_price - current_price
        pnl_pct = (pnl / entry_price) * 100
        position_type = "SHORT"
    
    # Determine profit/loss status
    if pnl > 0:
        status = "PROFIT"
        status_emoji = "✅"
    elif pnl < 0:
        status = "LOSS"
        status_emoji = "❌"
    else:
        status = "BREAKEVEN"
        status_emoji = "➖"
    
    # Calculate distance to stop-loss
    if stop_loss_price:
        if current_position > 0:  # LONG
            sl_distance = current_price - stop_loss_price
            sl_distance_pct = (sl_distance / entry_price) * 100
        else:  # SHORT
            sl_distance = stop_loss_price - current_price
            sl_distance_pct = (sl_distance / entry_price) * 100
    else:
        sl_distance = None
        sl_distance_pct = None
    
    # Display formatted status
    logger.info(f"{'='*60}")
    logger.info(f"{symbol} Position Status - {status_emoji} {status}")
    logger.info(f"{'='*60}")
    logger.info(f"  Position Type: {position_type}")
    logger.info(f"  Quantity: {abs(current_position)}")
    logger.info(f"  Entry Price: Rs {entry_price:.2f}")
    logger.info(f"  Current Price: Rs {current_price:.2f}")
    logger.info(f"  P&L: Rs {pnl:.2f} ({pnl_pct:+.2f}%)")
    logger.info(f"  Stop Loss: Rs {stop_loss_price:.2f}" if stop_loss_price else "  Stop Loss: Not Set")
    if sl_distance is not None:
        logger.info(f"  Distance to SL: Rs {sl_distance:.2f} ({sl_distance_pct:+.2f}%)")
    logger.info(f"{'='*60}")
'''

print("P&L tracking code template created.")
print("This function should be added to each strategy.")

