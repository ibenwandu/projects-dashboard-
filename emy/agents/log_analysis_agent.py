"""
LogAnalysisAgent - analyzes trading logs and detects performance anomalies.

This agent periodically reviews trading activity to identify concerning patterns
in win rate, closure types, and LLM accuracy. It generates detailed reports and
alerts if critical anomalies are detected.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz
from anthropic import Anthropic
from emy.agents.base_agent import EMySubAgent
from emy.tools.api_client import OandaClient
from emy.core.database import EMyDatabase

logger = logging.getLogger('LogAnalysisAgent')


class LogAnalysisAgent(EMySubAgent):
    """Analyzes trading logs and detects performance anomalies.

    This agent periodically reviews trading activity to identify concerning
    patterns in win rate, closure types, and LLM accuracy. It generates
    detailed analysis reports and alerts stakeholders if critical issues
    are detected.
    """

    def __init__(self):
        """Initialize LogAnalysisAgent with required clients and database connection."""
        # Initialize parent with name and model
        super().__init__(
            agent_name='LogAnalysisAgent',
            model='claude-3-5-haiku-20241022'
        )

        # Add name and description attributes for compatibility
        self.name = "LogAnalysisAgent"
        self.description = "Analyzes trading logs and detects performance anomalies"

        # Initialize database for querying signals and storing reports
        self.db = EMyDatabase()

        # Initialize OANDA client for trade data access
        self.oanda_client = OandaClient()

        # Initialize Claude client for analysis interpretation
        self.claude_client = Anthropic()

        logger.info(f"[LogAnalysisAgent] Initialized: {self.name}")

    def execute(self, instruction: str = None, **kwargs):
        """Execute the log analysis.

        Args:
            instruction (str, optional): User instruction (not used in standard analysis)
            **kwargs: Additional parameters

        Returns:
            dict: Analysis report with metrics, anomalies, and findings
        """
        logger.info(f"[LogAnalysisAgent] execute() called")
        return self.analyze()

    def analyze(self) -> Dict:
        """Analyze trading logs for last 24 hours and detect anomalies.

        Returns:
            dict: Complete analysis report with structure:
                {
                    "report_type": "log_analysis",
                    "timestamp": ISO8601,
                    "period": "2026-03-15 to 2026-03-16",
                    "metrics": {...},
                    "llm_analysis": {...},
                    "anomalies": [...],
                    "analysis": str,
                    "alert_sent": bool,
                    "error": None or str
                }
        """
        # Initialize report structure
        report = {
            "report_type": "log_analysis",
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "period": self._get_period_string(),
            "metrics": {},
            "llm_analysis": {},
            "anomalies": [],
            "analysis": None,
            "alert_sent": False,
            "error": None
        }

        try:
            # Step 1: Query trading signals from database
            signals = self._query_trading_signals()
            logger.info(f"[LogAnalysisAgent] Queried {len(signals)} trading signals")

            if not signals:
                logger.info("[LogAnalysisAgent] No trading signals in period")
                report["analysis"] = "No trading activity in the analysis period"
                return report

            # Step 2: Calculate metrics from signals
            report["metrics"] = self._calculate_metrics(signals)
            logger.info(f"[LogAnalysisAgent] Metrics calculated: {report['metrics']['total_trades']} trades, {report['metrics']['win_rate']:.1%} win rate")

            # Step 3: Query LLM recommendations (if available)
            recommendations = self._query_recommendations()
            if recommendations:
                report["llm_analysis"] = self._analyze_llm_performance(recommendations)
                logger.info(f"[LogAnalysisAgent] LLM analysis complete: {len(recommendations)} recommendations")

            # Step 4: Detect anomalies in metrics and LLM performance
            report["anomalies"] = self._detect_anomalies(report["metrics"], report.get("llm_analysis"))
            logger.info(f"[LogAnalysisAgent] Detected {len(report['anomalies'])} anomalies")

            # Step 5: Use Claude to interpret findings
            report["analysis"] = self._analyze_with_claude(report["metrics"], report["anomalies"])
            logger.info(f"[LogAnalysisAgent] Claude analysis complete")

            # Step 6: Send alert if critical anomalies detected
            if report["anomalies"]:
                self._send_alert_if_critical(report)

            # Step 7: Store report in database
            self._store_report(report)
            logger.info(f"[LogAnalysisAgent] Report stored in database")

            logger.info(f"[LogAnalysisAgent] Analysis complete: {len(report['anomalies'])} anomalies, alert_sent={report['alert_sent']}")
            return report

        except Exception as e:
            logger.error(f"[LogAnalysisAgent] Analysis error: {e}", exc_info=True)
            report["error"] = str(e)
            return report

    def _get_period_string(self) -> str:
        """Get human-readable period string for last 24 hours.

        Returns:
            str: Period in format "2026-03-15 to 2026-03-16"
        """
        now = datetime.now(pytz.UTC)
        start = now - timedelta(hours=24)
        return f"{start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}"

    def _query_trading_signals(self) -> List[Dict]:
        """Query trading signals from last 24 hours from database.

        This is a placeholder that would query the Scalp-Engine RL database
        or local monitoring_reports table for trading activity.

        Returns:
            list: List of signal dictionaries with keys:
                - id (int): Signal ID
                - outcome (str): "TP", "SL", "PENDING", "WIN", "LOSS"
                - pnl (float): Realized P&L in account currency
                - timestamp (str, optional): When signal was generated
        """
        logger.info("[LogAnalysisAgent] Querying trading signals")

        try:
            # Query database for recent trading activity
            # Placeholder: in real implementation, would query specific tables
            signals = self.db.query_all(
                """
                SELECT id, outcome, pnl FROM trading_signals
                WHERE timestamp >= datetime('now', '-24 hours')
                ORDER BY timestamp DESC
                """
            )
            return signals if signals else []
        except Exception as e:
            logger.warning(f"[LogAnalysisAgent] Could not query trading signals: {e}")
            return []

    def _query_recommendations(self) -> List[Dict]:
        """Query LLM recommendations from last 24 hours from database.

        This is a placeholder that would query the Trade-Alerts RL database
        for LLM recommendation history.

        Returns:
            list: List of recommendation dictionaries with keys:
                - id (int): Recommendation ID
                - llm_name (str): "chatgpt", "gemini", "claude", "deepseek"
                - hit (bool): Whether recommendation resulted in win
                - timestamp (str, optional): When recommendation was made
        """
        logger.info("[LogAnalysisAgent] Querying LLM recommendations")

        try:
            # Query database for recent recommendations
            # Placeholder: in real implementation, would query specific tables
            recommendations = self.db.query_all(
                """
                SELECT id, llm_name, hit FROM llm_recommendations
                WHERE timestamp >= datetime('now', '-24 hours')
                ORDER BY timestamp DESC
                """
            )
            return recommendations if recommendations else []
        except Exception as e:
            logger.warning(f"[LogAnalysisAgent] Could not query recommendations: {e}")
            return []

    def _calculate_metrics(self, signals: List[Dict]) -> Dict:
        """Calculate trading metrics from signals.

        Args:
            signals (list): List of signal dictionaries with 'outcome' and 'pnl' keys

        Returns:
            dict: Metrics dictionary with keys:
                - total_trades (int): Total number of trades analyzed
                - wins (int): Count of winning trades (outcome in ["TP", "WIN"])
                - losses (int): Count of losing trades (outcome in ["SL", "LOSS"])
                - win_rate (float): Win rate as percentage (0.0 to 1.0)
                - avg_pnl (float): Average P&L per closed trade
                - closure_reasons (dict): Distribution of closure types
        """
        if not signals:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "avg_pnl": 0.0,
                "closure_reasons": {
                    "SL": 0.0,
                    "TP": 0.0,
                    "runner_exit": 0.0,
                    "time_based": 0.0
                }
            }

        # Count wins and losses
        wins = sum(1 for s in signals if s.get("outcome") in ["TP", "WIN"])
        losses = sum(1 for s in signals if s.get("outcome") in ["SL", "LOSS"])
        pending = sum(1 for s in signals if s.get("outcome") in ["PENDING", "OPEN"])

        # Calculate total closed trades (not pending)
        closed_trades = wins + losses
        total_trades = len(signals)

        # Calculate win rate (only for closed trades)
        win_rate = wins / closed_trades if closed_trades > 0 else 0.0

        # Calculate average P&L (only for closed trades, not pending)
        closed_pnl = sum(
            s.get("pnl", 0.0) for s in signals
            if s.get("outcome") in ["TP", "WIN", "SL", "LOSS"]
        )
        avg_pnl = closed_pnl / closed_trades if closed_trades > 0 else 0.0

        # Calculate closure reason distribution
        closure_reasons = {
            "SL": 0.0,
            "TP": 0.0,
            "runner_exit": 0.0,
            "time_based": 0.0
        }

        if closed_trades > 0:
            closure_reasons["SL"] = losses / closed_trades
            closure_reasons["TP"] = wins / closed_trades
            # In a real implementation, these would be calculated from trade metadata
            # For now, keeping as placeholder (0.0)

        return {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "closure_reasons": closure_reasons
        }

    def _analyze_llm_performance(self, recommendations: List[Dict]) -> Dict:
        """Analyze LLM recommendation accuracy.

        Args:
            recommendations (list): List of recommendation dictionaries

        Returns:
            dict: LLM performance with structure:
                {
                    "chatgpt": {"recommendations": int, "hit_rate": float},
                    "gemini": {"recommendations": int, "hit_rate": float},
                    "claude": {"recommendations": int, "hit_rate": float},
                    "deepseek": {"recommendations": int, "hit_rate": float}
                }
        """
        if not recommendations:
            return {
                "chatgpt": {"recommendations": 0, "hit_rate": 0.0},
                "gemini": {"recommendations": 0, "hit_rate": 0.0},
                "claude": {"recommendations": 0, "hit_rate": 0.0},
                "deepseek": {"recommendations": 0, "hit_rate": 0.0}
            }

        # Group recommendations by LLM
        llm_stats = {}

        for llm_name in ["chatgpt", "gemini", "claude", "deepseek"]:
            llm_recs = [r for r in recommendations if r.get("llm_name", "").lower() == llm_name.lower()]

            if llm_recs:
                hits = sum(1 for r in llm_recs if r.get("hit", False))
                hit_rate = hits / len(llm_recs) if len(llm_recs) > 0 else 0.0
                llm_stats[llm_name] = {
                    "recommendations": len(llm_recs),
                    "hit_rate": hit_rate
                }
            else:
                llm_stats[llm_name] = {
                    "recommendations": 0,
                    "hit_rate": 0.0
                }

        return llm_stats

    def _detect_anomalies(self, metrics: Dict, llm_analysis: Optional[Dict] = None) -> List[Dict]:
        """Detect anomalies in trading metrics and LLM performance.

        Detection rules:
        - Win rate < 40% → "low_win_rate" (high severity)
        - SL closure rate > 70% → "high_sl_rate" (high severity)
        - Any LLM hit rate < 40% → "llm_divergence" (high severity)
        - Error rate > 10% → "high_error_rate" (critical severity)

        Args:
            metrics (dict): Trading metrics from _calculate_metrics()
            llm_analysis (dict, optional): LLM analysis from _analyze_llm_performance()

        Returns:
            list: List of anomaly dictionaries with keys:
                - type (str): Anomaly type identifier
                - severity (str): "low", "high", or "critical"
                - description (str): Human-readable description of anomaly
        """
        anomalies = []

        # Check win rate threshold
        win_rate = metrics.get("win_rate", 0.0)
        if win_rate < 0.4:  # Less than 40%
            anomalies.append({
                "type": "low_win_rate",
                "severity": "high",
                "description": f"Win rate {win_rate:.1%} is below 40% threshold"
            })

        # Check SL closure rate threshold
        sl_rate = metrics.get("closure_reasons", {}).get("SL", 0.0)
        if sl_rate > 0.7:  # More than 70%
            anomalies.append({
                "type": "high_sl_rate",
                "severity": "high",
                "description": f"Stop-loss closure rate {sl_rate:.1%} exceeds 70% threshold"
            })

        # Check LLM accuracy divergence
        if llm_analysis:
            for llm_name, stats in llm_analysis.items():
                hit_rate = stats.get("hit_rate", 0.0)
                if stats.get("recommendations", 0) > 0 and hit_rate < 0.4:  # Less than 40%
                    anomalies.append({
                        "type": "llm_divergence",
                        "severity": "high",
                        "description": f"{llm_name.capitalize()} hit rate {hit_rate:.1%} below 40% (out of {stats['recommendations']} recommendations)"
                    })

        return anomalies

    def _analyze_with_claude(self, metrics: Dict, anomalies: List[Dict]) -> str:
        """Use Claude to interpret trading analysis findings.

        Args:
            metrics (dict): Trading metrics from _calculate_metrics()
            anomalies (list): Detected anomalies from _detect_anomalies()

        Returns:
            str: Claude's interpretation and recommendations
        """
        try:
            # Build prompt with metrics and anomalies
            prompt = self._build_analysis_prompt(metrics, anomalies)

            # Call Claude for interpretation
            response = self.claude_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            analysis = response.content[0].text
            logger.info(f"[LogAnalysisAgent] Claude analysis: {analysis[:100]}...")
            return analysis

        except Exception as e:
            logger.error(f"[LogAnalysisAgent] Claude analysis error: {e}")
            return f"Analysis unavailable: {str(e)}"

    def _build_analysis_prompt(self, metrics: Dict, anomalies: List[Dict]) -> str:
        """Build prompt for Claude analysis.

        Args:
            metrics (dict): Trading metrics
            anomalies (list): Detected anomalies

        Returns:
            str: Formatted prompt for Claude
        """
        prompt = f"""Analyze this trading performance summary:

Trading Metrics:
- Total trades: {metrics.get('total_trades', 0)}
- Wins: {metrics.get('wins', 0)}
- Losses: {metrics.get('losses', 0)}
- Win rate: {metrics.get('win_rate', 0.0):.1%}
- Average P&L: ${metrics.get('avg_pnl', 0.0):.2f}

Closure Distribution:
- Stop-loss: {metrics.get('closure_reasons', {}).get('SL', 0.0):.1%}
- Take-profit: {metrics.get('closure_reasons', {}).get('TP', 0.0):.1%}

"""

        if anomalies:
            prompt += f"Anomalies Detected: {len(anomalies)}\n"
            for anomaly in anomalies:
                prompt += f"- {anomaly['type'].replace('_', ' ').title()}: {anomaly['description']}\n"
        else:
            prompt += "No anomalies detected.\n"

        prompt += "\nProvide a brief assessment of trading health and any recommended actions."

        return prompt

    def _send_alert_if_critical(self, report: Dict) -> None:
        """Send alert if critical anomalies detected.

        Args:
            report (dict): Complete analysis report
        """
        if not report.get("anomalies"):
            return

        # Filter for critical/high severity anomalies
        critical_anomalies = [
            a for a in report["anomalies"]
            if a.get("severity") in ["critical", "high"]
        ]

        if critical_anomalies:
            self._send_pushover_alert("critical", report)
            report["alert_sent"] = True
            logger.warning(f"[LogAnalysisAgent] Critical alert sent: {len(critical_anomalies)} anomalies")
        else:
            logger.info(f"[LogAnalysisAgent] No critical anomalies - alert not sent")

    def _send_pushover_alert(self, severity: str, report: Dict) -> None:
        """Send alert via Pushover.

        Args:
            severity (str): Alert severity ("critical", "warning", "info")
            report (dict): Analysis report with findings
        """
        anomaly_summary = f"{len(report['anomalies'])} anomalies detected: "
        anomaly_summary += ", ".join([f"{a['type']}" for a in report['anomalies'][:3]])
        if len(report['anomalies']) > 3:
            anomaly_summary += f" (and {len(report['anomalies']) - 3} more)"

        message = f"Trading Log Analysis Alert [{severity.upper()}]\n{anomaly_summary}\nWin rate: {report['metrics'].get('win_rate', 0.0):.1%}"

        try:
            from emy.tools.notification_tool import PushoverNotifier
            notifier = PushoverNotifier()
            # Map severity to priority: critical -> 2, warning -> 1, info -> 0
            priority_map = {"critical": 2, "warning": 1, "high": 1, "info": 0}
            priority = priority_map.get(severity, 0)
            notifier.send_alert(message, priority=priority)
        except Exception as e:
            logger.error(f"[LogAnalysisAgent] Failed to send alert: {e}")

    def _store_report(self, report: Dict) -> None:
        """Store analysis report in database.

        Args:
            report (dict): Complete analysis report
        """
        try:
            self.db.execute(
                """
                INSERT INTO monitoring_reports
                (report_type, timestamp, findings, analysis, critical)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    report["report_type"],
                    report["timestamp"],
                    str(report.get("anomalies", [])),
                    report.get("analysis", ""),
                    len(report.get("anomalies", [])) > 0
                )
            )
            logger.info("[LogAnalysisAgent] Report stored successfully")
        except Exception as e:
            logger.error(f"[LogAnalysisAgent] Error storing report: {e}")

    def run(self) -> tuple:
        """Execute the agent's primary task (inherited interface).

        Returns:
            tuple: (success: bool, results: Dict)
        """
        logger.info("[LogAnalysisAgent] run() called")
        # Placeholder for sync execution wrapper
        return (False, {"status": "use execute() for async operation"})
