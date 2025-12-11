@echo off
cd /d "f:\2nd Income\Stock Market\Code\openalgo"
echo ===== GIT STATUS ===== > git_info.txt
git status >> git_info.txt 2>&1
echo. >> git_info.txt
echo ===== CURRENT BRANCH ===== >> git_info.txt
git branch --show-current >> git_info.txt 2>&1
echo. >> git_info.txt
echo ===== ALL BRANCHES ===== >> git_info.txt
git branch -a >> git_info.txt 2>&1
echo. >> git_info.txt
echo ===== STASH LIST ===== >> git_info.txt
git stash list >> git_info.txt 2>&1
echo. >> git_info.txt
echo ===== COMMITS IN PAPER_TRADING NOT IN MAIN ===== >> git_info.txt
git log main..paper_trading --oneline >> git_info.txt 2>&1
echo. >> git_info.txt
echo ===== COMMITS IN MAIN NOT IN PAPER_TRADING ===== >> git_info.txt
git log paper_trading..main --oneline >> git_info.txt 2>&1
echo. >> git_info.txt
echo ===== RECENT REFLOG ===== >> git_info.txt
git reflog --all -30 >> git_info.txt 2>&1
echo. >> git_info.txt
echo ===== UNCOMMITTED CHANGES ===== >> git_info.txt
git diff --name-only >> git_info.txt 2>&1
echo. >> git_info.txt
echo ===== STAGED CHANGES ===== >> git_info.txt
git diff --cached --name-only >> git_info.txt 2>&1
type git_info.txt




