"""
FastAPI Gateway Server for Emy Phase 1a.

Provides HTTP API for workflow execution, monitoring, and agent status.
Wraps existing Emy agents with REST endpoints.

Endpoints:
- POST /workflows/execute - Create and execute workflow
- GET /workflows/{workflow_id} - Retrieve workflow details
- GET /workflows - List workflows with pagination
- POST /workflows/{workflow_id}/tasks/{task_id}/result - Update task result
- GET /agents/status - Get all agent metrics
- GET /health - Health check
"""

import logging
import json
import uuid
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.requests import Request
from pydantic import BaseModel, Field

from emy.storage.sqlite_store import SQLiteStore

logger = logging.getLogger("gateway")

# Enable SQLite to work with multiple threads
sqlite3.threadsafety = 3


# ============================================================================
# Pydantic Models
# ============================================================================

class WorkflowRequest(BaseModel):
    """Request model for creating and executing a workflow."""

    workflow_type: str = Field(..., description="Type of workflow to execute")
    agents: List[str] = Field(..., min_length=1, description="List of agent names to execute")
    input: Dict[str, Any] = Field(default_factory=dict, description="Input data for workflow")


class WorkflowResponse(BaseModel):
    """Response model for workflow execution."""

    workflow_id: str = Field(..., description="Unique workflow identifier")
    status: str = Field(..., description="Current workflow status")
    created_at: str = Field(..., description="Workflow creation timestamp")


class WorkflowDetailResponse(BaseModel):
    """Response model for workflow details."""

    id: str = Field(..., description="Workflow ID")
    name: str = Field(..., description="Workflow name")
    status: str = Field(..., description="Workflow status")
    created_at: str = Field(..., description="Creation timestamp")
    input: Optional[Dict[str, Any]] = Field(None, description="Input data")
    output: Optional[Dict[str, Any]] = Field(None, description="Output data")


class WorkflowListResponse(BaseModel):
    """Response model for workflow list."""

    workflows: List[Dict[str, Any]] = Field(..., description="List of workflows")
    total: int = Field(..., description="Total number of workflows")


class TaskResultRequest(BaseModel):
    """Request model for updating task results."""

    status: str = Field(..., description="Task status (completed, failed, pending)")
    output: Optional[Dict[str, Any]] = Field(None, description="Task output data")
    error: Optional[str] = Field(None, description="Error message if task failed")


class TaskResultResponse(BaseModel):
    """Response model for task result update."""

    success: bool = Field(..., description="Whether update was successful")
    message: Optional[str] = Field(None, description="Additional message")


class AgentMetrics(BaseModel):
    """Model for agent metrics."""

    status: str = Field(default="active", description="Agent status")
    tasks_completed: int = Field(default=0, description="Number of completed tasks")
    tasks_failed: int = Field(default=0, description="Number of failed tasks")
    last_activity: Optional[str] = Field(None, description="Last activity timestamp")
    last_error: Optional[str] = Field(None, description="Last error message")


class AgentStatusResponse(BaseModel):
    """Response model for agent status."""

    agents: Dict[str, AgentMetrics] = Field(..., description="Agent metrics by name")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Server status")
    database: str = Field(..., description="Database connection status")


# ============================================================================
# Database Initialization
# ============================================================================

# Global database instance
db: Optional[SQLiteStore] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.

    Startup: Initialize database
    Shutdown: Cleanup resources
    """
    global db

    # Startup
    try:
        db = SQLiteStore(db_path="emy/data/workflows.db")
        logger.info("[GATEWAY] SQLiteStore initialized on startup")
    except Exception as e:
        logger.error(f"[GATEWAY] Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    if db and db.conn:
        db.conn.close()
        logger.info("[GATEWAY] Database connection closed on shutdown")


# ============================================================================
# FastAPI App Initialization
# ============================================================================

app = FastAPI(
    title="Emy Gateway API",
    description="HTTP API for Emy workflow execution and monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Endpoint: Health Check
# ============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"]
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with status and database connection state
    """
    global db

    db_status = "connected" if db and db.conn else "disconnected"

    return HealthResponse(
        status="healthy",
        database=db_status
    )


# ============================================================================
# Endpoint: Execute Workflow
# ============================================================================

@app.post(
    "/workflows/execute",
    response_model=WorkflowResponse,
    status_code=status.HTTP_200_OK,
    tags=["Workflows"]
)
async def execute_workflow(request: WorkflowRequest) -> WorkflowResponse:
    """
    Execute a workflow.

    Creates a new workflow record and executes specified agents sequentially.

    Args:
        request: WorkflowRequest with workflow_type, agents, and input

    Returns:
        WorkflowResponse with workflow_id, status, and created_at

    Raises:
        HTTPException: If workflow creation fails
    """
    global db

    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )

    try:
        # Generate workflow ID
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        # Create workflow record
        workflow = {
            "id": workflow_id,
            "name": f"{request.workflow_type}_workflow",
            "status": "running",
            "created_at": now,
            "started_at": now,
            "completed_at": None,
            "input_data": json.dumps(request.input),
            "output_data": None,
            "error_message": None,
            "created_by": "gateway_api"
        }

        success = db.save_workflow(workflow)
        if not success:
            raise Exception("Failed to save workflow to database")

        # Create task records for each agent
        for step_num, agent_name in enumerate(request.agents, start=1):
            task_id = f"task_{workflow_id}_{step_num}"
            task = {
                "id": task_id,
                "workflow_id": workflow_id,
                "step_number": step_num,
                "agent_type": agent_name,
                "task_type": request.workflow_type,
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "input_data": json.dumps(request.input),
                "output_data": None,
                "error_message": None,
                "duration_seconds": None
            }
            db.save_task(task)

        # Initialize agent metrics if not exists
        for agent_name in request.agents:
            db.update_agent_metrics(
                agent_name,
                last_activity=now,
                status="active"
            )

        logger.info(f"[WORKFLOW] Created workflow {workflow_id} with agents: {request.agents}")

        return WorkflowResponse(
            workflow_id=workflow_id,
            status="running",
            created_at=now
        )

    except Exception as e:
        logger.error(f"[WORKFLOW] Failed to execute workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}"
        )


# ============================================================================
# Endpoint: Get Workflow
# ============================================================================

@app.get(
    "/workflows/{workflow_id}",
    response_model=WorkflowDetailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Workflows"]
)
async def get_workflow(workflow_id: str) -> WorkflowDetailResponse:
    """
    Retrieve workflow details.

    Args:
        workflow_id: The workflow ID to retrieve

    Returns:
        WorkflowDetailResponse with full workflow details

    Raises:
        HTTPException: If workflow not found
    """
    global db

    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )

    try:
        workflow = db.get_workflow(workflow_id)

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )

        # Parse JSON fields
        input_data = None
        output_data = None

        if workflow.get("input_data"):
            try:
                input_data = json.loads(workflow["input_data"])
            except json.JSONDecodeError:
                input_data = workflow["input_data"]

        if workflow.get("output_data"):
            try:
                output_data = json.loads(workflow["output_data"])
            except json.JSONDecodeError:
                output_data = workflow["output_data"]

        return WorkflowDetailResponse(
            id=workflow["id"],
            name=workflow["name"],
            status=workflow["status"],
            created_at=workflow["created_at"],
            input=input_data,
            output=output_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WORKFLOW] Failed to get workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve workflow: {str(e)}"
        )


# ============================================================================
# Endpoint: List Workflows
# ============================================================================

@app.get(
    "/workflows",
    response_model=WorkflowListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Workflows"]
)
async def list_workflows(
    limit: int = Query(10, ge=1, le=100, description="Maximum workflows to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> WorkflowListResponse:
    """
    List workflows with pagination.

    Args:
        limit: Maximum number of workflows to return (1-100, default 10)
        offset: Offset for pagination (default 0)

    Returns:
        WorkflowListResponse with workflows list and total count

    Raises:
        HTTPException: If retrieval fails
    """
    global db

    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )

    try:
        # Get all workflows with limit for pagination
        all_workflows = db.get_workflow_history(limit=limit + offset)
        total = len(all_workflows)

        # Apply offset
        workflows = all_workflows[offset:offset + limit]

        # Parse JSON fields for each workflow
        for wf in workflows:
            if wf.get("input_data"):
                try:
                    wf["input_data"] = json.loads(wf["input_data"])
                except json.JSONDecodeError:
                    pass

            if wf.get("output_data"):
                try:
                    wf["output_data"] = json.loads(wf["output_data"])
                except json.JSONDecodeError:
                    pass

        return WorkflowListResponse(
            workflows=[dict(w) for w in workflows],
            total=total
        )

    except Exception as e:
        logger.error(f"[WORKFLOW] Failed to list workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}"
        )


# ============================================================================
# Endpoint: Update Task Result
# ============================================================================

@app.post(
    "/workflows/{workflow_id}/tasks/{task_id}/result",
    response_model=TaskResultResponse,
    status_code=status.HTTP_200_OK,
    tags=["Tasks"]
)
async def update_task_result(
    workflow_id: str,
    task_id: str,
    request: TaskResultRequest
) -> TaskResultResponse:
    """
    Update a task result within a workflow.

    Args:
        workflow_id: The workflow ID
        task_id: The task ID to update
        request: TaskResultRequest with status, output, and error

    Returns:
        TaskResultResponse with success status

    Raises:
        HTTPException: If task update fails
    """
    global db

    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )

    # Validate status
    valid_statuses = ["pending", "running", "completed", "failed"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    try:
        # Get task to verify it exists
        task = db.get_task(task_id)

        if not task:
            logger.warning(f"[TASK] Task {task_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )

        if task["workflow_id"] != workflow_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task {task_id} does not belong to workflow {workflow_id}"
            )

        # Update task
        now = datetime.now(timezone.utc).isoformat()
        updated_task = dict(task)
        updated_task["status"] = request.status
        updated_task["output_data"] = json.dumps(request.output) if request.output else None
        updated_task["error_message"] = request.error
        updated_task["completed_at"] = now if request.status in ["completed", "failed"] else None

        success = db.save_task(updated_task)

        if not success:
            raise Exception("Failed to save task to database")

        # Update workflow status if all tasks complete
        workflow = db.get_workflow(workflow_id)
        workflow_tasks = db.get_workflow_tasks(workflow_id)

        all_completed = all(t["status"] in ["completed", "failed"] for t in workflow_tasks)
        if all_completed:
            final_status = "completed" if all(t["status"] == "completed" for t in workflow_tasks) else "failed"
            db.update_workflow_status(workflow_id, final_status)

        logger.info(f"[TASK] Updated task {task_id} with status {request.status}")

        return TaskResultResponse(
            success=True,
            message="Task result updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TASK] Failed to update task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task result: {str(e)}"
        )


# ============================================================================
# Endpoint: Get Agent Status
# ============================================================================

@app.get(
    "/agents/status",
    response_model=AgentStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["Agents"]
)
async def get_agent_status() -> AgentStatusResponse:
    """
    Get status and metrics for all agents.

    Returns:
        AgentStatusResponse with agent metrics

    Raises:
        HTTPException: If retrieval fails
    """
    global db

    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )

    try:
        # Known agent types
        known_agents = [
            "KnowledgeAgent",
            "TradingAgent",
            "ResearchAgent",
            "ProjectMonitorAgent"
        ]

        agents_status = {}

        for agent_name in known_agents:
            metrics = db.get_agent_metrics(agent_name)

            if metrics:
                agents_status[agent_name] = AgentMetrics(
                    status=metrics.get("status", "active"),
                    tasks_completed=metrics.get("tasks_completed", 0),
                    tasks_failed=metrics.get("tasks_failed", 0),
                    last_activity=metrics.get("last_activity"),
                    last_error=metrics.get("last_error")
                )
            else:
                # Initialize metrics for new agents
                agents_status[agent_name] = AgentMetrics(
                    status="active",
                    tasks_completed=0,
                    tasks_failed=0,
                    last_activity=None,
                    last_error=None
                )

        return AgentStatusResponse(agents=agents_status)

    except Exception as e:
        logger.error(f"[AGENTS] Failed to get agent status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent status: {str(e)}"
        )


# ============================================================================
# Middleware & Logging
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    """Log all HTTP requests."""
    logger.info(f"[HTTP] {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"[HTTP] Response: {response.status_code}")
    return response


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTPException with structured response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError with structured response."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": f"Invalid value: {str(exc)}",
            "status_code": status.HTTP_400_BAD_REQUEST
        },
    )


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["System"])
async def root() -> dict:
    """Root endpoint with API documentation link."""
    return {
        "message": "Emy Gateway API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
