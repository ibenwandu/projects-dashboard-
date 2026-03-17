"""
ProfitabilityAgent - analyzes profitability patterns and generates improvement recommendations.

This agent performs multi-dimensional analysis of trading performance by currency pair,
trading hour, market regime, and signal strength. It uses Claude Sonnet to synthesize
findings into specific, actionable improvement recommendations.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz
from anthropic import Anthropic
from emy.agents.base_agent import EMySubAgent
from emy.core.database import EMyDatabase

logger = logging.getLogger('ProfitabilityAgent')


class ProfitabilityAgent(EMySubAgent):
    """Analyzes profitability patterns and generates improvement recommendations.

    Performs multi-dimensional analysis of trading performance by pair, hour,
    regime, and signal strength. Uses Claude Sonnet to synthesize findings
    into specific, actionable recommendations.
    """

    def __init__(self):
        """Initialize ProfitabilityAgent."""
        # Initialize parent with agent name and model
        super().__init__(
            agent_name='ProfitabilityAgent',
            model='claude-3-5-sonnet-20241022'
        )

        # Add name and description attributes for compatibility
        self.name = "ProfitabilityAgent"
        self.description = "Analyzes profitability patterns and generates improvement recommendations"

        # Initialize database for querying trades and storing reports
        self.db = EMyDatabase()

        # Initialize Claude client for analysis interpretation
        self.claude_client = Anthropic()

        logger.info(f"[ProfitabilityAgent] Initialized: {self.name}")

    def execute(self, instruction: str = None, **kwargs):
        """Execute profitability analysis.

        Args:
            instruction (str, optional): User instruction (not used in standard analysis)
            **kwargs: Additional parameters

        Returns:
            dict: Profitability analysis report with metrics and recommendations
        """
        logger.info(f"[ProfitabilityAgent] execute() called")
        return self.analyze()

    def analyze(self) -> Dict:
        """Analyze profitability and generate recommendations.

        Returns:
            dict: Complete profitability analysis report with structure:
                {
                    "report_type": "profitability",
                    "timestamp": ISO8601,
                    "period": "Week of 2026-03-09 to 2026-03-15",
                    "profitability_analysis": {
                        "by_pair": {...},
                        "by_hour": {...},
                        "by_regime": {...},
                        "by_signal_strength": {...}
                    },
                    "llm_analysis": {...},
                    "recommendations": [...],
                    "alert_sent": bool,
                    "error": None or str
                }
        """
        # Initialize report structure
        report = {
            "report_type": "profitability",
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "period": self._get_period_string(),
            "profitability_analysis": {},
            "llm_analysis": {},
            "recommendations": [],
            "alert_sent": False,
            "error": None
        }

        try:
            # Step 1: Query trades from last 7 days
            trades = self._query_trades_last_week()
            logger.info(f"[ProfitabilityAgent] Queried {len(trades)} trades")

            if not trades:
                logger.info("[ProfitabilityAgent] No trades in period")
                report["recommendations"] = [
                    {
                        "priority": 1,
                        "title": "Increase trading activity",
                        "rationale": "No trades in analysis period",
                        "expected_impact": "Generate sufficient data for profitability analysis"
                    }
                ]
                return report

            # Step 2: Analyze by multiple dimensions
            report["profitability_analysis"]["by_pair"] = self._analyze_by_pair(trades)
            logger.info(f"[ProfitabilityAgent] Analyzed {len(report['profitability_analysis']['by_pair'])} pairs")

            report["profitability_analysis"]["by_hour"] = self._analyze_by_hour(trades)
            logger.info("[ProfitabilityAgent] Hour-based analysis complete")

            report["profitability_analysis"]["by_regime"] = self._analyze_by_regime(trades)
            logger.info("[ProfitabilityAgent] Regime-based analysis complete")

            report["profitability_analysis"]["by_signal_strength"] = self._analyze_by_signal_strength(trades)
            logger.info("[ProfitabilityAgent] Signal strength analysis complete")

            # Step 3: Analyze LLM performance
            report["llm_analysis"] = self._analyze_llm_weights_and_accuracy()
            logger.info("[ProfitabilityAgent] LLM analysis complete")

            # Step 4: Generate recommendations
            report["recommendations"] = self._generate_recommendations(report["profitability_analysis"])
            logger.info(f"[ProfitabilityAgent] Generated {len(report['recommendations'])} recommendations")

            # Step 5: Store report in database
            self._store_report(report)
            logger.info("[ProfitabilityAgent] Report stored in database")

            logger.info(f"[ProfitabilityAgent] Analysis complete: {len(report['recommendations'])} recommendations")
            return report

        except Exception as e:
            logger.error(f"[ProfitabilityAgent] Analysis error: {e}", exc_info=True)
            report["error"] = str(e)
            return report

    def _get_period_string(self) -> str:
        """Get human-readable period string for last 7 days.

        Returns:
            str: Period in format "Week of 2026-03-09 to 2026-03-15"
        """
        now = datetime.now(pytz.UTC)
        start = now - timedelta(days=7)
        return f"Week of {start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}"

    def _query_trades_last_week(self) -> List[Dict]:
        """Query completed trades from last 7 days from database.

        This is a placeholder that would query the database for closed trades
        with their outcomes, P&L, pair, hour, regime, and signal strength.

        Returns:
            list: List of trade dictionaries with keys:
                - pair (str): Currency pair (e.g., "EUR/USD")
                - outcome (str): "TP", "SL", "WIN", or "LOSS"
                - pnl (float): Realized P&L in account currency
                - hour (int): Trading hour (0-23)
                - regime (str): Market regime ("TRENDING", "RANGING", "HIGH_VOL")
                - signal_strength (float): Signal strength (0.0-1.0)
        """
        logger.info("[ProfitabilityAgent] Querying trades from last 7 days")

        try:
            # Placeholder: would query specific trades table
            trades = self.db.query_all(
                """
                SELECT pair, outcome, pnl, hour, regime, signal_strength
                FROM trades
                WHERE timestamp >= datetime('now', '-7 days')
                AND outcome IN ('TP', 'SL', 'WIN', 'LOSS')
                ORDER BY timestamp DESC
                """
            )
            return trades if trades else []
        except Exception as e:
            logger.warning(f"[ProfitabilityAgent] Could not query trades: {e}")
            return []

    def _analyze_by_pair(self, trades: List[Dict]) -> Dict:
        """Analyze profitability by currency pair.

        Args:
            trades (list): List of trade dictionaries with 'pair', 'outcome', 'pnl' keys

        Returns:
            dict: Profitability by pair with structure:
                {
                    "EUR/USD": {
                        "trades": int,
                        "win_rate": float,
                        "avg_pnl": float
                    },
                    ...
                }
        """
        pairs = {}

        # Group trades by pair
        for trade in trades:
            pair = trade.get("pair", "UNKNOWN")
            outcome = trade.get("outcome", "UNKNOWN")
            pnl = trade.get("pnl", 0.0)

            if pair not in pairs:
                pairs[pair] = {"trades": 0, "wins": 0, "total_pnl": 0.0}

            pairs[pair]["trades"] += 1
            pairs[pair]["total_pnl"] += pnl

            # Count wins (TP or WIN outcomes)
            if outcome in ["TP", "WIN"]:
                pairs[pair]["wins"] += 1

        # Calculate metrics for each pair
        result = {}
        for pair, data in pairs.items():
            result[pair] = {
                "trades": data["trades"],
                "win_rate": data["wins"] / data["trades"] if data["trades"] > 0 else 0.0,
                "avg_pnl": data["total_pnl"] / data["trades"] if data["trades"] > 0 else 0.0
            }

        logger.info(f"[ProfitabilityAgent] Analyzed {len(result)} pairs")
        return result

    def _analyze_by_hour(self, trades: List[Dict]) -> Dict:
        """Analyze profitability by trading hour.

        Groups trades into 4-hour windows (08:00-12:00, 12:00-16:00, 16:00-20:00)
        and calculates win rate for each period.

        Args:
            trades (list): List of trade dictionaries with 'hour', 'outcome', 'pnl' keys

        Returns:
            dict: Profitability by hour window with structure:
                {
                    "08:00-12:00": {"trades": int, "win_rate": float},
                    "12:00-16:00": {"trades": int, "win_rate": float},
                    "16:00-20:00": {"trades": int, "win_rate": float}
                }
        """
        time_windows = {
            "08:00-12:00": [],
            "12:00-16:00": [],
            "16:00-20:00": []
        }

        # Categorize trades by hour
        for trade in trades:
            hour = trade.get("hour", 0)
            outcome = trade.get("outcome", "UNKNOWN")

            if 8 <= hour < 12:
                time_windows["08:00-12:00"].append(trade)
            elif 12 <= hour < 16:
                time_windows["12:00-16:00"].append(trade)
            elif 16 <= hour < 20:
                time_windows["16:00-20:00"].append(trade)

        # Calculate metrics for each window
        result = {}
        for window, window_trades in time_windows.items():
            if window_trades:
                wins = sum(1 for t in window_trades if t.get("outcome") in ["TP", "WIN"])
                result[window] = {
                    "trades": len(window_trades),
                    "win_rate": wins / len(window_trades) if len(window_trades) > 0 else 0.0
                }
            else:
                result[window] = {
                    "trades": 0,
                    "win_rate": 0.0
                }

        logger.info("[ProfitabilityAgent] Hour-based analysis complete")
        return result

    def _analyze_by_regime(self, trades: List[Dict]) -> Dict:
        """Analyze profitability by market regime.

        Separates performance in TRENDING, RANGING, and HIGH_VOL market conditions.

        Args:
            trades (list): List of trade dictionaries with 'regime', 'outcome' keys

        Returns:
            dict: Profitability by regime with structure:
                {
                    "TRENDING": {"trades": int, "win_rate": float},
                    "RANGING": {"trades": int, "win_rate": float},
                    "HIGH_VOL": {"trades": int, "win_rate": float}
                }
        """
        regimes = {
            "TRENDING": [],
            "RANGING": [],
            "HIGH_VOL": []
        }

        # Categorize trades by regime
        for trade in trades:
            regime = trade.get("regime", "UNKNOWN")
            if regime in regimes:
                regimes[regime].append(trade)

        # Calculate metrics for each regime
        result = {}
        for regime, regime_trades in regimes.items():
            if regime_trades:
                wins = sum(1 for t in regime_trades if t.get("outcome") in ["TP", "WIN"])
                result[regime] = {
                    "trades": len(regime_trades),
                    "win_rate": wins / len(regime_trades) if len(regime_trades) > 0 else 0.0
                }
            else:
                result[regime] = {
                    "trades": 0,
                    "win_rate": 0.0
                }

        logger.info("[ProfitabilityAgent] Regime-based analysis complete")
        return result

    def _analyze_by_signal_strength(self, trades: List[Dict]) -> Dict:
        """Analyze profitability by signal strength.

        Categorizes trades into low (<0.4), medium (0.4-0.7), and high (>0.7)
        signal strength groups.

        Args:
            trades (list): List of trade dictionaries with 'signal_strength', 'outcome' keys

        Returns:
            dict: Profitability by signal strength with structure:
                {
                    "low": {"trades": int, "win_rate": float},
                    "medium": {"trades": int, "win_rate": float},
                    "high": {"trades": int, "win_rate": float}
                }
        """
        strengths = {
            "low": [],
            "medium": [],
            "high": []
        }

        # Categorize trades by signal strength
        for trade in trades:
            strength = trade.get("signal_strength", 0.0)

            if strength < 0.4:
                strengths["low"].append(trade)
            elif strength <= 0.7:
                strengths["medium"].append(trade)
            else:
                strengths["high"].append(trade)

        # Calculate metrics for each strength category
        result = {}
        for category, category_trades in strengths.items():
            if category_trades:
                wins = sum(1 for t in category_trades if t.get("outcome") in ["TP", "WIN"])
                result[category] = {
                    "trades": len(category_trades),
                    "win_rate": wins / len(category_trades) if len(category_trades) > 0 else 0.0
                }
            else:
                result[category] = {
                    "trades": 0,
                    "win_rate": 0.0
                }

        logger.info("[ProfitabilityAgent] Signal strength analysis complete")
        return result

    def _analyze_llm_weights_and_accuracy(self) -> Dict:
        """Analyze LLM performance metrics.

        Returns default weights and accuracy percentages for each LLM.

        Returns:
            dict: LLM performance with structure:
                {
                    "claude": {"weight": float, "accuracy": float},
                    "chatgpt": {"weight": float, "accuracy": float},
                    "gemini": {"weight": float, "accuracy": float}
                }
        """
        # Placeholder: would query actual LLM performance data
        return {
            "claude": {"weight": 0.45, "accuracy": 0.0},
            "chatgpt": {"weight": 0.35, "accuracy": 0.0},
            "gemini": {"weight": 0.20, "accuracy": 0.0}
        }

    def _generate_recommendations(self, analysis: Dict) -> List[Dict]:
        """Generate improvement recommendations via Claude Sonnet.

        Args:
            analysis (dict): Profitability analysis from _analyze_* methods

        Returns:
            list: List of recommendation dictionaries with structure:
                [
                    {
                        "priority": int (1-5),
                        "title": str,
                        "rationale": str,
                        "expected_impact": str
                    },
                    ...
                ]
        """
        try:
            # Build prompt with analysis data
            prompt = self._build_recommendations_prompt(analysis)

            # Call Claude Sonnet for synthesis
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse recommendations from response
            recommendations = self._parse_recommendations(response.content[0].text)
            logger.info(f"[ProfitabilityAgent] Generated {len(recommendations)} recommendations")
            return recommendations

        except Exception as e:
            logger.error(f"[ProfitabilityAgent] Claude error: {e}")
            return []

    def _build_recommendations_prompt(self, analysis: Dict) -> str:
        """Build prompt for Claude recommendation generation.

        Args:
            analysis (dict): Profitability analysis data

        Returns:
            str: Formatted prompt for Claude
        """
        by_pair = analysis.get("by_pair", {})
        by_regime = analysis.get("by_regime", {})
        by_hour = analysis.get("by_hour", {})
        by_strength = analysis.get("by_signal_strength", {})

        # Find best and worst performing pairs
        pair_wins = sorted(
            [(pair, metrics.get("win_rate", 0)) for pair, metrics in by_pair.items()],
            key=lambda x: x[1],
            reverse=True
        )

        # Find best and worst regimes
        regime_wins = sorted(
            [(regime, metrics.get("win_rate", 0)) for regime, metrics in by_regime.items()],
            key=lambda x: x[1],
            reverse=True
        )

        prompt = """Analyze this trading profitability data and generate 3-5 specific, actionable improvement recommendations.

By Pair Performance:
"""
        for pair, metrics in by_pair.items():
            prompt += f"- {pair}: {metrics.get('trades', 0)} trades, {metrics.get('win_rate', 0):.1%} win rate, {metrics.get('avg_pnl', 0):.2f} avg P&L\n"

        prompt += "\nBy Market Regime:\n"
        for regime, metrics in by_regime.items():
            prompt += f"- {regime}: {metrics.get('trades', 0)} trades, {metrics.get('win_rate', 0):.1%} win rate\n"

        prompt += "\nBy Signal Strength:\n"
        for strength, metrics in by_strength.items():
            prompt += f"- {strength}: {metrics.get('trades', 0)} trades, {metrics.get('win_rate', 0):.1%} win rate\n"

        prompt += """
For each recommendation, format as:
PRIORITY: [1-5]
TITLE: [Short descriptive title]
RATIONALE: [Why this matters based on the data]
EXPECTED_IMPACT: [Quantified improvement]

Focus on specific, measurable improvements. Prioritize based on win rate differentials and P&L impact."""

        return prompt

    def _parse_recommendations(self, text: str) -> List[Dict]:
        """Parse Claude's response into structured recommendations.

        Args:
            text (str): Claude's raw response text

        Returns:
            list: List of parsed recommendation dictionaries
        """
        recommendations = []
        lines = text.split("\n")

        current_rec = {}
        priority_counter = 0

        for line in lines:
            line = line.strip()

            if line.startswith("PRIORITY:"):
                if current_rec:
                    # Save previous recommendation
                    if "priority" in current_rec:
                        recommendations.append(current_rec)
                # Start new recommendation
                try:
                    priority_str = line.replace("PRIORITY:", "").strip()
                    # Extract first digit
                    priority = int(''.join(filter(str.isdigit, priority_str.split()[0]))) if priority_str else 0
                    priority = max(1, min(5, priority))  # Clamp 1-5
                except (ValueError, IndexError):
                    priority_counter += 1
                    priority = priority_counter

                current_rec = {"priority": priority}

            elif line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
                current_rec["title"] = title if title else "Improvement Recommendation"

            elif line.startswith("RATIONALE:"):
                rationale = line.replace("RATIONALE:", "").strip()
                current_rec["rationale"] = rationale if rationale else ""

            elif line.startswith("EXPECTED_IMPACT:"):
                impact = line.replace("EXPECTED_IMPACT:", "").strip()
                current_rec["expected_impact"] = impact if impact else ""

        # Save last recommendation
        if current_rec and "priority" in current_rec:
            # Ensure all required fields
            current_rec.setdefault("title", "Improvement Recommendation")
            current_rec.setdefault("rationale", "")
            current_rec.setdefault("expected_impact", "")
            recommendations.append(current_rec)

        # If no structured recommendations found, create fallback from text
        if not recommendations and text:
            # Try to create at least one recommendation from available text
            recommendations.append({
                "priority": 1,
                "title": "Optimize trading strategy based on analysis",
                "rationale": text[:200] if len(text) > 0 else "Review profitability data",
                "expected_impact": "Improved win rate and P&L"
            })

        return recommendations[:5]  # Return max 5 recommendations

    def _store_report(self, report: Dict) -> None:
        """Store profitability analysis report in database.

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
                    str(report.get("profitability_analysis", {})),
                    str(report.get("recommendations", [])),
                    False
                )
            )
            logger.info("[ProfitabilityAgent] Report stored successfully")
        except Exception as e:
            logger.error(f"[ProfitabilityAgent] Error storing report: {e}")

    def run(self) -> tuple:
        """Execute the agent's primary task (inherited interface).

        Returns:
            tuple: (success: bool, results: Dict)
        """
        logger.info("[ProfitabilityAgent] run() called")
        # Placeholder for sync execution wrapper
        return (False, {"status": "use execute() for async operation"})
