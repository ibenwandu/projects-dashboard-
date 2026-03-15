"""Emy Brain FastAPI Service.

Provides REST API for job submission, status tracking, and workflow execution.
Runs as separate service from Phase 1a gateway (port 8001 vs 8000).
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, field_validator, model_validator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from emy.brain.config import BRAIN_PORT, BRAIN_HOST, QUEUE_POLL_INTERVAL
from emy.brain.queue import JobQueue, Job
from emy.brain.graph import execute_workflow
from emy.brain.state import create_initial_state, create_initial_state_with_groups
from emy.brain.websocket import job_update_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('EMyBrain.Service')

# Initialize FastAPI app
app = FastAPI(
    title='Emy Brain Service',
    description='LangGraph-powered async orchestration for Emy agents',
    version='1.0.0'
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Initialize job queue (use in-memory for testing)
import os
DB_PATH = os.getenv('BRAIN_DB_PATH', ':memory:')  # Use :memory: by default for testing
job_queue = JobQueue(db_path=DB_PATH)

# Global job executor task
job_executor_task = None


# ============================================================================
# Request/Response Models
# ============================================================================

class JobSubmitRequest(BaseModel):
    """Request to submit a job (supports both single agent and agent groups)."""
    workflow_type: str
    agents: Optional[List[str]] = None  # Backward compat: single-agent mode
    agent_groups: Optional[List[List[str]]] = None  # Multi-agent mode with grouping
    input: Optional[Dict[str, Any]] = None

    @model_validator(mode='after')
    def check_agent_specification(self):
        """Ensure either agents or agent_groups is specified, but not both."""
        if not self.agents and not self.agent_groups:
            raise ValueError('Either agents or agent_groups must be specified')
        if self.agents and self.agent_groups:
            raise ValueError('Cannot specify both agents and agent_groups')
        return self


class JobResponse(BaseModel):
    """Response containing job information."""
    job_id: str
    workflow_type: str
    status: str
    created_at: str


class JobStatusResponse(BaseModel):
    """Response containing job status."""
    job_id: str
    workflow_type: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response for health check."""
    status: str
    timestamp: str


# ============================================================================
# API Endpoints
# ============================================================================

@app.get('/health', response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status='ok',
        timestamp=datetime.now().isoformat()
    )


@app.websocket('/ws/jobs')
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time job updates.

    Clients connect and receive job status updates as they happen.
    Clients can optionally send messages to subscribe to specific jobs.
    """
    await job_update_manager.connect(websocket)
    try:
        while True:
            # Keep connection open, receive/process client messages if needed
            data = await websocket.receive_text()
            # Handle client messages (e.g., subscribe to specific job)
            if data:
                try:
                    message = json.loads(data)
                    if message.get("type") == "subscribe":
                        job_id = message.get("job_id")
                        logger.info(f"Client subscribed to job {job_id}")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received on WebSocket: {data}")
    except WebSocketDisconnect:
        await job_update_manager.disconnect(websocket)


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
        state = create_initial_state_with_groups(
            workflow_type=request.workflow_type,
            agent_groups=request.agent_groups,
            input=request.input or {},
            workflow_id=job_id
        )
    else:
        state = create_initial_state(
            workflow_type=request.workflow_type,
            agents=request.agents or [],
            input=request.input or {},
            workflow_id=job_id
        )

    # Store in queue
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


@app.get('/jobs/{job_id}/status', response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get status of a job.

    Args:
        job_id: Job ID

    Returns:
        Job status and result (if complete)
    """
    status = await job_queue.get_status(job_id)

    if status == 'not_found':
        raise HTTPException(status_code=404, detail=f'Job {job_id} not found')

    # Get result if completed
    result = None
    if status == 'completed':
        result = await job_queue.get_result(job_id)

    return JobStatusResponse(
        job_id=job_id,
        workflow_type='unknown',  # TODO: retrieve from queue
        status=status,
        output=str(result) if result else None,
        error=None
    )


# ============================================================================
# Background Job Executor
# ============================================================================

async def job_executor():
    """
    Background task that continuously processes jobs from the queue.

    Polls queue for pending jobs and executes them through the LangGraph.
    """
    logger.info('Job executor starting...')

    while True:
        try:
            # Get next pending job
            job_data = await job_queue.get_next()

            if job_data:
                job_id = job_data['job_id']
                logger.info(f'Processing job {job_id}')

                # Mark as executing
                await job_queue.mark_executing(job_id)

                # Broadcast job started update
                await job_update_manager.broadcast_job_update(
                    job_id,
                    {"status": "executing", "message": f"Job {job_id} started"}
                )

                # Create state from job data
                if job_data.get('agent_groups'):
                    state = create_initial_state_with_groups(
                        workflow_type=job_data['workflow_type'],
                        agent_groups=job_data['agent_groups'],
                        input=job_data['input'],
                        workflow_id=job_id
                    )
                else:
                    state = create_initial_state(
                        workflow_type=job_data['workflow_type'],
                        agents=job_data['agents'],
                        input=job_data['input'],
                        workflow_id=job_id
                    )

                # Execute workflow
                try:
                    result = await execute_workflow(state)

                    # Mark complete with result
                    output_dict = {
                        'workflow_type': result.workflow_type,
                        'status': result.status,
                        'results': result.results,
                        'messages': result.messages,
                        'error': result.error
                    }
                    await job_queue.mark_complete(job_id, output_dict)
                    logger.info(f'Job {job_id} completed')

                    # Broadcast job state update
                    await job_update_manager.broadcast_job_state(
                        job_id,
                        {
                            "status": result.status,
                            "results": result.results,
                            "messages": result.messages,
                            "error": result.error
                        }
                    )

                except Exception as e:
                    error_msg = f'Workflow execution failed: {str(e)}'
                    logger.error(error_msg)
                    await job_queue.mark_failed(job_id, error_msg)

                    # Broadcast job failure update
                    await job_update_manager.broadcast_job_update(
                        job_id,
                        {"status": "failed", "error": error_msg}
                    )

            else:
                # No jobs, sleep briefly
                await asyncio.sleep(QUEUE_POLL_INTERVAL)

        except Exception as e:
            logger.exception(f'Error in job executor: {str(e)}')
            await asyncio.sleep(QUEUE_POLL_INTERVAL)


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event('startup')
async def startup_event():
    """Initialize on startup."""
    global job_executor_task

    logger.info('Emy Brain Service starting...')

    # Initialize job queue
    await job_queue.initialize()
    logger.info('Job queue initialized')

    # Start job executor background task
    job_executor_task = asyncio.create_task(job_executor())
    logger.info('Job executor started')


@app.on_event('shutdown')
async def shutdown_event():
    """Cleanup on shutdown."""
    global job_executor_task

    logger.info('Emy Brain Service shutting down...')

    if job_executor_task:
        job_executor_task.cancel()
        try:
            await job_executor_task
        except asyncio.CancelledError:
            pass

    logger.info('Emy Brain Service stopped')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        app,
        host=BRAIN_HOST,
        port=BRAIN_PORT,
        log_level='info'
    )
