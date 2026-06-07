"""
Check for Scalping Activity
Analyzes trades to detect rapid trading patterns
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.sandbox_db import SandboxTrades, db_session
from datetime import datetime, timedelta
import pytz

def check_scalping_activity():
    """Check for scalping patterns in trades"""
    print("\n" + "="*80)
    print("SCALPING ACTIVITY ANALYSIS")
    print("="*80)
    
    # Get today's trades
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).date()
    start_of_day = datetime.combine(today, datetime.min.time()).replace(tzinfo=ist)
    
    trades = SandboxTrades.query.filter(
        SandboxTrades.trade_timestamp >= start_of_day
    ).order_by(SandboxTrades.trade_timestamp).all()
    
    print(f"\nTotal trades today: {len(trades)}")
    
    if len(trades) < 2:
        print("\n[INFO] Not enough trades to analyze scalping patterns")
        return
    
    # Group trades by symbol
    trades_by_symbol = {}
    for trade in trades:
        key = f"{trade.symbol}_{trade.exchange}"
        if key not in trades_by_symbol:
            trades_by_symbol[key] = []
        trades_by_symbol[key].append(trade)
    
    print(f"\nSymbols traded today: {len(trades_by_symbol)}")
    
    # Check for scalping patterns
    scalping_detected = False
    scalping_threshold_seconds = 300  # 5 minutes between buy and sell
    
    print("\n" + "-"*80)
    print("SCALPING PATTERN ANALYSIS")
    print("-"*80)
    
    for symbol_key, symbol_trades in trades_by_symbol.items():
        if len(symbol_trades) < 2:
            continue
        
        # Sort by timestamp
        symbol_trades.sort(key=lambda x: x.trade_timestamp)
        
        # Check for rapid buy-sell cycles
        for i in range(len(symbol_trades) - 1):
            trade1 = symbol_trades[i]
            trade2 = symbol_trades[i + 1]
            
            time_diff = (trade2.trade_timestamp - trade1.trade_timestamp).total_seconds()
            
            # Check if it's a buy-sell or sell-buy cycle within threshold
            if time_diff <= scalping_threshold_seconds:
                if (trade1.action == 'BUY' and trade2.action == 'SELL') or \
                   (trade1.action == 'SELL' and trade2.action == 'BUY'):
                    
                    scalping_detected = True
                    pnl = 0
                    if trade1.action == 'BUY' and trade2.action == 'SELL':
                        pnl = (trade2.price - trade1.price) * trade1.quantity
                    else:
                        pnl = (trade1.price - trade2.price) * trade2.quantity
                    
                    print(f"\n[SCALPING DETECTED] {symbol_key}")
                    print(f"  Trade 1: {trade1.action} {trade1.quantity} @ {trade1.price} at {trade1.trade_timestamp.strftime('%H:%M:%S')}")
                    print(f"  Trade 2: {trade2.action} {trade2.quantity} @ {trade2.price} at {trade2.trade_timestamp.strftime('%H:%M:%S')}")
                    print(f"  Time difference: {int(time_diff)} seconds ({int(time_diff/60)} minutes)")
                    print(f"  Estimated P&L: Rs {pnl:.2f}")
    
    if not scalping_detected:
        print("\n[INFO] No scalping patterns detected (no rapid buy-sell cycles within 5 minutes)")
    
    # Check trade frequency
    print("\n" + "-"*80)
    print("TRADE FREQUENCY ANALYSIS")
    print("-"*80)
    
    if len(trades) > 1:
        total_time = (trades[-1].trade_timestamp - trades[0].trade_timestamp).total_seconds()
        if total_time > 0:
            trades_per_hour = (len(trades) / total_time) * 3600
            print(f"\nTrade frequency: {trades_per_hour:.2f} trades per hour")
            print(f"Average time between trades: {total_time / len(trades):.1f} seconds")
            
            if trades_per_hour > 20:  # More than 20 trades per hour
                print(f"[WARNING] High trade frequency detected! This may indicate scalping.")
            else:
                print(f"[INFO] Trade frequency is normal")
    
    # Show recent trades timeline
    print("\n" + "-"*80)
    print("RECENT TRADES TIMELINE (Last 10)")
    print("-"*80)
    
    recent_trades = trades[-10:] if len(trades) >= 10 else trades
    for i, trade in enumerate(recent_trades):
        if i > 0:
            prev_trade = recent_trades[i-1]
            time_diff = (trade.trade_timestamp - prev_trade.trade_timestamp).total_seconds()
            print(f"  {time_diff:6.1f}s -> {trade.symbol} {trade.action} {trade.quantity} @ {trade.price} ({trade.trade_timestamp.strftime('%H:%M:%S')})")
        else:
            print(f"  START -> {trade.symbol} {trade.action} {trade.quantity} @ {trade.price} ({trade.trade_timestamp.strftime('%H:%M:%S')})")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80 + "\n")
    
    return scalping_detected

if __name__ == '__main__':
    try:
        scalping = check_scalping_activity()
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


