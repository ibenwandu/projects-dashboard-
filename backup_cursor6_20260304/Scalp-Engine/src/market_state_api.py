"""
Market State API: Receives market state from Trade-Alerts via HTTP
Works across different Render Blueprints (no shared disk needed)
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MarketStateAPI:
    """Receives and stores market state from Trade-Alerts via API"""
    
    def __init__(self, state_file_path: str = None):
        """
        Initialize market state API receiver
        
        Args:
            state_file_path: Path to store market state (default: /var/data/market_state.json or local)
        """
        if state_file_path is None:
            # Check for environment variable first (for Render deployment)
            env_path = os.getenv('MARKET_STATE_FILE_PATH')
            if env_path:
                state_file_path = env_path
            else:
                # Default: Use shared disk if available, otherwise local
                if os.path.exists('/var/data'):
                    state_file_path = '/var/data/market_state.json'
                else:
                    state_file_path = 'market_state.json'
        
        self.state_file_path = Path(state_file_path)
        self.last_state = {}
        self.last_update_time = None

    def _atomic_write(self, state: Dict) -> bool:
        """
        Write state to file using atomic writes (temp file + rename).
        Prevents file corruption if write is interrupted.

        Args:
            state: State dictionary to write

        Returns:
            True if successful, False otherwise
        """
        import tempfile
        import shutil

        try:
            # Temp file in same directory (ensures same filesystem for atomic rename)
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.json',
                prefix='market_state_',
                dir=str(self.state_file_path.parent),
                text=True
            )

            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=4)

                # Atomic rename on same filesystem
                shutil.move(temp_path, str(self.state_file_path))
                return True
            except Exception as e:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                logger.error(f"Error writing to temp file: {e}")
                return False

        except Exception as e:
            logger.error(f"Error creating temp file for atomic write: {e}")
            return False

    def save_state(self, state: Dict) -> bool:
        """
        Save market state received from Trade-Alerts.

        CRITICAL: Preserve Fisher opportunities from existing file.
        Trade-Alerts does not know about Fisher; the Fisher scan writes them separately.
        If we overwrite without merging, Fisher opportunities would be lost.

        Args:
            state: Market state dictionary from Trade-Alerts

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure directory exists
            self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Validate required fields
            required_fields = ['timestamp', 'global_bias', 'regime', 'approved_pairs']
            if not all(field in state for field in required_fields):
                logger.error(f"Invalid state: missing required fields. Got: {list(state.keys())}")
                return False

            # Preserve Fisher and FT-DMI-EMA data from existing file (Trade-Alerts doesn't send these)
            existing = self.load_state()
            if existing:
                for key in ('fisher_opportunities', 'fisher_last_updated', 'fisher_count', 'fisher_analysis',
                            'ft_dmi_ema_opportunities', 'ft_dmi_ema_last_updated',
                            'dmi_ema_opportunities', 'dmi_ema_last_updated'):
                    if key in existing:
                        state[key] = existing[key]
                        if key == 'fisher_analysis':
                            logger.info(f"   Preserved Fisher data: {key}={len(existing.get(key, {}))} pairs")
                        else:
                            logger.info(f"   Preserved Fisher data: {key}={len(existing[key]) if isinstance(existing[key], list) else existing[key]}")
                # Apply Fisher warnings to LLM opportunities when we have fisher_analysis
                fa = state.get('fisher_analysis', {})
                if fa:
                    try:
                        from src.indicators.fisher_reversal_analyzer import check_fisher_warnings
                        for opp in state.get('opportunities', []):
                            if opp.get('llm_sources') or opp.get('consensus_level'):
                                check_fisher_warnings(opp, fa)
                    except Exception as e:
                        logger.warning("Could not apply Fisher warnings in save_state: %s", e)

            # Save merged state to file using atomic writes
            if not self._atomic_write(state):
                return False

            # Update cache
            self.last_state = state
            try:
                self.last_update_time = datetime.fromisoformat(state['timestamp'].replace('Z', '+00:00'))
            except (ValueError, KeyError):
                self.last_update_time = datetime.utcnow()

            logger.info(f"✅ Market state saved to {self.state_file_path}")
            logger.info(f"   Bias: {state.get('global_bias')}, Regime: {state.get('regime')}, Pairs: {state.get('approved_pairs')}")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving market state to {self.state_file_path}: {e}")
            return False
    
    def load_state(self) -> Optional[Dict]:
        """
        Load market state from file (for reading by Scalp-Engine)
        
        Returns:
            Market state dictionary or None if file doesn't exist or is invalid
        """
        if not self.state_file_path.exists():
            return None
        
        try:
            with open(self.state_file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Validate required fields
            required_fields = ['timestamp', 'global_bias', 'regime', 'approved_pairs']
            if not all(field in state for field in required_fields):
                return None
            
            # Update cache
            self.last_state = state
            try:
                self.last_update_time = datetime.fromisoformat(state['timestamp'].replace('Z', '+00:00'))
            except (ValueError, KeyError):
                self.last_update_time = datetime.utcnow()
            
            return state
                
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading market state: {e}")
            return None
    
    def merge_fisher_opportunities(self, fisher_data: Dict) -> bool:
        """
        Merge Fisher opportunities into market state (for POST /fisher-opportunities).
        Works without shared disk: Fisher scan POSTs, we merge into file.

        Args:
            fisher_data: {"fisher_opportunities": [...], "fisher_count": N, "fisher_last_updated": "..."}
        """
        try:
            state = self.load_state()
            if not state:
                # No existing state - create minimal and add Fisher
                state = {
                    'timestamp': fisher_data.get('fisher_last_updated', ''),
                    'global_bias': 'NEUTRAL',
                    'regime': 'UNKNOWN',
                    'approved_pairs': [],
                    'opportunities': []
                }

            state['fisher_opportunities'] = fisher_data.get('fisher_opportunities', [])
            state['fisher_count'] = fisher_data.get('fisher_count', len(state['fisher_opportunities']))
            state['fisher_last_updated'] = fisher_data.get('fisher_last_updated', '')
            fisher_analysis = fisher_data.get('fisher_analysis')
            if fisher_analysis:
                state['fisher_analysis'] = fisher_analysis
                # Apply Fisher warnings to LLM opportunities
                try:
                    from src.indicators.fisher_reversal_analyzer import check_fisher_warnings
                    for opp in state.get('opportunities', []):
                        if opp.get('llm_sources') or opp.get('consensus_level'):
                            check_fisher_warnings(opp, fisher_analysis)
                except Exception as e:
                    logger.warning("Could not apply Fisher warnings: %s", e)

            self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Use atomic write instead of direct write
            if not self._atomic_write(state):
                return False

            self.last_state = state
            logger.info(f"✅ Merged Fisher opportunities: {state['fisher_count']} opportunities")
            return True
        except Exception as e:
            logger.error(f"❌ Error merging Fisher opportunities: {e}")
            return False

    def merge_ft_dmi_ema_opportunities(self, ft_dmi_ema_data: Dict) -> bool:
        """
        Merge FT-DMI-EMA and optionally DMI-EMA opportunities into market state (for POST /ft-dmi-ema-opportunities).
        Payload may include dmi_ema_opportunities and dmi_ema_last_updated.
        """
        try:
            state = self.load_state()
            if not state:
                state = {
                    'timestamp': ft_dmi_ema_data.get('ft_dmi_ema_last_updated', ''),
                    'global_bias': 'NEUTRAL',
                    'regime': 'UNKNOWN',
                    'approved_pairs': [],
                    'opportunities': [],
                }
            state['ft_dmi_ema_opportunities'] = ft_dmi_ema_data.get('ft_dmi_ema_opportunities', [])
            state['ft_dmi_ema_last_updated'] = ft_dmi_ema_data.get('ft_dmi_ema_last_updated', '')
            if 'dmi_ema_opportunities' in ft_dmi_ema_data:
                state['dmi_ema_opportunities'] = ft_dmi_ema_data.get('dmi_ema_opportunities', [])
                state['dmi_ema_last_updated'] = ft_dmi_ema_data.get('dmi_ema_last_updated', '')

            self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Use atomic write instead of direct write
            if not self._atomic_write(state):
                return False

            self.last_state = state
            n_ft = len(state['ft_dmi_ema_opportunities'])
            n_dmi = len(state.get('dmi_ema_opportunities', []))
            logger.info(f"✅ Merged FT-DMI-EMA: {n_ft}, DMI-EMA: {n_dmi} opportunities")
            return True
        except Exception as e:
            logger.error(f"❌ Error merging FT-DMI-EMA opportunities: {e}")
            return False