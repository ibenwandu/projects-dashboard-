#!/usr/bin/env python3
"""
Run FT-DMI-EMA scan immediately (manual trigger).
Scans pairs from FT_DMI_EMA_PAIRS (or default list), evaluates 4H+1H setup and 15m Fisher trigger.
Publishes to market-state-api via HTTP (when MARKET_STATE_API_URL is set).

Usage:
  From Scalp-Engine directory:
    python run_ft_dmi_ema_scan.py

  On Render Web Shell (shell starts at Trade-Alerts repo root):
    cd Scalp-Engine && python run_ft_dmi_ema_scan.py
"""
import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

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
logger = logging.getLogger("run_ft_dmi_ema_scan")


def main():
    logger.info("=" * 60)
    logger.info("FT-DMI-EMA – immediate scan (4H+1H setup; 15m trigger optional)")
    logger.info("=" * 60)

    access_token = os.getenv("OANDA_ACCESS_TOKEN")
    account_id = os.getenv("OANDA_ACCOUNT_ID")
    environment = os.getenv("OANDA_ENV", "practice")

    if not access_token or not account_id:
        logger.error("OANDA_ACCESS_TOKEN and OANDA_ACCOUNT_ID must be set")
        sys.exit(1)

    try:
        from src.oanda_client import OandaClient
        from src.ft_dmi_ema import get_setup_status, get_dmi_ema_setup_status
        from src.ft_dmi_ema import fetch_ft_dmi_ema_dataframes, fetch_dmi_ema_dataframes
        from src.ft_dmi_ema import InstrumentConfig
        from src.ft_dmi_ema.candle_adapter import pair_to_oanda, oanda_to_pair
        from src.integration.fisher_market_bridge import post_ft_dmi_ema_to_api
    except ImportError as e:
        logger.error("Import failed (run from Scalp-Engine directory): %s", e)
        sys.exit(1)

    client = OandaClient(
        access_token=access_token,
        account_id=account_id,
        environment=environment,
    )

    def get_candles(inst: str, gran: str, count: int):
        return client.get_candles(inst, granularity=gran, count=count)

    # Use env FT_DMI_EMA_PAIRS first; if empty, fall back to default list in config
    env_pairs_raw = os.getenv("FT_DMI_EMA_PAIRS", "").strip()
    pairs = InstrumentConfig.get_monitored_pairs()
    if env_pairs_raw:
        logger.info("Using FT_DMI_EMA_PAIRS from env: %s", ", ".join(pairs))
    else:
        logger.info("FT_DMI_EMA_PAIRS not set; using default pairs: %s", ", ".join(pairs))

    opportunities = []
    for pair_key in pairs:
        try:
            oanda_instrument = pair_to_oanda(pair_key) if "/" in pair_key or "-" in pair_key else pair_key
            data_15m, data_1h, data_4h = fetch_ft_dmi_ema_dataframes(get_candles, oanda_instrument)
            if data_15m is None or data_1h is None or data_4h is None:
                logger.warning("  %s: missing candle data, skip", pair_key)
                continue

            price_data = client.get_current_price(oanda_instrument)
            if not price_data:
                logger.warning("  %s: no price, skip", pair_key)
                continue

            bid = price_data.get("bid") or 0
            ask = price_data.get("ask") or 0
            current_price = (bid + ask) / 2 if bid and ask else 0
            current_spread = float(price_data.get("spread", 0) or 0)
            if not current_price:
                continue

            now = datetime.utcnow()
            status = get_setup_status(
                oanda_instrument, data_15m, data_1h, data_4h,
                current_price, current_spread, now,
            )

            pair_display = oanda_to_pair(oanda_instrument)
            if status.get("long_setup_ready"):
                opp = {
                    "id": f"FT_DMI_EMA_{pair_display}_LONG",
                    "pair": pair_display,
                    "direction": "LONG",
                    "entry": current_price,
                    "current_price": current_price,
                    "source": "FT_DMI_EMA",
                    "ft_15m_trigger_met": status.get("long_trigger_met", False),
                    "reason": "Setup ready: 4H bias + 1H confirmation; trigger when 15m Fisher bullish crossover",
                    "execution_config": {"mode": "IMMEDIATE_MARKET"},
                }
                opportunities.append(opp)
                trigger = "TRIGGER MET" if opp["ft_15m_trigger_met"] else "setup only"
                logger.info("  %s LONG @ %.5f [%s]", pair_display, current_price, trigger)
            if status.get("short_setup_ready"):
                opp = {
                    "id": f"FT_DMI_EMA_{pair_display}_SHORT",
                    "pair": pair_display,
                    "direction": "SHORT",
                    "entry": current_price,
                    "current_price": current_price,
                    "source": "FT_DMI_EMA",
                    "ft_15m_trigger_met": status.get("short_trigger_met", False),
                    "reason": "Setup ready: 4H bias + 1H confirmation; trigger when 15m Fisher bearish crossover",
                    "execution_config": {"mode": "IMMEDIATE_MARKET"},
                }
                opportunities.append(opp)
                trigger = "TRIGGER MET" if opp["ft_15m_trigger_met"] else "setup only"
                logger.info("  %s SHORT @ %.5f [%s]", pair_display, current_price, trigger)

            if not status.get("long_setup_ready") and not status.get("short_setup_ready"):
                logger.debug("  %s: no setup ready", pair_key)
        except Exception as e:
            logger.warning("  %s: %s", pair_key, e)

    logger.info("FT-DMI-EMA scan: %s opportunity(ies) (trigger met: %s)",
                len(opportunities), sum(1 for o in opportunities if o.get("ft_15m_trigger_met")))

    # DMI-EMA scan (1D/4H/1H DMI+EMA alignment)
    dmi_opportunities = []
    for pair_key in pairs:
        try:
            oanda_instrument = pair_to_oanda(pair_key) if "/" in pair_key or "-" in pair_key else pair_key
            data_1d, data_4h, data_1h, data_15m = fetch_dmi_ema_dataframes(get_candles, oanda_instrument)
            if data_1d is None or data_4h is None or data_1h is None or data_15m is None:
                continue
            price_data = client.get_current_price(oanda_instrument)
            if not price_data:
                continue
            bid = price_data.get("bid") or 0
            ask = price_data.get("ask") or 0
            current_price = (bid + ask) / 2 if bid and ask else 0
            current_spread = float(price_data.get("spread", 0) or 0)
            if not current_price:
                continue
            now = datetime.utcnow()
            status = get_dmi_ema_setup_status(
                oanda_instrument, data_1d, data_4h, data_1h, data_15m,
                current_price, current_spread, now,
            )
            pair_display = oanda_to_pair(oanda_instrument)
            if status.get("long_setup_ready"):
                dmi_opportunities.append({
                    "id": f"DMI_EMA_{pair_display}_LONG",
                    "pair": pair_display,
                    "direction": "LONG",
                    "entry": current_price,
                    "current_price": current_price,
                    "source": "DMI_EMA",
                    "ft_15m_trigger_met": status.get("ft_15m_trigger_met", False),
                    "dmi_15m_trigger_met": status.get("dmi_15m_trigger_met", False),
                    "reason": "1D/4H/1H +DI>-DI; 1H EMA9>26, distance ≥5 pips",
                    "execution_config": {"mode": "FISHER_M15_TRIGGER"},
                    "confidence_flags": status.get("confidence_flags", {}),
                })
            if status.get("short_setup_ready"):
                dmi_opportunities.append({
                    "id": f"DMI_EMA_{pair_display}_SHORT",
                    "pair": pair_display,
                    "direction": "SHORT",
                    "entry": current_price,
                    "current_price": current_price,
                    "source": "DMI_EMA",
                    "ft_15m_trigger_met": status.get("ft_15m_trigger_met", False),
                    "dmi_15m_trigger_met": status.get("dmi_15m_trigger_met", False),
                    "reason": "1D/4H/1H -DI>+DI; 1H EMA9<26, distance ≥5 pips",
                    "execution_config": {"mode": "FISHER_M15_TRIGGER"},
                    "confidence_flags": status.get("confidence_flags", {}),
                })
        except Exception as e:
            logger.debug("  DMI-EMA %s: %s", pair_key, e)
    logger.info("DMI-EMA scan: %s opportunity(ies)", len(dmi_opportunities))

    # Publish both to market-state-api so UI shows them
    posted = post_ft_dmi_ema_to_api(opportunities, dmi_ema_opportunities=dmi_opportunities)
    if posted:
        logger.info("FT-DMI-EMA + DMI-EMA opportunities sent to market-state-api.")
    else:
        # Fallback: write to market_state file if path set and no API
        market_state_path = os.getenv("MARKET_STATE_FILE_PATH", "/var/data/market_state.json")
        if os.path.exists(market_state_path):
            try:
                with open(market_state_path, "r") as f:
                    on_disk = json.load(f)
                on_disk["ft_dmi_ema_opportunities"] = opportunities
                on_disk["ft_dmi_ema_last_updated"] = datetime.utcnow().isoformat()
                on_disk["dmi_ema_opportunities"] = dmi_opportunities
                on_disk["dmi_ema_last_updated"] = datetime.utcnow().isoformat()
                with open(market_state_path, "w") as f:
                    json.dump(on_disk, f, indent=2)
                logger.info("Wrote %s FT-DMI-EMA + %s DMI-EMA opportunities to %s",
                            len(opportunities), len(dmi_opportunities), market_state_path)
            except Exception as e:
                logger.warning("Could not write to market state file: %s", e)
        else:
            logger.info("MARKET_STATE_API_URL not set and file not found; results only in log.")

    logger.info("=" * 60)
    logger.info("FT-DMI-EMA immediate scan complete.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
