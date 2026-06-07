#!/usr/bin/env python
"""
Test script for metals backtesting framework
Validates strategies work correctly with historical data
"""

import os
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta

# Fix Windows encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Set environment
os.environ['DATABASE_URL'] = 'sqlite:///db/openalgo.db'

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

def test_adaptive_stop_loss():
    """Test adaptive stop-loss calculations"""
    print("\n" + "="*60)
    print("Testing Adaptive Stop-Loss Service")
    print("="*60)
    
    try:
        import pandas as pd
        import numpy as np
        from services.adaptive_stop_loss_service import (
            AdaptiveStopLossService, StopLossType, TradePosition
        )
        
        service = AdaptiveStopLossService()
        
        # Create sample price data
        dates = pd.date_range(start='2025-01-01', periods=100, freq='5min')
        np.random.seed(42)
        
        # Simulate gold price movement
        base_price = 60000
        returns = np.random.normal(0, 0.001, 100)
        prices = base_price * np.cumprod(1 + returns)
        
        df = pd.DataFrame({
            'open': prices * (1 + np.random.uniform(-0.001, 0.001, 100)),
            'high': prices * (1 + np.abs(np.random.uniform(0, 0.002, 100))),
            'low': prices * (1 - np.abs(np.random.uniform(0, 0.002, 100))),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        
        # Test position
        entry_price = 60000
        current_price = 60100
        
        position = TradePosition(
            entry_price=entry_price,
            current_price=current_price,
            action='BUY',
            entry_time=datetime.now(),
            current_stop_loss=None,
            highest_price=current_price,
            lowest_price=entry_price
        )
        
        # Test Fixed Stop Loss
        result = service.calculate_stop_loss(position, StopLossType.FIXED, df, stop_loss_pct=2.0)
        print(f"\n1. Fixed Stop Loss (2%):")
        print(f"   Entry: Rs.{entry_price:,.2f}")
        print(f"   Stop Loss: Rs.{result.stop_loss_price:,.2f}")
        print(f"   Distance: {result.distance_pct:.2f}%")
        
        # Test Trailing Stop Loss
        result = service.calculate_stop_loss(position, StopLossType.TRAILING, df, trailing_pct=1.5)
        print(f"\n2. Trailing Stop Loss (1.5%):")
        print(f"   Highest Price: Rs.{current_price:,.2f}")
        print(f"   Stop Loss: Rs.{result.stop_loss_price:,.2f}")
        print(f"   Distance: {result.distance_pct:.2f}%")
        
        # Test ATR-Based Stop Loss
        result = service.calculate_stop_loss(position, StopLossType.ATR_BASED, df, atr_multiplier=2.0)
        print(f"\n3. ATR-Based Stop Loss (2x ATR):")
        print(f"   ATR Value: Rs.{result.atr_value:,.2f}")
        print(f"   Stop Loss: Rs.{result.stop_loss_price:,.2f}")
        print(f"   Volatility Regime: {result.volatility_regime}")
        
        # Test Adaptive Stop Loss
        result = service.calculate_stop_loss(position, StopLossType.ADAPTIVE, df, base_stop_loss_pct=2.0)
        print(f"\n4. Adaptive Stop Loss:")
        print(f"   Stop Loss: Rs.{result.stop_loss_price:,.2f}")
        print(f"   Distance: {result.distance_pct:.2f}%")
        print(f"   Volatility Regime: {result.volatility_regime}")
        print(f"   Notes: {result.notes}")
        
        print("\n[PASS] Adaptive Stop-Loss Service: PASSED")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Adaptive Stop-Loss Service: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backtest_framework():
    """Test the backtesting framework"""
    print("\n" + "="*60)
    print("Testing Metals Backtesting Framework")
    print("="*60)
    
    try:
        # Import directly from the module file
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "metals_backtest_framework", 
            Path(__file__).parent / "strategies" / "backtest" / "metals_backtest_framework.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        MetalsBacktestEngine = module.MetalsBacktestEngine
        BacktestConfig = module.BacktestConfig
        
        # Create config for a quick test
        config = BacktestConfig(
            metal_type="GOLD",
            symbol="GC=F",  # Yahoo Finance gold futures symbol
            start_date=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            timeframe="1h",
            stop_loss_type="ADAPTIVE",
            stop_loss_pct=2.0,
            take_profit_pct=4.0,
            initial_capital=100000,
            min_signal_strength=40.0  # Lower threshold for testing
        )
        
        print(f"\nRunning backtest for {config.metal_type}...")
        print(f"Period: {config.start_date} to {config.end_date}")
        print(f"Timeframe: {config.timeframe}")
        print(f"Stop Loss: {config.stop_loss_type} ({config.stop_loss_pct}%)")
        
        engine = MetalsBacktestEngine(config)
        results = engine.run_backtest()
        
        print("\n" + "-"*40)
        print("BACKTEST RESULTS:")
        print("-"*40)
        print(f"Total Trades: {results.total_trades}")
        print(f"Winning Trades: {results.winning_trades}")
        print(f"Losing Trades: {results.losing_trades}")
        print(f"Win Rate: {results.win_rate:.2f}%")
        print(f"Total P&L: Rs.{results.total_pnl:,.2f} ({results.total_pnl_pct:.2f}%)")
        print(f"Profit Factor: {results.profit_factor:.2f}")
        print(f"Max Drawdown: {results.max_drawdown_pct:.2f}%")
        print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
        
        if results.exit_reasons:
            print("\nExit Reasons:")
            for reason, count in results.exit_reasons.items():
                print(f"  - {reason}: {count}")
        
        print("\n[PASS] Backtesting Framework: PASSED")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Backtesting Framework: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gold_strategy_signals():
    """Test gold strategy signal generation"""
    print("\n" + "="*60)
    print("Testing Gold Strategy Signal Generation")
    print("="*60)
    
    try:
        import pandas as pd
        import numpy as np
        
        # Mock dotenv if not available
        import sys
        if 'dotenv' not in sys.modules:
            class MockDotenv:
                def load_dotenv(self, *args, **kwargs):
                    pass
            sys.modules['dotenv'] = MockDotenv()
        
        # Create sample data
        dates = pd.date_range(start='2025-01-01', periods=200, freq='5min')
        np.random.seed(42)
        
        # Create trending price data
        base_price = 60000
        trend = np.linspace(0, 500, 200)  # Uptrend
        noise = np.random.normal(0, 50, 200)
        prices = base_price + trend + noise
        
        df = pd.DataFrame({
            'open': prices - np.abs(np.random.normal(0, 20, 200)),
            'high': prices + np.abs(np.random.normal(0, 50, 200)),
            'low': prices - np.abs(np.random.normal(0, 50, 200)),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 200)
        }, index=dates)
        
        # Test signal calculation
        from strategies.scripts.gold_trading_strategy import GoldTradingStrategy
        
        strategy = GoldTradingStrategy()
        analysis = strategy.analyze_signals(df)
        
        print(f"\nSignal Analysis:")
        print(f"  Signal: {analysis['signal']}")
        print(f"  Strength: {analysis['strength']:.1f}%")
        print(f"  Score: {analysis['score']:.3f}")
        print(f"  Current Price: Rs.{analysis['current_price']:,.2f}")
        
        print("\nComponent Signals:")
        for comp, data in analysis['components'].items():
            print(f"  - {comp}: {data['signal']} (value: {data['value']:.2f})")
        
        print("\n[PASS] Gold Strategy Signals: PASSED")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Gold Strategy Signals: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_silver_strategy_signals():
    """Test silver strategy signal generation"""
    print("\n" + "="*60)
    print("Testing Silver Strategy Signal Generation")
    print("="*60)
    
    try:
        import pandas as pd
        import numpy as np
        
        # Mock dotenv if not available
        import sys
        if 'dotenv' not in sys.modules:
            class MockDotenv:
                def load_dotenv(self, *args, **kwargs):
                    pass
            sys.modules['dotenv'] = MockDotenv()
        
        # Create sample data with higher volatility for silver
        dates = pd.date_range(start='2025-01-01', periods=200, freq='5min')
        np.random.seed(42)
        
        base_price = 75000
        trend = np.linspace(0, 800, 200)  # Uptrend
        noise = np.random.normal(0, 100, 200)  # Higher noise for silver
        prices = base_price + trend + noise
        
        df = pd.DataFrame({
            'open': prices - np.abs(np.random.normal(0, 30, 200)),
            'high': prices + np.abs(np.random.normal(0, 80, 200)),
            'low': prices - np.abs(np.random.normal(0, 80, 200)),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 200)
        }, index=dates)
        
        from strategies.scripts.silver_trading_strategy import SilverTradingStrategy
        
        strategy = SilverTradingStrategy()
        analysis = strategy.analyze_signals(df)
        
        print(f"\nSignal Analysis:")
        print(f"  Signal: {analysis['signal']}")
        print(f"  Strength: {analysis['strength']:.1f}%")
        print(f"  Score: {analysis['score']:.3f}")
        print(f"  Current Price: Rs.{analysis['current_price']:,.2f}")
        print(f"  Trend: {analysis.get('trend', 'N/A')}")
        
        print("\nComponent Signals:")
        for comp, data in analysis['components'].items():
            print(f"  - {comp}: {data['signal']} (value: {data['value']:.2f})")
        
        print("\n[PASS] Silver Strategy Signals: PASSED")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Silver Strategy Signals: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_notification_services():
    """Test notification services"""
    print("\n" + "="*60)
    print("Testing Notification Services")
    print("="*60)
    
    try:
        from services.metals_alert_service import metals_alert_service
        from services.whatsapp_service import whatsapp_service
        
        print("\nMetals Alert Service:")
        print(f"  - Telegram service loaded: {metals_alert_service.telegram_service is not None}")
        print(f"  - WhatsApp service loaded: {metals_alert_service.whatsapp_service is not None}")
        
        print("\nWhatsApp Service:")
        print(f"  - Is available: {whatsapp_service.is_available()}")
        print(f"  - Provider: {type(whatsapp_service.provider).__name__ if whatsapp_service.provider else 'None'}")
        
        # Test message formatting
        test_message = metals_alert_service._format_message(
            'trade_entry',
            emoji='🥇',
            metal='GOLD',
            action='BUY',
            price=60000,
            quantity=1,
            stop_loss=58800,
            sl_pct=2.0,
            take_profit=62400,
            tp_pct=4.0,
            signal_strength=75.5,
            volatility_regime='NORMAL',
            time='10:30:00'
        )
        
        print("\nSample Trade Entry Message:")
        print("-" * 40)
        print(test_message)
        print("-" * 40)
        
        print("\n[PASS] Notification Services: PASSED")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Notification Services: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("METALS TRADING SYSTEM - TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Adaptive Stop-Loss", test_adaptive_stop_loss()))
    results.append(("Gold Strategy Signals", test_gold_strategy_signals()))
    results.append(("Silver Strategy Signals", test_silver_strategy_signals()))
    results.append(("Notification Services", test_notification_services()))
    results.append(("Backtesting Framework", test_backtest_framework()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS] PASSED" if result else "[FAIL] FAILED"
        print(f"{name}: {status}")
    
    print("-"*40)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! The metals trading system is ready.")
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Please review the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
