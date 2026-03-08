@echo off
REM Run the job-alert workflow (fetch, score, report). Schedule this at 7 AM and 7 PM EST.
REM Use full paths so the log is always in the project folder (Task Scheduler may not set "Start in").
set "PROJECT=%~dp0"
set "LOG=%PROJECT%output\workflow_run.log"
if not exist "%PROJECT%output" mkdir "%PROJECT%output"
echo [%date% %time%] Batch started >> "%LOG%"
cd /d "%PROJECT%"
REM Use full path to script. Prefer 'python'; if not in PATH (common when task runs), try 'py'.
where python >nul 2>&1 && (python "%PROJECT%run_workflow.py" --phase all >> "%LOG%" 2>&1) || (py "%PROJECT%run_workflow.py" --phase all >> "%LOG%" 2>&1)
set EXIT_CODE=%errorlevel%
echo [%date% %time%] Batch finished, exit code: %EXIT_CODE% >> "%LOG%"
exit /b %EXIT_CODE%
