"""
Analyze losing trade patterns to identify common issues
"""
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
from collections import defaultdict
import os

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.sandbox_db import SandboxTrades, SandboxPositions, db_session
from sqlalchemy import func

def get_losing_trades():
    """Get all losing trades from database"""
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
        
        # Get all trades
        trades = db_session.query(SandboxTrades).filter(
            SandboxTrades.trade_timestamp >= session_start
        ).order_by(SandboxTrades.trade_timestamp).all()
        
        # Get positions to calculate P&L
        positions = db_session.query(SandboxPositions).filter(
            SandboxPositions.updated_at >= session_start
        ).all()
        
        # Match trades to calculate P&L
        losing_trades = []
        
        # Group trades by symbol and strategy
        symbol_trades = defaultdict(list)
        for trade in trades:
            key = f"{trade.symbol}_{trade.exchange}_{trade.strategy or 'No Strategy'}"
            symbol_trades[key].append(trade)
        
        # Calculate P&L for each symbol group
        for key, trades_list in symbol_trades.items():
            symbol, exchange, strategy = key.rsplit('_', 2)
            
            # Separate buy and sell trades
            buy_trades = [t for t in trades_list if t.action == 'BUY']
            sell_trades = [t for t in trades_list if t.action == 'SELL']
            
            # Match trades
            buy_idx = 0
            sell_idx = 0
            
            while buy_idx < len(buy_trades) and sell_idx < len(sell_trades):
                buy = buy_trades[buy_idx]
                sell = sell_trades[sell_idx]
                
                # Calculate P&L
                if buy.trade_timestamp < sell.trade_timestamp:
                    # Normal: Buy then Sell
                    pnl = (float(sell.price) - float(buy.price)) * buy.quantity
                    entry_time = buy.trade_timestamp
                    exit_time = sell.trade_timestamp
                    entry_price = float(buy.price)
                    exit_price = float(sell.price)
                    buy_idx += 1
                    sell_idx += 1
                else:
                    # Reverse: Sell then Buy (short)
                    pnl = (float(sell.price) - float(buy.price)) * sell.quantity
                    entry_time = sell.trade_timestamp
                    exit_time = buy.trade_timestamp
                    entry_price = float(sell.price)
                    exit_price = float(buy.price)
                    buy_idx += 1
                    sell_idx += 1
                
                if pnl < 0:  # Losing trade
                    losing_trades.append({
                        'symbol': symbol,
                        'exchange': exchange,
                        'strategy': strategy,
                        'entry_time': entry_time,
                        'exit_time': exit_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'quantity': buy.quantity if buy.trade_timestamp < sell.trade_timestamp else sell.quantity,
                        'pnl': pnl,
                        'pnl_pct': (pnl / (entry_price * buy.quantity)) * 100 if buy.trade_timestamp < sell.trade_timestamp else (pnl / (entry_price * sell.quantity)) * 100,
                        'duration_minutes': (exit_time - entry_time).total_seconds() / 60
                    })
        
        return losing_trades
        
    except Exception as e:
        print(f"Error getting losing trades: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        db_session.remove()


def analyze_patterns(losing_trades):
    """Analyze patterns in losing trades"""
    
    if not losing_trades:
        return {}
    
    patterns = {
        'by_strategy': defaultdict(list),
        'by_symbol': defaultdict(list),
        'by_time_of_day': defaultdict(list),
        'by_duration': {
            'quick_losses': [],  # < 30 minutes
            'medium_losses': [],  # 30 min - 2 hours
            'long_losses': []  # > 2 hours
        },
        'by_loss_size': {
            'small_losses': [],  # < ₹ 100
            'medium_losses': [],  # ₹ 100 - ₹ 500
            'large_losses': []  # > ₹ 500
        }
    }
    
    for trade in losing_trades:
        # By strategy
        patterns['by_strategy'][trade['strategy']].append(trade)
        
        # By symbol
        patterns['by_symbol'][trade['symbol']].append(trade)
        
        # By time of day
        hour = trade['entry_time'].hour
        if 9 <= hour < 12:
            time_slot = 'Morning (9-12)'
        elif 12 <= hour < 15:
            time_slot = 'Afternoon (12-15)'
        else:
            time_slot = 'Other'
        patterns['by_time_of_day'][time_slot].append(trade)
        
        # By duration
        duration = trade['duration_minutes']
        if duration < 30:
            patterns['by_duration']['quick_losses'].append(trade)
        elif duration < 120:
            patterns['by_duration']['medium_losses'].append(trade)
        else:
            patterns['by_duration']['long_losses'].append(trade)
        
        # By loss size
        pnl = abs(trade['pnl'])
        if pnl < 100:
            patterns['by_loss_size']['small_losses'].append(trade)
        elif pnl < 500:
            patterns['by_loss_size']['medium_losses'].append(trade)
        else:
            patterns['by_loss_size']['large_losses'].append(trade)
    
    return patterns


def print_pattern_analysis(patterns, losing_trades):
    """Print pattern analysis results"""
    
    print("\n" + "="*120)
    print("🔍 LOSING TRADE PATTERN ANALYSIS")
    print("="*120)
    
    if not losing_trades:
        print("\n✅ No losing trades found - excellent performance!")
        return
    
    print(f"\nTotal Losing Trades: {len(losing_trades)}")
    total_loss = sum(t['pnl'] for t in losing_trades)
    avg_loss = total_loss / len(losing_trades)
    print(f"Total Loss: ₹ {total_loss:,.2f}")
    print(f"Average Loss: ₹ {avg_loss:,.2f}")
    
    # By strategy
    print(f"\n{'─'*120}")
    print("📊 LOSES BY STRATEGY")
    print(f"{'─'*120}")
    print(f"{'Strategy':<40} {'Losing Trades':<20} {'Total Loss':<20} {'Avg Loss':<20}")
    print("-"*120)
    
    for strategy, trades in sorted(patterns['by_strategy'].items(), key=lambda x: sum(t['pnl'] for t in x[1])):
        strategy_loss = sum(t['pnl'] for t in trades)
        strategy_avg = strategy_loss / len(trades)
        print(f"{strategy[:38]:<40} {len(trades):<20} ₹ {strategy_loss:>15,.2f} ₹ {strategy_avg:>15,.2f}")
    
    # By symbol
    print(f"\n{'─'*120}")
    print("📊 LOSES BY SYMBOL")
    print(f"{'─'*120}")
    print(f"{'Symbol':<20} {'Losing Trades':<20} {'Total Loss':<20} {'Avg Loss':<20}")
    print("-"*120)
    
    for symbol, trades in sorted(patterns['by_symbol'].items(), key=lambda x: sum(t['pnl'] for t in x[1])):
        symbol_loss = sum(t['pnl'] for t in trades)
        symbol_avg = symbol_loss / len(trades)
        print(f"{symbol:<20} {len(trades):<20} ₹ {symbol_loss:>15,.2f} ₹ {symbol_avg:>15,.2f}")
    
    # By time of day
    print(f"\n{'─'*120}")
    print("📊 LOSES BY TIME OF DAY")
    print(f"{'─'*120}")
    print(f"{'Time Slot':<30} {'Losing Trades':<20} {'Total Loss':<20} {'Avg Loss':<20}")
    print("-"*120)
    
    for time_slot, trades in patterns['by_time_of_day'].items():
        time_loss = sum(t['pnl'] for t in trades)
        time_avg = time_loss / len(trades)
        print(f"{time_slot:<30} {len(trades):<20} ₹ {time_loss:>15,.2f} ₹ {time_avg:>15,.2f}")
    
    # By duration
    print(f"\n{'─'*120}")
    print("📊 LOSES BY TRADE DURATION")
    print(f"{'─'*120}")
    
    duration_categories = [
        ('Quick Losses (< 30 min)', patterns['by_duration']['quick_losses']),
        ('Medium Losses (30 min - 2 hrs)', patterns['by_duration']['medium_losses']),
        ('Long Losses (> 2 hrs)', patterns['by_duration']['long_losses'])
    ]
    
    for category, trades in duration_categories:
        if trades:
            category_loss = sum(t['pnl'] for t in trades)
            category_avg = category_loss / len(trades)
            avg_duration = sum(t['duration_minutes'] for t in trades) / len(trades)
            print(f"{category:<40} {len(trades):<10} ₹ {category_loss:>15,.2f} (Avg: {avg_duration:.1f} min)")
    
    # By loss size
    print(f"\n{'─'*120}")
    print("📊 LOSES BY LOSS SIZE")
    print(f"{'─'*120}")
    
    loss_categories = [
        ('Small Losses (< ₹ 100)', patterns['by_loss_size']['small_losses']),
        ('Medium Losses (₹ 100 - ₹ 500)', patterns['by_loss_size']['medium_losses']),
        ('Large Losses (> ₹ 500)', patterns['by_loss_size']['large_losses'])
    ]
    
    for category, trades in loss_categories:
        if trades:
            category_loss = sum(t['pnl'] for t in trades)
            category_avg = category_loss / len(trades)
            print(f"{category:<40} {len(trades):<10} ₹ {category_loss:>15,.2f} (Avg: ₹ {category_avg:,.2f})")
    
    # Recommendations
    print(f"\n{'─'*120}")
    print("💡 RECOMMENDATIONS BASED ON PATTERNS")
    print(f"{'─'*120}")
    
    # Strategy with most losses
    worst_strategy = max(patterns['by_strategy'].items(), key=lambda x: len(x[1]))
    if worst_strategy[1]:
        print(f"\n⚠️  {worst_strategy[0]} has {len(worst_strategy[1])} losing trades")
        print(f"   - Review entry/exit criteria")
        print(f"   - Ensure stop loss is properly implemented")
        print(f"   - Consider pausing until optimized")
    
    # Time slot with most losses
    worst_time = max(patterns['by_time_of_day'].items(), key=lambda x: len(x[1]))
    if worst_time[1]:
        print(f"\n⚠️  Most losses occur during {worst_time[0]}")
        print(f"   - Consider avoiding trading during this time")
        print(f"   - Or adjust strategy parameters for this time slot")
    
    # Quick losses
    if patterns['by_duration']['quick_losses']:
        print(f"\n⚠️  {len(patterns['by_duration']['quick_losses'])} quick losses (< 30 min)")
        print(f"   - May indicate whipsaw/choppy market conditions")
        print(f"   - Consider adding trend filter")
        print(f"   - Increase signal confirmation requirements")
    
    # Large losses
    if patterns['by_loss_size']['large_losses']:
        print(f"\n⚠️  {len(patterns['by_loss_size']['large_losses'])} large losses (> ₹ 500)")
        print(f"   - CRITICAL: Stop loss may not be working properly")
        print(f"   - Verify stop loss implementation")
        print(f"   - Consider reducing position size")
    
    print(f"\n{'='*120}\n")


def main():
    """Main function"""
    print("\n" + "="*120)
    print("🔍 ANALYZING LOSING TRADE PATTERNS")
    print("="*120)
    
    losing_trades = get_losing_trades()
    patterns = analyze_patterns(losing_trades)
    print_pattern_analysis(patterns, losing_trades)
    
    return patterns, losing_trades


if __name__ == "__main__":
    main()






