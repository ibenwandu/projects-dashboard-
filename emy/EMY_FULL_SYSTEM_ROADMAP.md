# Emy: Complete AI Chief of Staff System Roadmap

**Vision**: Autonomous 24/7 AI system managing Ibe's professional operations (trading, job search, knowledge management, project monitoring, research)

**Target**: Production-ready by end of Q2 2026

---

## System Architecture Overview

```
┌─────────────────────────────────────────┐
│         User Interfaces                  │
│  ┌──────────────┬──────────────┐        │
│  │   CLI        │  Gradio UI   │        │
│  │ (Rich)       │ (Web)        │        │
│  └──────────────┴──────────────┘        │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│    FastAPI Gateway (Render)              │
│    6 REST API Endpoints                 │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│    Agent Orchestration Layer             │
│  ┌──────────────────────────────────┐  │
│  │  Task Router & Delegation Engine │  │
│  └──────────────────────────────────┘  │
└─────────────────┬───────────────────────┘
                  ↓
┌──────────┬─────────────┬─────────────┬────────────┐
│ Trading  │ Job Search  │  Knowledge  │   Project  │
│ Agent    │   Agent     │   Agent     │  Monitor   │
│          │             │             │   Agent    │
└──────────┴─────────────┴─────────────┴────────────┘
                  ↓
┌─────────────────────────────────────────┐
│    Skill System & Tools Layer            │
│  ┌──────────────────────────────────┐  │
│  │  11 Skills + Auto-Improvement    │  │
│  │  OANDA API, Job APIs, Git, etc   │  │
│  └──────────────────────────────────┘  │
└─────────────────┬───────────────────────┘
                  ↓
┌──────────┬──────────────┬──────────────┐
│ SQLite   │   Obsidian   │  Pushover    │
│Database  │  Vault (Git) │  Alerts      │
└──────────┴──────────────┴──────────────┘
```

---

## Development Phases

### ✅ Phase 1a: Foundation (COMPLETE - March 12, 2026)

**Status**: Deployed to Render

**Deliverables**:
- ✅ SQLiteStore with 8 tables
- ✅ FastAPI Gateway (6 endpoints)
- ✅ Click CLI client
- ✅ Gradio UI framework
- ✅ 80+ integration tests
- ✅ Docker multi-stage build
- ✅ Environment variables configured

**What works**:
- REST API fully functional
- Workflow creation and status tracking
- Agent health monitoring
- In-memory workflow storage

---

### ⏳ Phase 1b: Real Agent Integration (NEXT - Week of Mar 12-18)

**Goal**: Replace stub agents with Claude API integration

**Tasks** (4-6 hours):

**Task 1: KnowledgeAgent Enhancement** (2h)
- Add Task Scheduler query (Windows integration)
- Add database metrics collection
- Auto-update Obsidian dashboard hourly
- Git auto-commit status changes
- **Files**: `emy/agents/knowledge_agent.py`, tests
- **Depends on**: Plans in `docs/plans/2026-03-10-knowledge-management-implementation.md`

**Task 2: Claude API Integration** (2h)
- Replace stub agent responses with Claude calls
- Implement streaming/async responses
- Add error handling and retries
- Budget tracking via `ANTHROPIC_API_KEY`
- **Files**: `emy/agents/base_agent.py`, all agent implementations
- **Config**: Use env var `ANTHROPIC_MODEL` (already set to claude-opus-4-6)

**Task 3: API Response Persistence** (1h)
- Store workflow outputs in database
- Replace in-memory storage with SQLite
- Enable workflow history across restarts
- **Files**: `emy/gateway/api.py`, `emy/core/database.py`

**Task 4: Testing** (1h)
- Update integration tests for real API calls
- Mock Claude for unit tests
- Test workflow execution end-to-end
- **Files**: `emy/tests/test_integration.py`

**Deliverables**:
- Real agent responses via Claude
- Workflow persistence
- Knowledge dashboard updates
- Production-ready Phase 1b

---

### ⏳ Phase 2: Domain Integration (Week of Mar 18-25)

**Goal**: Connect to OANDA, job search, and other APIs

**Components** (parallel development):

**2A: OANDA Real Integration** (3h)
- Live account connection
- Position monitoring
- Trade alerts via Pushover
- Dashboard metrics
- **Files**: `emy/agents/trading_agent.py`, `emy/tools/oanda_client.py`
- **Depends on**: `docs/plans/2026-03-10-oanda-real-integration-design.md`

**2B: Pushover Alerts System** (2h)
- Real-time notifications
- Alert prioritization
- Unread badge tracking
- **Files**: `emy/tools/notification_tool.py`, `emy/core/alert_manager.py`
- **Depends on**: `docs/plans/2026-03-10-pushover-alerts-implementation.md`

**2C: Job Search Automation** (4h)
- Indeed/LinkedIn scraping
- Job scoring (Gemini/OpenAI)
- Resume tailoring
- PDF generation + upload
- **Files**: `emy/agents/job_search_agent.py`, `emy/tools/job_scraper.py`
- **Depends on**: `docs/plans/2025-03-08-job-search-monorepo-implementation.md`

**2D: Obsidian Vault Integration** (2h)
- Auto-sync knowledge base
- Bidirectional updates
- Wikilink parsing
- Git version control
- **Files**: `emy/tools/obsidian_tool.py`, `emy/agents/knowledge_agent.py`
- **Depends on**: `docs/plans/2026-03-11-obsidian-vault-implementation.md`

**Deliverables**:
- OANDA live monitoring
- Pushover alerts working
- Job automation pipeline
- Knowledge vault sync

---

### ⏳ Phase 3: Advanced Features (Week of Mar 25-Apr 1)

**Goal**: Self-improvement, monitoring, and autonomous operation

**Features**:

**3A: Skill Self-Improvement** (3h)
- Track skill outcomes
- Auto-versioning
- Performance metrics
- Auto-rollback on failure
- **Files**: `emy/core/skill_improver.py`, skill system

**3B: Approval Workflows** (2h)
- High-stakes decision approvals
- Timeout mechanisms (24h)
- Audit trail
- **Files**: `emy/core/approval_gate.py`

**3C: Budget & Credit Tracking** (2h)
- Daily API budget enforcement
- Credit monitoring
- Spend reporting
- **Files**: `emy/core/budget_tracker.py`

**3D: Windows Task Scheduler Integration** (1h)
- 24/7 operation without restart
- Auto-recovery
- Cron-like scheduling
- **Files**: `emy/scheduler/task_scheduler_manager.py`

**Deliverables**:
- Autonomous 24/7 operation
- Self-improving skills
- Budget controls
- Approval gates for critical actions

---

### ⏳ Phase 4: Production Polish (Week of Apr 1-8)

**Goal**: Hardening, monitoring, documentation

**Work**:
- Error handling audit
- Logging & monitoring setup
- Performance optimization
- Documentation completion
- User guide creation
- Production deployment checklist

---

## File Organization

```
emy/
├── agents/                          # ← Phase 1b
│   ├── knowledge_agent.py              (enhance with Obsidian sync)
│   ├── trading_agent.py                (add OANDA integration)
│   ├── job_search_agent.py             (add job automation)
│   ├── research_agent.py               (implement)
│   └── project_monitor_agent.py        (implement)
│
├── tools/                           # ← Phase 2
│   ├── oanda_client.py                 (real OANDA connection)
│   ├── notification_tool.py            (Pushover alerts)
│   ├── job_scraper.py                  (Indeed/LinkedIn)
│   ├── obsidian_tool.py                (Obsidian integration)
│   └── api_client.py                   (base HTTP client)
│
├── core/                            # ← Phase 1b + 3
│   ├── database.py                     (add workflow persistence)
│   ├── skill_improver.py               (Phase 3 - self-improvement)
│   ├── approval_gate.py                (Phase 3 - approvals)
│   ├── budget_tracker.py               (Phase 3 - budget control)
│   └── ...
│
├── gateway/                         # ← Phase 1b
│   └── api.py                          (update for real responses)
│
├── skills/                          # ← Phases 2-4
│   └── (11 skill implementations)
│
└── tests/                           # ← All phases
    └── (integration + unit tests)
```

---

## Success Criteria by Phase

### Phase 1b Complete When:
- [ ] KnowledgeAgent uses Claude API for responses
- [ ] Workflow outputs stored in SQLite
- [ ] All 5 agents return real Claude responses
- [ ] Integration tests pass end-to-end
- [ ] Obsidian dashboard updates hourly

### Phase 2 Complete When:
- [ ] OANDA trades visible in dashboard
- [ ] Pushover alerts trigger correctly
- [ ] Job search pipeline runs daily
- [ ] Obsidian vault syncs bidirectionally
- [ ] All agent tools operational

### Phase 3 Complete When:
- [ ] Skills track success/failure rates
- [ ] Approval workflows work end-to-end
- [ ] Budget enforcement active
- [ ] Task Scheduler integration working
- [ ] 24/7 autonomous operation tested

### Phase 4 Complete When:
- [ ] Zero unhandled exceptions in 48h test
- [ ] Logging covers all code paths
- [ ] Performance benchmarks met
- [ ] Full documentation written
- [ ] User can run `emy.py run` and walk away

---

## Technology Stack

| Component | Tech | Status |
|-----------|------|--------|
| **API** | FastAPI, Pydantic | ✅ Done |
| **CLI** | Click, Rich | ✅ Done |
| **UI** | Gradio | ✅ Done |
| **Storage** | SQLite | ✅ Done |
| **AI** | Claude API (Anthropic SDK) | ⏳ Phase 1b |
| **Job APIs** | Indeed, LinkedIn | ⏳ Phase 2 |
| **Trading API** | OANDA v20 | ⏳ Phase 2 |
| **Notifications** | Pushover | ⏳ Phase 2 |
| **Knowledge** | Obsidian, Git | ⏳ Phase 2 |
| **Scheduling** | Windows Task Scheduler | ⏳ Phase 3 |
| **Deployment** | Docker, Render | ✅ Done |

---

## Implementation Rules (Golden)

1. **One change at a time** — Commit after each feature
2. **Tests first** — TDD on all new features
3. **Integration tests** — E2E verification before "done"
4. **Documentation** — Update docs.plans/ with implementation status
5. **No breaking changes** — Maintain API compatibility

---

## Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| **1a** | 1 week | Mar 5 | ✅ Mar 12 |
| **1b** | 1 week | Mar 12 | Mar 19 |
| **2** | 1 week | Mar 19 | Mar 26 |
| **3** | 1 week | Mar 26 | Apr 2 |
| **4** | 1 week | Apr 2 | Apr 9 |
| **Prod** | — | Apr 9 | 🚀 Live |

---

## Getting Started: Phase 1b This Week

**Step 1: Verify Setup** (5 min)
```bash
cd emy
pip install -r requirements.txt
python -m uvicorn gateway.api:app --port 8000 &
curl http://localhost:8000/health
```

**Step 2: Implement KnowledgeAgent Claude Integration** (2h)
- Read: `docs/plans/2026-03-10-knowledge-management-implementation.md`
- Implement TDD-style (test → code → test pass)
- Follow `superpowers:subagent-driven-development` for this task

**Step 3: Test End-to-End** (1h)
- Create workflow via API
- Verify Claude response in output
- Check SQLite database for persistence

**Step 4: Commit & Update Docs** (30 min)
- Commit Phase 1b start with message: "feat: Phase 1b - Claude integration for KnowledgeAgent"
- Update this roadmap with progress

---

## Notes

- **Openclaw Reference**: Emy is designed as Ibe's autonomous version of Claude Code (multi-agent, self-improving, domain-integrated)
- **Trade-Alerts Monitoring**: 48-hour test period (Mar 12-14) with DeepSeek parser fix; Emy development independent
- **Render Deployment**: Automatic via git push; environment variables already configured
- **Budget Control**: ANTHROPIC_API_KEY enforces Anthropic API usage; daily limits via environment

---

**Last Updated**: March 12, 2026
**Status**: Ready for Phase 1b implementation
**Next Session Focus**: KnowledgeAgent Claude integration + Phase 1b start
