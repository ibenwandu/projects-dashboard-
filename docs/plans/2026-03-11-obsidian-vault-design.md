# Obsidian Vault Design: Mission-Centric Knowledge System
**Date**: March 11, 2026
**Status**: Approved
**Scope**: Entire personal folder integrated into unified knowledge universe

---

## 🎯 Vision & Purpose

**Mission**: Building a 24/7 autonomous organization that brings value and financial rewards

The Obsidian vault becomes a **command center** that:
- Tracks progress of all projects toward the vision
- Prioritizes work (what to do next and why)
- Evaluates ideas (what to start, what to drop)
- Captures learnings from trading sessions and their impact
- Integrates the entire personal folder for unified reference

---

## 📊 Core Priorities the Vault Solves

1. **Where am I on each project toward the vision?**
   - Dashboard overview + individual project notes

2. **Which task should I work on next and why?**
   - Dashboard task prioritization + project roadmaps

3. **Which new ideas should I initiate and which old ones should I drop?**
   - Idea Backlog with evaluation criteria + research findings

4. **What did I learn from the last trading session and how does it change my approach?**
   - Trading Journal + impact analysis on projects

---

## 🏗️ Vault Architecture

### **Component 1: Dashboard (Master Command Center)**

**File**: `00-DASHBOARD.md`

Single master page showing:
- **Vision statement** (always visible at top)
- **Active Projects table** with status indicators
  - Format: Project name | Current phase | Status (🟢/🟡/🔴) | Next milestone | Link
  - Projects: Trade-Alerts, Scalp-Engine, Job-Search, Currency Tracker, Recruiter Email Automation
- **Quick links** to:
  - Top priority task for this week
  - Latest trading journal entry
  - Idea Backlog (for evaluation decisions)
  - Recent key learnings
- **Key metrics** (high-level progress toward 24/7 autonomy)
  - e.g., "Trade-Alerts: Phase 1 of 4 (SL/TP verification)"

**Purpose**: Open vault → immediate clarity on status and priorities

---

### **Component 2: Projects Section**

**Structure**: `/Projects/{ProjectName}.md`

Each project note contains:

```markdown
# [Project Name]

## Vision Alignment
How this project serves: "24/7 autonomous organization that brings value"
Example: "Trade-Alerts provides 24/7 autonomous trading with AI analysis"

## Current Status
- Phase: [Ideation | Development | Testing | Production | Paused]
- Last updated: [date]

## Key Metrics / Success Criteria
What success looks like for this project
Example: "95% trades with SL, 95% with TP, ≥90% close at TP/SL"

## Current Blockers
What's preventing progress right now

## Active Tasks
Links to [[Task: ...]] related to this project

## Related Learning
Links to [[Trading Journal: ...]] entries relevant to this project

## Next Milestone
Immediate next target (1-2 weeks out)

## Progress Notes
Brief updates as project evolves
```

**Projects to create**:
- Trade-Alerts
- Scalp-Engine
- Job-Search
- Currency Trend Tracker
- Recruiter Email Automation

---

### **Component 3: Trading Journal**

**Structure**: `/Trading-Journal/{Date-Range}.md`

Dated session entries after each significant trading period:

```markdown
# Trading Session: [Start Date] - [End Date]

## Session Overview
- Duration: X hours/days
- Market conditions: [summary]
- System mode: [AUTO/SEMI_AUTO/MONITOR]

## What Happened
- Summary of trades executed
- Key statistics (# trades, P&L, win rate)
- Notable patterns or anomalies

## What Worked
- Specific successes
- Strategies that performed well
- System behaviors that were correct

## What Failed
- Problems encountered
- Edge cases or exceptions
- Unexpected behaviors
- System errors or gaps

## Root Cause Analysis
Why did failures happen?
- System issue?
- Market condition?
- Logic error?

## Hypothesis
What I think needs to change

## Changes for Next Time
Specific updates to:
- [[Trade-Alerts]] strategy or code
- [[Scalp-Engine]] execution logic
- Risk management approach
- Monitoring or analysis

## Impact
Which project(s) does this affect?
How will the next phase change based on these learnings?

## Links
- [[Project: Trade-Alerts]]
- [[Project: Scalp-Engine]]
- Raw logs: `/c/Users/user/Desktop/Test/Manual logs/`
```

**Purpose**: Capture learning in context, create audit trail of evolution, reference past decisions

---

### **Component 4: Idea Backlog**

**File**: `/Ideas/00-IDEA-BACKLOG.md`

Central evaluation database for all ideas:

```markdown
# Idea Backlog

## Scoring Criteria

Each idea is evaluated on:
- **Vision Alignment** (1-10): How directly serves 24/7 autonomous org?
- **Effort** (Low/Medium/High): Dev/implementation cost
- **ROI** (1-10): Financial or strategic return
- **Dependencies**: What must happen first?
- **Status**: New | Researched | Ready | Active | Paused | Dropped
- **Research**: Links to supporting research findings

## Ideas

### [Idea Name]
| Metric | Score | Notes |
|--------|-------|-------|
| Vision Alignment | 8 | Directly supports autonomous trading |
| Effort | High | Requires 3-4 weeks dev |
| ROI | 7 | Potential 2x revenue increase |
| Dependencies | Trade-Alerts Phase 2 | Must complete SL/TP verification first |
| Status | Researched | Research findings in [[Research Log: Currency Tracker]] |
| Decision | TBD | Pending evaluation |

### Current Ideas
- Currency Trend Tracker (Pending research)
- Recruiter Email Automation (Pending research)
- [New ideas as research discovers them]

## Research Agent Input
Research findings automatically added here with initial scores
Format: "Research finding: [description] → Suggested backlog entry"
```

**Purpose**:
- Single source of truth for all ideas
- Clear evaluation criteria prevent "shiny object" syndrome
- Visible decision trail (why you started/dropped something)

---

### **Component 5: Research Log**

**Structure**: `/Research/{Topic}-{Date}.md`

Captures research findings that feed into Idea Backlog:

```markdown
# Research: [Topic]
**Date**: [date]
**Conducted by**: Research agent
**Related to**: [[Idea: Currency Trend Tracker]] or [[Project: Trade-Alerts]]

## Findings
[Research findings, opportunities, data]

## Potential Ideas
- Idea 1 [score: vision 7, effort medium, ROI 8]
- Idea 2 [score: vision 9, effort high, ROI 6]

## Recommended Actions
1. Add Idea 1 to [[00-IDEA-BACKLOG]]
2. Flag for evaluation in next review
3. Blocking dependencies: [list any]

## Links
- [[Project: ...]]
- [[Idea: ...]]
```

**Purpose**: Continuous discovery, feeds directly to Idea Backlog evaluation

---

## 🔄 Information Flow

```
Your Work & Decisions
    ↓
Dashboard (Status at a glance)
    ├→ Projects (Each initiative's state)
    │   ├→ Tasks (What to do next)
    │   └→ Links to relevant learnings
    ├→ Trading Journal (Session → Insights)
    │   └→ Informs Trade-Alerts/Scalp-Engine updates
    ├→ Idea Backlog (New opportunities)
    │   ├─← Research Agent (Continuous input)
    │   └→ Go/No-go decisions
    └→ Research Log (Discovery & findings)

External Integration
    ↓
Entire personal folder accessible via wiki-links
- CLAUDE_SESSION_LOG.md
- COMPREHENSIVE_SYSTEM_UNDERSTANDING.md
- Code documentation
- Commit history
```

---

## 📝 Content Organization

```
My Knowledge Base/
├─ 00-DASHBOARD.md              [Master command center]
├─ Projects/
│  ├─ Trade-Alerts.md
│  ├─ Scalp-Engine.md
│  ├─ Job-Search.md
│  ├─ Currency-Trend-Tracker.md
│  └─ Recruiter-Email-Automation.md
├─ Trading-Journal/
│  ├─ 2026-03-09_to_2026-03-11.md [Phase 1 Testing]
│  └─ [Future sessions...]
├─ Ideas/
│  ├─ 00-IDEA-BACKLOG.md
│  └─ Archive/
│     └─ [Dropped ideas with reasoning]
├─ Research/
│  ├─ Currency-Markets-2026-03-11.md
│  └─ [Other research topics...]
└─ [Existing folders: Tax/Benefits, Attachments, Personal, etc.]
```

---

## 🎯 Success Criteria

The vault is working when:
1. ✅ Opening dashboard gives you immediate project status in <10 seconds
2. ✅ You know your top 3 priorities for the week without hunting
3. ✅ Trading session learnings directly inform your next project updates
4. ✅ Idea evaluation is consistent (criteria-based, not impulse)
5. ✅ You can reference past decisions and learnings easily
6. ✅ Research findings automatically feed into evaluation pipeline
7. ✅ The entire personal folder is wiki-linked and discoverable

---

## 🔄 Maintenance & Review

- **Weekly**: Update dashboard with latest project status
- **After each trading session**: Create journal entry within 24 hours
- **Bi-weekly**: Review idea backlog, evaluate research findings
- **Monthly**: Assess progress toward vision, decide which ideas to activate
- **As needed**: Drop ideas with documented reasoning, update decision log

---

## 📊 Relationship to Personal Folder

The vault does NOT duplicate your existing work:
- CLAUDE_SESSION_LOG.md remains the session record (vault links to it)
- COMPREHENSIVE_SYSTEM_UNDERSTANDING.md remains the architecture doc (vault links to it)
- Code and projects remain in their folders (vault references them)
- Vault becomes the **navigation and insight layer** on top of your existing work

---

## Next Steps

1. Create vault structure with folders and stub files
2. Populate dashboard with current projects
3. Create project notes for all active initiatives
4. Backfill first trading journal entry (Phase 1 Mar 9-11)
5. Migrate existing ideas to Idea Backlog with evaluation
6. Set up research agent integration
7. Establish weekly review cadence
