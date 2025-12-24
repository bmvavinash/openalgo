#!/usr/bin/env python
"""
Fix all option strategies to add expiry date validation
"""
import os
import re
from pathlib import Path

STRATEGIES_DIR = Path('strategies/scripts')

def fix_option_strategy(file_path):
    """Add expiry date validation to an option strategy"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if validation already exists
    if 'Missing EXPIRY_DATE configuration' in content:
        print(f"  ✓ {file_path.name} already has validation")
        return False
    
    # Find the main() function
    main_pattern = r'(def main\(\):.*?)(\s+print\(f"Starting.*?Strategy"\).*?)(\s+print\(.*?\).*?)(\s+print\("-" \* 70\).*?)(\s+# Place)'
    
    # Try to find where to insert validation
    # Look for pattern: def main() -> print statements -> place order call
    lines = content.split('\n')
    new_lines = []
    i = 0
    found_main = False
    found_place = False
    
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # Found main function
        if 'def main():' in line:
            found_main = True
        
        # After main, look for print statements and then place order
        if found_main and not found_place:
            # Check if this is the line before place order call
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # If next line has place order or while loop, insert validation before it
                if ('place_' in next_line or 'while True' in next_line or '# Place' in next_line):
                    # Insert validation
                    new_lines.append('')
                    new_lines.append('    # Validate expiry date')
                    new_lines.append('    if not expiry_date or expiry_date.strip() == \'\':')
                    new_lines.append('        print(f"[{datetime.now()}] ERROR: Missing EXPIRY_DATE configuration. Skipping execution.")')
                    new_lines.append('        print(f"[{datetime.now()}] Please set EXPIRY_DATE environment variable (format: DDMMMYY or YYYY-MM-DD)")')
                    new_lines.append('        return')
                    new_lines.append('')
                    found_place = True
        
        i += 1
    
    if found_main and found_place:
        new_content = '\n'.join(new_lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✓ Fixed {file_path.name}")
        return True
    else:
        print(f"  ✗ Could not fix {file_path.name} - pattern not found")
        return False

def main():
    """Fix all option strategies"""
    option_files = list(STRATEGIES_DIR.glob('option_*_strategy_*.py'))
    
    print(f"Found {len(option_files)} option strategy files")
    print("=" * 70)
    
    fixed_count = 0
    for file_path in option_files:
        if fix_option_strategy(file_path):
            fixed_count += 1
    
    print("=" * 70)
    print(f"Fixed {fixed_count} out of {len(option_files)} option strategies")

if __name__ == "__main__":
    main()


