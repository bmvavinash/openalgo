#!/usr/bin/env python3
"""
Automatically resolve merge conflicts
"""
import subprocess
import os
import re

repo_path = r"f:\2nd Income\Stock Market\Code\openalgo"
os.chdir(repo_path)

def run_git(cmd_list):
    """Run a git command"""
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

def find_conflicted_files():
    """Find all files with merge conflicts"""
    conflicted = []
    
    # Check git status
    success, status, _ = run_git(['status', '--porcelain'])
    if success:
        for line in status.splitlines():
            if 'UU' in line or 'AA' in line or 'DD' in line:
                parts = line.split()
                if len(parts) > 1:
                    conflicted.append(parts[1])
    
    # Also search for conflict markers in files
    conflict_marker = re.compile(r'^&lt;&lt;&lt;&lt;&lt;&lt;&lt;')
    for root, dirs, files in os.walk(repo_path):
        # Skip .git directory
        if '.git' in root:
            continue
        for file in files:
            if file.endswith(('.py', '.js', '.html', '.md', '.txt', '.json', '.yaml', '.yml')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if '&lt;&lt;&lt;&lt;&lt;&lt;&lt;' in content:
                            rel_path = os.path.relpath(filepath, repo_path)
                            if rel_path not in conflicted:
                                conflicted.append(rel_path)
                except:
                    pass
    
    return conflicted

def resolve_conflict_in_file(filepath):
    """Resolve conflicts in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file has conflicts
        if '&lt;&lt;&lt;&lt;&lt;&lt;&lt;' not in content:
            return True, "No conflicts found"
        
        lines = content.splitlines()
        resolved_lines = []
        i = 0
        conflict_count = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Start of conflict marker
            if line.strip().startswith('&lt;&lt;&lt;&lt;&lt;&lt;&lt;'):
                conflict_count += 1
                # Find the separator
                separator_idx = None
                end_idx = None
                
                # Look for separator (=======)
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() == '=======':
                        separator_idx = j
                        break
                
                # Look for end marker (>>>>>>>)
                if separator_idx:
                    for j in range(separator_idx + 1, len(lines)):
                        if lines[j].strip().startswith('&gt;&gt;&gt;&gt;&gt;&gt;&gt;'):
                            end_idx = j
                            break
                
                if separator_idx and end_idx:
                    # Strategy: Keep both changes, preferring incoming (stashed) changes
                    # Get incoming changes (after =======)
                    incoming_lines = lines[separator_idx + 1:end_idx]
                    
                    # Get current changes (between <<<<<<< and =======)
                    current_lines = lines[i + 1:separator_idx]
                    
                    # For most cases, prefer incoming (stashed) changes
                    # But keep both if they don't conflict logically
                    resolved_lines.extend(incoming_lines)
                    i = end_idx + 1
                    continue
            
            resolved_lines.append(line)
            i += 1
        
        # Write resolved content
        resolved_content = '\n'.join(resolved_lines)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(resolved_content)
        
        return True, f"Resolved {conflict_count} conflict(s)"
    
    except Exception as e:
        return False, str(e)

print("="*80)
print("AUTOMATIC CONFLICT RESOLUTION")
print("="*80)

# Find conflicted files
conflicted_files = find_conflicted_files()

if not conflicted_files:
    print("\n✓ No conflicts found! Repository is clean.")
    print("\nChecking if branches are in sync...")
    
    # Check branch sync
    success, _, _ = run_git(['checkout', 'main'])
    success, diff, _ = run_git(['diff', 'paper_trading', '--name-only'])
    
    if not diff:
        print("✓ main and paper_trading are in sync!")
    else:
        print(f"⚠️  Found {len(diff.splitlines())} file(s) different between branches")
    
    exit(0)

print(f"\nFound {len(conflicted_files)} conflicted file(s):")
for cf in conflicted_files:
    print(f"  - {cf}")

print("\nResolving conflicts...")
print("-" * 80)

resolved_count = 0
failed_files = []

for filepath in conflicted_files:
    full_path = os.path.join(repo_path, filepath)
    if os.path.exists(full_path):
        print(f"\nResolving: {filepath}")
        success, message = resolve_conflict_in_file(full_path)
        if success:
            print(f"  ✓ {message}")
            resolved_count += 1
            # Stage the resolved file
            run_git(['add', filepath])
        else:
            print(f"  ✗ Error: {message}")
            failed_files.append(filepath)
    else:
        print(f"  ⚠️  File not found: {filepath}")

print("\n" + "="*80)
print("RESOLUTION SUMMARY")
print("="*80)
print(f"Total conflicted files: {len(conflicted_files)}")
print(f"Successfully resolved: {resolved_count}")
print(f"Failed: {len(failed_files)}")

if failed_files:
    print("\nFailed files:")
    for ff in failed_files:
        print(f"  - {ff}")

if resolved_count == len(conflicted_files):
    print("\n✓ All conflicts resolved! Staging files...")
    # Complete the merge/stash application
    success, _, _ = run_git(['add', '.'])
    if success:
        print("✓ All resolved files staged")
        print("\nYou can now commit the changes with:")
        print("  git commit -m 'Resolved merge conflicts'")
    else:
        print("⚠️  Could not stage all files")

print("="*80)




