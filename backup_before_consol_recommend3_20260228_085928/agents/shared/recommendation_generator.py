"""
Recommendation generation for Forex Trading Expert Agent.

Generates specific, actionable recommendations with code locations and impact estimates.
"""

from typing import List, Dict, Any, Optional
from enum import Enum


class RecommendationType(Enum):
    """Type of recommendation."""
    CODE_CHANGE = "CODE_CHANGE"
    PARAMETER_ADJUSTMENT = "PARAMETER_ADJUSTMENT"
    CONFIGURATION = "CONFIGURATION"
    STRATEGY_CHANGE = "STRATEGY_CHANGE"
    MONITORING = "MONITORING"


class RecommendationSeverity(Enum):
    """Recommendation severity/priority."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RecommendationGenerator:
    """Generate recommendations from issues."""

    def generate(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate recommendations from issues.

        Returns:
            List of recommendations with code changes, parameters, and impact
        """
        recommendations = []

        for issue in issues:
            issue_id = issue.get("issue_id", "")
            severity = issue.get("severity")

            if "TRAILING_SL_STALL" in issue_id:
                recommendations.append(self._recommend_trailing_sl_stall_fix(issue))

            elif "TRAILING_SL_ERRATIC" in issue_id:
                recommendations.append(self._recommend_trailing_sl_erratic_fix(issue))

            elif "SL_VALIDITY" in issue_id:
                recommendations.append(self._recommend_sl_validity_fix(issue))

            elif "CONSISTENCY" in issue_id:
                recommendations.append(self._recommend_consistency_fix(issue))

            elif "LOW_WIN_RATE" in issue_id:
                recommendations.append(self._recommend_win_rate_improvement(issue))

            elif "HIGH_DRAWDOWN" in issue_id:
                recommendations.append(self._recommend_drawdown_reduction(issue))

            elif "FREQUENT_SL_HITS" in issue_id:
                recommendations.append(self._recommend_sl_adjustment(issue))

            elif "POOR_RISK_REWARD" in issue_id:
                recommendations.append(self._recommend_tp_adjustment(issue))

        return recommendations

    def _recommend_trailing_sl_stall_fix(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend fix for stalled trailing SL."""
        return {
            "recommendation_id": f"REC_{issue.get('issue_id')}",
            "issue_id": issue.get("issue_id"),
            "priority": RecommendationType.CODE_CHANGE,
            "severity": RecommendationSeverity.CRITICAL,
            "title": "Fix Trailing SL Stall Detection and Logging",
            "description": "Trailing stop loss is not updating for extended periods. Add logging and error handling to detect and fix the issue.",
            "affected_file": "Scalp-Engine/auto_trader_core.py",
            "affected_methods": ["_update_trailing_sl", "_check_atr_trailing_conversion"],
            "code_changes": [
                {
                    "location": "_update_trailing_sl method",
                    "change": "Add try-except around ATR fetch with detailed logging",
                    "before": "atr = self.market_bridge.get_atr(pair, timeframe)",
                    "after": """try:
    atr = self.market_bridge.get_atr(pair, timeframe)
    logger.debug(f'ATR fetch successful for {trade_id}: {atr}')
except Exception as e:
    logger.error(f'Failed to fetch ATR for {trade_id}: {e}', exc_info=True)
    return  # Skip update on error"""
                },
                {
                    "location": "_update_trailing_sl method",
                    "change": "Add validation for SL movement direction",
                    "code": """# Never move SL backwards
if is_long and new_sl <= old_sl:
    logger.warning(f'SL would move backwards for LONG {trade_id}: {old_sl} -> {new_sl}')
    new_sl = old_sl
if is_short and new_sl >= old_sl:
    logger.warning(f'SL would move backwards for SHORT {trade_id}: {old_sl} -> {new_sl}')
    new_sl = old_sl"""
                },
                {
                    "location": "_update_trailing_sl method",
                    "change": "Add timestamp logging for every update",
                    "code": "logger.info(f'SL updated for {trade_id} at {datetime.utcnow().isoformat()}: {old_sl} -> {new_sl}')"
                }
            ],
            "testing": [
                "Verify SL updates every 30 seconds for ATR_TRAILING trades",
                "Verify SL never moves against profit direction",
                "Test with different volatility regimes",
                "Monitor logs for any ATR fetch errors"
            ],
            "estimated_impact": {
                "win_rate_improvement_percent": 0,
                "drawdown_reduction_percent": 5,
                "consistency_improvement_percent": 10
            },
            "implementation_effort": "MEDIUM",
            "risk_level": "LOW"
        }

    def _recommend_trailing_sl_erratic_fix(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend fix for erratic trailing SL jumps."""
        return {
            "recommendation_id": f"REC_{issue.get('issue_id')}",
            "issue_id": issue.get("issue_id"),
            "priority": RecommendationType.CODE_CHANGE,
            "severity": RecommendationSeverity.HIGH,
            "title": "Add Volatility Regime Caching and Smoothing",
            "description": "Trailing SL is jumping erratically, suggesting race condition in volatility regime detection. Add caching and confirmation logic.",
            "affected_file": "Scalp-Engine/auto_trader_core.py",
            "affected_methods": ["_check_atr_trailing_conversion", "_detect_volatility_regime"],
            "code_changes": [
                {
                    "location": "_check_atr_trailing_conversion method",
                    "change": "Cache volatility regime for minimum 5-minute window",
                    "code": """# Cache regime to prevent rapid oscillation
last_check_time = getattr(position, 'last_regime_check_time', None)
current_time = datetime.utcnow()

if last_check_time and (current_time - last_check_time).total_seconds() < 300:
    # Use cached regime (5 minute window)
    regime = getattr(position, 'cached_regime', 'NORMAL')
else:
    # Fetch new regime
    regime = self._detect_volatility_regime(pair)
    position.last_regime_check_time = current_time
    position.cached_regime = regime"""
                },
                {
                    "location": "_check_atr_trailing_conversion method",
                    "change": "Only update regime if change persists for 2+ checks",
                    "code": """if regime != position.cached_regime:
    consecutive_changes = getattr(position, 'regime_change_count', 0) + 1
    if consecutive_changes >= 2:
        logger.info(f'Regime change confirmed for {trade_id}: {position.cached_regime} -> {regime}')
        position.cached_regime = regime
        position.regime_change_count = 0
    else:
        position.regime_change_count = consecutive_changes
        logger.debug(f'Regime change pending ({consecutive_changes}/2 confirmations)')"""
                },
                {
                    "location": "_update_trailing_sl method",
                    "change": "Add maximum SL change limit per update",
                    "code": """# Limit SL change to prevent erratic jumps
max_change_pips = 50
current_change_pips = abs(new_sl - old_sl) * 10000  # Approximate pips

if current_change_pips > max_change_pips:
    logger.warning(f'SL change limited for {trade_id}: {current_change_pips:.0f} pips -> {max_change_pips} pips')
    # Move SL in profit direction only by max amount
    direction = 1 if is_long else -1
    new_sl = old_sl + (direction * max_change_pips / 10000)"""
                }
            ],
            "testing": [
                "Verify SL updates smoothly without jumping",
                "Verify regime changes only after 2 confirmations",
                "Test with rapid volatility changes",
                "Monitor SL change rates"
            ],
            "estimated_impact": {
                "win_rate_improvement_percent": 2,
                "drawdown_reduction_percent": 8,
                "consistency_improvement_percent": 5
            },
            "implementation_effort": "MEDIUM",
            "risk_level": "LOW"
        }

    def _recommend_sl_validity_fix(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend fix for invalid SL placement."""
        return {
            "recommendation_id": f"REC_{issue.get('issue_id')}",
            "issue_id": issue.get("issue_id"),
            "priority": RecommendationType.CODE_CHANGE,
            "severity": RecommendationSeverity.CRITICAL,
            "title": "Add SL Validation Before Trade Execution",
            "description": "Invalid stop loss values detected. Add validation at entry time to prevent trades with wrong SL direction.",
            "affected_file": "Scalp-Engine/auto_trader_core.py",
            "affected_methods": ["_execute_trade", "validate_trade_parameters"],
            "code_changes": [
                {
                    "location": "validate_trade_parameters method (new or enhanced)",
                    "change": "Add SL direction validation",
                    "code": """def validate_trade_parameters(pair, direction, entry_price, sl_price):
    '''Validate trade parameters before execution'''

    # Check SL direction
    if direction == 'LONG':
        if sl_price >= entry_price:
            raise ValueError(f'LONG trade SL ({sl_price}) must be below entry ({entry_price})')
    elif direction == 'SHORT':
        if sl_price <= entry_price:
            raise ValueError(f'SHORT trade SL ({sl_price}) must be above entry ({entry_price})')

    return True"""
                },
                {
                    "location": "_execute_trade method",
                    "change": "Call validation before order placement",
                    "code": """try:
    validate_trade_parameters(pair, direction, entry_price, sl_price)
    logger.info(f'Trade parameters valid for {pair} {direction}')
except ValueError as e:
    logger.error(f'Trade parameter validation failed: {e}')
    return False  # Don't execute trade"""
                }
            ],
            "testing": [
                "Test LONG trade with SL below entry (should pass)",
                "Test LONG trade with SL above entry (should fail)",
                "Test SHORT trade with SL above entry (should pass)",
                "Test SHORT trade with SL below entry (should fail)"
            ],
            "estimated_impact": {
                "win_rate_improvement_percent": 0,
                "drawdown_reduction_percent": 0,
                "consistency_improvement_percent": 100
            },
            "implementation_effort": "LOW",
            "risk_level": "CRITICAL"
        }

    def _recommend_consistency_fix(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend fix for data consistency issues."""
        return {
            "recommendation_id": f"REC_{issue.get('issue_id')}",
            "issue_id": issue.get("issue_id"),
            "priority": RecommendationType.MONITORING,
            "severity": RecommendationSeverity.HIGH,
            "title": "Enhance Logging for UI/Scalp-Engine/OANDA Consistency",
            "description": "Data inconsistencies between systems detected. Add comprehensive logging to track sync status.",
            "affected_file": "Scalp-Engine/auto_trader_core.py",
            "affected_methods": ["_log_trade_entry", "_log_trade_exit", "sync_with_oanda"],
            "code_changes": [
                {
                    "location": "_log_trade_entry method",
                    "change": "Log trade entry with timestamp and source",
                    "code": """logger.info(f'TRADE_ENTRY | {pair} {direction} @ {entry_price} SL: {sl_price} | Source: {source}')"""
                },
                {
                    "location": "sync_with_oanda method",
                    "change": "Log every OANDA sync attempt",
                    "code": """logger.info(f'OANDA_SYNC | Comparing {len(se_trades)} SE trades with {len(oanda_trades)} OANDA trades')
for trade in oanda_trades:
    logger.debug(f'OANDA_TRADE | {trade[\"instrument\"]} {trade[\"initialUnits\"]} | {trade[\"openTime\"]}')"""
                }
            ],
            "testing": [
                "Monitor logs for entry/exit consistency",
                "Compare timestamps between UI, SE, and OANDA",
                "Verify OANDA positions appear in SE logs within 5 minutes"
            ],
            "estimated_impact": {
                "win_rate_improvement_percent": 3,
                "drawdown_reduction_percent": 0,
                "consistency_improvement_percent": 50
            },
            "implementation_effort": "LOW",
            "risk_level": "LOW"
        }

    def _recommend_win_rate_improvement(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend improvements for low win rate."""
        return {
            "recommendation_id": f"REC_{issue.get('issue_id')}",
            "issue_id": issue.get("issue_id"),
            "priority": RecommendationType.PARAMETER_ADJUSTMENT,
            "severity": RecommendationSeverity.CRITICAL,
            "title": "Improve Entry Signal Quality with Filtering",
            "description": "Win rate below optimal threshold. Consider adding entry filters or signal confirmation.",
            "parameter_changes": [
                {
                    "parameter": "FISHER_SIGNAL_THRESHOLD",
                    "current_value": "0.8",
                    "recommended_value": "0.85 or higher",
                    "rationale": "Higher threshold accepts only stronger signals, should improve win rate"
                },
                {
                    "parameter": "MIN_VOLUME_FOR_ENTRY",
                    "current_value": "not_set",
                    "recommended_value": "1.5x average hourly volume",
                    "rationale": "Filter out low-volume entries which have higher failure rates"
                },
                {
                    "parameter": "REQUIRE_DMI_CONFIRMATION",
                    "current_value": "false",
                    "recommended_value": "true",
                    "rationale": "Require DMI alignment with Fisher signal for stronger entries"
                }
            ],
            "strategy_suggestions": [
                "Add volume spike filter before entry",
                "Require multiple indicators to align (Fisher + DMI + EMA)",
                "Add time-of-day filter (avoid entries during low-liquidity hours)",
                "Consider waiting for pullback to EMA before entry (instead of breakout)"
            ],
            "estimated_impact": {
                "win_rate_improvement_percent": 8,
                "drawdown_reduction_percent": 5,
                "trade_frequency_change_percent": -30
            },
            "implementation_effort": "MEDIUM",
            "risk_level": "MEDIUM"
        }

    def _recommend_drawdown_reduction(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend improvements for high drawdown."""
        return {
            "recommendation_id": f"REC_{issue.get('issue_id')}",
            "issue_id": issue.get("issue_id"),
            "priority": RecommendationType.PARAMETER_ADJUSTMENT,
            "severity": RecommendationSeverity.HIGH,
            "title": "Reduce Drawdown Through Position Sizing or SL Adjustment",
            "description": "Maximum drawdown exceeds acceptable levels. Adjust position sizing or SL distance.",
            "parameter_changes": [
                {
                    "parameter": "POSITION_SIZE_PERCENT",
                    "current_value": "2.0%",
                    "recommended_value": "1.5%",
                    "rationale": "Smaller positions reduce impact of losing trades"
                },
                {
                    "parameter": "ATR_TRAILING_MULTIPLIER",
                    "current_value": "1.5x (normal) / 3.0x (high vol)",
                    "recommended_value": "2.0x (normal) / 4.0x (high vol)",
                    "rationale": "Wider SL stops gives trades more room to breathe"
                }
            ],
            "estimated_impact": {
                "win_rate_improvement_percent": 0,
                "drawdown_reduction_percent": 25,
                "profit_reduction_percent": 15
            },
            "implementation_effort": "LOW",
            "risk_level": "LOW"
        }

    def _recommend_sl_adjustment(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend SL adjustment for frequent hits."""
        return {
            "recommendation_id": f"REC_{issue.get('issue_id')}",
            "issue_id": issue.get("issue_id"),
            "priority": RecommendationType.PARAMETER_ADJUSTMENT,
            "severity": RecommendationSeverity.MEDIUM,
            "title": "Widen Stop Loss Distance",
            "description": "Stop loss being hit too frequently. Consider wider SL to reduce whipsaws.",
            "parameter_changes": [
                {
                    "parameter": "SL_DISTANCE_PIPS",
                    "current_value": "35 pips average",
                    "recommended_value": "50 pips",
                    "rationale": "Wider SL reduces hit rate from whipsaws without significantly affecting risk"
                }
            ],
            "estimated_impact": {
                "win_rate_improvement_percent": 5,
                "drawdown_reduction_percent": 0,
                "risk_increase_percent": 15
            },
            "implementation_effort": "LOW",
            "risk_level": "LOW"
        }

    def _recommend_tp_adjustment(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend take profit adjustment for poor risk/reward."""
        return {
            "recommendation_id": f"REC_{issue.get('issue_id')}",
            "issue_id": issue.get("issue_id"),
            "priority": RecommendationType.PARAMETER_ADJUSTMENT,
            "severity": RecommendationSeverity.MEDIUM,
            "title": "Increase Take Profit Target Distance",
            "description": "Risk/reward ratio below optimal. Increase TP distance relative to SL.",
            "parameter_changes": [
                {
                    "parameter": "TAKE_PROFIT_DISTANCE_PIPS",
                    "current_value": "current distance",
                    "recommended_value": "2x current distance",
                    "rationale": "Larger profit targets improve risk/reward ratio"
                }
            ],
            "estimated_impact": {
                "win_rate_improvement_percent": 0,
                "average_win_size_improvement_percent": 50,
                "profit_factor_improvement_percent": 30
            },
            "implementation_effort": "LOW",
            "risk_level": "LOW"
        }
