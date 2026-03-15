# Emy Phase 3 Week 3: Real-Time Orchestration & Production Hardening

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate real-time job tracking via WebSocket, enhance dashboard with multi-agent visualization, implement error recovery, and harden for production deployment.

**Architecture:** Add WebSocket layer to Brain service for streaming job updates. Extend dashboard to show real-time progress, agent execution status, and result aggregation. Implement job resumption and timeout recovery. Harden logging, monitoring, and error handling for Render deployment.

**Tech Stack:** FastAPI WebSocket, client-side event listeners, SQLite transactions, structured logging, Sentry integration (optional)

---

## Week 3 Objectives

| Objective | Metric | Why |
|-----------|--------|-----|
| Real-time job tracking | WebSocket stream job state updates | No polling overhead, instant status visibility |
| Multi-agent dashboard | Visual timeline of group execution | Users see parallel agents running side-by-side |
| Error recovery | Job resumption from checkpoint | Production resilience, user experience |
| Timeout handling | Graceful timeout recovery | Prevent indefinite hangs, clear error messages |
| Production logging | Structured logs for Sentry/monitoring | Debugging production issues, performance tracking |
| Rate limiting | Request throttling per IP | Prevent abuse, fair resource allocation |
| Database transactions | ACID compliance for state updates | Prevent race conditions, data consistency |
| Deployment readiness | Environment config, CI/CD hooks | Render deployment without manual intervention |

---

## Implementation Plan

### Task 1: Add WebSocket endpoint for job updates

**Files:**
- Create: `emy/brain/websocket.py`
- Modify: `emy/brain/service.py` (add WebSocket route)
- Test: `tests/brain/test_websocket.py`

**Step 1: Write failing test**

```python
import pytest
from fastapi.testclient import TestClient
from emy.brain.service import app

def test_websocket_job_updates():
    """Test WebSocket streaming of job updates."""
    client = TestClient(app)

    with client.websocket_connect("/ws/jobs") as websocket:
        # Connect successfully
        data = websocket.receive_json()
        assert data["status"] == "connected"
```

**Step 2: Create websocket.py**

```python
"""WebSocket management for real-time job updates."""

import asyncio
import json
import logging
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
from emy.brain.queue import JobQueue

logger = logging.getLogger('EMyBrain.WebSocket')


class JobUpdateManager:
    """Manages WebSocket connections and broadcasts job updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.job_queue: JobQueue = None

    async def connect(self, websocket: WebSocket):
        """Accept WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "status": "connected",
            "message": "WebSocket connected for job updates"
        })

        logger.info(f"WebSocket connected. Active connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast_job_update(self, job_id: str, update: dict):
        """Broadcast job update to all connected clients."""
        message = {
            "type": "job_update",
            "job_id": job_id,
            **update
        }

        # Send to all connected clients
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send update to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)

    async def broadcast_job_state(self, job_id: str, state: dict):
        """Broadcast complete job state."""
        await self.broadcast_job_update(job_id, {
            "state": state,
            "current_group_index": state.get("current_group_index"),
            "status": state.get("status"),
            "results": state.get("results"),
            "agents_executing": state.get("agents_executing"),
            "messages": state.get("messages")
        })


# Global manager instance
job_update_manager = JobUpdateManager()
```

**Step 3: Add WebSocket route to service.py**

```python
from fastapi import WebSocket, WebSocketDisconnect
from emy.brain.websocket import job_update_manager

@app.websocket("/ws/jobs")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time job updates."""
    await job_update_manager.connect(websocket)
    try:
        while True:
            # Keep connection open, receive/process client messages if needed
            data = await websocket.receive_text()
            # Handle client messages (e.g., subscribe to specific job)
            if data:
                message = json.loads(data)
                if message.get("type") == "subscribe":
                    job_id = message.get("job_id")
                    logger.info(f"Client subscribed to job {job_id}")
    except WebSocketDisconnect:
        await job_update_manager.disconnect(websocket)
```

**Step 4: Update job_executor() to broadcast updates**

In `service.py` job_executor() function, add broadcast calls:

```python
async def job_executor():
    """Background job executor with real-time updates."""
    logger.info('Job executor starting...')

    while True:
        try:
            job_data = await job_queue.get_next()

            if job_data:
                job_id = job_data['job_id']

                # Broadcast job started
                await job_update_manager.broadcast_job_update(job_id, {
                    "status": "executing",
                    "message": f"Job {job_id} started"
                })

                await job_queue.mark_executing(job_id)

                # Create and execute state
                state = create_initial_state(...)

                try:
                    result = await execute_workflow(state)

                    # Broadcast final state
                    await job_update_manager.broadcast_job_state(job_id, {
                        "workflow_type": result.workflow_type,
                        "status": result.status,
                        "results": result.results,
                        "messages": result.messages,
                        "error": result.error
                    })

                    output_dict = {...}
                    await job_queue.mark_complete(job_id, output_dict)

                except Exception as e:
                    error_msg = f'Workflow execution failed: {str(e)}'

                    # Broadcast error
                    await job_update_manager.broadcast_job_update(job_id, {
                        "status": "failed",
                        "error": error_msg
                    })

                    await job_queue.mark_failed(job_id, error_msg)
```

**Step 5: Run test**

```bash
pytest tests/brain/test_websocket.py::test_websocket_job_updates -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add emy/brain/websocket.py emy/brain/service.py tests/brain/test_websocket.py
git commit -m "feat: Add WebSocket endpoint for real-time job updates"
```

---

### Task 2: Update dashboard UI for real-time job tracking

**Files:**
- Modify: `emy/ui/static/app.js`
- Modify: `emy/ui/static/index.html`
- Modify: `emy/ui/static/style.css`

**Step 1: Add WebSocket connection in app.js**

```javascript
// WebSocket connection for real-time updates
let ws = null;
let jobUpdateHandlers = {};  // Map job_id → update callback

function connectWebSocket() {
    const wsUrl = `ws://${window.location.host}/ws/jobs`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('[WebSocket] Connected to job updates');
        document.getElementById('wsStatus').textContent = '🟢 Live';
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.type === 'job_update') {
            const jobId = message.job_id;

            // Update job in local cache
            if (jobId in jobUpdateHandlers) {
                jobUpdateHandlers[jobId](message);
            }

            // Update UI
            updateJobStatus(jobId, message);
        }
    };

    ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        document.getElementById('wsStatus').textContent = '🔴 Disconnected';
    };

    ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        document.getElementById('wsStatus').textContent = '🟡 Reconnecting...';
        // Attempt reconnect in 3 seconds
        setTimeout(connectWebSocket, 3000);
    };
}

function updateJobStatus(jobId, update) {
    const jobElement = document.querySelector(`[data-job-id="${jobId}"]`);
    if (!jobElement) return;

    // Update status badge
    const statusBadge = jobElement.querySelector('.status-badge');
    if (statusBadge && update.status) {
        statusBadge.textContent = update.status;
        statusBadge.className = `status-badge status-${update.status}`;
    }

    // Update agent execution visualization
    if (update.agents_executing && update.agents_executing.length > 0) {
        const agentsDiv = jobElement.querySelector('.executing-agents');
        if (agentsDiv) {
            agentsDiv.innerHTML = update.agents_executing
                .map(a => `<span class="agent-badge">${a}</span>`)
                .join('');
        }
    }

    // Update progress
    if (update.current_group_index !== undefined) {
        const progress = jobElement.querySelector('.progress-bar');
        if (progress) {
            const percent = (update.current_group_index / (update.total_groups || 2)) * 100;
            progress.style.width = `${percent}%`;
        }
    }
}

// Connect WebSocket on page load
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
});
```

**Step 2: Add HTML elements for real-time status**

In `index.html`, update the job submission response section:

```html
<!-- WebSocket Status Indicator -->
<div class="ws-status" id="wsStatus">🟡 Connecting...</div>

<!-- Job History with Real-Time Updates -->
<section class="job-history">
    <h3>Active & Recent Jobs</h3>
    <div id="jobsList" class="jobs-list">
        <!-- Jobs rendered here with WebSocket updates -->
    </div>
</section>

<!-- Job Detail View (updated in real-time) -->
<section class="job-detail" id="jobDetail" style="display:none">
    <div class="job-header">
        <h3 id="jobTitle">Job Details</h3>
        <span class="status-badge" id="jobStatus">pending</span>
    </div>

    <!-- Agent Execution Timeline -->
    <div class="agent-timeline">
        <div class="timeline-label">Executing Agents:</div>
        <div class="executing-agents" id="executingAgents"></div>
    </div>

    <!-- Progress Bar -->
    <div class="progress-container">
        <div class="progress-bar" id="jobProgress" style="width:0%"></div>
    </div>

    <!-- Real-time Messages/Log -->
    <div class="job-log" id="jobLog">
        <div class="log-header">Execution Log:</div>
        <div class="log-entries" id="logEntries"></div>
    </div>

    <!-- Results (updated as agents complete) -->
    <div class="job-results" id="jobResults" style="display:none">
        <div class="results-header">Results:</div>
        <pre id="resultsContent"></pre>
    </div>
</section>
```

**Step 3: Add CSS for real-time visualization**

In `style.css`:

```css
/* WebSocket Status Indicator */
.ws-status {
    position: fixed;
    top: 10px;
    right: 10px;
    padding: 8px 12px;
    border-radius: 4px;
    background: #f5f5f5;
    font-size: 12px;
    font-weight: bold;
}

/* Agent Execution Timeline */
.agent-timeline {
    margin: 16px 0;
    padding: 12px;
    background: #f9f9f9;
    border-left: 4px solid #2196F3;
    border-radius: 4px;
}

.executing-agents {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
}

.agent-badge {
    display: inline-block;
    padding: 4px 12px;
    background: #2196F3;
    color: white;
    border-radius: 16px;
    font-size: 12px;
    animation: pulse 1s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

/* Progress Bar */
.progress-container {
    width: 100%;
    height: 24px;
    background: #e0e0e0;
    border-radius: 12px;
    overflow: hidden;
    margin: 16px 0;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #4CAF50, #45a049);
    transition: width 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 12px;
    font-weight: bold;
}

/* Job Log */
.job-log {
    max-height: 300px;
    overflow-y: auto;
    background: #f5f5f5;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 12px;
    margin: 16px 0;
    font-family: monospace;
    font-size: 12px;
}

.log-entry {
    padding: 4px 0;
    color: #333;
}

.log-entry.agent-msg {
    color: #1976D2;
}

.log-entry.error {
    color: #d32f2f;
}

/* Status Badges */
.status-badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: bold;
}

.status-pending { background: #FFF9C4; color: #F57F17; }
.status-executing { background: #B3E5FC; color: #0277BD; }
.status-completed { background: #C8E6C9; color: #2E7D32; }
.status-failed { background: #FFCDD2; color: #C62828; }
```

**Step 4: Test manually**

```bash
# Start Brain service
python -m emy.brain.service

# In another terminal, visit dashboard and submit a job
# Watch for real-time updates
```

**Step 5: Commit**

```bash
git add emy/ui/static/app.js emy/ui/static/index.html emy/ui/static/style.css
git commit -m "feat: Update dashboard UI for real-time WebSocket job tracking"
```

---

### Task 3: Implement job resumption from checkpoints

**Files:**
- Modify: `emy/brain/queue.py` (add checkpoint tracking)
- Modify: `emy/brain/service.py` (add resume logic)
- Create: `emy/brain/checkpoint.py` (checkpoint management)
- Test: `tests/brain/test_checkpoint.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_resume_job_from_checkpoint():
    """Test resuming job from group checkpoint."""
    # Create job with multi-agent groups
    job_id = "test_resume_001"

    # Simulate job failing at group 1
    state = create_initial_state_with_groups(
        workflow_type="test",
        agent_groups=[["Agent1"], ["Agent2"], ["Agent3"]],
        input={"query": "Test"}
    )
    state.current_group_index = 1  # Failed at group 1
    state.status = "failed"

    # Save checkpoint
    checkpoint_manager.save_checkpoint(job_id, state)

    # Resume from checkpoint
    resumed_state = checkpoint_manager.load_checkpoint(job_id)

    assert resumed_state.current_group_index == 1
    assert resumed_state.agents == ["Agent1", "Agent2", "Agent3"]
```

**Step 2: Create checkpoint.py**

```python
"""Checkpoint management for job resumption."""

import json
import logging
from pathlib import Path
from typing import Optional
from emy.brain.state import EMyState

logger = logging.getLogger('EMyBrain.Checkpoint')


class CheckpointManager:
    """Saves and loads job state for resumption."""

    def __init__(self, checkpoint_dir: str = "emy_checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)

    def save_checkpoint(self, job_id: str, state: EMyState):
        """Save job state as checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{job_id}.json"

        # Convert state to dict
        state_dict = {
            "workflow_id": state.workflow_id,
            "workflow_type": state.workflow_type,
            "agents": state.agents,
            "agent_groups": state.agent_groups,
            "current_agent": state.current_agent,
            "current_group_index": state.current_group_index,
            "agents_executing": state.agents_executing,
            "input": state.input,
            "results": state.results,
            "messages": state.messages,
            "status": state.status,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "error": state.error,
            "error_context": state.error_context
        }

        with open(checkpoint_file, 'w') as f:
            json.dump(state_dict, f, indent=2)

        logger.info(f"Saved checkpoint for job {job_id}")

    def load_checkpoint(self, job_id: str) -> Optional[EMyState]:
        """Load job state from checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{job_id}.json"

        if not checkpoint_file.exists():
            return None

        with open(checkpoint_file, 'r') as f:
            state_dict = json.load(f)

        # Reconstruct state from dict
        from emy.brain.state import EMyState
        from dataclasses import fields

        # Create state with basic fields
        state = EMyState(
            workflow_id=state_dict['workflow_id'],
            workflow_type=state_dict['workflow_type'],
            agents=state_dict['agents'],
            input=state_dict['input']
        )

        # Set remaining fields
        state.agent_groups = state_dict.get('agent_groups', [])
        state.current_agent = state_dict.get('current_agent')
        state.current_group_index = state_dict.get('current_group_index', 0)
        state.agents_executing = state_dict.get('agents_executing', [])
        state.results = state_dict.get('results', {})
        state.messages = state_dict.get('messages', [])
        state.status = state_dict.get('status', 'pending')
        state.created_at = state_dict.get('created_at')
        state.updated_at = state_dict.get('updated_at')
        state.error = state_dict.get('error')
        state.error_context = state_dict.get('error_context', {})

        logger.info(f"Loaded checkpoint for job {job_id}")
        return state

    def delete_checkpoint(self, job_id: str):
        """Delete checkpoint after successful completion."""
        checkpoint_file = self.checkpoint_dir / f"{job_id}.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info(f"Deleted checkpoint for job {job_id}")


# Global checkpoint manager
checkpoint_manager = CheckpointManager()
```

**Step 3: Add resume endpoint to service.py**

```python
@app.post('/jobs/{job_id}/resume')
async def resume_job(job_id: str):
    """Resume a failed job from its last checkpoint."""
    from emy.brain.checkpoint import checkpoint_manager

    # Load checkpoint
    state = checkpoint_manager.load_checkpoint(job_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"No checkpoint for job {job_id}")

    # Create new job with resumed state
    job_data = {
        "job_id": job_id,
        "workflow_type": state.workflow_type,
        "agents": state.agents,
        "agent_groups": state.agent_groups,
        "input": state.input
    }

    job = Job(**job_data)
    await job_queue.submit(job)

    logger.info(f"Resumed job {job_id} from checkpoint (group {state.current_group_index})")

    return JobResponse(
        job_id=job_id,
        workflow_type=state.workflow_type,
        status='pending',
        created_at=datetime.now().isoformat()
    )
```

**Step 4: Update job_executor to save checkpoints on error**

```python
try:
    result = await execute_workflow(state)
    # ... success path ...
except Exception as e:
    error_msg = f'Workflow execution failed: {str(e)}'

    # Save checkpoint for resumption
    checkpoint_manager.save_checkpoint(job_id, state)

    # Broadcast error with resume hint
    await job_update_manager.broadcast_job_update(job_id, {
        "status": "failed",
        "error": error_msg,
        "resumable": True,
        "message": f"Job failed at group {state.current_group_index}. Use /jobs/{job_id}/resume to retry."
    })

    await job_queue.mark_failed(job_id, error_msg)
```

**Step 5: Tests**

```bash
pytest tests/brain/test_checkpoint.py -v
```

**Step 6: Commit**

```bash
git add emy/brain/checkpoint.py emy/brain/service.py tests/brain/test_checkpoint.py
git commit -m "feat: Implement job resumption from checkpoints for error recovery"
```

---

### Task 4: Add structured logging and monitoring

**Files:**
- Create: `emy/brain/logging_config.py`
- Modify: All modules to use structured logging
- Test: `tests/brain/test_logging.py`

**Step 1: Create logging config**

```python
"""Structured logging configuration for EMyBrain."""

import logging
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(log_level=logging.INFO, log_file=None):
    """Setup structured logging."""
    root_logger = logging.getLogger('EMyBrain')
    root_logger.setLevel(log_level)

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    return root_logger
```

**Step 2: Update service.py to use structured logging**

```python
from emy.brain.logging_config import setup_logging

# Setup at startup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('EMyBrain.Service')
```

**Step 3: Tests and commit**

```bash
pytest tests/brain/test_logging.py -v
git add emy/brain/logging_config.py emy/brain/service.py tests/brain/test_logging.py
git commit -m "feat: Add structured JSON logging for monitoring and debugging"
```

---

### Task 5: Add rate limiting and request throttling

**Files:**
- Create: `emy/brain/rate_limit.py`
- Modify: `emy/brain/service.py` (add middleware)
- Test: `tests/brain/test_rate_limit.py`

**Step 1: Create rate limiter**

```python
"""Rate limiting for Emy Brain service."""

from collections import defaultdict
from time import time
import logging

logger = logging.getLogger('EMyBrain.RateLimit')


class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)  # ip → [timestamps]

    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed for client."""
        now = time()
        window_start = now - self.window_seconds

        # Clean old requests
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip]
            if ts > window_start
        ]

        # Check limit
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return False

        # Record request
        self.requests[client_ip].append(now)
        return True


rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
```

**Step 2: Add rate limiting middleware**

```python
from fastapi import Request
from emy.brain.rate_limit import rate_limiter

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to all requests."""
    client_ip = request.client.host if request.client else "unknown"

    if not rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Rate limited."}
        )

    response = await call_next(request)
    return response
```

**Step 3: Tests and commit**

```bash
pytest tests/brain/test_rate_limit.py -v
git add emy/brain/rate_limit.py emy/brain/service.py tests/brain/test_rate_limit.py
git commit -m "feat: Add rate limiting to prevent abuse"
```

---

### Task 6: Add database transaction support

**Files:**
- Modify: `emy/brain/queue.py` (add transactions)
- Test: `tests/brain/test_transactions.py`

**Step 1: Add transaction support**

```python
# In JobQueue.__init__, enable foreign keys and WAL mode
cursor.execute("PRAGMA foreign_keys = ON")
cursor.execute("PRAGMA journal_mode = WAL")
```

**Step 2: Wrap operations in transactions**

```python
async def submit(self, job: Job) -> str:
    """Submit job with transaction safety."""
    with self.get_connection() as conn:
        cursor = conn.cursor()
        try:
            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")

            # Insert job
            cursor.execute("""
                INSERT INTO jobs (...)
                VALUES (...)
            """)

            # Commit transaction
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise

    return job.job_id
```

**Step 3: Tests and commit**

```bash
pytest tests/brain/test_transactions.py -v
git add emy/brain/queue.py tests/brain/test_transactions.py
git commit -m "feat: Add database transaction support for consistency"
```

---

### Task 7: Environment configuration and deployment

**Files:**
- Create: `.env.example`
- Modify: `emy/brain/config.py` (add deployment settings)
- Create: `Dockerfile` and `docker-compose.yml` (if needed)

**Step 1: Create .env.example**

```
# Emy Brain Service Configuration

# Service
BRAIN_HOST=0.0.0.0
BRAIN_PORT=8001
ENV=production

# Database
BRAIN_DB_PATH=/data/emy_brain.db

# WebSocket
WS_HEARTBEAT_INTERVAL=30

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/emy_brain.log

# Monitoring (optional)
SENTRY_DSN=
SENTRY_ENVIRONMENT=production

# Security
CORS_ORIGINS=http://localhost:3000,https://example.com
```

**Step 2: Update config.py**

```python
import os
from pathlib import Path

# Service Configuration
BRAIN_HOST = os.getenv("BRAIN_HOST", "0.0.0.0")
BRAIN_PORT = int(os.getenv("BRAIN_PORT", "8001"))
ENV = os.getenv("ENV", "development")

# Database
DB_PATH = Path(os.getenv("BRAIN_DB_PATH", "emy_brain.db"))

# Queue
QUEUE_BATCH_SIZE = int(os.getenv("QUEUE_BATCH_SIZE", "10"))
QUEUE_POLL_INTERVAL = int(os.getenv("QUEUE_POLL_INTERVAL", "5"))

# WebSocket
WS_HEARTBEAT_INTERVAL = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))

# Rate Limiting
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE")

# Monitoring
SENTRY_DSN = os.getenv("SENTRY_DSN")
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", ENV)

# Security
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Deployment
IS_PRODUCTION = ENV == "production"
DEBUG = not IS_PRODUCTION
```

**Step 3: Commit**

```bash
git add .env.example emy/brain/config.py
git commit -m "feat: Add deployment configuration and environment settings"
```

---

### Task 8: Production deployment verification

**Files:**
- Create: `docs/DEPLOYMENT.md`
- Create: `tests/brain/test_integration_full.py` (full deployment test)

**Step 1: Create deployment guide**

```markdown
# Emy Brain Deployment Guide

## Prerequisites
- Python 3.9+
- SQLite3
- FastAPI, LangGraph, asyncio libraries

## Local Development

1. Install dependencies
2. Set environment: `export ENV=development`
3. Run service: `python -m emy.brain.service`
4. Dashboard: `http://localhost:8000` (Phase 1a gateway)
5. Brain API: `http://localhost:8001` (Swagger UI)
6. WebSocket: `ws://localhost:8001/ws/jobs`

## Render Deployment

1. Create Render service with Python environment
2. Set environment variables from `.env.example`
3. Command: `python -m emy.brain.service`
4. Port: 8001
5. Health check: GET `/health`

## Monitoring

- Logs: CloudWatch/Render Logs
- Errors: Sentry integration (if configured)
- Performance: Monitor `/health` endpoint

## Scaling

- Horizontal: Run multiple Brain service instances with shared database
- Database: Upgrade to PostgreSQL for better concurrency
- Caching: Add Redis for job result caching
```

**Step 2: Full integration test**

```python
@pytest.mark.asyncio
async def test_full_production_workflow():
    """Test complete production workflow."""
    # Setup
    client = TestClient(app)

    # 1. Submit multi-agent job
    response = client.post("/jobs", json={
        "workflow_type": "market_analysis",
        "agent_groups": [["TradingAgent"], ["ResearchAgent"]],
        "input": {"query": "Test"}
    })
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    # 2. Check status via REST
    response = client.get(f"/jobs/{job_id}/status")
    assert response.status_code == 200
    assert response.json()["status"] in ["pending", "executing"]

    # 3. Test WebSocket connection
    with client.websocket_connect("/ws/jobs") as ws:
        data = ws.receive_json()
        assert data["type"] == "connected"

    # 4. Test rate limiting
    for i in range(101):
        response = client.get("/health")
        if i == 100:
            assert response.status_code == 429  # Rate limited
        else:
            assert response.status_code == 200

    # 5. Resume from checkpoint (if failed)
    # ... checkpoint test logic ...

    # 6. Verify logs
    # ... logging test logic ...
```

**Step 3: Commit**

```bash
git add docs/DEPLOYMENT.md tests/brain/test_integration_full.py
git commit -m "docs: Add deployment guide and production integration tests"
```

---

## Execution Order & Dependencies

| Task | Depends On | Est. Time |
|------|-----------|-----------|
| 1. WebSocket endpoint | — | 20 min |
| 2. Dashboard UI | 1 | 25 min |
| 3. Job resumption | — | 20 min |
| 4. Structured logging | — | 15 min |
| 5. Rate limiting | — | 15 min |
| 6. Database transactions | — | 10 min |
| 7. Deployment config | 1-6 | 10 min |
| 8. Production tests | 1-7 | 15 min |

**Total: ~130 minutes = 2.2 hours for complete Week 3**

**Sequential flow:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

---

## Verification Checklist

After completing all tasks:

- [ ] WebSocket streams job updates to dashboard
- [ ] Dashboard shows real-time agent execution
- [ ] Failed jobs can be resumed from checkpoint
- [ ] Logs are JSON-formatted and searchable
- [ ] Rate limiting blocks excess requests (429 status)
- [ ] Database transactions prevent race conditions
- [ ] Environment variables load correctly
- [ ] Deployment guide covers Render setup
- [ ] Full integration test passes
- [ ] All 40+ tests passing

---

## Success Criteria

| Criterion | Metric | Pass |
|-----------|--------|------|
| Real-time updates | WebSocket updates <1s | ✓ |
| Dashboard UX | Visual agent timeline | ✓ |
| Error recovery | Job resumption works | ✓ |
| Observability | Structured JSON logs | ✓ |
| Safety | Rate limiting active | ✓ |
| Data integrity | Transaction support | ✓ |
| Configuration | 12+ env variables | ✓ |
| Documentation | Deployment guide complete | ✓ |

---

## Deployment Path

**After Week 3 complete:**

1. Merge to master
2. Tag as v0.3.0 (Week 3)
3. Deploy to Render staging
4. Run smoke tests
5. Deploy to production (https://emy-phase3.onrender.com)
6. Monitor for 48 hours
7. Document lessons learned

