# Agent Sync System - Quick Reference Card

**Created**: Feb 17, 2026 | **For**: Every session after agent execution

---

## ⚡ TL;DR

Agents run at **17:30 EST** on Render. Results synced automatically to:
```
agents/shared-docs/agent-coordination.md
```

Check this file to see status of all 4 agents. That's it.

---

## 📋 What to Check (In Order)

### 1️⃣ **Coordination Log** (Primary Source)
```bash
cat agents/shared-docs/agent-coordination.md
```

**You'll see:**
- Cycle number
- Status of each agent (✅ ⏳ ❌)
- Timestamps when each completed
- Links to full reports

### 2️⃣ **Verify Sync Status** (If unsure)
```bash
python agents/sync_render_results.py --verify
```

**Output:**
```
Latest cycle: [N]
  Analyst: [STATUS]
  Expert: [STATUS]
  Coder: [STATUS]
  Orchestrator: [STATUS]
```

### 3️⃣ **Check Downloaded Logs** (If investigating)
```bash
ls -la agents/shared-docs/logs/
```

Should show 3 files:
- `scalp_engine.log` (from Render scalp_engine_YYYYMMDD.log)
- `oanda_trades.log` (from Render oanda_YYYYMMDD.log)
- `ui_activity.log` (from Render scalp_ui_YYYYMMDD.log)

---

## 🎯 Common Scenarios

### ✅ "All agents completed successfully"
```markdown
## Session 5 - 2026-02-17 22:35:00 UTC
### Analyst Phase: ✅ COMPLETED
### Forex Expert Phase: ✅ COMPLETED
### Coding Expert Phase: ✅ COMPLETED
### Orchestrator Phase: ✅ APPROVED
```

**Action**: Check the recommendations and implementations in the report links.

### ⏳ "Agents are still running"
```markdown
## Session 5 - 2026-02-17 22:32:00 UTC
### Analyst Phase: ✅ COMPLETED
### Forex Expert Phase: ⏳ IN_PROGRESS
```

**Action**: Wait a few minutes and re-check.

### ❌ "Agent phase failed"
```markdown
## Session 5 - 2026-02-17 22:32:00 UTC
### Analyst Phase: ✅ COMPLETED
### Forex Expert Phase: ❌ FAILED
```

**Action**: Check `agents/SYNC_SYSTEM_README.md` troubleshooting section.

### ❓ "No session in coordination log"
**Possible causes**:
1. Agents haven't run yet (before 17:35 EST)
2. Sync hasn't run (run manually: `python agents/sync_render_results.py`)
3. Agents failed silently on Render (check Render logs)

**Fix**:
```bash
# Trigger manual sync
python agents/sync_render_results.py

# Or verify database has data
python agents/sync_render_results.py --verify
```

---

## 📁 File Locations

| What | Where |
|-----|-------|
| Coordination log (Auto-updated) | `agents/shared-docs/agent-coordination.md` |
| Downloaded logs from Render | `agents/shared-docs/logs/` |
| Sync script | `agents/sync_render_results.py` |
| Full documentation | `agents/SYNC_SYSTEM_README.md` |
| Implementation details | `AGENT_SYNC_IMPLEMENTATION.md` |
| Session history | `CLAUDE_SESSION_LOG.md` (Session 10) |

---

## 🔧 Manual Operations

### Force Re-sync
```bash
python agents/sync_render_results.py
```

### Just Check Status (Don't Download)
```bash
python agents/sync_render_results.py --verify
```

### Use Local Database Copy
```bash
python agents/sync_render_results.py --local-db /path/to/agent_system.db
```

### Run Helper Script
```bash
bash agents/run-sync.sh
```

---

## 🚨 Troubleshooting Quick Links

| Issue | Solution |
|-------|----------|
| "Database not found" | See SYNC_SYSTEM_README.md section: Database Issues |
| "Logs not downloaded" | See SYNC_SYSTEM_README.md section: Log File Issues |
| "Coordination.md not updating" | See SYNC_SYSTEM_README.md section: Coordination Log Issues |
| Agents not running at all | See CLAUDE_SESSION_LOG.md Session 10: Verify execution time |

---

## 🧠 Key Facts (Don't Forget!)

1. **Agents run at 17:30 EST** (NOT UTC)
   - = 22:30 UTC
   - Main.py auto-syncs results to local machine

2. **Three log streams collected**:
   - UI logs (user inputs/config changes)
   - Scalp-Engine logs (trade decisions)
   - OANDA logs (actual executions)

3. **Analyst compares**:
   - Expected output (from UI configuration)
   - vs Observed output (from Scalp-Engine and OANDA)

4. **Results in 4 agent phases**:
   1. Analyst - Identifies issues
   2. Forex Expert - Recommends improvements
   3. Coding Expert - Implements code changes
   4. Orchestrator - Approves/rejects changes

5. **Log filename note**: Actual logs on Render have dates (e.g., `scalp_engine_20260217.log`) but sync script normalizes them to expected names

---

## 📞 Need Help?

### For Implementation Details
→ `AGENT_SYNC_IMPLEMENTATION.md`

### For Technical How-To
→ `agents/SYNC_SYSTEM_README.md`

### For Full Session History
→ `CLAUDE_SESSION_LOG.md` (Session 10 has everything)

### For Personal Context
→ `~/.claude/PERSONAL_MEMORY.md`

---

## ✨ Remember

**The entire point of this system**: You should NEVER have to manually check Render again.

- Agents run automatically ✅
- Results sync automatically ✅
- Everything visible locally ✅
- No manual context-switching ✅

Just check `agents/shared-docs/agent-coordination.md` and you're done!

---

**Last Updated**: 2026-02-17 22:30 EST
**Valid Until**: Agents or scheduling changes
**Review**: Session 10 in CLAUDE_SESSION_LOG.md if confused
