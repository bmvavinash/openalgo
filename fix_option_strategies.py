#!/usr/bin/env python3
"""
Fix all option strategies to show proper error messages
"""
import re
from pathlib import Path

STRATEGIES_DIR = Path('strategies/scripts')

# Pattern to find and replace
OLD_PATTERN = r"print\(f\"  Leg \{leg\.get\('leg'\)\}: \{leg\.get\('action'\)\} \{leg\.get\('option_type'\)\} \"\s+f\"\{leg\.get\('offset'\)\} - \{leg\.get\('status'\)\} - \{leg\.get\('orderid'\)\}\"\)"

NEW_CODE = """            for leg in response.get('results', []):
                leg_status = leg.get('status', 'unknown')
                leg_orderid = leg.get('orderid', 'N/A')
                leg_message = leg.get('message', '')
                if leg_status == 'success':
                    print(f"  Leg {leg.get('leg')}: {leg.get('action')} {leg.get('option_type')} "
                          f"{leg.get('offset')} - {leg_status} - OrderID: {leg_orderid}")
                else:
                    error_msg = leg_message or 'Unknown error'
                    print(f"  Leg {leg.get('leg')}: {leg.get('action')} {leg.get('option_type')} "
                          f"{leg.get('offset')} - {leg_status} - Error: {error_msg}")"""

def fix_strategy_file(file_path):
    """Fix a single strategy file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file needs fixing
        if "leg.get('orderid')" in content and "leg_status = leg.get('status'" not in content:
            # Find the pattern and replace
            pattern = r"for leg in response\.get\('results', \[\]\):\s+print\(f\"  Leg \{leg\.get\('leg'\)\}: \{leg\.get\('action'\)\} \{leg\.get\('option_type'\)\} \"\s+f\"\{leg\.get\('offset'\)\} - \{leg\.get\('status'\)\} - \{leg\.get\('orderid'\)\}\"\)"
            
            if re.search(pattern, content):
                content = re.sub(pattern, NEW_CODE, content)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Fixed: {file_path.name}")
                return True
            else:
                # Try simpler pattern
                old_code = """for leg in response.get('results', []):
                print(f"  Leg {leg.get('leg')}: {leg.get('action')} {leg.get('option_type')} "
                      f"{leg.get('offset')} - {leg.get('status')} - {leg.get('orderid')}")"""
                
                if old_code in content:
                    content = content.replace(old_code, NEW_CODE)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Fixed: {file_path.name}")
                    return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path.name}: {e}")
        return False

def main():
    """Fix all option strategy files"""
    option_files = list(STRATEGIES_DIR.glob('option_*_strategy*.py'))
    fixed_count = 0
    
    print(f"Found {len(option_files)} option strategy files")
    
    for file_path in option_files:
        if fix_strategy_file(file_path):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()




