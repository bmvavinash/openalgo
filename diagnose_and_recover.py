#!/usr/bin/env python3
"""
Git Repository Diagnosis and Recovery Script
Automatically checks for missing changes and recovers them
"""
import subprocess
import os
import sys

# Change to the openalgo directory
repo_path = r"f:\2nd Income\Stock Market\Code\openalgo"
os.chdir(repo_path)

def run_git(cmd_list, capture=True):
    """Run a git command and return the result"""
    try:
        result = subprocess.run(
            ['git'] + cmd_list,
            capture_output=capture,
            text=True,
            cwd=repo_path
        )
        if capture:
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        return result.returncode == 0
    except Exception as e:
        return False, "", str(e)

def main():
    output_file = open("recovery_log.txt", "w", encoding="utf-8")
    
    def log(msg):
        print(msg)
        output_file.write(msg + "\n")
        output_file.flush()
    
    log("="*80)
    log("GIT REPOSITORY DIAGNOSIS AND RECOVERY")
    log("="*80)
    log("")
    
    # 1. Check current branch
    success, current_branch, _ = run_git(['branch', '--show-current'])
    if success:
        log(f"Current branch: {current_branch}")
    else:
        log("ERROR: Could not determine current branch")
        output_file.close()
        return
    
    # 2. Check git status
    log("\n[1] Checking Git status...")
    success, status, _ = run_git(['status', '--short'])
    if success:
        if status:
            log(f"Uncommitted changes found:\n{status}")
        else:
            log("No uncommitted changes")
    else:
        log("Could not check status")
    
    # 3. Check for stashes
    log("\n[2] Checking for stashed changes...")
    success, stash_list, _ = run_git(['stash', 'list'])
    if success and stash_list:
        log(f"Found stashes:\n{stash_list}")
        # Apply the most recent stash
        log("\nApplying most recent stash...")
        if run_git(['stash', 'pop'], capture=False):
            log("✓ Stash applied successfully")
        else:
            log("✗ Failed to apply stash")
    else:
        log("No stashes found")
    
    # 4. Check commits in main not in paper_trading
    log("\n[3] Checking for commits in main not in paper_trading...")
    success, main_commits, _ = run_git(['log', 'paper_trading..main', '--oneline'])
    if success:
        if main_commits:
            commit_count = len(main_commits.splitlines())
            log(f"Found {commit_count} commit(s) in main not in paper_trading:")
            log(main_commits)
            log("\n⚠️  RECOVERY NEEDED: Merging main into paper_trading...")
            
            # Ensure we're on paper_trading branch
            if current_branch != 'paper_trading':
                log(f"Switching to paper_trading branch...")
                if run_git(['checkout', 'paper_trading'], capture=False):
                    log("✓ Switched to paper_trading")
                    current_branch = 'paper_trading'
                else:
                    log("✗ Failed to switch branch")
                    output_file.close()
                    return
            
            # Merge main into paper_trading
            log("Merging main into paper_trading...")
            merge_success = run_git(['merge', 'main', '--no-edit'], capture=False)
            if merge_success:
                log("✓ Successfully merged main into paper_trading")
            else:
                log("✗ Merge failed - may have conflicts")
                # Check if there are conflicts
                success, status, _ = run_git(['status', '--short'])
                if status and ('UU' in status or 'AA' in status or 'DD' in status):
                    log("⚠️  Merge conflicts detected - manual resolution needed")
        else:
            log("✓ paper_trading is up to date with main")
    else:
        log("Could not check commits")
    
    # 5. Check commits in paper_trading not in main
    log("\n[4] Checking for commits in paper_trading not in main...")
    success, paper_commits, _ = run_git(['log', 'main..paper_trading', '--oneline'])
    if success:
        if paper_commits:
            log(f"Found {len(paper_commits.splitlines())} commit(s) in paper_trading not in main:")
            log(paper_commits)
        else:
            log("No unique commits in paper_trading")
    
    # 6. Final status check
    log("\n[5] Final status check...")
    success, final_status, _ = run_git(['status'])
    if success:
        log("Current Git status:")
        log(final_status)
    
    log("\n" + "="*80)
    log("DIAGNOSIS AND RECOVERY COMPLETE")
    log("="*80)
    output_file.close()

if __name__ == "__main__":
    main()




