# Emy: From Task Scheduler to AI Chief of Staff
## Transformation Strategy & Architecture Recommendations

**Date:** March 16, 2026
**Status:** Strategic Planning (Pre-Implementation)
**Vision Alignment:** Transforming from hardcoded workflow automation to intelligent autonomous orchestration

---

## Executive Summary

**Current State:** Emy has three specialist agents (TradingHoursMonitor, LogAnalysis, Profitability) running on hardcoded Celery Beat schedules. This is **task automation**, not **AI orchestration**.

**Target State:** Emy as an AI Chief of Staff that accepts natural language commands from users, reasons about which agents to delegate to, dynamically schedules work, and synthesizes results back naturally.

**Transformation Approach:** Add three new orchestration components to Emy's core without rewriting existing agents. This allows incremental growth while preserving the specialist agents we've built.

---

## Vision Reminder: Why Emy Exists

From your original vision:
> "Emy is an autonomous AI Chief of Staff for trading operations. Users give high-level directives ('monitor trading hours', 'analyze performance', 'optimize profitability'). Emy understands intent, delegates to specialized agents, manages execution, and synthesizes results back to the user."

**Current System Violates This:**
- ❌ No natural language interface for user commands
- ❌ Schedules are hardcoded in render.yaml, not user-driven
- ❌ No reasoning about WHEN to act (cron just fires)
- ❌ No synthesis layer (results go to database, user must query)
- ✅ Specialist agents work correctly (good foundation)

---

## The Gap Analysis

| Capability | Current | Needed | Gap |
|-----------|---------|--------|-----|
| Natural language commands | ❌ None | ✅ Chat interface | User can't speak to Emy |
| Intent parsing | ❌ None | ✅ Task interpreter | No understanding of user intent |
| Agent delegation | ❌ Hardcoded schedules | ✅ Dynamic routing | Emy can't decide what to do |
| Scheduling | ❌ Fixed cron times | ✅ User-configurable | Can't adapt to user needs |
| Result synthesis | ❌ Raw database | ✅ Natural language | Results are machine-readable, not human-readable |
| Autonomy | ⚠️ Partial (agents run alone) | ✅ Full orchestration | No central decision-making |

---

## Recommended Transformation Architecture

**Option: Hybrid Orchestration Layer** (Recommended - incremental, low-risk, aligns with vision)

### Three New Components to Add

#### 1. **TaskInterpreter** (Intent Parser)
**Purpose:** Convert natural language user commands into structured agent delegation requests

**What it does:**
- Takes user message: "Monitor trading hours and handle any issues"
- Parses intent: `{ "type": "enforcement", "action": "monitor_and_enforce", "frequency": "continuous" }`
- Outputs agent list: `["TradingHoursMonitorAgent"]` with execution parameters
- Handles variations: "check compliance", "ensure trading rules", "validate hours" → all map to TradingHoursMonitor

**Technology:**
- Claude Haiku (cheap + fast)
- Prompt engineering with few-shot examples of user intents
- Structured output (JSON) with validation

**Example Flow:**
```
User: "Analyze yesterday's trades and tell me what worked"
TaskInterpreter: {
  "intent": "performance_analysis",
  "agents": ["LogAnalysisAgent"],
  "parameters": {
    "period": "yesterday",
    "include_recommendations": false
  },
  "output_format": "natural_language"
}
```

#### 2. **DynamicScheduler** (Scheduling Manager)
**Purpose:** Convert user intent into Celery Beat schedules dynamically

**What it does:**
- Takes output from TaskInterpreter
- Translates to Celery schedule format: `crontab(hour=21, minute=30, day_of_week=4)` for "Friday evening"
- Updates Celery Beat beat_schedule at runtime (no code changes needed)
- Stores user's scheduling preferences in database for persistence
- Handles natural language time expressions: "daily", "weekly", "every 6 hours", "Friday evening"

**Technology:**
- Database table: `user_task_schedules` (command, agents, cron_expression, active, created_at, updated_at)
- Celery Beat dynamic scheduler (updates schedule without restart)
- Cron expression builder from natural language

**Example Flow:**
```
User: "Check trading hours compliance twice a day"
DynamicScheduler converts to:
  - 00:00 UTC (midnight check)
  - 12:00 UTC (midday check)
Updates Celery Beat beat_schedule without restarting
```

#### 3. **ResultPresenter** (Synthesis & Communication)
**Purpose:** Convert raw agent outputs into natural language summaries for user

**What it does:**
- Takes agent result (structured data: trades closed, P&L, anomalies detected)
- Synthesizes into natural human response
- Determines if alerts needed (Pushover, email)
- Formats for different contexts (chat, email, dashboard)
- Handles multi-agent synthesis (combines LogAnalysis + Profitability insights)

**Technology:**
- Claude Sonnet (for synthesis — higher quality)
- Template system for standard responses
- Alert routing logic

**Example Flow:**
```
Agent Output (raw):
{
  "trades_closed": 2,
  "total_pnl": -45.30,
  "closure_reason": "trading_hours_enforcement",
  "alert_level": "critical"
}

ResultPresenter Output (natural):
"Trading hours enforcement completed at 21:30 UTC Friday. Closed 2 non-compliant positions with realized loss of $45.30. Alert sent to your Pushover app."
```

---

## Recommended Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  USER INTERFACE (Chat / Natural Language)                   │
│  "Monitor trading hours, analyze performance, etc."         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ╔════════════════════════════╗
        ║  EMY ORCHESTRATION LAYER   ║
        ║  (NEW - Add These Three)   ║
        ╠════════════════════════════╣
        ║ 1. TaskInterpreter         ║ ← Understand what user wants
        ║ 2. DynamicScheduler        ║ ← When to run it
        ║ 3. ResultPresenter         ║ ← How to communicate back
        ╚────────────┬───────────────╝
                     │
        ┌────────────┴────────────────┐
        ↓                             ↓
   AGENT DELEGATION         CELERY BEAT SCHEDULING
   (Existing agents)        (Enhanced, stays the same)
        │                             │
        ├─ TradingHoursMonitor       Cron schedules
        ├─ LogAnalysis              (now user-defined)
        └─ Profitability             │
                     │               │
                     └───────┬───────┘
                             ↓
                    SPECIALIST AGENTS
                    (Run unchanged)
                             │
                     ┌───────┴────────┐
                     ↓                ↓
                  Database         OANDA API
                                  Pushover API
```

---

## Implementation Strategy

### Phase 1: Add TaskInterpreter (Week 1)
- Create `emy/agents/task_interpreter_agent.py`
- Define intent taxonomy (monitoring, analysis, optimization, etc.)
- Build few-shot examples for Claude
- Add tests for intent parsing accuracy
- **Cost impact:** Minimal (uses Haiku, very cheap)

### Phase 2: Add DynamicScheduler (Week 2)
- Create `user_task_schedules` database table
- Implement Celery Beat dynamic schedule updates
- Build natural language → cron converter
- Add API endpoint: `/api/tasks/schedule` for user commands
- **Cost impact:** Zero (no new API calls)

### Phase 3: Add ResultPresenter (Week 3)
- Create `emy/services/result_presenter.py`
- Build synthesis prompts (per agent type)
- Implement alert routing
- Add database logging of presented results
- **Cost impact:** Medium (uses Sonnet for synthesis)

### Phase 4: Integration & Testing (Week 4)
- Wire three components together
- Full end-to-end workflow testing
- User acceptance testing
- Deploy to Render

---

## Key Design Principles

### 1. **Non-Invasive**
- Specialist agents (TradingHoursMonitor, LogAnalysis, Profitability) remain **unchanged**
- They continue to work as-is, just scheduled differently
- New components sit *above* them in the stack

### 2. **Incremental**
- Each component can be tested independently
- You can deploy TaskInterpreter, then DynamicScheduler, then ResultPresenter
- No big-bang rewrite

### 3. **Vision-Aligned**
- Every component directly supports "AI Chief of Staff" vision
- Removes nothing; only adds orchestration intelligence
- User drives behavior through natural language, not code changes

### 4. **Cost-Conscious**
- TaskInterpreter: Haiku (cheap)
- DynamicScheduler: Zero API cost (local logic)
- ResultPresenter: Sonnet (only when synthesizing results)
- Total incremental cost: ~$0.50/day for typical usage

### 5. **Autonomous**
- Once scheduled, agents run without user intervention
- System intelligently synthesizes results
- Alerts only when critical (no noise)

---

## Data Model Changes

### New Table: `user_task_schedules`
```sql
CREATE TABLE user_task_schedules (
  id SERIAL PRIMARY KEY,
  user_id INTEGER,                    -- Who created this schedule
  command TEXT,                       -- Original user command
  intent_type VARCHAR(50),            -- "monitoring", "analysis", "optimization"
  agents TEXT[],                      -- Which agents to invoke
  cron_expression VARCHAR(100),       -- Celery cron format
  parameters JSONB,                   -- Extra params for agents
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  last_run_at TIMESTAMP,
  next_run_at TIMESTAMP
);
```

### Enhanced Table: `monitoring_reports`
Add columns:
- `presented_to_user BOOLEAN` — Has this result been shown to user?
- `user_summary TEXT` — Natural language version of report

---

## Success Criteria (Tomorrow's Plan Should Address)

✅ User can say "Monitor trading hours and alert me" (no config files)
✅ Emy parses intent correctly (evaluated against intent taxonomy)
✅ Schedules update dynamically (user changes frequency, schedule updates)
✅ Results are natural language (user reads summaries, not database queries)
✅ Multi-agent synthesis works (LogAnalysis + Profitability combined for recommendations)
✅ No specialist agent changes (backward compatible)
✅ Cost remains reasonable (~$1/day)

---

## Why This Approach Wins

| Aspect | Why This Works |
|--------|-----------------|
| **Vision Alignment** | Directly implements "AI Chief of Staff" concept |
| **Risk** | Low — no changes to working agents |
| **Time to Value** | Fast — each phase delivers capability in 1 week |
| **Scalability** | Easy to add new agents later (just teach TaskInterpreter about them) |
| **User Experience** | Natural language interface, no config changes |
| **Cost** | Minimal incremental cost (Haiku + Sonnet for synthesis only) |
| **Maintenance** | Clean separation: interpretation, scheduling, synthesis |

---

## Alternative Approaches (Considered & Rejected)

### ❌ Approach A: Build Custom NLP from Scratch
- Custom regex parsers, hardcoded intent matching
- **Why rejected:** Brittle, doesn't scale, reinvents the wheel

### ❌ Approach B: Complete Rewrite Using LangGraph State Machines
- Rearchitect entire system around state graphs
- **Why rejected:** High risk, long timeline, breaks working agents

### ❌ Approach C: Use External Workflow Engine (Temporal, Airflow)
- Delegate orchestration to external service
- **Why rejected:** Adds complexity, new platform to manage, cost

### ✅ Approach D: Hybrid Orchestration (RECOMMENDED)
- Add thin intelligence layer above existing agents
- **Why chosen:** Low risk, incremental, aligned with vision, leverages Claude

---

## Tomorrow's Planning Session

When we build the implementation plan tomorrow, ensure it covers:

1. **TaskInterpreter**
   - Intent taxonomy (all possible user commands)
   - Few-shot examples for each intent
   - Validation logic
   - Test cases

2. **DynamicScheduler**
   - Database schema for `user_task_schedules`
   - Cron expression builder from natural language
   - Celery Beat dynamic schedule update logic
   - API endpoint for scheduling new tasks

3. **ResultPresenter**
   - Synthesis prompts per agent type
   - Alert routing rules
   - Template system
   - Multi-agent synthesis logic

4. **Integration Points**
   - How chat interface routes to TaskInterpreter
   - How scheduled tasks invoke agents
   - How results flow to ResultPresenter
   - How user receives synthesized results

---

## Staying True to Vision

**Ibe's Vision for Emy:**
> An autonomous AI Chief of Staff that enables the user to delegate trading system monitoring and optimization through natural language commands, with Emy making intelligent decisions about what to do, when to do it, and how to communicate results.

**This transformation delivers exactly that:**
- ✅ Natural language interface (user speaks, Emy listens)
- ✅ Intelligent decision-making (TaskInterpreter reasons about intent)
- ✅ Autonomous execution (scheduled agents run without intervention)
- ✅ Clear communication (ResultPresenter synthesizes findings)
- ✅ Scalable architecture (easy to add new agents and capabilities)

**What we're NOT building:**
- ❌ Random features that don't fit the vision
- ❌ Complex infrastructure for its own sake
- ❌ Redundant pieces that duplicate existing functionality
- ❌ Anything that moves away from the "Chief of Staff" concept

---

## Next Steps

1. **Tonight:** Review this document, note questions
2. **Tomorrow:** Create detailed implementation plan using writing-plans skill
3. **This week:** Execute plan using subagent-driven-development skill
4. **By end of week:** Emy transitions from task scheduler to AI Chief of Staff

---

**Document prepared by:** Claude Code
**Status:** Ready for review & planning
**Last updated:** March 16, 2026, 11:47 AM EDT
