#!/usr/bin/env python3
"""
Fisher Transform scan – runnable from Render when project root is src/.

Use this when the service Root Directory is "src": from the shell run
  python run_fisher_scan.py
"""
import os
import sys
import logging
from pathlib import Path

# When this file lives in src/, project root may be src contents
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("run_fisher_scan")


def main():
    logger.info("=" * 60)
    logger.info("Fisher Transform – immediate scan (manual)")
    logger.info("=" * 60)

    access_token = os.getenv("OANDA_ACCESS_TOKEN")
    account_id = os.getenv("OANDA_ACCOUNT_ID")
    environment = os.getenv("OANDA_ENV", "practice")

    if not access_token or not account_id:
        logger.error("OANDA_ACCESS_TOKEN and OANDA_ACCOUNT_ID must be set")
        sys.exit(1)

    try:
        from oandapyV20 import API
        from scanners.fisher_daily_scanner import FisherDailyScanner
        from integration.fisher_market_bridge import FisherMarketBridge
    except ImportError as e:
        logger.error("Import failed: %s", e)
        sys.exit(1)

    api = API(access_token=access_token, environment=environment)
    scanner = FisherDailyScanner(api)
    bridge = FisherMarketBridge()

    logger.info("Running Fisher scan for %s pairs...", len(scanner.pairs))
    opportunities = scanner.scan()

    if opportunities:
        bridge.add_fisher_opportunities(opportunities)
        logger.info("Added %s Fisher opportunities to market_state.", len(opportunities))
        for opp in opportunities:
            logger.info("  - %s %s @ %s (%s)", opp.get("pair"), opp.get("direction"), opp.get("entry"), opp.get("fisher_analysis", {}).get("setup_type", "N/A"))
    else:
        bridge.add_fisher_opportunities([])
        logger.info("No actionable Fisher opportunities; market_state fisher list cleared/updated.")

    logger.info("=" * 60)
    logger.info("Fisher immediate scan complete.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
