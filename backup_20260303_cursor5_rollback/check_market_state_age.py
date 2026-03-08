#!/usr/bin/env python3
"""
Health check: verify market state age is within acceptable limit (default 4 hours).
Exits 0 if state is fresh, 1 if stale or missing. For use in cron, Render health checks, or alerting.

Usage:
  python check_market_state_age.py
  python check_market_state_age.py --max-age-hours 4
  python check_market_state_age.py --max-age-hours 4 --path /var/data/market_state.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_iso_timestamp(ts: str):
    """Parse ISO timestamp with optional Z, return naive UTC datetime."""
    if not ts:
        return None
    ts = ts.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Check market state file age (exit 0=fresh, 1=stale/missing)")
    parser.add_argument("--max-age-hours", type=float, default=4.0, help="Max age in hours to consider fresh (default: 4)")
    parser.add_argument("--path", type=str, default=None, help="Path to market_state.json (default: MARKET_STATE_FILE_PATH or /var/data/market_state.json)")
    args = parser.parse_args()

    path = args.path or os.getenv("MARKET_STATE_FILE_PATH", "/var/data/market_state.json")
    path_obj = Path(path)

    if not path_obj.exists():
        print(f"❌ Market state file not found: {path}")
        return 1

    try:
        with open(path_obj, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read market state: {e}")
        return 1

    ts_str = state.get("timestamp")
    if not ts_str:
        print("❌ Market state has no timestamp")
        return 1

    then = parse_iso_timestamp(ts_str)
    if not then:
        print(f"❌ Could not parse timestamp: {ts_str}")
        return 1

    now = datetime.now(timezone.utc)
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    age_seconds = (now - then).total_seconds()
    age_hours = age_seconds / 3600.0

    if age_hours <= args.max_age_hours:
        print(f"✅ Market state is fresh (age: {age_hours:.2f}h, max: {args.max_age_hours}h)")
        return 0
    else:
        print(f"❌ Market state is stale (age: {age_hours:.2f}h > {args.max_age_hours}h)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
