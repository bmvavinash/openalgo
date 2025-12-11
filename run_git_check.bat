@echo off
echo ========================================
echo GIT REPOSITORY STATUS CHECK
echo ========================================
echo.

cd /d "f:\2nd Income\Stock Market\Code\openalgo"

echo [1] Current Branch:
git branch --show-current
echo.

echo [2] Git Status:
git status
echo.

echo [3] Stash List:
git stash list
echo.

echo [4] Commits in MAIN not in PAPER_TRADING:
git log paper_trading..main --oneline
echo.

echo [5] Commits in PAPER_TRADING not in MAIN:
git log main..paper_trading --oneline
echo.

echo [6] Recent Reflog (last 20 operations):
git reflog --all -20
echo.

echo ========================================
echo Check complete! Review the output above.
echo ========================================
pause




