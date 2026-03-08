"""
Semi-Auto Controller
Per-opportunity execution configuration for Fisher and LLM opportunities.
Fisher opportunities can only trade on Semi-Auto or Manual — never full-auto.

When CONFIG_API_URL is set, load/save via config-api so UI and engine see the same
enabled trades (they run on different servers and do not share disk).
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

CONFIG_FILE = "/var/data/semi_auto_config.json"


def _config_api_base() -> Optional[str]:
    """Config API base URL (no /config suffix) for semi-auto-config endpoint."""
    url = os.getenv("CONFIG_API_URL", "").strip()
    if not url:
        return None
    base = url.rstrip("/")
    if base.endswith("/config"):
        base = base[:-7]
    return base


class SemiAutoController:
    """
    Manages per-opportunity execution configuration.
    Used by Fisher opportunities and optional per-opp overrides for LLM.
    When CONFIG_API_URL is set, uses config-api so UI and engine share the same config.
    """
    
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self._config: Dict = {}
        self._load()
    
    def _load(self):
        """Load per-opportunity config from config-api (if set) or disk."""
        self._config = {'opportunities': {}, 'updated': None}
        api_base = _config_api_base()
        if api_base:
            try:
                import requests
                r = requests.get(f"{api_base}/semi-auto-config", timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    self._config = data if isinstance(data, dict) else self._config
                    if 'opportunities' not in self._config:
                        self._config['opportunities'] = {}
                    n = len(self._config['opportunities'])
                    enabled = sum(1 for o in self._config['opportunities'].values() if o.get('enabled'))
                    logger.info(f"Semi-auto config loaded from API: {n} opportunities, {enabled} enabled")
                    return
            except Exception as e:
                logger.warning(f"Could not load semi-auto config from API: {e} - using file fallback")
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self._config = json.load(f)
                if 'opportunities' not in self._config:
                    self._config['opportunities'] = {}
                logger.debug(f"Loaded semi-auto config from file: {len(self._config.get('opportunities', {}))} opportunities")
        except Exception as e:
            logger.warning(f"Could not load semi-auto config from file: {e}")
    
    def _save(self):
        """Save config to config-api (if set) and optionally to disk."""
        self._config['updated'] = datetime.utcnow().isoformat()
        api_base = _config_api_base()
        if api_base:
            try:
                import requests
                r = requests.post(f"{api_base}/semi-auto-config", json=self._config, timeout=5)
                if r.status_code == 200:
                    logger.debug("Semi-auto config saved to API")
                else:
                    logger.warning(f"Semi-auto config API save returned {r.status_code}")
            except Exception as e:
                logger.warning(f"Could not save semi-auto config to API: {e}")
        try:
            os.makedirs(os.path.dirname(self.config_path) or '.', exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving semi-auto config to file: {e}")
    
    def get_opportunity_config(self, opp_id: str) -> Optional[Dict]:
        """Get execution config for an opportunity (e.g. enabled, mode, max_runs).
        If source-aware key (e.g. LLM_USD/JPY_SHORT) is missing, fall back to legacy key (USD/JPY_SHORT).
        """
        opps = self._config.get('opportunities', {})
        cfg = opps.get(opp_id)
        if cfg is not None:
            return cfg
        if '_' in opp_id:
            legacy_key = opp_id.split('_', 1)[-1]
            return opps.get(legacy_key)
        return None
    
    def set_opportunity_config(self, opp_id: str, enabled: bool = True,
                               mode: str = "MANUAL", max_runs: int = 1,
                               sl_type: Optional[str] = None, **kwargs) -> None:
        """
        Set per-opportunity execution config.
        mode: MANUAL | FISHER_H1_CROSSOVER | FISHER_M15_CROSSOVER | RECOMMENDED_PRICE | IMMEDIATE_MARKET
        """
        if 'opportunities' not in self._config:
            self._config['opportunities'] = {}
        self._config['opportunities'][opp_id] = {
            'enabled': enabled,
            'mode': mode,
            'max_runs': max_runs,
            'sl_type': sl_type,
            **kwargs
        }
        self._save()
        logger.info(f"Semi-auto: Updated config for {opp_id} (enabled={enabled}, mode={mode})")
    
    def is_enabled(self, opp_id: str) -> bool:
        """Return True if this opportunity is enabled for execution."""
        cfg = self.get_opportunity_config(opp_id)
        return bool(cfg and cfg.get('enabled', False))
    
    def set_opportunity_enabled(self, opp_id: str, enabled: bool) -> None:
        """
        Set only the enabled flag for an opportunity, preserving mode/max_runs/sl_type.
        Used when an opportunity leaves market state so it reappears as Disabled (basis may have changed).
        """
        cfg = self.get_opportunity_config(opp_id) or {}
        self.set_opportunity_config(
            opp_id,
            enabled=enabled,
            mode=cfg.get('mode', 'MANUAL'),
            max_runs=cfg.get('max_runs', 1),
            sl_type=cfg.get('sl_type'),
        )
    
    def list_fisher_opportunities_config(self) -> List[Dict]:
        """List all stored configs (for UI)."""
        return [
            {'id': k, **v}
            for k, v in self._config.get('opportunities', {}).items()
        ]


__all__ = ['SemiAutoController', 'CONFIG_FILE']
