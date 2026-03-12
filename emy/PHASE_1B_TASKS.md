# Emy Phase 1b: Implementation Tasks (Week of Mar 12-18, 2026)

**Goal**: Replace stub agents with real Claude API integration

**Status**: Ready to start

---

## Task Order (Sequential, TDD)

### Task 1: KnowledgeAgent Claude Integration (2h)
**Objective**: Make KnowledgeAgent return real Claude responses instead of stubs

**Acceptance Criteria**:
- [ ] KnowledgeAgent can invoke Claude API via ANTHROPIC_API_KEY
- [ ] Responses appear in workflow output (not null)
- [ ] Integration tests verify end-to-end
- [ ] Errors handled gracefully (network, budget, invalid key)

**Implementation Steps**:
1. Read: `docs/plans/2026-03-10-knowledge-management-implementation.md` (first part)
2. Add Claude API import to `emy/agents/base_agent.py`
3. Implement `_call_claude()` helper method
4. Update `KnowledgeAgent.execute()` to use Claude
5. Write tests in `emy/tests/test_knowledge_agent.py`
6. Update `emy/gateway/api.py` to return real outputs (not null)
7. Test via API: POST /workflows/execute with KnowledgeAgent

**Files to Modify**:
- `emy/agents/base_agent.py` — Add Claude SDK integration
- `emy/agents/knowledge_agent.py` — Use Claude instead of stub
- `emy/gateway/api.py` — Return real workflow output
- `emy/tests/test_knowledge_agent.py` — Add Claude integration tests
- `emy/core/database.py` — Add workflow output storage

**Key Code Pattern**:
```python
from anthropic import Anthropic

client = Anthropic()

def _call_claude(self, prompt: str) -> str:
    """Call Claude API with prompt"""
    try:
        message = client.messages.create(
            model=os.getenv('ANTHROPIC_MODEL', 'claude-opus-4-6'),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        raise
```

**Test via Curl**:
```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "knowledge_query",
    "agents": ["KnowledgeAgent"],
    "input": {"query": "What is your current status?"}
  }'

# Expected: output with real Claude response, not null
```

---

### Task 2: Trading Agent OANDA Connection (2h)
**Objective**: Make TradingAgent return real trade data from OANDA

**Acceptance Criteria**:
- [ ] TradingAgent connects to OANDA API
- [ ] Returns current positions and P&L
- [ ] Handles missing credentials gracefully
- [ ] Tests verify OANDA connection

**Implementation Steps**:
1. Read: `docs/plans/2026-03-10-oanda-real-integration-design.md`
2. Add OANDA SDK to `emy/tools/oanda_client.py`
3. Implement position fetching in `TradingAgent`
4. Update agent response to include trade data
5. Handle missing OANDA_ACCESS_TOKEN

**Test via Curl**:
```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "trading_health",
    "agents": ["TradingAgent"],
    "input": {}
  }'

# Expected: Current positions and account status
```

---

### Task 3: Workflow Output Persistence (1h)
**Objective**: Store workflow outputs in database (not just in-memory)

**Acceptance Criteria**:
- [ ] Workflow output stored in `emy.db` after execution
- [ ] Can retrieve output via GET /workflows/{id}
- [ ] Outputs persist across API restart
- [ ] Tests verify persistence

**Implementation Steps**:
1. Update `emy_workflows` table schema: add `output` column
2. Modify `api.py`: save output to database after agent execution
3. Modify GET `/workflows/{id}`: return output from database
4. Add migration logic (handle existing databases)
5. Tests verify data persists

---

### Task 4: Integration Tests & Verification (1h)
**Objective**: Verify Phase 1b works end-to-end

**Acceptance Criteria**:
- [ ] All integration tests pass
- [ ] Real Claude API calls work (not mocked)
- [ ] Workflow execution returns real outputs
- [ ] Database persistence verified
- [ ] Error cases handled

**Test Plan**:
```bash
# Start API
python -m uvicorn emy.gateway.api:app --port 8000 &

# Run integration tests
pytest emy/tests/test_integration.py -v

# Manual workflow test
python emy/cli/main.py execute knowledge KnowledgeAgent

# Check database
sqlite3 emy/data/emy.db "SELECT * FROM emy_workflows ORDER BY created_at DESC LIMIT 1;"
```

---

## Implementation Sequence

```
Week of Mar 12-18:

Mon 3/12   Wed 3/13   Thu 3/14   Fri 3/15
└─ Task 1─►─Task 2─►─Task 3──────────►├─ Task 4
   2h       2h        1h         1h   │
                                      └─ Final testing + commit

Final state: Phase 1b complete, ready for Phase 2
```

---

## Commit Messages

Each task should end with a clear commit:

```bash
# Task 1
git commit -m "feat: Phase 1b Task 1 - KnowledgeAgent Claude API integration"

# Task 2
git commit -m "feat: Phase 1b Task 2 - TradingAgent OANDA connection"

# Task 3
git commit -m "feat: Phase 1b Task 3 - Workflow output persistence to SQLite"

# Task 4
git commit -m "feat: Phase 1b Task 4 - Integration tests and verification"
```

---

## Success Criteria for Phase 1b Complete

- [x] Environment variables configured on Render
- [ ] Task 1 complete: KnowledgeAgent returns Claude responses
- [ ] Task 2 complete: TradingAgent returns OANDA data
- [ ] Task 3 complete: Outputs stored in database
- [ ] Task 4 complete: All tests passing

---

## Notes

- **Use `superpowers:subagent-driven-development`** for test-driven implementation of each task
- **One task at a time** — don't batch; commit after each task
- **Test before moving on** — verify task works before starting next
- **Update roadmap progress** after each task completion

---

**Ready to start Task 1?**

Next: Use `superpowers:subagent-driven-development` to implement Task 1 with TDD approach.
