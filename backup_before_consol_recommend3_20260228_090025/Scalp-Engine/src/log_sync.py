"""
Push local log files to config-api so backup agent can read them.

Render does not share disks across services, so scalp-engine and scalp-engine-ui
each have their own /var/data. This module periodically reads the local log
files and POSTs them to config-api's /logs/ingest so config-api (and the
backup agent) can serve them.

Usage:
  Start the sync thread from scalp_engine.py (engine + oanda) and scalp_ui.py (ui).
"""
import os
import time
import threading
import logging
import requests
from datetime import datetime
from typing import List, Tuple

_log = logging.getLogger(__name__)

# (API component name, log filename prefix without date)
# e.g. ('engine', 'scalp_engine') -> reads scalp_engine_YYYYMMDD.log
COMPONENT_PREFIXES: List[Tuple[str, str]] = [
    ('engine', 'scalp_engine'),
    ('oanda', 'oanda'),
    ('ui', 'scalp_ui'),
]


def _get_log_dir() -> str:
    """Same logic as src/logger.get_log_dir()."""
    if os.getenv('ENV') == 'production' or os.getenv('RENDER'):
        return '/var/data/logs'
    from pathlib import Path
    scalp_engine_dir = Path(__file__).parent.parent
    return str(scalp_engine_dir / 'logs')


def _sync_once(config_api_base: str, components: List[Tuple[str, str]], timeout: int = 15) -> None:
    """
    Read local log files for the given components and POST to config-api.

    components: list of (api_component, filename_prefix), e.g. [('engine', 'scalp_engine'), ('oanda', 'oanda')]
    """
    if not config_api_base or not config_api_base.strip():
        return
    base = config_api_base.rstrip('/')
    if base.endswith('/config'):
        base = base[:-7]  # strip trailing '/config' only (don't touch hostname)
    url = f'{base}/logs/ingest'
    log_dir = _get_log_dir()
    today = datetime.utcnow().strftime('%Y%m%d')

    for api_component, prefix in components:
        filename = f'{prefix}_{today}.log'
        path = os.path.join(log_dir, filename)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception:
            continue
        try:
            r = requests.post(
                url,
                json={'component': api_component, 'content': content},
                timeout=timeout,
                headers={'Content-Type': 'application/json'},
            )
            if r.status_code == 200:
                _log.debug("[LogSync] %s -> config-api OK (%s chars)", api_component, len(content))
            else:
                print(f"[LogSync] {api_component} -> config-api {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"[LogSync] {api_component} -> error: {e}")


def start_log_sync_thread(
    config_api_base: str,
    components: List[Tuple[str, str]],
    interval_seconds: int = 60,
) -> threading.Thread:
    """
    Start a daemon thread that syncs local log files to config-api every interval_seconds.

    config_api_base: e.g. https://config-api-8n37.onrender.com or .../config (will be normalized)
    components: e.g. [('engine', 'scalp_engine'), ('oanda', 'oanda')] for engine; [('ui', 'scalp_ui')] for UI
    """
    def _run() -> None:
        while True:
            try:
                _sync_once(config_api_base, components)
            except Exception:
                pass
            time.sleep(interval_seconds)

    t = threading.Thread(target=_run, daemon=True, name='LogSyncToConfigAPI')
    t.start()
    return t
