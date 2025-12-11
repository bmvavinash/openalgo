#!/usr/bin/env python3
"""
Check and resolve merge conflicts
"""
import subprocess
import os
import re

repo_path = r"f:\2nd Income\Stock Market\Code\openalgo"
os.chdir(repo_path)

def run_git(cmd_list):
    """Run a git command and return the result"""
    try:
        result = subprocess.run(
            ['git'] + cmd_list,
            capture_output=True,
            text=True,
            cwd=repo_path
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

print("="*80)
print("CHECKING MERGE CONFLICTS")
print("="*80)

# Check current branch
success, branch, _ = run_git(['branch', '--show-current'])
print(f"Current branch: {branch}")

# Check status
success, status, _ = run_git(['status', '--porcelain'])
if success:
    conflicted_files = []
    for line in status.splitlines():
        if 'UU' in line or 'AA' in line or 'DD' in line:
            parts = line.split()
            if len(parts) > 1:
                conflicted_files.append(parts[1])
    
    if conflicted_files:
        print(f"\nFound {len(conflicted_files)} conflicted file(s):")
        for cf in conflicted_files:
            print(f"  - {cf}")
        
        # Save conflicted files list
        with open('conflicted_files.txt', 'w') as f:
            for cf in conflicted_files:
                f.write(cf + '\n')
        
        print("\nConflicted files saved to: conflicted_files.txt")
    else:
        print("\nNo conflicts found!")
else:
    print("Could not check status")

# Get full status
success, full_status, _ = run_git(['status'])
if success:
    print("\n" + "="*80)
    print("FULL GIT STATUS")
    print("="*80)
    print(full_status)




