import subprocess
import sys
import os

os.chdir(r"f:\2nd Income\Stock Market\Code\openalgo")

commands = [
    ("git status", "status.txt"),
    ("git branch -a", "branches.txt"),
    ("git branch --show-current", "current_branch.txt"),
    ("git stash list", "stash.txt"),
    ("git log --oneline --all --graph -20", "log.txt"),
    ("git log main..paper_trading --oneline", "main_to_paper.txt"),
    ("git log paper_trading..main --oneline", "paper_to_main.txt"),
    ("git reflog --all -30", "reflog.txt"),
]

for cmd, filename in commands:
    try:
        result = subprocess.run(cmd.split(), capture_output=True, text=True, cwd=r"f:\2nd Income\Stock Market\Code\openalgo")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Command: {cmd}\n")
            f.write(f"Exit code: {result.returncode}\n")
            f.write("="*80 + "\n")
            f.write("STDOUT:\n")
            f.write(result.stdout)
            f.write("\n" + "="*80 + "\n")
            f.write("STDERR:\n")
            f.write(result.stderr)
            f.write("\n")
        print(f"✓ {cmd} -> {filename}")
    except Exception as e:
        print(f"✗ {cmd} -> Error: {e}")

print("\nAll Git information saved to files!")




