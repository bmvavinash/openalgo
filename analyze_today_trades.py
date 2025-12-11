"""
Analyze today's market trades by strategy and provide P&L comparison
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

def get_today_strategy_analysis():
    """Get today's P&L analysis grouped by strategy"""
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
        
        # Get all trades for today grouped by strategy
        trades = db_session.query(SandboxTrades).filter(
            SandboxTrades.trade_timestamp >= session_start
        ).order_by(SandboxTrades.trade_timestamp).all()
        
        # Get all positions for today
        positions = db_session.query(SandboxPositions).filter(
            SandboxPositions.updated_at >= session_start
        ).all()
        
        # Group trades by strategy
        strategy_trades = defaultdict(list)
        for trade in trades:
            strategy_name = trade.strategy or "No Strategy"
            strategy_trades[strategy_name].append(trade)
        
        # Group positions by strategy (from trades)
        strategy_positions = defaultdict(list)
        for position in positions:
            # Find strategy from trades for this symbol
            symbol_trades = [t for t in trades if t.symbol == position.symbol and t.exchange == position.exchange]
            if symbol_trades:
                strategy_name = symbol_trades[0].strategy or "No Strategy"
            else:
                strategy_name = "No Strategy"
            strategy_positions[strategy_name].append(position)
        
        # Calculate metrics for each strategy
        strategy_stats = {}
        
        for strategy_name in set(list(strategy_trades.keys()) + list(strategy_positions.keys())):
            strategy_trades_list = strategy_trades.get(strategy_name, [])
            strategy_positions_list = strategy_positions.get(strategy_name, [])
            
            # Calculate realized P&L from closed positions
            realized_pnl = sum(
                float(pos.accumulated_realized_pnl) if pos.accumulated_realized_pnl else 0.0 
                for pos in strategy_positions_list
            )
            
            # Calculate unrealized P&L from open positions
            unrealized_pnl = 0.0
            open_positions_count = 0
            for pos in strategy_positions_list:
                if pos.quantity != 0:
                    pnl = float(pos.pnl) if pos.pnl else 0.0
                    unrealized_pnl += pnl
                    open_positions_count += 1
            
            # Calculate total P&L
            total_pnl = realized_pnl + unrealized_pnl
            
            # Count trades
            total_trades = len(strategy_trades_list)
            
            # Count winning and losing trades
            winning_trades = 0
            losing_trades = 0
            
            # Group trades by symbol to calculate win/loss
            symbol_trade_groups = defaultdict(list)
            for trade in strategy_trades_list:
                key = f"{trade.symbol}_{trade.exchange}"
                symbol_trade_groups[key].append(trade)
            
            for symbol_key, symbol_trades_list in symbol_trade_groups.items():
                # Calculate net P&L for this symbol
                buy_trades = [t for t in symbol_trades_list if t.action == 'BUY']
                sell_trades = [t for t in symbol_trades_list if t.action == 'SELL']
                
                # Simple calculation: if we have both buy and sell, calculate P&L
                if buy_trades and sell_trades:
                    avg_buy_price = sum(float(t.price) * t.quantity for t in buy_trades) / sum(t.quantity for t in buy_trades)
                    avg_sell_price = sum(float(t.price) * t.quantity for t in sell_trades) / sum(t.quantity for t in sell_trades)
                    qty_traded = min(sum(t.quantity for t in buy_trades), sum(t.quantity for t in sell_trades))
                    
                    if avg_sell_price > avg_buy_price:
                        winning_trades += 1
                    elif avg_sell_price < avg_buy_price:
                        losing_trades += 1
            
            # Count unique symbols
            unique_symbols = len(set(f"{t.symbol}_{t.exchange}" for t in strategy_trades_list))
            
            # Calculate win rate
            closed_trades = winning_trades + losing_trades
            win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0.0
            
            strategy_stats[strategy_name] = {
                'total_pnl': total_pnl,
                'realized_pnl': realized_pnl,
                'unrealized_pnl': unrealized_pnl,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'unique_symbols': unique_symbols,
                'open_positions': open_positions_count,
                'trades': strategy_trades_list,
                'positions': strategy_positions_list
            }
        
        return strategy_stats, session_start, now
        
    except Exception as e:
        print(f"Error analyzing trades: {e}")
        import traceback
        traceback.print_exc()
        return {}, None, None
    finally:
        db_session.remove()


def print_strategy_comparison_table(strategy_stats):
    """Print a formatted comparison table of strategies"""
    
    if not strategy_stats:
        print("\n❌ No trading activity found today.")
        return
    
    # Sort strategies by total P&L (descending)
    sorted_strategies = sorted(
        strategy_stats.items(), 
        key=lambda x: x[1]['total_pnl'], 
        reverse=True
    )
    
    print("\n" + "="*120)
    print("📊 TODAY'S MARKET TRADES ANALYSIS - STRATEGY COMPARISON")
    print("="*120)
    
    # Table header
    print(f"\n{'Strategy Name':<30} {'Total P&L':<15} {'Realized':<15} {'Unrealized':<15} {'Trades':<10} {'Win Rate':<12} {'Symbols':<10} {'Status':<15}")
    print("-" * 120)
    
    # Table rows
    for strategy_name, stats in sorted_strategies:
        total_pnl = stats['total_pnl']
        realized = stats['realized_pnl']
        unrealized = stats['unrealized_pnl']
        trades = stats['total_trades']
        win_rate = stats['win_rate']
        symbols = stats['unique_symbols']
        
        # Format P&L with color indicators
        if total_pnl > 0:
            status = "✅ PROFIT"
            pnl_str = f"₹ +{total_pnl:,.2f}"
        elif total_pnl < 0:
            status = "❌ LOSS"
            pnl_str = f"₹ {total_pnl:,.2f}"
        else:
            status = "➖ BREAK EVEN"
            pnl_str = f"₹ {total_pnl:,.2f}"
        
        realized_str = f"₹ {realized:,.2f}"
        unrealized_str = f"₹ {unrealized:,.2f}"
        win_rate_str = f"{win_rate:.1f}%" if win_rate > 0 else "N/A"
        
        print(f"{strategy_name[:28]:<30} {pnl_str:<15} {realized_str:<15} {unrealized_str:<15} "
              f"{trades:<10} {win_rate_str:<12} {symbols:<10} {status:<15}")
    
    print("-" * 120)
    
    # Summary statistics
    total_pnl_all = sum(s['total_pnl'] for s in strategy_stats.values())
    total_trades_all = sum(s['total_trades'] for s in strategy_stats.values())
    total_realized = sum(s['realized_pnl'] for s in strategy_stats.values())
    total_unrealized = sum(s['unrealized_pnl'] for s in strategy_stats.values())
    
    print(f"\n{'SUMMARY':<30} {'Total P&L':<15} {'Realized':<15} {'Unrealized':<15} {'Trades':<10} {'Win Rate':<12} {'Symbols':<10}")
    print("-" * 120)
    
    overall_win_rate = 0.0
    total_wins = sum(s['winning_trades'] for s in strategy_stats.values())
    total_losses = sum(s['losing_trades'] for s in strategy_stats.values())
    if (total_wins + total_losses) > 0:
        overall_win_rate = (total_wins / (total_wins + total_losses)) * 100
    
    total_symbols = len(set(
        f"{t.symbol}_{t.exchange}" 
        for stats in strategy_stats.values() 
        for t in stats['trades']
    ))
    
    if total_pnl_all > 0:
        pnl_str = f"₹ +{total_pnl_all:,.2f}"
    else:
        pnl_str = f"₹ {total_pnl_all:,.2f}"
    
    print(f"{'ALL STRATEGIES':<30} {pnl_str:<15} ₹ {total_realized:,.2f} {'':<13} ₹ {total_unrealized:,.2f} {'':<13} "
          f"{total_trades_all:<10} {overall_win_rate:.1f}%{'':<9} {total_symbols:<10}")
    
    print("="*120)


def print_best_strategy(strategy_stats):
    """Identify and print the best performing strategy"""
    
    if not strategy_stats:
        return
    
    # Find best strategy by total P&L
    best_strategy = max(
        strategy_stats.items(), 
        key=lambda x: x[1]['total_pnl']
    )
    
    strategy_name, stats = best_strategy
    
    print("\n" + "="*120)
    print("🏆 BEST PERFORMING STRATEGY TODAY")
    print("="*120)
    print(f"\nStrategy: {strategy_name}")
    print(f"Total P&L: ₹ {stats['total_pnl']:,.2f}")
    print(f"  - Realized P&L: ₹ {stats['realized_pnl']:,.2f}")
    print(f"  - Unrealized P&L: ₹ {stats['unrealized_pnl']:,.2f}")
    print(f"\nTrading Statistics:")
    print(f"  - Total Trades: {stats['total_trades']}")
    print(f"  - Winning Trades: {stats['winning_trades']}")
    print(f"  - Losing Trades: {stats['losing_trades']}")
    print(f"  - Win Rate: {stats['win_rate']:.1f}%")
    print(f"  - Unique Symbols: {stats['unique_symbols']}")
    print(f"  - Open Positions: {stats['open_positions']}")
    
    # Show top trades
    if stats['trades']:
        print(f"\nRecent Trades:")
        for trade in stats['trades'][-5:]:  # Show last 5 trades
            print(f"  - {trade.action} {trade.quantity} {trade.symbol} @ ₹ {float(trade.price):,.2f} "
                  f"({trade.trade_timestamp.strftime('%H:%M:%S')})")
    
    print("="*120)


def print_detailed_strategy_breakdown(strategy_stats):
    """Print detailed breakdown for each strategy"""
    
    if not strategy_stats:
        return
    
    print("\n" + "="*120)
    print("📋 DETAILED STRATEGY BREAKDOWN")
    print("="*120)
    
    for strategy_name, stats in sorted(strategy_stats.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
        print(f"\n{'─'*120}")
        print(f"Strategy: {strategy_name}")
        print(f"{'─'*120}")
        
        print(f"\nP&L Summary:")
        print(f"  Total P&L:        ₹ {stats['total_pnl']:>12,.2f}")
        print(f"  Realized P&L:     ₹ {stats['realized_pnl']:>12,.2f}")
        print(f"  Unrealized P&L:   ₹ {stats['unrealized_pnl']:>12,.2f}")
        
        print(f"\nTrading Activity:")
        print(f"  Total Trades:     {stats['total_trades']:>12}")
        print(f"  Winning Trades:   {stats['winning_trades']:>12}")
        print(f"  Losing Trades:    {stats['losing_trades']:>12}")
        print(f"  Win Rate:         {stats['win_rate']:>11.1f}%")
        print(f"  Unique Symbols:  {stats['unique_symbols']:>12}")
        print(f"  Open Positions:   {stats['open_positions']:>12}")
        
        # Show positions
        if stats['positions']:
            print(f"\nPositions:")
            for pos in stats['positions']:
                if pos.quantity != 0:
                    print(f"  - {pos.symbol} ({pos.exchange}): Qty={pos.quantity}, "
                          f"Avg=₹ {float(pos.average_price):,.2f}, "
                          f"LTP=₹ {float(pos.ltp):,.2f if pos.ltp else 0:.2f}, "
                          f"P&L=₹ {float(pos.pnl):,.2f if pos.pnl else 0:.2f}")


def main():
    """Main function to run the analysis"""
    print("\n" + "="*120)
    print("🔍 ANALYZING TODAY'S MARKET TRADES")
    print("="*120)
    
    strategy_stats, session_start, current_time = get_today_strategy_analysis()
    
    if session_start and current_time:
        print(f"\nSession Start: {session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Current Time:  {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not strategy_stats:
        print("\n❌ No trading activity found today.")
        print("   Make sure you have executed trades in sandbox/paper trading mode.")
        return
    
    # Print comparison table
    print_strategy_comparison_table(strategy_stats)
    
    # Print best strategy
    print_best_strategy(strategy_stats)
    
    # Print detailed breakdown
    print_detailed_strategy_breakdown(strategy_stats)
    
    print("\n" + "="*120)
    print("✅ Analysis Complete")
    print("="*120 + "\n")


if __name__ == "__main__":
    main()






