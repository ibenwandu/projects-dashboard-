"""
Fisher Transform Daily Scanner - Reversal Strategy

Uses Fisher as TREND EXHAUSTION DETECTOR and REVERSAL SIGNAL GENERATOR.
Daily timeframe only. Generates opportunities when Fisher crosses Trigger from extreme zones.

CRITICAL: Fisher opportunities NEVER execute in FULL-AUTO mode.

Pairs: Set FISHER_PAIRS (comma-separated, e.g. EUR_USD,GBP_USD or EUR/USD,GBP/USD) to use env;
if unset or empty, uses hardcoded default list.
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Optional
from src.indicators.fisher_reversal_analyzer import analyze_pair_daily, check_fisher_warnings

logger = logging.getLogger(__name__)

# Default pairs when FISHER_PAIRS env is not set (slash format for display/OANDA compatibility)
DEFAULT_FISHER_PAIRS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD",
    "USD/CAD", "USD/CHF", "NZD/USD",
    "EUR/GBP", "EUR/JPY", "GBP/JPY"
]


def _get_fisher_pairs_from_env() -> List[str]:
    """Parse FISHER_PAIRS env var (comma-separated). Accepts EUR_USD or EUR/USD; normalizes to EUR/USD."""
    raw = os.getenv("FISHER_PAIRS", "").strip()
    if not raw:
        return []
    return [p.strip().replace("_", "/") for p in raw.split(",") if p.strip()]


class FisherDailyScanner:
    """
    Daily Fisher Transform Scanner - Reversal Strategy

    Scans configured pairs for Fisher reversal signals (crossover from extreme zones).
    Applies Fisher warnings to existing LLM opportunities.

    CRITICAL: Fisher opportunities NEVER execute in FULL-AUTO mode
    """

    def __init__(self, oanda_client, pairs: List[str] = None):
        self.oanda = oanda_client
        if pairs is not None and len(pairs) > 0:
            self.pairs = pairs
        else:
            env_pairs = _get_fisher_pairs_from_env()
            self.pairs = env_pairs if env_pairs else DEFAULT_FISHER_PAIRS
        self.logger = logging.getLogger('FisherDailyScanner')

    def scan(
        self,
        existing_opportunities: List[Dict] = None,
        market_state: Dict = None
    ) -> Dict:
        """
        Scan all configured pairs for Fisher reversal opportunities.

        Returns:
            {
                'opportunities': List[Dict],  # New Fisher reversal opportunities
                'fisher_analysis': Dict[str, Dict],  # Per-pair Fisher data (for warnings)
                'warnings_applied': int,  # Count of LLM opportunities with warnings
            }
        """
        self.logger.info(f"🔍 Starting Fisher scan for {len(self.pairs)} pairs (Daily, Reversal Strategy)")
        scan_time = datetime.utcnow()

        opportunities = []
        fisher_analysis = {}
        failed_pairs = []

        for pair in self.pairs:
            try:
                self.logger.info(f"Analyzing {pair} (Daily)...")
                result = analyze_pair_daily(self.oanda, pair)

                if not result:
                    failed_pairs.append((pair, "Analysis returned None"))
                    continue

                fa = result.get('fisher_analysis', {})
                fisher_analysis[pair] = fa

                opp = result.get('opportunity')
                if opp:
                    opp['scan_time'] = scan_time.isoformat()
                    opportunities.append(opp)
                    self.logger.info(
                        f"✅ {pair}: {opp['direction']} (in zone, persists until exit past ±1.5) "
                        f"confidence: {opp['confidence']:.0%}, "
                        f"MACD: {opp['confirmations']['macd_crossover']}, Div: {opp['confirmations']['divergence']}"
                    )
                else:
                    zone = fa.get('zone', 'NEUTRAL')
                    signal_type = fa.get('signal_type')
                    if signal_type == 'WARNING':
                        self.logger.info(
                            f"⚠️ {pair}: WARNING - {zone} | {fa.get('warning_message', 'Watching for crossover.')}"
                        )
                    else:
                        self.logger.info(
                            f"⏭️ {pair}: No reversal signal (zone: {zone})"
                        )

            except Exception as e:
                self.logger.error(f"❌ Failed to scan {pair}: {e}", exc_info=True)
                failed_pairs.append((pair, str(e)))

        self.logger.info(
            f"📊 Fisher scan complete: {len(opportunities)} opportunities, "
            f"{len(failed_pairs)} failures"
        )
        if failed_pairs:
            self.logger.warning(f"Failed pairs: {failed_pairs}")

        # Apply Fisher warnings to existing LLM opportunities
        warnings_applied = 0
        if market_state and fisher_analysis:
            llm_opps = market_state.get('opportunities', [])
            for opp in llm_opps:
                if opp.get('llm_sources') or opp.get('consensus_level'):  # LLM opportunity
                    check_fisher_warnings(opp, fisher_analysis)
                    if opp.get('fisher_warning'):
                        warnings_applied += 1

        return {
            'opportunities': opportunities,
            'fisher_analysis': fisher_analysis,
            'warnings_applied': warnings_applied,
        }

    def get_scan_schedule(self) -> str:
        return "Every hour during trading hours (Mon 01:00 UTC - Fri 21:30 UTC)"
