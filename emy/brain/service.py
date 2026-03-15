"""Emy Brain FastAPI Service.

Provides REST API for job submission, status tracking, and workflow execution.
Runs as separate service from Phase 1a gateway (port 8001 vs 8000).
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from emy.brain.config import BRAIN_PORT, BRAIN_HOST, QUEUE_POLL_INTERVAL
from emy.brain.queue import JobQueue, Job
from emy.brain.graph import execute_workflow
from emy.brain.state import create_initial_state

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
    """Request to submit a job."""
    workflow_type: str
    agents: List[str]
    input: Optional[Dict[str, Any]] = None


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


@app.post('/jobs', response_model=JobResponse)
async def submit_job(request: JobSubmitRequest):
    """
    Submit a new job for execution.

    Args:
        request: Job submission request

    Returns:
        Job information with ID and status
    """
    import uuid

    # Create job
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    job = Job(
        job_id=job_id,
        workflow_type=request.workflow_type,
        agents=request.agents,
        input=request.input or {}
    )

    # Submit to queue
    submitted_id = await job_queue.submit(job)
    logger.info(f"Job {job_id} submitted for workflow {request.workflow_type}")

    return JobResponse(
        job_id=submitted_id,
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

                # Create state from job data
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

                except Exception as e:
                    error_msg = f'Workflow execution failed: {str(e)}'
                    logger.error(error_msg)
                    await job_queue.mark_failed(job_id, error_msg)

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
