"""
JSON schema definitions for all agent outputs.

These schemas define the structure of data exchanged between agents
and stored in the SQLite database.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json


class AnalysisSchema:
    """Schema for Analyst Agent output."""

    @staticmethod
    def validate(data: Dict[str, Any]) -> bool:
        """Validate analysis JSON structure."""
        required_keys = {
            "metadata", "summary", "trade_consistency",
            "stop_loss_validation", "trailing_sl_analysis",
            "profitability_metrics", "risk_management_metrics",
            "recommendations_for_expert", "log_locations"
        }
        return all(key in data for key in required_keys)

    @staticmethod
    def create_empty() -> Dict[str, Any]:
        """Create empty analysis structure."""
        return {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "analysis_id": "",
                "agent_version": "1.0.0",
                "cycle_number": 0
            },
            "summary": {
                "total_trades_reviewed": 0,
                "period_start": "",
                "period_end": "",
                "overall_health": "UNKNOWN",  # CRITICAL, WARNING, GOOD, UNKNOWN
                "confidence_score": 0.0
            },
            "trade_consistency": {
                "ui_scalp_engine_match": {
                    "status": "UNKNOWN",
                    "matches": 0,
                    "mismatches": 0,
                    "details": []
                },
                "scalp_engine_oanda_match": {
                    "status": "UNKNOWN",
                    "matches": 0,
                    "mismatches": 0,
                    "details": []
                }
            },
            "stop_loss_validation": {
                "total_sl_checks": 0,
                "sl_correct": 0,
                "sl_issues": 0,
                "details": []
            },
            "trailing_sl_analysis": {
                "total_trailing_sl": 0,
                "actively_trailing": 0,
                "not_trailing": 0,
                "issues": []
            },
            "profitability_metrics": {
                "total_profit_pips": 0.0,
                "total_loss_pips": 0.0,
                "net_profit_pips": 0.0,
                "win_rate": 0.0,
                "winning_trades": 0,
                "losing_trades": 0,
                "average_win_pips": 0.0,
                "average_loss_pips": 0.0,
                "profit_factor": 0.0,
                "risk_reward_ratio": 0.0
            },
            "risk_management_metrics": {
                "max_drawdown_pips": 0.0,
                "max_drawdown_percent": 0.0,
                "stop_loss_hit_rate": 0.0,
                "average_sl_distance_pips": 0.0,
                "largest_winning_trade_pips": 0.0,
                "largest_losing_trade_pips": 0.0
            },
            "recommendations_for_expert": {
                "priority_issues": [],
                "opportunities": []
            },
            "log_locations": {
                "ui_logs": "",
                "scalp_engine_logs": "",
                "oanda_logs": ""
            }
        }


class RecommendationSchema:
    """Schema for Forex Trading Expert Agent output."""

    @staticmethod
    def validate(data: Dict[str, Any]) -> bool:
        """Validate recommendations JSON structure."""
        required_keys = {
            "metadata", "executive_summary",
            "critical_issues_requiring_code_changes",
            "performance_improvement_recommendations",
            "non_code_recommendations"
        }
        return all(key in data for key in required_keys)

    @staticmethod
    def create_empty() -> Dict[str, Any]:
        """Create empty recommendations structure."""
        return {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "recommendation_id": "",
                "agent_version": "1.0.0",
                "analysis_id": "",
                "cycle_number": 0
            },
            "executive_summary": {
                "overall_assessment": "",
                "confidence_level": 0.0,
                "recommended_actions": 0,
                "estimated_impact": {
                    "win_rate_improvement": 0.0,
                    "risk_reward_improvement": 0.0,
                    "max_drawdown_reduction_percent": 0.0
                }
            },
            "critical_issues_requiring_code_changes": [],
            "performance_improvement_recommendations": [],
            "non_code_recommendations": []
        }


class ImplementationSchema:
    """Schema for Coding Expert Agent output."""

    @staticmethod
    def validate(data: Dict[str, Any]) -> bool:
        """Validate implementation JSON structure."""
        required_keys = {
            "metadata", "summary", "implementations",
            "git_details", "test_results", "deployment_readiness"
        }
        return all(key in data for key in required_keys)

    @staticmethod
    def create_empty() -> Dict[str, Any]:
        """Create empty implementation structure."""
        return {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "implementation_id": "",
                "agent_version": "1.0.0",
                "recommendation_id": "",
                "cycle_number": 0
            },
            "summary": {
                "recommendations_processed": 0,
                "recommendations_implemented": 0,
                "recommendations_deferred": 0,
                "total_files_modified": 0,
                "total_commits": 0,
                "testing_status": "PENDING",
                "deployment_status": "PENDING"
            },
            "implementations": [],
            "git_details": {
                "commit_hash": "",
                "commit_message": "",
                "files_changed": [],
                "insertions": 0,
                "deletions": 0,
                "backup_hash": ""
            },
            "test_results": {
                "unit_tests": {"total": 0, "passed": 0, "failed": 0, "coverage": 0.0},
                "integration_tests": {"total": 0, "passed": 0, "failed": 0},
                "performance_tests": {"total": 0, "passed": 0, "failed": 0, "metrics": {}}
            },
            "deployment_readiness": {
                "status": "PENDING",
                "blockers": [],
                "warnings": [],
                "recommended_next_steps": []
            }
        }


class ApprovalSchema:
    """Schema for approval decisions."""

    @staticmethod
    def validate(data: Dict[str, Any]) -> bool:
        """Validate approval record structure."""
        required_keys = {
            "cycle", "timestamp", "decision", "test_coverage",
            "risk_assessment", "git_commit_hash", "files_modified"
        }
        return all(key in data for key in required_keys)

    @staticmethod
    def create_empty(cycle_number: int, implementation_id: int) -> Dict[str, Any]:
        """Create empty approval record."""
        return {
            "cycle": cycle_number,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "implementation_id": implementation_id,
            "decision": "PENDING",  # PENDING, APPROVED, AUTO_APPROVED, REJECTED, CHANGES_REQUESTED
            "reason": "",
            "auto_approved": False,
            "test_coverage": 0.0,
            "risk_assessment": "UNKNOWN",  # LOW, MEDIUM, HIGH, CRITICAL
            "critical_issues_count": 0,
            "git_commit_hash": "",
            "files_modified": [],
            "changes_summary": "",
            "user_reviewed": False,
            "user_reviewed_timestamp": None,
            "user_review_comments": None,
            "rollback_available": True,
            "rollback_hash": "",
            "rollback_command": ""
        }


class AuditEventSchema:
    """Schema for audit trail events."""

    @staticmethod
    def validate(data: Dict[str, Any]) -> bool:
        """Validate audit event structure."""
        required_keys = {"timestamp", "cycle_number", "event", "agent", "phase"}
        return all(key in data for key in required_keys)

    @staticmethod
    def create_event(
        cycle_number: int,
        event: str,
        agent: str,
        phase: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create audit event."""
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cycle_number": cycle_number,
            "event": event,
            "agent": agent,
            "phase": phase,
            "details": details or {}
        }


class WorkflowStateSchema:
    """Schema for orchestrator workflow state."""

    @staticmethod
    def validate(data: Dict[str, Any]) -> bool:
        """Validate workflow state structure."""
        required_keys = {"metadata", "current_workflow_state", "phase_transitions"}
        return all(key in data for key in required_keys)

    @staticmethod
    def create_empty(cycle_number: int) -> Dict[str, Any]:
        """Create empty workflow state."""
        return {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "cycle_number": cycle_number,
                "workflow_version": "1.0.0"
            },
            "current_workflow_state": {
                "phase": "PENDING",
                "status": "PENDING",
                "started_at": None,
                "expected_completion": None
            },
            "phase_transitions": [],
            "backup_registry": {},
            "next_actions": []
        }


def serialize_to_json(obj: Any) -> str:
    """Serialize object to JSON string."""
    return json.dumps(obj, indent=2, default=str)


def deserialize_from_json(json_str: str) -> Dict[str, Any]:
    """Deserialize JSON string to object."""
    return json.loads(json_str)
