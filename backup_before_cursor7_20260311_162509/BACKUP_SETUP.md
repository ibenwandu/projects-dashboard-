# Log Backup Agent - Windows Task Scheduler Setup

## Overview

The Log Backup Agent backs up logs every 15 minutes to your local `logs_archive/` directory.

**Why local backups?**
- You have direct access for troubleshooting
- Future agents can analyze logs without context limits
- Independent of Render

---

## Setup Instructions

### Step 1: Create the Task in Windows Task Scheduler

1. **Open Task Scheduler**
   - Press `Win + R`, type `taskschd.msc`, press Enter
   - Or: Control Panel → Administrative Tools → Task Scheduler

2. **Create a new task**
   - Right-click on "Task Scheduler Library" → Select "Create Task..."
   - Name: `Trade-Alerts Log Backup`
   - Check: ✓ "Run with highest privileges" (optional but recommended)

3. **Set the Trigger (When to Run)**
   - Click "Triggers" tab → New...
   - Begin the task: `On a schedule`
   - Settings:
     - Recurrence: `Repeat every` **15 minutes**
     - Duration: For a period of **Indefinitely**
   - OK

4. **Set the Action (What to Run)**
   - Click "Actions" tab → New...
   - Action: `Start a program`
   - Program/script: `python`
   - Add arguments: `agents/log_backup_agent.py`
   - Start in: `C:\Users\user\projects\personal\Trade-Alerts`
   - OK

5. **Configure Additional Settings (Optional)**
   - Click "Settings" tab
   - ✓ "Run the task as soon as possible after a scheduled start is missed"
   - ✓ "Stop the task if it runs longer than" → set to **5 minutes** (safe default)
   - OK

6. **Save the Task**
   - Click OK to create the task
   - You may be prompted for your Windows password

---

## Verify It's Working

**Manual Test (First Time)**

```bash
cd C:\Users\user\projects\personal\Trade-Alerts
python agents/log_backup_agent.py
```

You should see:
```
📁 Archive directory: C:\Users\user\projects\personal\Trade-Alerts\logs_archive
🔄 Starting log backup cycle...
✅ Backed up: logs/trade_alerts_20260220.log (39KB)
...
📊 BACKUP SUMMARY
  Files backed up: 4
  Files skipped: 0
📝 Session log saved: logs_archive/sessions/20260220/backup_20260220_193501.json
✅ Log backup cycle completed successfully
```

**Check Scheduled Runs**

1. Open Task Scheduler
2. Navigate to: Task Scheduler Library
3. Search for: `Trade-Alerts Log Backup`
4. Right-click → View → History
5. You should see successful runs every 15 minutes

---

## Backup Archive Structure

After running, you'll have:

```
logs_archive/
├── logs/                            # Backed up logs
│   ├── 20260220_193501_trade_alerts_20260220.log
│   ├── 20260220_193501_scalp_engine.log
│   └── ...
└── sessions/                        # Session logs from backup runs
    └── 20260220/
        ├── backup_20260220_193501.json
        ├── backup_20260220_194001.json
        └── ...
```

---

## Troubleshooting

### Task doesn't run
1. Check Windows Task Scheduler → View History
2. Look for error messages
3. Verify Python is in PATH: `python --version` in Command Prompt

### Logs not backing up
1. Check that source directories exist:
   - `C:\Users\user\projects\personal\Trade-Alerts\logs\`
   - `C:\Users\user\projects\personal\Trade-Alerts\Scalp-Engine\logs\`

2. Verify log files exist in those directories

3. Run manually to see detailed error:
   ```bash
   cd C:\Users\user\projects\personal\Trade-Alerts
   python agents/log_backup_agent.py
   ```

### Task running but creating empty session logs
- Session logs show what was backed up
- If logs directory is empty, nothing gets backed up (normal)
- Check that Trading-Alerts and Scalp-Engine are actually running and creating logs

---

## Enable/Disable the Backup

**To disable:**
1. Task Scheduler → Find "Trade-Alerts Log Backup"
2. Right-click → Disable

**To re-enable:**
1. Right-click → Enable

**To delete:**
1. Right-click → Delete → Confirm

---

## Alternative: Using Batch Script

If you prefer, use the provided `run_log_backup.bat` script:

1. **Create the task** (same steps above, but in Step 4):
   - Program/script: `C:\Users\user\projects\personal\Trade-Alerts\run_log_backup.bat`
   - (Remove the "Add arguments" field)

This is useful if you want to add logging or other batch operations later.

---

## Logs Location

Once the backup starts running, you can access logs here:

```
C:\Users\user\projects\personal\Trade-Alerts\logs_archive\
```

- **For troubleshooting**: Check `logs_archive/logs/`
- **For debugging backup runs**: Check `logs_archive/sessions/YYYYMMDD/`

---

## What Gets Backed Up

Every 15 minutes, these logs are backed up:

| Source | Files |
|--------|-------|
| Trade-Alerts | `logs/trade_alerts_*.log` |
| Scalp-Engine | `Scalp-Engine/logs/scalp_engine*.log` |
| Scalp-Engine UI | `Scalp-Engine/logs/ui_activity*.log` |
| OANDA | `Scalp-Engine/logs/oanda*.log` |

---

## Next Steps

Once the backup task is running:
1. ✅ Logs automatically back up every 15 minutes
2. ✅ Local `logs_archive/` directory gets populated
3. ✅ I can search logs directly for troubleshooting (no copying/pasting needed)
4. ✅ Future agents can access backed-up logs

---

## Questions?

If the task isn't running, share:
1. Task Scheduler → View History output
2. Manually run output: `python agents/log_backup_agent.py`

