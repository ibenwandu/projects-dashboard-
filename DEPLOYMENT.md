# Emy Deployment Guide

## Overview

Emy is a fully autonomous AI agent that can run 24/7, managing:
- Trading system monitoring (Phase 1)
- Job search automation (Phase 2)
- Knowledge management (Phase 3)
- Approval gates & skill self-improvement (Phase 4)
- Conversational CLI interface (Phase 5)

This guide covers deployment to Windows Task Scheduler for persistent background operation.

---

## Prerequisites

- Python 3.8+ installed and in PATH
- Windows 10 or later
- Administrator access
- Anthropic API key with active credits
- Git for version control

---

## Step 1: Verify Installation

```bash
# Test that Python works
python --version

# Test that Emy boots
python emy.py status

# Test all CLI commands
python emy.py skills
python emy.py agents
python emy.py status
```

Expected output: Dashboard showing 40+ completed tasks, skill list, agent list.

---

## Step 2: Configure Environment

### API Key Setup

The `.env` file in `emy/` directory must contain:

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
EMY_DAILY_BUDGET_USD=5.00
EMY_LOG_LEVEL=INFO
```

**Verify configuration:**
```bash
# Check .env file exists
ls -la emy/.env

# Test API connectivity (requires credits)
python emy.py ask "what is your status?"
```

### Optional: OANDA Configuration

To enable real trading monitoring, add to `.env`:

```env
OANDA_ACCESS_TOKEN=your_token
OANDA_ACCOUNT_ID=your_account_id
```

### Optional: Pushover Notifications

To enable alerts on service downtime:

```env
PUSHOVER_USER_KEY=your_user_key
PUSHOVER_API_TOKEN=your_api_token
```

### OANDA Trading Setup

1. **Get Credentials**
   - Log in to https://developer.oanda.com
   - Create API token (Account Settings → API → Create Token)
   - Note your Account ID (Account Summary page)

2. **Configure .env**
   ```env
   OANDA_ACCESS_TOKEN=<token>
   OANDA_ACCOUNT_ID=<account-id>
   OANDA_ENV=practice
   OANDA_MAX_POSITION_SIZE=10000
   OANDA_MAX_DAILY_LOSS_USD=100.0
   OANDA_MAX_CONCURRENT_POSITIONS=5
   ```

3. **Verify Connection**
   ```bash
   python emy.py status
   # Should show live equity and margin metrics
   ```

4. **Monitor Operations**
   ```bash
   tail -f emy/data/emy.log
   sqlite3 emy/data/emy.db "SELECT * FROM oanda_trades LIMIT 5;"
   ```

## Pushover Alert Setup

1. **Get Pushover credentials:**
   - User Key: From https://pushover.net/
   - API Token: Create application at https://pushover.net/apps/build

2. **Configure emy/.env:**
   ```
   PUSHOVER_USER_KEY=<key>
   PUSHOVER_API_TOKEN=<token>
   PUSHOVER_ALERT_ENABLED=true
   ```

3. **Test alerts manually:**
   ```bash
   python -c "from emy.tools.notification_tool import PushoverNotifier; n = PushoverNotifier(); n.send_alert('Test', 'Pushover working', 0)"
   ```

4. **Monitor alerts in Pushover app while trading.**

### Alert Types Explained
- **Normal Priority (0)**: Trade execution and rejection alerts
- **High Priority (1)**: Daily loss warning at 75%
- **Emergency Priority (2)**: Daily loss limit hit at 100% (retries for 60 minutes)

---

## Step 3: Register Windows Task Scheduler

### Automated Setup (Recommended)

```powershell
# Run as Administrator
powershell -ExecutionPolicy Bypass -File setup-task-scheduler.ps1
```

This will:
1. Create a scheduled task named "Emy Chief of Staff"
2. Trigger at system startup
3. Run `python emy.py run` in the background
4. Report status

### Manual Setup (Alternative)

1. Open Task Scheduler (search "Task Scheduler" in Windows)
2. Click "Create Basic Task..."
3. Name: "Emy Chief of Staff"
4. Trigger: "At system startup"
5. Action: "Start a program"
   - Program: `python`
   - Arguments: `emy.py run`
   - Start in: `C:\Users\user\projects\personal\.worktrees\emy`
6. Finish

### Verify Registration

```powershell
# Check task status
Get-ScheduledTask -TaskName "Emy Chief of Staff"

# View last run details
Get-ScheduledTaskInfo -TaskName "Emy Chief of Staff"
```

---

## Step 4: Monitor Execution

### View Logs

```bash
# Real-time main loop execution
tail -f emy/data/emy.log

# Database task history
sqlite3 emy/data/emy.db "SELECT id, domain, task_type, status FROM emy_tasks ORDER BY id DESC LIMIT 20;"
```

### Check Budget Usage

```bash
# Current day spending
python emy.py status

# View API spend detail
sqlite3 emy/data/emy.db "SELECT model, COUNT(*) as calls, SUM(cost_usd) as total FROM api_spend WHERE DATE(timestamp) = DATE('now') GROUP BY model;"
```

### View Scheduled Job Execution

```bash
# List executed jobs (last 10)
sqlite3 emy/data/emy.db "SELECT job_name, scheduled_time, status FROM schedule_runs ORDER BY id DESC LIMIT 10;"
```

---

## Step 5: Emergency Controls

### Disable Emy Temporarily

Create `.emy_disabled` file in working directory:

```bash
touch .emy_disabled
```

Emy will detect this on next tick and halt all scheduled tasks. Remove to re-enable:

```bash
rm .emy_disabled
```

### Stop Task Immediately

```powershell
# Stop the running task
Stop-ScheduledTask -TaskName "Emy Chief of Staff"

# Restart the task
Start-ScheduledTask -TaskName "Emy Chief of Staff"
```

### Remove from Task Scheduler

```powershell
# Run as Administrator
powershell -ExecutionPolicy Bypass -File setup-task-scheduler.ps1 -Uninstall
```

---

## Running Modes

### Mode 1: Background Service (Production)

```bash
# System starts Emy automatically on boot
# Runs in background continuously
# Logs to emy/data/emy.log
# Executes 6 scheduled jobs autonomously
```

### Mode 2: Interactive CLI (Manual)

```bash
# Single-shot queries via conversational interface
python emy.py ask "run job search for analyst track"
python emy.py ask "check render service status"
python emy.py status
python emy.py skills
python emy.py agents
```

### Mode 3: Development (Testing)

```bash
# Start main loop with console output
python emy.py run

# Press Ctrl+C to stop
# Database persists all state
```

---

## Scheduled Jobs (Running 24/7)

| Job | Frequency | Purpose |
|-----|-----------|---------|
| trading_health_check | Every 15 min | Monitor OANDA account & Render health |
| job_search_daily | Daily (9 AM EST) | Search 4 platforms for jobs |
| resume_tailor_approved | Daily (10 AM EST) | Tailor resumes for high-scoring jobs |
| obsidian_dashboard_update | Daily (8 PM EST) | Update Obsidian knowledge base |
| memory_persist | Every 4 hours | Save findings to MEMORY.md |
| skill_improvement_sweep | Daily (11 PM EST) | Auto-improve underperforming skills |

---

## Troubleshooting

### Task Not Starting

**Check logs:**
```bash
# Task Scheduler event log
eventvwr.msc  # Search "Emy Chief of Staff"

# Emy main log
cat emy/data/emy.log | tail -50
```

**Common causes:**
- Working directory path incorrect (edit Task Scheduler task)
- Python not in PATH (add to Path environment variable)
- .env file missing or API key wrong
- Database locked by another process

### Budget Exceeded

Emy automatically disables when daily budget is exceeded:

```bash
# Check current spend
python emy.py status

# View budget tracking
sqlite3 emy/data/emy.db "SELECT SUM(cost_usd) FROM api_spend WHERE DATE(timestamp) = DATE('now');"

# Increase daily budget in .env
echo "EMY_DAILY_BUDGET_USD=10.00" >> emy/.env
```

### API Errors

**Credit balance too low:**
- Verify API key in .env
- Add credits to Anthropic account (https://console.anthropic.com/account/billing/overview)
- Wait 1-2 minutes for credits to activate

**Invalid API key:**
- Get key from Emy-Anthropic-Key.txt in personal folder
- Update emy/.env with correct key
- Restart Task Scheduler task

---

## Performance Tuning

### Optimize API Costs

1. Reduce daily budget: `EMY_DAILY_BUDGET_USD=2.00`
2. Increase skill improvement interval (currently daily, could be weekly)
3. Disable low-priority jobs as needed

### Monitor Resource Usage

```bash
# Check database size
du -h emy/data/emy.db

# Archive old logs if needed
mv emy/data/emy.log emy/data/emy.log.archive.$(date +%Y%m%d)
```

---

## Disaster Recovery

### Backup

```bash
# Backup database (contains all task history)
cp emy/data/emy.db emy/data/emy.db.backup

# Backup configuration
cp emy/.env emy/.env.backup
```

### Restore

```bash
# Restore from backup
cp emy/data/emy.db.backup emy/data/emy.db
cp emy/.env.backup emy/.env

# Restart task
Stop-ScheduledTask -TaskName "Emy Chief of Staff"
Start-ScheduledTask -TaskName "Emy Chief of Staff"
```

---

## Support

**View system status:**
```bash
python emy.py status
```

**Check agent availability:**
```bash
python emy.py agents
```

**Review executed skills:**
```bash
python emy.py skills
```

**View recent tasks:**
```bash
sqlite3 emy/data/emy.db "SELECT * FROM emy_tasks ORDER BY id DESC LIMIT 5;"
```

**For issues**, check:
1. emy/data/emy.log for error messages
2. Database for task failures: `SELECT * FROM emy_tasks WHERE status='failed' ORDER BY id DESC LIMIT 5;`
3. API spend for budget issues
4. Windows Task Scheduler event log

---

## Maintenance

### Weekly

- Review completed tasks: `sqlite3 emy/data/emy.db "SELECT COUNT(*) FROM emy_tasks WHERE completed_at > DATE('now', '-7 days');"`
- Check API spend trends
- Monitor budget utilization

### Monthly

- Backup database to external drive
- Review skill success rates
- Update MEMORY.md with new learnings
- Commit changes to git

### As Needed

- Improve underperforming skills (automatic, but monitor)
- Add new job platforms to search (update JobSearchAgent)
- Extend task router with new domains (add agents)
- Adjust scheduled job cadences

---

## Summary

Emy is now production-ready:

✅ All 5 phases implemented
✅ 6 scheduled jobs running autonomously
✅ Windows Task Scheduler integration available
✅ API key configured with credits
✅ Emergency kill-switch in place
✅ Database persistence of all state
✅ Comprehensive logging and monitoring

**Next step:** Run `setup-task-scheduler.ps1` as Administrator to enable 24/7 operation.
