#!/usr/bin/env python3
"""
Check uncommitted changes in main, compare with paper_trading, and verify market watch
"""
import subprocess
import os

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

output_file = open("uncommitted_and_marketwatch_check.txt", "w", encoding="utf-8")

def log(msg):
    print(msg)
    output_file.write(msg + "\n")
    output_file.flush()

log("="*80)
log("UNCOMMITTED CHANGES AND MARKET WATCH VERIFICATION")
log("="*80)
log("")

# Switch to main branch
log("[1] Switching to main branch...")
success, _, _ = run_git(['checkout', 'main'])
if success:
    log("✓ Switched to main branch")
else:
    log("✗ Failed to switch to main")
    output_file.close()
    exit(1)

# Check uncommitted changes
log("\n[2] Checking for uncommitted changes in main...")
success, status, _ = run_git(['status', '--short'])
if success:
    if status:
        log("UNCOMMITTED CHANGES FOUND IN MAIN:")
        log(status)
        files = [line.split()[1] for line in status.splitlines() if len(line.split()) > 1]
        log(f"\nTotal uncommitted files: {len(files)}")
        for f in files:
            log(f"  - {f}")
    else:
        log("No uncommitted changes in main branch")
else:
    log("Could not check status")

# Check unstaged changes
log("\n[3] Checking unstaged changes...")
success, unstaged, _ = run_git(['diff', '--name-only'])
if success and unstaged:
    log("UNSTAGED FILES:")
    log(unstaged)
    unstaged_files = unstaged.splitlines()
    log(f"Total unstaged files: {len(unstaged_files)}")
else:
    log("No unstaged changes")
    unstaged_files = []

# Check staged changes
log("\n[4] Checking staged changes...")
success, staged, _ = run_git(['diff', '--cached', '--name-only'])
if success and staged:
    log("STAGED FILES:")
    log(staged)
    staged_files = staged.splitlines()
    log(f"Total staged files: {len(staged_files)}")
else:
    log("No staged changes")
    staged_files = []

# Check stash
log("\n[5] Checking stash...")
success, stash_list, _ = run_git(['stash', 'list'])
if success and stash_list:
    log("STASHES FOUND:")
    log(stash_list)
    stash_count = len(stash_list.splitlines())
    log(f"Total stashes: {stash_count}")
    
    # Show stash contents
    for i in range(stash_count):
        log(f"\nStash {i} contents:")
        success, stash_show, _ = run_git(['stash', 'show', '-p', f'stash@{{{i}}}'])
        if success:
            stash_files = [line for line in stash_show.splitlines() if line.startswith('diff --git')]
            for sf in stash_files[:10]:  # Show first 10 files
                log(f"  {sf}")
else:
    log("No stashes found")

# Check if these files exist in paper_trading
log("\n[6] Checking if uncommitted files exist in paper_trading...")
success, _, _ = run_git(['checkout', 'paper_trading'])
if success:
    log("✓ Switched to paper_trading branch")
    
    all_uncommitted = unstaged_files + staged_files
    if all_uncommitted:
        log(f"\nChecking {len(all_uncommitted)} files in paper_trading:")
        missing_files = []
        present_files = []
        
        for file in all_uncommitted:
            if os.path.exists(os.path.join(repo_path, file)):
                present_files.append(file)
                log(f"  ✓ {file} - EXISTS in paper_trading")
            else:
                missing_files.append(file)
                log(f"  ✗ {file} - MISSING in paper_trading")
        
        if missing_files:
            log(f"\n⚠️  WARNING: {len(missing_files)} file(s) missing in paper_trading:")
            for mf in missing_files:
                log(f"  - {mf}")
        else:
            log(f"\n✓ All {len(all_uncommitted)} files are present in paper_trading")
    else:
        log("No uncommitted files to check")
else:
    log("✗ Failed to switch to paper_trading")

# Check for market watch related files
log("\n[7] Checking for Market Watch functionality...")
market_watch_files = []
market_watch_keywords = ['market', 'watch', 'watchlist', 'playground']

# Search for market watch in file names
import glob
for pattern in ['**/*market*watch*', '**/*watchlist*', '**/playground*']:
    files = glob.glob(os.path.join(repo_path, pattern), recursive=True)
    market_watch_files.extend([os.path.relpath(f, repo_path) for f in files])

# Check specific known files
known_market_watch_files = [
    'playground/script.js',
    'playground/index.html',
    'templates/navbar.html',
    'templates/base.html',
    'E2E_TEST_REPORT.md'
]

for kwf in known_market_watch_files:
    full_path = os.path.join(repo_path, kwf)
    if os.path.exists(full_path):
        market_watch_files.append(kwf)

if market_watch_files:
    log(f"✓ Found {len(market_watch_files)} Market Watch related files:")
    for mwf in set(market_watch_files):
        log(f"  - {mwf}")
        
    # Check if these files are in paper_trading
    log("\nVerifying Market Watch files in paper_trading:")
    missing_mw = []
    for mwf in set(market_watch_files):
        if os.path.exists(os.path.join(repo_path, mwf)):
            log(f"  ✓ {mwf} - EXISTS")
        else:
            missing_mw.append(mwf)
            log(f"  ✗ {mwf} - MISSING")
    
    if missing_mw:
        log(f"\n⚠️  WARNING: {len(missing_mw)} Market Watch file(s) missing!")
    else:
        log("\n✓ All Market Watch files are present in paper_trading")
else:
    log("⚠️  No Market Watch files found (this might be a problem)")

# Compare branches
log("\n[8] Comparing main and paper_trading branches...")
success, diff_files, _ = run_git(['diff', '--name-status', 'main', 'paper_trading'])
if success:
    if diff_files:
        log("FILES DIFFERENT BETWEEN BRANCHES:")
        log(diff_files)
    else:
        log("✓ No differences between main and paper_trading (branches are in sync)")

# Final summary
log("\n" + "="*80)
log("SUMMARY")
log("="*80)
log(f"Uncommitted files in main: {len(unstaged_files + staged_files)}")
log(f"Files in stash: {stash_count if stash_list else 0}")
log(f"Market Watch files found: {len(set(market_watch_files))}")
log("="*80)

output_file.close()
print("\nCheck complete! Results saved to: uncommitted_and_marketwatch_check.txt")




