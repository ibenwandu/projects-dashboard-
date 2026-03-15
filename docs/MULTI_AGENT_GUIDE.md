# Multi-Agent Coordination Guide

## Overview

Emy Brain now supports parallel execution of multiple agents within a single workflow using **agent groups**. Agents within a group execute concurrently; groups execute sequentially.

## API: Job Submission

### Single Agent (Backward Compatible)

```bash
curl -X POST http://localhost:8001/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "trading_health",
    "agents": ["TradingAgent"],
    "input": {"query": "Check market health"}
  }'
```

### Multiple Agents in Parallel (New)

```bash
curl -X POST http://localhost:8001/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "market_analysis",
    "agent_groups": [
      ["TradingAgent", "ResearchAgent"],
      ["KnowledgeAgent"]
    ],
    "input": {"query": "Analyze EUR/USD outlook"}
  }'
```

**Request:**
- `agent_groups`: List of lists. Each inner list is a group (agents in group run in parallel).
- Groups execute sequentially: Group 0 → Group 1 → Group 2...

**Response:**
```json
{
  "job_id": "job_a1b2c3d4",
  "workflow_type": "market_analysis",
  "status": "pending",
  "created_at": "2026-03-14T10:30:00"
}
```

## Common Patterns

### Pattern 1: Multi-Perspective Analysis
Analyze a question from multiple angles in parallel, then synthesize.

```json
{
  "agent_groups": [
    ["TradingAgent", "ResearchAgent", "KnowledgeAgent"],
    ["ProjectMonitorAgent"]
  ]
}
```

### Pattern 2: Sequential Refinement
Coarse analysis → detailed analysis → synthesis.

```json
{
  "agent_groups": [
    ["TradingAgent"],
    ["ResearchAgent"],
    ["KnowledgeAgent"]
  ]
}
```

### Pattern 3: Independent Checks
Run multiple independent analyses in parallel.

```json
{
  "agent_groups": [
    ["TradingAgent", "JobSearchAgent"],
    ["ResearchAgent"]
  ]
}
```

## Monitoring

Track job status:

```bash
curl http://localhost:8001/jobs/{job_id}/status
```

**Response includes:**
- `status`: pending → executing → completed/failed
- `output`: Aggregated results from all agents
- `error`: Error message if failed

## Architecture

### Execution Flow: Multi-Agent Workflow

1. **Router Node** — Detects agent_groups, routes to executor
2. **Agent Group Executor** — Runs agents in current group in parallel via asyncio.gather()
3. **Result Aggregation** — Merges results from all agents into state.results (keyed by agent name)
4. **Group Progression** — After group completes, routes back to router for next group
5. **Completion** — All groups executed, workflow completes

### State Management

Each workflow execution maintains:
- `agent_groups`: List of agent groups (nested list)
- `current_group_index`: Which group is executing (0, 1, 2...)
- `agents_executing`: List of agents currently running
- `results`: Dict keyed by agent name with outputs
- `messages`: Audit trail of all execution steps
- `status`: pending → executing → completed/failed

## Implementation Details

### Parallel Execution: asyncio.gather()

```python
# Execute all agents in a group concurrently
results = await asyncio.gather(*tasks, return_exceptions=True)

# Timeout protection: 300 seconds per group
results = await asyncio.wait_for(
    asyncio.gather(*tasks, return_exceptions=True),
    timeout=300
)
```

### Result Merging

Agent results are aggregated into a single dict:
```python
state.results = {
    "TradingAgent": {"market_status": "bullish", ...},
    "ResearchAgent": {"analysis": "Rates rising", ...},
    "KnowledgeAgent": {"context": "Fed signals", ...}
}
```

### Backward Compatibility

Single-agent workflows continue to work:
```json
{
  "agents": ["TradingAgent"]  // Old API still works
}
```

The router detects single-agent mode and executes the agent directly.

## Deployment

Emy Brain service runs on **port 8001** (separate from Phase 1a gateway on port 8000).

- Brain service: `http://localhost:8001`
- Gateway: `http://localhost:8000`

## Next Steps

- Week 3: WebSocket integration for real-time job tracking
- Week 4: Error handling and job resumption capability
- Week 5: Production hardening and Render deployment
