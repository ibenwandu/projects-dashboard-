# Emy Phase 2: Advanced Features & Multi-Agent Orchestration

**Status**: PLANNING
**Target Start**: March 15, 2026
**Phase 1b Baseline**: 58+ tests, 2 agents, 5 endpoints, 1 database

---

## Overview

Phase 2 expands Emy from a dual-agent system to a full multi-agent orchestration platform with:
- **3 additional agents** (ResearchAgent, ProjectMonitorAgent, GeminiAgent)
- **LangGraph workflow orchestration** for complex multi-step workflows
- **Advanced scheduling** for recurring tasks
- **Multi-LLM integration** (Claude + Gemini for redundancy)
- **Real-time updates** via WebSocket
- **Enhanced database** (migration from SQLite → PostgreSQL)

---

## Phase 2 Agents

### Current Agents (Phase 1b)
1. ✅ **KnowledgeAgent** — Claude API analysis, session documentation
2. ✅ **TradingAgent** — OANDA market data, trading signals

### New Agents (Phase 2)

#### 3. ResearchAgent
**Purpose**: Deep research and competitive analysis
**Capabilities**:
- Web search and content scraping
- Document analysis and extraction
- Report generation
- Citation and source tracking

**Integration Points**:
- Claude API for analysis
- Firecrawl/web scraping for content
- Document storage in Obsidian vault

**Workflows**:
- `research_topic` — Search topic, compile analysis
- `competitive_analysis` — Analyze competitors
- `market_research` — Market trend analysis

---

#### 4. ProjectMonitorAgent
**Purpose**: Project health tracking and status reporting
**Capabilities**:
- Git repository monitoring
- Issue/PR tracking (GitHub)
- Deployment status monitoring (Render)
- Performance metrics collection
- Alert generation

**Integration Points**:
- GitHub API for repos/issues
- Render API for deployments
- Obsidian vault for dashboards
- Database for metrics storage

**Workflows**:
- `project_health_check` — Full health scan
- `deployment_monitor` — Watch Render deploys
- `alert_on_issues` — Monitor GitHub issues

---

#### 5. GeminiAgent
**Purpose**: Redundant LLM provider for failover/consensus
**Capabilities**:
- Claude API backup (if Claude unavailable)
- Consensus analysis (run analysis on both Claude + Gemini)
- Cost optimization (use cheaper model for some tasks)
- Multi-model voting for critical decisions

**Integration Points**:
- Google Gemini API (https://ai.google.dev)
- Fallback routing in AgentExecutor
- Consensus voting in workflows

**Workflows**:
- `consensus_analysis` — Run on both Claude + Gemini, compare results
- `fallback_analysis` — Use Gemini if Claude unavailable

---

## Phase 2 Architecture Changes

### LangGraph Integration
**Current**: Sequential agent execution via AgentExecutor
**Phase 2**: Complex workflow graphs via LangGraph

**Benefits**:
- Conditional routing (if X, then A; else B)
- Parallel execution (run multiple agents concurrently)
- State persistence across steps
- Automatic tool availability discovery

**Example Workflow**:
```
START
  ↓
[ResearchAgent: Analyze topic]
  ↓
[ProjectMonitorAgent: Check project status]
  ↓
[Fork: GeminiAgent + Claude parallel]
  ├→ [GeminiAgent: Generate insights]
  └→ [KnowledgeAgent: Analyze findings]
  ↓
[Consensus: Compare outputs]
  ↓
[KnowledgeAgent: Generate final report]
  ↓
END
```

### Database Upgrade
**Current**: SQLite (local file, single instance)
**Phase 2**: PostgreSQL (networked, multi-instance)

**Benefits**:
- Multiple Emy instances can share database
- Transactional guarantees
- Row-level security
- Backup/replication support

**Migration Path**:
1. Create PostgreSQL schema matching SQLite
2. Implement database abstraction layer
3. Update tests to use both SQLite and PostgreSQL
4. Deploy with PostgreSQL in production
5. Archive SQLite for local development

---

## Phase 2 Capabilities

### 1. Workflow Scheduling
**Current**: Workflows execute on-demand via API
**Phase 2**: Scheduled recurring workflows

**Example**:
```bash
POST /workflows/schedule
{
  "workflow_type": "project_health_check",
  "agents": ["ProjectMonitorAgent"],
  "schedule": "0 9 * * MON",  # 9am every Monday
  "max_concurrent": 1
}
```

---

### 2. Multi-Step Workflows
**Current**: Single agent per workflow_type
**Phase 2**: Complex multi-agent workflows

**Example**:
```bash
POST /workflows/execute/complex
{
  "workflow_name": "weekly_analysis",
  "steps": [
    {"type": "research", "agent": "ResearchAgent"},
    {"type": "project_check", "agent": "ProjectMonitorAgent"},
    {"type": "consensus", "agent": ["GeminiAgent", "KnowledgeAgent"]},
    {"type": "report", "agent": "KnowledgeAgent"}
  ]
}
```

---

### 3. Real-Time Updates via WebSocket
**Current**: Request/response via REST
**Phase 2**: Streaming updates via WebSocket

```javascript
// Client
ws = new WebSocket('wss://emy-phase1a.onrender.com/workflows/stream');
ws.on('message', (event) => {
  console.log('Workflow update:', event.data);
  // {"workflow_id":"wf_...", "step":2, "status":"in_progress", "partial_output":"..."}
});
```

---

### 4. Multi-LLM Consensus
**Current**: Single LLM per agent (Claude)
**Phase 2**: Consensus across multiple LLMs

**Example Workflow**:
```
[Research Topic]
  ↓
[Run analysis on Claude] || [Run analysis on Gemini] (parallel)
  ↓
[Compare outputs for consensus]
  ↓
[If confidence < 80%, ask user for decision]
  ↓
[Return consensus analysis with confidence score]
```

---

### 5. Intelligent Caching
**Current**: No caching
**Phase 2**: Redis-based result caching

**Scenarios**:
- Cache research results (same query within 1 hour)
- Cache market data (same symbols within 5 minutes)
- Cache project status (same repo within 10 minutes)

**Benefits**:
- 50-70% reduction in API calls
- Faster response times
- Cost savings on API usage

---

## Phase 2 Breakdown

### Phase 2a: ResearchAgent + LangGraph (Task 1-2)
**Duration**: 2-3 weeks
**Focus**: Multi-agent orchestration foundation

**Deliverables**:
- ✅ ResearchAgent fully implemented
- ✅ LangGraph workflow support
- ✅ 20+ new tests
- ✅ Example complex workflows
- ✅ Documentation

**Success Criteria**:
- ResearchAgent executes workflows
- LangGraph orchestration working
- Complex workflows execute end-to-end
- All tests passing

---

### Phase 2b: ProjectMonitorAgent + GeminiAgent (Task 3-4)
**Duration**: 2-3 weeks
**Focus**: Monitoring and multi-LLM support

**Deliverables**:
- ✅ ProjectMonitorAgent fully implemented
- ✅ GeminiAgent with fallback routing
- ✅ Consensus analysis workflows
- ✅ 20+ new tests
- ✅ GitHub/Render integration verified

**Success Criteria**:
- ProjectMonitorAgent working
- GeminiAgent fallback routing working
- Consensus analysis produces valid results
- All tests passing

---

### Phase 2c: Advanced Features (Task 5-6)
**Duration**: 2-3 weeks
**Focus**: Scheduling, real-time updates, caching

**Deliverables**:
- ✅ Workflow scheduling support
- ✅ WebSocket real-time updates
- ✅ Redis caching layer
- ✅ PostgreSQL migration
- ✅ 15+ new tests

**Success Criteria**:
- Scheduled workflows execute on time
- WebSocket updates streaming in real-time
- Cache hit rate > 40%
- PostgreSQL working in production

---

## Technical Decisions

### LangGraph vs. Other Orchestration
**Considered**: Airflow, Prefect, Temporal, custom
**Selected**: LangGraph
**Rationale**:
- Native Python integration
- Built for AI workflows
- Lightweight (no separate service)
- Integrates with LangChain ecosystem
- State management out of the box

### PostgreSQL Migration
**When**: Phase 2c
**Why**: Single-instance SQLite insufficient for scheduling/parallel workflows
**How**: Database abstraction layer allows both SQLite (dev) + PostgreSQL (prod)

### WebSocket vs. Server-Sent Events
**Selected**: WebSocket
**Rationale**:
- Bidirectional (can cancel running workflows)
- Lower latency than polling
- Standard for real-time applications
- Easier to implement across frameworks

---

## Phase 2 Dependencies

### External Services
1. **Google Gemini API** — GeminiAgent implementation
2. **PostgreSQL Database** — Enhanced persistence
3. **Redis** — Caching layer
4. **GitHub API** — ProjectMonitorAgent
5. **Firecrawl** — Web research capability

### Internal Dependencies
- Phase 1b must be fully complete and stable
- All tests passing before Phase 2a starts
- Database abstraction layer before migrations

---

## Success Metrics

| Metric | Phase 1b | Phase 2 Target |
|--------|----------|----------------|
| Agent count | 2 | 5 |
| Workflows supported | 2 | 10+ |
| Test coverage | 58+ tests | 100+ tests |
| API endpoints | 5 | 8+ |
| Multi-step workflows | ❌ | ✅ |
| Scheduling support | ❌ | ✅ |
| Real-time updates | ❌ | ✅ |
| Multi-LLM support | ❌ | ✅ |
| Cache layer | ❌ | ✅ |
| Database | SQLite | PostgreSQL |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LangGraph complexity | High | Start with simple graphs, test extensively |
| Multi-LLM consistency | Medium | Implement consensus validation |
| Database migration | High | Dual-layer abstraction, extensive testing |
| WebSocket scaling | Medium | Load test before production |
| PostgreSQL failover | High | Implement connection pooling, backups |

---

## Resource Requirements

### Development
- **Estimated effort**: 6-9 weeks full-time
- **Team size**: 1 senior engineer (Ibe)
- **Tools**: Python 3.11, LangGraph, PostgreSQL, Redis

### Infrastructure
- **PostgreSQL instance** on Render (estimated $20-50/month)
- **Redis instance** on Render (estimated $10-20/month)
- **Storage increase** for historical data (estimated 5-10GB)

### External Services
- **Google Gemini API** (free tier available, $0.075/M tokens paid)
- **GitHub API** (free, 5000 requests/hour)
- **Firecrawl** (free tier, $99+ paid for high volume)

---

## Phase 2 Readiness Checklist

- [x] Phase 1b complete and verified
- [x] All 58+ tests passing
- [x] All 5 endpoints live in production
- [x] Code review ready
- [x] Documentation complete
- [ ] Phase 2a design finalized
- [ ] Resource allocation confirmed
- [ ] External service accounts created
- [ ] Development environment ready

---

## Next Steps

1. **Finalize Phase 2a design** (ResearchAgent + LangGraph)
2. **Create detailed task breakdown** for Phase 2a
3. **Set up PostgreSQL and Redis** in Render
4. **Create GitHub milestone** for Phase 2
5. **Begin Phase 2a: ResearchAgent implementation**

---

**Phase 1b Status**: ✅ COMPLETE & PRODUCTION READY
**Phase 2 Status**: 📋 PLANNED & READY TO START
