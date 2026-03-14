"""
Emy FastAPI Gateway Server.

Provides REST API endpoints for CLI client and external integrations.
Acts as a gateway to the main Emy agent loop and database.
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from emy.core.database import EMyDatabase
from emy.agents.agent_executor import AgentExecutor

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

logger = logging.getLogger('EmyGateway')

# Initialize FastAPI app
app = FastAPI(
    title='Emy API Gateway',
    description='REST API for Emy AI Chief of Staff',
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

# ============================================================================
# Request/Response Models
# ============================================================================


class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow."""
    workflow_type: str
    agents: List[str]
    input: Optional[Dict[str, Any]] = None


class WorkflowResponse(BaseModel):
    """Response containing workflow information."""
    workflow_id: str
    type: str
    status: str
    created_at: str
    updated_at: Optional[str] = None
    input: Optional[str] = None
    output: Optional[str] = None


class WorkflowListResponse(BaseModel):
    """Response containing workflow list."""
    workflows: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class AgentStatusResponse(BaseModel):
    """Response containing agent status information."""
    agent_name: str
    status: str
    tasks_completed: int
    tasks_failed: int
    last_activity: str


class AgentsListResponse(BaseModel):
    """Response containing list of agents."""
    agents: List[AgentStatusResponse]


class HealthResponse(BaseModel):
    """Response containing health check information."""
    status: str
    timestamp: str


# ============================================================================
# In-Memory Storage (for development/testing)
# ============================================================================

# TODO: Replace with actual database calls to EMyDatabase
_workflows: Dict[str, Dict[str, Any]] = {}
_agents: Dict[str, Dict[str, Any]] = {
    'TradingAgent': {
        'agent_name': 'TradingAgent',
        'status': 'healthy',
        'tasks_completed': 0,
        'tasks_failed': 0,
        'last_activity': datetime.now().isoformat()
    },
    'KnowledgeAgent': {
        'agent_name': 'KnowledgeAgent',
        'status': 'healthy',
        'tasks_completed': 0,
        'tasks_failed': 0,
        'last_activity': datetime.now().isoformat()
    },
    'ProjectMonitorAgent': {
        'agent_name': 'ProjectMonitorAgent',
        'status': 'healthy',
        'tasks_completed': 0,
        'tasks_failed': 0,
        'last_activity': datetime.now().isoformat()
    },
    'ResearchAgent': {
        'agent_name': 'ResearchAgent',
        'status': 'healthy',
        'tasks_completed': 0,
        'tasks_failed': 0,
        'last_activity': datetime.now().isoformat()
    }
}


# ============================================================================
# API Endpoints
# ============================================================================


@app.get('/health', response_model=HealthResponse)
async def health_check():
    """Health check endpoint.

    Returns:
        Server health status
    """
    return HealthResponse(
        status='ok',
        timestamp=datetime.now().isoformat()
    )


@app.post('/workflows/execute', response_model=WorkflowResponse)
async def execute_workflow(request: WorkflowExecuteRequest):
    """Execute a new workflow and persist to database.

    Args:
        request: Workflow execution request

    Returns:
        Workflow information with real output from agent execution
    """
    import json

    workflow_id = f'wf_{uuid.uuid4().hex[:8]}'
    now = datetime.now().isoformat()

    # Get database instance
    db = EMyDatabase()

    # Prepare input data
    input_data = json.dumps(request.input) if request.input else None

    # Execute the workflow using AgentExecutor
    logger.info(f"Executing workflow {workflow_id}: type={request.workflow_type}, agents={request.agents}")
    success, output = AgentExecutor.execute(
        request.workflow_type,
        request.agents,
        request.input or {}
    )

    # Determine final status
    final_status = 'completed' if success else 'error'

    # Store workflow output to database
    db.store_workflow_output(
        workflow_id,
        request.workflow_type,
        final_status,
        output  # Real output from agent execution
    )

    workflow = {
        'workflow_id': workflow_id,
        'type': request.workflow_type,
        'status': final_status,
        'agents': request.agents,
        'created_at': now,
        'updated_at': now,
        'input': input_data,
        'output': output
    }

    # Also keep in-memory for API compatibility
    _workflows[workflow_id] = workflow

    return WorkflowResponse(
        workflow_id=workflow_id,
        type=request.workflow_type,
        status=final_status,
        created_at=now,
        updated_at=now,
        input=input_data,
        output=output
    )


@app.get('/workflows/{workflow_id}', response_model=WorkflowResponse)
async def get_workflow_status(workflow_id: str):
    """Get status of a specific workflow from database.

    Args:
        workflow_id: ID of the workflow

    Returns:
        Workflow information

    Raises:
        HTTPException: If workflow not found
    """
    # Try database first
    db = EMyDatabase()
    wf = db.get_workflow(workflow_id)

    if wf:
        return WorkflowResponse(
            workflow_id=wf['workflow_id'],
            type=wf['type'],
            status=wf['status'],
            created_at=wf['created_at'],
            updated_at=wf.get('updated_at'),
            input=wf.get('input'),
            output=wf.get('output')
        )

    # Fall back to in-memory for backward compatibility
    if workflow_id in _workflows:
        wf = _workflows[workflow_id]
        return WorkflowResponse(
            workflow_id=wf['workflow_id'],
            type=wf['type'],
            status=wf['status'],
            created_at=wf['created_at'],
            updated_at=wf.get('updated_at'),
            input=wf.get('input'),
            output=wf.get('output')
        )

    raise HTTPException(status_code=404, detail='Workflow not found')


@app.get('/workflows', response_model=WorkflowListResponse)
async def list_workflows(limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)):
    """List workflows with pagination.

    Args:
        limit: Number of results to return (1-100)
        offset: Number of results to skip

    Returns:
        Paginated list of workflows
    """
    all_workflows = list(_workflows.values())
    total = len(all_workflows)

    # Apply pagination
    paginated = all_workflows[offset:offset + limit]

    workflows_data = [
        {
            'workflow_id': wf['workflow_id'],
            'type': wf['type'],
            'status': wf['status'],
            'created_at': wf['created_at'],
            'updated_at': wf.get('updated_at')
        }
        for wf in paginated
    ]

    return WorkflowListResponse(
        workflows=workflows_data,
        total=total,
        limit=limit,
        offset=offset
    )


@app.get('/agents/status', response_model=AgentsListResponse)
async def get_agents_status():
    """Get status of all agents.

    Returns:
        List of agent statuses
    """
    agents_list = list(_agents.values())
    return AgentsListResponse(agents=agents_list)


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with custom format.

    Args:
        request: Request that caused the exception
        exc: HTTPException instance

    Returns:
        JSON response with error details
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={'error': exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions.

    Args:
        request: Request that caused the exception
        exc: Exception instance

    Returns:
        JSON response with error details
    """
    logger.error(f'Unhandled exception: {exc}')
    return JSONResponse(
        status_code=500,
        content={'error': 'Internal server error'}
    )


# ============================================================================
# Startup/Shutdown Events
# ============================================================================


@app.on_event('startup')
async def startup_event():
    """Initialize database and log server startup."""
    logger.info('Emy API Gateway starting...')

    # Initialize database schema on startup
    try:
        db = EMyDatabase()
        db.initialize_schema()
        logger.info('Database schema initialized successfully')
    except Exception as e:
        logger.error(f'Failed to initialize database: {e}')


@app.on_event('shutdown')
async def shutdown_event():
    """Log server shutdown."""
    logger.info('Emy API Gateway shutting down...')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
