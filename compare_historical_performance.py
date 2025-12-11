"""
Compare today's performance with historical data
"""
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
import os
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.sandbox_db import SandboxPositions, SandboxTrades, db_session
from sqlalchemy import func, extract

def get_daily_performance(days_back=7):
    """Get daily performance for the last N days"""
    try:
        session_expiry_str = os.getenv('SESSION_EXPIRY_TIME', '03:00')
        expiry_hour, expiry_minute = map(int, session_expiry_str.split(':'))
        
        now = datetime.now()
        daily_stats = []
        
        # Get data for each day
        for days_ago in range(days_back + 1):
            target_date = now.date() - timedelta(days=days_ago)
            
            # Calculate session start for this day
            if days_ago == 0:
                # Today
                if now.time() < time(expiry_hour, expiry_minute):
                    session_start = datetime.combine(target_date - timedelta(days=1), time(expiry_hour, expiry_minute))
                else:
                    session_start = datetime.combine(target_date, time(expiry_hour, expiry_minute))
                session_end = now
            else:
                # Past days
                session_start = datetime.combine(target_date, time(expiry_hour, expiry_minute))
                session_end = datetime.combine(target_date, time(23, 59, 59))
            
            # Get trades for this day
            trades = db_session.query(SandboxTrades).filter(
                SandboxTrades.trade_timestamp >= session_start,
                SandboxTrades.trade_timestamp <= session_end
            ).all()
            
            # Get positions for this day
            positions = db_session.query(SandboxPositions).filter(
                SandboxPositions.updated_at >= session_start,
                SandboxPositions.updated_at <= session_end
            ).all()
            
            # Calculate P&L
            realized_pnl = sum(
                float(pos.accumulated_realized_pnl) if pos.accumulated_realized_pnl else 0.0 
                for pos in positions
            )
            
            unrealized_pnl = sum(
                float(pos.pnl) if pos.pnl and pos.quantity != 0 else 0.0
                for pos in positions
            )
            
            total_pnl = realized_pnl + unrealized_pnl
            
            # Group by strategy
            strategy_pnl = defaultdict(float)
            for trade in trades:
                strategy_name = trade.strategy or "No Strategy"
                # Simple P&L calculation - would need more complex logic for accurate P&L
                # For now, just count trades per strategy
                strategy_pnl[strategy_name] += 0  # Placeholder
            
            daily_stats.append({
                'date': target_date,
                'total_pnl': total_pnl,
                'realized_pnl': realized_pnl,
                'unrealized_pnl': unrealized_pnl,
                'total_trades': len(trades),
                'strategies': dict(strategy_pnl),
                'is_today': days_ago == 0
            })
        
        return daily_stats
        
    except Exception as e:
        print(f"Error getting historical performance: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        db_session.remove()


def get_strategy_daily_performance():
    """Get daily performance grouped by strategy"""
    try:
        session_expiry_str = os.getenv('SESSION_EXPIRY_TIME', '03:00')
        expiry_hour, expiry_minute = map(int, session_expiry_str.split(':'))
        
        now = datetime.now()
        
        # Get all trades from last 7 days
        days_back = 7
        start_date = datetime.combine((now.date() - timedelta(days=days_back)), time(expiry_hour, expiry_minute))
        
        trades = db_session.query(SandboxTrades).filter(
            SandboxTrades.trade_timestamp >= start_date
        ).all()
        
        positions = db_session.query(SandboxPositions).filter(
            SandboxPositions.updated_at >= start_date
        ).all()
        
        # Group by date and strategy
        daily_strategy_stats = defaultdict(lambda: defaultdict(lambda: {
            'trades': 0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0
        }))
        
        # Process trades
        for trade in trades:
            trade_date = trade.trade_timestamp.date()
            strategy_name = trade.strategy or "No Strategy"
            daily_strategy_stats[trade_date][strategy_name]['trades'] += 1
        
        # Process positions
        for position in positions:
            pos_date = position.updated_at.date()
            # Find strategy from trades
            symbol_trades = [t for t in trades if t.symbol == position.symbol and t.exchange == position.exchange]
            if symbol_trades:
                strategy_name = symbol_trades[0].strategy or "No Strategy"
            else:
                strategy_name = "No Strategy"
            
            if position.accumulated_realized_pnl:
                daily_strategy_stats[pos_date][strategy_name]['realized_pnl'] += float(position.accumulated_realized_pnl)
            if position.pnl and position.quantity != 0:
                daily_strategy_stats[pos_date][strategy_name]['unrealized_pnl'] += float(position.pnl)
        
        return dict(daily_strategy_stats)
        
    except Exception as e:
        print(f"Error getting strategy daily performance: {e}")
        import traceback
        traceback.print_exc()
        return {}
    finally:
        db_session.remove()


def print_historical_comparison():
    """Print historical performance comparison"""
    
    print("\n" + "="*120)
    print("📊 HISTORICAL PERFORMANCE COMPARISON")
    print("="*120)
    
    # Get today's performance
    from analyze_today_trades import get_today_strategy_analysis
    today_stats, session_start, current_time = get_today_strategy_analysis()
    
    if not today_stats:
        print("\n❌ No trading data available for comparison.")
        return
    
    # Get historical data
    daily_strategy_stats = get_strategy_daily_performance()
    
    # Calculate today's total
    today_total_pnl = sum(s['total_pnl'] for s in today_stats.values())
    today_date = datetime.now().date()
    
    print(f"\n📅 Today's Date: {today_date.strftime('%Y-%m-%d')}")
    print(f"Today's Total P&L: ₹ {today_total_pnl:,.2f}")
    
    # Get last 7 days performance
    print(f"\n{'='*120}")
    print("📈 LAST 7 DAYS PERFORMANCE SUMMARY")
    print(f"{'='*120}")
    
    print(f"\n{'Date':<12} {'Total P&L':<15} {'Trades':<10} {'Strategies':<15} {'Status':<15}")
    print("-"*120)
    
    # Sort dates
    sorted_dates = sorted(daily_strategy_stats.keys(), reverse=True)[:7]
    
    for date in sorted_dates:
        day_stats = daily_strategy_stats[date]
        day_total_pnl = sum(s['realized_pnl'] + s['unrealized_pnl'] for s in day_stats.values())
        day_total_trades = sum(s['trades'] for s in day_stats.values())
        day_strategies = len(day_stats)
        
        if day_total_pnl > 0:
            status = "✅ PROFIT"
        elif day_total_pnl < 0:
            status = "❌ LOSS"
        else:
            status = "➖ BREAK EVEN"
        
        date_str = date.strftime('%Y-%m-%d')
        if date == today_date:
            date_str = f"{date_str} (TODAY)"
        
        print(f"{date_str:<20} ₹ {day_total_pnl:>12,.2f} {day_total_trades:>10} {day_strategies:>15} {status:<15}")
    
    # Strategy-wise comparison
    print(f"\n{'='*120}")
    print("📊 STRATEGY PERFORMANCE OVER TIME")
    print(f"{'='*120}")
    
    # Get all unique strategies
    all_strategies = set()
    for day_stats in daily_strategy_stats.values():
        all_strategies.update(day_stats.keys())
    all_strategies.update(today_stats.keys())
    
    if all_strategies:
        print(f"\n{'Strategy':<40} {'Today P&L':<15} {'7-Day Avg':<15} {'Best Day':<15} {'Worst Day':<15} {'Status':<15}")
        print("-"*120)
        
        for strategy in sorted(all_strategies):
            today_pnl = today_stats.get(strategy, {}).get('total_pnl', 0.0)
            
            # Calculate 7-day average
            strategy_daily_pnls = []
            for day_stats in daily_strategy_stats.values():
                if strategy in day_stats:
                    pnl = day_stats[strategy]['realized_pnl'] + day_stats[strategy]['unrealized_pnl']
                    strategy_daily_pnls.append(pnl)
            
            avg_7day = sum(strategy_daily_pnls) / len(strategy_daily_pnls) if strategy_daily_pnls else 0.0
            best_day = max(strategy_daily_pnls) if strategy_daily_pnls else 0.0
            worst_day = min(strategy_daily_pnls) if strategy_daily_pnls else 0.0
            
            # Status comparison
            if today_pnl > avg_7day:
                status = "📈 ABOVE AVG"
            elif today_pnl < avg_7day:
                status = "📉 BELOW AVG"
            else:
                status = "➖ AT AVG"
            
            strategy_display = strategy[:38]
            print(f"{strategy_display:<40} ₹ {today_pnl:>12,.2f} ₹ {avg_7day:>12,.2f} "
                  f"₹ {best_day:>12,.2f} ₹ {worst_day:>12,.2f} {status:<15}")
    
    # Performance trends
    print(f"\n{'='*120}")
    print("📈 PERFORMANCE TRENDS")
    print(f"{'='*120}")
    
    if len(sorted_dates) >= 3:
        recent_3_days = sorted_dates[:3]
        recent_pnls = [
            sum(s['realized_pnl'] + s['unrealized_pnl'] for s in daily_strategy_stats[date].values())
            for date in recent_3_days
        ]
        
        if len(recent_pnls) == 3:
            trend = "📈 IMPROVING" if recent_pnls[0] > recent_pnls[2] else "📉 DECLINING" if recent_pnls[0] < recent_pnls[2] else "➖ STABLE"
            print(f"\n3-Day Trend: {trend}")
            print(f"  Day 1: ₹ {recent_pnls[0]:,.2f}")
            print(f"  Day 2: ₹ {recent_pnls[1]:,.2f}")
            print(f"  Day 3: ₹ {recent_pnls[2]:,.2f}")
    
    # Comparison with historical best
    if sorted_dates:
        historical_pnls = [
            sum(s['realized_pnl'] + s['unrealized_pnl'] for s in daily_strategy_stats[date].values())
            for date in sorted_dates
        ]
        best_historical = max(historical_pnls) if historical_pnls else 0.0
        
        print(f"\n{'='*120}")
        print("🏆 COMPARISON WITH HISTORICAL BEST")
        print(f"{'='*120}")
        print(f"\nToday's P&L: ₹ {today_total_pnl:,.2f}")
        print(f"Best Historical Day: ₹ {best_historical:,.2f}")
        
        if today_total_pnl > best_historical:
            print(f"✅ Today is the BEST DAY! (+₹ {today_total_pnl - best_historical:,.2f} better)")
        elif today_total_pnl < best_historical:
            print(f"📊 Today is ₹ {best_historical - today_total_pnl:,.2f} below best day")
        else:
            print(f"➖ Today matches the best day")


def main():
    """Main function"""
    print_historical_comparison()
    
    print("\n" + "="*120)
    print("✅ Historical Comparison Complete")
    print("="*120 + "\n")


if __name__ == "__main__":
    main()






