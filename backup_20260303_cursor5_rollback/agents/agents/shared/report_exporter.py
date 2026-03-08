"""
Export Agent Analysis Results to Markdown Reports

Consolidates outputs from all 4 agent phases into a single markdown file.
Files are saved with date and cycle number for easy archiving and review.

Usage:
    from agents.shared.report_exporter import AgentReportExporter

    exporter = AgentReportExporter()
    exporter.export_cycle(cycle_number)
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import sqlite3

from agents.shared.database import get_database


class AgentReportExporter:
    """Export agent analysis results to markdown reports."""

    def __init__(self, reports_dir: str = "agent_analysis"):
        """Initialize exporter."""
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.db = get_database()

    def export_cycle(self, cycle_number: int) -> Optional[Path]:
        """
        Export complete cycle results to markdown file.

        Args:
            cycle_number: Cycle number to export

        Returns:
            Path to exported file, or None if export failed
        """
        try:
            # Retrieve all cycle data
            analysis = self._get_analysis(cycle_number)
            recommendation = self._get_recommendation(cycle_number)
            implementation = self._get_implementation(cycle_number)
            approval = self._get_approval(cycle_number)

            if not analysis:
                print(f"[EXPORT] No analysis found for cycle {cycle_number}")
                return None

            # Generate markdown content
            content = self._generate_markdown(
                cycle_number, analysis, recommendation, implementation, approval
            )

            # Save to file
            file_path = self._save_report(cycle_number, content)
            return file_path

        except Exception as e:
            print(f"[EXPORT] Error exporting cycle {cycle_number}: {e}")
            return None

    def _get_analysis(self, cycle_number: int) -> Optional[Dict[str, Any]]:
        """Get analysis from database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agent_analyses WHERE cycle_number = ?", (cycle_number,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "cycle_number": row[1],
                    "timestamp": row[2],
                    "analysis_json": json.loads(row[3]),
                    "status": row[4],
                }
            return None

    def _get_recommendation(self, cycle_number: int) -> Optional[Dict[str, Any]]:
        """Get recommendation from database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agent_recommendations WHERE cycle_number = ?",
                (cycle_number,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "cycle_number": row[1],
                    "timestamp": row[2],
                    "recommendation_json": json.loads(row[3]),
                    "status": row[4],
                }
            return None

    def _get_implementation(self, cycle_number: int) -> Optional[Dict[str, Any]]:
        """Get implementation from database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agent_implementations WHERE cycle_number = ?",
                (cycle_number,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "cycle_number": row[1],
                    "timestamp": row[2],
                    "implementation_json": json.loads(row[3]),
                    "status": row[4],
                    "git_commit_hash": row[5],
                }
            return None

    def _get_approval(self, cycle_number: int) -> Optional[Dict[str, Any]]:
        """Get approval from database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM approval_history WHERE cycle_number = ?",
                (cycle_number,),
            )
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

    def _generate_markdown(
        self,
        cycle_number: int,
        analysis: Dict[str, Any],
        recommendation: Optional[Dict[str, Any]],
        implementation: Optional[Dict[str, Any]],
        approval: Optional[Dict[str, Any]],
    ) -> str:
        """Generate markdown report from cycle data."""
        analysis_data = analysis.get("analysis_json", {})
        timestamp = analysis.get("timestamp", datetime.utcnow().isoformat())

        md = []
        md.append(f"# Agent Analysis Report - Cycle {cycle_number}")
        md.append("")
        md.append(f"**Generated**: {timestamp}")
        md.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append("")

        # Executive Summary
        md.append("## Executive Summary")
        md.append("")
        summary = analysis_data.get("summary", {})
        md.append(f"- **Overall Health**: {summary.get('overall_health', 'UNKNOWN')}")
        md.append(f"- **Confidence**: {summary.get('confidence_score', 0):.1%}")
        md.append(f"- **Trades Reviewed**: {summary.get('total_trades_reviewed', 0)}")
        md.append("")

        # Phase 1: Analyst Results
        md.append("## Phase 1: Analyst Agent Results")
        md.append("")
        md.append("### Trade Consistency")
        consistency = analysis_data.get("trade_consistency", {})
        ui_se = consistency.get("ui_scalp_engine_match", {})
        se_oanda = consistency.get("scalp_engine_oanda_match", {})
        md.append(f"- **UI vs Scalp-Engine**: {ui_se.get('status', 'UNKNOWN')} ({ui_se.get('matches', 0)} matches, {ui_se.get('mismatches', 0)} mismatches)")
        md.append(
            f"- **Scalp-Engine vs OANDA**: {se_oanda.get('status', 'UNKNOWN')} ({se_oanda.get('matches', 0)} matches, {se_oanda.get('mismatches', 0)} mismatches)"
        )
        md.append("")

        # Consistency issues
        if se_oanda.get("mismatches", 0) > 0:
            md.append("**Issues Detected**:")
            for issue in se_oanda.get("details", []):
                md.append(f"- {issue.get('pair', 'N/A')} {issue.get('direction', 'N/A')}: {issue.get('issue', 'Unknown issue')} (Severity: {issue.get('severity', 'UNKNOWN')})")
            md.append("")

        # Profitability
        md.append("### Profitability Metrics")
        metrics = analysis_data.get("profitability_metrics", {})
        md.append(f"- **Net Profit**: {metrics.get('net_profit_pips', 0)} pips")
        md.append(f"- **Win Rate**: {metrics.get('win_rate', 0):.1%}")
        md.append(f"- **Winning Trades**: {metrics.get('winning_trades', 0)}")
        md.append(f"- **Losing Trades**: {metrics.get('losing_trades', 0)}")
        if metrics.get('winning_trades', 0) > 0:
            md.append(f"- **Avg Win**: {metrics.get('average_win_pips', 0):.1f} pips")
        if metrics.get('losing_trades', 0) > 0:
            md.append(f"- **Avg Loss**: {metrics.get('average_loss_pips', 0):.1f} pips")
        md.append("")

        # Risk Management
        md.append("### Risk Management")
        risk = analysis_data.get("risk_management_metrics", {})
        md.append(f"- **Max Drawdown**: {risk.get('max_drawdown_pips', 0):.1f} pips ({risk.get('max_drawdown_percent', 0):.1%})")
        md.append(f"- **SL Hit Rate**: {risk.get('stop_loss_hit_rate', 0):.1%}")
        md.append(f"- **Avg SL Distance**: {risk.get('average_sl_distance_pips', 0):.1f} pips")
        md.append("")

        # Phase 2: Forex Expert Results
        if recommendation:
            md.append("## Phase 2: Forex Expert Recommendations")
            md.append("")
            rec_data = recommendation.get("recommendation_json", {})
            exec_summary = rec_data.get("executive_summary", {})
            md.append(f"- **Overall Assessment**: {exec_summary.get('overall_assessment', 'No assessment')}")
            md.append(f"- **Confidence**: {exec_summary.get('confidence_level', 0):.1%}")
            md.append(f"- **Issues Found**: {exec_summary.get('total_issues_found', 0)}")

            issue_breakdown = exec_summary.get("issue_breakdown", {})
            if issue_breakdown:
                md.append("  - Critical: " + str(issue_breakdown.get("critical", 0)))
                md.append("  - High: " + str(issue_breakdown.get("high", 0)))
                md.append("  - Medium: " + str(issue_breakdown.get("medium", 0)))
                md.append("  - Low: " + str(issue_breakdown.get("low", 0)))

            estimated = exec_summary.get("estimated_impact", {})
            if estimated:
                md.append("")
                md.append("**Estimated Impact**:")
                md.append(f"- Win Rate Improvement: {estimated.get('win_rate_improvement', 0):+.1%}")
                md.append(f"- Risk/Reward Improvement: {estimated.get('risk_reward_improvement', 0):+.1%}")
                md.append(f"- Drawdown Reduction: {estimated.get('max_drawdown_reduction_percent', 0):+.1%}")
            md.append("")

        # Phase 3: Coding Expert Results
        if implementation:
            md.append("## Phase 3: Coding Expert Implementation")
            md.append("")
            impl_data = implementation.get("implementation_json", {})
            impl_summary = impl_data.get("implementation_summary", {})
            md.append(f"- **Status**: {impl_summary.get('overall_status', 'UNKNOWN')}")
            md.append(f"- **Changes Attempted**: {impl_summary.get('changes_attempted', 0)}")
            md.append(f"- **Changes Successful**: {impl_summary.get('changes_successful', 0)}")
            md.append(f"- **Changes Failed**: {impl_summary.get('changes_failed', 0)}")

            test_results = impl_data.get("test_results", {})
            unit = test_results.get("unit_tests", {})
            md.append("")
            md.append("**Test Results**:")
            md.append(f"- **Unit Tests**: {unit.get('passed', 0)}/{unit.get('total', 0)} passed ({unit.get('coverage', 0):.1%} coverage)")
            md.append(f"- **Git Commit**: {impl_summary.get('git_commit', 'NONE')}")
            md.append("")

        # Phase 4: Orchestrator Decision
        if approval:
            md.append("## Phase 4: Orchestrator Decision")
            md.append("")
            md.append(f"- **Decision**: **{approval.get('decision', 'UNKNOWN')}**")
            md.append(f"- **Risk Assessment**: {approval.get('risk_assessment', 'UNKNOWN')}")
            md.append(f"- **Test Coverage**: {approval.get('test_coverage', 0):.1%}")
            md.append(f"- **Critical Issues**: {approval.get('critical_issues_count', 0)}")
            md.append(f"- **Auto Approved**: {'Yes' if approval.get('auto_approved') else 'No'}")
            md.append("")

        # Footer
        md.append("---")
        md.append("*Report generated by Agent Analysis System*")
        md.append(f"*Cycle: {cycle_number}*")

        return "\n".join(md)

    def _save_report(self, cycle_number: int, content: str) -> Path:
        """Save report to file."""
        # Format: YYYYMMDD_HHMMSS_cycle_N.md
        now = datetime.now()
        filename = f"{now.strftime('%Y%m%d_%H%M%S')}_cycle_{cycle_number}.md"
        file_path = self.reports_dir / filename

        with open(file_path, "w") as f:
            f.write(content)

        print(f"[EXPORT] Report saved: {file_path}")
        return file_path

    def get_latest_report(self) -> Optional[Path]:
        """Get the latest report file."""
        reports = sorted(self.reports_dir.glob("*.md"), reverse=True)
        return reports[0] if reports else None

    def list_reports(self, limit: int = 10) -> list:
        """List recent reports."""
        reports = sorted(self.reports_dir.glob("*.md"), reverse=True)
        return [str(r) for r in reports[:limit]]
