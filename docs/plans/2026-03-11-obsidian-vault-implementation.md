# Obsidian Vault Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with code review.

**Goal:** Build a mission-centric Obsidian vault that integrates all projects, trades, ideas, and learnings into a unified command center for your 24/7 autonomous organization vision.

**Architecture:** The vault is structured as a central dashboard linking to project notes, trading journals, idea backlog, and research logs. All components reference back to the original personal folder files via wiki-links, creating a navigation and insight layer without duplicating work.

**Tech Stack:** Obsidian (markdown-based), wiki-links for internal navigation, Markdown formatting

**Design Reference:** `docs/plans/2026-03-11-obsidian-vault-design.md`

---

## Phase 1: Folder Structure & Dashboard

### Task 1: Create core vault folders

**Files:**
- Create: `Obsidian Vault/My Knowledge Base/Projects/.gitkeep`
- Create: `Obsidian Vault/My Knowledge Base/Trading-Journal/.gitkeep`
- Create: `Obsidian Vault/My Knowledge Base/Ideas/.gitkeep`
- Create: `Obsidian Vault/My Knowledge Base/Ideas/Archive/.gitkeep`
- Create: `Obsidian Vault/My Knowledge Base/Research/.gitkeep`

**Step 1: Create directories**

```bash
mkdir -p "Obsidian Vault/My Knowledge Base/Projects"
mkdir -p "Obsidian Vault/My Knowledge Base/Trading-Journal"
mkdir -p "Obsidian Vault/My Knowledge Base/Ideas/Archive"
mkdir -p "Obsidian Vault/My Knowledge Base/Research"
```

**Step 2: Add .gitkeep files to preserve empty directories**

```bash
touch "Obsidian Vault/My Knowledge Base/Projects/.gitkeep"
touch "Obsidian Vault/My Knowledge Base/Trading-Journal/.gitkeep"
touch "Obsidian Vault/My Knowledge Base/Ideas/.gitkeep"
touch "Obsidian Vault/My Knowledge Base/Ideas/Archive/.gitkeep"
touch "Obsidian Vault/My Knowledge Base/Research/.gitkeep"
```

**Step 3: Verify structure**

```bash
tree "Obsidian Vault/My Knowledge Base" -L 2
```

Expected output shows Projects, Trading-Journal, Ideas, Research folders created.

**Step 4: Commit**

```bash
git add "Obsidian Vault/My Knowledge Base/*/.gitkeep"
git commit -m "feat: create core vault folder structure

Create Projects, Trading-Journal, Ideas, and Research folders
to organize all vault components"
```

---

### Task 2: Create Master Dashboard

**Files:**
- Create: `Obsidian Vault/My Knowledge Base/00-DASHBOARD.md`

**Step 1: Write the dashboard file**

Create `Obsidian Vault/My Knowledge Base/00-DASHBOARD.md`:

```markdown
# 🎯 Mission Control Dashboard

## Your Vision
**Building a 24/7 autonomous organization that brings value and financial rewards**

---

## 📊 Active Projects Status

| Project | Phase | Status | Next Milestone | Progress |
|---------|-------|--------|-----------------|----------|
| [[Trade-Alerts]] | Phase 1: SL/TP Verification | 🟡 Testing | Complete log review & analysis | 48+ hrs testing done |
| [[Scalp-Engine]] | Supporting Trade-Alerts | 🟡 Testing | Pass Phase 1, enable Phase 2 | Running on Render |
| [[Job-Search]] | Automation | 🟢 Paused | Disabled to save API credits | Enabled when needed |
| [[Currency-Trend-Tracker]] | Ideation | 🟡 Pending Research | Complete research & backlog entry | Pending evaluation |
| [[Recruiter-Email-Automation]] | Ideation | 🟡 Pending Research | Complete research & backlog entry | Pending evaluation |

🟢 = On track | 🟡 = At risk / Awaiting decision | 🔴 = Blocked

---

## 🎯 This Week's Priorities

1. **[URGENT]** [[Task: Review Phase 1 SL/TP Logs]] - Trade-Alerts Phase 1 completion
2. **[HIGH]** Evaluate [[Ideas]] - Decide on Currency Tracker & Recruiter Email Automation
3. **[MEDIUM]** Update project notes with latest status

---

## 🚀 Quick Links

**Latest Trading Session:**
- [[Trading Session: 2026-03-09 to 2026-03-11 Phase 1 Testing]]

**Idea Evaluation:**
- [[00-IDEA-BACKLOG]]

**Recent Research:**
- Check [[Research/]] for new findings

**Personal Folder Integration:**
- [[CLAUDE_SESSION_LOG.md]] - Session documentation
- [[COMPREHENSIVE_SYSTEM_UNDERSTANDING.md]] - System architecture
- [[TRADING_SYSTEM_IMPROVEMENT_PLAN.md]] - Improvement roadmap

---

## 📈 Key Metrics

**Toward 24/7 Autonomy:**
- Trade-Alerts: Phase 1 of 4 (SL/TP verification) ✓
- Scalp-Engine: Phase 1 of 4 (execution testing) ✓
- Job-Search: Ready (paused for credits)
- Autonomous income sources: 1/3 active

---

## Last Updated
2026-03-11 (Initial creation)

*Open projects or idea backlog below to explore in detail*
```

**Step 2: Verify file created**

```bash
test -f "Obsidian Vault/My Knowledge Base/00-DASHBOARD.md" && echo "Dashboard created successfully" || echo "Failed to create dashboard"
```

Expected: "Dashboard created successfully"

**Step 3: Commit**

```bash
git add "Obsidian Vault/My Knowledge Base/00-DASHBOARD.md"
git commit -m "feat: create master dashboard

Add command center dashboard showing:
- Vision statement
- All active projects with status
- This week's priorities
- Quick links to journals, backlog, research
- Key metrics toward 24/7 autonomy"
```

---

## Phase 2: Project Notes

### Task 3: Create Trade-Alerts project note

**Files:**
- Create: `Obsidian Vault/My Knowledge Base/Projects/Trade-Alerts.md`

**Step 1: Write Trade-Alerts project note**

Create `Obsidian Vault/My Knowledge Base/Projects/Trade-Alerts.md`:

```markdown
# 📊 Trade-Alerts Project

## Vision Alignment
Trade-Alerts is the **core 24/7 autonomous income generator** for your organization. LLM-based market analysis that feeds opportunities to Scalp-Engine for execution.

Serves mission: "24/7 autonomous organization" ✓

---

## Current Status
- **Phase**: Phase 1 - SL/TP Verification
- **Last Updated**: 2026-03-11
- **Environment**: Render (production)
- **Mode**: AUTO (continuous analysis)

---

## Key Metrics & Success Criteria

**Phase 1 Requirements:**
- ✅ ≥95% trades have Stop Loss defined
- ✅ ≥95% trades have Take Profit defined
- ✅ ≥90% trades close at TP/SL (not manual closure)
- ✅ 0 trades where loss > SL distance

**System Health:**
- OAuth2 credentials: ✓ Working (Trade-Alerts-OAuth app)
- LLM access: ✓ ChatGPT, Gemini, Claude, DeepSeek
- RL database: ✓ Located at `/var/data/trade_alerts_rl.db`
- Market state export: ✓ Writing to `market_state.json`

---

## Current Blockers
**URGENT**: Awaiting Phase 1 log review to verify SL/TP implementation is working.
- Logs location: `/c/Users/user/Desktop/Test/Manual logs/`
- Task: [[Task: Review Phase 1 SL/TP Logs]]

---

## Active Tasks
- [[Task: Review Phase 1 SL/TP Logs]] - URGENT, in progress

---

## Related Learning & Decisions
- [[Trading Session: 2026-03-09 to 2026-03-11 Phase 1 Testing]]
- Architecture reference: [[COMPREHENSIVE_SYSTEM_UNDERSTANDING.md]]
- Session log: [[CLAUDE_SESSION_LOG.md]]

---

## Next Milestone
**Complete Phase 1 analysis (This week)**
1. Review all logs from Mar 9-11
2. Verify each trade has SL/TP
3. Confirm P&L matches SL/TP logic
4. Pass/fail verdict
5. If PASS → Proceed to Phase 2 (investigate manual closures)
6. If FAIL → Debug SL/TP before live trading

---

## Progress Notes

### 2026-03-09: Phase 1 Testing Started
- Started 48+ hours continuous trading
- Both Trade-Alerts and Scalp-Engine operational on Render
- Logs backed up for analysis
- Created reminder task for log review

### 2026-03-11: Context Preparation
- Re-established system context
- Prepared for Phase 1 analysis
- Confirmed logs accessible

---

## Key Components
- **main.py** - Entry point, orchestrates LLM pipeline
- **src/drive_reader.py** - Google Drive integration
- **src/llm_analyzer.py** - Multi-LLM analysis
- **src/market_bridge.py** - Exports market_state.json for Scalp-Engine
- **src/trade_alerts_rl.py** - RL system for learning
- **.env** - Configuration with OAuth, API keys

---

## Links
- Project root: `C:\Users\user\projects\personal\Trade-Alerts`
- Design doc: [[2026-03-11-obsidian-vault-design.md]]
```

**Step 2: Verify file created**

```bash
test -f "Obsidian Vault/My Knowledge Base/Projects/Trade-Alerts.md" && echo "Trade-Alerts note created" || echo "Failed"
```

**Step 3: Commit**

```bash
git add "Obsidian Vault/My Knowledge Base/Projects/Trade-Alerts.md"
git commit -m "feat: create Trade-Alerts project note

Document Trade-Alerts vision, status, metrics, blockers, and next steps.
Establish Phase 1 verification as current blocker with task link."
```

---

### Task 4: Create Scalp-Engine project note

**Files:**
- Create: `Obsidian Vault/My Knowledge Base/Projects/Scalp-Engine.md`

**Step 1: Write Scalp-Engine project note**

Create `Obsidian Vault/My Knowledge Base/Projects/Scalp-Engine.md`:

```markdown
# 🤖 Scalp-Engine Project

## Vision Alignment
Scalp-Engine is the **execution engine** that transforms Trade-Alerts opportunities into real trades. Executes 24/7 via OANDA API with real-time risk management.

Serves mission: "24/7 autonomous organization" ✓

---

## Current Status
- **Phase**: Phase 1 - SL/TP Verification
- **Last Updated**: 2026-03-11
- **Environment**: Render (production)
- **Mode**: AUTO (continuous execution)
- **Dependency**: Reads [[Trade-Alerts]] market_state.json

---

## Key Metrics & Success Criteria

**Phase 1 Requirements (mirrored from Trade-Alerts):**
- ✅ ≥95% trades have Stop Loss defined
- ✅ ≥95% trades have Take Profit defined
- ✅ ≥90% trades close at TP/SL (not manual)
- ✅ 0 trades where loss > SL distance

**System Health:**
- OANDA API: ✓ Connected (demo account)
- Order placement: ✓ Working
- Risk management: ✓ Active
- DB schema: ✓ Fixed (pnl_pips column added by Cursor)

---

## Current Blockers
**URGENT**: Same as Trade-Alerts - awaiting Phase 1 log review to confirm SL/TP execution is working.
- Dependent on: [[Task: Review Phase 1 SL/TP Logs]]

---

## Active Tasks
- [[Task: Review Phase 1 SL/TP Logs]] - Blocks Scalp-Engine Phase 2

---

## Related Learning & Decisions
- [[Trading Session: 2026-03-09 to 2026-03-11 Phase 1 Testing]]
- Architecture reference: [[COMPREHENSIVE_SYSTEM_UNDERSTANDING.md]]

---

## Next Milestone
**Complete Phase 1 analysis (This week)**
1. Review all execution logs
2. Verify SL/TP enforcement at order level
3. Confirm OANDA feedback matches expected behavior
4. Pass/fail verdict
5. If PASS → Phase 2 (investigate why 80% manual closures)
6. If FAIL → Debug order placement or SL/TP logic

---

## Progress Notes

### 2026-03-09: Phase 1 Testing Started
- Operational and executing trades in AUTO mode
- Receiving opportunities from Trade-Alerts
- Trading actively on demo account

### Feb 20, 2026: Bug Fixes
- Fixed opportunity ID mismatch (max_runs blocking)
- Fixed stale execution records
- Fixed FT-DMI-EMA AUTO mode config

---

## Key Components
- **scalp_engine.py** - Main loop, opportunity scanning
- **auto_trader_core.py** - Order placement, position management, risk control
- **src/execution/execution_mode_enforcer.py** - Per-opportunity execution rules
- **src/scalping_rl_enhanced.py** - Enhanced RL system for learning
- **src/logger.py** - Logging to disk and console

---

## Links
- Project root: `C:\Users\user\projects\personal\Scalp-Engine`
- Parent: [[Trade-Alerts]] (depends on market_state.json)
- Design doc: [[2026-03-11-obsidian-vault-design.md]]
```

**Step 2: Verify file created**

```bash
test -f "Obsidian Vault/My Knowledge Base/Projects/Scalp-Engine.md" && echo "Scalp-Engine note created" || echo "Failed"
```

**Step 3: Commit**

```bash
git add "Obsidian Vault/My Knowledge Base/Projects/Scalp-Engine.md"
git commit -m "feat: create Scalp-Engine project note

Document Scalp-Engine vision, status, metrics, and dependency on Trade-Alerts.
Link to Phase 1 verification task."
```

---

### Task 5: Create Job-Search project note

**Files:**
- Create: `Obsidian Vault/My Knowledge Base/Projects/Job-Search.md`

**Step 1: Write Job-Search project note**

Create `Obsidian Vault/My Knowledge Base/Projects/Job-Search.md`:

```markdown
# 💼 Job-Search Project

## Vision Alignment
Job-Search automates the job application workflow to maintain income stability while building autonomous trading systems. Reduces manual effort while keeping opportunities visible.

Serves mission: "Diversified income toward 24/7 autonomy" ✓

---

## Current Status
- **Phase**: Production (Paused)
- **Last Updated**: 2026-03-11
- **Mode**: DISABLED (intentional)
- **Reason**: Paused to conserve API credits (Gmail, Claude, Gemini)

---

## Key Metrics

**Workflow:**
- Daily analysis of job alerts (when enabled)
- Resume customization for top 5 matches
- Scoring: 0-100 scale
- Target: Apply to 3-5 roles/week with high-quality materials

**Acceptance Criteria:**
- Jobs ranked by relevance to profile
- Custom resumes for top matches
- Application tracking log maintained

---

## Current Blockers
**None** - Project is intentionally paused to manage API costs. Can be re-enabled when needed.

---

## Active Tasks
**None** - Project paused

---

## Related Learning & Decisions
- Workflow documentation: [[../job-search/CLAUDE.md]]
- Session log: [[../job-search/CLAUDE_SESSION_LOG.md]]
- Decision: Paused 2026-02-27 to stop token drain

---

## Next Milestone
**Planned Re-enable: When needed**
1. Assess job market conditions
2. Determine API credit budget
3. Re-enable workflow
4. Run for 2-4 week intensive application cycle

---

## Progress Notes

### 2026-02-27: Workflow Paused
- User reported workflow was running and consuming credits unnecessarily
- Added disable guard: `.workflow_disabled` file stops all API calls
- Task Scheduler continues to fire but exits immediately
- Can be re-enabled by deleting `.workflow_disabled`

### Earlier: Production Phase
- System extracts job opportunities from Indeed alerts
- Scores and ranks them
- Customizes resumes for top 5
- Ready to apply with high-quality materials

---

## Key Components
- **daily_workflow.py** - Main orchestrator (disabled by default)
- **config/** - Profile, scoring criteria, resume template
- **extracted-jobs/** - Parsed job data
- **analysis/** - Rankings and match reports
- **customized-resumes/** - Generated resume variations

---

## Links
- Project root: `C:\Users\user\projects\personal\job-search`
- Workflow config: [[../job-search/CLAUDE.md]]
- Disable doc: [[../job-search/WORKFLOW_DISABLED.md]]
```

**Step 2: Verify file created**

```bash
test -f "Obsidian Vault/My Knowledge Base/Projects/Job-Search.md" && echo "Job-Search note created" || echo "Failed"
```

**Step 3: Commit**

```bash
git add "Obsidian Vault/My Knowledge Base/Projects/Job-Search.md"
git commit -m "feat: create Job-Search project note

Document job search automation project status, intentional pause decision,
and re-enablement criteria."
```

---

### Task 6: Create pending project stubs

**Files:**
- Create: `Obsidian Vault/My Knowledge Base/Projects/Currency-Trend-Tracker.md`
- Create: `Obsidian Vault/My Knowledge Base/Projects/Recruiter-Email-Automation.md`

**Step 1: Create Currency-Trend-Tracker.md**

```markdown
# 💱 Currency Trend Tracker

## Vision Alignment
Auto-discover and track trending currencies. Analyze news driving movements. Provides secondary autonomous income stream and market intelligence.

Serves mission: "24/7 autonomous organization" ✓

---

## Current Status
- **Phase**: Ideation / Pending Research
- **Status**: 🟡 Awaiting evaluation
- **Decision**: Pending [[00-IDEA-BACKLOG]] review

---

## Concept
1. **Discovery Phase**: Identify top 10 movers daily
2. **Tracking Phase**: Monitor for 7 days with news analysis
3. **Reset**: Archive and start new cycle

Uses Claude API for news analysis + Google Sheets for tracking.

---

## Links
- Design in vault: [[../../2025-12-16.md]]
- Idea backlog: [[../Ideas/00-IDEA-BACKLOG]]
```

**Step 2: Create Recruiter-Email-Automation.md**

```markdown
# ✉️ Recruiter Email Automation

## Vision Alignment
Auto-respond to recruiter emails with customized responses. Maintains 24/7 presence in job market without manual effort.

Serves mission: "24/7 autonomous organization" ✓

---

## Current Status
- **Phase**: Ideation / Pending Research
- **Status**: 🟡 Awaiting evaluation
- **Decision**: Pending [[00-IDEA-BACKLOG]] review

---

## Concept
**n8n workflow that:**
1. Searches Gmail for recruiter emails (daily)
2. Auto-generates professional responses + customized resume
3. Summarizes job site emails (Indeed, etc.)
4. Sends consolidated report by 7pm

Eliminates manual recruiter email triage.

---

## Links
- Design in vault: [[../../2025-12-14.md]]
- Idea backlog: [[../Ideas/00-IDEA-BACKLOG]]
```

**Step 3: Add both files**

```bash
git add "Obsidian Vault/My Knowledge Base/Projects/Currency-Trend-Tracker.md"
git add "Obsidian Vault/My Knowledge Base/Projects/Recruiter-Email-Automation.md"
git commit -m "feat: create pending project stubs

Add Currency-Trend-Tracker and Recruiter-Email-Automation as pending
projects awaiting idea backlog evaluation."
```

---

## Phase 3: Trading Journal

### Task 7: Create first trading session journal entry

**Files:**
- Create: `Obsidian Vault/My Knowledge Base/Trading-Journal/2026-03-09_to_2026-03-11_Phase1Testing.md`

**Step 1: Write trading session entry**

Create `Obsidian Vault/My Knowledge Base/Trading-Journal/2026-03-09_to_2026-03-11_Phase1Testing.md`:

```markdown
# Trading Session: Phase 1 SL/TP Verification
**Dates**: 2026-03-09 to 2026-03-11 (48+ hours)
**System**: Trade-Alerts + Scalp-Engine (Render production)
**Mode**: AUTO (continuous trading)

---

## Session Overview

**Duration**: 48+ hours continuous
**Market**: Forex (major pairs)
**System Status**: Both services operational
**Logging**: Full logs backed up to `/c/Users/user/Desktop/Test/Manual logs/`

---

## Objective
Verify that Stop Loss and Take Profit are correctly implemented in Scalp-Engine order placement and enforcement.

**Pass Criteria:**
- ✅ ≥95% trades have SL defined
- ✅ ≥95% trades have TP defined
- ✅ ≥90% trades close at TP/SL (not manual)
- ✅ 0 trades where loss exceeds SL distance

---

## What Happened
**Status**: AWAITING ANALYSIS

Logs are backed up and ready for review. Task: [[Task: Review Phase 1 SL/TP Logs]]

Log files to review:
- Scalp-Engine logs: `Scalp-Engine/logs/scalp_engine_*.log`
- OANDA transaction history: `Scalp-Engine/logs/oanda_*.log`
- Trade-Alerts analysis: `Trade-Alerts/logs/trade_alerts_*.log`

---

## What Worked
**Pending analysis**

---

## What Failed
**Pending analysis**

---

## Root Cause Analysis
**Pending analysis**

---

## Hypothesis for Next Phase
**Pending analysis**

---

## Changes for Next Phase
**To be determined after Phase 1 analysis**

Expected changes may include:
- Adjustments to SL/TP calculation if violations found
- Changes to order placement logic
- Strategy adjustments based on outcomes

---

## Impact on Projects
- **Trade-Alerts**: Phase 1 completion blocks Phase 2
- **Scalp-Engine**: Phase 1 completion blocks Phase 2
- **Next Focus**: Manual closure investigation (Phase 2)

---

## Links
- Project: [[../Projects/Trade-Alerts]]
- Project: [[../Projects/Scalp-Engine]]
- Dashboard: [[../00-DASHBOARD]]
- Log location: `/c/Users/user/Desktop/Test/Manual logs/`
- Session notes: [[../../CLAUDE_SESSION_LOG.md]]

---

## Status
🟡 **PENDING ANALYSIS** - Logs backed up, ready for review in next session
```

**Step 2: Verify file created**

```bash
test -f "Obsidian Vault/My Knowledge Base/Trading-Journal/2026-03-09_to_2026-03-11_Phase1Testing.md" && echo "Trading journal created" || echo "Failed"
```

**Step 3: Commit**

```bash
git add "Obsidian Vault/My Knowledge Base/Trading-Journal/2026-03-09_to_2026-03-11_Phase1Testing.md"
git commit -m "feat: create first trading journal entry

Add Phase 1 SL/TP Verification session entry. Session complete,
awaiting log analysis. Documents objective, pass criteria, and links
to projects."
```

---

## Phase 4: Idea Backlog

### Task 8: Create Idea Backlog

**Files:**
- Create: `Obsidian Vault/My Knowledge Base/Ideas/00-IDEA-BACKLOG.md`

**Step 1: Write Idea Backlog**

Create `Obsidian Vault/My Knowledge Base/Ideas/00-IDEA-BACKLOG.md`:

```markdown
# 💡 Idea Backlog

Central database for evaluating new ideas against the vision.

---

## Evaluation Criteria

Each idea is scored on a 1-10 scale:

| Metric | Question | High Score | Low Score |
|--------|----------|-----------|-----------|
| **Vision Alignment** | How directly does this serve "24/7 autonomous organization"? | 10 = Core to vision | 1 = Nice-to-have |
| **Effort** | How much development/implementation is needed? | Low = <1 week | High = >4 weeks |
| **ROI** | What's the financial or strategic return? | 10 = Significant $ or key blocker | 1 = Minimal impact |
| **Dependencies** | What must happen first? | None = Can start now | Multiple = Blocked |
| **Status** | Where is the idea in its lifecycle? | New | Active | Dropped |

---

## Current Ideas

### 1. Currency Trend Tracker
**Vision Alignment**: 8/10 — Direct autonomous income (like Trade-Alerts)
**Effort**: Medium (2-3 weeks)
**ROI**: 7/10 — Potential secondary income, market intelligence
**Dependencies**: Requires API (Claude or Perplexity), Google Sheets, Google Apps Script
**Status**: Researched (design in vault: [[../../2025-12-16.md]])

**Decision**: PENDING
- Waiting for evaluation decision
- Can be started anytime after Trade-Alerts Phase 1 completes
- Recommend: LOW priority (Trade-Alerts Phase 2 more critical)

**Links**: [[../Projects/Currency-Trend-Tracker]]

---

### 2. Recruiter Email Automation
**Vision Alignment**: 7/10 — 24/7 market presence without effort
**Effort**: Medium (2-3 weeks)
**ROI**: 6/10 — Reduces friction, maintains opportunity flow
**Dependencies**: Requires n8n account, Gmail API, Anthropic SDK
**Status**: Researched (design in vault: [[../../2025-12-14.md]])

**Decision**: PENDING
- Waiting for evaluation decision
- Can complement Job-Search if both enabled
- Recommend: MEDIUM priority (supportive to income stability)

**Links**: [[../Projects/Recruiter-Email-Automation]]

---

### 3. Enhanced Market Regime Detection
**Vision Alignment**: 9/10 — Directly improves win rate by avoiding trending markets
**Effort**: High (1-2 weeks core logic, testing)
**ROI**: 9/10 — Win rate improvement = direct P&L impact
**Dependencies**: Requires RL learning integration, historical analysis
**Status**: New (identified from Phase 1 analysis)

**Decision**: PENDING
- Recommended AFTER Phase 1 analysis completes
- Part of Phase 3 roadmap (win rate improvement)
- Blocking Trade-Alerts Phase 3 deployment

**Research Needed**: Historical patterns from demo account

---

## Archive

Ideas that were evaluated and rejected go here with reasoning.

*Currently empty - Archive builds as decisions are made*

---

## Guidelines

**When to INITIATE an idea:**
1. Vision alignment ≥7/10
2. ROI ≥6/10 (unless critical blocker)
3. No blocking dependencies OR dependencies near completion
4. Capacity available (other projects not in critical phase)

**When to DROP an idea:**
1. Vision alignment <5/10
2. ROI <4/10 (and not a strategic blocker)
3. Effort is unexpectedly high (>original estimate)
4. Better alternative exists
5. Dependencies will never be met

**Review Schedule:**
- Weekly: Check for new research findings
- Bi-weekly: Evaluate scoring of pending ideas
- Monthly: Make go/no-go decisions on pending ideas

---

## Links
- Dashboard: [[../00-DASHBOARD]]
- Trading Journal: [[../Trading-Journal/]]
- Research: [[../Research/]]
```

**Step 2: Verify file created**

```bash
test -f "Obsidian Vault/My Knowledge Base/Ideas/00-IDEA-BACKLOG.md" && echo "Idea backlog created" || echo "Failed"
```

**Step 3: Commit**

```bash
git add "Obsidian Vault/My Knowledge Base/Ideas/00-IDEA-BACKLOG.md"
git commit -m "feat: create idea backlog with evaluation criteria

Establish centralized idea evaluation system with scoring matrix.
Populate with three current ideas: Currency Tracker, Recruiter Email
Automation, Market Regime Detection. Set up decision guidelines."
```

---

## Phase 5: Research Log Template

### Task 9: Create Research folder structure and template

**Files:**
- Create: `Obsidian Vault/My Knowledge Base/Research/README.md`

**Step 1: Write Research README**

Create `Obsidian Vault/My Knowledge Base/Research/README.md`:

```markdown
# 🔬 Research Log

This folder contains research findings and discovery that feed into the [[00-IDEA-BACKLOG]].

---

## How Research Flows Into Ideas

1. **Research Agent discovers opportunities** → Creates dated research entry
2. **Entry includes preliminary scoring** → Idea backlog candidate
3. **You review & evaluate** → Make go/no-go decision
4. **Decision documented** → Backlog updated + linked to research

---

## Research File Format

```markdown
# Research: [Topic]
**Date**: YYYY-MM-DD
**Conducted by**: [Research Agent | Manual investigation]
**Related to**: [[Currency-Trend-Tracker]] or [[Trade-Alerts]]

## Key Findings
- Finding 1
- Finding 2

## Potential Ideas / Opportunities
- Idea 1 (preliminary scores: Vision 7, Effort Medium, ROI 8)
- Idea 2 (preliminary scores: Vision 6, Effort Low, ROI 5)

## Recommended Actions
1. Add Idea X to [[00-IDEA-BACKLOG]]
2. Flag for next decision review
3. Blockers: [list if any]

## Links
- [[Project: ...]]
- [[Idea: ...]]
```

---

## Research Archive

Completed research entries go here after decision is made.

---

## Next Research Topics

- [ ] Currency market opportunities (for Currency Tracker evaluation)
- [ ] Email automation tools comparison (for Recruiter Email Automation)
- [ ] Historical trading pattern analysis (for Market Regime Detection)
- [ ] API costs analysis (Claude vs Perplexity vs others)
```

**Step 2: Verify file created**

```bash
test -f "Obsidian Vault/My Knowledge Base/Research/README.md" && echo "Research README created" || echo "Failed"
```

**Step 3: Commit**

```bash
git add "Obsidian Vault/My Knowledge Base/Research/README.md"
git commit -m "feat: create research log structure and guidelines

Establish research folder with README explaining how findings
flow into idea backlog evaluation."
```

---

## Phase 6: Integration & Final Tasks

### Task 10: Update existing vault notes with wiki-links

**Files:**
- Modify: `Obsidian Vault/My Knowledge Base/AI tools.md`
- Modify: `Obsidian Vault/My Knowledge Base/A&M.md`

**Step 1: Update AI tools.md**

Edit `Obsidian Vault/My Knowledge Base/AI tools.md` to:

```markdown
# 🤖 AI Tools

This is a reference page for AI tools used across projects.

## Trade-Alerts LLMs
- **ChatGPT**: Primary analysis, fast response
- **Gemini**: Secondary analysis, validation
- **Claude**: Synthesis analysis, decision making
- **DeepSeek**: Emerging analysis (parser work in progress)

See: [[Trade-Alerts]]

## Job-Search Analysis
- **Claude**: Resume customization, match scoring
- **Gemini**: Job description analysis

See: [[Job-Search]]

## Currency Tracker Analysis
- **Claude**: News analysis, correlation detection
- **Perplexity**: Web search for currency news

See: [[Currency-Trend-Tracker]]
```

**Step 2: Update A&M.md**

Edit `Obsidian Vault/My Knowledge Base/A&M.md` to:

```markdown
# A&M

Reference for Analysts & Management projects (payslips, employment records).

See: [[Tax, Investments & Benefits/Tax documents.md]]
```

**Step 3: Commit**

```bash
git add "Obsidian Vault/My Knowledge Base/AI tools.md"
git add "Obsidian Vault/My Knowledge Base/A&M.md"
git commit -m "feat: populate AI tools and A&M notes with project links

Add wiki-links connecting reference notes to active projects
and personal folders."
```

---

### Task 11: Create .gitignore for Obsidian config

**Files:**
- Create: `Obsidian Vault/.gitignore`

**Step 1: Write gitignore**

Create `Obsidian Vault/.gitignore`:

```
.obsidian/cache/
.obsidian/plugins/
.DS_Store
*.swp
```

**Step 2: Verify and commit**

```bash
git add "Obsidian Vault/.gitignore"
git commit -m "chore: add gitignore for Obsidian cache files

Exclude Obsidian cache and plugin folders from version control"
```

---

### Task 12: Verify complete vault structure

**Step 1: List complete structure**

```bash
tree "Obsidian Vault/My Knowledge Base" -L 3 --dirsfirst
```

Expected output shows:
- `00-DASHBOARD.md`
- `Projects/` with 5 project notes
- `Trading-Journal/` with 1 session entry
- `Ideas/` with backlog and archive folder
- `Research/` with README
- Original folders: `Attachments/`, `Tax, Investments & Benefits/`, `Personal/`, etc.

**Step 2: Final commit with summary**

```bash
git add "Obsidian Vault/My Knowledge Base"
git commit -m "build: complete Obsidian vault structure for mission control

Vault now provides command center for 24/7 autonomous organization:
- Dashboard (project status overview)
- Projects (Trade-Alerts, Scalp-Engine, Job-Search, pending ideas)
- Trading Journal (session learning capture)
- Idea Backlog (evaluation with criteria)
- Research (discovery feed)

All components interconnected via wiki-links. Ready for weekly reviews
and decision-making on project prioritization and idea evaluation."
```

**Step 3: Verify git log**

```bash
git log --oneline | head -15
```

Expected: See commits for dashboard, projects, journal, backlog, research structure.

---

## Implementation Complete

All vault components are created and interconnected. The vault is ready to serve as your command center for the 24/7 autonomous organization vision.

**Next**: Open vault in Obsidian app and customize as needed.
