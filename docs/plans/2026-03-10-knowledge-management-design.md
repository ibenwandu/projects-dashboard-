# Enhancement #6 Design: Automated Knowledge Management for Obsidian Dashboard

**Date**: March 10, 2026
**Status**: Approved
**Target**: Hourly automated updates to Mission Control Dashboard with Emy status (zero manual processes)

---

## Overview

Implement automated Obsidian dashboard updates that eliminate manual tracking. The KnowledgeAgent runs hourly, queries Emy's database and Windows Task Scheduler, and updates the Mission Control Dashboard with current status, activity summary, and critical alerts.

**Scope**: Emy project status in Obsidian 00-DASHBOARD.md
**Automation**: Fully automated hourly via Emy's scheduler
**Integration**: Database queries + Task Scheduler API + git auto-commit

---

## Problem Statement

Currently, the Mission Control Dashboard requires manual updates to show:
- Whether Emy is running
- When it last executed
- What it's doing next
- Recent activity and alerts

This introduces human error risk and requires discipline to keep current.

**Solution**: Fully automated hourly updates that:
- Query Task Scheduler for actual task status
- Read database for activity metrics
- Update Obsidian markdown automatically
- Commit changes to git
- Require zero manual intervention

---

## Architecture

### Components

**KnowledgeAgent Enhancement** (`emy/agents/knowledge_agent.py`):
- Existing methods: `_update_obsidian_dashboard()`, `_commit_changes()`
- New methods:
  - `_get_emy_status()` — Query Task Scheduler for "Emy Chief of Staff"
  - `_get_last_run_time()` — Query database (emy_tasks table)
  - `_get_next_scheduled_job()` — Parse Task Scheduler for upcoming jobs
  - `_get_recent_alerts()` — Query database for Pushover alerts (last 24 hours)
  - `_check_critical_alerts()` — Scan for emergency conditions (100% daily loss)
  - `_format_dashboard_row()` — Generate markdown table row with all data
  - `_update_dashboard_table()` — Modify Obsidian file

**Data Sources**:
1. Windows Task Scheduler API — Real-time task status
2. SQLite (emy.db) — Historical data and activity
3. Obsidian vault file (00-DASHBOARD.md) — Dashboard markdown

**Git Integration**:
- Auto-commit after updates: `git add 00-DASHBOARD.md && git commit -m "auto: update Emy status [hourly]"`
- No force-push (local only, user controls sync to remote)

---

## Data Requirements

### Task Scheduler Queries

```
Get-ScheduledTask -TaskName "Emy Chief of Staff" | Select-Object:
  - State (Running/Ready/Stopped/Disabled)
  - LastRunTime (timestamp)
  - NextRunTime (timestamp)
  - LastTaskResult (0=success)
```

### Database Queries

**Last Run Time:**
```sql
SELECT MAX(created_at) FROM emy_tasks
WHERE domain = 'trading' OR domain = 'job_search' OR domain = 'knowledge'
```

**Recent Alerts (last 24 hours):**
```sql
SELECT action, COUNT(*) as count
FROM emy_tasks
WHERE action LIKE 'alert_%'
  AND created_at > datetime('now', '-24 hours')
GROUP BY action
```

**Critical Alerts:**
```sql
SELECT * FROM emy_tasks
WHERE alert_level = 'CRITICAL'
  AND created_at > datetime('now', '-24 hours')
```

---

## Dashboard Display Format

### Current (Manual)
```markdown
| Emy | Phase 1: Pushover Alerts | 🟢 RUNNING | Monitor first 24 hrs | Alerts configured, Task Scheduler deployed |
```

### Updated (Hourly Auto)

**Normal Status:**
```markdown
| Emy | Phase 1: Pushover Alerts | 🟢 RUNNING (14:32) | trading_health_check in 13min | ✅ Executions: 156 | Alerts: 3T/1R | Last: NOW |
```

**With Critical Alert:**
```markdown
| Emy | Phase 1: Pushover Alerts | 🔴 CRITICAL | Daily loss 100% - Trading disabled | ⚠️ INVESTIGATE IMMEDIATELY |
```

**Fields Displayed:**
- Status: Task Scheduler state + last run timestamp
- Next Milestone: Next scheduled job + time until execution
- Progress: Task counts + alert summary + "Last: NOW" (updates hourly)

---

## Data Flow

```
Scheduled Event: Every Hour (via Emy's internal scheduler)
  ↓
KnowledgeAgent.run() triggered
  ├─ Disable check (skip if .emy_disabled)
  │
  ├─ Step 1: Get Task Scheduler Status
  │   ├─ Query "Emy Chief of Staff" task
  │   ├─ Get: State (Running/Stopped/etc)
  │   ├─ Get: LastRunTime
  │   └─ Store: status_text = "🟢 RUNNING (14:32)" or "🔴 STOPPED"
  │
  ├─ Step 2: Get Next Job
  │   ├─ Parse scheduler
  │   ├─ Find next job after now()
  │   └─ Store: next_job = "trading_health_check in 13min"
  │
  ├─ Step 3: Get Activity Metrics
  │   ├─ Query emy_tasks for recent alerts (24 hours)
  │   ├─ Count by action type
  │   └─ Store: alerts_summary = "✅ Executions: 156 | Alerts: 3T/1R"
  │
  ├─ Step 4: Check Critical Alerts
  │   ├─ Query for CRITICAL severity
  │   ├─ If found: Use critical_status = "🔴 CRITICAL"
  │   └─ Else: Use normal_status
  │
  ├─ Step 5: Update Obsidian File
  │   ├─ Load 00-DASHBOARD.md
  │   ├─ Find Emy row in table
  │   ├─ Replace cells with new values
  │   └─ Write back to file
  │
  ├─ Step 6: Commit to Git
  │   ├─ git add 00-DASHBOARD.md
  │   ├─ git commit -m "auto: update Emy status [hourly]"
  │   └─ Log success/failure
  │
  └─ Log completion to emy_tasks (timestamp, status)

Next execution: +60 minutes
```

---

## Error Handling

### Scenario 1: Task Scheduler Unreachable
**Condition**: PowerShell API call fails
**Action**:
- Log warning: "Task Scheduler unavailable, using last known status"
- Display "🟡 UNKNOWN" instead of specific status
- Continue with database queries
- Try again next hour

**Impact**: Status may be stale, but no crash

### Scenario 2: Database Query Fails
**Condition**: emy_tasks table unavailable or corrupted
**Action**:
- Log error with specific query that failed
- Skip alert summary (show "N/A")
- Continue with other updates
- Don't block git commit

**Impact**: Alerts won't update, but status still updates

### Scenario 3: Obsidian File Missing
**Condition**: 00-DASHBOARD.md not found
**Action**:
- Log error
- Create file with template header and empty Emy row
- Populate with current data
- Commit new file

**Impact**: Dashboard recreated from scratch

### Scenario 4: Git Commit Fails
**Condition**: Working directory dirty or merge conflict
**Action**:
- Log error with git output
- Continue anyway (dashboard still updated locally)
- Don't force-push
- Operator should resolve manually

**Impact**: Changes local only, not committed to git

### Scenario 5: Critical Alert Detected
**Condition**: 100% daily loss or API error found
**Action**:
- Update dashboard with 🔴 CRITICAL status
- Send Pushover Emergency alert (via TradingAgent)
- Log as critical event
- Continue hourly updates

**Impact**: Alert visible in dashboard + Pushover notification

---

## Integration Points

### With Existing Systems

**TradingAgent**:
- Reads: emy_tasks table (populated by TradingAgent)
- Writes: Dashboard status (no feedback to TradingAgent)

**Task Scheduler**:
- Reads: Task status via PowerShell Get-ScheduledTask
- Writes: None (read-only)

**Obsidian Vault**:
- Reads: 00-DASHBOARD.md to find Emy row
- Writes: Updated cells in Emy row

**Git**:
- Reads: Current commit history (none needed)
- Writes: New commit with dashboard updates

### Scheduled Job Registration

In Emy's job scheduler (main.py):
```
Job: obsidian_dashboard_update
  Cadence: Every 60 minutes
  Agent: KnowledgeAgent
  Priority: MEDIUM
```

---

## Testing Strategy

### Unit Tests

1. **Task Scheduler Query**
   - Mock Get-ScheduledTask with RUNNING state
   - Verify status formatting "🟢 RUNNING (HH:MM)"
   - Test STOPPED, DISABLED, ERROR states

2. **Database Queries**
   - Mock emy_tasks table with sample data
   - Verify alert count calculation
   - Test empty results (no alerts)

3. **Markdown Parsing**
   - Load real 00-DASHBOARD.md
   - Find Emy row correctly
   - Replace cells without corrupting other rows

4. **Critical Alert Detection**
   - Mock critical alert in database
   - Verify 🔴 CRITICAL status generated
   - Verify Pushover alert triggered

### Integration Tests

1. **Full Pipeline**
   - Task Scheduler query + database query + file update + git commit
   - Verify file changed + commit created

2. **Error Recovery**
   - Simulate Task Scheduler timeout
   - Verify update still completes with "UNKNOWN" status

3. **Idempotence**
   - Run twice in succession
   - Verify dashboard shows current time both times
   - Verify only one commit for unchanged data

### Mock Tests

- Mock Task Scheduler responses (Running, Stopped, Error)
- Mock database empty results
- Mock Obsidian file not found
- Mock git failure scenarios

---

## Success Criteria

✅ Dashboard updates every 60 minutes automatically
✅ Status reflects actual Task Scheduler state
✅ Last run time current (within 5 minutes of actual)
✅ Alert counts accurate (matches database query)
✅ Critical alerts (100% daily loss) display with 🔴 CRITICAL
✅ Changes auto-committed to git (with descriptive message)
✅ Zero manual intervention required
✅ All tests pass (unit + integration + error scenarios)
✅ No performance degradation to Emy (scheduler remains responsive)
✅ Error handling prevents crashes (graceful degradation)

---

## Dependencies

- **PowerShell 5.0+**: For Task Scheduler API access
- **sqlite3**: Already in requirements.txt (database queries)
- **git**: Already available (auto-commits)
- **Python pathlib**: For file operations
- **Obsidian Vault**: Pre-existing at `../Obsidian Vault/My Knowledge Base/`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Task Scheduler queries fail | Use "UNKNOWN" status, don't crash, try next hour |
| Database corrupted | Skip metrics, continue with status update, alert operator |
| Obsidian file permissions denied | Log error, create backup, try again next hour |
| Git conflict on commit | Log error, don't force-push, operator resolves manually |
| Hourly updates cause clock drift | Stateless job, no persistent timers, Task Scheduler tracks timing |
| Too many git commits (100/day) | Acceptable (25KB avg per commit, easily managed) |
| Dashboard becomes stale | Automatic recovery: next hour's update fixes it |

---

## Timeline

- **Phase 1**: Enhance KnowledgeAgent methods (1 hour)
- **Phase 2**: Database query implementation (1 hour)
- **Phase 3**: Markdown parsing + update logic (1 hour)
- **Phase 4**: Testing + git integration (1.5 hours)

**Total**: ~4.5 hours

---

## Design Decisions

1. **Hourly frequency** (not real-time) — Balances freshness with resource usage
2. **Read-only Task Scheduler** — Avoids modifying system state
3. **Auto-commit locally** (no remote push) — You control sync timing
4. **Graceful degradation** — Missing data fields show "N/A", system continues
5. **SQLite for activity** (not real-time logs) — Structured queries easier than parsing logs

---

**Design approved by**: Ibe Nwandu
**Date approved**: March 10, 2026
**Next step**: Implementation planning (writing-plans skill)
