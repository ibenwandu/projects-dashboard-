"""
Reads market state from Trade-Alerts market_state.json
Supports both file-based and API-based reading
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
import pytz

# Try to import requests for API communication
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

class MarketStateReader:
    """Reads and validates market state from Trade-Alerts"""
    
    def __init__(self, state_file_path: str = None):
        """
        Initialize state reader
        
        Args:
            state_file_path: Path to market_state.json (default: ../Trade-Alerts/market_state.json)
        """
        if state_file_path is None:
            # CRITICAL FIX: Always use shared disk path on Render
            # Check if we're on Render (shared disk exists)
            if os.path.exists('/var/data') and os.access('/var/data', os.W_OK):
                # On Render with shared disk - use the standard path
                state_file_path = '/var/data/market_state.json'
            else:
                # Check for environment variable (may be set but corrupted)
                env_path = os.getenv('MARKET_STATE_FILE_PATH')
                if env_path:
                    # CRITICAL FIX: Clean up environment variable - fix any corruption
                    env_path_str = str(env_path).strip()
                    # Fix common corruption patterns (.jsc, .jsor should be .json)
                    if env_path_str.endswith('.jsc'):
                        env_path_str = env_path_str[:-4] + '.json'
                    elif env_path_str.endswith('.jsor'):
                        env_path_str = env_path_str[:-5] + '.json'
                    elif not env_path_str.endswith('.json'):
                        # If path contains market_state but wrong extension, fix it
                        if '/var/data/market_state' in env_path_str or env_path_str == '/var/data/market_state':
                            env_path_str = '/var/data/market_state.json'
                        elif 'market_state' in env_path_str:
                            env_path_str = env_path_str.split('market_state')[0] + 'market_state.json'
                        elif '/var/data/' in env_path_str:
                            env_path_str = '/var/data/market_state.json'
                        else:
                            env_path_str = '/var/data/market_state.json'
                    state_file_path = env_path_str
                else:
                    # Default: look in Trade-Alerts root directory (local dev)
                    current_dir = Path(__file__).parent.parent
                    trade_alerts_dir = current_dir.parent / "Trade-Alerts"
                    state_file_path = trade_alerts_dir / "market_state.json"
        
        # CRITICAL FIX: Ensure state_file_path is clean and ends with .json
        if isinstance(state_file_path, Path):
            path_str = str(state_file_path)
        else:
            path_str = str(state_file_path).strip() if state_file_path else ''
        
        # Always ensure path ends with .json - fix any corruption
        if path_str:
            # Fix common corruption patterns
            if path_str.endswith('.jsc'):
                path_str = path_str[:-4] + '.json'
            elif path_str.endswith('.jsor'):
                path_str = path_str[:-5] + '.json'
            elif not path_str.endswith('.json'):
                # If path doesn't end with .json, reconstruct it
                if '/var/data/market_state' in path_str or path_str == '/var/data/market_state':
                    path_str = '/var/data/market_state.json'
                elif 'market_state' in path_str:
                    # Extract base path before 'market_state' and add '.json'
                    parts = path_str.split('market_state')
                    path_str = parts[0] + 'market_state.json'
                elif path_str.endswith('/var/data/'):
                    path_str = '/var/data/market_state.json'
                else:
                    # Last resort: default to shared disk path
                    path_str = '/var/data/market_state.json'
        else:
            path_str = '/var/data/market_state.json'
        
        # Final validation: must end with .json
        if not path_str.endswith('.json'):
            path_str = '/var/data/market_state.json'
        
        self.state_file_path = Path(path_str)
        self.last_state = {}
        self.last_update_time = None
        
        # API configuration (for reading from API service)
        self.api_url = os.getenv('MARKET_STATE_API_URL')
        self.api_key = os.getenv('MARKET_STATE_API_KEY')
    
    def _load_from_api(self) -> Optional[Dict]:
        """
        Load market state from API service via HTTP GET
        
        Returns:
            Market state dictionary or None if API is unavailable
        """
        if not self.api_url:
            return None
        
        if not REQUESTS_AVAILABLE:
            print("⚠️ requests library not available - cannot read from API")
            return None
        
        try:
            headers = {}
            if self.api_key and self.api_key != 'change-me-in-production':
                headers['X-API-Key'] = self.api_key
            
            print(f"🌐 Attempting to load market state from API: {self.api_url}")
            response = requests.get(self.api_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                state = response.json()
                # Validate required fields
                required_fields = ['timestamp', 'global_bias', 'regime', 'approved_pairs']
                if all(field in state for field in required_fields):
                    print(f"✅ Market state loaded from API successfully")
                    return state
                else:
                    missing = [f for f in required_fields if f not in state]
                    print(f"⚠️ API response missing required fields: {missing}")
            else:
                print(f"⚠️ API returned status {response.status_code}: {response.text[:100]}")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"⚠️ API connection error: {e} - falling back to file reading")
            return None
        except requests.exceptions.Timeout:
            print(f"⚠️ API request timeout - falling back to file reading")
            return None
        except Exception as e:
            print(f"⚠️ API error: {e} - falling back to file reading")
            return None
        
    def load_state(self) -> Optional[Dict]:
        """
        Load market state from API service (preferred) or JSON file (fallback)
        
        Returns:
            Market state dictionary or None if unavailable
        """
        # Try API first (if configured)
        api_state = self._load_from_api()
        if api_state:
            # Validate and process API state
            try:
                timestamp = datetime.fromisoformat(api_state['timestamp'].replace('Z', '+00:00'))
                now = datetime.now(pytz.UTC)
                age_hours = (now - timestamp).total_seconds() / 3600
                
                if age_hours > 4:
                    # Stale state - return None
                    self.last_state = api_state
                    self.last_update_time = timestamp
                    return None
                
                self.last_state = api_state
                self.last_update_time = timestamp
                return api_state
            except (ValueError, KeyError):
                return None
        
        # Fallback to file-based reading
        # Debug: Log the path being checked
        if not self.state_file_path.exists():
            # Log helpful debug info (only in development/debug mode)
            import os
            if os.getenv('DEBUG_MARKET_STATE', 'false').lower() == 'true':
                print(f"⚠️ Market state file not found at: {self.state_file_path}")
                print(f"   Parent directory exists: {self.state_file_path.parent.exists()}")
                print(f"   Environment variable MARKET_STATE_FILE_PATH: {os.getenv('MARKET_STATE_FILE_PATH', 'Not set')}")
                if self.state_file_path.parent.exists():
                    try:
                        files = list(self.state_file_path.parent.iterdir())
                        print(f"   Files in parent directory: {[f.name for f in files]}")
                    except Exception as e:
                        print(f"   Could not list directory: {e}")
            return None
        
        try:
            with open(self.state_file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Validate required fields
            required_fields = ['timestamp', 'global_bias', 'regime', 'approved_pairs']
            if not all(field in state for field in required_fields):
                # Log missing fields for debugging
                missing_fields = [f for f in required_fields if f not in state]
                import os
                if os.getenv('DEBUG_MARKET_STATE', 'false').lower() == 'true':
                    print(f"⚠️ Market state missing required fields: {missing_fields}")
                return None
            
            # Check if state is stale (older than 4 hours)
            try:
                timestamp = datetime.fromisoformat(state['timestamp'].replace('Z', '+00:00'))
                now = datetime.now(pytz.UTC)
                age_hours = (now - timestamp).total_seconds() / 3600
                
                if age_hours > 4:
                    # Log staleness for debugging
                    import os
                    if os.getenv('DEBUG_MARKET_STATE', 'false').lower() == 'true':
                        print(f"⚠️ Market state is stale: {age_hours:.2f} hours old (threshold: 4 hours)")
                        print(f"   Timestamp: {state['timestamp']}, Current time: {now.isoformat()}")
                    # Store the stale state anyway (with a flag) for debugging
                    self.last_state = state
                    self.last_update_time = timestamp
                    # Still return None to indicate staleness, but at least we've loaded it
                    return None
                
                self.last_state = state
                self.last_update_time = timestamp
                return state
            except (ValueError, KeyError) as e:
                # Log parsing error for debugging
                import os
                if os.getenv('DEBUG_MARKET_STATE', 'false').lower() == 'true':
                    print(f"⚠️ Error parsing market state timestamp: {e}")
                return None
                
        except json.JSONDecodeError as e:
            # Log JSON parse error for debugging
            import os
            if os.getenv('DEBUG_MARKET_STATE', 'false').lower() == 'true':
                print(f"⚠️ Invalid JSON in market state file: {e}")
            return None
        except IOError as e:
            # Log IO error for debugging
            import os
            if os.getenv('DEBUG_MARKET_STATE', 'false').lower() == 'true':
                print(f"⚠️ IO error reading market state file: {e}")
            return None
    
    def get_bias(self) -> Optional[str]:
        """Get global bias (BULLISH, BEARISH, NEUTRAL)"""
        if not self.last_state:
            self.load_state()
        return self.last_state.get('global_bias')
    
    def get_regime(self) -> Optional[str]:
        """Get market regime (TRENDING, RANGING, HIGH_VOL, NORMAL)"""
        if not self.last_state:
            self.load_state()
        return self.last_state.get('regime', 'NORMAL')
    
    def get_approved_pairs(self) -> list:
        """Get list of approved trading pairs"""
        if not self.last_state:
            self.load_state()
        return self.last_state.get('approved_pairs', [])
    
    def is_state_valid(self) -> bool:
        """Check if state file exists and is not stale"""
        state = self.load_state()
        return state is not None
    
    def get_state_age_hours(self) -> Optional[float]:
        """Get age of current state in hours"""
        if not self.last_update_time:
            if not self.load_state():
                return None
        
        if self.last_update_time:
            now = datetime.now(pytz.UTC)
            return (now - self.last_update_time).total_seconds() / 3600
        return None

