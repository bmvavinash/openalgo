# Start Continuous Monitoring Script
# Runs monitoring in background and logs to file

$logFile = "log\monitoring_$(Get-Date -Format 'yyyyMMdd').log"
$scriptDir = "F:\2nd Income\Stock Market\Code\openalgo"

Write-Host "Starting Continuous Monitoring..."
Write-Host "Log file: $logFile"
Write-Host "Press Ctrl+C to stop"

cd $scriptDir

if (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
}

# Run monitoring (check every 5 minutes = 300 seconds)
python continuous_monitor.py --interval 300 2>&1 | Tee-Object -FilePath $logFile




