"""
Centralized audit trail logging.

Logs all agent events, decisions, and state changes to database and JSON files.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from .database import get_database
from .json_schema import AuditEventSchema


class AuditLogger:
    """Centralized audit trail logger."""

    def __init__(self, export_dir: str = "agents/audit_exports"):
        """Initialize audit logger."""
        self.export_dir = export_dir
        self.db = get_database()
        Path(export_dir).mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        cycle_number: int,
        event: str,
        agent: str,
        phase: str,
        details: Optional[Dict[str, Any]] = None,
        print_to_console: bool = True
    ) -> bool:
        """
        Log audit event to database.

        Args:
            cycle_number: Workflow cycle number
            event: Event type (e.g., "ANALYST_STARTED", "APPROVAL_APPROVED")
            agent: Agent name (e.g., "ANALYST", "ORCHESTRATOR")
            phase: Workflow phase (e.g., "ANALYSIS", "IMPLEMENTATION_REVIEW")
            details: Optional event details dict
            print_to_console: Whether to print event to console

        Returns:
            Success flag
        """
        try:
            event_data = AuditEventSchema.create_event(
                cycle_number=cycle_number,
                event=event,
                agent=agent,
                phase=phase,
                details=details
            )

            # Save to database
            self.db.log_audit_event(event_data)

            # Print to console if requested
            if print_to_console:
                self._print_event(event_data)

            return True
        except Exception as e:
            print(f"[ERROR] Error logging audit event: {e}")
            return False

    def log_workflow_started(self, cycle_number: int) -> bool:
        """Log workflow start."""
        return self.log_event(
            cycle_number=cycle_number,
            event="WORKFLOW_STARTED",
            agent="ORCHESTRATOR",
            phase="STARTED",
            details={"scheduled_time": datetime.utcnow().isoformat() + "Z"}
        )

    def log_agent_started(self, cycle_number: int, agent: str, phase: str) -> bool:
        """Log agent start."""
        return self.log_event(
            cycle_number=cycle_number,
            event=f"{agent}_STARTED",
            agent=agent,
            phase=phase
        )

    def log_agent_completed(
        self,
        cycle_number: int,
        agent: str,
        phase: str,
        output_id: str,
        execution_time_seconds: float,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log agent completion."""
        details = details or {}
        details.update({
            "execution_time_seconds": execution_time_seconds,
            "output_id": output_id
        })
        return self.log_event(
            cycle_number=cycle_number,
            event=f"{agent}_COMPLETED",
            agent=agent,
            phase=phase,
            details=details
        )

    def log_approval_decision(
        self,
        cycle_number: int,
        decision: str,
        reason: str,
        test_coverage: float,
        risk_assessment: str,
        auto_approved: bool = False
    ) -> bool:
        """Log approval decision."""
        event_type = "AUTO_APPROVAL_DECISION" if auto_approved else "USER_APPROVAL_DECISION"
        return self.log_event(
            cycle_number=cycle_number,
            event=event_type,
            agent="ORCHESTRATOR",
            phase="IMPLEMENTATION_REVIEW",
            details={
                "decision": decision,
                "reason": reason,
                "test_coverage": test_coverage,
                "risk_assessment": risk_assessment,
                "auto_approved": auto_approved
            }
        )

    def log_deployment_started(self, cycle_number: int, environment: str) -> bool:
        """Log deployment start."""
        return self.log_event(
            cycle_number=cycle_number,
            event="DEPLOYMENT_STARTED",
            agent="ORCHESTRATOR",
            phase="DEPLOYMENT",
            details={"target_environment": environment}
        )

    def log_rollback(self, cycle_number: int, commit_hash: str, reason: str) -> bool:
        """Log rollback operation."""
        return self.log_event(
            cycle_number=cycle_number,
            event="ROLLBACK_INITIATED",
            agent="ORCHESTRATOR",
            phase="ROLLBACK",
            details={
                "target_commit": commit_hash,
                "reason": reason
            }
        )

    def log_workflow_completed(self, cycle_number: int, duration_seconds: float) -> bool:
        """Log workflow completion."""
        return self.log_event(
            cycle_number=cycle_number,
            event="WORKFLOW_COMPLETED",
            agent="ORCHESTRATOR",
            phase="COMPLETED",
            details={"total_duration_seconds": duration_seconds}
        )

    def export_audit_trail(self, cycle_number: Optional[int] = None) -> bool:
        """
        Export audit trail to JSON file.

        Args:
            cycle_number: If specified, export only events for this cycle

        Returns:
            Success flag
        """
        try:
            events = self.db.get_audit_trail(cycle_number=cycle_number)

            if not events:
                return False

            # Convert to dict format (handle sqlite3.Row)
            events_list = [dict(event) for event in events]

            # Filename
            if cycle_number:
                filename = f"audit_trail_cycle_{cycle_number}.json"
            else:
                filename = "audit_trail.json"

            filepath = Path(self.export_dir) / filename

            # Write to file
            with open(filepath, "w") as f:
                json.dump(events_list, f, indent=2, default=str)

            return True
        except Exception as e:
            print(f"❌ Error exporting audit trail: {e}")
            return False

    def export_approval_history(self) -> bool:
        """
        Export approval history to JSON file for user review.

        Returns:
            Success flag
        """
        try:
            approvals = self.db.get_approval_history(limit=1000)

            if not approvals:
                return False

            # Convert to dict format
            approvals_list = [dict(approval) for approval in approvals]

            filepath = Path(self.export_dir) / "approval_history.json"

            # Write to file
            with open(filepath, "w") as f:
                json.dump(approvals_list, f, indent=2, default=str)

            return True
        except Exception as e:
            print(f"❌ Error exporting approval history: {e}")
            return False

    def get_cycle_summary(self, cycle_number: int) -> Dict[str, Any]:
        """
        Get summary of all events for a cycle.

        Returns:
            Dict with event counts by type
        """
        events = self.db.get_audit_trail(cycle_number=cycle_number)

        summary = {
            "cycle_number": cycle_number,
            "total_events": len(events),
            "events_by_type": {},
            "agents_involved": set(),
            "phases": set()
        }

        for event in events:
            event_type = event["event_type"] if isinstance(event, dict) else event[3]
            agent = event.get("agent_name") if isinstance(event, dict) else (event[4] if len(event) > 4 else "")
            phase = event.get("phase") if isinstance(event, dict) else (event[5] if len(event) > 5 else "")

            summary["events_by_type"][event_type] = summary["events_by_type"].get(event_type, 0) + 1
            if agent:
                summary["agents_involved"].add(agent)
            if phase:
                summary["phases"].add(phase)

        summary["agents_involved"] = list(summary["agents_involved"])
        summary["phases"] = list(summary["phases"])

        return summary

    def _print_event(self, event_data: Dict[str, Any]):
        """Pretty-print audit event to console."""
        timestamp = event_data.get("timestamp", "")[:19]  # YYYY-MM-DD HH:MM:SS
        event = event_data.get("event", "UNKNOWN")
        agent = event_data.get("agent", "")
        phase = event_data.get("phase", "")
        cycle = event_data.get("cycle_number", "?")

        # Status indicator map for common events
        status_map = {
            "WORKFLOW_STARTED": "[START]",
            "WORKFLOW_COMPLETED": "[COMPLETE]",
            "ANALYST_STARTED": "[ANALYST]",
            "ANALYST_COMPLETED": "[OK]",
            "FOREX_EXPERT_STARTED": "[EXPERT]",
            "FOREX_EXPERT_COMPLETED": "[OK]",
            "CODING_EXPERT_STARTED": "[CODER]",
            "CODING_EXPERT_COMPLETED": "[OK]",
            "AUTO_APPROVAL_DECISION": "[AUTO]",
            "USER_APPROVAL_DECISION": "[USER]",
            "ROLLBACK_INITIATED": "[ROLLBACK]",
            "DEPLOYMENT_STARTED": "[DEPLOY]"
        }

        status = status_map.get(event, "[*]")
        print(f"{status} [{timestamp}] Cycle {cycle} | {event} | {agent} | {phase}")


# Global audit logger instance
_audit_logger_instance: Optional[AuditLogger] = None


def get_audit_logger(export_dir: str = "agents/audit_exports") -> AuditLogger:
    """Get or create global audit logger instance."""
    global _audit_logger_instance
    if _audit_logger_instance is None:
        _audit_logger_instance = AuditLogger(export_dir)
    return _audit_logger_instance
