# Emy Phase 1b: Atomic Units Breakdown
## Time-Boxed, Credit-Tracked Units

**Total Phase 1b**: 6 hours | **Total Estimated Tokens**: ~80-100k tokens
**Created**: March 13, 2026

---

## 🎯 How to Use This Document

Each **UNIT** is:
- **Small** (~15-20 min)
- **Atomic** (can stop after any unit without breaking next)
- **Single-focus** (one clear deliverable)
- **Checkpointed** (safe places to pause)

Track time/tokens as you go. **Stop whenever you need to.**

---

## TASK 1: KnowledgeAgent Claude Integration (2h total)

**Total Tokens for Task 1**: ~25-30k
**Approach**: TDD (write tests first)

### 📌 Unit 1.1: Read Design & Plan (15 min | ~3-5k tokens)
**Deliverable**: Understand the architecture
- Read: `docs/plans/2026-03-10-knowledge-management-implementation.md` (first section only)
- Read: `emy/agents/base_agent.py` (current implementation)
- Read: `emy/agents/knowledge_agent.py` (current stub)
- **Stop here if out of tokens?** YES — you can pause after reading

**Verification**: Explain to yourself how Claude API will be called

---

### 📌 Unit 1.2: Write Tests for Claude Integration (20 min | ~5-8k tokens)
**Deliverable**: Tests that prove Claude is being called
- Create/update: `emy/tests/test_knowledge_agent.py`
- Add tests:
  - `test_knowledge_agent_calls_claude_api()` — verify Anthropic client used
  - `test_knowledge_agent_returns_non_null_response()` — verify output is real
  - `test_knowledge_agent_handles_api_error()` — verify error handling
  - `test_knowledge_agent_with_real_api_key()` — integration test (if key present)
- Run tests (should fail — RED phase)

**Stop & Checkpoint?** YES — tests written, failures documented

---

### 📌 Unit 1.3: Add Claude SDK to Base Agent (15 min | ~3-5k tokens)
**Deliverable**: Claude client available in agents
- Edit: `emy/agents/base_agent.py`
- Add: `from anthropic import Anthropic` (top)
- Add: `_call_claude(prompt: str) -> str` helper method
- Pattern:
  ```python
  def _call_claude(self, prompt: str) -> str:
      """Call Claude API"""
      try:
          message = self.client.messages.create(
              model=os.getenv('ANTHROPIC_MODEL', 'claude-opus-4-6'),
              max_tokens=1024,
              messages=[{"role": "user", "content": prompt}]
          )
          return message.content[0].text
      except Exception as e:
          logger.error(f"Claude error: {e}")
          raise
  ```
- Commit: `git add emy/agents/base_agent.py && git commit -m "feat: add Claude SDK to base_agent"`

**Stop & Checkpoint?** YES — foundation in place, tests still failing

---

### 📌 Unit 1.4: Implement KnowledgeAgent.execute() (20 min | ~5-7k tokens)
**Deliverable**: KnowledgeAgent calls Claude instead of returning stub
- Edit: `emy/agents/knowledge_agent.py`
- Update: `execute()` method to:
  1. Build prompt from workflow input
  2. Call `self._call_claude(prompt)`
  3. Return response in output dict
- Pattern:
  ```python
  def execute(self, workflow_input: dict) -> dict:
      query = workflow_input.get('query', 'Status check')
      response = self._call_claude(query)
      return {
          'status': 'success',
          'response': response,
          'query': query
      }
  ```
- Run tests — they should pass now (GREEN phase)
- Commit: `git add emy/agents/knowledge_agent.py && git commit -m "feat: KnowledgeAgent calls Claude API"`

**Stop & Checkpoint?** YES — agent implementation complete, tests passing

---

### 📌 Unit 1.5: Update Gateway to Return Real Outputs (15 min | ~3-5k tokens)
**Deliverable**: API doesn't return null outputs
- Edit: `emy/gateway/api.py` — `/workflows/execute` endpoint
- Current code: `"output": None`
- New code: Capture agent response, return it
- Pattern:
  ```python
  result = agent.execute(workflow_input)
  workflow_output = result  # Not None
  return {
      "workflow_id": workflow_id,
      "status": "completed",
      "output": workflow_output
  }
  ```
- Verify: Tests still pass
- Commit: `git add emy/gateway/api.py && git commit -m "feat: return real workflow outputs from API"`

**Stop & Checkpoint?** YES — API now returns real data

---

### 📌 Unit 1.6: Manual Integration Test via Curl (15 min | ~2-3k tokens)
**Deliverable**: Prove Task 1 works end-to-end
1. Start API:
   ```bash
   cd C:\Users\user\projects\personal
   python -m uvicorn emy.gateway.api:app --reload --port 8000 &
   ```
2. Test request:
   ```bash
   curl -X POST http://localhost:8000/workflows/execute \
     -H "Content-Type: application/json" \
     -d '{
       "workflow_type": "knowledge_query",
       "agents": ["KnowledgeAgent"],
       "input": {"query": "What is your status?"}
     }'
   ```
3. Verify response includes real Claude output (not null, not stub)
4. Check logs for any errors

**Stop & Checkpoint?** YES — manual test passes

---

### 📌 Unit 1.7: Commit Task 1 Complete (5 min | <1k tokens)
**Deliverable**: Clean git state
```bash
git add -A
git commit -m "feat: Phase 1b Task 1 - KnowledgeAgent Claude API integration

- Added Claude SDK to base_agent.py
- Implemented KnowledgeAgent.execute() to call Claude API
- Updated gateway to return real workflow outputs
- All tests passing (KnowledgeAgent integration tests)
- Manual curl test verified end-to-end"
```

✅ **TASK 1 COMPLETE — Safe to stop here**

---

## TASK 2: TradingAgent OANDA Connection (2h total)

**Total Tokens for Task 2**: ~25-30k
**Approach**: Same TDD pattern

### 📌 Unit 2.1: Read OANDA Design (10 min | ~2-3k tokens)
**Deliverable**: Understand OANDA integration architecture
- Read: `docs/plans/2026-03-10-oanda-real-integration-design.md`
- Review: Current `emy/tools/oanda_client.py`
- Check: Environment variables available (OANDA_ACCESS_TOKEN, OANDA_ACCOUNT_ID)

**Stop & Checkpoint?** YES

---

### 📌 Unit 2.2: Write OANDA Tests (15 min | ~4-6k tokens)
**Deliverable**: Tests that prove OANDA is connected
- Create: `emy/tests/test_trading_agent.py`
- Add tests:
  - `test_trading_agent_connects_to_oanda()`
  - `test_trading_agent_returns_positions()`
  - `test_trading_agent_returns_account_summary()`
  - `test_trading_agent_handles_missing_credentials()`
- Run tests (RED — should fail)

**Stop & Checkpoint?** YES

---

### 📌 Unit 2.3: Implement OANDA Client (20 min | ~5-8k tokens)
**Deliverable**: OANDA API client working
- Edit: `emy/tools/oanda_client.py`
- Add methods:
  - `get_positions()` → list of open positions
  - `get_account_summary()` → account balance, PnL
  - `connect()` → initialize API connection
- Pattern uses `oandapyV20` SDK (already in requirements)
- Commit: `git add emy/tools/oanda_client.py && git commit -m "feat: implement OANDA client methods"`

**Stop & Checkpoint?** YES

---

### 📌 Unit 2.4: Update TradingAgent to Use OANDA (20 min | ~5-7k tokens)
**Deliverable**: TradingAgent returns real OANDA data
- Edit: `emy/agents/trading_agent.py`
- Update: `execute()` to:
  1. Call `self.oanda_client.get_positions()`
  2. Call `self.oanda_client.get_account_summary()`
  3. Return in response dict
- Pattern:
  ```python
  def execute(self, workflow_input: dict) -> dict:
      positions = self.oanda_client.get_positions()
      summary = self.oanda_client.get_account_summary()
      return {
          'status': 'success',
          'positions': positions,
          'account': summary
      }
  ```
- Run tests — should pass (GREEN)
- Commit: `git add emy/agents/trading_agent.py && git commit -m "feat: TradingAgent calls OANDA API"`

**Stop & Checkpoint?** YES

---

### 📌 Unit 2.5: Manual OANDA Test via Curl (10 min | ~2-3k tokens)
**Deliverable**: Prove OANDA connection works
```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "trading_health",
    "agents": ["TradingAgent"],
    "input": {}
  }'
```
Verify response includes positions and account summary

**Stop & Checkpoint?** YES

---

### 📌 Unit 2.6: Commit Task 2 Complete (5 min | <1k tokens)
```bash
git commit -m "feat: Phase 1b Task 2 - TradingAgent OANDA connection

- Implemented OANDA client methods (get_positions, get_account_summary)
- Updated TradingAgent.execute() to fetch real OANDA data
- Tests passing (trading agent integration)
- Manual curl test verified positions and account data"
```

✅ **TASK 2 COMPLETE — Safe to stop here**

---

## TASK 3: Workflow Output Persistence (1h total)

**Total Tokens for Task 3**: ~15-20k

### 📌 Unit 3.1: Update Database Schema (15 min | ~3-5k tokens)
**Deliverable**: SQLite table has `output` column
- Edit: `emy/core/database.py`
- Migration logic:
  ```python
  def init_db():
      # Check if output column exists
      # If not, ADD COLUMN output TEXT
      # If exists, skip
  ```
- Commit: `git add emy/core/database.py && git commit -m "feat: add output column to emy_workflows table"`

**Stop & Checkpoint?** YES

---

### 📌 Unit 3.2: Save Workflow Output to DB (15 min | ~4-6k tokens)
**Deliverable**: API saves output after execution
- Edit: `emy/gateway/api.py` — `/workflows/execute` endpoint
- After agent execution, save output:
  ```python
  db.save_workflow(
      workflow_id=workflow_id,
      workflow_type=workflow_type,
      output=result,
      status='completed'
  )
  ```
- Commit: `git add emy/gateway/api.py && git commit -m "feat: save workflow output to database"`

**Stop & Checkpoint?** YES

---

### 📌 Unit 3.3: Retrieve Workflow Output from DB (15 min | ~4-6k tokens)
**Deliverable**: GET /workflows/{id} returns saved output
- Edit: `emy/gateway/api.py` — GET endpoint
- Change from in-memory to database retrieval:
  ```python
  workflow = db.get_workflow(workflow_id)
  return {
      "workflow_id": workflow_id,
      "output": workflow.output,
      "status": workflow.status
  }
  ```
- Commit: `git add emy/gateway/api.py && git commit -m "feat: retrieve workflow output from database"`

**Stop & Checkpoint?** YES

---

### 📌 Unit 3.4: Write Persistence Tests (10 min | ~3-4k tokens)
**Deliverable**: Tests prove output persists
- Add tests to `emy/tests/test_integration.py`:
  - `test_workflow_output_saved_to_db()`
  - `test_retrieve_workflow_output()` — restart API, verify data still there
  - `test_persistence_across_restarts()`
- Run tests — should pass

**Stop & Checkpoint?** YES

---

### 📌 Unit 3.5: Commit Task 3 Complete (5 min | <1k tokens)
```bash
git commit -m "feat: Phase 1b Task 3 - Workflow output persistence

- Updated database schema with output column
- API saves workflow output after execution
- GET /workflows/{id} retrieves output from database
- Tests verify persistence across restarts"
```

✅ **TASK 3 COMPLETE — Safe to stop here**

---

## TASK 4: Integration Tests & Verification (1h total)

**Total Tokens for Task 4**: ~10-15k

### 📌 Unit 4.1: Run Full Test Suite (10 min | ~2-3k tokens)
**Deliverable**: All tests pass
```bash
cd C:\Users\user\projects\personal
pytest emy/tests/ -v
```
Document any failures

**Stop & Checkpoint?** YES (if all pass)

---

### 📌 Unit 4.2: Manual End-to-End Test (15 min | ~3-4k tokens)
**Deliverable**: Prove all 3 tasks work together
1. Start API
2. Execute KnowledgeAgent workflow → verify Claude response saved to DB
3. Retrieve workflow → verify output returned
4. Execute TradingAgent workflow → verify OANDA data saved to DB
5. Verify both in database

**Stop & Checkpoint?** YES

---

### 📌 Unit 4.3: Verify Database Persistence (10 min | ~2-3k tokens)
**Deliverable**: Data survives API restart
```bash
# After tests, check database directly
sqlite3 emy/data/emy.db "SELECT workflow_type, status FROM emy_workflows ORDER BY created_at DESC LIMIT 5;"

# Restart API
# Query same workflows — data still there
```

**Stop & Checkpoint?** YES

---

### 📌 Unit 4.4: Handle Any Failures (20 min | ~3-5k tokens)
**Deliverable**: All issues resolved
- If tests fail: diagnose, fix, re-run
- If API crashes: check logs, fix
- If database issues: verify schema, fix migrations

**Stop & Checkpoint?** YES (only if all passing)

---

### 📌 Unit 4.5: Final Phase 1b Commit (5 min | <1k tokens)
```bash
git commit -m "feat: Phase 1b complete - All integration tests passing

- Task 1: KnowledgeAgent Claude integration ✅
- Task 2: TradingAgent OANDA connection ✅
- Task 3: Workflow output persistence ✅
- Task 4: All integration tests passing ✅

Phase 1b is production-ready. Ready for Phase 2."
```

✅ **PHASE 1B COMPLETE**

---

## 📊 Time & Token Tracking

### Task 1 (KnowledgeAgent)
| Unit | Time | Tokens | Cumulative |
|------|------|--------|-----------|
| 1.1 | 15m | 3-5k | 3-5k |
| 1.2 | 20m | 5-8k | 8-13k |
| 1.3 | 15m | 3-5k | 11-18k |
| 1.4 | 20m | 5-7k | 16-25k |
| 1.5 | 15m | 3-5k | 19-30k |
| 1.6 | 15m | 2-3k | 21-33k |
| 1.7 | 5m | <1k | 21-33k |
| **TOTAL** | **2h** | **~25-30k** | |

### Task 2 (TradingAgent)
| Unit | Time | Tokens | Cumulative |
|------|------|--------|-----------|
| 2.1 | 10m | 2-3k | 23-36k |
| 2.2 | 15m | 4-6k | 27-42k |
| 2.3 | 20m | 5-8k | 32-50k |
| 2.4 | 20m | 5-7k | 37-57k |
| 2.5 | 10m | 2-3k | 39-60k |
| 2.6 | 5m | <1k | 39-60k |
| **TOTAL** | **1.5h** | **~25-30k** | |

### Task 3 (Persistence)
| Unit | Time | Tokens | Cumulative |
|------|------|--------|-----------|
| 3.1 | 15m | 3-5k | 42-65k |
| 3.2 | 15m | 4-6k | 46-71k |
| 3.3 | 15m | 4-6k | 50-77k |
| 3.4 | 10m | 3-4k | 53-81k |
| 3.5 | 5m | <1k | 53-81k |
| **TOTAL** | **1h** | **~15-20k** | |

### Task 4 (Verification)
| Unit | Time | Tokens | Cumulative |
|------|------|--------|-----------|
| 4.1 | 10m | 2-3k | 55-84k |
| 4.2 | 15m | 3-4k | 58-88k |
| 4.3 | 10m | 2-3k | 60-91k |
| 4.4 | 20m | 3-5k | 63-96k |
| 4.5 | 5m | <1k | 63-96k |
| **TOTAL** | **1h** | **~10-15k** | |

---

## 🛑 Safe Stop Points

**You can safely stop after:**
- Unit 1.7 (Task 1 complete)
- Unit 2.6 (Task 2 complete)
- Unit 3.5 (Task 3 complete)
- Unit 4.5 (Phase 1b complete)

**Each stop point = zero technical debt, next session can pick up Task N+1**

---

## ⚠️ Running Low on Credits?

**Strategy**:
1. Complete current unit fully
2. Commit your work (`git commit`)
3. Update CLAUDE_SESSION_LOG.md with current state
4. Stop before starting next unit

**You won't lose progress — just resume next session at Unit N+1**

---

**Ready to start Unit 1.1?**
