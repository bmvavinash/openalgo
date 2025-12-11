"""
Detailed trade-by-trade analysis for today's market trades
"""
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
import os
from collections import defaultdict
from decimal import Decimal

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.sandbox_db import SandboxPositions, SandboxTrades, db_session
from sqlalchemy import func

def get_trade_details():
    """Get detailed trade-by-trade analysis"""
    try:
        # Get session expiry time
        session_expiry_str = os.getenv('SESSION_EXPIRY_TIME', '03:00')
        expiry_hour, expiry_minute = map(int, session_expiry_str.split(':'))
        
        now = datetime.now()
        today = now.date()
        session_expiry_time = time(expiry_hour, expiry_minute)
        
        if now.time() < session_expiry_time:
            session_start = datetime.combine(today - timedelta(days=1), session_expiry_time)
        else:
            session_start = datetime.combine(today, session_expiry_time)
        
        # Get all trades for today
        trades = db_session.query(SandboxTrades).filter(
            SandboxTrades.trade_timestamp >= session_start
        ).order_by(SandboxTrades.trade_timestamp).all()
        
        # Get all positions for today
        positions = db_session.query(SandboxPositions).filter(
            SandboxPositions.updated_at >= session_start
        ).all()
        
        return trades, positions, session_start, now
        
    except Exception as e:
        print(f"Error getting trade details: {e}")
        import traceback
        traceback.print_exc()
        return [], [], None, None
    finally:
        db_session.remove()


def analyze_trades_by_symbol(trades):
    """Analyze trades grouped by symbol"""
    symbol_trades = defaultdict(list)
    
    for trade in trades:
        key = f"{trade.symbol}_{trade.exchange}"
        symbol_trades[key].append(trade)
    
    return symbol_trades


def calculate_symbol_pnl(trades_list):
    """Calculate P&L for a symbol's trades"""
    buy_trades = []
    sell_trades = []
    
    for trade in trades_list:
        if trade.action == 'BUY':
            buy_trades.append({
                'time': trade.trade_timestamp,
                'price': float(trade.price),
                'quantity': trade.quantity,
                'trade_id': trade.tradeid
            })
        else:  # SELL
            sell_trades.append({
                'time': trade.trade_timestamp,
                'price': float(trade.price),
                'quantity': trade.quantity,
                'trade_id': trade.tradeid
            })
    
    # Match buy and sell trades to calculate P&L
    matched_trades = []
    total_pnl = 0.0
    
    # Process buy trades
    buy_idx = 0
    sell_idx = 0
    
    while buy_idx < len(buy_trades) and sell_idx < len(sell_trades):
        buy = buy_trades[buy_idx]
        sell = sell_trades[sell_idx]
        
        # Match quantities
        matched_qty = min(buy['quantity'], sell['quantity'])
        
        if matched_qty > 0:
            pnl = (sell['price'] - buy['price']) * matched_qty
            total_pnl += pnl
            
            matched_trades.append({
                'entry_time': buy['time'],
                'exit_time': sell['time'],
                'entry_price': buy['price'],
                'exit_price': sell['price'],
                'quantity': matched_qty,
                'pnl': pnl,
                'pnl_percent': ((sell['price'] - buy['price']) / buy['price']) * 100,
                'entry_trade_id': buy['trade_id'],
                'exit_trade_id': sell['trade_id'],
                'status': 'PROFIT' if pnl > 0 else 'LOSS' if pnl < 0 else 'BREAK EVEN'
            })
            
            # Update quantities
            buy['quantity'] -= matched_qty
            sell['quantity'] -= matched_qty
            
            if buy['quantity'] == 0:
                buy_idx += 1
            if sell['quantity'] == 0:
                sell_idx += 1
        else:
            # No match possible, move to next
            if buy['time'] < sell['time']:
                buy_idx += 1
            else:
                sell_idx += 1
    
    return matched_trades, total_pnl


def print_detailed_trade_analysis(trades, positions):
    """Print detailed trade-by-trade analysis"""
    
    print("\n" + "="*120)
    print("📊 DETAILED TRADE-BY-TRADE ANALYSIS")
    print("="*120)
    
    if not trades:
        print("\n❌ No trades found today.")
        return
    
    # Group trades by strategy
    strategy_trades = defaultdict(list)
    for trade in trades:
        strategy_name = trade.strategy or "No Strategy"
        strategy_trades[strategy_name].append(trade)
    
    # Analyze each strategy
    for strategy_name, strategy_trades_list in sorted(strategy_trades.items()):
        print(f"\n{'─'*120}")
        print(f"Strategy: {strategy_name}")
        print(f"{'─'*120}")
        
        # Group by symbol
        symbol_trades = analyze_trades_by_symbol(strategy_trades_list)
        
        for symbol_key, symbol_trades_list in symbol_trades.items():
            symbol, exchange = symbol_key.rsplit('_', 1)
            print(f"\n📈 Symbol: {symbol} ({exchange})")
            print(f"{'─'*80}")
            
            # Calculate P&L for this symbol
            matched_trades, total_pnl = calculate_symbol_pnl(symbol_trades_list)
            
            # Print individual trades
            print(f"\n{'Time':<12} {'Action':<8} {'Qty':<8} {'Price':<15} {'Trade ID':<20}")
            print("-"*80)
            
            for trade in symbol_trades_list:
                print(f"{trade.trade_timestamp.strftime('%H:%M:%S'):<12} "
                      f"{trade.action:<8} "
                      f"{trade.quantity:<8} "
                      f"₹ {float(trade.price):>12,.2f} "
                      f"{trade.tradeid:<20}")
            
            # Print matched trades (P&L pairs)
            if matched_trades:
                print(f"\n{'─'*80}")
                print("💰 TRADE PAIRS & P&L ANALYSIS")
                print(f"{'─'*80}")
                print(f"\n{'Entry Time':<12} {'Exit Time':<12} {'Entry Price':<15} {'Exit Price':<15} "
                      f"{'Qty':<8} {'P&L':<15} {'P&L %':<12} {'Status':<15}")
                print("-"*120)
                
                for mt in matched_trades:
                    status_icon = "✅" if mt['status'] == 'PROFIT' else "❌" if mt['status'] == 'LOSS' else "➖"
                    print(f"{mt['entry_time'].strftime('%H:%M:%S'):<12} "
                          f"{mt['exit_time'].strftime('%H:%M:%S'):<12} "
                          f"₹ {mt['entry_price']:>12,.2f} "
                          f"₹ {mt['exit_price']:>12,.2f} "
                          f"{mt['quantity']:<8} "
                          f"₹ {mt['pnl']:>12,.2f} "
                          f"{mt['pnl_percent']:>10.2f}% "
                          f"{status_icon} {mt['status']:<12}")
                
                print(f"\n{'─'*80}")
                print(f"Total P&L for {symbol}: ₹ {total_pnl:,.2f}")
                
                # Statistics
                winning_trades = [t for t in matched_trades if t['pnl'] > 0]
                losing_trades = [t for t in matched_trades if t['pnl'] < 0]
                
                if winning_trades:
                    avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades)
                    max_win = max(t['pnl'] for t in winning_trades)
                    print(f"Winning Trades: {len(winning_trades)}, Avg Win: ₹ {avg_win:,.2f}, Max Win: ₹ {max_win:,.2f}")
                
                if losing_trades:
                    avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades)
                    max_loss = min(t['pnl'] for t in losing_trades)
                    print(f"Losing Trades: {len(losing_trades)}, Avg Loss: ₹ {avg_loss:,.2f}, Max Loss: ₹ {max_loss:,.2f}")
            else:
                print(f"\n⚠️  No matched trade pairs found (all positions may still be open)")
    
    # Print all trades summary
    print(f"\n{'='*120}")
    print("📋 ALL TRADES SUMMARY")
    print(f"{'='*120}")
    print(f"\n{'Time':<12} {'Strategy':<35} {'Symbol':<15} {'Action':<8} {'Qty':<8} {'Price':<15} {'Trade ID':<20}")
    print("-"*120)
    
    for trade in sorted(trades, key=lambda x: x.trade_timestamp):
        strategy_display = (trade.strategy or "No Strategy")[:33]
        print(f"{trade.trade_timestamp.strftime('%H:%M:%S'):<12} "
              f"{strategy_display:<35} "
              f"{trade.symbol:<15} "
              f"{trade.action:<8} "
              f"{trade.quantity:<8} "
              f"₹ {float(trade.price):>12,.2f} "
              f"{trade.tradeid:<20}")


def main():
    """Main function"""
    print("\n" + "="*120)
    print("🔍 DETAILED TRADE ANALYSIS")
    print("="*120)
    
    trades, positions, session_start, current_time = get_trade_details()
    
    if session_start and current_time:
        print(f"\nSession Start: {session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Current Time:  {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not trades:
        print("\n❌ No trades found today.")
        return
    
    print_detailed_trade_analysis(trades, positions)
    
    print("\n" + "="*120)
    print("✅ Detailed Analysis Complete")
    print("="*120 + "\n")


if __name__ == "__main__":
    main()






