#!/usr/bin/env python3
import subprocess
import os
import sys

# Change to the openalgo directory
os.chdir(r"f:\2nd Income\Stock Market\Code\openalgo")

output_file = "git_analysis.txt"

def run_git_command(cmd, description):
    """Run a git command and return the output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=r"f:\2nd Income\Stock Market\Code\openalgo"
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {str(e)}\n"

# Open file for writing
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("GIT REPOSITORY ANALYSIS\n")
    f.write("="*80 + "\n\n")
    
    # Check if .git exists
    git_dir = os.path.join(r"f:\2nd Income\Stock Market\Code\openalgo", ".git")
    if os.path.exists(git_dir):
        f.write("✓ Git repository found\n\n")
    else:
        f.write("✗ No .git directory found\n\n")
        f.write("Checking parent directory...\n")
        parent_git = os.path.join(r"f:\2nd Income\Stock Market\Code", ".git")
        if os.path.exists(parent_git):
            f.write("✓ Git repository found in parent directory\n\n")
            os.chdir(r"f:\2nd Income\Stock Market\Code")
        else:
            f.write("✗ No Git repository found\n")
            sys.exit(1)
    
    # Get current directory
    f.write(f"Working directory: {os.getcwd()}\n\n")
    
    # Git status
    f.write("="*80 + "\n")
    f.write("1. GIT STATUS\n")
    f.write("="*80 + "\n")
    f.write(run_git_command("git status", "status"))
    f.write("\n")
    
    # Current branch
    f.write("="*80 + "\n")
    f.write("2. CURRENT BRANCH\n")
    f.write("="*80 + "\n")
    f.write(run_git_command("git branch --show-current", "current branch"))
    f.write("\n")
    
    # All branches
    f.write("="*80 + "\n")
    f.write("3. ALL BRANCHES\n")
    f.write("="*80 + "\n")
    f.write(run_git_command("git branch -a", "all branches"))
    f.write("\n")
    
    # Stash list
    f.write("="*80 + "\n")
    f.write("4. STASH LIST\n")
    f.write("="*80 + "\n")
    stash_output = run_git_command("git stash list", "stash list")
    if stash_output.strip() and "Error" not in stash_output:
        f.write(stash_output)
    else:
        f.write("(No stashes found)\n")
    f.write("\n")
    
    # Uncommitted changes
    f.write("="*80 + "\n")
    f.write("5. UNCOMMITTED CHANGES\n")
    f.write("="*80 + "\n")
    f.write(run_git_command("git diff --name-only", "uncommitted"))
    f.write("\n")
    
    # Staged changes
    f.write("="*80 + "\n")
    f.write("6. STAGED CHANGES\n")
    f.write("="*80 + "\n")
    f.write(run_git_command("git diff --cached --name-only", "staged"))
    f.write("\n")
    
    # Commits in paper_trading not in main
    f.write("="*80 + "\n")
    f.write("7. COMMITS IN paper_trading NOT IN main\n")
    f.write("="*80 + "\n")
    f.write(run_git_command("git log main..paper_trading --oneline", "paper_trading commits"))
    f.write("\n")
    
    # Commits in main not in paper_trading
    f.write("="*80 + "\n")
    f.write("8. COMMITS IN main NOT IN paper_trading\n")
    f.write("="*80 + "\n")
    main_commits = run_git_command("git log paper_trading..main --oneline", "main commits")
    f.write(main_commits)
    if main_commits.strip() and "Error" not in main_commits:
        f.write("\n⚠️  WARNING: There are commits in main that are NOT in paper_trading!\n")
        f.write("This means paper_trading branch is missing some changes from main.\n")
    f.write("\n")
    
    # Recent log
    f.write("="*80 + "\n")
    f.write("9. RECENT COMMIT HISTORY (all branches)\n")
    f.write("="*80 + "\n")
    f.write(run_git_command("git log --oneline --all --graph -20", "recent log"))
    f.write("\n")
    
    # Reflog
    f.write("="*80 + "\n")
    f.write("10. REFLOG (recent Git operations)\n")
    f.write("="*80 + "\n")
    f.write(run_git_command("git reflog --all -30", "reflog"))
    f.write("\n")
    
    # Branch relationship
    f.write("="*80 + "\n")
    f.write("11. BRANCH RELATIONSHIP\n")
    f.write("="*80 + "\n")
    merge_base = run_git_command("git merge-base main paper_trading", "merge base")
    f.write(f"Common ancestor: {merge_base.strip()}\n")
    f.write("\n")

print(f"Git analysis complete! Results saved to: {output_file}")
print(f"File location: {os.path.abspath(output_file)}")




