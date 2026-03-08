"""
Fisher Market Bridge
Integrates Fisher opportunities into market_state.json
Keeps Fisher opportunities separate from LLM opportunities in UI

Supports POST to market-state-api when MARKET_STATE_API_URL is set (no shared disk needed).
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _to_json_safe(obj: Any) -> Any:
    """Convert numpy/NumPy types to native Python for JSON serialization."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    # NumPy scalars (np.bool_, np.int64, etc.) are not JSON serializable
    try:
        import numpy as np
        if hasattr(obj, 'item'):  # numpy scalar (bool_, int64, float64, etc.)
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except (ImportError, AttributeError, ValueError):
        pass
    return obj


def post_fisher_to_api(
    opportunities: List[Dict],
    fisher_analysis: Dict = None
) -> bool:
    """POST Fisher opportunities and optional fisher_analysis to market-state-api."""
    api_url = os.getenv("MARKET_STATE_API_URL", "").strip()
    if not api_url:
        logger.debug("MARKET_STATE_API_URL not set, skipping API POST")
        return False
    base = api_url.rstrip("/")
    if base.endswith("/market-state"):
        base = base[:-len("/market-state")]
    url = f"{base}/fisher-opportunities"

    parsed = urlparse(url)
    host = (parsed.hostname or parsed.netloc or "").split(":")[0]
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        logger.warning(
            "MARKET_STATE_API_URL has invalid scheme. Expected https://market-state-api.onrender.com/market-state, got: %s",
            api_url[:80] + ("..." if len(api_url) > 80 else ""),
        )
        return False

    logger.info("POSTing Fisher opportunities to %s", parsed.scheme + "://" + (parsed.netloc or host) + "/fisher-opportunities")
    api_key = os.getenv("MARKET_STATE_API_KEY", "")
    try:
        import requests
        payload = {
            "fisher_opportunities": _to_json_safe(opportunities),
            "fisher_count": len(opportunities),
            "fisher_last_updated": datetime.utcnow().isoformat(),
        }
        if fisher_analysis:
            payload["fisher_analysis"] = _to_json_safe(fisher_analysis)
        headers = {"Content-Type": "application/json"}
        if api_key and api_key != "change-me-in-production":
            headers["X-API-Key"] = api_key
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            logger.info("POSTed %s Fisher opportunities to market-state-api", len(opportunities))
            return True
        logger.warning("market-state-api returned %s: %s", r.status_code, (r.text or "")[:200])
    except Exception as e:
        logger.warning("Could not POST to market-state-api: %s", e)
    return False


def post_ft_dmi_ema_to_api(
    opportunities: List[Dict],
    dmi_ema_opportunities: Optional[List[Dict]] = None,
) -> bool:
    """POST FT-DMI-EMA and optionally DMI-EMA opportunities to market-state-api so the UI can show them."""
    api_url = os.getenv("MARKET_STATE_API_URL", "").strip()
    if not api_url:
        logger.debug("MARKET_STATE_API_URL not set, skipping FT-DMI-EMA API POST")
        return False
    base = api_url.rstrip("/")
    if base.endswith("/market-state"):
        base = base[:-len("/market-state")]
    url = f"{base}/ft-dmi-ema-opportunities"

    parsed = urlparse(url)
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        logger.warning(
            "MARKET_STATE_API_URL has invalid scheme for FT-DMI-EMA POST: %s",
            api_url[:80] + ("..." if len(api_url) > 80 else ""),
        )
        return False

    n_ft = len(opportunities)
    n_dmi = len(dmi_ema_opportunities) if dmi_ema_opportunities is not None else 0
    logger.info("POSTing %s FT-DMI-EMA + %s DMI-EMA opportunity(ies) to %s", n_ft, n_dmi, base)
    api_key = os.getenv("MARKET_STATE_API_KEY", "")
    try:
        import requests
        payload = {
            "ft_dmi_ema_opportunities": _to_json_safe(opportunities),
            "ft_dmi_ema_last_updated": datetime.utcnow().isoformat(),
        }
        if dmi_ema_opportunities is not None:
            payload["dmi_ema_opportunities"] = _to_json_safe(dmi_ema_opportunities)
            payload["dmi_ema_last_updated"] = datetime.utcnow().isoformat()
        headers = {"Content-Type": "application/json"}
        if api_key and api_key != "change-me-in-production":
            headers["X-API-Key"] = api_key
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            logger.info("POSTed FT-DMI-EMA + DMI-EMA opportunities to market-state-api")
            return True
        logger.warning("market-state-api FT-DMI-EMA returned %s: %s", r.status_code, (r.text or "")[:200])
    except Exception as e:
        logger.warning("Could not POST FT-DMI-EMA to market-state-api: %s", e)
    return False


class FisherMarketBridge:
    """
    Bridges Fisher Transform analysis into market state
    
    Maintains separation:
    - LLM opportunities: market_state['opportunities']
    - Fisher opportunities: market_state['fisher_opportunities']
    
    This allows separate UI display as requested
    """
    
    def __init__(self, market_state_path: str = "/var/data/market_state.json"):
        """
        Args:
            market_state_path: Path to market_state.json
        """
        self.market_state_path = market_state_path
        self.logger = logging.getLogger('FisherMarketBridge')
    
    def add_fisher_opportunities(
        self,
        fisher_opportunities: List[Dict],
        fisher_analysis: Dict = None
    ) -> bool:
        """
        Add Fisher opportunities and optional fisher_analysis to market_state.json.
        Keeps Fisher separate from LLM opportunities.

        Args:
            fisher_opportunities: List of Fisher opportunities from scanner
            fisher_analysis: Optional per-pair Fisher data (for warnings)
        """
        try:
            market_state = self._load_market_state()
            market_state['fisher_opportunities'] = fisher_opportunities
            market_state['fisher_last_updated'] = datetime.utcnow().isoformat()
            market_state['fisher_count'] = len(fisher_opportunities)
            if fisher_analysis:
                market_state['fisher_analysis'] = fisher_analysis
                try:
                    from src.indicators.fisher_reversal_analyzer import check_fisher_warnings
                    for opp in market_state.get('opportunities', []):
                        if opp.get('llm_sources') or opp.get('consensus_level'):
                            check_fisher_warnings(opp, fisher_analysis)
                except Exception as e:
                    self.logger.warning("Could not apply Fisher warnings: %s", e)

            self._save_market_state(market_state)
            self.logger.info(
                f"✅ Added {len(fisher_opportunities)} Fisher opportunities to market state"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error adding Fisher opportunities: {e}", exc_info=True)
            return False
    
    def get_fisher_opportunities(self) -> List[Dict]:
        """
        Get Fisher opportunities from market state
        
        Returns:
            List of Fisher opportunities
        """
        
        try:
            market_state = self._load_market_state()
            return market_state.get('fisher_opportunities', [])
        except Exception as e:
            self.logger.error(f"❌ Error getting Fisher opportunities: {e}")
            return []
    
    def clear_fisher_opportunities(self):
        """Clear all Fisher opportunities from market state"""
        
        try:
            market_state = self._load_market_state()
            market_state['fisher_opportunities'] = []
            market_state['fisher_last_updated'] = datetime.utcnow().isoformat()
            market_state['fisher_count'] = 0
            self._save_market_state(market_state)
            self.logger.info("🧹 Cleared Fisher opportunities from market state")
        except Exception as e:
            self.logger.error(f"❌ Error clearing Fisher opportunities: {e}")
    
    def update_fisher_opportunity_status(self, opp_id: str, enabled: bool, 
                                        config: Dict = None) -> bool:
        """
        Update Fisher opportunity enabled status and configuration
        
        Args:
            opp_id: Opportunity ID
            enabled: Whether opportunity is enabled
            config: Optional configuration updates
        
        Returns:
            True if successful
        """
        
        try:
            market_state = self._load_market_state()
            fisher_opps = market_state.get('fisher_opportunities', [])
            
            for opp in fisher_opps:
                if opp.get('id') == opp_id:
                    opp['fisher_config']['enabled'] = enabled
                    if config:
                        opp['fisher_config'].update(config)
                    
                    self._save_market_state(market_state)
                    self.logger.info(
                        f"✅ Updated Fisher opportunity {opp_id}: enabled={enabled}"
                    )
                    return True
            
            self.logger.warning(f"⚠️ Fisher opportunity {opp_id} not found")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error updating Fisher opportunity: {e}")
            return False
    
    def _load_market_state(self) -> Dict:
        """Load market state from disk. Returns minimal state if file missing or corrupt."""
        
        try:
            with open(self.market_state_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'opportunities': [],
                'fisher_opportunities': [],
                'bias': 'NEUTRAL',
                'regime': 'UNKNOWN',
                'timestamp': datetime.utcnow().isoformat()
            }
        except json.JSONDecodeError as e:
            self.logger.warning(f"Corrupt market_state.json, using fresh state: {e}")
            return {
                'opportunities': [],
                'fisher_opportunities': [],
                'bias': 'NEUTRAL',
                'regime': 'UNKNOWN',
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error loading market state: {e}")
            return {
                'opportunities': [],
                'fisher_opportunities': [],
                'bias': 'NEUTRAL',
                'regime': 'UNKNOWN',
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _save_market_state(self, market_state: Dict):
        """Save market state to disk using atomic writes (sanitizes numpy types for JSON)."""
        import os
        import tempfile
        import shutil

        try:
            os.makedirs(os.path.dirname(self.market_state_path), exist_ok=True)
            safe_state = _to_json_safe(market_state)

            # Atomic write: write to temp file first, then rename
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.json',
                prefix='market_state_',
                dir=os.path.dirname(self.market_state_path),
                text=True
            )

            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(safe_state, f, indent=2)

                # Atomic rename
                shutil.move(temp_path, self.market_state_path)
            except Exception as e:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise

        except Exception as e:
            self.logger.error(f"Error saving market state: {e}")
            raise
