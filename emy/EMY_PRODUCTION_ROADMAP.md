# 🚀 Emy Production Roadmap (Phase 3+)

**Status**: ✅ **PRODUCTION LIVE** (March 15, 2026)

**Architecture**: Two-service Render deployment (Gateway + Brain)

**Vision**: Autonomous 24/7 AI Chief of Staff with real-time dashboards, multi-agent orchestration, and intelligent automation

---

## Current Production Status (Phase 3 Week 3)

### ✅ What's Live
- **Gateway Service**: https://emy-phase1a.onrender.com (FastAPI, REST endpoints)
- **Brain Service**: https://emy-brain.onrender.com (LangGraph, job orchestration)
- **3 Active Agents**: TradingAgent, ResearchAgent, KnowledgeAgent
- **Real-time Features**: WebSocket updates, checkpoint job resumption, rate limiting
- **Database**: SQLite persistence on /data mounts (2GB each)
- **Budget Control**: $10/day Claude API limit active
- **Documentation**: PRODUCTION_DEPLOYMENT.md, EMY_OPERATIONS_MANUAL.md, EMY_QUICK_REFERENCE.md

### 🟢 All Tests Passing
- 40/40 integration tests (Week 3 completion)
- End-to-end workflow execution verified
- All 3 agents health-checked and operational
- Database persistence verified
- Rate limiting active (100 req/min per IP)

---

## Production Week Development Roadmap

### 🎯 Priority 1: Emy Dashboard UI (Weeks 1-2 of next cycle)

**Objective**: Replace JSON API outputs with interactive dashboard (similar to mission_control_interactive.html)

**Design Reference**: `mission_control_interactive.html`
- Dark theme with CSS custom properties (--bg, --surface, --green, --amber, --blue, --red, --text, --muted)
- Real-time metrics cards (systems running, agents healthy, active workflows, automation status)
- Filterable project cards with color-coded status indicators
- Expandable detail sections for each workflow
- Live priorities panel with progress tracking
- System status overview
- Activity log with real-time updates
- Interactive animations and hover effects

**Tasks**:
1. **Task 1: Dashboard Frontend** (3h)
   - Create dashboard.html with dark theme matching mission_control
   - Implement metrics cards (agent health, workflow count, budget usage)
   - Build filterable project cards (live status, completions, pending)
   - Add expandable details for workflows
   - Real-time clock and activity log
   - Files: `emy/templates/dashboard.html`, `emy/static/dashboard.css`, `emy/static/dashboard.js`

2. **Task 2: Real-time Data API** (2h)
   - Add WebSocket endpoint for live metrics (agent status, workflow updates)
   - Implement polling fallback for browsers without WebSocket
   - Stream workflow execution updates to dashboard
   - Files: `emy/gateway/api.py` (new endpoints)

3. **Task 3: Dashboard Integration** (1h)
   - Wire dashboard.html to FastAPI static files
   - Add route `/dashboard` to serve dashboard UI
   - Connect to WebSocket endpoints
   - Files: `emy/gateway/api.py`, `emy/core/database.py` (metrics methods)

4. **Task 4: Testing** (1h)
   - Test metrics endpoint accuracy
   - Test WebSocket real-time updates
   - Verify dashboard loads and filters work
   - Files: `emy/tests/test_dashboard.py`

**Success Criteria**:
- [ ] Dashboard loads at `/dashboard` with live metrics
- [ ] Real-time updates via WebSocket (agent status, workflow changes)
- [ ] All 3 agents show as "healthy" with execution counts
- [ ] Workflow cards show correct status (running, completed, pending)
- [ ] Filter buttons work (All, Live, Complete, Pending)
- [ ] Responsive design works on desktop and mobile

**Dependencies**: None (works with existing API)

---

### ✅ Week 5: Multi-Agent Workflows (Parallel Agent Coordination) — COMPLETE

**Objective**: Enable multiple agents to execute in parallel and coordinate results

**Status**: ✅ COMPLETE (March 15, 2026, Evening)
- Budget Tracker: 6/6 tests passing
- Result Aggregator & Conflict Resolver: 11/11 tests passing
- Agent Selection Logic: 8/8 tests passing
- Integration Tests: 11/11 tests passing
- **Total: 36/36 tests passing**

**Previous State**: Agents execute sequentially; WorkflowRunner calls one agent at a time

**Challenges**:
- Budget control across parallel executions
- Result aggregation and conflict resolution
- Error handling in multi-agent scenarios
- Coordination protocol between agents

**Tasks**:

1. **Task 1: Multi-Agent Workflow Graph** (2h)
   - Design LangGraph workflow for parallel execution
   - Implement agent_node dispatcher that selects and executes agents
   - Add result_aggregator node to combine outputs
   - Implement conflict_resolver for contradictory results
   - Files: `emy/brain/orchestration.py`, `emy/brain/workflows/multi_agent.py`

2. **Task 2: Budget Enforcement in Parallel** (1h)
   - Track per-agent budget usage
   - Distribute daily budget across agents proportionally
   - Stop agents if budget exhausted
   - Files: `emy/core/budget_tracker.py`

3. **Task 3: API Enhancement** (1h)
   - Add `/workflows/execute` parameter: `"agent_selection": "auto" | ["TradingAgent", "ResearchAgent"]`
   - Implement auto-selection logic (which agents suit this task?)
   - Files: `emy/gateway/api.py`

4. **Task 4: Testing** (1.5h)
   - Test 2-agent parallel execution
   - Test 3-agent coordination
   - Test budget enforcement across parallel agents
   - Test conflict resolution
   - Files: `emy/tests/test_multi_agent_workflows.py`

**Success Criteria**:
- [ ] TradingAgent + ResearchAgent execute in parallel
- [ ] Results combined in single workflow output
- [ ] Budget splits correctly across agents
- [ ] Conflicts detected and resolved
- [ ] 6/6 tests passing

---

### 🎯 Week 6: Email Integration & Outreach

**Objective**: Enable agents to send and parse emails for outreach, feedback, and communication

**Agents Affected**: ResearchAgent, ProjectMonitorAgent, KnowledgeAgent

**Tasks**:

1. **Task 1: Email Tool Implementation** (2h)
   - Implement SMTP client for sending emails
   - Add Gmail API integration (read/parse incoming)
   - Support templating for different email types
   - Files: `emy/tools/email_tool.py`

2. **Task 2: Agent Email Skills** (1.5h)
   - **ResearchAgent**: Send feasibility assessment emails
   - **ProjectMonitorAgent**: Send daily status digests
   - **KnowledgeAgent**: Send research summaries
   - Files: `emy/agents/research_agent.py`, `emy/agents/project_monitor_agent.py`, `emy/agents/knowledge_agent.py`

3. **Task 3: Email Parsing & Response** (1.5h)
   - Auto-parse incoming emails (feedback, questions)
   - Route to appropriate agent
   - Generate responses
   - Files: `emy/tools/email_parser.py`, `emy/gateway/api.py` (webhook endpoint)

4. **Task 4: Testing** (1h)
   - Test email sending (with sandbox)
   - Test email parsing
   - Test agent response generation
   - Files: `emy/tests/test_email_integration.py`

**Success Criteria**:
- [ ] ResearchAgent can send evaluation emails
- [ ] Incoming emails parsed and routed correctly
- [ ] Agents generate contextual responses
- [ ] All email types tested
- [ ] 5/5 tests passing

---

### 🎯 Week 7: Advanced Scheduling & Automation

**Objective**: Enable agents to schedule and execute tasks on recurring basis (daily, weekly, custom cron)

**Current State**: Manual workflow execution via API only

**Tasks**:

1. **Task 1: Cron Scheduler** (2h)
   - Implement cron expression parser
   - Create scheduler that manages recurring workflows
   - Add persistence for scheduled jobs
   - Files: `emy/scheduler/cron_scheduler.py`, `emy/core/database.py` (scheduled_jobs table)

2. **Task 2: Scheduled Workflow Management** (1h)
   - Add `/workflows/schedule` endpoint (create recurring job)
   - Add `/workflows/scheduled` endpoint (list scheduled jobs)
   - Add `/workflows/schedule/{id}/cancel` endpoint
   - Files: `emy/gateway/api.py`

3. **Task 3: Agent Automation Definitions** (1.5h)
   - **TradingAgent**: Schedule daily market analysis (8 AM, 12 PM, 4 PM)
   - **ResearchAgent**: Weekly project review (every Monday 9 AM)
   - **KnowledgeAgent**: Daily dashboard update (every 1 hour)
   - **ProjectMonitorAgent**: Status email (every Friday 5 PM)
   - Files: `emy/scheduler/automation_profiles.json`

4. **Task 4: Testing & Integration** (1h)
   - Test cron expression parsing
   - Test scheduler execution (without waiting for real time)
   - Test job persistence across restarts
   - Files: `emy/tests/test_scheduler.py`

**Success Criteria**:
- [ ] TradingAgent runs on schedule (hourly)
- [ ] ResearchAgent runs on schedule (weekly)
- [ ] Dashboard updates hourly without manual trigger
- [ ] Scheduled jobs survive service restart
- [ ] Scheduler tests passing (time-travel testing)
- [ ] 6/6 tests passing

---

### 🎯 Week 8: Memory Enhancement (Vector Search & Knowledge Embeddings)

**Objective**: Add semantic search and embeddings for knowledge base to enable better agent decision-making

**Current State**: Agents read CLAUDE.md and MEMORY.md as plain text

**Improvements**:
- Semantic similarity search
- Relevant context auto-retrieval
- Long-term memory management
- Cross-project knowledge synthesis

**Tasks**:

1. **Task 1: Embedding Pipeline** (2h)
   - Integrate Anthropic Embeddings API
   - Chunk CLAUDE.md, MEMORY.md into semantic pieces
   - Embed all chunks and store in database
   - Implement similarity search
   - Files: `emy/tools/embedding_tool.py`, `emy/core/memory_manager.py`

2. **Task 2: Agent Memory Integration** (1.5h)
   - Modify all agents to use semantic search for context
   - Auto-retrieve relevant memory before agent execution
   - Pass top-3 similar memory items as system context
   - Files: `emy/agents/base_agent.py`, all agent implementations

3. **Task 3: Memory Auto-Pruning** (1h)
   - Remove old/stale memory entries
   - Consolidate redundant knowledge
   - Keep memory database <100MB
   - Files: `emy/core/memory_manager.py`

4. **Task 4: Testing** (1h)
   - Test embedding generation
   - Test similarity search accuracy
   - Test agent context retrieval
   - Files: `emy/tests/test_memory_embeddings.py`

**Success Criteria**:
- [ ] Embeddings generated for all memory files
- [ ] Similarity search returns relevant contexts
- [ ] Agents use retrieved context in decisions
- [ ] Memory database size stable
- [ ] Search latency <500ms
- [ ] 5/5 tests passing

---

### 📅 After Week 7: Week 4 - JobSearchAgent with Browser Automation

**Defer Reason**: Depends on stable multi-agent and email infrastructure (Weeks 5-6)

**Objective**: Automate job discovery, application, and follow-up

**Tasks**:

1. **Task 1: Browser Automation** (3h)
   - Implement Playwright for web interaction
   - Auto-login to job boards (Indeed, LinkedIn)
   - Scrape job listings matching criteria
   - Files: `emy/tools/browser_automation.py`

2. **Task 2: JobSearchAgent Implementation** (2h)
   - Parse job descriptions
   - Evaluate fit against skill/salary criteria
   - Score and rank opportunities
   - Files: `emy/agents/job_search_agent.py`

3. **Task 3: Application Automation** (2h)
   - Auto-fill applications
   - Generate cover letters (via ResearchAgent)
   - Submit via browser
   - Track submissions
   - Files: `emy/agents/job_search_agent.py`, `emy/tools/application_automation.py`

4. **Task 4: Follow-up Integration** (1h)
   - Send follow-up emails (Week 6 infrastructure)
   - Track response rates
   - Update candidate profile based on feedback
   - Files: `emy/tools/email_tool.py` (integration)

**Success Criteria**:
- [ ] JobSearchAgent discovers jobs matching criteria
- [ ] Applications submitted automatically
- [ ] Follow-up emails sent post-submission
- [ ] Tracking database shows metrics
- [ ] 8/8 tests passing

---

## Implementation Timeline

| Week | Focus | Status |
|------|-------|--------|
| ✅ **Now** | Dashboard UI + Multi-Agent Workflows | ✅ COMPLETE (Mar 15) |
| **+1** | Email Integration & Outreach | 🎯 Starting |
| **+2** | Advanced Scheduling & Automation | 📝 Planning |
| **+3** | Memory Enhancement (Embeddings) | 📝 Planning |
| **+4+** | JobSearchAgent (deferred) | 🔄 After Week 7 |

---

## Key Success Metrics

### By End of Dashboard Week:
- Dashboard loads live at `/dashboard`
- All 3 agents show real-time status
- Workflow execution visible in real-time

### By End of Week 5:
- 2+ agents execute in parallel
- Budget correctly split across parallel agents
- 12+ tests passing

### By End of Week 6:
- Agents can send emails
- Email parsing works
- Auto-responses generated

### By End of Week 7:
- TradingAgent runs on schedule (no manual trigger)
- All scheduled workflows execute on time
- Dashboard updates automatically

### By End of Week 8:
- Semantic search working
- Agents retrieve relevant memory automatically
- Decision quality improved

### After Week 7:
- JobSearchAgent discovers and applies to jobs
- Follow-up emails sent
- Tracking shows submission metrics

---

## Production Monitoring (Ongoing)

### Daily Checks
```bash
# Morning (9 AM)
curl https://emy-phase1a.onrender.com/health
curl https://emy-phase1a.onrender.com/agents/status

# Evening (6 PM)
# Check error logs via Render dashboard
```

### Weekly Checks
- Database disk usage (<500MB/2GB target)
- Workflow count trending
- Agent success rates
- Budget usage ($10/day target)

### Alert Conditions
- Health check fails → Page oncall
- Brain service down → Emergency restart
- Database >1.8GB → Backup and cleanup
- Budget >$8/day → Review agent frequency
- Agent response >30s → Investigate latency

---

## Dependencies & External Services

| Service | Purpose | Status | Cost |
|---------|---------|--------|------|
| **Render** | Hosting (Gateway + Brain) | ✅ Live | $24/mo |
| **Claude API** | Agent intelligence | ✅ Live | $10/day |
| **OANDA** | Forex trading data | ⏳ TradingAgent | Free |
| **Anthropic Embeddings** | Memory search | ⏳ Week 8 | ~$0.10/mo |
| **Gmail API** | Email integration | ⏳ Week 6 | Free |
| **Pushover** | Alerts (optional) | ⏳ Future | $5/mo |

**Total Monthly**: ~$330-350 (including Claude API budget)

---

## Architecture Updates for New Features

### Dashboard Frontend
```
emy/
├── templates/
│   └── dashboard.html          (new)
├── static/
│   ├── dashboard.css           (new)
│   ├── dashboard.js            (new)
│   └── theme.css               (new)
└── gateway/
    └── api.py                  (update: /dashboard route)
```

### Multi-Agent Workflows
```
emy/
├── brain/
│   └── workflows/
│       └── multi_agent.py      (new)
└── core/
    └── budget_tracker.py       (update: parallel budgets)
```

### Email Integration
```
emy/
├── tools/
│   ├── email_tool.py           (new)
│   └── email_parser.py         (new)
└── agents/
    ├── research_agent.py       (update: email skills)
    ├── project_monitor_agent.py (update: email skills)
    └── knowledge_agent.py      (update: email skills)
```

### Scheduling
```
emy/
├── scheduler/
│   ├── cron_scheduler.py       (new)
│   └── automation_profiles.json (new)
└── core/
    └── database.py             (update: scheduled_jobs table)
```

### Memory Embeddings
```
emy/
├── tools/
│   └── embedding_tool.py       (new)
└── core/
    └── memory_manager.py       (new)
```

---

## Notes for Implementation

### Dashboard UI Inspiration
- Reference: `mission_control_interactive.html` (provided by Ibe)
- Dark theme with CSS custom properties
- Real-time metrics via WebSocket
- Interactive filtering and expandable cards
- Activity log at bottom

### Multi-Agent Coordination
- Use LangGraph's parallel_node pattern
- Implement agent_router to select agents based on task
- Aggregate results with conflict detection
- Budget enforcement at workflow level

### Email Architecture
- Use Gmail API for outbound (more reliable than SMTP)
- Implement webhook for inbound email processing
- Parse email intent and route to agents
- Templates for common email types

### Scheduling
- Cron expressions for flexibility
- Persist scheduled jobs in SQLite
- Support timezone awareness
- Test with time-travel (mock time)

### Memory Enhancement
- Use Anthropic Embeddings API (same account)
- Chunk documents intelligently (by section)
- Store embeddings in SQLite
- Implement LRU cache for frequently-used memories

---

## Testing Strategy

- **Unit Tests**: Agent functions, tools, utilities (mock external APIs)
- **Integration Tests**: End-to-end workflows (with real Brain service)
- **E2E Tests**: Full cycle via API (dashboard → workflow → output)
- **Staging Tests**: On Render before production (5-minute cycle)

**Target**: 80%+ code coverage, all tests <5s, integration tests <30s

---

## Deployment Strategy

1. **Local Development**: Test locally with `uvicorn` and `brain.py`
2. **Staging on Render**: Push to `dev` branch, auto-deploy to staging URL
3. **Production**: Merge to `master`, auto-deploy to `emy-phase1a` + `emy-brain`
4. **Rollback**: Git revert + `git push` (Render auto-redeploys)

**Safety**: Every deployment runs health checks first; fails if health check doesn't pass

---

**Last Updated**: March 15, 2026, Evening EDT
**Status**: ✅ Dashboard UI COMPLETE + Week 5 Multi-Agent Workflows COMPLETE
**Completion Summary**:
- Dashboard UI: 12 tasks, 14 tests (100% pass)
- Week 5 Multi-Agent Workflows: 4 tasks, 36 tests (100% pass)
- Architecture: Budget Tracker + Result Aggregation + Conflict Resolution + Agent Selection
- Production Ready: Both features deployed and verified on Render
**Next Action**: Begin Week 6 Email Integration & Outreach

