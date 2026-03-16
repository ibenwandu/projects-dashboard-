"""
Emy FastAPI Gateway Server.

Provides REST API endpoints for CLI client and external integrations.
Acts as a gateway to the main Emy agent loop and database.
"""

import os
import uuid
import logging
import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

from emy.core.database import EMyDatabase
from emy.core.metrics import collect_metrics
from emy.agents.agent_executor import AgentExecutor
from emy.brain.agent_selector import AgentSelector

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

logger = logging.getLogger('EmyGateway')

# Initialize agent selector
selector = AgentSelector()

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
# Static Files (Dashboard UI)
# ============================================================================

# Determine static files directory
static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')

# Root endpoint - serve dashboard HTML
@app.get("/")
async def root():
    """Serve dashboard at root URL."""
    index_path = os.path.join(static_dir, 'index.html')
    logger.info(f"Dashboard request - checking: {index_path}")
    logger.info(f"Static dir exists: {os.path.exists(static_dir)}")
    logger.info(f"Index file exists: {os.path.exists(index_path)}")

    if os.path.exists(index_path):
        logger.info(f"Serving dashboard from: {index_path}")
        return FileResponse(index_path)

    logger.error(f"Dashboard not found at: {index_path}")
    return {"message": "Dashboard not available", "debug": {"static_dir": static_dir, "index_path": index_path}}

# Backwards-compatible /ui/ alias
@app.get("/ui/")
async def ui_redirect():
    """Redirect /ui/ to root for backwards compatibility."""
    return RedirectResponse(url="/")

# Mount static assets (CSS, JS) at /static/
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ============================================================================
# WebSocket Management
# ============================================================================

# Global set of connected WebSocket clients
connected_clients = set()

# ============================================================================
# Request/Response Models
# ============================================================================


class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow."""
    workflow_type: str
    agents: Optional[List[str]] = None
    input: Optional[Dict[str, Any]] = None
    agent_selection: Optional[str] = None  # 'auto' for intelligent selection, or agent list


class AgentSelectionRequest(BaseModel):
    """Request for intelligent agent selection."""
    task: Dict[str, Any]
    mode: str = 'auto'  # 'auto' or 'explicit'
    agents: Optional[List[str]] = None  # For explicit mode


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


@app.get('/dashboard')
async def dashboard():
    """Serve the interactive dashboard UI"""
    dashboard_path = Path(__file__).parent.parent / "templates" / "dashboard.html"
    if not dashboard_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return FileResponse(dashboard_path, media_type="text/html")


@app.get('/api/metrics')
async def get_metrics():
    """Get all dashboard metrics"""
    try:
        metrics = collect_metrics()
        return metrics.dict()
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to collect metrics")


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics"""
    await websocket.accept()
    connected_clients.add(websocket)

    try:
        # Send initial system metrics immediately
        metrics = collect_metrics()
        await websocket.send_json({
            "event": "system_metrics",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {
                "response_time_ms": metrics.system.response_time_ms,
                "db_usage_percentage": metrics.system.db_usage_percentage,
                "status": metrics.system.status
            }
        })

        # Send system metrics every 30 seconds
        while True:
            await asyncio.sleep(30)
            metrics = collect_metrics()
            await websocket.send_json({
                "event": "system_metrics",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "response_time_ms": metrics.system.response_time_ms,
                    "db_usage_percentage": metrics.system.db_usage_percentage,
                    "status": metrics.system.status
                }
            })

    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.discard(websocket)


async def broadcast_metric_event(event: str, data: dict):
    """Broadcast metric event to all connected WebSocket clients"""
    message = {
        "event": event,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data
    }

    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            disconnected.append(client)

    # Remove disconnected clients
    for client in disconnected:
        connected_clients.discard(client)


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

    Supports both local execution (AgentExecutor) and remote (Brain service via HTTP).
    Uses Brain service if BRAIN_SERVICE_URL environment variable is set.

    Supports intelligent agent selection via agent_selection parameter:
    - 'auto': Automatically select agents based on workflow_type and input
    - List of agent names: Use explicit agents

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

    # Auto-select agents if needed
    agents = request.agents
    if not agents or (request.agent_selection == 'auto'):
        logger.info(f"Auto-selecting agents for workflow {workflow_id}")
        task = {
            'type': request.workflow_type,
            'input': request.input if request.input else {}
        }
        agents = selector.select_agents(task, mode='auto')
        logger.info(f"Selected agents: {agents}")

    if not agents:
        raise HTTPException(status_code=400, detail="No valid agents available for workflow")

    # Prepare input data
    input_data = json.dumps(request.input) if request.input else None

    # Check if Brain service is available (Render deployment)
    brain_service_url = os.getenv('BRAIN_SERVICE_URL')

    if brain_service_url:
        # Remote execution via Brain service
        logger.info(f"Executing workflow {workflow_id} via Brain service at {brain_service_url}")
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Convert agents list to agent_groups format for Brain service
                agent_groups = [[agent] for agent in request.agents]

                brain_request = {
                    "workflow_type": request.workflow_type,
                    "agent_groups": agent_groups,
                    "input": request.input or {}
                }

                response = await client.post(
                    f"{brain_service_url}/jobs",
                    json=brain_request
                )

                if response.status_code != 200:
                    logger.error(f"Brain service error: {response.status_code} - {response.text}")
                    final_status = 'error'
                    output_str = f"Brain service error: {response.status_code}"
                else:
                    brain_response = response.json()
                    job_id = brain_response.get('job_id')

                    # Poll for job completion (with timeout)
                    max_polls = 60  # 5 minutes with 5-second polls
                    poll_count = 0

                    while poll_count < max_polls:
                        status_response = await client.get(
                            f"{brain_service_url}/jobs/{job_id}/status"
                        )

                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            if status_data.get('status') in ['completed', 'error']:
                                final_status = status_data.get('status', 'error')
                                output_str = status_data.get('output', '')
                                break

                        # Wait before next poll
                        import asyncio
                        await asyncio.sleep(5)
                        poll_count += 1
                    else:
                        # Timeout
                        final_status = 'error'
                        output_str = "Brain service job execution timeout"

        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Brain service: {e}")
            final_status = 'error'
            output_str = f"Brain service connection error: {str(e)}"
        except Exception as e:
            logger.error(f"Brain service execution error: {e}")
            final_status = 'error'
            output_str = f"Brain service error: {str(e)}"
    else:
        # Local execution (development mode)
        logger.info(f"Executing workflow {workflow_id}: type={request.workflow_type}, agents={request.agents}")
        success, output = AgentExecutor.execute(
            request.workflow_type,
            request.agents,
            request.input or {}
        )
        final_status = 'completed' if success else 'error'
        output_str = str(output) if output else None

    # Store workflow output to database (with input data)
    db.store_workflow_output(
        workflow_id,
        request.workflow_type,
        final_status,
        output_str,  # Real output from agent execution
        input_data  # Input data passed to workflow
    )

    workflow = {
        'workflow_id': workflow_id,
        'type': request.workflow_type,
        'status': final_status,
        'agents': request.agents,
        'created_at': now,
        'updated_at': now,
        'input': input_data,
        'output': output_str
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
        output=output_str
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
        # Ensure output is a string
        output_val = str(wf.get('output')) if wf.get('output') else None
        return WorkflowResponse(
            workflow_id=wf['workflow_id'],
            type=wf['type'],
            status=wf['status'],
            created_at=wf['created_at'],
            updated_at=wf.get('updated_at'),
            input=wf.get('input'),
            output=output_val
        )

    # Fall back to in-memory for backward compatibility
    if workflow_id in _workflows:
        wf = _workflows[workflow_id]
        output_val = str(wf.get('output')) if wf.get('output') else None
        return WorkflowResponse(
            workflow_id=wf['workflow_id'],
            type=wf['type'],
            status=wf['status'],
            created_at=wf['created_at'],
            updated_at=wf.get('updated_at'),
            input=wf.get('input'),
            output=output_val
        )

    raise HTTPException(status_code=404, detail='Workflow not found')


@app.get('/workflows', response_model=WorkflowListResponse)
async def list_workflows(limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)):
    """List workflows with pagination, reading from database.

    Args:
        limit: Number of results to return (1-100)
        offset: Number of results to skip

    Returns:
        Paginated list of workflows with input/output
    """
    db = EMyDatabase()
    workflows = db.get_workflows(limit=limit, offset=offset)
    total = db.count_workflows()

    workflows_data = [
        {
            'workflow_id': wf['workflow_id'],
            'type': wf['type'],
            'status': wf['status'],
            'created_at': wf['created_at'],
            'updated_at': wf.get('updated_at'),
            'input': wf.get('input'),
            'output': str(wf.get('output')) if wf.get('output') else None
        }
        for wf in workflows
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


@app.post('/agents/select')
async def select_agents(request: AgentSelectionRequest):
    """Intelligently select agents for a task.

    Uses the AgentSelector to automatically choose the best agents
    based on task type, input text, and required capabilities.

    Args:
        request: AgentSelectionRequest with task and selection mode

    Returns:
        Dict with selected agents and explanation
    """
    try:
        agents = selector.select_agents(
            request.task,
            mode=request.mode,
            agents=request.agents
        )

        return {
            'selected_agents': agents,
            'mode': request.mode,
            'task_type': request.task.get('type'),
            'count': len(agents)
        }
    except Exception as e:
        logger.error(f"Error selecting agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/agents/capabilities/{agent_name}')
async def get_agent_capabilities(agent_name: str):
    """Get capabilities for a specific agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Dict with capabilities list
    """
    try:
        if not selector.is_valid_agent(agent_name):
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

        capabilities = selector.get_agent_capabilities(agent_name)

        return {
            'agent': agent_name,
            'capabilities': capabilities,
            'count': len(capabilities)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Email Processing Endpoints
# ============================================================================


@app.post('/emails/process')
async def process_emails():
    """Manually trigger email processing from Gmail inbox.

    Checks inbox for unread emails, parses them, classifies intent,
    and routes to appropriate agents.

    Returns:
        Dict with processing status and counts
    """
    try:
        from emy.tools.email_parser import EmailParser

        parser = EmailParser()
        db = EMyDatabase()

        # Check inbox for unread emails
        emails = await parser.check_inbox()
        processed_count = 0
        failed_count = 0

        for email_msg in emails:
            try:
                # Parse email
                email = await parser.parse_email(email_msg['id'])
                if not email:
                    failed_count += 1
                    continue

                # Classify intent
                intent = await parser.classify_intent(email)
                email['intent'] = intent

                # Route to agent
                agent_name = await parser.route_to_agent(email)
                email['agent'] = agent_name

                # Log email in database
                await parser.log_email(email, 'processed')
                processed_count += 1

                logger.info(f"Processed email from {email['sender']} with intent {intent}")

            except Exception as e:
                logger.error(f"Error processing email {email_msg.get('id')}: {e}")
                failed_count += 1

        return {
            'status': 'success',
            'processed_count': processed_count,
            'failed_count': failed_count,
            'total_emails': len(emails)
        }

    except Exception as e:
        logger.error(f"Error in email processing endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/emails/status')
async def get_email_status():
    """Get email processing status from last 24 hours.

    Returns:
        Dict with email statistics
    """
    try:
        db = EMyDatabase()

        # Query email statistics from last 24 hours
        result = db.query("""
            SELECT
                COUNT(*) as total_emails,
                SUM(CASE WHEN direction = 'outbound' THEN 1 ELSE 0 END) as sent_count,
                SUM(CASE WHEN direction = 'inbound' THEN 1 ELSE 0 END) as received_count,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count
            FROM email_log
            WHERE created_at >= datetime('now', '-24 hours')
        """)

        if result:
            row = result[0]
            return {
                'status': 'success',
                'period': '24_hours',
                'total_emails': row[0] or 0,
                'sent_count': row[1] or 0,
                'received_count': row[2] or 0,
                'failed_count': row[3] or 0,
                'success_rate': round(
                    ((row[0] or 1) - (row[3] or 0)) / (row[0] or 1) * 100, 2
                ) if row[0] else 0
            }
        else:
            return {
                'status': 'success',
                'period': '24_hours',
                'total_emails': 0,
                'sent_count': 0,
                'received_count': 0,
                'failed_count': 0,
                'success_rate': 100.0
            }

    except Exception as e:
        logger.error(f"Error getting email status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/emails/polling-status')
async def get_polling_status():
    """
    Get email polling status and metrics.

    Returns:
        {
            'status': 'active' | 'inactive' | 'error' | 'no_data',
            'last_check': '2026-03-16T10:30:00Z',
            'email_count': 5,
            'next_check': '2026-03-16T10:40:00Z',
            'uptime': '2h 15m',
            'error_message': null
        }
    """
    db = EMyDatabase()

    try:
        # Get last polling event
        result = db.query_all(
            "SELECT status, email_count, timestamp FROM polling_log ORDER BY timestamp DESC LIMIT 1"
        )
        last_event = result[0] if result else None

        if not last_event:
            return {
                'status': 'no_data',
                'last_check': None,
                'email_count': 0,
                'next_check': (datetime.utcnow() + timedelta(minutes=10)).isoformat() + 'Z',
                'error_message': 'No polling events recorded yet'
            }

        last_status, email_count, timestamp = last_event
        last_check = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
        next_check = last_check + timedelta(minutes=10)

        # Calculate uptime
        first_event_result = db.query_all("SELECT MIN(timestamp) FROM polling_log")
        first_event = first_event_result[0][0] if first_event_result and first_event_result[0] else None

        uptime = None
        if first_event:
            first_time = datetime.fromisoformat(first_event) if isinstance(first_event, str) else first_event
            uptime = str(datetime.utcnow() - first_time).split('.')[0]

        return {
            'status': 'active' if last_status == 'success' else 'error',
            'last_check': last_check.isoformat() + 'Z',
            'email_count': email_count or 0,
            'next_check': next_check.isoformat() + 'Z',
            'uptime': uptime if uptime else 'unknown',
            'error_message': None if last_status == 'success' else f"Last status: {last_status}"
        }

    except Exception as e:
        logger.error(f"Error getting polling status: {e}")
        return {
            'status': 'error',
            'error_message': str(e),
            'last_check': None,
            'next_check': None,
            'email_count': 0
        }


@app.post('/emails/trigger-polling')
async def trigger_polling_manually():
    """
    Manually trigger email polling (for testing/debugging).

    Returns:
        {
            'status': 'triggered' | 'error',
            'message': str,
            'processed': int
        }
    """
    try:
        from emy.tasks.email_polling_task import check_inbox_periodically
        result = check_inbox_periodically()

        return {
            'status': 'triggered',
            'message': f"Polling triggered - {result.get('processed', 0)} emails processed",
            'processed': result.get('processed', 0)
        }
    except Exception as e:
        logger.error(f"Error triggering polling: {e}")
        return {
            'status': 'error',
            'message': f"Failed to trigger polling: {str(e)}",
            'processed': 0
        }


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
