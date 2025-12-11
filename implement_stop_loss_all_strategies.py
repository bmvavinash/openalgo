"""
Implement stop loss for all strategies that don't have it
"""
import sys
import re
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.config_loader import get_config

def find_strategy_files() -> List[Path]:
    """Find all Python strategy files"""
    strategies_dir = PROJECT_ROOT / 'strategies' / 'scripts'
    if not strategies_dir.exists():
        return []
    
    return list(strategies_dir.glob('*.py'))


def check_has_stop_loss(file_path: Path) -> Tuple[bool, List[str]]:
    """Check if strategy file has stop loss implementation"""
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Check for stop loss related code
        stop_loss_indicators = [
            'stop_loss',
            'stoploss',
            'stop loss',
            'SL-M',
            'SL',
            'trigger_price',
            'place_stop_loss',
            'manage_stop_loss'
        ]
        
        has_stop_loss = any(indicator.lower() in content.lower() for indicator in stop_loss_indicators)
        
        # Get strategy name from file
        strategy_name_match = re.search(r'STRATEGY_NAME\s*=\s*["\']([^"\']+)["\']', content)
        strategy_name = strategy_name_match.group(1) if strategy_name_match else file_path.stem
        
        return has_stop_loss, [strategy_name]
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False, []


def add_stop_loss_to_strategy(file_path: Path, stop_loss_pct: float = 2.0):
    """Add stop loss implementation to a strategy file"""
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Check if already has stop loss
        has_stop_loss, _ = check_has_stop_loss(file_path)
        if has_stop_loss:
            print(f"  ✅ {file_path.name} already has stop loss")
            return False
        
        # Get strategy name
        strategy_name_match = re.search(r'STRATEGY_NAME\s*=\s*["\']([^"\']+)["\']', content)
        strategy_name = strategy_name_match.group(1) if strategy_name_match else "Strategy"
        
        # Add stop loss tracking variables after position tracking
        if 'positions = {' in content:
            # Add stop loss tracking after positions
            positions_pattern = r'(positions\s*=\s*\{[^}]+\})'
            replacement = f'\\1\n\n# Stop loss tracking\nstop_loss_prices = {{symbol: None for symbol in SYMBOLS}}\nentry_prices = {{symbol: None for symbol in SYMBOLS}}'
            content = re.sub(positions_pattern, replacement, content)
        else:
            # Add after SYMBOLS definition
            symbols_pattern = r'(SYMBOLS\s*=\s*[^\n]+)'
            if re.search(symbols_pattern, content):
                content = re.sub(
                    symbols_pattern,
                    f'\\1\n\n# Stop loss tracking\nSTOP_LOSS_PCT = {stop_loss_pct}\nstop_loss_prices = {{symbol: None for symbol in SYMBOLS}}\nentry_prices = {{symbol: None for symbol in SYMBOLS}}',
                    content,
                    count=1
                )
        
        # Add stop loss configuration from risk management
        if 'risk_config = config.get_risk_management_config()' not in content:
            # Find where config is loaded
            config_pattern = r'(strategy_config\s*=\s*config\.get_strategy_config\([^)]+\))'
            if re.search(config_pattern, content):
                content = re.sub(
                    config_pattern,
                    f'\\1\nrisk_config = config.get_risk_management_config()',
                    content
                )
        
        # Add stop loss percentage constant
        if f'STOP_LOSS_PCT = {stop_loss_pct}' not in content:
            # Add after risk_config
            risk_config_pattern = r'(risk_config\s*=\s*config\.get_risk_management_config\(\))'
            if re.search(risk_config_pattern, content):
                content = re.sub(
                    risk_config_pattern,
                    f'\\1\nSTOP_LOSS_PCT = risk_config.get("stop_loss_pct", {stop_loss_pct})',
                    content
                )
            elif 'STOP_LOSS_PCT' not in content:
                # Add after QUANTITY
                quantity_pattern = r'(QUANTITY\s*=\s*[^\n]+)'
                if re.search(quantity_pattern, content):
                    content = re.sub(
                        quantity_pattern,
                        f'\\1\nSTOP_LOSS_PCT = {stop_loss_pct}',
                        content,
                        count=1
                    )
        
        # Modify place_order function to track entry prices
        if 'def place_order(' in content:
            # Find place_order function and add entry price tracking
            place_order_pattern = r'(def place_order\([^)]+\):[^:]+if response\.get\([\'"]status[\'"]\)\s*==\s*[\'"]success[\'"]:)'
            if re.search(place_order_pattern, content, re.DOTALL):
                content = re.sub(
                    place_order_pattern,
                    f'\\1\n                        entry_prices[symbol] = signals.get(\'price\') or df[\'close\'].iloc[-1]',
                    content,
                    flags=re.DOTALL
                )
        
        # Add stop loss check function before run_strategy
        stop_loss_function = f'''
def check_and_place_stop_loss(symbol: str, df: pd.DataFrame):
    """Check if stop loss should be triggered and place order if needed"""
    try:
        if entry_prices[symbol] is None or stop_loss_prices[symbol] is None:
            return
        
        current_price = df['close'].iloc[-1]
        entry_price = entry_prices[symbol]
        current_position = positions[symbol]
        
        if current_position > 0:  # Long position
            # Check if price dropped below stop loss
            if current_price <= stop_loss_prices[symbol]:
                logger.warning(f"STOP LOSS TRIGGERED for {{symbol}} at {{current_price:.2f}} (Entry: {{entry_price:.2f}})")
                response = place_order(symbol, "SELL", abs(current_position))
                if response.get('status') == 'success':
                    positions[symbol] = 0
                    entry_prices[symbol] = None
                    stop_loss_prices[symbol] = None
                    logger.info(f"Stop loss executed for {{symbol}}")
        
        elif current_position < 0:  # Short position
            # Check if price rose above stop loss
            if current_price >= stop_loss_prices[symbol]:
                logger.warning(f"STOP LOSS TRIGGERED for {{symbol}} at {{current_price:.2f}} (Entry: {{entry_price:.2f}})")
                response = place_order(symbol, "BUY", abs(current_position))
                if response.get('status') == 'success':
                    positions[symbol] = 0
                    entry_prices[symbol] = None
                    stop_loss_prices[symbol] = None
                    logger.info(f"Stop loss executed for {{symbol}}")
    
    except Exception as e:
        logger.error(f"Error checking stop loss for {{symbol}}: {{e}}")


'''
        
        # Insert stop loss function before run_strategy
        if 'def check_and_place_stop_loss' not in content:
            run_strategy_pattern = r'(def run_strategy\(\):)'
            if re.search(run_strategy_pattern, content):
                content = re.sub(run_strategy_pattern, stop_loss_function + '\\1', content)
        
        # Modify run_strategy to set stop loss on entry and check on each iteration
        if 'if signals[\'buy\']' in content or 'if signals["buy"]' in content:
            # Add stop loss setting after buy signal
            buy_pattern = r'(if signals\[[\'"]buy[\'"]\]\s+and\s+current_position\s*<=\s*0:[^}]+positions\[symbol\]\s*=\s*QUANTITY)'
            replacement = f'\\1\n                        entry_prices[symbol] = signals.get(\'price\') or df[\'close\'].iloc[-1]\n                        stop_loss_prices[symbol] = entry_prices[symbol] * (1 - STOP_LOSS_PCT / 100)'
            content = re.sub(buy_pattern, replacement, content, flags=re.DOTALL)
        
        if 'if signals[\'sell\']' in content or 'if signals["sell"]' in content:
            # Add stop loss setting after sell signal (for short)
            sell_pattern = r'(if signals\[[\'"]sell[\'"]\]\s+and\s+current_position\s*>=\s*0:[^}]+positions\[symbol\]\s*=\s*-QUANTITY)'
            replacement = f'\\1\n                        entry_prices[symbol] = signals.get(\'price\') or df[\'close\'].iloc[-1]\n                        stop_loss_prices[symbol] = entry_prices[symbol] * (1 + STOP_LOSS_PCT / 100)'
            content = re.sub(sell_pattern, replacement, content, flags=re.DOTALL)
        
        # Add stop loss check in main loop
        if 'for symbol in SYMBOLS:' in content:
            # Add stop loss check after signal check
            symbol_loop_pattern = r'(for symbol in SYMBOLS:[^}]+logger\.debug\([^)]+\))'
            if re.search(symbol_loop_pattern, content, re.DOTALL):
                content = re.sub(
                    symbol_loop_pattern,
                    f'\\1\n                \n                # Check stop loss\n                check_and_place_stop_loss(symbol, df)',
                    content,
                    flags=re.DOTALL
                )
        
        # Write updated content
        file_path.write_text(content, encoding='utf-8')
        print(f"  ✅ Added stop loss to {file_path.name}")
        return True
    
    except Exception as e:
        print(f"  ❌ Error adding stop loss to {file_path.name}: {e}")
        return False


def main():
    """Main function to implement stop loss for all strategies"""
    print("\n" + "="*80)
    print("🛡️  IMPLEMENTING STOP LOSS FOR ALL STRATEGIES")
    print("="*80)
    
    # Get stop loss percentage from config
    config = get_config()
    risk_config = config.get_risk_management_config()
    stop_loss_pct = risk_config.get('stop_loss_pct', 2.0)
    
    print(f"\nStop Loss Percentage: {stop_loss_pct}%")
    print(f"Source: risk_management.stop_loss_pct from config\n")
    
    # Find all strategy files
    strategy_files = find_strategy_files()
    
    if not strategy_files:
        print("❌ No strategy files found in strategies/scripts/")
        return
    
    print(f"Found {len(strategy_files)} strategy file(s):\n")
    
    # Check and update each strategy
    updated_count = 0
    already_has_count = 0
    
    for strategy_file in strategy_files:
        print(f"📄 {strategy_file.name}:")
        has_stop_loss, strategy_names = check_has_stop_loss(strategy_file)
        
        if has_stop_loss:
            print(f"  ✅ Already has stop loss implementation")
            already_has_count += 1
        else:
            if add_stop_loss_to_strategy(strategy_file, stop_loss_pct):
                updated_count += 1
            else:
                print(f"  ⚠️  Could not add stop loss (may need manual review)")
    
    print(f"\n{'='*80}")
    print("📊 SUMMARY")
    print(f"{'='*80}")
    print(f"Total Strategies: {len(strategy_files)}")
    print(f"✅ Updated: {updated_count}")
    print(f"✅ Already had stop loss: {already_has_count}")
    print(f"❌ Failed: {len(strategy_files) - updated_count - already_has_count}")
    
    if updated_count > 0:
        print(f"\n💡 Next Steps:")
        print(f"   1. Review updated strategy files")
        print(f"   2. Test strategies in paper trading mode")
        print(f"   3. Monitor stop loss execution")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()






