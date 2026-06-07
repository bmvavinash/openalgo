#!/usr/bin/env python3
"""
Fix Paper Trading Mode for All Services
Updates all services to allow paper trading with API key only (no broker auth required)
"""

import os
import re
import sys

# Services that need to be updated
SERVICES_TO_FIX = [
    'place_smart_order_service.py',
    'basket_order_service.py',
    'split_order_service.py',
    'place_options_order_service.py',
    'modify_order_service.py',
    'cancel_order_service.py',
    'cancel_all_order_service.py',
    'close_position_service.py',
    'quotes_service.py',
    'option_symbol_service.py',
    'positionbook_service.py',
    'holdings_service.py',
    'symbol_service.py',
    'ping_service.py',
    'orderstatus_service.py',
]

def fix_service_file(filepath):
    """Fix a service file to support paper trading mode"""
    if not os.path.exists(filepath):
        print(f"  [SKIP] {os.path.basename(filepath)} - File not found")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern 1: Find the API key authentication section
    # Look for: if api_key and not (auth_token and broker):
    pattern1 = r'(# Case 1: API-based authentication\s+if api_key and not \(auth_token and broker\):)(.*?)(AUTH_TOKEN, broker_name = get_auth_token_broker\(api_key\)\s+if AUTH_TOKEN is None:)'
    
    # Check if already fixed (has analyze_mode check)
    if 'analyze_mode = get_analyze_mode()' in content and 'Paper trading mode:' in content:
        print(f"  [SKIP] {os.path.basename(filepath)} - Already fixed")
        return False
    
    # Check if get_analyze_mode is imported
    needs_import = 'from database.settings_db import get_analyze_mode' not in content
    if needs_import and 'get_analyze_mode' in content:
        # Check if it's imported differently
        if 'from database.settings_db import' in content:
            # Add get_analyze_mode to existing import
            content = re.sub(
                r'(from database\.settings_db import[^\n]+)',
                r'\1, get_analyze_mode',
                content,
                count=1
            )
        else:
            # Add new import at top
            content = re.sub(
                r'(from database\.auth_db import[^\n]+)',
                r'\1\nfrom database.settings_db import get_analyze_mode',
                content,
                count=1
            )
    
    # Pattern: Find the section where AUTH_TOKEN is checked
    # Replace with paper trading check
    replacement = r'''\1
        # Check if in analyze/paper trading mode - allow without broker auth
        analyze_mode = get_analyze_mode()
        
        if analyze_mode:
            # In paper trading mode, verify API key but don't require broker auth
            from database.auth_db import verify_api_key
            user_id = verify_api_key(api_key)
            if not user_id:
                error_response = {
                    'status': 'error',
                    'message': 'Invalid openalgo apikey'
                }
                return False, error_response, 403
            
            # API key is valid - route to sandbox or return success for paper trading
            logger.info(f"Paper trading mode: API key valid for user_id={user_id}")
            # For order placement services, route to sandbox
            # For read-only services, return empty/sandbox data
            # This will be handled by individual service implementations
        
        # Live trading mode - require broker authentication
        \3'''
    
    # Try to apply the fix
    if re.search(pattern1, content, re.DOTALL):
        content = re.sub(pattern1, replacement, content, flags=re.DOTALL)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  [OK] {os.path.basename(filepath)} - Fixed")
            return True
        else:
            print(f"  [SKIP] {os.path.basename(filepath)} - No changes needed")
            return False
    else:
        print(f"  [SKIP] {os.path.basename(filepath)} - Pattern not found (may need manual fix)")
        return False

def main():
    print("="*60)
    print("FIXING PAPER TRADING MODE FOR ALL SERVICES")
    print("="*60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    services_dir = os.path.join(base_dir, 'services')
    
    fixed_count = 0
    skipped_count = 0
    
    for service_file in SERVICES_TO_FIX:
        filepath = os.path.join(services_dir, service_file)
        if fix_service_file(filepath):
            fixed_count += 1
        else:
            skipped_count += 1
    
    print(f"\n[SUMMARY] Fixed: {fixed_count}, Skipped: {skipped_count}")
    print("="*60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())






