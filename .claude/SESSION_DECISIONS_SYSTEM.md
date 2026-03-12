# Automated Session Decisions & Plans Persistence System

**Purpose**: Ensure NO decisions, plans, or critical context is ever lost between sessions, even during auto-compress.

**Status**: ACTIVE - Implement immediately at end of every session

---

## Architecture

### Layer 1: Persistent Storage (Git-Backed)

**Location**: `.claude/session-decisions/` (version controlled)

```
.claude/
├── session-decisions/
│   ├── DECISION_INDEX.md          # Master index of all decisions
│   ├── ACTIVE_PROJECTS.md         # Current project status & priorities
│   ├── EMY_VISION_COMPLETE.md     # Emy OpenClaw deployment plan (THIS IS CRITICAL)
│   ├── TRADE_ALERTS_STATUS.md     # Trade-Alerts monitoring status
│   ├── [DATE]-[PROJECT]-[DECISION].md  # Timestamped decision records
│   └── [DATE]-[PROJECT]-[PLAN].md
└── memory/                          # Existing per-project memory
```

### Layer 2: Automatic Capture (End of Session)

**What gets captured**:
- ✅ All plans created (architecture, implementation, roadmap)
- ✅ All major decisions made (approach, technology, trade-offs)
- ✅ All approvals given by user
- ✅ All designs/diagrams discussed
- ✅ All blockers and workarounds
- ✅ Current project status
- ✅ Next steps explicitly stated

**How**: Every session ending must include:
```bash
# Automated capture script runs BEFORE session closes
python .claude/capture_session_decisions.py \
  --session-id $SESSION_ID \
  --project "Emy|Trade-Alerts|Job-Search" \
  --decisions-created [list] \
  --decisions-approved [list] \
  --status-update [text]
```

### Layer 3: Auto-Load at Session Start

**What loads automatically**:
1. Previous session's pending items
2. Active project decisions
3. Current blockers
4. Next milestone
5. User's explicit instructions from last session

**How**: `start-session-root` skill ALWAYS runs:
```bash
1. Read .claude/session-decisions/DECISION_INDEX.md
2. Read .claude/session-decisions/ACTIVE_PROJECTS.md
3. Read project-specific decision file
4. Present in session summary
```

### Layer 4: Indexed Search (Fast Access)

**Index file**: `.claude/session-decisions/DECISION_INDEX.md`

```markdown
# Decision Index (Searchable)

## By Project
- **Emy**: EMY_VISION_COMPLETE.md (Mar 11, 2026, OpenClaw deployment)
- **Trade-Alerts**: TRADE_ALERTS_STATUS.md (Mar 12, monitoring phase)
- **Job-Search**: Disabled (decision in index)

## By Type
- Plans: [list with links]
- Decisions: [list with links]
- Approvals: [list with links]
- Blockers: [list with links]

## By Date (Latest First)
- 2026-03-12: Emy Phase 1a complete, Phase 1b ready
- 2026-03-11: OpenClaw plan created (587 lines)
- ...
```

---

## Critical Files That MUST NOT BE LOST

These need PERMANENT storage with auto-backup:

1. **EMY_VISION_COMPLETE.md** (MISSING - RECREATE NOW)
   - OpenClaw-aligned Emy deployment plan
   - Voice, Vision, Multimodal agents
   - All phases with detailed specs
   - Status: NEEDS RECONSTRUCTION

2. **TRADE_ALERTS_STATUS.md** (Create now)
   - Current monitoring: DeepSeek parser fix (48-hour test)
   - Last known good state
   - Next actions when monitoring complete

3. **EMY_OPENCLAW_ALIGNMENT.md** (Create now)
   - How Emy maps to OpenClaw architecture
   - Multi-agent orchestration
   - Multimodal capabilities

---

## Implementation: Immediate Actions

### Action 1: Create Master Decision Index

**File**: `.claude/session-decisions/DECISION_INDEX.md`

Content structure:
```markdown
# Session Decisions Master Index

**Last Updated**: [DATE TIME]
**Auto-Load**: YES (triggers on every session start)

## CRITICAL - ACTIVELY BEING WORKED ON
- Emy Phase 1b Development (TARGET COMPLETE: Mar 19)
  - File: EMY_VISION_COMPLETE.md (MISSING - NEEDS RECREATION)
  - Status: BLOCKED on plan retrieval

## MONITORING (48-hour test period)
- Trade-Alerts Phase 1 Analysis
  - Fix: DeepSeek parser + logging improvements
  - Period: Mar 12-14, 2026
  - Next: Monitor results, provide feedback

## COMPLETED ✅
- Emy Phase 1a Deployment (Mar 12, 2026)
- Trade-Alerts Phase 1 Analysis (Mar 2-11, 2026)
```

### Action 2: Store Session Decisions Automatically

Create script: `.claude/capture_session_decisions.py`

```python
#!/usr/bin/env python3
"""
Automatically capture session decisions before session close.
Run at END of every session.
"""

import json
from datetime import datetime
from pathlib import Path

DECISIONS_DIR = Path.home() / ".claude" / "session-decisions"
DECISIONS_DIR.mkdir(parents=True, exist_ok=True)

def capture_session(session_id, project, decisions, status):
    """Capture session decisions to persistent storage"""

    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{project}-decisions.md"
    filepath = DECISIONS_DIR / filename

    content = f"""# {project} Session Decisions

**Date**: {datetime.now().isoformat()}
**Session ID**: {session_id}

## Decisions Made
{decisions}

## Current Status
{status}

## Auto-Captured
This file was automatically generated at session end.
Do NOT delete - needed for next session start.
"""

    filepath.write_text(content)
    print(f"✅ Decisions captured: {filepath}")

if __name__ == "__main__":
    import sys
    capture_session(
        session_id=sys.argv[1] if len(sys.argv) > 1 else "unknown",
        project=sys.argv[2] if len(sys.argv) > 2 else "Unknown",
        decisions=sys.argv[3] if len(sys.argv) > 3 else "No decisions",
        status=sys.argv[4] if len(sys.argv) > 4 else "In progress"
    )
```

### Action 3: Auto-Load at Session Start

Update `start-session-root` skill to:

```python
# Load decision index automatically
decisions_index = DECISIONS_DIR / "DECISION_INDEX.md"
if decisions_index.exists():
    print("📋 PREVIOUS SESSION DECISIONS:")
    print(decisions_index.read_text())
```

---

## Backup Strategy: Redundancy

### Backup 1: Git Commits (Searchable History)

```bash
# Every decision stored as git commit
git add .claude/session-decisions/
git commit -m "docs: Session decisions - $(date +%Y-%m-%d) - [PROJECT] - [DECISION]"
```

Search via:
```bash
git log --grep="Decision\|Plan\|Emy" --oneline | head -20
```

### Backup 2: Structured JSON (Machine-Readable)

File: `.claude/session-decisions/DECISIONS.json`

```json
{
  "sessions": [
    {
      "date": "2026-03-11",
      "project": "Emy",
      "decision": "Create OpenClaw-aligned deployment plan",
      "status": "COMPLETE - 587 lines",
      "file": "EMY_VISION_COMPLETE.md",
      "critical": true
    }
  ]
}
```

### Backup 3: Plain Text (Human-Readable)

File: `.claude/session-decisions/README.txt`

```
CRITICAL FILES - DO NOT DELETE
===============================

EMY_VISION_COMPLETE.md (MISSING - Mar 11, 2026)
  - OpenClaw-aligned Emy architecture
  - Voice, Vision, Multimodal agents
  - Full development roadmap
  - STATUS: NEEDS IMMEDIATE RECOVERY

TRADE_ALERTS_STATUS.md (CREATE - Mar 12, 2026)
  - Monitoring: DeepSeek fix (48 hours)
  - Detailed tracking

[MORE FILES]
```

---

## Workflow: How This Works

### Session End (Automatic)

```
1. User: "Let me close this session"
2. System: Runs capture_session_decisions.py
3. Captures: All plans, decisions, status
4. Stores: .claude/session-decisions/[DATE]-[PROJECT].md
5. Git commits: New decision record
6. Updates: DECISION_INDEX.md
7. Ready for: Next session auto-load
```

### Session Start (Automatic)

```
1. System: Runs start-session-root skill
2. Loads: DECISION_INDEX.md from .claude/session-decisions/
3. Presents: "Here's what you were working on..."
4. Loads: Project-specific decisions
5. Shows: Current blockers, next steps
6. Zero manual recall needed
```

### Mid-Session Compress (Automatic)

```
If session gets auto-compressed:
1. Critical context files ALREADY in .claude/ filesystem
2. start-session-root reloads from disk
3. No information lost
4. Continues as if no compress happened
```

---

## Query System: Find Anything Instantly

User wants to find something → search workflow:

```bash
# Search all past decisions
grep -r "Openclaw\|Voice Agent\|Vision" .claude/session-decisions/

# Search by date
ls -lrt .claude/session-decisions/ | grep "2026-03"

# Search by project
ls .claude/session-decisions/ | grep "Emy\|Trade-Alerts"

# Open last session
cat .claude/session-decisions/DECISION_INDEX.md
```

---

## IMMEDIATE NEXT STEPS (RIGHT NOW)

### Step 1: Create Session Decisions Directory
```bash
mkdir -p ~/.claude/session-decisions
git add .claude/session-decisions/
```

### Step 2: Create DECISION_INDEX.md (NOW)
Document what we know is missing:
- Emy OpenClaw plan (Mar 11, 587 lines)
- Status of all projects
- What needs recovery

### Step 3: Find & Store the Missing Plan
Search previous session for "OpenClaw" plan content
If found: Save to `EMY_VISION_COMPLETE.md`
If not found: RECREATE from scratch with full detail

### Step 4: Commit This System
```bash
git add .claude/SESSION_DECISIONS_SYSTEM.md
git add .claude/session-decisions/
git commit -m "infra: Implement fail-safe session decisions persistence system"
```

---

## Success Criteria

- [x] System designed
- [ ] Directory created
- [ ] DECISION_INDEX.md created
- [ ] capture_session_decisions.py created
- [ ] start-session-root updated
- [ ] Missing Emy plan recovered or recreated
- [ ] First automatic capture tested
- [ ] Zero manual context recall needed in next session

---

## CRITICAL GUARANTEE

After implementation:

**User NEVER has to manually recall past work again.**

✅ Session auto-loads all decisions
✅ Git searchable history
✅ Indexed access
✅ Auto-captured every session end
✅ Survives auto-compress
✅ Survives session restart
✅ Survives machine restart

---

**This solves the problem permanently.**

Next: Implement this system, then recover/recreate the missing Emy OpenClaw plan.
