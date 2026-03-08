#!/usr/bin/env python3
"""
Run Fisher Transform scan immediately (manual trigger).
Uses REVERSAL strategy: crossover from extreme zones only.
Publishes to market-state-api via HTTP (when MARKET_STATE_API_URL is set).

Usage:
  From Scalp-Engine directory:
    python run_fisher_scan.py

  On Render Web Shell (Blueprint: shell starts at Trade-Alerts repo root):
    cd Scalp-Engine && python run_fisher_scan.py
"""
import json
import os
import sys
import logging
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

# Load .env so manual run works with env vars from project root
try:
    from dotenv import load_dotenv
    load_dotenv(_script_dir / ".env")
    load_dotenv()  # also current dir / parent
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("run_fisher_scan")


def main():
    logger.info("=" * 60)
    logger.info("Fisher Transform – immediate scan (Reversal Strategy)")
    logger.info("=" * 60)

    access_token = os.getenv("OANDA_ACCESS_TOKEN")
    account_id = os.getenv("OANDA_ACCOUNT_ID")
    environment = os.getenv("OANDA_ENV", "practice")

    if not access_token or not account_id:
        logger.error("OANDA_ACCESS_TOKEN and OANDA_ACCOUNT_ID must be set")
        sys.exit(1)

    try:
        from oandapyV20 import API
        from src.scanners.fisher_daily_scanner import FisherDailyScanner
        from src.integration.fisher_market_bridge import FisherMarketBridge, post_fisher_to_api
    except ImportError as e:
        logger.error("Import failed (run from Scalp-Engine directory): %s", e)
        sys.exit(1)

    api = API(access_token=access_token, environment=environment)
    scanner = FisherDailyScanner(api)

    market_state_path = os.getenv("MARKET_STATE_FILE_PATH", "/var/data/market_state.json")
    logger.info("Market state path: %s", market_state_path)
    bridge = FisherMarketBridge(market_state_path=market_state_path)

    # Load existing market state for warning application to LLM opportunities
    market_state = None
    try:
        with open(market_state_path, 'r') as f:
            market_state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    logger.info("Running Fisher scan for %s pairs (Daily, Reversal)...", len(scanner.pairs))
    result = scanner.scan(market_state=market_state)

    opportunities = result.get('opportunities', [])
    fisher_analysis = result.get('fisher_analysis', {})
    warnings_applied = result.get('warnings_applied', 0)

    if opportunities:
        for opp in opportunities:
            conf = opp.get('confirmations', {})
            logger.info(
                "  - %s %s @ %s (conf: %.0f%%, MACD: %s, Div: %s)",
                opp.get("pair"), opp.get("direction"), opp.get("entry"),
                opp.get("confidence", 0) * 100,
                conf.get("macd_crossover", False),
                conf.get("divergence", False),
            )
    if warnings_applied:
        logger.info("Applied Fisher warnings to %s LLM opportunities", warnings_applied)

    posted = post_fisher_to_api(opportunities, fisher_analysis=fisher_analysis)
    if posted:
        logger.info("Fisher opportunities and analysis sent to market-state-api.")
    else:
        bridge.add_fisher_opportunities(opportunities, fisher_analysis=fisher_analysis)
        if opportunities:
            logger.info("Added %s Fisher opportunities via disk bridge.", len(opportunities))
        else:
            logger.info("No Fisher reversal opportunities; fisher list cleared/updated.")
        try:
            with open(market_state_path, 'r') as f:
                saved_state = json.load(f)
            fisher_count = len(saved_state.get('fisher_opportunities', []))
            fisher_updated = saved_state.get('fisher_last_updated', 'N/A')
            logger.info("VERIFICATION: File contains %s Fisher opportunities (last updated: %s)", fisher_count, fisher_updated)
        except Exception as e:
            logger.warning("Could not verify disk write: %s", e)

    logger.info("=" * 60)
    logger.info("Fisher immediate scan complete.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
