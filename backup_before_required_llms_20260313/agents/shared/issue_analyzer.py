"""
Issue analysis utilities for Forex Trading Expert Agent.

Categorizes issues, analyzes root causes, and prioritizes recommendations.
"""

from typing import List, Dict, Any, Optional
from enum import Enum


class IssueSeverity(Enum):
    """Issue severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IssueCategory(Enum):
    """Issue categories."""
    TRAILING_SL_STALL = "TRAILING_SL_STALL"
    TRAILING_SL_ERRATIC = "TRAILING_SL_ERRATIC"
    SL_VALIDITY = "SL_VALIDITY"
    CONSISTENCY_MISMATCH = "CONSISTENCY_MISMATCH"
    LOW_WIN_RATE = "LOW_WIN_RATE"
    HIGH_DRAWDOWN = "HIGH_DRAWDOWN"
    POOR_RISK_REWARD = "POOR_RISK_REWARD"
    FREQUENT_SL_HITS = "FREQUENT_SL_HITS"
    LOSING_STREAK = "LOSING_STREAK"
    SIGNAL_LATENCY = "SIGNAL_LATENCY"


class IssueAnalyzer:
    """Analyze issues from analyst output."""

    def analyze(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze analysis.json and extract issues.

        Returns:
            List of issues with severity, category, and details
        """
        issues = []

        # Extract issues from different analysis sections
        issues.extend(self._analyze_consistency(analysis))
        issues.extend(self._analyze_stop_loss(analysis))
        issues.extend(self._analyze_trailing_sl(analysis))
        issues.extend(self._analyze_profitability(analysis))
        issues.extend(self._analyze_risk_management(analysis))

        # Sort by severity
        severity_order = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.HIGH: 1,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 3
        }
        issues.sort(key=lambda x: severity_order.get(x.get("severity"), 4))

        return issues

    def _analyze_consistency(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze consistency issues."""
        issues = []
        consistency = analysis.get("trade_consistency", {})

        # UI to Scalp-Engine consistency
        ui_se = consistency.get("ui_scalp_engine_match", {})
        if ui_se.get("mismatches", 0) > 0:
            mismatches = ui_se.get("mismatches", 0)
            severity = IssueSeverity.HIGH if mismatches > 2 else IssueSeverity.MEDIUM

            issues.append({
                "issue_id": "CONSISTENCY_UI_SE",
                "category": IssueCategory.CONSISTENCY_MISMATCH,
                "severity": severity,
                "description": f"UI and Scalp-Engine have {mismatches} entry price mismatches",
                "affected_trades": [d.get("trade_id") for d in ui_se.get("details", [])],
                "data": ui_se.get("details", []),
                "root_cause_hypothesis": "Possible execution delay or price slippage between UI and Scalp-Engine"
            })

        # Scalp-Engine to OANDA consistency
        se_oanda = consistency.get("scalp_engine_oanda_match", {})
        if se_oanda.get("mismatches", 0) > 0:
            mismatches = se_oanda.get("mismatches", 0)
            severity = IssueSeverity.CRITICAL if mismatches > 2 else IssueSeverity.HIGH

            issues.append({
                "issue_id": "CONSISTENCY_SE_OANDA",
                "category": IssueCategory.CONSISTENCY_MISMATCH,
                "severity": severity,
                "description": f"Scalp-Engine and OANDA have {mismatches} trade discrepancies",
                "affected_trades": [d.get("trade_id") for d in se_oanda.get("details", [])],
                "data": se_oanda.get("details", []),
                "root_cause_hypothesis": "Trades executed in OANDA but not logged in Scalp-Engine, or vice versa"
            })

        return issues

    def _analyze_stop_loss(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze stop loss validity issues."""
        issues = []
        sl_validation = analysis.get("stop_loss_validation", {})

        if sl_validation.get("sl_issues", 0) > 0:
            issue_count = sl_validation.get("sl_issues", 0)

            issues.append({
                "issue_id": "SL_VALIDITY",
                "category": IssueCategory.SL_VALIDITY,
                "severity": IssueSeverity.CRITICAL,
                "description": f"Found {issue_count} invalid stop loss configurations",
                "affected_trades": [d.get("trade_id") for d in sl_validation.get("details", [])],
                "data": sl_validation.get("details", []),
                "root_cause_hypothesis": "SL set in wrong direction (LONG SL above entry or SHORT SL below entry)"
            })

        return issues

    def _analyze_trailing_sl(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze trailing stop loss issues."""
        issues = []
        trailing = analysis.get("trailing_sl_analysis", {})

        sl_issues = trailing.get("issues", [])
        for issue in sl_issues:
            status = issue.get("status", "UNKNOWN")

            if status == "STALLED":
                severity = IssueSeverity.HIGH
                category = IssueCategory.TRAILING_SL_STALL
                description = f"Trailing SL stalled for {issue.get('time_since_update_minutes', 0):.0f} minutes"
                root_cause = "Possible exception in SL update loop or missing ATR data fetch"

            elif status == "ERRATIC":
                severity = IssueSeverity.MEDIUM
                category = IssueCategory.TRAILING_SL_ERRATIC
                description = f"Trailing SL jumping erratically"
                root_cause = "Possible race condition in volatility regime detection or ATR calculation"

            else:
                continue

            issues.append({
                "issue_id": f"TRAILING_SL_{issue.get('trade_id', 'UNKNOWN')}",
                "category": category,
                "severity": severity,
                "description": description,
                "affected_trades": [issue.get("trade_id")],
                "data": issue,
                "root_cause_hypothesis": root_cause
            })

        return issues

    def _analyze_profitability(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze profitability issues."""
        issues = []
        metrics = analysis.get("profitability_metrics", {})

        win_rate = metrics.get("win_rate", 1.0)
        profit_factor = metrics.get("profit_factor", 1.0)

        # Low win rate
        if win_rate < 0.5:
            issues.append({
                "issue_id": "LOW_WIN_RATE",
                "category": IssueCategory.LOW_WIN_RATE,
                "severity": IssueSeverity.CRITICAL,
                "description": f"Win rate is {win_rate*100:.1f}% (below 50% threshold)",
                "affected_trades": [],
                "data": {
                    "win_rate": win_rate,
                    "winning_trades": metrics.get("winning_trades", 0),
                    "losing_trades": metrics.get("losing_trades", 0)
                },
                "root_cause_hypothesis": "Signal generation producing too many losing trades; may need entry filtering or strategy adjustment"
            })
        elif win_rate < 0.6:
            issues.append({
                "issue_id": "LOW_WIN_RATE",
                "category": IssueCategory.LOW_WIN_RATE,
                "severity": IssueSeverity.HIGH,
                "description": f"Win rate is {win_rate*100:.1f}% (below 60% optimal)",
                "affected_trades": [],
                "data": metrics,
                "root_cause_hypothesis": "Entry signal quality could be improved with additional filters"
            })

        # Low profit factor
        if profit_factor < 1.5:
            issues.append({
                "issue_id": "LOW_PROFIT_FACTOR",
                "category": IssueCategory.LOW_WIN_RATE,
                "severity": IssueSeverity.MEDIUM,
                "description": f"Profit factor is {profit_factor:.2f} (below 1.5 threshold)",
                "affected_trades": [],
                "data": metrics,
                "root_cause_hypothesis": "Average winning trade size too small relative to losing trades"
            })

        return issues

    def _analyze_risk_management(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze risk management issues."""
        issues = []
        risk_metrics = analysis.get("risk_management_metrics", {})
        profit_metrics = analysis.get("profitability_metrics", {})

        # High drawdown
        max_drawdown_pct = risk_metrics.get("max_drawdown_percent", 0)
        if max_drawdown_pct > 5:
            issues.append({
                "issue_id": "HIGH_DRAWDOWN",
                "category": IssueCategory.HIGH_DRAWDOWN,
                "severity": IssueSeverity.HIGH,
                "description": f"Max drawdown is {max_drawdown_pct:.1f}% (above 5% threshold)",
                "affected_trades": [],
                "data": risk_metrics,
                "root_cause_hypothesis": "Position sizing too aggressive for volatility or SL too far from entry"
            })

        # Frequent SL hits
        sl_hit_rate = risk_metrics.get("stop_loss_hit_rate", 0)
        if sl_hit_rate > 0.4:
            issues.append({
                "issue_id": "FREQUENT_SL_HITS",
                "category": IssueCategory.FREQUENT_SL_HITS,
                "severity": IssueSeverity.MEDIUM,
                "description": f"SL hit rate is {sl_hit_rate*100:.1f}% (above 40% threshold)",
                "affected_trades": [],
                "data": risk_metrics,
                "root_cause_hypothesis": "SL set too close to entry; consider widening SL or improving entry timing"
            })

        # Poor risk/reward
        rr_ratio = profit_metrics.get("risk_reward_ratio", 1.0)
        if rr_ratio < 1.0:
            issues.append({
                "issue_id": "POOR_RISK_REWARD",
                "category": IssueCategory.POOR_RISK_REWARD,
                "severity": IssueSeverity.MEDIUM,
                "description": f"Risk/reward ratio is {rr_ratio:.2f} (below 1.0 optimal)",
                "affected_trades": [],
                "data": {"risk_reward_ratio": rr_ratio},
                "root_cause_hypothesis": "Take profit targets too close to entry; should increase TP distance"
            })

        return issues


class RootCauseAnalyzer:
    """Perform deeper root cause analysis."""

    def analyze_issue_relationship(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze relationships between issues to identify root causes.

        Returns:
            {
                "root_causes": [
                    {
                        "cause": "...",
                        "affected_issues": [...],
                        "severity": "...",
                        "confidence": 0.0-1.0
                    }
                ],
                "clusters": [...]
            }
        """
        root_causes = []

        # Check if trailing SL issues are related to ATR calculation
        trailing_issues = [i for i in issues if "TRAILING_SL" in i.get("issue_id", "")]
        if len(trailing_issues) > 1:
            root_causes.append({
                "cause": "ATR calculation or volatility regime detection error",
                "affected_issues": [i.get("issue_id") for i in trailing_issues],
                "description": "Multiple trailing SL issues suggest systematic problem in ATR or regime logic",
                "severity": IssueSeverity.CRITICAL,
                "confidence": 0.85
            })

        # Check if consistency issues lead to other problems
        consistency_issues = [i for i in issues if "CONSISTENCY" in i.get("issue_id", "")]
        if consistency_issues and any("LOW_WIN" in i.get("issue_id", "") for i in issues):
            root_causes.append({
                "cause": "Data inconsistency between systems causing entry/exit mismatches",
                "affected_issues": consistency_issues + [i.get("issue_id") for i in issues if "LOW_WIN" in i.get("issue_id", "")],
                "description": "Discrepancies between UI, Scalp-Engine, and OANDA may be causing false entries",
                "severity": IssueSeverity.HIGH,
                "confidence": 0.70
            })

        # Check if SL issues are related to drawdown
        sl_issues = [i for i in issues if "SL" in i.get("issue_id", "") or "FREQUENT" in i.get("issue_id", "")]
        high_drawdown = any("HIGH_DRAWDOWN" in i.get("issue_id", "") for i in issues)
        if sl_issues and high_drawdown:
            root_causes.append({
                "cause": "Suboptimal stop loss placement or management",
                "affected_issues": [i.get("issue_id") for i in sl_issues + [i for i in issues if "HIGH_DRAWDOWN" in i.get("issue_id", "")]],
                "description": "SL issues contributing to larger drawdowns",
                "severity": IssueSeverity.HIGH,
                "confidence": 0.80
            })

        return {
            "root_causes": root_causes,
            "total_issues": len(issues),
            "critical_issues": len([i for i in issues if i.get("severity") == IssueSeverity.CRITICAL]),
            "high_issues": len([i for i in issues if i.get("severity") == IssueSeverity.HIGH])
        }
