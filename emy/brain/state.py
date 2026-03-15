"""LangGraph state schema for Emy Brain."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime


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
    status: str = "pending"  # Use string for JSON compatibility

    # Timestamps
    created_at: str = ""  # ISO 8601 timestamp
    updated_at: str = ""  # ISO 8601 timestamp

    # Error handling
    error: Optional[str] = None  # Error message if failed
    error_context: Dict[str, Any] = field(default_factory=dict)  # Error details


def create_initial_state(
    workflow_type: str,
    agents: List[str],
    input: Dict[str, Any],
    workflow_id: Optional[str] = None
) -> EMyState:
    """
    Create initial state for a workflow execution.

    Args:
        workflow_type: Type of workflow (e.g., "trading_health")
        agents: List of agent names
        input: User input data
        workflow_id: Optional workflow ID; generated if not provided

    Returns:
        Initial EMyState for the workflow
    """
    import uuid

    if workflow_id is None:
        workflow_id = f"wf_{uuid.uuid4().hex[:8]}"

    now = datetime.now().isoformat()

    return EMyState(
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        agents=agents,
        current_agent=None,
        input=input,
        results={},
        messages=[],
        status="pending",
        created_at=now,
        updated_at=now,
        error=None,
        error_context={}
    )
