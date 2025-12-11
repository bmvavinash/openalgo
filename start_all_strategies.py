#!/usr/bin/env python
"""
Start All Strategies Script
Checks and starts all configured strategies that are not running
"""

import os
import sys
import json
import psutil
from pathlib import Path
from datetime import datetime
import pytz

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

IST = pytz.timezone('Asia/Kolkata')

def check_process_running(pid):
    """Check if a process is running"""
    try:
        process = psutil.Process(pid)
        return process.is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def load_strategy_configs():
    """Load strategy configurations"""
    config_file = Path('strategies') / 'strategy_configs.json'
    if not config_file.exists():
        return {}
    
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading configs: {e}")
        return {}

def save_strategy_configs(configs):
    """Save strategy configurations"""
    config_file = Path('strategies') / 'strategy_configs.json'
    try:
        with open(config_file, 'w') as f:
            json.dump(configs, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving configs: {e}")
        return False

def start_strategy(strategy_id, config):
    """Start a strategy by running it directly"""
    file_path = Path(config['file_path'])
    if not file_path.exists():
        print(f"  ERROR: Strategy file not found: {file_path}")
        return False
    
    try:
        import subprocess
        python_exe = sys.executable
        
        # Create log directory
        log_dir = Path('log') / 'strategies'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with timestamp
        ist_now = datetime.now(IST)
        log_file = log_dir / f"{strategy_id}_{ist_now.strftime('%Y%m%d_%H%M%S')}_IST.log"
        
        # Start process with correct working directory and Python path
        env = os.environ.copy()
        # Add current directory to PYTHONPATH (strategies expect openalgo directory in path)
        current_dir = str(Path.cwd())
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{current_dir}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = current_dir
        
        # Start process - strategies use sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        # This means they expect to be run from openalgo directory with absolute path
        with open(log_file, 'w', encoding='utf-8', buffering=1) as log_handle:
            # Use absolute path like the official system does
            process = subprocess.Popen(
                [python_exe, '-u', str(file_path.absolute())],
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                cwd=str(Path.cwd()),  # Must be openalgo directory
                env=env,
                bufsize=1  # Line buffered
            )
        
        # Update config
        config['is_running'] = True
        config['pid'] = process.pid
        config['last_started'] = ist_now.isoformat()
        if 'last_stopped' in config:
            del config['last_stopped']
        
        print(f"  Started with PID: {process.pid}")
        print(f"  Log file: {log_file}")
        return True
        
    except Exception as e:
        print(f"  ERROR: Failed to start: {e}")
        return False

def check_and_start_strategies():
    """Check all strategies and start those that aren't running"""
    configs = load_strategy_configs()
    current_time = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')
    
    print(f"\n{'='*80}")
    print(f"Strategy Status Check - {current_time}")
    print(f"{'='*80}\n")
    
    started_count = 0
    already_running_count = 0
    failed_count = 0
    
    for strategy_id, config in configs.items():
        name = config.get('name', 'Unknown')
        pid = config.get('pid')
        is_running = config.get('is_running', False)
        
        # Check if process is actually running
        actually_running = False
        if pid:
            actually_running = check_process_running(pid)
        
        print(f"Strategy: {name}")
        print(f"  ID: {strategy_id}")
        
        if is_running and actually_running:
            print(f"  Status: [RUNNING] (PID: {pid})")
            already_running_count += 1
        elif is_running and not actually_running:
            print(f"  Status: [DEAD] - Process marked running but not found")
            print(f"  Action: Starting...")
            if start_strategy(strategy_id, config):
                started_count += 1
            else:
                failed_count += 1
        else:
            print(f"  Status: [STOPPED]")
            print(f"  Action: Starting...")
            if start_strategy(strategy_id, config):
                started_count += 1
            else:
                failed_count += 1
        
        print()
    
    # Save updated configs
    if started_count > 0:
        save_strategy_configs(configs)
    
    print(f"{'='*80}")
    print(f"Summary:")
    print(f"  Already Running: {already_running_count}")
    print(f"  Started: {started_count}")
    print(f"  Failed: {failed_count}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    check_and_start_strategies()

