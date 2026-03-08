"""
Monitoring Agent - Phase 6 Implementation

Tracks post-deployment performance and detects issues.

Workflow:
1. Retrieve deployment information (Phase 5 approval)
2. Collect current trading data
3. Calculate performance metrics
4. Compare to baseline
5. Detect anomalies and regressions
6. Generate alerts
7. Export monitoring report

Run: python -m agents.monitoring_agent
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

from agents.shared.database import get_database
from agents.shared.audit_logger import get_audit_logger
from agents.shared.performance_tracker import PerformanceTracker, PerformanceMetrics
from agents.shared.anomaly_detector import AnomalyDetector


class MonitoringAgent:
    """Monitoring agent for post-deployment performance tracking."""

    def __init__(self):
        """Initialize monitoring agent."""
        self.db = get_database()
        self.audit = get_audit_logger()

        self.performance_tracker = PerformanceTracker()
        self.anomaly_detector = AnomalyDetector()

    def run_monitoring(self, cycle_number: int, lookback_hours: int = 24) -> bool:
        """
        Run monitoring for deployed changes.

        Args:
            cycle_number: Current cycle number
            lookback_hours: Hours to lookback for data

        Returns:
            Success flag
        """
        start_time = time.time()

        try:
            self.audit.log_agent_started(
                cycle_number=cycle_number,
                agent="MONITORING",
                phase="PERFORMANCE_MONITORING"
            )

            print("[MONITOR] Starting monitoring cycle...")

            # Step 1: Get approval/deployment info
            print("[MONITOR] Retrieving deployment information...")
            approval = self.db.get_latest_approval()
            if not approval:
                print("[WARNING] No approval record found")
                return False

            approval_data = approval.get("approval_json", "{}")
            if isinstance(approval_data, str):
                approval_data = json.loads(approval_data)

            # Step 2: Get baseline metrics (pre-deployment)
            print("[MONITOR] Retrieving baseline metrics...")
            baseline_metrics = self._get_baseline_metrics(cycle_number)
            if baseline_metrics:
                self.performance_tracker.set_baseline(baseline_metrics)
                print(f"  - Baseline win rate: {baseline_metrics.win_rate:.1%}")
                print(f"  - Baseline drawdown: {baseline_metrics.max_drawdown_pips:.1f} pips")

            # Step 3: Collect current trading data
            print("[MONITOR] Collecting current trading data...")
            trades = self._collect_recent_trades(lookback_hours)
            print(f"  - Found {len(trades)} trades in last {lookback_hours} hours")

            # Step 4: Calculate current metrics
            print("[MONITOR] Calculating performance metrics...")
            current_metrics = self.performance_tracker.calculate_metrics(
                trades,
                period_start=approval_data.get("metadata", {}).get("timestamp"),
                period_end=datetime.utcnow().isoformat() + "Z"
            )
            self.performance_tracker.record_metrics(current_metrics)

            # Step 5: Detect anomalies
            print("[MONITOR] Detecting anomalies and regressions...")
            monitoring_report = self._generate_monitoring_report(
                current_metrics,
                baseline_metrics,
                approval_data
            )

            # Step 6: Check for critical issues
            critical_issues = monitoring_report.get("anomalies", {}).get("critical_issues_count", 0)
            high_issues = monitoring_report.get("anomalies", {}).get("high_issues_count", 0)

            if critical_issues > 0:
                print(f"[ALERT] CRITICAL: {critical_issues} critical issues detected")
                monitoring_report["action_required"] = "IMMEDIATE_REVIEW"
            elif high_issues > 0:
                print(f"[ALERT] WARNING: {high_issues} high-severity issues detected")
                monitoring_report["action_required"] = "REVIEW_RECOMMENDED"
            else:
                print("[OK] Performance within acceptable parameters")
                monitoring_report["action_required"] = "NONE"

            # Step 7: Save monitoring report
            print("[MONITOR] Saving monitoring report to database...")
            report_id = self.db.save_monitoring_report(
                cycle_number,
                json.dumps(monitoring_report, indent=2, default=str)
            )

            # Log completion
            execution_time = time.time() - start_time
            self.audit.log_agent_completed(
                cycle_number=cycle_number,
                agent="MONITORING",
                phase="PERFORMANCE_MONITORING",
                output_id=f"monitor_{report_id}",
                execution_time_seconds=execution_time
            )

            # Log monitoring event
            self.audit.log_event(
                cycle_number=cycle_number,
                event="MONITORING_COMPLETED",
                agent="MONITORING",
                phase="PERFORMANCE_MONITORING",
                details={
                    "trades_analyzed": len(trades),
                    "win_rate": current_metrics.win_rate,
                    "max_drawdown_pips": current_metrics.max_drawdown_pips,
                    "critical_issues": critical_issues,
                    "high_issues": high_issues,
                    "action_required": monitoring_report.get("action_required")
                }
            )

            print(f"[MONITOR] Monitoring complete ({execution_time:.1f}s)")
            return True

        except Exception as e:
            print(f"[ERROR] Monitoring Agent failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_baseline_metrics(self, cycle_number: int) -> Optional[PerformanceMetrics]:
        """
        Get baseline metrics from before deployment.

        Args:
            cycle_number: Current cycle number

        Returns:
            PerformanceMetrics or None
        """
        try:
            # In real scenario, would retrieve pre-deployment metrics from database
            # For now, return None as no historical data exists
            return None
        except Exception:
            return None

    def _collect_recent_trades(self, lookback_hours: int) -> list:
        """
        Collect recent trades for analysis.

        Args:
            lookback_hours: Hours to lookback

        Returns:
            List of trade records
        """
        # In real scenario, would query trading database
        # For now, return empty list
        return []

    def _generate_monitoring_report(
        self,
        current_metrics: PerformanceMetrics,
        baseline_metrics: Optional[PerformanceMetrics],
        approval_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive monitoring report.

        Args:
            current_metrics: Current performance metrics
            baseline_metrics: Baseline metrics for comparison
            approval_data: Original approval decision

        Returns:
            Monitoring report dict
        """
        report = {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "monitoring_id": f"monitor_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "approval_id": approval_data.get("metadata", {}).get("implementation_id", "")
            },
            "current_metrics": current_metrics.to_dict(),
            "baseline_metrics": baseline_metrics.to_dict() if baseline_metrics else None,
            "comparison": None,
            "anomalies": None,
            "performance_status": "UNKNOWN",
            "recommendations": []
        }

        # Compare to baseline
        if baseline_metrics:
            comparison = self.performance_tracker.compare_to_baseline()
            report["comparison"] = comparison

        # Generate anomaly report
        metrics_dict = {
            "win_rate": current_metrics.win_rate,
            "profit_factor": current_metrics.profit_factor,
            "max_drawdown_pips": current_metrics.max_drawdown_pips,
            "max_drawdown_percent": current_metrics.max_drawdown_percent,
            "recovery_factor": current_metrics.recovery_factor,
            "rr_ratio": current_metrics.risk_reward_ratio,
            "sharpe_ratio": current_metrics.sharpe_ratio,
            "stop_loss_hit_rate": current_metrics.stop_loss_hit_rate,
            "current_streak_type": current_metrics.current_streak_type,
            "current_streak_count": current_metrics.current_streak_count
        }

        baseline_dict = baseline_metrics.to_dict() if baseline_metrics else None
        anomaly_report = self.anomaly_detector.generate_anomaly_report(
            metrics_dict,
            baseline_dict,
            max_drawdown_threshold=approval_data.get("test_coverage", 5.0)
        )
        report["anomalies"] = anomaly_report

        # Determine performance status
        status = anomaly_report.get("overall_status", "UNKNOWN")
        report["performance_status"] = status

        # Generate recommendations
        if status == "CRITICAL":
            report["recommendations"].append({
                "priority": "URGENT",
                "action": "Immediate review and potential rollback required",
                "reason": "Critical anomalies detected"
            })
        elif status == "WARNING":
            report["recommendations"].append({
                "priority": "HIGH",
                "action": "Close monitoring recommended",
                "reason": "High-severity issues detected"
            })
        elif status == "CAUTION":
            report["recommendations"].append({
                "priority": "MEDIUM",
                "action": "Continue monitoring with attention to metrics",
                "reason": "Potential performance concerns"
            })
        else:
            report["recommendations"].append({
                "priority": "LOW",
                "action": "Continue normal operations",
                "reason": "Performance within acceptable ranges"
            })

        return report

    def get_monitoring_history(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get monitoring history.

        Args:
            limit: Maximum number of reports

        Returns:
            History with metrics trends
        """
        return {
            "metrics_history": self.performance_tracker.get_metrics_history(limit),
            "total_reports": len(self.performance_tracker.metrics_history)
        }

    def get_performance_status(self) -> Dict[str, Any]:
        """
        Get current performance status.

        Returns:
            Status dict with latest metrics
        """
        latest = self.performance_tracker.get_latest_metrics()

        if not latest:
            return {"status": "NO_DATA"}

        return {
            "status": "OK",
            "latest_metrics": latest.to_dict(),
            "win_rate_trend": self.performance_tracker.get_trend("win_rate"),
            "drawdown_trend": self.performance_tracker.get_trend("drawdown"),
            "recovery_trend": self.performance_tracker.get_trend("recovery")
        }


def main():
    """Run monitoring agent standalone."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    cycle_number = int(os.getenv("CURRENT_CYCLE", "1"))
    lookback_hours = int(os.getenv("MONITORING_LOOKBACK_HOURS", "24"))

    agent = MonitoringAgent()
    success = agent.run_monitoring(cycle_number=cycle_number, lookback_hours=lookback_hours)

    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
