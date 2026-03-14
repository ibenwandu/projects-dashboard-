# Multi-Agent System - Quick Reference

**Status**: Plan Complete ✅ | Ready for Phase 1 Implementation

---

## Your Configuration Choices

| Aspect | Your Choice | Details |
|--------|-------------|---------|
| **Database** | SQLite (Free) | Already used in `trade_alerts_rl.db`, perfect for this system |
| **Schedule** | 5:30 PM EST Daily | 11:30 PM UTC (after US market close) |
| **Auto-Approval** | Enabled | Test coverage > 95% + Risk = LOW → automatic |
| **Approval Records** | Full Git History | `approval_history.json` committed daily with user comments |
| **Notifications** | Pushover | You already have subscription |
| **Git Commits** | All Outputs | Every phase exports JSON + commits for full traceability |

---

## System Architecture (90-Second Overview)

```
┌─ 5:30 PM EST ─────────────────────────────────────────┐
│  ANALYST AGENT (30 min)                                │
│  ├─ Parse logs (UI, scalp-engine, OANDA)              │
│  ├─ Check consistency (entry prices, SL types)        │
│  ├─ Validate trailing SL behavior                     │
│  ├─ Calculate metrics (win rate, profit factor)       │
│  └─ Output: analysis.json → SQLite                    │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  FOREX TRADING EXPERT AGENT (30 min)                    │
│  ├─ Read: analysis.json from SQLite                    │
│  ├─ Categorize issues (CRITICAL, HIGH, MEDIUM, LOW)   │
│  ├─ Root cause analysis                               │
│  ├─ Estimate impact (win rate %, drawdown %)          │
│  └─ Output: recommendations.json → SQLite             │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  CODING EXPERT AGENT (3 hours)                          │
│  ├─ Read: recommendations.json from SQLite            │
│  ├─ Create backup: git backup-20260216-233959         │
│  ├─ Implement changes (file modifications)            │
│  ├─ Run tests (unit, integration, performance)        │
│  ├─ Commit changes: git commit (include backup hash)  │
│  └─ Output: implementation_report.json → SQLite       │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  ORCHESTRATOR AGENT (Decision Point)                    │
│  ├─ Review: test_coverage, risk_assessment            │
│  ├─ Decision:                                          │
│  │  ├─ If test_coverage > 95% + risk = LOW            │
│  │  │  → AUTO-APPROVE (record to DB + Pushover)      │
│  │  │                                                  │
│  │  └─ Else → PENDING USER APPROVAL (Pushover alert) │
│  │                                                    │
│  ├─ If APPROVED: Deploy to staging, then production  │
│  ├─ If REJECTED: Rollback using backup_hash          │
│  └─ Record decision to approval_history → Git commit  │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  GIT REPOSITORY (Full Traceability)                   │
│  ├─ analysis_20260216_233959.json                    │
│  ├─ recommendations_20260216_233959.json             │
│  ├─ implementation_20260216_233959.json              │
│  └─ approval_history.json (you can review/comment)  │
└────────────────────────────────────────────────────────┘
```

---

## Key Files to Implement (Phase 1)

```
agents/
├── __init__.py
├── shared/
│   ├── __init__.py
│   ├── json_schema.py           # Define schemas for all JSON objects
│   ├── database.py              # SQLite helper functions
│   ├── backup_manager.py        # Git backup/rollback operations
│   ├── audit_logger.py          # Record audit trail
│   └── pushover_notifier.py     # Send Pushover notifications
├── orchestrator_agent.py        # Main coordinator
├── analyst_agent.py             # Will implement Phase 2
├── forex_trading_expert_agent.py # Will implement Phase 3
├── coding_expert_agent.py       # Will implement Phase 4
└── tests/
    ├── test_database.py
    ├── test_backup_manager.py
    ├── test_audit_logger.py
    └── test_orchestrator.py

agent_scheduler.py              # Cron job runner for local dev

data/
└── agent_system.db              # SQLite database (will be created)
```

---

## Approval Flow Example

### Scenario 1: Auto-Approval (Test Coverage 97%)

```
Cycle 42 Complete
├─ Test Coverage: 97% ✅ (> 95% threshold)
├─ Risk Assessment: LOW ✅
├─ Files Modified: 1 (auto_trader_core.py)
└─ Decision: AUTO-APPROVED
   ├─ Record to DB: approval_history table
   ├─ Pushover Alert: "Cycle 42 Auto-Approved - 97% coverage, LOW risk"
   ├─ Git Commit: "Agent approval: cycle 42 - AUTO-APPROVED"
   └─ Status: Ready for staging deployment

User sees in Web UI:
  ✅ Cycle 42 | AUTO_APPROVED | Test: 97% | Risk: LOW | Ready to deploy
```

### Scenario 2: User Approval Needed (Test Coverage 92%)

```
Cycle 41 Complete
├─ Test Coverage: 92% ✅ (> 90% minimum)
├─ Risk Assessment: LOW ✅
├─ Files Modified: 2 (fisher_reversal_analyzer.py, dmi_ema_setup.py)
└─ Decision: PENDING USER APPROVAL
   ├─ Record to DB: approval_history table (user_reviewed = FALSE)
   ├─ Pushover Alert: "Cycle 41 Awaiting Approval - Link: https://your-domain.com/approvals/41"
   ├─ Status: Waiting for user review (24 hour timeout)

User reviews in Web UI:
  ⏳ Cycle 41 | PENDING | Test: 92% | Risk: LOW | [Approve] [Reject]
     User reads details, adds comment: "Good work. Let's monitor for 48h."
  → Clicks [Approve]
     ├─ Update DB: user_reviewed = TRUE, decision = APPROVED
     ├─ Git Commit: "Agent approval: cycle 41 - USER APPROVED (user comment)"
     ├─ Pushover Alert: "Cycle 41 APPROVED by you - Deploying to staging"
     └─ Status: Ready for staging deployment
```

### Scenario 3: Rejection (Low Test Coverage)

```
Cycle 40 Complete
├─ Test Coverage: 87% ❌ (< 90% minimum)
├─ Risk Assessment: MEDIUM ⚠️
├─ Files Modified: 2 (auto_trader_core.py, risk_manager.py)
└─ Decision: PENDING USER APPROVAL (will likely reject)
   ├─ Record to DB: approval_history table
   ├─ Pushover Alert: "Cycle 40 Awaiting Approval - Coverage only 87%, needs review"

User reviews in Web UI:
  ⏳ Cycle 40 | PENDING | Test: 87% ❌ | Risk: MEDIUM ⚠️ | [Approve] [Reject]
     User reads details, adds comment: "Coverage too low. Let's revisit next cycle."
  → Clicks [Reject]
     ├─ Update DB: user_reviewed = TRUE, decision = REJECTED
     ├─ Rollback: git reset --hard jkl789mno123 (pre-implementation backup)
     ├─ Git Commit: "Agent approval: cycle 40 - REJECTED (user: low coverage)"
     ├─ Pushover Alert: "Cycle 40 REJECTED - Rolled back. Will revisit next cycle."
     └─ Status: Code reverted, will reappear improved in Cycle 41+
```

---

## Approval History for Your Review

**File**: `agents/audit_exports/approval_history.json` (Updated daily, committed to git)

```json
[
  {
    "cycle": 42,
    "timestamp": "2026-02-16T23:30:00Z",
    "decision": "AUTO_APPROVED",
    "reason": "Test coverage 97% > 95% threshold",
    "auto_approved": true,
    "test_coverage": 0.97,
    "risk_assessment": "LOW",
    "git_commit_hash": "abc123def456",
    "files_modified": ["Scalp-Engine/auto_trader_core.py"],
    "changes_summary": "Fix trailing SL stalls",
    "user_reviewed": false,
    "rollback_hash": "xyz789uvw123",
    "rollback_command": "git reset --hard xyz789uvw123"
  },
  {
    "cycle": 41,
    "timestamp": "2026-02-15T23:30:00Z",
    "decision": "APPROVED",
    "reason": "User-approved after review",
    "auto_approved": false,
    "test_coverage": 0.92,
    "risk_assessment": "LOW",
    "git_commit_hash": "def789abc123",
    "files_modified": ["Scalp-Engine/src/indicators/fisher_reversal_analyzer.py"],
    "changes_summary": "Add volume filter to Fisher",
    "user_reviewed": true,
    "user_reviewed_timestamp": "2026-02-15T23:42:00Z",
    "user_review_comments": "Good work. Monitor for 48h.",
    "rollback_hash": "abc456def789"
  }
]
```

---

## Database Tables (SQLite)

**Why SQLite?**
- ✅ FREE (no external service)
- ✅ Already in your codebase (`trade_alerts_rl.db`)
- ✅ Perfect for this data structure
- ✅ ACID compliance (safe transactions)
- ✅ File-based (can be committed to git)

**Tables to Create**:

1. **agent_analyses** - Analyst Agent outputs
2. **agent_recommendations** - Forex Expert outputs
3. **agent_implementations** - Coding Expert outputs + test results
4. **approval_history** - User approval audit trail (THE KEY TABLE)
5. **audit_trail** - Event log (who did what, when)
6. **orchestrator_state** - Current workflow status
7. **config** - Schedule + agent configurations

---

## Environment Variables to Add

```bash
# Database
DATABASE_PATH=/var/data/agent_system.db  # Render
# DATABASE_PATH=data/agent_system.db      # Local dev

# Schedule
AGENT_RUN_TIME=17:30  # 5:30 PM EST
AGENT_TIMEZONE=America/New_York

# Auto-Approval
ORCHESTRATOR_AUTO_APPROVE_THRESHOLD=0.95  # 95% test coverage
ORCHESTRATOR_AUTO_APPROVE_MAX_RISK=LOW     # Never auto-approve MEDIUM/HIGH

# Pushover
PUSHOVER_API_TOKEN=your_app_token
PUSHOVER_USER_KEY=your_user_key

# Git
AGENT_GIT_AUTHOR_NAME="Claude Code Agent"
AGENT_GIT_AUTHOR_EMAIL="agent@trade-alerts.local"
```

---

## Success Metrics (After Deployment)

Track these metrics:

| Metric | Target | Check |
|--------|--------|-------|
| **Analysis Accuracy** | <1% false positives | Do identified issues match actual problems? |
| **Recommendation Quality** | >80% actionable | Do recommended fixes actually resolve issues? |
| **Implementation Success** | 100% pass tests | Do changes break anything? |
| **Approval Process** | <5% manual overrides needed | Is auto-approval working well? |
| **Cycle Time** | <6 hours total | Analyst (1h) + Expert (0.5h) + Coder (3h) + Review (1.5h) |
| **Rollback Reliability** | 100% | Can we always revert? |

---

## Phase 1 Implementation Tasks

### Week 1: Foundation

- [ ] Create `agents/` directory structure
- [ ] Create SQLite database schema (agent_system.db)
- [ ] Implement `shared/json_schema.py` (all JSON schemas)
- [ ] Implement `shared/database.py` (connection + helpers)
- [ ] Implement `shared/backup_manager.py` (git operations)
- [ ] Implement `shared/audit_logger.py` (audit trail)
- [ ] Implement `shared/pushover_notifier.py` (alerts)
- [ ] Create agent configuration templates
- [ ] Test database creation locally
- [ ] Test backup/rollback mechanism
- [ ] Update .env template with new variables
- [ ] Create README documenting the system
- [ ] **Ready for Phase 2**: Analyst Agent implementation

---

## Next Action

**Ready to proceed with Phase 1 implementation?**

The plan is complete and committed to git. Once you confirm, I'll start building:

1. **agents/** directory with shared utilities
2. **SQLite schema** with all 7 tables
3. **Database helpers** for safe reads/writes
4. **Backup manager** for git-based rollbacks
5. **Pushover integration** for notifications
6. **Audit logger** for complete event trail

Then we'll move to Phase 2 (Analyst Agent) once Phase 1 is solid.

