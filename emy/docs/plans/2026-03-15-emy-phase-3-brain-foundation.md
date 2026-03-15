# Emy Phase 3: Brain Foundation (LangGraph) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build Emy Brain service with LangGraph-powered async orchestration, enabling multi-agent coordination and autonomous request handling for OpenClaw parity.

**Architecture:**
- New `emy_brain` service running on Render (separate from existing FastAPI gateway)
- LangGraph state graph manages task execution, agent coordination, and result persistence
- AsyncIO job queue handles concurrent workflow execution with resumption capability
- REST API + WebSocket layer enables dashboard integration and real-time status updates
- Existing agents (Trading, Knowledge, Research, ProjectMonitor) integrate as LangGraph nodes

**Tech Stack:** LangGraph (langgraph 0.1.x), AsyncIO, SQLite (existing DB), FastAPI, WebSocket, Claude API

**Timeline:** March 15-April 1, 2026 (17 days)

**Success Metrics:**
- ✅ LangGraph state graph with 5 agent nodes operational
- ✅ Async job queue submitting and executing tasks
- ✅ Multi-agent workflow (Router → TradingAgent → KnowledgeAgent) completes end-to-end
- ✅ Dashboard receives real-time status via WebSocket
- ✅ Failed jobs resume without data loss
- ✅ 30+ tests passing (LangGraph, queue, integration)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ User Interface (Dashboard)                                  │
│ - REST API calls to Gateway (Phase 1a - EXISTING)           │
│ - WebSocket connection to Emy Brain (NEW)                   │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
           │                              │
    ┌──────▼──────┐            ┌──────────▼─────────┐
    │ Phase 1a     │            │ Emy Brain (NEW)    │
    │ Gateway      │            │ LangGraph Service  │
    │ (FastAPI)    │            │                    │
    │ - Health ✅  │            │ - Async queue      │
    │ - Workflows  │            │ - State graph      │
    │ - Agents     │            │ - WebSocket        │
    │ - History    │            │ - Job executor     │
    └──────┬───────┘            └──────────┬─────────┘
           │                              │
           └──────────┬───────────────────┘
                      │
           ┌──────────▼──────────┐
           │ Shared Database     │
           │ (SQLite)            │
           │ - workflows         │
           │ - jobs (NEW)        │
           │ - job_executions    │
           │ - agents            │
           │ - skills            │
           └─────────────────────┘

           ┌──────────┬──────────┬──────────┬──────────┬──────────┐
           │          │          │          │          │          │
           ▼          ▼          ▼          ▼          ▼          ▼
        Trading   Knowledge  Research  ProjectMon   Router    JobSearch
        Agent     Agent      Agent     Agent        Agent     Agent
        (EXISTING - wired into LangGraph nodes)
```

---

## Phase 3 Breakdown: Week 1 vs Week 2

### Week 1 (Mar 15-21): Foundation & Integration
- Days 1-2: LangGraph state graph + database schema
- Days 3-4: Async job queue (submit, track, retrieve)
- Days 5-6: Agent node integration (TradingAgent → LangGraph node)
- Day 7: Integration test (Router → TradingAgent → LangGraph completes)

### Week 2 (Mar 22-29): Multi-Agent & Production
- Days 8-10: Multi-agent coordination (chain agents, share context)
- Days 11-12: REST + WebSocket layer (dashboard integration)
- Days 13-14: Error handling, resumption, monitoring
- Days 15-17: Production hardening, deployment

---

## Task List

### WEEK 1: FOUNDATION & INTEGRATION

---

### Task 1: Create Emy Brain Service Structure

**Files:**
- Create: `emy/brain/__init__.py`
- Create: `emy/brain/service.py` (main service entry point)
- Create: `emy/brain/config.py` (configuration)
- Create: `emy/brain/state.py` (LangGraph state schema)
- Create: `emy/brain/nodes.py` (agent nodes)
- Create: `emy/brain/queue.py` (async job queue)
- Create: `tests/brain/test_brain_integration.py`

**Step 1: Create directory structure and __init__.py**

```bash
mkdir -p emy/brain
mkdir -p tests/brain
touch emy/brain/__init__.py
touch emy/brain/config.py
touch emy/brain/state.py
touch emy/brain/nodes.py
touch emy/brain/queue.py
touch emy/brain/service.py
touch tests/brain/__init__.py
touch tests/brain/test_brain_integration.py
```

**Step 2: Write config.py with environment settings**

File: `emy/brain/config.py`
```python
"""Emy Brain configuration."""
import os
from pathlib import Path

# Service settings
BRAIN_PORT = int(os.getenv("BRAIN_PORT", "8001"))
BRAIN_HOST = os.getenv("BRAIN_HOST", "0.0.0.0")
ENV = os.getenv("ENV", "development")

# Database
DB_PATH = Path(os.getenv("DB_PATH", "emy_brain.db"))

# Job queue
QUEUE_BATCH_SIZE = int(os.getenv("QUEUE_BATCH_SIZE", "10"))
QUEUE_POLL_INTERVAL = int(os.getenv("QUEUE_POLL_INTERVAL", "5"))

# Agent timeouts (seconds)
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "300"))

# LangGraph
LANGGRAPH_DEBUG = os.getenv("LANGGRAPH_DEBUG", "false").lower() == "true"
```

**Step 3: Commit**

```bash
git add emy/brain/ tests/brain/
git commit -m "feat: Initialize Emy Brain service directory structure"
```

---

### Task 2: Define LangGraph State Schema

**Files:**
- Modify: `emy/brain/state.py`
- Test: `tests/brain/test_state.py` (new)

**Step 1: Write failing tests for state schema**

File: `tests/brain/test_state.py`
```python
"""Tests for LangGraph state schema."""
from typing import Any, Dict, List
from emy.brain.state import EMyState, create_initial_state
import pytest


def test_initial_state_creation():
    """Test creating initial state for a workflow."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check market health"}
    )

    assert state.workflow_type == "trading_health"
    assert state.agents == ["TradingAgent"]
    assert state.input == {"query": "Check market health"}
    assert state.current_agent is None
    assert state.results == {}
    assert state.messages == []
    assert state.status == "pending"


def test_state_update_after_agent_execution():
    """Test updating state after an agent processes a task."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    # Simulate agent execution
    state.current_agent = "TradingAgent"
    state.status = "executing"

    assert state.current_agent == "TradingAgent"
    assert state.status == "executing"


def test_state_add_result():
    """Test adding result from an agent execution."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    result = {
        "analysis": "Market is healthy",
        "signals": ["BUY", "HOLD"],
        "timestamp": "2026-03-15T12:00:00Z"
    }

    state.results["TradingAgent"] = result

    assert "TradingAgent" in state.results
    assert state.results["TradingAgent"] == result


def test_state_add_message():
    """Test adding a message to state for audit trail."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    state.messages.append({
        "agent": "Router",
        "message": "Routing to TradingAgent"
    })

    assert len(state.messages) == 1
    assert state.messages[0]["agent"] == "Router"
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/brain/test_state.py -v
# Expected: FAILED - module 'emy.brain.state' has no attribute 'EMyState'
```

**Step 3: Implement state schema**

File: `emy/brain/state.py`
```python
"""LangGraph state schema for Emy Brain."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    RESUMING = "resuming"


@dataclass
class EMyState:
    """
    LangGraph state for Emy Brain.

    Represents the execution context for a workflow across all agents.
    Persists to database for resumption capability.
    """
    # Workflow identification
    workflow_id: str  # Unique ID for this workflow execution
    workflow_type: str  # Type of workflow (e.g., "trading_health", "job_search")

    # Agent coordination
    agents: List[str]  # List of agent names that can be used
    current_agent: Optional[str] = None  # Which agent is currently processing

    # User input and context
    input: Dict[str, Any] = field(default_factory=dict)  # Original user input

    # Execution results
    results: Dict[str, Any] = field(default_factory=dict)  # Results keyed by agent name

    # Audit trail
    messages: List[Dict[str, Any]] = field(default_factory=list)  # Execution trace

    # Status tracking
    status: JobStatus = JobStatus.PENDING

    # Timestamps
    created_at: str = ""  # ISO 8601 timestamp
    updated_at: str = ""  # ISO 8601 timestamp

    # Error handling
    error: Optional[str] = None
    error_context: Dict[str, Any] = field(default_factory=dict)


def create_initial_state(
    workflow_type: str,
    agents: List[str],
    input: Dict[str, Any],
    workflow_id: Optional[str] = None
) -> EMyState:
    """
    Create initial state for a new workflow.

    Args:
        workflow_type: Type of workflow (e.g., "trading_health")
        agents: List of available agents
        input: User input/query
        workflow_id: Optional pre-generated ID (usually from job queue)

    Returns:
        Initial EMyState ready for LangGraph execution
    """
    from datetime import datetime
    import uuid

    if workflow_id is None:
        workflow_id = f"wf_{uuid.uuid4().hex[:8]}"

    now = datetime.utcnow().isoformat()

    return EMyState(
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        agents=agents,
        input=input,
        created_at=now,
        updated_at=now,
        status=JobStatus.PENDING
    )


def to_dict(state: EMyState) -> Dict[str, Any]:
    """Convert state to dictionary for database storage."""
    return {
        "workflow_id": state.workflow_id,
        "workflow_type": state.workflow_type,
        "agents": state.agents,
        "current_agent": state.current_agent,
        "input": state.input,
        "results": state.results,
        "messages": state.messages,
        "status": state.status.value,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
        "error": state.error,
        "error_context": state.error_context
    }


def from_dict(data: Dict[str, Any]) -> EMyState:
    """Reconstruct state from database dictionary."""
    return EMyState(
        workflow_id=data["workflow_id"],
        workflow_type=data["workflow_type"],
        agents=data["agents"],
        current_agent=data.get("current_agent"),
        input=data.get("input", {}),
        results=data.get("results", {}),
        messages=data.get("messages", []),
        status=JobStatus(data.get("status", "pending")),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        error=data.get("error"),
        error_context=data.get("error_context", {})
    )
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/brain/test_state.py -v
# Expected: PASSED (4 passed)
```

**Step 5: Commit**

```bash
git add emy/brain/state.py tests/brain/test_state.py
git commit -m "feat: Define EMyState schema for LangGraph"
```

---

### Task 3: Create Async Job Queue

**Files:**
- Modify: `emy/brain/queue.py`
- Test: `tests/brain/test_queue.py` (new)
- Modify: `emy/core/database.py` (add job tables)

**Step 1: Add job tables to database schema**

File: `emy/core/database.py` - Add to `initialize_schema()` method:

```python
# Add these CREATE TABLE statements to initialize_schema() in EMyDatabase

# Jobs table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        workflow_type TEXT NOT NULL,
        agents TEXT NOT NULL,
        input TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT NOT NULL,
        started_at TEXT,
        completed_at TEXT,
        error TEXT
    )
""")

# Job executions table (for tracking retries and resumption)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_executions (
        execution_id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        input TEXT,
        output TEXT,
        error TEXT,
        created_at TEXT NOT NULL,
        completed_at TEXT,
        FOREIGN KEY (job_id) REFERENCES jobs(job_id)
    )
""")
```

**Step 2: Write failing tests for job queue**

File: `tests/brain/test_queue.py`
```python
"""Tests for async job queue."""
import pytest
import asyncio
from emy.brain.queue import JobQueue, Job
from datetime import datetime


@pytest.fixture
def job_queue():
    """Create a job queue for testing."""
    return JobQueue()


@pytest.mark.asyncio
async def test_submit_job(job_queue):
    """Test submitting a job to the queue."""
    job = Job(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    job_id = await job_queue.submit(job)

    assert job_id is not None
    assert job_id.startswith("job_")


@pytest.mark.asyncio
async def test_get_job_status(job_queue):
    """Test retrieving job status."""
    job = Job(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    job_id = await job_queue.submit(job)
    status = await job_queue.get_status(job_id)

    assert status == "pending"


@pytest.mark.asyncio
async def test_retrieve_pending_job(job_queue):
    """Test retrieving next pending job."""
    job = Job(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    job_id = await job_queue.submit(job)
    pending_job = await job_queue.get_next()

    assert pending_job is not None
    assert pending_job["job_id"] == job_id


@pytest.mark.asyncio
async def test_mark_job_complete(job_queue):
    """Test marking a job as completed."""
    job = Job(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    job_id = await job_queue.submit(job)
    result = {"analysis": "Healthy"}

    await job_queue.mark_complete(job_id, result)
    status = await job_queue.get_status(job_id)

    assert status == "completed"
```

**Step 3: Run tests to verify they fail**

```bash
pytest tests/brain/test_queue.py -v
# Expected: FAILED - module 'emy.brain.queue' has no attribute 'JobQueue'
```

**Step 4: Implement async job queue**

File: `emy/brain/queue.py`
```python
"""Async job queue for Emy Brain."""
import asyncio
import uuid
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
from emy.core.database import EMyDatabase


@dataclass
class Job:
    """A job submitted to the queue."""
    workflow_type: str
    agents: List[str]
    input: Dict[str, Any]
    job_id: Optional[str] = None

    def __post_init__(self):
        if self.job_id is None:
            self.job_id = f"job_{uuid.uuid4().hex[:8]}"


class JobQueue:
    """
    Async job queue for managing workflow execution.

    Features:
    - Submit jobs and get back job IDs
    - Retrieve pending jobs for execution
    - Track job status (pending, executing, completed, failed)
    - Persist to database for resumption
    """

    def __init__(self):
        """Initialize job queue with database connection."""
        self.db = EMyDatabase()
        self._executing = set()  # Jobs currently being processed

    async def submit(self, job: Job) -> str:
        """
        Submit a job to the queue.

        Args:
            job: Job to submit

        Returns:
            Job ID
        """
        now = datetime.utcnow().isoformat()

        self.db.execute(
            """
            INSERT INTO jobs (job_id, workflow_type, agents, input, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                job.job_id,
                job.workflow_type,
                json.dumps(job.agents),
                json.dumps(job.input),
                "pending",
                now
            )
        )

        return job.job_id

    async def get_status(self, job_id: str) -> str:
        """
        Get the status of a job.

        Args:
            job_id: ID of the job

        Returns:
            Status string (pending, executing, completed, failed)
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            return row["status"] if row else None

    async def get_next(self) -> Optional[Dict[str, Any]]:
        """
        Get next pending job from queue.

        Returns:
            Job dict or None if queue is empty
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT job_id, workflow_type, agents, input
                FROM jobs
                WHERE status = 'pending'
                LIMIT 1
                """
            )
            row = cursor.fetchone()

            if row:
                return {
                    "job_id": row["job_id"],
                    "workflow_type": row["workflow_type"],
                    "agents": json.loads(row["agents"]),
                    "input": json.loads(row["input"])
                }
            return None

    async def mark_executing(self, job_id: str) -> None:
        """Mark a job as currently executing."""
        now = datetime.utcnow().isoformat()
        self.db.execute(
            "UPDATE jobs SET status = 'executing', started_at = ? WHERE job_id = ?",
            (now, job_id)
        )
        self._executing.add(job_id)

    async def mark_complete(self, job_id: str, result: Dict[str, Any]) -> None:
        """Mark a job as completed with result."""
        now = datetime.utcnow().isoformat()
        self.db.execute(
            """
            UPDATE jobs
            SET status = 'completed', completed_at = ?, output = ?
            WHERE job_id = ?
            """,
            (now, json.dumps(result), job_id)
        )
        self._executing.discard(job_id)

    async def mark_failed(self, job_id: str, error: str) -> None:
        """Mark a job as failed with error message."""
        now = datetime.utcnow().isoformat()
        self.db.execute(
            """
            UPDATE jobs
            SET status = 'failed', completed_at = ?, error = ?
            WHERE job_id = ?
            """,
            (now, error, job_id)
        )
        self._executing.discard(job_id)

    async def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve result of a completed job."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT output FROM jobs WHERE job_id = ? AND status = 'completed'",
                (job_id,)
            )
            row = cursor.fetchone()
            return json.loads(row["output"]) if row else None
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/brain/test_queue.py -v
# Expected: PASSED (5 passed)
```

**Step 6: Commit**

```bash
git add emy/brain/queue.py tests/brain/test_queue.py emy/core/database.py
git commit -m "feat: Implement async job queue with database persistence"
```

---

### Task 4: Wire First Agent into LangGraph (TradingAgent)

**Files:**
- Modify: `emy/brain/nodes.py`
- Test: `tests/brain/test_nodes.py` (new)
- Modify: `emy/agents/trading_agent.py` (add LangGraph-compatible method)

**Step 1: Write failing test for agent node**

File: `tests/brain/test_nodes.py`
```python
"""Tests for LangGraph agent nodes."""
import pytest
from emy.brain.nodes import create_agent_node, router_node
from emy.brain.state import EMyState, JobStatus, create_initial_state


@pytest.mark.asyncio
async def test_router_node_selects_trading_agent():
    """Test router node selects TradingAgent for trading_health workflow."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check market health"}
    )

    result = await router_node(state)

    assert result["current_agent"] == "TradingAgent"
    assert result["status"] == JobStatus.EXECUTING


@pytest.mark.asyncio
async def test_agent_node_executes():
    """Test executing TradingAgent through node."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )
    state.current_agent = "TradingAgent"

    # Get the trading agent node
    trading_node = create_agent_node("TradingAgent")
    result = await trading_node(state)

    assert "TradingAgent" in result["results"]
    assert result["results"]["TradingAgent"] is not None
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/brain/test_nodes.py -v
# Expected: FAILED - module has no attribute 'create_agent_node'
```

**Step 3: Implement agent nodes**

File: `emy/brain/nodes.py`
```python
"""LangGraph nodes for Emy agents."""
from typing import Any, Dict, Callable, Awaitable
from emy.brain.state import EMyState, JobStatus
from emy.agents.trading_agent import TradingAgent
from emy.agents.knowledge_agent import KnowledgeAgent
from emy.agents.research_agent import ResearchAgent
from emy.agents.project_monitor_agent import ProjectMonitorAgent
import logging

logger = logging.getLogger(__name__)


# Agent registry - maps agent names to their classes
AGENT_REGISTRY = {
    "TradingAgent": TradingAgent,
    "KnowledgeAgent": KnowledgeAgent,
    "ResearchAgent": ResearchAgent,
    "ProjectMonitorAgent": ProjectMonitorAgent,
}


async def router_node(state: EMyState) -> Dict[str, Any]:
    """
    Router node - determines which agent should handle the request.

    For now, uses simple routing based on workflow type.
    Could be enhanced with Claude-based routing later.
    """
    logger.info(f"Router: Routing workflow {state.workflow_type}")

    # Simple routing: pick first agent (should match workflow type)
    if state.agents:
        current_agent = state.agents[0]
        state.current_agent = current_agent
        state.status = JobStatus.EXECUTING
        state.messages.append({
            "agent": "Router",
            "message": f"Routing to {current_agent}"
        })

    return {
        "current_agent": state.current_agent,
        "status": state.status,
        "messages": state.messages
    }


def create_agent_node(agent_name: str) -> Callable[[EMyState], Awaitable[Dict[str, Any]]]:
    """
    Create a node that executes a specific agent.

    Args:
        agent_name: Name of agent (e.g., "TradingAgent")

    Returns:
        Async function that executes the agent and returns results
    """

    async def agent_node(state: EMyState) -> Dict[str, Any]:
        """Execute an agent and return results."""
        logger.info(f"Executing {agent_name}")

        try:
            # Get agent class
            agent_class = AGENT_REGISTRY.get(agent_name)
            if not agent_class:
                raise ValueError(f"Unknown agent: {agent_name}")

            # Instantiate agent
            agent = agent_class()

            # Execute agent (assume agents have an execute() method)
            # For TradingAgent, this might be execute_workflow()
            if hasattr(agent, 'execute_workflow'):
                success, output = agent.execute_workflow(
                    state.workflow_type,
                    state.input
                )
            elif hasattr(agent, 'execute'):
                success, output = agent.execute(state.workflow_type, state.input)
            else:
                raise NotImplementedError(f"{agent_name} has no execute method")

            # Store result
            state.results[agent_name] = output
            state.messages.append({
                "agent": agent_name,
                "message": "Execution completed",
                "success": success
            })

            if success:
                state.status = JobStatus.COMPLETED
            else:
                state.status = JobStatus.FAILED
                state.error = "Agent execution failed"

        except Exception as e:
            logger.error(f"Error executing {agent_name}: {e}")
            state.status = JobStatus.FAILED
            state.error = str(e)
            state.messages.append({
                "agent": agent_name,
                "message": f"Error: {e}"
            })

        return {
            "results": state.results,
            "status": state.status,
            "error": state.error,
            "messages": state.messages
        }

    return agent_node


# Placeholder nodes for other agents (will be filled in later)
async def knowledge_agent_node(state: EMyState) -> Dict[str, Any]:
    """Placeholder for KnowledgeAgent node."""
    return {"results": state.results}


async def research_agent_node(state: EMyState) -> Dict[str, Any]:
    """Placeholder for ResearchAgent node."""
    return {"results": state.results}


async def project_monitor_node(state: EMyState) -> Dict[str, Any]:
    """Placeholder for ProjectMonitorAgent node."""
    return {"results": state.results}
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/brain/test_nodes.py -v
# Expected: PASSED (2 passed)
```

**Step 5: Commit**

```bash
git add emy/brain/nodes.py tests/brain/test_nodes.py
git commit -m "feat: Create LangGraph nodes for agent execution"
```

---

### Task 5: Build LangGraph State Graph

**Files:**
- Create: `emy/brain/graph.py` (LangGraph workflow definition)
- Test: `tests/brain/test_graph.py` (new)

**Step 1: Write failing test for state graph**

File: `tests/brain/test_graph.py`
```python
"""Tests for LangGraph state graph."""
import pytest
import asyncio
from emy.brain.graph import build_graph, execute_workflow
from emy.brain.state import create_initial_state, JobStatus


@pytest.mark.asyncio
async def test_build_graph_creates_graph():
    """Test that build_graph creates a valid StateGraph."""
    graph = build_graph()
    assert graph is not None
    # Check that graph has nodes
    assert len(graph.nodes) > 0


@pytest.mark.asyncio
async def test_execute_workflow_simple():
    """Test executing a simple workflow through the graph."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    result_state = await execute_workflow(state)

    assert result_state is not None
    assert result_state.status in [JobStatus.COMPLETED, JobStatus.FAILED]


@pytest.mark.asyncio
async def test_workflow_state_persisted():
    """Test that workflow state is properly updated through execution."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    initial_messages = len(state.messages)
    result_state = await execute_workflow(state)

    # Should have added messages during execution
    assert len(result_state.messages) > initial_messages
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/brain/test_graph.py -v
# Expected: FAILED - module has no attribute 'build_graph'
```

**Step 3: Implement LangGraph state graph**

File: `emy/brain/graph.py`
```python
"""LangGraph state graph for Emy Brain."""
from langgraph.graph import StateGraph, END
from typing import Dict, Any, Annotated, Sequence
from emy.brain.state import EMyState, JobStatus
from emy.brain.nodes import router_node, create_agent_node
import logging

logger = logging.getLogger(__name__)


def build_graph() -> StateGraph:
    """
    Build the LangGraph state graph for Emy Brain.

    Graph structure:
    - Start → Router
    - Router → AgentNode(TradingAgent | KnowledgeAgent | ...)
    - AgentNode → End

    Returns:
        Compiled StateGraph ready for execution
    """

    # Create state graph
    graph = StateGraph(EMyState)

    # Add router node
    graph.add_node("router", router_node)

    # Add agent nodes dynamically for each registered agent
    agent_names = [
        "TradingAgent",
        "KnowledgeAgent",
        "ResearchAgent",
        "ProjectMonitorAgent"
    ]

    for agent_name in agent_names:
        agent_node = create_agent_node(agent_name)
        graph.add_node(agent_name, agent_node)

    # Set router as entry point
    graph.set_entry_point("router")

    # Add edges from router to agents
    def route_to_agent(state: EMyState) -> str:
        """Route from router to appropriate agent."""
        if state.current_agent:
            return state.current_agent
        return END

    graph.add_conditional_edges("router", route_to_agent)

    # Add edges from agents to END
    for agent_name in agent_names:
        graph.add_edge(agent_name, END)

    # Compile the graph
    compiled_graph = graph.compile()

    logger.info("LangGraph state graph compiled successfully")
    return compiled_graph


async def execute_workflow(state: EMyState) -> EMyState:
    """
    Execute a workflow through the LangGraph.

    Args:
        state: Initial workflow state

    Returns:
        Final state after graph execution
    """
    logger.info(f"Executing workflow {state.workflow_id}")

    graph = build_graph()

    try:
        # Invoke the graph with initial state
        result = await graph.ainvoke(
            {
                "workflow_id": state.workflow_id,
                "workflow_type": state.workflow_type,
                "agents": state.agents,
                "input": state.input,
                "results": state.results,
                "messages": state.messages,
                "status": state.status,
                "error": state.error,
                "created_at": state.created_at,
                "updated_at": state.updated_at
            }
        )

        # Convert result dict back to EMyState
        final_state = EMyState(**result)
        logger.info(f"Workflow {state.workflow_id} completed with status {final_state.status}")
        return final_state

    except Exception as e:
        logger.error(f"Workflow {state.workflow_id} failed: {e}")
        state.status = JobStatus.FAILED
        state.error = str(e)
        return state
```

**Step 4: Install langgraph dependency**

```bash
pip install langgraph>=0.1.0
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/brain/test_graph.py -v
# Expected: PASSED (3 passed)
```

**Step 6: Commit**

```bash
git add emy/brain/graph.py tests/brain/test_graph.py
git commit -m "feat: Build LangGraph state graph with agent nodes"
```

---

### Task 6: Create FastAPI Service for Emy Brain

**Files:**
- Modify: `emy/brain/service.py`
- Test: `tests/brain/test_service.py` (new)

**Step 1: Write failing tests for service**

File: `tests/brain/test_service.py`
```python
"""Tests for Emy Brain FastAPI service."""
import pytest
from fastapi.testclient import TestClient
from emy.brain.service import app


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_submit_job_endpoint(client):
    """Test submitting a job via API."""
    response = client.post("/jobs", json={
        "workflow_type": "trading_health",
        "agents": ["TradingAgent"],
        "input": {"query": "Check health"}
    })

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_get_job_status_endpoint(client):
    """Test getting job status via API."""
    # First submit a job
    submit_response = client.post("/jobs", json={
        "workflow_type": "trading_health",
        "agents": ["TradingAgent"],
        "input": {"query": "Check health"}
    })
    job_id = submit_response.json()["job_id"]

    # Then retrieve its status
    status_response = client.get(f"/jobs/{job_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "pending"
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/brain/test_service.py -v
# Expected: FAILED - app not defined
```

**Step 3: Implement FastAPI service**

File: `emy/brain/service.py`
```python
"""Emy Brain FastAPI service."""
import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uvicorn

from emy.brain.queue import JobQueue, Job
from emy.brain.state import create_initial_state
from emy.brain.graph import execute_workflow
from emy.core.database import EMyDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Emy Brain",
    description="LangGraph-powered async orchestration for Emy agents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
job_queue = JobQueue()
db = EMyDatabase()

# ============================================================================
# Request/Response Models
# ============================================================================


class JobSubmitRequest(BaseModel):
    """Request to submit a job."""
    workflow_type: str
    agents: list[str]
    input: Dict[str, Any]


class JobResponse(BaseModel):
    """Response containing job information."""
    job_id: str
    workflow_type: str
    status: str
    created_at: str


class JobStatusResponse(BaseModel):
    """Response containing job status."""
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response for health check."""
    status: str
    timestamp: str


# ============================================================================
# Health Check
# ============================================================================


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat()
    )


# ============================================================================
# Job Submission & Status
# ============================================================================


@app.post("/jobs", response_model=JobResponse)
async def submit_job(request: JobSubmitRequest):
    """
    Submit a new job to the queue.

    Args:
        request: Job submission request

    Returns:
        Job details with job_id
    """
    logger.info(f"Submitting job: {request.workflow_type}")

    job = Job(
        workflow_type=request.workflow_type,
        agents=request.agents,
        input=request.input
    )

    job_id = await job_queue.submit(job)

    return JobResponse(
        job_id=job_id,
        workflow_type=request.workflow_type,
        status="pending",
        created_at=datetime.utcnow().isoformat()
    )


@app.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a job.

    Args:
        job_id: ID of the job

    Returns:
        Job status and result (if completed)
    """
    status = await job_queue.get_status(job_id)

    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")

    result = None
    error = None

    if status == "completed":
        result = await job_queue.get_result(job_id)
    elif status == "failed":
        # Retrieve error from database
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT error FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            error = row["error"] if row else "Unknown error"

    return JobStatusResponse(
        job_id=job_id,
        status=status,
        result=result,
        error=error
    )


# ============================================================================
# Job Execution Loop (Background Task)
# ============================================================================


async def job_executor():
    """
    Background task that continuously processes jobs from queue.
    This should be run as a separate asyncio task.
    """
    logger.info("Job executor started")

    while True:
        try:
            # Get next pending job
            job_data = await job_queue.get_next()

            if job_data:
                job_id = job_data["job_id"]
                logger.info(f"Processing job {job_id}")

                # Mark as executing
                await job_queue.mark_executing(job_id)

                # Create initial state
                state = create_initial_state(
                    workflow_type=job_data["workflow_type"],
                    agents=job_data["agents"],
                    input=job_data["input"],
                    workflow_id=job_id
                )

                # Execute through LangGraph
                final_state = await execute_workflow(state)

                # Mark as complete or failed
                if final_state.status.value == "completed":
                    await job_queue.mark_complete(job_id, final_state.results)
                    logger.info(f"Job {job_id} completed")
                else:
                    await job_queue.mark_failed(job_id, final_state.error or "Unknown error")
                    logger.error(f"Job {job_id} failed: {final_state.error}")

            else:
                # No pending jobs, wait a bit before polling again
                import asyncio
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in job executor: {e}")
            import asyncio
            await asyncio.sleep(5)  # Back off on error


# ============================================================================
# Startup/Shutdown
# ============================================================================


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info("Emy Brain service starting...")

    # Initialize database
    db.initialize_schema()

    # Start job executor as background task
    import asyncio
    asyncio.create_task(job_executor())

    logger.info("Emy Brain service started")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Emy Brain service shutting down...")


# ============================================================================
# Main Entry Point
# ============================================================================


if __name__ == "__main__":
    port = int(os.getenv("BRAIN_PORT", "8001"))
    host = os.getenv("BRAIN_HOST", "0.0.0.0")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/brain/test_service.py -v
# Expected: PASSED (3 passed)
```

**Step 5: Commit**

```bash
git add emy/brain/service.py tests/brain/test_service.py
git commit -m "feat: Create FastAPI service for Emy Brain with job queue polling"
```

---

### Task 7: Integration Test - Router → TradingAgent → Complete

**Files:**
- Modify: `tests/brain/test_brain_integration.py`

**Step 1: Write end-to-end integration test**

File: `tests/brain/test_brain_integration.py`
```python
"""End-to-end integration tests for Emy Brain."""
import pytest
import asyncio
from emy.brain.state import create_initial_state, JobStatus
from emy.brain.graph import execute_workflow


@pytest.mark.asyncio
async def test_full_workflow_router_to_trading_agent():
    """
    Integration test: Router → TradingAgent → Complete

    This tests the full flow of a workflow execution:
    1. Create initial state
    2. Submit to graph
    3. Router selects agent
    4. Agent executes
    5. Result stored and state updated
    """
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check market health"}
    )

    # Execute the workflow
    final_state = await execute_workflow(state)

    # Verify workflow completed
    assert final_state is not None
    assert final_state.workflow_id == state.workflow_id
    assert final_state.status in [JobStatus.COMPLETED, JobStatus.FAILED]

    # Verify router executed
    router_messages = [m for m in final_state.messages if m.get("agent") == "Router"]
    assert len(router_messages) > 0

    # Verify agent executed
    agent_messages = [m for m in final_state.messages if m.get("agent") == "TradingAgent"]
    assert len(agent_messages) > 0

    # Verify results were stored
    assert "TradingAgent" in final_state.results
    assert final_state.results["TradingAgent"] is not None
```

**Step 2: Run integration test**

```bash
pytest tests/brain/test_brain_integration.py -v
# Expected: PASSED (1 passed)
```

**Step 3: Commit**

```bash
git add tests/brain/test_brain_integration.py
git commit -m "test: Add end-to-end integration test for Router → TradingAgent flow"
```

---

## WEEK 2: MULTI-AGENT & PRODUCTION (Placeholder - Detailed in Follow-up)

### Task 8: Multi-Agent Coordination (Task → Task chaining)
- Implement agent-to-agent message passing
- Allow one agent to request results from another
- Add context sharing between agents
- Test: Router → TradingAgent → KnowledgeAgent workflow

### Task 9: REST + WebSocket Layer for Dashboard Integration
- Add WebSocket endpoint for real-time job status updates
- Add `/jobs/{job_id}/stream` endpoint
- Integrate with existing web dashboard
- Update dashboard to listen to WebSocket events

### Task 10: Error Handling & Job Resumption
- Implement retry logic with exponential backoff
- Add job pause/resume capability
- Persist execution context for resumption
- Test recovery from agent crashes

### Task 11: Production Hardening
- Add monitoring and metrics (job throughput, duration, error rates)
- Add health checks for agents
- Implement rate limiting and queue prioritization
- Deploy to Render with auto-scaling

---

## Success Criteria (End of Week 1)

By end of Day 7 (March 21, 2026):

- [ ] LangGraph state graph compiles without errors
- [ ] Job queue submits and tracks jobs
- [ ] At least one agent (TradingAgent) executes through LangGraph
- [ ] Router → Agent → Complete flow works end-to-end
- [ ] 30+ tests passing (state, queue, nodes, graph, service, integration)
- [ ] Service runs locally on port 8001
- [ ] All work committed to git with clear commit messages

---

## Database Schema Changes

```sql
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    workflow_type TEXT NOT NULL,
    agents TEXT NOT NULL,          -- JSON array
    input TEXT,                    -- JSON
    output TEXT,                   -- JSON (when completed)
    status TEXT DEFAULT 'pending',  -- pending, executing, completed, failed
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS job_executions (
    execution_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    input TEXT,                    -- JSON
    output TEXT,                   -- JSON
    error TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);
```

---

## Dependencies to Install

```bash
pip install langgraph>=0.1.0
pip install fastapi>=0.104.0
pip install uvicorn[standard]>=0.24.0
pip install python-dotenv>=1.0.0
pip install pytest-asyncio>=0.21.0  # For async tests
```

---

## Architecture Decision Log

| Decision | Rationale |
|----------|-----------|
| Separate service (port 8001) | Enables independent scaling; Phase 1a gateway stays unchanged |
| AsyncIO + async/await | Python native async; integrates cleanly with FastAPI |
| Job queue in SQLite | Persistent; survives crashes; no external dependencies |
| LangGraph nodes as callables | Composable; easy to add/remove agents |
| Minimal Week 1 scope | Focus on foundation; multi-agent coordination deferred to Week 2 |

---

## Execution Notes

- **Use TDD**: Write test first, verify it fails, then implement
- **Frequent commits**: Commit after each task (minimum 7 commits by end of Week 1)
- **Local testing**: Verify each task with `pytest` before moving to next
- **Database**: Reuse existing `EMyDatabase` class; add tables via `initialize_schema()`
- **Agents**: Existing agents (TradingAgent, etc.) should have `execute_workflow()` or `execute()` method; if not, add a thin wrapper

---

## Next Phase (Week 2) Overview

After Week 1 foundation, Week 2 will add:
1. **Multi-agent chaining**: Agent A → Agent B (sequential/parallel)
2. **Context sharing**: Agents read/write shared state fields
3. **WebSocket streaming**: Real-time job status to dashboard
4. **Error recovery**: Pause/resume broken jobs
5. **Production deployment**: Render, monitoring, health checks

---

## Files Checklist (Week 1)

- ✅ `emy/brain/__init__.py`
- ✅ `emy/brain/config.py`
- ✅ `emy/brain/state.py` + `tests/brain/test_state.py`
- ✅ `emy/brain/queue.py` + `tests/brain/test_queue.py`
- ✅ `emy/brain/nodes.py` + `tests/brain/test_nodes.py`
- ✅ `emy/brain/graph.py` + `tests/brain/test_graph.py`
- ✅ `emy/brain/service.py` + `tests/brain/test_service.py`
- ✅ `tests/brain/test_brain_integration.py`
- ✅ `emy/core/database.py` (add job tables)
- ✅ `requirements.txt` (add langgraph, pytest-asyncio)

---

## Quick Commands Reference

```bash
# Run all brain tests
pytest tests/brain/ -v

# Run specific test
pytest tests/brain/test_state.py::test_initial_state_creation -v

# Start Emy Brain service locally
python -m emy.brain.service

# Check database schema
sqlite3 emy_brain.db ".schema jobs"
```

---

**Ready to execute?** Use `superpowers:executing-plans` to implement tasks 1-7 in sequence.
