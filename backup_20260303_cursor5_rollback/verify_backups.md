# Manual Backup Verification Guide

Quick reference for checking if the backup system is working.

## Method 1: Quick Visual Check (File Explorer)

1. **Open File Explorer**
2. **Navigate to**: `C:\Users\user\projects\personal\Trade-Alerts\logs_archive\Trade-Alerts\`
3. **What to look for**:
   - Files should have timestamps in the format: `YYYYMMDD_HHMMSS_trade_alerts_YYYYMMDD.log`
   - Files should be created every 15 minutes
   - Latest file should be from within the last 15-30 minutes
   - File sizes should be around 15-25 KB each

**Example**: You should see files like:
- `20260223_164807_trade_alerts_20260222.log`
- `20260223_170307_trade_alerts_20260222.log`
- `20260223_171807_trade_alerts_20260222.log`

## Method 2: Check Latest Backup Time (PowerShell)

```powershell
# Navigate to the archive directory
cd C:\Users\user\projects\personal\Trade-Alerts\logs_archive\Trade-Alerts

# Get the most recent file
$latest = Get-ChildItem -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1

Write-Host "Latest backup file: $($latest.Name)"
Write-Host "Created at: $($latest.LastWriteTime)"
Write-Host "Age: $([math]::Round((Get-Date - $latest.LastWriteTime).TotalMinutes, 1)) minutes ago"

# Check if it's recent (should be < 30 minutes)
if ((Get-Date - $latest.LastWriteTime).TotalMinutes -lt 30) {
    Write-Host "Status: OK - Backup is recent" -ForegroundColor Green
} else {
    Write-Host "Status: WARNING - Backup is stale" -ForegroundColor Yellow
}
```

## Method 3: Count Recent Backups (PowerShell)

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts\logs_archive\Trade-Alerts

# Count files created in the last hour
$recent = Get-ChildItem -File | Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-1) }
Write-Host "Files backed up in last hour: $($recent.Count)"
Write-Host "Expected: 4 files (one every 15 minutes)"

if ($recent.Count -ge 3) {
    Write-Host "Status: OK - System is backing up regularly" -ForegroundColor Green
} else {
    Write-Host "Status: WARNING - Fewer backups than expected" -ForegroundColor Yellow
}
```

## Method 4: Check Session Metadata (PowerShell)

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts\logs_archive\sessions\20260223

# Get the latest session log
$latest = Get-ChildItem *.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1

Write-Host "Latest session log: $($latest.Name)"
Write-Host "Created at: $($latest.LastWriteTime)"

# Read and display the contents
$content = Get-Content $latest.FullName | ConvertFrom-Json
Write-Host "`nBackup Statistics:"
Write-Host "  Files backed up: $($content.files_backed_up)"
Write-Host "  Files skipped: $($content.files_skipped)"
Write-Host "  Errors: $($content.errors.Count)"

if ($content.errors.Count -eq 0) {
    Write-Host "  Status: OK - No errors" -ForegroundColor Green
} else {
    Write-Host "  Status: WARNING - Errors present:" -ForegroundColor Yellow
    $content.errors | ForEach-Object { Write-Host "    - $_" }
}
```

## Method 5: Run Statistics Script

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
python get_backup_stats.py
```

This will show:
- Total files and archive size
- Breakdown by directory
- Backup counts by date
- Latest backup timestamp and age
- Status indicators

## Method 6: Manual Backup Test

**Trigger a backup manually** to verify it's working:

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
python agents/log_backup_agent.py
```

**What to expect**:
- Console output showing backup progress
- Summary showing files backed up
- New file created in `logs_archive/Trade-Alerts/`
- New session log in `logs_archive/sessions/20260223/`

## Method 7: Check Task Scheduler Status

```powershell
# Check if the task exists and is enabled
$task = Get-ScheduledTask -TaskName "Trade-Alerts Log Backup" -ErrorAction SilentlyContinue

if ($task) {
    Write-Host "Task Status: $($task.State)"
    Write-Host "Last Run: $($task | Get-ScheduledTaskInfo | Select-Object -ExpandProperty LastRunTime)"
    Write-Host "Next Run: $($task | Get-ScheduledTaskInfo | Select-Object -ExpandProperty NextRunTime)"
    Write-Host "Last Result: $($task | Get-ScheduledTaskInfo | Select-Object -ExpandProperty LastTaskResult)"
    
    if ($task.State -eq "Running") {
        Write-Host "Status: OK - Task is enabled and running" -ForegroundColor Green
    } else {
        Write-Host "Status: WARNING - Task is not running" -ForegroundColor Yellow
    }
} else {
    Write-Host "Status: ERROR - Task not found!" -ForegroundColor Red
}
```

## Method 8: Compare File Counts Over Time

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts\logs_archive\Trade-Alerts

# Count current files
$count1 = (Get-ChildItem -File).Count
Write-Host "Current file count: $count1"

# Wait 15 minutes, then run again
Write-Host "`nWaiting 15 minutes... (or press Ctrl+C to cancel)"
Start-Sleep -Seconds 900

$count2 = (Get-ChildItem -File).Count
Write-Host "New file count: $count2"

if ($count2 -gt $count1) {
    Write-Host "Status: OK - New files were created ($($count2 - $count1) new files)" -ForegroundColor Green
} else {
    Write-Host "Status: WARNING - No new files created" -ForegroundColor Yellow
}
```

## Quick Health Check Checklist

Run these checks to verify everything is working:

- [ ] **File Explorer**: Latest file in `logs_archive/Trade-Alerts/` is < 30 minutes old
- [ ] **PowerShell**: Latest backup time shows recent timestamp
- [ ] **Session Logs**: Latest JSON in `logs_archive/sessions/20260223/` shows `files_backed_up: 1` or more
- [ ] **Task Scheduler**: Task shows "Running" state and recent LastRunTime
- [ ] **Statistics Script**: `python get_backup_stats.py` shows recent backup status
- [ ] **Manual Test**: Running `python agents/log_backup_agent.py` creates new files

## Troubleshooting

**If no new files are appearing**:
1. Check Task Scheduler - is the task enabled?
2. Check Task Scheduler History - are there errors?
3. Run manual backup test - does it work when run manually?
4. Check Python path - is Python accessible from Task Scheduler?

**If files are old (> 30 minutes)**:
1. Task Scheduler may have stopped
2. Check Task Scheduler History for errors
3. Verify the task is set to run every 15 minutes
4. Check if Windows is sleeping/hibernating (tasks won't run)

**If session logs show errors**:
1. API endpoints may be down (expected - documented issue)
2. Trade-Alerts logs should still be backing up
3. Check if `logs/trade_alerts_*.log` files exist locally

