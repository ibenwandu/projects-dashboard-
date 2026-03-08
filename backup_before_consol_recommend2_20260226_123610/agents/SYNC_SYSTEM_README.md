# Agent Sync System - Complete Documentation

## Overview

The **Agent Sync System** automatically pulls agent execution results from Render and makes them available locally without requiring manual Render checks.

**Key Features:**
- ✅ Downloads agent database from Render (`/var/data/agent_system.db`)
- ✅ Pulls logs from Render (UI, Scalp-Engine, OANDA)
- ✅ Extracts agent cycle results and statuses
- ✅ Updates `agent-coordination.md` with verification
- ✅ Handles dated log files (fixes filename mismatch)
- ✅ Can be run manually or automatically

---

## How It Works

### Automated Flow (Recommended)

```
17:30 EST: Agents run on Render
    ↓
Orchestrator completes and updates database
    ↓
Trade-Alerts main.py automatically calls sync
    ↓
Results synced to local machine
    ↓
agent-coordination.md updated with status
```

### Manual Sync

Run anytime to pull the latest results:

```bash
python agents/sync_render_results.py
```

Or use the helper script:

```bash
bash agents/run-sync.sh
```

---

## The Sync Process

### Step 1: Download Database from Render

The sync script attempts to download `/var/data/agent_system.db` from Render using:
1. **HTTP endpoint** (if configured)
2. **Local copy** (if already exists locally)

**If both fail:**
```bash
# Manual method: Download from Render and place at
~/Trade-Alerts/data/agent_system.db
```

### Step 2: Download Logs from Render

Downloads the three log streams from the Render API:

```
GET /logs/engine   → scalp_engine_YYYYMMDD.log
GET /logs/ui       → scalp_ui_YYYYMMDD.log
GET /logs/oanda    → oanda_YYYYMMDD.log
```

These are saved to:
```
agents/shared-docs/logs/
├── scalp_engine.log (symlink/copy)
├── oanda_trades.log (symlink/copy)
└── ui_activity.log (symlink/copy)
```

### Step 3: Query Database

Extracts the latest cycle results:

```sql
SELECT cycle_number FROM approval_history WHERE cycle_number = MAX(...)
SELECT * FROM agent_analyses WHERE cycle_number = ?
SELECT * FROM agent_recommendations WHERE cycle_number = ?
SELECT * FROM agent_implementations WHERE cycle_number = ?
SELECT * FROM approval_history WHERE cycle_number = ?
```

### Step 4: Update Coordination Log

Appends a new session entry to `agents/shared-docs/agent-coordination.md`:

```markdown
## Session 5 - 2026-02-17 22:35:00 UTC

### Analyst Phase
- **Status:** ✅ COMPLETED
- **Timestamp:** 2026-02-17T22:32:15Z
- **Report:** `analyst/analysis-reports/report-cycle5.md`

### Forex Expert Phase
- **Status:** ✅ COMPLETED
- **Timestamp:** 2026-02-17T22:33:45Z
- **Recommendations:** `forex-expert/recommendations/recommendations-cycle5.md`

### Coding Expert Phase
- **Status:** ✅ COMPLETED
- **Timestamp:** 2026-02-17T22:34:20Z
- **Implementation:** `coding-expert/implementations/implementation-cycle5.md`

### Orchestrator Phase
- **Status:** ✅ APPROVED
- **Timestamp:** 2026-02-17T22:35:00Z
- **Decision:** APPROVED

### Sync Status
- **Last Synced:** 2026-02-17T22:35:10Z
- **Sync Source:** Render `/var/data/agent_system.db`
- **Logs Available:** 3 files
```

---

## Log File Handling

### The Problem

Actual log filenames (created by Render):
- `scalp_engine_20260217.log`
- `scalp_ui_20260217.log`
- `oanda_20260217.log`

Expected by analyst agent:
- `scalp_engine.log`
- `ui_activity.log`
- `oanda_trades.log`

### The Solution

The `get_log_files()` function in `agents/shared/log_parser.py` now:
1. Searches for both exact and dated filenames
2. Returns the most recent dated version if found
3. Falls back to exact names if available
4. Ensures analyst agent always finds the right logs

**Updated patterns:**
```python
{
    "scalp_engine": ["scalp_engine.log", "scalp_engine_*.log"],
    "ui_activity": ["ui_activity.log", "scalp_ui_*.log"],
    "oanda_trades": ["oanda_trades.log", "oanda_*.log"]
}
```

---

## Usage Guide

### Option 1: Automatic (Recommended)

No action needed! After agents run on Render:
1. `main.py` automatically calls the sync
2. Results synced to `agents/shared-docs/`
3. Check `agent-coordination.md` for status

### Option 2: Manual Sync

Run anytime to get the latest results:

```bash
# From project root
python agents/sync_render_results.py
```

**Output:**
```
============================================================
🔄 AGENT SYNC SYSTEM - Pulling Results from Render
============================================================
📥 Attempting to download agent database from Render...
   ℹ️  Using existing local database
📥 Attempting to download logs from Render...
   Downloading engine logs from https://...
   ✅ Downloaded engine: 156 KB
   ...
📊 Extracting cycle results...
   Cycle 5:
   - Analyst: COMPLETED
   - Expert: COMPLETED
   - Coder: COMPLETED
   - Orchestrator: APPROVED
✅ Updated coordination log: agents/shared-docs/agent-coordination.md

============================================================
✅ SYNC COMPLETE
============================================================

📂 Results location: agents/shared-docs/
📋 Coordination log: agents/shared-docs/agent-coordination.md
📥 Logs directory: agents/shared-docs/logs/
```

### Option 3: Verify Status Only

Check if agents have run without downloading:

```bash
python agents/sync_render_results.py --verify
```

**Output:**
```
✅ Verification mode
Latest cycle: 5
  Analyst: COMPLETED
  Expert: COMPLETED
  Coder: COMPLETED
  Orchestrator: APPROVED
```

### Option 4: Use Local Database

If you've manually downloaded the database from Render:

```bash
python agents/sync_render_results.py --local-db /path/to/agent_system.db
```

---

## Render API Configuration

The sync script expects these Render services to be running:

### Trade-Alerts Service

**Endpoints needed for log collection:**
- `GET /logs` - List available log files
- `GET /logs/engine` - Get Scalp-Engine logs
- `GET /logs/oanda` - Get OANDA logs
- `GET /logs/ui` - Get UI logs

These endpoints already exist in `config_api_server.py`.

### Database Download

For automated database sync, consider adding to Trade-Alerts or Scalp-Engine:

```python
@app.route('/download-db', methods=['GET'])
def download_db():
    """Download agent system database."""
    db_path = '/var/data/agent_system.db'
    if os.path.exists(db_path):
        return send_file(db_path, as_attachment=True, download_name='agent_system.db')
    return jsonify({'error': 'Database not found'}), 404
```

---

## File Structure

```
agents/
├── sync_render_results.py          # Main sync script ← YOU ARE HERE
├── run-sync.sh                     # Helper script for easy execution
├── SYNC_SYSTEM_README.md           # This file
├── shared-docs/
│   ├── agent-coordination.md       # Auto-updated coordination log
│   ├── logs/                       # Log files pulled from Render
│   │   ├── scalp_engine.log        # Most recent engine logs
│   │   ├── oanda_trades.log        # Most recent OANDA logs
│   │   └── ui_activity.log         # Most recent UI logs
│   └── context/
│       ├── system-state.json
│       └── current-strategy.md
├── analyst/
├── forex-expert/
├── coding-expert/
└── shared/
    └── log_parser.py               # UPDATED: Handles dated log files
```

---

## Expected Workflow Timeline

### Daily Agent Execution (Render Side)

```
17:30 EST (22:30 UTC) - Agent execution starts
  │
  ├─ 22:32 UTC - Analyst completes
  ├─ 22:33 UTC - Forex Expert completes
  ├─ 22:34 UTC - Coding Expert completes (if code changes needed)
  ├─ 22:35 UTC - Orchestrator approval completes
  │
  └─ Database updated with all results
```

### Local Side

```
17:30 EST+
  │
  ├─ (Automatic) main.py syncs results
  │   └─ agent-coordination.md updated
  │
  ├─ (Optional) Manual: python agents/sync_render_results.py
  │   └─ Pulls fresh results
  │
  └─ Check results anytime:
     agents/shared-docs/agent-coordination.md
```

---

## Troubleshooting

### Sync Fails: "Database not found"

**Issue:** Cannot download database from Render

**Solutions:**
1. **Manual download:**
   ```bash
   # On Render machine or via SSH
   cp /var/data/agent_system.db ~/Downloads/
   # Then copy to local Trade-Alerts/data/agent_system.db
   ```

2. **Add database endpoint to Render service** (see configuration section above)

3. **Check if agents actually ran:**
   ```bash
   python agents/sync_render_results.py --verify
   ```

### Logs Not Found

**Issue:** "Empty response" or "No log file found"

**Possible causes:**
- Logs haven't been written yet (agents just started)
- Render logs are in `/var/data/logs/` but API not returning them
- Wrong log file date (check Render directly)

**Solution:**
```bash
# Check what logs are available on Render
curl https://trade-alerts-api.onrender.com/logs

# Get specific logs manually
curl https://trade-alerts-api.onrender.com/logs/engine?lines=100
```

### Coordination.md Not Updating

**Issue:** File exists but no new sessions added

**Check:**
1. Did agents actually complete?
   ```bash
   python agents/sync_render_results.py --verify
   ```

2. Does database have data?
   ```bash
   sqlite3 data/agent_system.db "SELECT COUNT(*) FROM approval_history;"
   ```

3. Check sync output for errors

### Log File Mismatches

**Issue:** Analyst agent can't find logs

**Root cause:** Dated filenames don't match expected names

**Solution:** ALREADY FIXED in this implementation!

The updated `get_log_files()` function now:
- Finds both `scalp_engine.log` and `scalp_engine_*.log`
- Returns the most recent version
- Automatically handles dated files

---

## Next Steps

### 1. Verify Sync Works

```bash
# Test the sync system
python agents/sync_render_results.py --verify
```

### 2. Set Render API URL (if different)

If your Render service is at a different URL:

```bash
python agents/sync_render_results.py --api-url https://your-render-service.onrender.com
```

### 3. Monitor First Few Cycles

After agents run (17:30 EST):
1. Check `agents/shared-docs/agent-coordination.md`
2. Verify session entries appear with correct status
3. Check that logs are downloaded successfully

### 4. Optional: Automate Further

Could add to cron/scheduler:
```bash
# Every day at 18:00 EST (after agents finish at 17:35 EST)
0 18 * * * cd ~/Trade-Alerts && python agents/sync_render_results.py
```

---

## Summary

| Component | Status | Purpose |
|-----------|--------|---------|
| `sync_render_results.py` | ✅ NEW | Downloads DB and logs from Render |
| `log_parser.py` | ✅ UPDATED | Handles dated log filenames |
| `main.py` | ✅ UPDATED | Calls sync after agents complete |
| `agent-coordination.md` | ✅ NEW | Auto-populated with cycle results |
| `run-sync.sh` | ✅ NEW | Helper script for manual sync |
| Log file handling | ✅ FIXED | Properly finds dated logs |

The system is ready to use! No manual Render checks needed tomorrow. 🎉
