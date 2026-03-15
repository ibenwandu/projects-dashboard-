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
    agent_groups: List[List[str]] = field(default_factory=list)  # Agent groups for parallel execution
    current_group_index: int = 0  # Which group is currently executing
    agents_executing: List[str] = field(default_factory=list)  # Agents currently running in current group

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
