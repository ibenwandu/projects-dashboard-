# Modular Agent System

**Status**: Foundation phase - Building modular architecture for extensibility

## Overview

The agent system is being refactored into a **modular, extensible architecture**. Each agent handles a single responsibility and runs independently on a schedule.

**Why modular?**
- Old 4-phase system (Analyst → Expert → Coder → Orchestrator) never worked reliably
- Removed 12 broken agent files + dependencies
- Starting fresh with proven components (foundation) + simple, focused agents

---

## Current Agents

### 1. Log Backup Agent ✅

**File**: `agents/log_backup_agent.py`

**Purpose**: Back up all log files every 15 minutes to a local archive directory

**Logs backed up**:
- Trade-Alerts service: `logs/trade_alerts_*.log`
- Scalp-Engine service: `Scalp-Engine/logs/scalp_engine*.log`
- Scalp-Engine UI: `Scalp-Engine/logs/ui_activity*.log`
- OANDA trades: `Scalp-Engine/logs/oanda*.log`

**Output directory**: `logs_archive/` (local, not cloud)

**Why local backups?**
- You can search and troubleshoot logs yourself anytime
- Agents will have direct file access for future analysis without copying/pasting
- No cloud storage limits or delays

**Run manually**:
```bash
python agents/log_backup_agent.py
```

**Schedule (15-min interval)**:
```bash
# Add to crontab on Render (or Windows Task Scheduler locally)
*/15 * * * * cd /app && python agents/log_backup_agent.py
```

**Output**:
```
📁 Archive directory: /Trade-Alerts/logs_archive
🔄 Starting log backup cycle...
✅ Backed up: logs/trade_alerts_20260220.log (39KB)
✅ Backed up: Scalp-Engine/logs/scalp_engine.log (3.2KB)
...
📊 BACKUP SUMMARY
  Files backed up: 4
  Files skipped: 0
📝 Session log saved: logs_archive/sessions/20260220/backup_20260220_193501.json
✅ Log backup cycle completed successfully
```

---

## Foundation Components (Shared)

Located in `agents/shared/` - Available to all agents:

| Component | Purpose |
|-----------|---------|
| `database.py` | SQLite persistence for agent data |
| `backup_manager.py` | Git backup/rollback operations |
| `audit_logger.py` | Event logging and audit trail |
| `pushover_notifier.py` | Notifications to mobile device |
| `json_schema.py` | Data structure definitions |

**Note**: These were built for the old multi-phase system. As new agents are created, we'll use what's needed and deprecate what isn't.

---

## Directory Structure

```
agents/
├── log_backup_agent.py              # [ACTIVE] Backs up logs every 15 min
├── shared/
│   ├── database.py                  # SQLite persistence
│   ├── backup_manager.py            # Git operations
│   ├── audit_logger.py              # Audit trail logging
│   ├── pushover_notifier.py         # Mobile notifications
│   ├── json_schema.py               # Data schemas
│   └── (other utilities)
├── tests/
│   └── test_phase1_foundation.py    # Foundation component tests
├── shared-docs/
│   └── agent-coordination.md        # Agent status tracking
├── sync_render_results.py           # Sync Render data locally
└── README.md                        # This file

[REMOVED - 12 files]
├── analyst_agent.py                 ❌ REMOVED
├── forex_trading_expert_agent.py    ❌ REMOVED
├── coding_expert_agent.py           ❌ REMOVED
├── orchestrator_agent.py            ❌ REMOVED
├── monitoring_agent.py              ❌ REMOVED (monitoring_agent.py kept if needed)
└── test files + READMEs             ❌ REMOVED
```

---

## How to Add New Agents

The Log Backup Agent demonstrates the pattern for building new agents:

### 1. Single Responsibility
Each agent does **one thing well**:
- Log Backup Agent: Backs up logs
- Future: Analysis Agent might parse logs for insights
- Future: Recommendation Agent might suggest improvements

### 2. Template Structure

```python
"""
MyAgent - Brief description

Runs every X minutes and does Y.
"""

import logging
from pathlib import Path

logger = logging.getLogger('MyAgent')

class MyAgent:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent  # Trade-Alerts root
        # Initialize state
        pass

    def run(self) -> bool:
        """Main execution logic."""
        try:
            # Do work
            return True
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

def main():
    agent = MyAgent()
    success = agent.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
```

### 3. Scheduling

Use cron (Render) or Task Scheduler (Windows):

```bash
# Run every 15 minutes
*/15 * * * * cd /app && python agents/log_backup_agent.py

# Run every hour at minute 30
30 * * * * cd /app && python agents/my_agent.py

# Run daily at 11 AM EST
0 11 * * * TZ=America/New_York python agents/daily_agent.py
```

### 4. Logging

All agents should use Python's `logging` module:

```python
import logging
logger = logging.getLogger('MyAgent')

logger.info("Starting...")
logger.debug("Detailed info")
logger.warning("Something unusual")
logger.error("Something broke")
```

---

## Archive Structure

As agents run, they create session logs:

```
logs_archive/
├── logs/                            # Backed up Trade-Alerts logs
│   ├── 20260220_193501_trade_alerts_20260220.log
│   └── 20260220_194001_trade_alerts_20260220.log
├── Scalp-Engine/                    # Backed up Scalp-Engine logs
│   ├── 20260220_193501_scalp_engine.log
│   └── ...
└── sessions/                        # Session logs from agents
    └── 20260220/
        ├── backup_20260220_193501.json
        ├── backup_20260220_194001.json
        └── my_agent_20260220_100000.json
```

Each session log contains:
- Timestamp and session ID
- Files backed up / skipped / errored
- Statistics and error log
- Useful for debugging and monitoring agent activity

---

## Testing

**Test Log Backup Agent**:
```bash
python agents/log_backup_agent.py
```

Should produce:
- New `logs_archive/` directory if it doesn't exist
- Backed up log files in `logs_archive/logs/` and `logs_archive/Scalp-Engine/`
- Session log in `logs_archive/sessions/YYYYMMDD/backup_*.json`

**Test Foundation Components**:
```bash
python agents/tests/test_phase1_foundation.py
```

---

## Future Agents (Planned)

Once Log Backup Agent is proven stable:

1. **Analysis Agent** - Parse backed-up logs for patterns
   - Trade execution stats
   - Error frequency
   - Performance metrics

2. **Anomaly Detector** - Identify unusual patterns
   - Unusual trade counts
   - High error rates
   - Performance degradation

3. **Report Agent** - Generate summaries
   - Daily/weekly performance reports
   - Improvement recommendations
   - Alerts on critical issues

---

## Troubleshooting

**Archive directory not created?**
- Check file permissions in Trade-Alerts directory
- Ensure `/Trade-Alerts` has write access

**Logs not being backed up?**
- Check that source directories exist: `logs/`, `Scalp-Engine/logs/`
- Look for error messages in agent output

**Session logs empty?**
- Verify agent is running: `python agents/log_backup_agent.py`
- Check that log files exist in source directories

---

## Environment Variables

Optional configuration (in .env):

```bash
# Agent directories (auto-detected if not set)
# AGENT_BASE_DIR=/path/to/Trade-Alerts
# AGENT_ARCHIVE_DIR=/path/to/Trade-Alerts/logs_archive

# Future: Scheduling
# AGENT_RUN_TIME=17:30  # For daily agents
# AGENT_TIMEZONE=America/New_York
```

---

## Summary

✅ **What Changed:**
- Removed 12 broken agents (Phases 2-5) that never worked reliably
- Kept proven foundation components (`agents/shared/`)
- Added modular **Log Backup Agent** (runs every 15 min)
- Set up local log archives for troubleshooting

✅ **Next Steps:**
1. Test Log Backup Agent in production (Render)
2. Build additional agents following the same pattern
3. Gradually expand agent ecosystem as needed

---

## Files

| File | Purpose |
|------|---------|
| `log_backup_agent.py` | Backs up logs every 15 minutes |
| `shared/database.py` | SQLite persistence |
| `shared/backup_manager.py` | Git operations |
| `shared/audit_logger.py` | Event logging |
| `shared/pushover_notifier.py` | Notifications |
| `shared/json_schema.py` | Data schemas |
| `tests/test_phase1_foundation.py` | Foundation tests |
| `sync_render_results.py` | Sync data from Render |
| `README.md` | This file |

---

