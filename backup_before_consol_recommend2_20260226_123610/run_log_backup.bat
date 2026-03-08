@echo off
REM Log Backup Agent - Windows Task Scheduler Runner
REM Runs the Log Backup Agent every 15 minutes

REM Navigate to Trade-Alerts directory
cd /d "C:\Users\user\projects\personal\Trade-Alerts"

REM Run the backup agent
python agents/log_backup_agent.py

REM Exit with status code
exit /b %ERRORLEVEL%
