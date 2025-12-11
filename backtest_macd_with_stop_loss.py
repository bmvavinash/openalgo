"""
Backtest MACD Strategy with Stop Loss
Compares MACD performance with and without stop loss
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.config_loader import get_config
from utils.nse_data_fetcher import get_nse_data

def calculate_macd(data: pd.DataFrame, fast=12, slow=26, signal=9):
    """Calculate MACD indicators"""
    ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def backtest_macd_without_stop_loss(df: pd.DataFrame, symbol: str, quantity: int = 1):
    """Backtest MACD strategy without stop loss"""
    trades = []
    position = 0
    entry_price = None
    
    macd_line, signal_line, histogram = calculate_macd(df)
    
    for i in range(1, len(df)):
        prev_macd = macd_line.iloc[i-1]
        curr_macd = macd_line.iloc[i]
        prev_signal = signal_line.iloc[i-1]
        curr_signal = signal_line.iloc[i]
        current_price = df['close'].iloc[i]
        
        # Buy signal: MACD crosses above signal
        buy_signal = (prev_macd < prev_signal) and (curr_macd > curr_signal)
        # Sell signal: MACD crosses below signal
        sell_signal = (prev_macd > prev_signal) and (curr_macd < curr_signal)
        
        if buy_signal and position <= 0:
            if position < 0:
                # Close short position
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'entry_time': df.index[i],
                    'exit_time': df.index[i],
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': abs(position),
                    'action': 'BUY',
                    'pnl': pnl,
                    'type': 'CLOSE_SHORT'
                })
            
            # Open long position
            position = quantity
            entry_price = current_price
        
        elif sell_signal and position >= 0:
            if position > 0:
                # Close long position
                pnl = (current_price - entry_price) * position
                trades.append({
                    'entry_time': df.index[i],
                    'exit_time': df.index[i],
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': position,
                    'action': 'SELL',
                    'pnl': pnl,
                    'type': 'CLOSE_LONG'
                })
            
            # Open short position
            position = -quantity
            entry_price = current_price
    
    # Close any open position at the end
    if position != 0:
        final_price = df['close'].iloc[-1]
        pnl = (final_price - entry_price) * position if position > 0 else (entry_price - final_price) * abs(position)
        trades.append({
            'entry_time': df.index[-1],
            'exit_time': df.index[-1],
            'entry_price': entry_price,
            'exit_price': final_price,
            'quantity': abs(position),
            'action': 'SELL' if position > 0 else 'BUY',
            'pnl': pnl,
            'type': 'FINAL_CLOSE'
        })
    
    return trades


def backtest_macd_with_stop_loss(df: pd.DataFrame, symbol: str, quantity: int = 1, stop_loss_pct: float = 2.0):
    """Backtest MACD strategy with stop loss"""
    trades = []
    position = 0
    entry_price = None
    stop_loss_price = None
    
    macd_line, signal_line, histogram = calculate_macd(df)
    
    for i in range(1, len(df)):
        prev_macd = macd_line.iloc[i-1]
        curr_macd = macd_line.iloc[i]
        prev_signal = signal_line.iloc[i-1]
        curr_signal = signal_line.iloc[i]
        current_price = df['close'].iloc[i]
        
        # Check stop loss first
        if position != 0 and stop_loss_price is not None:
            if position > 0:  # Long position
                if current_price <= stop_loss_price:
                    # Stop loss triggered
                    pnl = (current_price - entry_price) * position
                    trades.append({
                        'entry_time': df.index[i],
                        'exit_time': df.index[i],
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'quantity': position,
                        'action': 'SELL',
                        'pnl': pnl,
                        'type': 'STOP_LOSS',
                        'stop_loss_price': stop_loss_price
                    })
                    position = 0
                    entry_price = None
                    stop_loss_price = None
                    continue
            
            elif position < 0:  # Short position
                if current_price >= stop_loss_price:
                    # Stop loss triggered
                    pnl = (entry_price - current_price) * abs(position)
                    trades.append({
                        'entry_time': df.index[i],
                        'exit_time': df.index[i],
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'quantity': abs(position),
                        'action': 'BUY',
                        'pnl': pnl,
                        'type': 'STOP_LOSS',
                        'stop_loss_price': stop_loss_price
                    })
                    position = 0
                    entry_price = None
                    stop_loss_price = None
                    continue
        
        # Buy signal: MACD crosses above signal
        buy_signal = (prev_macd < prev_signal) and (curr_macd > curr_signal)
        # Sell signal: MACD crosses below signal
        sell_signal = (prev_macd > prev_signal) and (curr_macd < curr_signal)
        
        if buy_signal and position <= 0:
            if position < 0:
                # Close short position
                pnl = (entry_price - current_price) * abs(position)
                trades.append({
                    'entry_time': df.index[i],
                    'exit_time': df.index[i],
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': abs(position),
                    'action': 'BUY',
                    'pnl': pnl,
                    'type': 'CLOSE_SHORT'
                })
            
            # Open long position
            position = quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        
        elif sell_signal and position >= 0:
            if position > 0:
                # Close long position
                pnl = (current_price - entry_price) * position
                trades.append({
                    'entry_time': df.index[i],
                    'exit_time': df.index[i],
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'quantity': position,
                    'action': 'SELL',
                    'pnl': pnl,
                    'type': 'CLOSE_LONG'
                })
            
            # Open short position
            position = -quantity
            entry_price = current_price
            stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
    
    # Close any open position at the end
    if position != 0:
        final_price = df['close'].iloc[-1]
        pnl = (final_price - entry_price) * position if position > 0 else (entry_price - final_price) * abs(position)
        trades.append({
            'entry_time': df.index[-1],
            'exit_time': df.index[-1],
            'entry_price': entry_price,
            'exit_price': final_price,
            'quantity': abs(position),
            'action': 'SELL' if position > 0 else 'BUY',
            'pnl': pnl,
            'type': 'FINAL_CLOSE'
        })
    
    return trades


def analyze_backtest_results(trades_without_sl, trades_with_sl, symbol: str):
    """Analyze and compare backtest results"""
    
    total_pnl_without = sum(t['pnl'] for t in trades_without_sl)
    total_pnl_with = sum(t['pnl'] for t in trades_with_sl)
    
    winning_without = [t for t in trades_without_sl if t['pnl'] > 0]
    losing_without = [t for t in trades_without_sl if t['pnl'] < 0]
    
    winning_with = [t for t in trades_with_sl if t['pnl'] > 0]
    losing_with = [t for t in trades_with_sl if t['pnl'] < 0]
    
    stop_loss_trades = [t for t in trades_with_sl if t.get('type') == 'STOP_LOSS']
    
    results = {
        'symbol': symbol,
        'without_stop_loss': {
            'total_pnl': total_pnl_without,
            'total_trades': len(trades_without_sl),
            'winning_trades': len(winning_without),
            'losing_trades': len(losing_without),
            'win_rate': (len(winning_without) / len(trades_without_sl) * 100) if trades_without_sl else 0,
            'avg_win': sum(t['pnl'] for t in winning_without) / len(winning_without) if winning_without else 0,
            'avg_loss': sum(t['pnl'] for t in losing_without) / len(losing_without) if losing_without else 0,
            'max_loss': min((t['pnl'] for t in losing_without), default=0)
        },
        'with_stop_loss': {
            'total_pnl': total_pnl_with,
            'total_trades': len(trades_with_sl),
            'winning_trades': len(winning_with),
            'losing_trades': len(losing_with),
            'win_rate': (len(winning_with) / len(trades_with_sl) * 100) if trades_with_sl else 0,
            'avg_win': sum(t['pnl'] for t in winning_with) / len(winning_with) if winning_with else 0,
            'avg_loss': sum(t['pnl'] for t in losing_with) / len(losing_with) if losing_with else 0,
            'max_loss': min((t['pnl'] for t in losing_with), default=0),
            'stop_loss_triggers': len(stop_loss_trades)
        },
        'improvement': {
            'pnl_difference': total_pnl_with - total_pnl_without,
            'improvement_pct': ((total_pnl_with - total_pnl_without) / abs(total_pnl_without) * 100) if total_pnl_without != 0 else 0
        }
    }
    
    return results


def print_backtest_results(results):
    """Print backtest comparison results"""
    
    print("\n" + "="*120)
    print(f"📊 MACD BACKTEST RESULTS - {results['symbol']}")
    print("="*120)
    
    without = results['without_stop_loss']
    with_sl = results['with_stop_loss']
    improvement = results['improvement']
    
    print(f"\n{'Metric':<30} {'Without Stop Loss':<25} {'With Stop Loss (2%)':<25} {'Difference':<20}")
    print("-"*120)
    
    print(f"{'Total P&L':<30} ₹ {without['total_pnl']:>20,.2f} ₹ {with_sl['total_pnl']:>20,.2f} "
          f"₹ {improvement['pnl_difference']:>15,.2f}")
    
    print(f"{'Total Trades':<30} {without['total_trades']:>25} {with_sl['total_trades']:>25} "
          f"{with_sl['total_trades'] - without['total_trades']:>20}")
    
    print(f"{'Winning Trades':<30} {without['winning_trades']:>25} {with_sl['winning_trades']:>25} "
          f"{with_sl['winning_trades'] - without['winning_trades']:>20}")
    
    print(f"{'Losing Trades':<30} {without['losing_trades']:>25} {with_sl['losing_trades']:>25} "
          f"{with_sl['losing_trades'] - without['losing_trades']:>20}")
    
    print(f"{'Win Rate':<30} {without['win_rate']:>23.1f}% {with_sl['win_rate']:>23.1f}% "
          f"{with_sl['win_rate'] - without['win_rate']:>18.1f}%")
    
    print(f"{'Average Win':<30} ₹ {without['avg_win']:>20,.2f} ₹ {with_sl['avg_win']:>20,.2f} "
          f"₹ {with_sl['avg_win'] - without['avg_win']:>15,.2f}")
    
    print(f"{'Average Loss':<30} ₹ {without['avg_loss']:>20,.2f} ₹ {with_sl['avg_loss']:>20,.2f} "
          f"₹ {with_sl['avg_loss'] - without['avg_loss']:>15,.2f}")
    
    print(f"{'Max Loss':<30} ₹ {without['max_loss']:>20,.2f} ₹ {with_sl['max_loss']:>20,.2f} "
          f"₹ {with_sl['max_loss'] - without['max_loss']:>15,.2f}")
    
    print(f"{'Stop Loss Triggers':<30} {'N/A':<25} {with_sl['stop_loss_triggers']:>25} {'N/A':<20}")
    
    print("\n" + "="*120)
    
    if improvement['pnl_difference'] > 0:
        print(f"✅ Stop Loss IMPROVED performance by ₹ {improvement['pnl_difference']:,.2f} "
              f"({improvement['improvement_pct']:.1f}%)")
    elif improvement['pnl_difference'] < 0:
        print(f"⚠️  Stop Loss REDUCED performance by ₹ {abs(improvement['pnl_difference']):,.2f} "
              f"({abs(improvement['improvement_pct']):.1f}%)")
    else:
        print(f"➖ Stop Loss had NO IMPACT on performance")
    
    print("="*120 + "\n")


def main():
    """Main backtest function"""
    print("\n" + "="*120)
    print("🔬 MACD STRATEGY BACKTESTING - WITH vs WITHOUT STOP LOSS")
    print("="*120)
    
    # Get configuration
    config = get_config()
    trading_config = config.get_trading_preferences()
    risk_config = config.get_risk_management_config()
    historical_config = config.get_historical_data_config()
    
    symbols = trading_config.get('symbols', ['NIFTY', 'BANKNIFTY'])
    quantity = trading_config.get('quantity', 1)
    stop_loss_pct = risk_config.get('stop_loss_pct', 2.0)
    period = historical_config.get('period', '1Y')
    interval = historical_config.get('interval', '5m')
    
    print(f"\nConfiguration:")
    print(f"  Symbols: {symbols}")
    print(f"  Quantity: {quantity}")
    print(f"  Stop Loss: {stop_loss_pct}%")
    print(f"  Period: {period}")
    print(f"  Interval: {interval}\n")
    
    all_results = []
    
    for symbol in symbols:
        print(f"\n{'─'*120}")
        print(f"Backtesting {symbol}...")
        print(f"{'─'*120}")
        
        try:
            # Fetch historical data
            df = get_nse_data(symbol=symbol, exchange='NSE', interval=interval, period=period)
            
            if df.empty:
                print(f"  ⚠️  No data available for {symbol}")
                continue
            
            print(f"  ✅ Loaded {len(df)} data points")
            
            # Backtest without stop loss
            print(f"  🔄 Running backtest WITHOUT stop loss...")
            trades_without_sl = backtest_macd_without_stop_loss(df, symbol, quantity)
            
            # Backtest with stop loss
            print(f"  🔄 Running backtest WITH {stop_loss_pct}% stop loss...")
            trades_with_sl = backtest_macd_with_stop_loss(df, symbol, quantity, stop_loss_pct)
            
            # Analyze results
            results = analyze_backtest_results(trades_without_sl, trades_with_sl, symbol)
            all_results.append(results)
            
            # Print results
            print_backtest_results(results)
        
        except Exception as e:
            print(f"  ❌ Error backtesting {symbol}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Summary
    if all_results:
        print("\n" + "="*120)
        print("📊 OVERALL SUMMARY")
        print("="*120)
        
        total_without = sum(r['without_stop_loss']['total_pnl'] for r in all_results)
        total_with = sum(r['with_stop_loss']['total_pnl'] for r in all_results)
        total_improvement = total_with - total_without
        
        print(f"\nTotal P&L Without Stop Loss: ₹ {total_without:,.2f}")
        print(f"Total P&L With Stop Loss: ₹ {total_with:,.2f}")
        print(f"Improvement: ₹ {total_improvement:,.2f}")
        
        if total_improvement > 0:
            print(f"\n✅ Stop Loss improves overall performance by ₹ {total_improvement:,.2f}")
        else:
            print(f"\n⚠️  Stop Loss reduces overall performance by ₹ {abs(total_improvement):,.2f}")
        
        print("="*120 + "\n")


if __name__ == "__main__":
    main()






