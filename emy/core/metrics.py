from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel
import os

# ====== RESPONSE MODELS ======
class AgentMetric(BaseModel):
    name: str
    status: str  # healthy, executing, error, disabled
    last_execution: str  # ISO format
    execution_count_today: int
    last_result_summary: str

class WorkflowMetric(BaseModel):
    workflow_id: str
    type: str
    agent: str
    status: str
    created_at: str
    duration_seconds: float
    output_summary: str

class WorkflowMetrics(BaseModel):
    total_today: int
    running: int
    completed: int
    failed: int
    recent: List[WorkflowMetric]

class BudgetMetrics(BaseModel):
    daily_limit: float
    spent_today: float
    percentage_used: float
    remaining: float
    currency: str = "USD"

class SystemMetrics(BaseModel):
    response_time_ms: float
    db_disk_usage_gb: float
    db_disk_limit_gb: float
    db_usage_percentage: float
    rate_limit_hits_today: int
    rate_limit_max: int
    uptime_seconds: int
    status: str  # ok, warning, error

class MetricsResponse(BaseModel):
    timestamp: str
    agents: List[AgentMetric]
    workflows: WorkflowMetrics
    budget: BudgetMetrics
    system: SystemMetrics

# ====== METRICS COLLECTION ======
def collect_metrics() -> MetricsResponse:
    """Collect all dashboard metrics from database and system"""

    # Get agent status
    agents = get_agent_metrics()

    # Get workflow metrics
    workflows = get_workflow_metrics()

    # Get budget metrics
    budget = get_budget_metrics()

    # Get system metrics
    system = get_system_metrics()

    return MetricsResponse(
        timestamp=datetime.utcnow().isoformat() + "Z",
        agents=agents,
        workflows=workflows,
        budget=budget,
        system=system
    )

def get_agent_metrics() -> List[AgentMetric]:
    """Get status of all agents"""
    # Query database for agent status
    # For now, return hardcoded agents based on current system
    agents = [
        AgentMetric(
            name="TradingAgent",
            status="healthy",
            last_execution=datetime.utcnow().isoformat() + "Z",
            execution_count_today=0,
            last_result_summary="Awaiting market data"
        ),
        AgentMetric(
            name="ResearchAgent",
            status="healthy",
            last_execution=datetime.utcnow().isoformat() + "Z",
            execution_count_today=0,
            last_result_summary="Ready for queries"
        ),
        AgentMetric(
            name="KnowledgeAgent",
            status="healthy",
            last_execution=datetime.utcnow().isoformat() + "Z",
            execution_count_today=0,
            last_result_summary="Ready for queries"
        )
    ]
    return agents

def get_workflow_metrics() -> WorkflowMetrics:
    """Get workflow execution metrics"""
    # For now, return empty metrics (will populate from database in future)
    return WorkflowMetrics(
        total_today=0,
        completed=0,
        failed=0,
        running=0,
        recent=[]
    )

def get_budget_metrics() -> BudgetMetrics:
    """Get API budget usage metrics"""
    daily_limit = 10.0  # $10/day from ENV
    spent = 0.0  # TODO: Query from database

    return BudgetMetrics(
        daily_limit=daily_limit,
        spent_today=spent,
        percentage_used=(spent / daily_limit * 100) if daily_limit > 0 else 0,
        remaining=daily_limit - spent,
        currency="USD"
    )

def get_system_metrics() -> SystemMetrics:
    """Get system health metrics"""
    import time

    # Response time (mock for now)
    response_time_ms = 100.0

    # Database disk usage
    db_path = os.getenv('DATABASE_PATH', '/data/emy.db')
    db_disk_usage = 0.1  # GB (mock)
    db_disk_limit = 2.0  # GB

    if os.path.exists(db_path):
        db_size_bytes = os.path.getsize(db_path)
        db_disk_usage = db_size_bytes / (1024 * 1024 * 1024)  # Convert to GB

    # Determine status
    status = "ok"
    if db_disk_usage > 1.8:
        status = "error"
    elif db_disk_usage > 1.5:
        status = "warning"

    return SystemMetrics(
        response_time_ms=response_time_ms,
        db_disk_usage_gb=db_disk_usage,
        db_disk_limit_gb=db_disk_limit,
        db_usage_percentage=(db_disk_usage / db_disk_limit * 100),
        rate_limit_hits_today=0,
        rate_limit_max=6000,
        uptime_seconds=int(time.time()),  # Mock
        status=status
    )
