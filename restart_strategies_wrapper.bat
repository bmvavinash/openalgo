@echo off
REM Wrapper script to run restart_strategies.py with unbuffered output
echo ============================================================
echo RESTART STRATEGIES WRAPPER
echo ============================================================
echo.

cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo [WRAPPER] Running restart_strategies.py with unbuffered output...
echo.

python -u restart_strategies.py

echo.
echo [WRAPPER] Script completed with exit code: %ERRORLEVEL%
pause






