# Emy Phase 3 Week 2: Multi-Agent Coordination

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable parallel execution of multiple agents within a single workflow, allowing orchestration of diverse agent perspectives on the same task.

**Architecture:** Extend LangGraph to support agent grouping and parallel execution. When a workflow specifies multiple agents, spawn them concurrently, aggregate results, and merge state updates. Agent groups execute in sequence; agents within a group execute in parallel.

**Tech Stack:** LangGraph async execution, Python asyncio.gather(), state merging utilities

---

## Week 2 Objectives

| Objective | Metric | Why |
|-----------|--------|-----|
| Parallel agent execution | ≤3 agents run concurrently | Unlock multi-perspective analysis (e.g., market health from Trading + Research + Knowledge) |
| Agent grouping | Support 2-3 sequential groups | Enable orchestration patterns (analyze → synthesize → act) |
| Result aggregation | Merge results into state.results keyed by agent name | Preserve results from all agents |
| State synchronization | No race conditions in concurrent execution | Ensure consistency under parallel load |
| Backward compatibility | Single-agent workflows unchanged | Existing integrations continue to work |

---

## Implementation Plan

### Task 1: Extend EMyState for agent grouping

**Files:**
- Modify: `emy/brain/state.py:18-53` (EMyState dataclass)
- Test: `tests/brain/test_state.py`

**Step 1: Write failing test for agent grouping**

```python
def test_state_with_agent_groups():
    """Test that state supports agent groups."""
    state = create_initial_state_with_groups(
        workflow_type="market_analysis",
        agent_groups=[
            ["TradingAgent", "ResearchAgent"],  # Group 1: run in parallel
            ["KnowledgeAgent"]  # Group 2: run sequentially after Group 1
        ],
        input={"query": "Analyze EUR/USD"}
    )

    assert state.agent_groups == [
        ["TradingAgent", "ResearchAgent"],
        ["KnowledgeAgent"]
    ]
    assert state.agents == ["TradingAgent", "ResearchAgent", "KnowledgeAgent"]  # Flat list for backward compat
    assert state.current_group_index == 0
    assert state.agents_executing == []  # Track which agents are currently running
```

**Step 2: Update EMyState dataclass**

Add three new fields to EMyState (after `agents: List[str]`):

```python
agent_groups: List[List[str]] = field(default_factory=list)  # Agent groups for parallel execution
current_group_index: int = 0  # Which group is currently executing
agents_executing: List[str] = field(default_factory=list)  # Agents currently running in current group
```

**Step 3: Create `create_initial_state_with_groups()` factory**

```python
def create_initial_state_with_groups(
    workflow_type: str,
    agent_groups: List[List[str]],
    input: Dict[str, Any],
    workflow_id: Optional[str] = None
) -> EMyState:
    """
    Create initial state with agent grouping for parallel execution.

    Args:
        workflow_type: Type of workflow
        agent_groups: List of agent groups (each group runs in parallel, groups run sequentially)
        input: User input data
        workflow_id: Optional workflow ID

    Returns:
        Initial EMyState with agent_groups set and flat agents list for backward compatibility
    """
    # Flatten groups into single agents list (backward compatibility)
    flat_agents = [agent for group in agent_groups for agent in group]

    state = create_initial_state(
        workflow_type=workflow_type,
        agents=flat_agents,
        input=input,
        workflow_id=workflow_id
    )

    # Add grouping fields
    state.agent_groups = agent_groups
    state.current_group_index = 0
    state.agents_executing = []

    return state
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/brain/test_state.py::test_state_with_agent_groups -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add emy/brain/state.py tests/brain/test_state.py
git commit -m "feat: Extend EMyState with agent grouping support for parallel execution"
```

---

### Task 2: Create parallel agent executor node

**Files:**
- Create: `emy/brain/executor.py`
- Test: `tests/brain/test_executor.py`

**Step 1: Write failing test**

```python
import pytest
import asyncio
from emy.brain.executor import execute_agent_group_parallel
from emy.brain.state import create_initial_state_with_groups

@pytest.mark.asyncio
async def test_execute_agent_group_parallel_with_two_agents():
    """Test that two agents in a group execute concurrently."""
    state = create_initial_state_with_groups(
        workflow_type="test",
        agent_groups=[["TradingAgent", "KnowledgeAgent"]],
        input={"query": "Test"}
    )

    # Execute the group
    result = await execute_agent_group_parallel(state)

    # Both agents should have results
    assert "TradingAgent" in result.results
    assert "KnowledgeAgent" in result.results

    # agents_executing should be set (or cleared after execution)
    assert result.current_group_index == 0
    assert len(result.agents_executing) == 2  # Both agents were executing

    # Messages should include both agent executions
    assert any("TradingAgent" in msg.get("agent", "") for msg in result.messages)
    assert any("KnowledgeAgent" in msg.get("agent", "") for msg in result.messages)
```

**Step 2: Create executor module**

```python
"""Parallel agent executor for LangGraph."""

import asyncio
import logging
from typing import Type
from emy.brain.state import EMyState
from emy.agents.base_agent import EMySubAgent
from emy.brain.nodes import AGENT_REGISTRY

logger = logging.getLogger('EMyBrain.Executor')


async def execute_agent_group_parallel(state: EMyState) -> EMyState:
    """
    Execute all agents in the current group in parallel.

    Args:
        state: Current EMyState with agent_groups set

    Returns:
        Updated state with results from all agents in the group
    """
    if not state.agent_groups or state.current_group_index >= len(state.agent_groups):
        logger.warning(f"Invalid group index {state.current_group_index}")
        return state

    # Get current group
    current_group = state.agent_groups[state.current_group_index]
    state.agents_executing = current_group.copy()

    logger.info(f"Executing agent group {state.current_group_index}: {current_group}")

    # Create tasks for all agents in the group
    tasks = []
    for agent_name in current_group:
        task = execute_single_agent(agent_name, state)
        tasks.append(task)

    # Run all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge results into state
    for agent_name, result in zip(current_group, results):
        if isinstance(result, Exception):
            state.results[agent_name] = {"error": str(result)}
            state.messages.append({
                "agent": agent_name,
                "message": f"Failed: {str(result)}"
            })
            logger.error(f"Agent {agent_name} failed: {result}")
        else:
            success, output = result
            state.results[agent_name] = output
            state.messages.append({
                "agent": agent_name,
                "message": f"Completed: {success}"
            })
            logger.info(f"Agent {agent_name} completed: {success}")

    # Move to next group
    state.current_group_index += 1
    state.agents_executing = []

    return state


async def execute_single_agent(agent_name: str, state: EMyState) -> tuple:
    """
    Execute a single agent asynchronously.

    Args:
        agent_name: Name of agent to execute
        state: Current workflow state

    Returns:
        (success: bool, results: dict) from agent.run()
    """
    if agent_name not in AGENT_REGISTRY:
        raise ValueError(f"Agent {agent_name} not found in registry")

    agent_class: Type[EMySubAgent] = AGENT_REGISTRY[agent_name]
    agent = agent_class()

    logger.info(f"Starting agent {agent_name}")

    # Run agent (blocking call, but executed in parallel via asyncio.gather)
    success, output = agent.run()

    return (success, output)
```

**Step 3: Run test**

```bash
pytest tests/brain/test_executor.py::test_execute_agent_group_parallel_with_two_agents -v
```

Expected: PASS (both agents execute, results aggregated)

**Step 4: Write integration test for sequential groups**

```python
@pytest.mark.asyncio
async def test_execute_multiple_groups_sequentially():
    """Test that groups execute sequentially."""
    state = create_initial_state_with_groups(
        workflow_type="test",
        agent_groups=[
            ["TradingAgent"],  # Group 0
            ["KnowledgeAgent", "ResearchAgent"]  # Group 1
        ],
        input={"query": "Test"}
    )

    # Execute first group
    state = await execute_agent_group_parallel(state)
    assert state.current_group_index == 1
    assert "TradingAgent" in state.results

    # Execute second group (both agents in parallel)
    state = await execute_agent_group_parallel(state)
    assert state.current_group_index == 2
    assert "KnowledgeAgent" in state.results
    assert "ResearchAgent" in state.results
```

**Step 5: Commit**

```bash
git add emy/brain/executor.py tests/brain/test_executor.py
git commit -m "feat: Add parallel agent executor for concurrent execution within groups"
```

---

### Task 3: Update LangGraph to use parallel executor

**Files:**
- Modify: `emy/brain/graph.py:1-130`
- Modify: `emy/brain/nodes.py:25-52` (router logic)
- Test: `tests/brain/test_graph.py`

**Step 1: Write failing test for new graph with parallel execution**

```python
@pytest.mark.asyncio
async def test_graph_with_agent_groups_executes_parallel():
    """Test that graph supports agent groups and executes them."""
    from emy.brain.state import create_initial_state_with_groups

    state = create_initial_state_with_groups(
        workflow_type="market_analysis",
        agent_groups=[
            ["TradingAgent"],
            ["KnowledgeAgent"]
        ],
        input={"query": "Check market"}
    )

    graph = build_graph()
    result = await execute_workflow(state)

    # Both groups should have executed
    assert result.current_group_index == 2  # Both groups processed
    assert "TradingAgent" in result.results
    assert "KnowledgeAgent" in result.results
```

**Step 2: Update router_node to handle groups**

```python
async def router_node(state: EMyState) -> EMyState:
    """
    Route workflow to next agent group.

    If agent_groups is set, execute first group. Otherwise use agents list (backward compat).
    """
    # Check if using agent groups
    if state.agent_groups and state.current_group_index < len(state.agent_groups):
        current_group = state.agent_groups[state.current_group_index]
        logger.info(f"Routing to agent group {state.current_group_index}: {current_group}")
    elif state.agents and len(state.agents) > 0:
        # Backward compatibility: single agent mode
        next_agent = state.agents[0]
        state.current_agent = next_agent
        logger.info(f"Routing to agent {next_agent} (backward compat mode)")
    else:
        logger.warning(f"No agents specified for workflow {state.workflow_id}")

    state.status = "executing"
    state.messages.append({
        "agent": "Router",
        "message": f"Routing to group {state.current_group_index}" if state.agent_groups else f"Routing to {state.current_agent}"
    })

    return state
```

**Step 3: Create new agent_group_node in nodes.py**

```python
def create_agent_group_node():
    """
    Create a LangGraph node for executing an agent group in parallel.

    Returns:
        Async function that executes the current group and updates state
    """
    async def agent_group_node(state: EMyState) -> EMyState:
        """
        Execute all agents in current group in parallel.
        """
        from emy.brain.executor import execute_agent_group_parallel

        if not state.agent_groups or state.current_group_index >= len(state.agent_groups):
            logger.info(f"No more agent groups to execute")
            return state

        logger.info(f"Executing agent group {state.current_group_index}")

        try:
            result = await execute_agent_group_parallel(state)
            result.status = "completed"
            return result
        except Exception as e:
            state.error = f"Agent group execution failed: {str(e)}"
            state.status = "failed"
            logger.exception(f"Agent group execution error")
            return state

    return agent_group_node
```

**Step 4: Update build_graph() to support both modes**

```python
def build_graph():
    """
    Build LangGraph with support for both single-agent and multi-agent modes.
    """
    from langgraph.graph import StateGraph, END

    workflow = StateGraph(EMyState)

    # Add router node
    workflow.add_node("router", router_node)

    # Add agent group executor (for parallel execution)
    workflow.add_node("agent_group_executor", create_agent_group_node())

    # Add individual agent nodes (for backward compatibility)
    for agent_name in AGENT_REGISTRY.keys():
        workflow.add_node(agent_name, create_agent_node(agent_name))

    # Router decides which path: agent groups or individual agents
    def route_after_router(state: EMyState) -> str:
        if state.agent_groups:
            return "agent_group_executor"
        elif state.current_agent:
            return state.current_agent
        else:
            return END

    workflow.add_conditional_edges("router", route_after_router, {
        "agent_group_executor": "agent_group_executor",
        **{agent_name: agent_name for agent_name in AGENT_REGISTRY.keys()},
        END: END
    })

    # From agent group executor, loop back to router if more groups exist
    def route_after_group_execution(state: EMyState) -> str:
        if state.agent_groups and state.current_group_index < len(state.agent_groups):
            return "router"  # Execute next group
        else:
            return END  # All groups complete

    workflow.add_conditional_edges("agent_group_executor", route_after_group_execution, {
        "router": "router",
        END: END
    })

    # Individual agents go to END (backward compat)
    for agent_name in AGENT_REGISTRY.keys():
        workflow.add_edge(agent_name, END)

    # Set entry point
    workflow.set_entry_point("router")

    return workflow.compile()
```

**Step 5: Run test**

```bash
pytest tests/brain/test_graph.py::test_graph_with_agent_groups_executes_parallel -v
```

Expected: PASS

**Step 6: Run integration test to verify backward compatibility**

```bash
pytest tests/brain/test_integration.py -v
```

Expected: All existing tests still pass (single-agent mode unchanged)

**Step 7: Commit**

```bash
git add emy/brain/graph.py emy/brain/nodes.py tests/brain/test_graph.py
git commit -m "feat: Extend LangGraph with parallel agent group execution while maintaining backward compatibility"
```

---

### Task 4: Add state merging utilities

**Files:**
- Create: `emy/brain/merge.py`
- Test: `tests/brain/test_merge.py`

**Step 1: Write failing test for state merging**

```python
from emy.brain.merge import merge_agent_results, aggregate_messages

def test_merge_agent_results_from_parallel_execution():
    """Test merging results from multiple agents."""
    base_results = {
        "TradingAgent": {"market_status": "bullish", "confidence": 0.8}
    }

    new_results = {
        "KnowledgeAgent": {"context": "US Fed meeting"},
        "ResearchAgent": {"analysis": "Rate hikes expected"}
    }

    merged = merge_agent_results(base_results, new_results)

    assert "TradingAgent" in merged
    assert "KnowledgeAgent" in merged
    assert "ResearchAgent" in merged
    assert merged["TradingAgent"]["market_status"] == "bullish"
```

**Step 2: Create merge utilities**

```python
"""Utilities for merging results from parallel agent execution."""

from typing import Dict, Any, List


def merge_agent_results(base: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge agent results into base results.

    Args:
        base: Existing results dict
        new: New results from agents

    Returns:
        Merged results dict with both base and new entries
    """
    merged = base.copy()
    merged.update(new)
    return merged


def aggregate_messages(messages: List[Dict[str, Any]], new_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aggregate audit messages from all agents.

    Args:
        messages: Existing messages
        new_messages: New messages from agents

    Returns:
        Combined messages list (preserves order)
    """
    return messages + new_messages


def aggregate_agent_outputs(agent_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a summary of all agent outputs for dashboard/API response.

    Args:
        agent_results: Dict keyed by agent name with agent outputs

    Returns:
        Aggregated summary with agent perspectives
    """
    summary = {
        "agent_count": len(agent_results),
        "agents": {},
        "insights": []
    }

    for agent_name, output in agent_results.items():
        summary["agents"][agent_name] = output

        # Extract insight if available
        if isinstance(output, dict) and "insight" in output:
            summary["insights"].append({
                "agent": agent_name,
                "insight": output["insight"]
            })

    return summary
```

**Step 3: Run test**

```bash
pytest tests/brain/test_merge.py -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add emy/brain/merge.py tests/brain/test_merge.py
git commit -m "feat: Add result merging utilities for parallel agent aggregation"
```

---

### Task 5: Add agent group routing to FastAPI service

**Files:**
- Modify: `emy/brain/service.py:53-127` (request models)
- Test: `tests/brain/test_service.py`

**Step 1: Write failing test for agent group submission**

```python
def test_submit_job_with_agent_groups(client):
    """Test submitting a job with agent groups."""
    job_data = {
        "workflow_type": "market_analysis",
        "agent_groups": [
            ["TradingAgent", "ResearchAgent"],
            ["KnowledgeAgent"]
        ],
        "input": {"query": "Analyze EUR/USD"}
    }

    response = client.post("/jobs", json=job_data)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["workflow_type"] == "market_analysis"
```

**Step 2: Update JobSubmitRequest model**

```python
class JobSubmitRequest(BaseModel):
    """Request to submit a job (supports both single agent and agent groups)."""
    workflow_type: str
    agents: Optional[List[str]] = None  # Backward compat: single-agent mode
    agent_groups: Optional[List[List[str]]] = None  # Multi-agent mode with grouping
    input: Optional[Dict[str, Any]] = None

    @validator('agents', 'agent_groups', pre=True, always=True)
    def check_agent_specification(cls, v, values):
        """Ensure either agents or agent_groups is specified, but not both."""
        agents = values.get('agents')
        agent_groups = values.get('agent_groups')

        if not agents and not agent_groups:
            raise ValueError('Either agents or agent_groups must be specified')
        if agents and agent_groups:
            raise ValueError('Cannot specify both agents and agent_groups')

        return v
```

**Step 3: Update submit_job endpoint to handle agent_groups**

```python
@app.post('/jobs', response_model=JobResponse)
async def submit_job(request: JobSubmitRequest):
    """
    Submit a new job for execution.

    Supports both:
    - Single agent: agents=["TradingAgent"]
    - Agent groups: agent_groups=[["TradingAgent", "ResearchAgent"], ["KnowledgeAgent"]]
    """
    import uuid

    job_id = f"job_{uuid.uuid4().hex[:8]}"

    # Determine how to create state
    if request.agent_groups:
        from emy.brain.state import create_initial_state_with_groups
        state = create_initial_state_with_groups(
            workflow_type=request.workflow_type,
            agent_groups=request.agent_groups,
            input=request.input or {},
            workflow_id=job_id
        )
    else:
        from emy.brain.state import create_initial_state
        state = create_initial_state(
            workflow_type=request.workflow_type,
            agents=request.agents or [],
            input=request.input or {},
            workflow_id=job_id
        )

    # Store in queue
    from emy.brain.queue import Job

    job_data = {
        "job_id": job_id,
        "workflow_type": request.workflow_type,
        "agents": request.agents or [],
        "agent_groups": request.agent_groups or [],
        "input": request.input or {}
    }

    job = Job(**job_data)
    await job_queue.submit(job)

    logger.info(f"Job {job_id} submitted with {'agent_groups' if request.agent_groups else 'single agent'}")

    return JobResponse(
        job_id=job_id,
        workflow_type=request.workflow_type,
        status='pending',
        created_at=datetime.now().isoformat()
    )
```

**Step 4: Run test**

```bash
pytest tests/brain/test_service.py::test_submit_job_with_agent_groups -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add emy/brain/service.py tests/brain/test_service.py
git commit -m "feat: Add agent_groups parameter to job submission endpoint"
```

---

### Task 6: Update queue schema to persist agent groups

**Files:**
- Modify: `emy/brain/queue.py:30-60` (Job dataclass and schema)
- Modify: `tests/brain/test_queue.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_queue_persist_agent_groups():
    """Test that queue persists and retrieves agent_groups."""
    queue = JobQueue(db_path=":memory:")
    await queue.initialize()

    job = Job(
        job_id="test_groups_001",
        workflow_type="market_analysis",
        agents=[],
        agent_groups=[["TradingAgent", "ResearchAgent"], ["KnowledgeAgent"]],
        input={"query": "Test"}
    )

    await queue.submit(job)

    # Retrieve next job
    next_job = await queue.get_next()
    assert next_job["agent_groups"] == [["TradingAgent", "ResearchAgent"], ["KnowledgeAgent"]]
```

**Step 2: Update Job dataclass**

```python
@dataclass
class Job:
    """Job submission data."""
    job_id: str
    workflow_type: str
    agents: List[str] = field(default_factory=list)  # Backward compat
    agent_groups: List[List[str]] = field(default_factory=list)  # New: agent groups
    input: Dict[str, Any] = field(default_factory=dict)
```

**Step 3: Update queue schema**

Add `agent_groups` column to `jobs` table (JSON):

```python
# In JobQueue.__init__ create_jobs_table():
# Change from:
#   agents TEXT NOT NULL,
# To:
#   agents TEXT NOT NULL,
#   agent_groups TEXT,  -- JSON array of arrays
```

**Step 4: Update queue methods to serialize/deserialize agent_groups**

```python
async def submit(self, job: Job) -> str:
    """Submit a job to the queue."""
    import json

    agent_groups_json = json.dumps(job.agent_groups) if job.agent_groups else "[]"

    with self.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jobs (job_id, workflow_type, agents, agent_groups, input, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            job.job_id,
            job.workflow_type,
            json.dumps(job.agents),
            agent_groups_json,
            json.dumps(job.input),
            'pending'
        ))
        conn.commit()

    return job.job_id
```

**Step 5: Run test**

```bash
pytest tests/brain/test_queue.py::test_queue_persist_agent_groups -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add emy/brain/queue.py tests/brain/test_queue.py
git commit -m "feat: Update job queue to persist and retrieve agent_groups"
```

---

### Task 7: End-to-end test: multi-agent workflow

**Files:**
- Create: `tests/brain/test_multi_agent_workflow.py`

**Step 1: Write comprehensive multi-agent integration test**

```python
import pytest
import pytest_asyncio
from emy.brain.graph import execute_workflow
from emy.brain.state import create_initial_state_with_groups


@pytest.mark.asyncio
async def test_multi_agent_workflow_parallel_execution():
    """
    Test complete multi-agent workflow with parallel execution.

    Simulates: Market Analysis workflow
    - Group 1 (parallel): TradingAgent + ResearchAgent analyze market
    - Group 2 (sequential): KnowledgeAgent synthesizes insights
    """
    state = create_initial_state_with_groups(
        workflow_type="market_analysis",
        agent_groups=[
            ["TradingAgent", "ResearchAgent"],  # Parallel: market analysis
            ["KnowledgeAgent"]  # Sequential: synthesis
        ],
        input={
            "query": "What is the market outlook for EUR/USD?",
            "market_pair": "EUR/USD"
        }
    )

    # Execute workflow
    result = await execute_workflow(state)

    # Verify completion
    assert result.workflow_id == state.workflow_id
    assert result.status in ["completed", "failed"]

    # Verify all groups executed
    assert result.current_group_index == 2  # Both groups processed

    # Verify results from both groups
    assert "TradingAgent" in result.results or result.error is not None
    assert "ResearchAgent" in result.results or result.error is not None
    assert "KnowledgeAgent" in result.results or result.error is not None

    # Verify audit trail
    assert len(result.messages) > 0
    assert any("TradingAgent" in msg.get("agent", "") for msg in result.messages)
    assert any("KnowledgeAgent" in msg.get("agent", "") for msg in result.messages)


@pytest.mark.asyncio
async def test_backward_compatibility_single_agent_unchanged():
    """Verify that single-agent workflows still work (backward compatibility)."""
    from emy.brain.state import create_initial_state

    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    result = await execute_workflow(state)

    # Single-agent workflow should complete
    assert result.status in ["completed", "failed"]
    assert result.current_agent == "TradingAgent"
    assert "TradingAgent" in result.results or result.error is not None
```

**Step 2: Run test**

```bash
pytest tests/brain/test_multi_agent_workflow.py -v
```

Expected: PASS (both multi-agent and backward compat modes work)

**Step 3: Run full test suite to verify nothing broke**

```bash
pytest tests/brain/ -v
```

Expected: All tests passing (24+ tests including new ones)

**Step 4: Commit**

```bash
git add tests/brain/test_multi_agent_workflow.py
git commit -m "feat: Add end-to-end multi-agent workflow tests with parallel execution"
```

---

### Task 8: Documentation and API examples

**Files:**
- Create: `docs/MULTI_AGENT_GUIDE.md`

**Step 1: Write API documentation**

```markdown
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
```

**Step 2: Commit**

```bash
git add docs/MULTI_AGENT_GUIDE.md
git commit -m "docs: Add multi-agent coordination guide and API examples"
```

---

## Execution Order & Dependencies

| Task | Depends On | Est. Time |
|------|-----------|-----------|
| 1. Extend EMyState | — | 15 min |
| 2. Create executor | 1 | 20 min |
| 3. Update LangGraph | 2 | 25 min |
| 4. Merge utilities | — | 10 min |
| 5. Update FastAPI | 1, 4 | 15 min |
| 6. Update queue | 5 | 10 min |
| 7. Integration test | 3, 6 | 10 min |
| 8. Documentation | 7 | 10 min |

**Total: ~115 minutes = 2 hours for complete Week 2 implementation**

**Sequential flow:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

---

## Verification Checklist

After completing all tasks:

- [ ] All 30+ tests pass (Week 1: 24 + Week 2: new tests)
- [ ] Single-agent workflows (backward compat) unchanged
- [ ] Multi-agent parallel execution verified in tests
- [ ] Agent group result aggregation working
- [ ] FastAPI service accepts both `agents` and `agent_groups`
- [ ] Queue persists agent_groups in database
- [ ] Documentation examples work end-to-end
- [ ] No conflicts with existing Phase 1a/2 code

---

## Success Criteria

| Criterion | Metric | Pass |
|-----------|--------|------|
| Parallel execution | ≤3 agents run concurrently (verified in test) | ✓ |
| Backward compatibility | Single-agent workflows unchanged | ✓ |
| Result aggregation | All agent results merged in state.results | ✓ |
| API usability | agent_groups parameter accepted and processed | ✓ |
| Testing | 30+ tests passing, 0 failures | ✓ |
| Documentation | API guide with examples | ✓ |

---

## Deployment Notes

**Week 2 is ready to deploy to Render after all tests pass.**

- Brain service runs on port 8001 (separate from Phase 1a gateway on 8000)
- Backward compatibility ensures no breaking changes to existing integrations
- Parallel execution optimizes response time for multi-agent workflows
- Next Week 3 can focus on dashboard integration (WebSocket, real-time updates)

