"""
Approval management for code implementations.

Handles:
- Evaluation of implementation results
- Coverage and risk assessment
- Auto-approval decision logic
- User review workflows
- Approval history tracking
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime


class ApprovalEvaluator:
    """Evaluates implementation results for approval."""

    def __init__(self):
        """Initialize approval evaluator."""
        self.coverage_threshold = 90.0
        self.max_failures_for_approval = 0
        self.auto_approval_threshold = 0.85  # Confidence level

    def evaluate(self, implementation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate implementation for approval.

        Args:
            implementation: Implementation report from Phase 4

        Returns:
            Evaluation result with decision and reasoning
        """
        evaluation = {
            "implementation_id": implementation.get("metadata", {}).get("implementation_id", ""),
            "evaluation_timestamp": datetime.utcnow().isoformat() + "Z",
            "recommendation": "PENDING",  # APPROVE, REJECT, MANUAL_REVIEW
            "confidence": 0.0,
            "blockers": [],
            "warnings": [],
            "risk_level": "UNKNOWN",
            "reasoning": ""
        }

        try:
            summary = implementation.get("summary", {})
            test_results = implementation.get("test_results", {})
            git_details = implementation.get("git_details", {})

            # Check deployment status
            deployment_status = summary.get("deployment_status", "UNKNOWN")
            if deployment_status == "BLOCKED":
                evaluation["recommendation"] = "REJECT"
                evaluation["blockers"].append("Deployment blocked by implementation")
                return evaluation

            # Check test results
            unit_tests = test_results.get("unit_tests", {})
            coverage = unit_tests.get("coverage", 0.0)
            tests_failed = unit_tests.get("failed", 0)

            # Coverage validation
            if coverage < self.coverage_threshold:
                evaluation["blockers"].append(
                    f"Coverage {coverage:.1f}% below minimum {self.coverage_threshold}%"
                )
                evaluation["recommendation"] = "REJECT"
                return evaluation

            # Test failure validation
            if tests_failed > self.max_failures_for_approval:
                evaluation["blockers"].append(
                    f"{tests_failed} tests failed (maximum allowed: {self.max_failures_for_approval})"
                )
                evaluation["recommendation"] = "REJECT"
                return evaluation

            # Risk assessment
            risk_level = self._assess_risk(implementation)
            evaluation["risk_level"] = risk_level

            # Changes validation
            changes_attempted = summary.get("changes_attempted", 0)
            changes_successful = summary.get("changes_successful", 0)

            if changes_attempted > 0 and changes_successful == 0:
                evaluation["blockers"].append("No changes were successfully applied")
                evaluation["recommendation"] = "REJECT"
                return evaluation

            if changes_attempted > 0 and changes_successful < changes_attempted:
                pct = (changes_successful / changes_attempted) * 100
                evaluation["warnings"].append(
                    f"Only {changes_successful}/{changes_attempted} changes applied ({pct:.0f}%)"
                )

            # Calculate confidence
            confidence = self._calculate_confidence(implementation, risk_level)
            evaluation["confidence"] = confidence

            # Make recommendation
            if confidence >= self.auto_approval_threshold and risk_level in ["LOW", "MEDIUM"]:
                evaluation["recommendation"] = "APPROVE"
            elif risk_level == "CRITICAL":
                evaluation["recommendation"] = "REJECT"
                evaluation["blockers"].append("Critical risk level requires rejection")
            else:
                evaluation["recommendation"] = "MANUAL_REVIEW"

            # Generate reasoning
            evaluation["reasoning"] = self._generate_reasoning(
                evaluation, coverage, tests_failed, changes_successful, changes_attempted
            )

        except Exception as e:
            evaluation["recommendation"] = "MANUAL_REVIEW"
            evaluation["warnings"].append(f"Evaluation error: {str(e)}")

        return evaluation

    def _assess_risk(self, implementation: Dict[str, Any]) -> str:
        """
        Assess risk level of implementation.

        Args:
            implementation: Implementation report

        Returns:
            Risk level: LOW, MEDIUM, HIGH, CRITICAL
        """
        risk_indicators = []
        summary = implementation.get("summary", {})
        test_results = implementation.get("test_results", {})

        # Check test results
        unit_tests = test_results.get("unit_tests", {})
        if unit_tests.get("failed", 0) > 0:
            risk_indicators.append("HIGH")

        # Check changes
        changes_attempted = summary.get("changes_attempted", 0)
        changes_successful = summary.get("changes_successful", 0)

        if changes_attempted > 5:
            risk_indicators.append("MEDIUM")

        if changes_attempted > 10:
            risk_indicators.append("HIGH")

        if changes_successful == 0 and changes_attempted > 0:
            risk_indicators.append("CRITICAL")

        # Check coverage
        coverage = unit_tests.get("coverage", 100.0)
        if coverage < 80.0:
            risk_indicators.append("HIGH")
        elif coverage < 90.0:
            risk_indicators.append("MEDIUM")

        # Determine risk level
        if "CRITICAL" in risk_indicators:
            return "CRITICAL"
        elif "HIGH" in risk_indicators:
            return "HIGH"
        elif "MEDIUM" in risk_indicators:
            return "MEDIUM"
        else:
            return "LOW"

    def _calculate_confidence(
        self,
        implementation: Dict[str, Any],
        risk_level: str
    ) -> float:
        """
        Calculate confidence level for approval.

        Args:
            implementation: Implementation report
            risk_level: Assessed risk level

        Returns:
            Confidence level (0.0-1.0)
        """
        confidence = 0.5

        summary = implementation.get("summary", {})
        test_results = implementation.get("test_results", {})

        # Test results impact
        unit_tests = test_results.get("unit_tests", {})
        total_tests = unit_tests.get("total", 0)
        passed_tests = unit_tests.get("passed", 0)

        if total_tests > 0:
            pass_rate = passed_tests / total_tests
            confidence += pass_rate * 0.3

        # Coverage impact
        coverage = unit_tests.get("coverage", 0.0)
        if coverage >= 95.0:
            confidence += 0.15
        elif coverage >= 90.0:
            confidence += 0.10
        elif coverage >= 80.0:
            confidence += 0.05

        # Risk impact
        risk_multiplier = {
            "LOW": 1.0,
            "MEDIUM": 0.8,
            "HIGH": 0.5,
            "CRITICAL": 0.0
        }
        confidence *= risk_multiplier.get(risk_level, 0.5)

        # Changes success rate
        changes_attempted = summary.get("changes_attempted", 0)
        changes_successful = summary.get("changes_successful", 0)

        if changes_attempted > 0:
            success_rate = changes_successful / changes_attempted
            confidence += success_rate * 0.1

        return min(1.0, max(0.0, confidence))

    def _generate_reasoning(
        self,
        evaluation: Dict[str, Any],
        coverage: float,
        tests_failed: int,
        changes_successful: int,
        changes_attempted: int
    ) -> str:
        """Generate reasoning for approval decision."""
        lines = []

        recommendation = evaluation["recommendation"]
        confidence = evaluation["confidence"]
        risk_level = evaluation["risk_level"]

        if recommendation == "APPROVE":
            lines.append(f"Implementation approved with {confidence:.0%} confidence")
            lines.append(f"Coverage: {coverage:.1f}% (above {self.coverage_threshold}% threshold)")
            lines.append(f"Risk Level: {risk_level}")
            if changes_attempted > 0:
                lines.append(f"Changes: {changes_successful}/{changes_attempted} successful")

        elif recommendation == "REJECT":
            lines.append("Implementation rejected due to:")
            for blocker in evaluation["blockers"]:
                lines.append(f"  - {blocker}")

        else:  # MANUAL_REVIEW
            lines.append(f"Manual review recommended (confidence: {confidence:.0%})")
            lines.append(f"Risk Level: {risk_level}")
            if evaluation["warnings"]:
                lines.append("Warnings:")
                for warning in evaluation["warnings"]:
                    lines.append(f"  - {warning}")

        return "\n".join(lines)


class ApprovalHistory:
    """Track approval decisions."""

    def __init__(self):
        """Initialize approval history."""
        self.decisions = []

    def record_evaluation(
        self,
        cycle_number: int,
        implementation_id: str,
        evaluation: Dict[str, Any]
    ) -> None:
        """
        Record an approval evaluation.

        Args:
            cycle_number: Cycle number
            implementation_id: Implementation ID
            evaluation: Evaluation result
        """
        decision = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cycle_number": cycle_number,
            "implementation_id": implementation_id,
            "recommendation": evaluation.get("recommendation"),
            "confidence": evaluation.get("confidence", 0.0),
            "risk_level": evaluation.get("risk_level"),
            "blockers": evaluation.get("blockers", []),
            "warnings": evaluation.get("warnings", [])
        }
        self.decisions.append(decision)

    def get_history(self, limit: Optional[int] = None) -> list:
        """
        Get approval history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of decisions
        """
        if limit:
            return self.decisions[-limit:]
        return self.decisions

    def get_approval_rate(self) -> float:
        """
        Calculate approval rate.

        Returns:
            Percentage of approved implementations (0.0-1.0)
        """
        if not self.decisions:
            return 0.0

        approved = len([d for d in self.decisions if d.get("recommendation") == "APPROVE"])
        return approved / len(self.decisions)

    def get_decision_stats(self) -> Dict[str, Any]:
        """
        Get decision statistics.

        Returns:
            Stats dict with counts by recommendation type
        """
        stats = {
            "total_decisions": len(self.decisions),
            "approved": 0,
            "rejected": 0,
            "manual_review": 0,
            "average_confidence": 0.0
        }

        for decision in self.decisions:
            rec = decision.get("recommendation")
            if rec == "APPROVE":
                stats["approved"] += 1
            elif rec == "REJECT":
                stats["rejected"] += 1
            elif rec == "MANUAL_REVIEW":
                stats["manual_review"] += 1

        if self.decisions:
            avg_confidence = sum(d.get("confidence", 0) for d in self.decisions) / len(self.decisions)
            stats["average_confidence"] = avg_confidence

        return stats
