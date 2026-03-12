# Emy: OpenClaw Parity Design Document

**Date**: March 12, 2026
**Status**: Design Approved ✅
**Author**: Claude Code
**Scope**: Functional equivalence to OpenClaw AI agent framework

---

## Executive Summary

Build Emy to achieve **functional equivalence** with OpenClaw: autonomous, context-aware AI agent capable of executing complex multi-step tasks (job applications, trading, knowledge management) via browser automation and API integration. Unlike OpenClaw's multi-channel messaging approach, Emy uses a **web-first interface** (Gradio, REST API) with a **modular architecture** (Phase 1a Gateway + new Emy Brain).

---

## Design Decisions (Approved)

### 1. Scope: Functional Equivalence (Not Feature-For-Feature)
- **✅ Approved**: Emy should operate autonomously and take actions via APIs, not replicate OpenClaw's 25 messaging channels
- **Rationale**: Ibe's use cases (trading, job search, knowledge management) don't require WhatsApp/Slack integrations; web UI is sufficient
- **Implication**: Focus on capabilities (browser automation, multi-agent coordination) rather than channels

### 2. Autonomy Model: Hybrid (Request-Driven with Persistent Context)
- **✅ Approved**: Always-on context + request-driven execution + no background monitoring
- **Why not 24/7 monitoring?** Monitoring should be assignment-based, not proactive
- **Implication**: Emy activates only when user requests a workflow; persistent context survives across sessions

### 3. Priority Capabilities (Ranked)
- **🥇 Priority 1**: Browser automation (form filling, navigation, scraping) + Web UI (Gradio, REST)
- **🥈 Priority 2**: Multi-channel execution (coordinated trading, job search, knowledge agents)
- **🥉 Priority 3**: Voice interaction (deferred post-Phase 5)

**Why?** Job applications and trading require sophisticated browser automation; voice is nice-to-have.

### 4. Technical Architecture: Modular Hybrid
- **✅ Approved**: Keep Phase 1a lightweight; build new "Emy Brain" service for orchestration + automation
- **Phase 1a** (Existing): FastAPI gateway, SQLite database, Gradio UI, CLI
- **Emy Brain** (New): LangGraph orchestration, Playwright automation, Claude reasoning, persistent context
- **Communication**: REST + WebSocket for async task execution

**Why?** Separates concerns, allows independent scaling, avoids monolithic complexity.

### 5. Orchestration Framework: LangGraph + Playwright
- **✅ Approved**: LangGraph for agent workflows, Playwright for browser automation
- **LangGraph**: Multi-step state machines, agent routing, error handling, checkpoints
- **Playwright**: Headless Chrome automation, form filling, screenshots, element interaction
- **Claude**: Reasoning engine at each workflow step

**Why?** LangGraph is production-grade for multi-agent orchestration; Playwright is industry-standard for browser automation.

---

## System Architecture

### Overall Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  ┌──────────────────┬──────────────────┬──────────────────┐ │
│  │   Gradio Web UI  │   FastAPI Docs   │   CLI (Rich)     │ │
│  └──────────┬───────┴────────┬─────────┴────────┬─────────┘ │
└─────────────┼────────────────┼──────────────────┼────────────┘
              │                │                  │
┌─────────────┴────────────────┴──────────────────┴────────────┐
│         Phase 1a: API Gateway (Lightweight)                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FastAPI + SQLite Database + Authentication Layer    │   │
│  │  - Workflow creation & status tracking               │   │
│  │  - Agent health monitoring                           │   │
│  │  - Results storage & retrieval                       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────┬────────────────────────────────────────────────┘
              │
              ↓ (WebSocket/REST)
┌─────────────────────────────────────────────────────────────┐
│     Emy Brain: Orchestration & Execution Engine (NEW)       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LangGraph Orchestration + Playwright Automation     │   │
│  │  - Multi-agent task workflows                        │   │
│  │  - Browser automation (form filling, navigation)     │   │
│  │  - Persistent context & memory                       │   │
│  │  - Task state management & resumption               │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌─────────────┬──────────────┬──────────────┬──────────┐   │
│  │ Knowledge   │ Trading      │ Job Search   │ Project  │   │
│  │ Agent       │ Agent        │ Agent        │ Monitor  │   │
│  │ (Claude +   │ (OANDA API   │ (LinkedIn,   │ Agent    │   │
│  │ Memory)     │ + analysis)  │ Indeed APIs) │ (GitHub) │   │
│  └─────────────┴──────────────┴──────────────┴──────────┘   │
│                          ↓                                   │
│  ┌─────────────┬──────────────┬──────────────┬──────────┐   │
│  │ Playwright  │ Claude API   │ External     │ Context  │   │
│  │ Browser     │ Integration  │ APIs         │ Memory   │   │
│  │ (Chrome)    │ (Reasoning)  │ (OANDA, Job │ (SQLite) │   │
│  │             │              │ Boards)      │          │   │
│  └─────────────┴──────────────┴──────────────┴──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Emy Brain Internal Architecture

**LangGraph State Management:**

```python
@dataclass
class WorkflowState:
    # Input/Output
    user_request: dict
    workflow_type: str

    # Execution Context
    current_agent: str
    step_count: int

    # Shared Memory (persists across agent switches)
    context: dict  # Job details, market data, etc.
    execution_history: list  # What's been done

    # Results
    final_result: dict
    status: str  # "running", "complete", "error"
    error: Optional[str]

    # For resumption (if paused)
    checkpoint: dict  # Can pause and resume long tasks
```

**Agent Execution Loop (per agent, managed by LangGraph):**

```
1. Agent receives WorkflowState
2. Claude evaluates: "What should I do next?"
3. Options:
   - Execute browser action (Playwright)
   - Call external API (OANDA, LinkedIn)
   - Switch to another agent (hand-off)
   - Complete task
   - Error/ask for help
4. Execute action, update WorkflowState
5. Loop until "complete" or "error"
```

---

## Agent Specifications

### Core Agents

| Agent | Role | Key Capabilities | Examples |
|-------|------|---|---|
| **RouterAgent** | Request classification & delegation | Claude-based routing, workflow type detection | Determines which agent(s) to activate |
| **JobSearchAgent** | Autonomous job discovery & application | LinkedIn/Indeed automation, form filling, resume tailoring | Apply to jobs, customize applications |
| **TradingAgent** | Market analysis & trade execution | OANDA integration, technical analysis, risk management | Execute trades, monitor positions, manage SL/TP |
| **KnowledgeAgent** | Information synthesis & storage | Claude reasoning, Obsidian updates, Git commits | Answer questions, update knowledge base, write cover letters |
| **ProjectMonitorAgent** | Task & deadline tracking | GitHub API, status synthesis, alerts | Monitor repos, flag issues, suggest next steps |

### Supporting Components

| Component | Responsibility |
|---|---|
| **BrowserController** | Manages Playwright instances, screenshots, element interaction, error recovery |
| **MemoryStore** | SQLite interface for persistent context, workflow history, decisions |
| **SkillExecutor** | Runs 11+ existing skills (OANDA, job APIs, Git, etc.) |
| **ErrorHandler** | Retry logic, escalation, checkpoint management |

---

## Data Flow: Request to Result

**Complete workflow example: Job application**

```
1. User: "Apply to 10 jobs matching my criteria"
   ↓
2. Phase 1a: Creates Workflow(type="job_search", input={...})
   ↓
3. Emy Brain: Receives request, initializes WorkflowState
   ↓
4. RouterAgent: "This is job_search → use JobSearchAgent"
   ↓
5. JobSearchAgent Loop:
   - Claude: "What should I do?" → "Browse LinkedIn for jobs"
   - Playwright: Launch browser, search, scrape job listings
   - Claude: "Evaluate first job. Match?" → "Yes, apply"
   - Playwright: Click job, screenshot, parse description
   - KnowledgeAgent: "Write cover letter for this job"
   - Playwright: Fill form, paste letter, submit
   - Loop: Repeat for next job
   - Claude: "10 jobs done?" → "Yes, complete"
   ↓
6. Emy Brain: Save result to SQLite
   ↓
7. Phase 1a: Return result to user
   ↓
8. Gradio UI: "✅ Applied to 10 jobs"
```

---

## External Integrations

| API | Used By | Purpose |
|---|---|---|
| **OANDA** | TradingAgent | Trade execution, position tracking, P&L |
| **LinkedIn** | JobSearchAgent | Job search, application submission |
| **Indeed** | JobSearchAgent | Job search, data extraction |
| **GitHub** | ProjectMonitorAgent | Repo activity, PR/issue tracking |
| **Claude** | All Agents | Reasoning, decision-making at each step |
| **Obsidian Git** | KnowledgeAgent | Knowledge storage, version control |

---

## Error Handling & Resumption

**Example: CAPTCHA during job application**

```
1. Playwright encounters CAPTCHA
2. Agent calls Claude: "I can't proceed. What should I do?"
3. Claude: "Request user intervention" or "Skip this job"
4. Error logged with checkpoint (state before CAPTCHA)
5. Workflow status = "paused_on_error"
6. Gradio UI: "⚠️ CAPTCHA encountered. Retry? (Skip/Manual)"
7. User action triggers resumption from checkpoint
8. Brain resumes from exact step, no re-execution
```

---

## Implementation Phasing

### Phase 1b (Current: Mar 12-18) ✅ Existing Plan
- Claude API integration with stub agents
- Real workflow execution via Phase 1a API
- **Duration**: 1 week
- **Deliverable**: Phase 1a with live Claude integration

### Phase 2 (Mar 19-25): Emy Brain Foundation
- LangGraph framework setup
- Router Agent implementation
- BrowserController (Playwright management)
- MemoryStore (SQLite context)
- Deploy Emy Brain service to Render
- **Duration**: 1 week
- **Deliverable**: Basic orchestration working

### Phase 3 (Mar 26-Apr 1): JobSearchAgent
- LinkedIn + Indeed integration
- Browser automation (search, navigate, fill forms)
- Claude-based decision-making
- Tests & documentation
- **Duration**: 1 week
- **Deliverable**: Autonomous job applications working

### Phase 4 (Apr 2-8): TradingAgent + Multi-Agent Coordination
- Enhanced TradingAgent (real OANDA trading)
- KnowledgeAgent improvements (Obsidian integration)
- Multi-agent hand-offs (job search + knowledge)
- **Duration**: 1 week
- **Deliverable**: Coordinated workflows working

### Phase 5 (Apr 9-15): Production Hardening
- Error handling, retries, checkpoints
- Workflow resumption logic
- Monitoring, logging, performance optimization
- **Duration**: 1 week
- **Deliverable**: Production-ready Emy Brain

### Post-Phase 5 (Deferred)
- Voice integration (wake words, voice commands)
- Additional messaging integrations if needed
- Advanced features (multi-day workflows, etc.)

---

## Success Criteria

**Phase 1b Complete (Mar 18):**
- ✅ Claude API integrated with all agents
- ✅ Real workflow outputs stored in database
- ✅ Gradio UI shows live responses

**Phase 2 Complete (Mar 25):**
- ✅ Emy Brain service deployed to Render
- ✅ Router Agent correctly classifies requests
- ✅ LangGraph state management working

**Phase 3 Complete (Apr 1):**
- ✅ JobSearchAgent can browse and apply to jobs
- ✅ Handles forms, screenshots, text input
- ✅ Integrates with LinkedIn/Indeed APIs
- ✅ 80%+ success rate on simple job applications

**Phase 4 Complete (Apr 8):**
- ✅ TradingAgent executes real trades
- ✅ Multi-agent coordination working (job search + knowledge)
- ✅ All agents responding to requests autonomously

**Phase 5 Complete (Apr 15):**
- ✅ Error recovery and resumption working
- ✅ Long-running workflows (1+ hour) complete without intervention
- ✅ All logging and monitoring in place
- **✅ Emy has OpenClaw parity**: Autonomous, context-aware, multi-agent orchestration

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Playwright instability on Render | High | Test early (Phase 2), use managed headless Chrome service if needed |
| CAPTCHA blocking job applications | Medium | Manual intervention or skip logic; explore CAPTCHA-solving services |
| LangGraph complexity | Medium | Use simplified patterns first; iterate to more complex workflows |
| Claude API costs | Low-Medium | Budget tracking, cost alerts, monthly limits |
| Phase timeline slip | Medium | TDD-driven development, early testing, weekly checkpoints |

---

## Dependencies & Prerequisites

- ✅ Phase 1a deployed and working
- ✅ ANTHROPIC_API_KEY configured
- ✅ OANDA account and credentials
- ✅ Render account with sufficient resources
- ✅ LangGraph and Playwright libraries available

---

## Next Steps

1. **Validate this design**: User approval (DONE ✅)
2. **Create implementation plan**: Invoke writing-plans skill
3. **Execute Phase 1b**: Claude API integration (1 week)
4. **Checkpoint & review**: Before Phase 2
5. **Continue phases 2-5**: Weekly increments

---

## Document Metadata

- **Created**: 2026-03-12
- **Last Updated**: 2026-03-12
- **Status**: Design Approved by User
- **Next Review**: After Phase 1b completion (Mar 18)
