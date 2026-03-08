# Agent Coordination Log

**Auto-Updated by Sync System** | Last Sync: N/A

---

## Overview

This file tracks the workflow between all agents running on Render at **17:30 EST daily**:
1. **Analyst Agent** - Analyzes UI, Scalp-Engine, and OANDA logs for consistency
2. **Forex Expert Agent** - Reviews analysis and generates improvement recommendations
3. **Coding Expert Agent** - Implements recommended code changes
4. **Orchestrator Agent** - Reviews implementations and approves/rejects changes

Each session entry below is automatically populated by the sync system based on database records from Render.

---

## How to Read This Log

- ✅ = Completed successfully
- ⏳ = In progress or pending
- ❌ = Failed
- ❓ = Not yet run

The timestamps show when each phase completed on Render (UTC).

---

## Active Sessions

[Sessions will be added here automatically by the sync system]

---

## How the Sync Works

The `agents/sync_render_results.py` script:
1. Downloads agent database from Render (`/var/data/agent_system.db`)
2. Pulls logs from Render (`/var/data/logs/`)
3. Extracts latest cycle results
4. Updates this file with status and timestamps
5. Makes results accessible locally for review

**Manual Sync:**
```bash
python agents/sync_render_results.py
```

**Verify Status Only:**
```bash
python agents/sync_render_results.py --verify
```

---

## Expected Workflow

### Cycle Starts at 17:30 EST

```
17:30 UTC = 12:30 EST (EST = UTC-5)
22:30 UTC = 17:30 EST
```

### Sequence

1. **17:30 EST** - Orchestrator Agent starts
   - Loads latest logs from UI, Scalp-Engine, OANDA
   - Triggers Analyst Agent

2. **Analyst Agent (typically <2min)**
   - Parses logs from three sources
   - Compares expected output vs actual output
   - Saves analysis to database

3. **Forex Expert Agent (typically <2min)**
   - Reviews analyst findings
   - Generates improvement recommendations
   - Saves to database

4. **Coding Expert Agent (typically <5min)**
   - Implements recommended code changes
   - Runs tests
   - Commits to git
   - Saves implementation to database

5. **Orchestrator Approval (typically <1min)**
   - Reviews implementation results
   - Auto-approves or flags for manual review
   - Saves decision to database

6. **Sync to Local Machine**
   - Run `python agents/sync_render_results.py` after 17:30 EST
   - Automatically updates this file
   - Can be run manually or scheduled

---

## Session History

Sessions are listed below in reverse chronological order (newest first).

---

## Troubleshooting

### Agents Not Running?
1. Check Render Trade-Alerts service logs
2. Verify `AGENT_RUN_TIME=17:30` environment variable is set
3. Look for "Multi-Agent Workflow Time" messages in logs

### Sync Not Downloading Data?
1. Verify Render services are running
2. Check network access to Render endpoints
3. Run `python agents/sync_render_results.py --verify` to check database
4. Manually copy `/var/data/agent_system.db` from Render if endpoints fail

### Logs Not Found?
1. Verify logs exist in `/var/data/logs/` on Render
2. Check that log file names match patterns:
   - `scalp_engine_YYYYMMDD.log`
   - `scalp_ui_YYYYMMDD.log`
   - `oanda_YYYYMMDD.log`

---

## Questions?

If there are questions or issues between agents:
1. Add them to the relevant session section
2. Next agent run will include them in analysis
3. Track resolutions in follow-up sessions

---
