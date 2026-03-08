"""
Enhanced Scalp-Engine with Auto-Trading Capabilities
This replaces your existing Scalp-Engine/scalp_engine.py

Integrates monitoring + execution into a unified system
"""

import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
import pytz

# OANDA imports (already in your requirements.txt)
from oandapyV20 import API
from oandapyV20.endpoints import accounts, orders, trades, pricing
from oandapyV20.exceptions import V20Error

# Stable opportunity ID (shared with UI and enforcer so re-enable + reset run count work)
try:
    from src.execution.opportunity_id import get_stable_opportunity_id
except ImportError:
    get_stable_opportunity_id = None  # type: ignore[misc, assignment]


def _stable_opp_id_fallback(opp: Dict) -> str:
    """Fallback when get_stable_opportunity_id is not available. Must match opportunity_id.py exactly."""
    pair_raw = (opp.get('pair') or '').strip().replace('_', '/')
    pair = pair_raw.upper() if pair_raw else ''
    direction_raw = (opp.get('direction') or '').strip().upper()
    direction = (
        'LONG' if direction_raw in ('LONG', 'BUY') else
        'SHORT' if direction_raw in ('SHORT', 'SELL') else
        direction_raw
    )
    return f"{pair}_{direction}" if pair and direction else (opp.get('id') or '')

# Execution modes whose trigger is crossover/signal (not price). Skip price staleness check for these.
EXECUTION_MODES_TRIGGER_IS_CROSSOVER = (
    'FISHER_H1_CROSSOVER', 'FISHER_M15_CROSSOVER',
    'DMI_H1_CROSSOVER', 'DMI_M15_CROSSOVER',
)

# Import the new auto-trader components
# These will be in the same directory (Scalp-Engine/)
try:
    from auto_trader_core import (
        TradeConfig, TradingMode, StopLossType, TradeState, ExecutionMode,
        TradeExecutor, PositionManager, RiskController
    )
    AUTO_TRADER_AVAILABLE = True
except ImportError:
    AUTO_TRADER_AVAILABLE = False
    print("⚠️ Auto-trader core not found. Running in monitoring mode only.")

FT_CANDLE_FETCHER_AVAILABLE = False
FTCandleFetcher = None
try:
    from src.ft_dmi_ema.ft_candle_fetcher import FTCandleFetcher
    FT_CANDLE_FETCHER_AVAILABLE = True
except ImportError:
    pass


class ScalpEngine:
    """
    Enhanced Scalp-Engine with auto-trading capabilities
    
    Modes:
    - MONITOR: Original behavior (just watch, no trading)
    - MANUAL: Generate trade proposals for UI approval
    - AUTO: Execute trades automatically based on intelligence
    """
    
    def __init__(self):
        """Initialize enhanced engine"""
        self.logger = self._setup_logger()

        # Attach file handlers for persistent logging on Render/local dev
        try:
            from src.logger import attach_file_handler
            attach_file_handler(
                ['ScalpEngine', 'TradeExecutor', 'PositionManager', 'RiskController'],
                'scalp_engine'
            )
            attach_file_handler(['OandaClient'], 'oanda')
        except ImportError:
            self.logger.warning("⚠️ Logger module not available - stdout only")

        # Push log files to config-api so backup agent can read them (Render disks are per-service)
        try:
            config_api_url = os.getenv('CONFIG_API_URL')
            if config_api_url:
                from src.log_sync import start_log_sync_thread, COMPONENT_PREFIXES
                engine_oanda = [(c, p) for c, p in COMPONENT_PREFIXES if c in ('engine', 'oanda')]
                start_log_sync_thread(config_api_url, engine_oanda, interval_seconds=60)
                self.logger.info("Log sync to config-api started (engine+oanda, every 60s)")
            else:
                self.logger.warning("CONFIG_API_URL not set - log sync disabled")
        except Exception as e:
            self.logger.warning("Log sync failed to start: %s", e)

        # OANDA Configuration (from environment)
        self.access_token = os.getenv('OANDA_ACCESS_TOKEN')
        self.account_id = os.getenv('OANDA_ACCOUNT_ID')
        self.environment = os.getenv('OANDA_ENV', 'practice')
        
        if not self.access_token or not self.account_id:
            raise ValueError("OANDA credentials not configured")
        
        # Initialize OANDA client (raw API for TradeExecutor)
        self.oanda_api = API(
            access_token=self.access_token,
            environment=self.environment
        )
        
        # Also create OandaClient wrapper for MACD calculations (has get_candles method)
        try:
            # Try to import from src directory (if available)
            import sys
            from pathlib import Path
            src_path = Path(__file__).parent / "src"
            if src_path.exists() and str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))
            
            from oanda_client import OandaClient
            self.oanda_client = OandaClient(
                access_token=self.access_token,
                account_id=self.account_id,
                environment=self.environment
            )
        except ImportError:
            # Fallback: create a simple wrapper if OandaClient not available
            self.logger.warning("⚠️ OandaClient wrapper not available - MACD features may not work")
            # Create a minimal wrapper that uses the raw API
            class SimpleOandaWrapper:
                def __init__(self, api, account_id, logger):
                    self.client = api
                    self.account_id = account_id
                    self.logger = logger
                
                def get_candles(self, instrument: str, granularity: str = "M1", count: int = 100):
                    try:
                        from oandapyV20.endpoints import instruments
                        params = {
                            "count": count,
                            "granularity": granularity,
                            "price": "M"
                        }
                        r = instruments.InstrumentsCandles(instrument=instrument, params=params)
                        self.client.request(r)
                        
                        candles = []
                        for candle in r.response.get('candles', []):
                            if candle.get('complete', False):
                                candles.append({
                                    'time': candle['time'],
                                    'open': float(candle['mid']['o']),
                                    'high': float(candle['mid']['h']),
                                    'low': float(candle['mid']['l']),
                                    'close': float(candle['mid']['c']),
                                    'volume': int(candle.get('volume', 0))
                                })
                        return candles
                    except Exception as e:
                        if hasattr(self, 'logger'):
                            self.logger.error(f"Error getting candles: {e}")
                        return None
            
            self.oanda_client = SimpleOandaWrapper(self.oanda_api, self.account_id, self.logger)
        
        # FT-DMI-EMA dedicated candle fetcher (avoids 500/HTML errors from wrapper)
        self.ft_candle_fetcher = None
        if FT_CANDLE_FETCHER_AVAILABLE and FTCandleFetcher:
            try:
                self.ft_candle_fetcher = FTCandleFetcher(self.oanda_api, self.account_id)
                self.logger.info("✅ FT-DMI-EMA candle fetcher initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ FT-DMI-EMA candle fetcher unavailable, using oanda_client: {e}")
        
        # Market state file (shared with Trade-Alerts) - fallback if API not available
        self.market_state_file = os.getenv(
            'MARKET_STATE_FILE_PATH',
            '/var/data/market_state.json'
        )
        
        # Market state API URL (preferred over file)
        self.market_state_api_url = os.getenv('MARKET_STATE_API_URL')  # e.g., https://market-state-api.onrender.com/market-state
        self.market_state_api_key = os.getenv('MARKET_STATE_API_KEY')  # Optional API key for authentication
        
        # Configuration and state files
        self.config_file = "/var/data/auto_trader_config.json"
        self.state_file = "/var/data/trade_states.json"
        
        # Config API URL (primary source, like indicator-alerts-worker)
        self.config_api_url = os.getenv('CONFIG_API_URL')  # e.g., https://scalp-engine-ui.onrender.com/api/config
        
        # Track config file modification time for reloading (for file fallback)
        self.config_file_mtime = None
        
        # Load or create configuration (API first, then file fallback)
        self.config = self._load_config()
        
        # Initialize auto-trader components if available
        if AUTO_TRADER_AVAILABLE:
            self.executor = TradeExecutor(self.oanda_api, self.account_id)  # TradeExecutor needs raw API
            self.risk_controller = RiskController(self.config)
            self.position_manager = PositionManager(
                self.executor, 
                self.config,
                state_file=self.state_file,
                config_api_url=self.config_api_url,
                risk_controller=self.risk_controller
            )
            
            # Sync with OANDA on startup to detect existing trades and pending orders
            # CRITICAL: This must complete before main loop starts checking opportunities
            # This prevents duplicate trades from being opened on restart
            if self.config.trading_mode == TradingMode.AUTO:
                self.logger.info("🔄 Syncing with OANDA on startup (this prevents duplicate trades)...")
                try:
                    # Sync without market_state on startup (market_state not available yet)
                    self.position_manager.sync_with_oanda(market_state=None)
                    active_count = len(self.position_manager.active_trades)
                    pending_count = sum(1 for t in self.position_manager.active_trades.values() 
                                      if t.state == TradeState.PENDING)
                    open_count = active_count - pending_count
                    self.logger.info(
                        f"✅ Startup sync complete - {active_count} total ({open_count} open, "
                        f"{pending_count} pending) loaded from OANDA"
                    )
                    if active_count > 0:
                        trade_list = []
                        for t in list(self.position_manager.active_trades.values())[:10]:  # Show up to 10
                            trade_list.append(f"{t.pair} {t.direction} ({t.state.value})")
                        self.logger.info(
                            f"📋 Loaded trades: {', '.join(trade_list)}"
                        )
                except Exception as e:
                    self.logger.error(f"❌ Startup sync failed: {e}", exc_info=True)
                    # Continue anyway - has_existing_position will check OANDA directly
            
            self.logger.info("✅ Auto-trader components initialized")
        else:
            self.executor = None
            self.position_manager = None
            self.risk_controller = None
            self.logger.warning("⚠️ Running in MONITOR mode only")
        
        # State
        self.current_market_state = {}
        self.llm_weights = {}
        self.check_interval = 60  # seconds (main loop - market state checks)
        self.check_count = 0
        self.config_check_interval = 30  # seconds - check config file more frequently (2-5 minute range as requested)
        self.last_config_check_time = time.time()
        self.last_market_state_timestamp = None  # Track when market state was last updated
        self._last_file_mtime = None  # Track file modification time to detect updates
        # RL DB once per process (consol-recommend2 Phase 1.1)
        self._rl_db = None
        # RED FLAG duplicate-block log throttle: (pair, direction) -> last ERROR log time (consol-recommend2 Phase 1.2; consol-recommend3: 15 min)
        self._red_flag_duplicate_last_logged = {}
        self._red_flag_duplicate_window_seconds = 1800  # 30 min (suggestions cursor3 §5.4: extend to reduce log volume)
        # Stale opportunity price log throttle: first per (pair, direction) per window at INFO, rest at DEBUG (consol-recommend3 Phase 1.3)
        self._stale_price_log_last: Dict[tuple, float] = {}
        self._stale_price_log_window_seconds = 600  # 10 min
        # REJECTING STALE OPPORTUNITY log throttle: first per (pair, direction) per window at WARNING, rest at DEBUG (suggestions cursor3 §5.5)
        self._stale_reject_log_last: Dict[tuple, float] = {}
        self._stale_reject_log_window_seconds = 600  # 10 min
        # "Only one required LLM" throttle: once per process/hour at WARNING, rest at DEBUG (suggestions cursor3 §5.6)
        self._single_required_llm_last_warning: Optional[float] = None
        self._single_required_llm_warning_interval_seconds = 3600  # 1 hour
        # Weekend shutdown cancel message throttle: first per window at WARNING, rest at DEBUG (suggestions cursor3 §5.7)
        self._weekend_cancel_last_logged: Optional[float] = None
        self._weekend_cancel_window_seconds = 900  # 15 min
        # Config loaded from API: track last config for change detection (suggestions cursor3 §5.8 Option B)
        self._last_config_snapshot: Optional[tuple] = None  # (mode, stop_loss, max_trades)
        self._config_loaded_once = False

        self._log_startup()
    
    def _setup_logger(self):
        """Setup logging"""
        import logging
        logger = logging.getLogger('ScalpEngine')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _log_startup(self):
        """Log startup information"""
        self.logger.info("="*80)
        self.logger.info("🚀 ENHANCED SCALP-ENGINE STARTING")
        self.logger.info("="*80)
        self.logger.info(f"Environment: {self.environment}")
        self.logger.info(f"Account: {self.account_id}")
        
        if AUTO_TRADER_AVAILABLE:
            self.logger.info(f"Mode: {self.config.trading_mode.value}")
            self.logger.info(f"Max Open Trades: {self.config.max_open_trades}")
            self.logger.info(f"Stop Loss Type: {self.config.stop_loss_type.value}")
            self.logger.info(f"Min Consensus: {self.config.min_consensus_level}")
        else:
            self.logger.info("Mode: MONITOR (auto-trading not available)")
        
        self.logger.info("="*80)

    def _get_rl_db(self):
        """Return cached ScalpingRLEnhanced instance (init once per process, consol-recommend2 Phase 1.1)."""
        if self._rl_db is None:
            from pathlib import Path
            if os.path.exists('/var/data'):
                db_path = '/var/data/scalping_rl.db'
            else:
                data_dir = Path(__file__).parent / 'data'
                data_dir.mkdir(exist_ok=True)
                db_path = str(data_dir / 'scalping_rl.db')
            from src.scalping_rl_enhanced import ScalpingRLEnhanced
            self._rl_db = ScalpingRLEnhanced(db_path=db_path)
        return self._rl_db

    def _load_config_from_api(self) -> Optional['TradeConfig']:
        """Load configuration from API (primary source, like indicator-alerts-worker)"""
        if not self.config_api_url:
            return None
        
        # Use the URL as-is (config-api service endpoint is /config, not /api/config)
        api_url = self.config_api_url.rstrip('/')
        # Only append /config if URL doesn't already end with it
        if not api_url.endswith('/config'):
            api_url = f"{api_url}/config"
        
        # Retry logic for 502 errors (service might be sleeping on free tier)
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    self.logger.debug(f"Retrying API config load (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                
                self.logger.info(f"📡 Attempting to load config from API: {api_url}")
                response = requests.get(api_url, timeout=15)
                
                # Handle 502 Bad Gateway (service sleeping)
                if response.status_code == 502:
                    if attempt < max_retries - 1:
                        self.logger.info(f"Service appears to be sleeping (502). Waiting {retry_delay}s before retry...")
                        continue
                    else:
                        self.logger.warning(f"Service still sleeping after {max_retries} attempts. Falling back to file.")
                        return None
                
                response.raise_for_status()
                data = response.json()
                # Strip last_updated/updated so TradeConfig never receives them (consol-recommend2 Phase 2.1)
                data.pop('last_updated', None)
                data.pop('updated', None)

                # Debug: Log required_llms from API response
                if 'required_llms' in data:
                    self.logger.debug(
                        f"📋 Config API returned required_llms: {data['required_llms']} "
                        f"(type: {type(data['required_llms'])})"
                    )
                
                # Convert string enums to objects
                if 'trading_mode' in data:
                    data['trading_mode'] = TradingMode(data['trading_mode'])
                if 'stop_loss_type' in data:
                    data['stop_loss_type'] = StopLossType.from_string(data['stop_loss_type'])
                if 'execution_mode' in data:
                    data['execution_mode'] = ExecutionMode(data['execution_mode'])
                
                # Backward compatibility: convert require_gemini to required_llms
                # MUST do this BEFORE creating TradeConfig, and REMOVE the old key
                if 'required_llms' not in data and 'require_gemini' in data:
                    if data.get('require_gemini', True):
                        data['required_llms'] = ['gemini']
                    else:
                        data['required_llms'] = []
                    # Remove the old key so TradeConfig doesn't see it
                    del data['require_gemini']
                elif 'require_gemini' in data:
                    # If both exist, prefer required_llms and remove require_gemini
                    del data['require_gemini']
                
                config = TradeConfig(**data)
                
                loaded_mode = config.trading_mode.value
                loaded_sl = config.stop_loss_type.value
                required_llms = getattr(config, 'required_llms', None)
                required_llms_str = ', '.join(required_llms) if required_llms else 'None'
                # suggestions cursor3 §5.8 Option B: INFO only on first load or when mode/stop_loss/max_trades change; else DEBUG
                snapshot = (loaded_mode, loaded_sl, config.max_open_trades)
                is_first = not self._config_loaded_once
                is_change = self._last_config_snapshot is not None and self._last_config_snapshot != snapshot
                if is_first or is_change:
                    self.logger.info(
                        f"✅ Config loaded from API - Mode: {loaded_mode}, Stop Loss: {loaded_sl}, "
                        f"Max Trades: {config.max_open_trades}, Required LLMs: {required_llms_str}"
                    )
                    self._last_config_snapshot = snapshot
                    self._config_loaded_once = True
                else:
                    self.logger.debug(
                        f"Config loaded from API - Mode: {loaded_mode}, Stop Loss: {loaded_sl}, "
                        f"Max Trades: {config.max_open_trades}, Required LLMs: {required_llms_str}"
                    )
                # suggestions cursor3 §5.6: "Only one required LLM" at WARNING once per process/hour, rest at DEBUG
                if required_llms and len(required_llms) == 1:
                    now_ts = time.time()
                    last_ts = self._single_required_llm_last_warning
                    if last_ts is None or (now_ts - last_ts) >= self._single_required_llm_warning_interval_seconds:
                        self.logger.warning("⚠️ Only one required LLM (unusual) - verify config if unintended.")
                        self._single_required_llm_last_warning = now_ts
                    else:
                        self.logger.debug("Only one required LLM (unusual) - verify config if unintended (throttled).")
                
                return config
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    self.logger.debug(f"API timeout. Retrying in {retry_delay}s...")
                    continue
                else:
                    self.logger.warning(f"API timeout after {max_retries} attempts. Falling back to file.")
                    return None
            except requests.exceptions.RequestException as e:
                # Don't retry on 4xx errors (client errors)
                if hasattr(e, 'response') and e.response is not None:
                    if 400 <= e.response.status_code < 500:
                        self.logger.warning(f"Client error loading config from API ({api_url}): {e}, falling back to file")
                        return None
                # Retry on other network errors
                if attempt < max_retries - 1:
                    self.logger.debug(f"Network error. Retrying in {retry_delay}s...")
                    continue
                else:
                    self.logger.warning(f"Failed to load config from API ({api_url}) after {max_retries} attempts: {e}, falling back to file")
                    return None
            except (ValueError, json.JSONDecodeError) as e:
                self.logger.warning(f"Invalid JSON response from API ({api_url}): {e}, falling back to file")
                return None
            except Exception as e:
                self.logger.warning(f"Unexpected error loading config from API ({api_url}): {e}, falling back to file")
            return None
        
            return None
    
    def _load_config(self) -> 'TradeConfig':
        """Load configuration from API (primary) or file (fallback)"""
        if not AUTO_TRADER_AVAILABLE:
            # Return a dummy config for monitoring mode
            return type('DummyConfig', (), {
                'trading_mode': type('Mode', (), {'value': 'MONITOR'})()
            })()
        
        # Try API first if URL is provided (like indicator-alerts-worker pattern)
        # API service is on same disk as UI, so it always has latest config
        if self.config_api_url:
            config = self._load_config_from_api()
            if config:
                return config
            # If API fails, fall through to file fallback
            self.logger.warning("⚠️ API config load failed, falling back to file")
        
        # Fallback to file
        try:
            if os.path.exists(self.config_file):
                # Track file modification time
                self.config_file_mtime = os.path.getmtime(self.config_file)
                
                self.logger.info(f"📖 Loading config from: {self.config_file} (mtime: {self.config_file_mtime})")
                
                with open(self.config_file, 'r') as f:
                    file_content = f.read()
                    # Log full file content for debugging - this shows what's ACTUALLY in the file
                    self.logger.info("="*80)
                    self.logger.info("📄 RAW CONFIG FILE CONTENTS (from disk):")
                    self.logger.info("="*80)
                    self.logger.info(file_content)
                    self.logger.info("="*80)
                    f.seek(0)  # Reset file pointer
                    data = json.load(f)
                
                # Log what we loaded
                loaded_mode = data.get('trading_mode', 'UNKNOWN')
                loaded_sl = data.get('stop_loss_type', 'UNKNOWN')
                self.logger.info(f"📖 Config loaded from file - Mode: {loaded_mode}, Stop Loss: {loaded_sl}, Max Trades: {data.get('max_open_trades', 'N/A')}, Min Consensus: {data.get('min_consensus_level', 'N/A')}")
                    
                    # Convert string enums to objects
                if 'trading_mode' in data:
                    data['trading_mode'] = TradingMode(data['trading_mode'])
                if 'stop_loss_type' in data:
                    data['stop_loss_type'] = StopLossType.from_string(data['stop_loss_type'])
                if 'execution_mode' in data:
                    data['execution_mode'] = ExecutionMode(data['execution_mode'])
                
                # Strip last_updated/updated so TradeConfig never receives them (consol-recommend2 Phase 2.1)
                data.pop('last_updated', None)
                data.pop('updated', None)
                # Backward compatibility: convert require_gemini to required_llms
                # MUST do this BEFORE creating TradeConfig, and REMOVE the old key
                if 'required_llms' not in data and 'require_gemini' in data:
                    if data.get('require_gemini', True):
                        data['required_llms'] = ['gemini']
                    else:
                        data['required_llms'] = []
                    # Remove the old key so TradeConfig doesn't see it
                    del data['require_gemini']
                elif 'require_gemini' in data:
                    # If both exist, prefer required_llms and remove require_gemini
                    del data['require_gemini']

                return TradeConfig(**data)
            else:
                # Config file doesn't exist - DON'T create default (let UI create it)
                # Creating default would overwrite any UI config
                self.logger.info(f"ℹ️ Config file not found at {self.config_file}, using default (MANUAL mode) until UI saves config")
                self.config_file_mtime = None
                # Return default config but DON'T save it (let UI create the file)
                return TradeConfig(trading_mode=TradingMode.MANUAL)
                
        except Exception as e:
            self.logger.error(f"❌ Error loading config from {self.config_file}: {e}", exc_info=True)
            return TradeConfig(trading_mode=TradingMode.MANUAL)
    
    def _reload_config_if_changed(self):
        """Check if config has changed and reload (API first, then file mtime check)"""
        if not AUTO_TRADER_AVAILABLE:
            self.logger.warning("⚠️ Auto-trader not available, skipping config check")
            return
        
        # If API is configured, reload from API (it will always have latest from UI)
        # API service is on same disk as UI, so it always has latest config
        if self.config_api_url:
            config = self._load_config_from_api()
            if config:
                # Check if ANY config field has changed (not just mode and stop_loss_type)
                config_changed = (
                    config.trading_mode != self.config.trading_mode or
                    config.stop_loss_type != self.config.stop_loss_type or
                    config.max_open_trades != self.config.max_open_trades or
                    getattr(config, 'auto_trade_llm', True) != getattr(self.config, 'auto_trade_llm', True) or
                    getattr(config, 'auto_trade_fisher', True) != getattr(self.config, 'auto_trade_fisher', True) or
                    getattr(config, 'auto_trade_ft_dmi_ema', True) != getattr(self.config, 'auto_trade_ft_dmi_ema', True) or
                    getattr(config, 'auto_trade_dmi_ema', True) != getattr(self.config, 'auto_trade_dmi_ema', True) or
                    config.min_consensus_level != self.config.min_consensus_level or
                    config.base_position_size != self.config.base_position_size or
                    config.execution_mode != self.config.execution_mode or
                    config.macd_timeframe != self.config.macd_timeframe or
                    getattr(config, 'macd_sl_timeframe', None) != getattr(self.config, 'macd_sl_timeframe', None) or
                    getattr(config, 'dmi_sl_timeframe', None) != getattr(self.config, 'dmi_sl_timeframe', None) or
                    config.required_llms != self.config.required_llms
                )
                
                if config_changed:
                    old_mode = self.config.trading_mode.value
                    old_sl = self.config.stop_loss_type.value
                    old_base_size = self.config.base_position_size
                    old_max_trades = self.config.max_open_trades
                    
                    self.config = config
                    new_mode = config.trading_mode.value
                    new_sl = config.stop_loss_type.value
                    new_base_size = config.base_position_size
                    new_max_trades = config.max_open_trades
                    
                    # Update components
                    if self.position_manager:
                        self.position_manager.config = self.config
                    if self.risk_controller:
                        self.risk_controller.config = self.config
                    
                    self.logger.info(f"🔄 Configuration reloaded from API:")
                    if old_mode != new_mode:
                        self.logger.info(f"   Mode: {old_mode} → {new_mode}")
                    if old_sl != new_sl:
                        self.logger.info(f"   Stop Loss: {old_sl} → {new_sl}")
                    if old_max_trades != new_max_trades:
                        self.logger.info(f"   Max Trades: {old_max_trades} → {new_max_trades}")
                    if old_base_size != new_base_size:
                        self.logger.info(f"   Base Position Size: {old_base_size} → {new_base_size}")
                    self.logger.info(f"   Min Consensus: {self.config.min_consensus_level}")
                    self.logger.info(f"   Execution Mode: {self.config.execution_mode.value}")
                # If API succeeds, don't fall through to file check
                return
        
        # Fallback: File mtime check (if API not configured)
        try:
            if os.path.exists(self.config_file):
                current_mtime = os.path.getmtime(self.config_file)
                
                # Log file status on first check
                if self.config_file_mtime is None:
                    self.logger.info(f"🔍 Config file found: {self.config_file} (mtime: {current_mtime})")
                    # Also log current file contents for debugging
                    try:
                        with open(self.config_file, 'r') as f:
                            file_data = json.load(f)
                            self.logger.info(f"🔍 Initial file contents - Mode: {file_data.get('trading_mode', 'UNKNOWN')}, SL: {file_data.get('stop_loss_type', 'UNKNOWN')}")
                    except Exception as e:
                        self.logger.warning(f"Could not read initial file contents: {e}")
                
                # Always log mtime comparison when checking (for debugging)
                if self.config_file_mtime is not None:
                    changed = current_mtime > self.config_file_mtime
                    if changed:
                        self.logger.info(f"🔍 Config file mtime changed: {self.config_file_mtime} → {current_mtime} (diff: {current_mtime - self.config_file_mtime:.2f}s)")
                    else:
                        self.logger.debug(f"🔍 Config file unchanged: mtime={current_mtime}")
                
                if self.config_file_mtime is None or current_mtime > self.config_file_mtime:
                    # Config file has changed, reload it
                    old_mode = self.config.trading_mode.value if hasattr(self.config, 'trading_mode') else 'UNKNOWN'
                    old_sl = self.config.stop_loss_type.value if hasattr(self.config, 'stop_loss_type') else 'UNKNOWN'
                    
                    self.logger.info(f"🔍 Config file modified detected (mtime: {self.config_file_mtime} → {current_mtime}), reloading...")
                    
                    self.config = self._load_config()
                    
                    # Update mtime after successful reload
                    self.config_file_mtime = os.path.getmtime(self.config_file)
                    
                    new_mode = self.config.trading_mode.value
                    new_sl = self.config.stop_loss_type.value
                    
                    # Update components that use config
                    if self.position_manager:
                        self.position_manager.config = self.config
                    if self.risk_controller:
                        self.risk_controller.config = self.config
                    
                    # Log config change
                    if old_mode != new_mode or old_sl != new_sl:
                        self.logger.info(f"🔄 Configuration reloaded:")
                        self.logger.info(f"   Mode: {old_mode} → {new_mode}")
                        self.logger.info(f"   Stop Loss: {old_sl} → {new_sl}")
                        self.logger.info(f"   Max Trades: {self.config.max_open_trades}")
                        self.logger.info(f"   Min Consensus: {self.config.min_consensus_level}")
                    else:
                        self.logger.info(f"🔍 Config reloaded but values unchanged (Mode: {old_mode}, SL: {old_sl})")
                else:
                    # File exists but hasn't changed
                    self.logger.debug(f"🔍 Config file unchanged (mtime: {current_mtime})")
            else:
                # File doesn't exist
                if self.config_file_mtime is None:
                    self.logger.info(f"🔍 Config file not found at {self.config_file} (will be created on first save from UI)")
                else:
                    # File was deleted after existing
                    self.logger.warning(f"⚠️ Config file was deleted: {self.config_file}")
                    self.config_file_mtime = None
                    
        except Exception as e:
            self.logger.error(f"❌ Error checking/reloading config file: {e}", exc_info=True)
    
    def _save_config(self, config: 'TradeConfig'):
        """Save configuration"""
        if not AUTO_TRADER_AVAILABLE:
            return
        
        try:
            data = {
                'trading_mode': config.trading_mode.value,
                'max_open_trades': config.max_open_trades,
                'stop_loss_type': config.stop_loss_type.value,
                'execution_mode': getattr(config, 'execution_mode', ExecutionMode.RECOMMENDED).value,
                'auto_trade_llm': getattr(config, 'auto_trade_llm', True),
                'auto_trade_fisher': getattr(config, 'auto_trade_fisher', True),
                'auto_trade_ft_dmi_ema': getattr(config, 'auto_trade_ft_dmi_ema', True),
                'auto_trade_dmi_ema': getattr(config, 'auto_trade_dmi_ema', True),
                'min_consensus_level': config.min_consensus_level,
                'required_llms': getattr(config, 'required_llms', None) or ['gemini'],
                'base_position_size': config.base_position_size,
                'consensus_multiplier': config.consensus_multiplier,
                'hard_trailing_pips': config.hard_trailing_pips,
                'be_trigger_pips': config.be_trigger_pips,
                'atr_multiplier_low_vol': config.atr_multiplier_low_vol,
                'atr_multiplier_high_vol': config.atr_multiplier_high_vol,
                'max_account_risk_pct': config.max_account_risk_pct,
                'max_daily_loss': config.max_daily_loss,
                'macd_timeframe': getattr(config, 'macd_timeframe', 'H1'),
                'macd_sl_timeframe': getattr(config, 'macd_sl_timeframe', None),
                'dmi_sl_timeframe': getattr(config, 'dmi_sl_timeframe', None),
            }
            
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
    
    def _read_market_state(self) -> Optional[Dict]:
        """Read market state from Trade-Alerts (API first, then file fallback)"""
        # Try API first if configured
        if self.market_state_api_url:
            market_state = self._read_market_state_from_api()
            if market_state:
                return market_state
            # If API fails, fall through to file fallback
        
        # Fallback to file
        return self._read_market_state_from_file()
    
    def _read_market_state_from_api(self) -> Optional[Dict]:
        """Read market state from API endpoint"""
        try:
            # Prepare headers
            headers = {'Content-Type': 'application/json'}
            if self.market_state_api_key:
                headers['X-API-Key'] = self.market_state_api_key
            
            response = requests.get(
                self.market_state_api_url,
                timeout=5,
                headers=headers
            )
            
            if response.status_code == 200:
                market_state = response.json()
                
                # Check if API returned an error message
                if 'error' in market_state:
                    if self.check_count % 10 == 0:  # Every 10 checks (10 minutes)
                        self.logger.warning(
                            f"⚠️ API returned error: {market_state.get('error')}"
                        )
                    return None
                
                # Validate market state structure
                if not isinstance(market_state, dict):
                    self.logger.error(
                        f"❌ Market state from API is not a dictionary: {type(market_state)}"
                    )
                    return None
                
                opportunities_count = len(market_state.get('opportunities', []))
                timestamp = market_state.get('timestamp', 'N/A')
                
                # Check if this is a new market state (timestamp changed)
                is_new_state = timestamp != self.last_market_state_timestamp
                if is_new_state:
                    self.last_market_state_timestamp = timestamp
                    self.logger.info(
                        f"🆕 NEW market state detected from API: {opportunities_count} opportunities "
                        f"(timestamp: {timestamp}, URL: {self.market_state_api_url})"
                    )
                elif opportunities_count > 0:
                    # Log periodically when opportunities exist but state hasn't changed
                    if self.check_count % 5 == 0:
                        self.logger.info(
                            f"📊 Market state checked from API: {opportunities_count} opportunities "
                            f"(timestamp: {timestamp}, no change)"
                        )
                elif self.check_count % 10 == 0:
                    # Log periodically when no opportunities
                    self.logger.info(
                        f"📊 Market state checked from API: 0 opportunities "
                        f"(timestamp: {timestamp})"
                    )
                
                return market_state
            elif response.status_code == 404:
                # Market state not available yet
                if self.check_count % 10 == 0:  # Every 10 checks (10 minutes)
                    self.logger.info(
                        f"ℹ️ Market state not available from API yet (404) - will try file fallback"
                    )
                return None
            elif response.status_code == 401:
                # Unauthorized - API key issue
                if self.check_count % 10 == 0:  # Every 10 checks (10 minutes)
                    self.logger.warning(
                        f"⚠️ API authentication failed (401) - check MARKET_STATE_API_KEY"
                    )
                return None
            else:
                if self.check_count % 10 == 0:  # Every 10 checks (10 minutes)
                    self.logger.warning(
                        f"⚠️ API returned status {response.status_code} for market state "
                        f"(URL: {self.market_state_api_url})"
                    )
                return None
                
        except requests.exceptions.RequestException as e:
            if self.check_count % 10 == 0:  # Every 10 checks (10 minutes)
                self.logger.warning(
                    f"⚠️ Error loading market state from API ({self.market_state_api_url}): {e} "
                    f"- will try file fallback"
                )
            return None
        except Exception as e:
            if self.check_count % 10 == 0:  # Every 10 checks (10 minutes)
                self.logger.warning(
                    f"⚠️ Unexpected error loading market state from API: {e}"
                )
            return None
    
    def _read_market_state_from_file(self) -> Optional[Dict]:
        """Read market state from file (fallback)"""
        try:
            if not os.path.exists(self.market_state_file):
                # Log at WARNING level more frequently so we know if file is missing
                if self.check_count % 5 == 0:  # Every 5 checks (5 minutes)
                    self.logger.warning(
                        f"⚠️ Market state file not found: {self.market_state_file} "
                        f"(check #{self.check_count})"
                    )
                return None
            
            # Check file modification time to detect updates
            file_mtime = os.path.getmtime(self.market_state_file)
            file_was_updated = not hasattr(self, '_last_file_mtime') or file_mtime != self._last_file_mtime
            
            with open(self.market_state_file, 'r') as f:
                market_state = json.load(f)
                
                # Validate market state structure
                if not isinstance(market_state, dict):
                    self.logger.error(
                        f"❌ Market state is not a dictionary: {type(market_state)}"
                    )
                    return None
                
                opportunities_count = len(market_state.get('opportunities', []))
                timestamp = market_state.get('timestamp', 'N/A')
                
                # Check if this is a new market state (timestamp or file mtime changed)
                is_new_state = (timestamp != self.last_market_state_timestamp) or file_was_updated
                if is_new_state:
                    self.last_market_state_timestamp = timestamp
                    self._last_file_mtime = file_mtime
                    self.logger.info(
                        f"🆕 NEW market state detected from file: {opportunities_count} opportunities "
                        f"(file: {self.market_state_file}, timestamp: {timestamp})"
                    )
                elif opportunities_count > 0:
                    # Log periodically when opportunities exist but state hasn't changed
                    if self.check_count % 5 == 0:
                        self.logger.info(
                            f"📊 Market state checked from file: {opportunities_count} opportunities "
                            f"(timestamp: {timestamp}, no change)"
                        )
                elif self.check_count % 10 == 0:
                    # Log periodically when no opportunities
                    self.logger.info(
                        f"📊 Market state checked from file: 0 opportunities "
                        f"(file: {self.market_state_file}, timestamp: {timestamp})"
                    )
                
                return market_state
                
        except json.JSONDecodeError as e:
            self.logger.error(
                f"❌ Invalid JSON in market state file {self.market_state_file}: {e}"
            )
            # Repair: overwrite corrupt file with minimal valid JSON so future reads succeed
            try:
                from datetime import datetime
                repair_state = {
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'global_bias': 'NEUTRAL',
                    'regime': 'UNKNOWN',
                    'approved_pairs': [],
                    'opportunities': [],
                    'fisher_opportunities': [],
                }
                with open(self.market_state_file, 'w') as f:
                    json.dump(repair_state, f, indent=2)
                self.logger.warning(
                    f"🔧 Repaired corrupt market_state.json with minimal valid state "
                    f"(API/Trade-Alerts will repopulate)"
                )
            except Exception as repair_e:
                self.logger.warning(f"Could not repair market_state.json: {repair_e}")
            return None
        except Exception as e:
            self.logger.error(
                f"❌ Error reading market state from {self.market_state_file}: {e}",
                exc_info=True
            )
            return None
    
    def _get_current_prices(self, pairs: List[str]) -> Dict[str, float]:
        """Get current prices from OANDA"""
        prices = {}
        
        for pair in pairs:
            try:
                # Convert pair format: GBP/USD -> GBP_USD for OANDA
                oanda_pair = pair.replace('/', '_').replace('-', '_')
                
                params = {"instruments": oanda_pair}
                req = pricing.PricingInfo(accountID=self.account_id, params=params)
                response = self.oanda_api.request(req)  # Use raw API, not wrapper
                
                if 'prices' in response and len(response['prices']) > 0:
                    price_data = response['prices'][0]
                    bid = float(price_data['bids'][0]['price'])
                    ask = float(price_data['asks'][0]['price'])
                    mid = (bid + ask) / 2
                    prices[pair] = mid
                    
            except Exception as e:
                self.logger.error(
                    f"❌ Error fetching price for {pair} from OANDA: {e}",
                    exc_info=True
                )
        
        return prices
    
    def _get_account_summary(self) -> Dict:
        """Get OANDA account summary"""
        try:
            req = accounts.AccountSummary(accountID=self.account_id)
            response = self.oanda_api.request(req)  # Use raw API, not wrapper
            return response.get('account', {})
        except Exception as e:
            self.logger.error(f"Error fetching account summary: {e}")
            return {}
    
    def _monitor_mode_check(self):
        """Original monitoring behavior (no trading)"""
        # Get account info
        account = self._get_account_summary()
        
        if account:
            balance = float(account.get('balance', 0))
            unrealized_pl = float(account.get('unrealizedPL', 0))
            open_trade_count = int(account.get('openTradeCount', 0))
            
            self.logger.info(
                f"📊 Account: Balance=${balance:.2f}, "
                f"Unrealized P/L=${unrealized_pl:.2f}, "
                f"Open Trades={open_trade_count}"
            )
        
        # Read and display market state
        market_state = self._read_market_state()
        if market_state:
            opportunities = market_state.get('opportunities', [])
            self.logger.info(
                f"🧠 Intelligence: {market_state.get('global_bias')} bias, "
                f"{len(opportunities)} opportunities"
            )
    
    def _auto_trader_mode_check(self):
        """Auto-trader behavior (with execution)"""
        # Read latest market state
        market_state = self._read_market_state()
        
        if not market_state:
            # Log at INFO level more frequently so we know if market state is unavailable
            if self.check_count % 5 == 0:  # Every 5 checks (5 minutes)
                file_exists = os.path.exists(self.market_state_file)
                self.logger.warning(
                    f"⚠️ No market state available (check #{self.check_count}) - "
                    f"File exists: {file_exists}, Path: {self.market_state_file}"
                )
            return
        
        # Update our state
        self.current_market_state = market_state
        self.llm_weights = market_state.get('llm_weights', {})
        
        # Inject FT-DMI-EMA opportunities when enabled (two-stage: setup ready + 15m trigger)
        self._inject_ft_dmi_ema_opportunities(market_state)
        # Inject DMI-EMA opportunities (1D/4H/1H DMI+EMA alignment; same FT_DMI_EMA_SIGNALS_ENABLED)
        self._inject_dmi_ema_opportunities(market_state)
        
        opportunities_count = len(market_state.get('opportunities', []))
        
        # Log market context periodically
        if self.check_count % 10 == 0:
            self.logger.info(
                f"🧠 Market: {market_state.get('global_bias')} bias, "
                f"{market_state.get('regime')} volatility, "
                f"{opportunities_count} opportunities"
            )
        
        # CRITICAL: Sync with OANDA FIRST to detect trades opened manually or externally
        # This must happen before checking opportunities to ensure we have accurate trade count
        # and to detect trades that exist in OANDA but aren't in our memory
        # Pass market_state so excess trades can be closed based on relevance
        self.position_manager.sync_with_oanda(market_state)
        
        # Always check for new opportunities (logging is handled inside)
        self._check_new_opportunities(market_state)
        
        # Check Fisher opportunities (SEMI_AUTO/MANUAL only - never in AUTO)
        self._check_fisher_opportunities(market_state)
        
        # Check FT-DMI-EMA opportunities (SEMI_AUTO/MANUAL only; trigger when 15m Fisher met)
        self._check_ft_dmi_ema_opportunities(market_state)
        # Check DMI-EMA opportunities
        self._check_dmi_ema_opportunities(market_state)
        
        # Check pending Fisher signals for H1/M15 crossover activation (SEMI_AUTO/MANUAL only)
        self._check_fisher_activation_signals(market_state)
        
        # Check pending FT-DMI-EMA signals for 15m trigger activation (SEMI_AUTO/MANUAL only)
        self._check_ft_dmi_ema_activation_signals(market_state)
        # Check pending DMI-EMA signals for 15m trigger activation
        self._check_dmi_ema_activation_signals(market_state)
        
        # Check for MACD triggers on pending HYBRID orders (every 5 minutes)
        self._check_hybrid_macd_triggers(market_state)
        
        # Monitor existing positions
        self._monitor_positions(market_state)
        
        # Log active trades summary
        if self.position_manager.active_trades:
            summary = self.position_manager.get_active_trades_summary()
            self.logger.info(
                f"📈 Active: {summary['total_trades']}/{self.config.max_open_trades}, "
                f"Unrealized: {summary['total_unrealized_pnl']:.1f} pips"
            )
    
    def _check_new_opportunities(self, market_state: Dict):
        """Check for new trading opportunities"""
        # AUTO mode: only process LLM opportunities if auto_trade_llm is enabled
        if self.config.trading_mode == TradingMode.AUTO and not getattr(self.config, 'auto_trade_llm', True):
            return
        opportunities = market_state.get('opportunities', [])
        
        if not opportunities:
            # Log at INFO level periodically when no opportunities are found
            if self.check_count % 20 == 0:  # Every 20 checks (20 minutes)
                self.logger.info(
                    f"ℹ️ No opportunities in market state (check #{self.check_count})"
                )
            return
        
        # NEW: Review pending trades and replace with better entry prices
        self._review_and_replace_pending_trades(opportunities, market_state)
        
        # Log opportunity check summary
        # Always log when we have opportunities (important for debugging)
        # Safely get required_llms string
        try:
            if hasattr(self.config, 'required_llms') and self.config.required_llms:
                required_llms_str = ', '.join(self.config.required_llms)
            else:
                required_llms_str = 'None'
        except (AttributeError, TypeError):
            required_llms_str = 'None'
        # SEMI_AUTO: log how many opportunities are enabled (engine loads from config-api, same as UI)
        enabled_llm_count = None
        if self.config.trading_mode == TradingMode.SEMI_AUTO and opportunities:
            try:
                from src.execution.semi_auto_controller import SemiAutoController
                sac = SemiAutoController()
                # Use stable key (pair_direction) so count matches UI; market-state opp.id can differ
                enabled_llm_count = sum(1 for o in opportunities if sac.is_enabled(get_stable_opportunity_id(o, source='LLM') if get_stable_opportunity_id else _stable_opp_id_fallback(o)))
                self.logger.info(
                    f"📋 SEMI_AUTO: {enabled_llm_count} enabled LLM opportunity(ies) (of {len(opportunities)} total)"
                )
            except Exception as e:
                self.logger.debug(f"SemiAutoController check: {e}")
        
        self.logger.info(
            f"🔍 Checking {len(opportunities)} opportunities "
            f"(Min Consensus: {self.config.min_consensus_level}, "
            f"Required LLMs: {required_llms_str})"
        )
        
        # Track processing results
        processed_count = 0
        blocked_duplicate = 0
        skipped_validation = 0
        skipped_stale = 0
        skipped_max_trades = 0
        skipped_no_price = 0
        skipped_macd_wait = 0
        errors = 0
        
        for opp in opportunities:
            try:
                opp['source'] = opp.get('source') or 'LLM'
                pair = opp.get('pair', '')
                direction = opp.get('direction', '').upper()
                
                # SEMI_AUTO: Only process opportunities explicitly enabled in the UI; merge per-opportunity config
                semi_auto = None
                stable_opp_id = get_stable_opportunity_id(opp, source='LLM') if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
                if self.config.trading_mode == TradingMode.SEMI_AUTO:
                    try:
                        from src.execution.semi_auto_controller import SemiAutoController
                        semi_auto = SemiAutoController()
                        if not semi_auto.is_enabled(stable_opp_id):
                            continue
                        # Merge semi-auto per-opportunity config so enforcer uses selected mode (FT crossover, etc.)
                        saved = semi_auto.get_opportunity_config(stable_opp_id)
                        if saved:
                            ec = dict(opp.get('execution_config') or {})
                            ec.update({k: v for k, v in saved.items() if k in ('mode', 'max_runs', 'sl_type') and v is not None})
                            opp['execution_config'] = ec
                    except Exception as e:
                        self.logger.warning(f"⚠️ SemiAutoController unavailable for LLM: {e} - skipping in SEMI_AUTO")
                        continue
                
                # CRITICAL: Check cooldown first (prevents immediate reopening after duplicate closure)
                if self.position_manager.is_pair_in_cooldown(pair):
                    self.logger.warning(
                        f"⏸️ Skipped {pair} {direction} - pair is in cooldown period "
                        f"after being closed as duplicate (prevents immediate reopening)"
                    )
                    blocked_duplicate += 1
                    continue
                
                # STRICT RULE: Check if already have ANY order for this pair (regardless of direction)
                # Only ONE order per pair is allowed - this is a RED FLAG if violated
                # This checks BOTH in-memory active_trades AND OANDA directly
                # This is critical to prevent duplicates after service restarts
                already_open = self.position_manager.has_existing_position(pair, direction)
                
                if already_open:
                    # RED FLAG log throttle: first block per (pair, direction) in window at ERROR, repeats at DEBUG (consol-recommend2 Phase 1.2)
                    key = (pair, direction)
                    now_ts = time.time()
                    last_ts = self._red_flag_duplicate_last_logged.get(key, 0)
                    if now_ts - last_ts >= self._red_flag_duplicate_window_seconds:
                        self.logger.error(
                            f"🚨 RED FLAG: BLOCKED DUPLICATE - {pair} {direction} - "
                            f"already have an order for this pair (ONLY ONE ORDER PER PAIR ALLOWED)"
                        )
                        self._red_flag_duplicate_last_logged[key] = now_ts
                    else:
                        self.logger.debug(
                            f"🚨 RED FLAG: BLOCKED DUPLICATE - {pair} {direction} - "
                            f"already have an order for this pair (throttled)"
                        )
                    blocked_duplicate += 1
                    continue
                
                # Check max trades limit BEFORE validating opportunity (save processing)
                can_open, reason = self.position_manager.can_open_new_trade()
                if not can_open:
                    # Always log when max trades limit is reached (important for debugging)
                    self.logger.info(f"⏭️ Skipped {pair} {direction} - {reason}")
                    skipped_max_trades += 1
                    
                    # RL LOGGING: Log non-executed opportunity for simulation (max trades limit)
                    try:
                        rl_db = self._get_rl_db()
                        signal_id = rl_db.log_signal(
                            pair=pair,
                            direction=direction,
                            entry_price=opp.get('entry', 0.0),
                            stop_loss=opp.get('stop_loss', 0.0),
                            take_profit=opp.get('exit'),
                            llm_sources=opp.get('llm_sources', []),
                            consensus_level=opp.get('consensus_level', 1),
                            rationale=opp.get('recommendation', ''),
                            confidence=opp.get('confidence', 0.5),
                            executed=False,
                            trade_id=None,
                            position_size=0.0
                        )
                        self.logger.debug(f"📊 RL: Logged simulated opportunity {signal_id} for {pair} {direction} (max trades limit)")
                    except Exception as e:
                        self.logger.debug(f"Could not log opportunity to RL database: {e}")
                    
                    continue
                
                # Validate opportunity (consensus level, required LLMs, etc.)
                consensus = opp.get('consensus_level', 1)
                llm_sources = opp.get('llm_sources', [])
                is_valid, reason = self.risk_controller.validate_opportunity(
                    opp, self.llm_weights
                )
                
                if not is_valid:
                    # Always log when opportunities are skipped due to validation (important for debugging)
                    self.logger.info(
                        f"⏭️ Skipped {pair} {direction} @ {opp.get('entry', 'N/A')}: {reason} "
                        f"(consensus: {consensus}, sources: {llm_sources})"
                    )
                    skipped_validation += 1
                    
                    # RL LOGGING: Log non-executed opportunity for simulation
                    try:
                        rl_db = self._get_rl_db()
                        signal_id = rl_db.log_signal(
                            pair=pair,
                            direction=direction,
                            entry_price=opp.get('entry', 0.0),
                            stop_loss=opp.get('stop_loss', 0.0),
                            take_profit=opp.get('exit'),
                            llm_sources=llm_sources,
                            consensus_level=consensus,
                            rationale=opp.get('recommendation', ''),
                            confidence=opp.get('confidence', 0.5),
                            executed=False,  # This is a simulated opportunity
                            trade_id=None,
                            position_size=0.0
                        )
                        self.logger.debug(f"📊 RL: Logged simulated opportunity {signal_id} for {pair} {direction} (skipped: {reason})")
                    except Exception as e:
                        self.logger.debug(f"Could not log opportunity to RL database: {e}")
                    
                    continue
                
                # Get current market price
                pairs = [pair]
                current_prices = self._get_current_prices(pairs)
                current_price = current_prices.get(pair)
                
                if not current_price:
                    self.logger.warning(
                        f"⚠️ No current price for {pair} - cannot execute trade "
                        f"(OANDA API may be unavailable or pair not found)"
                    )
                    skipped_no_price += 1
                    continue
                
                # Per-opportunity execution mode (used for staleness skip and crossover branch below)
                per_opp_mode = (opp.get('execution_config') or {}).get('mode')
                
                # CRITICAL: Validate that opportunity's current_price is not stale (unless trigger is crossover)
                # For FT/DMI crossover modes the trigger is the signal, not price; skip price staleness reject.
                opp_current_price = opp.get('current_price')
                if opp_current_price and opp_current_price > 0 and per_opp_mode not in EXECUTION_MODES_TRIGGER_IS_CROSSOVER:
                    pip_size = 0.01 if 'JPY' in pair else 0.0001
                    price_diff = abs(current_price - opp_current_price)
                    price_diff_pips = price_diff / pip_size
                    price_diff_percent = abs((current_price - opp_current_price) / opp_current_price * 100) if opp_current_price else 0
                    
                    # Threshold: 50 pips or 0.5% for INTRADAY, 200 pips or 2% for SWING
                    timeframe = opp.get('timeframe', 'INTRADAY')
                    if timeframe == 'SWING':
                        max_pips = 200.0
                        max_percent = 2.0
                    else:
                        max_pips = 50.0
                        max_percent = 0.5
                    
                    if price_diff_pips > max_pips or price_diff_percent > max_percent:
                        # Throttle: first per (pair, direction) per window at WARNING, rest at DEBUG (suggestions cursor3 §5.5)
                        key = (pair, direction)
                        now_ts = time.time()
                        last_ts = self._stale_reject_log_last.get(key, 0)
                        if now_ts - last_ts >= self._stale_reject_log_window_seconds:
                            self.logger.warning(
                                f"🚫 REJECTING STALE OPPORTUNITY: {pair} {direction} - "
                                f"stored current_price ({opp_current_price:.5f}) is {price_diff_pips:.1f} pips "
                                f"({price_diff_percent:.2f}%) away from live price ({current_price:.5f}). "
                                f"Recommendation is based on outdated market data (threshold: {max_pips} pips / {max_percent}%). "
                                f"Entry: {opp.get('entry', 'N/A')}, Stop Loss: {opp.get('stop_loss', 'N/A')}"
                            )
                            self._stale_reject_log_last[key] = now_ts
                        else:
                            self.logger.debug(
                                f"🚫 REJECTING STALE OPPORTUNITY (throttled): {pair} {direction} - "
                                f"stored price {opp_current_price:.5f} vs live {current_price:.5f} "
                                f"({price_diff_pips:.1f} pips) - threshold {max_pips} pips / {max_percent}%"
                            )
                        skipped_stale += 1
                        continue  # Skip this opportunity - it's based on stale data
                    elif price_diff_pips > 10 or price_diff_percent > 0.1:
                        # Price is slightly stale but within tolerance - log info but allow (consol-recommend3 Phase 1.3: throttle)
                        key = (pair, direction)
                        now_ts = time.time()
                        last_ts = self._stale_price_log_last.get(key, 0)
                        if now_ts - last_ts >= self._stale_price_log_window_seconds:
                            self.logger.info(
                                f"⚠️ Opportunity {pair} has slightly stale current_price: "
                                f"{opp_current_price:.5f} vs live {current_price:.5f} "
                                f"({price_diff_pips:.1f} pips diff) - proceeding with live price"
                            )
                            self._stale_price_log_last[key] = now_ts
                        else:
                            self.logger.debug(
                                f"⚠️ Opportunity {pair} slightly stale current_price "
                                f"{opp_current_price:.5f} vs live {current_price:.5f} ({price_diff_pips:.1f} pips) - proceeding (throttled)"
                            )
                
                # Semi-auto FT or DMI crossover (1h/15m): pass to enforcer; it returns WAIT_SIGNAL and stores pending
                if per_opp_mode in EXECUTION_MODES_TRIGGER_IS_CROSSOVER:
                    opp_with_order = {**opp, 'current_price': current_price}
                    self._maybe_reset_run_count_and_open_trade(opp_with_order, market_state)
                    label = 'FT' if per_opp_mode.startswith('FISHER_') else 'DMI'
                    tf = '1h' if 'H1' in per_opp_mode else '15m'
                    self.logger.info(
                        f"⏳ Stored {pair} {direction} for {label} crossover ({tf}) - will execute when crossover detected"
                    )
                    continue
                
                # Check execution mode: use per-opportunity mode when in SEMI_AUTO and set; else global config
                execution_mode = getattr(self.config, 'execution_mode', ExecutionMode.RECOMMENDED)
                if self.config.trading_mode == TradingMode.SEMI_AUTO and per_opp_mode in ('MARKET', 'RECOMMENDED', 'MACD_CROSSOVER', 'HYBRID', 'DMI_H1_CROSSOVER', 'DMI_M15_CROSSOVER'):
                    try:
                        execution_mode = ExecutionMode(per_opp_mode)
                    except ValueError:
                        pass
                
                if execution_mode == ExecutionMode.HYBRID:
                    # HYBRID mode: Place pending order at recommended price AND check MACD crossover
                    recommended_entry = opp.get('entry', current_price)
                    pip_size = 0.01 if 'JPY' in pair else 0.0001
                    entry_diff_pips = abs(current_price - recommended_entry) / pip_size
                    
                    # Determine order type based on current price vs recommended entry
                    if direction in ['LONG', 'BUY']:
                        if current_price <= recommended_entry:
                            order_type = 'LIMIT'  # Buy at or below recommended price
                        else:
                            order_type = 'STOP'  # Buy when price rises to recommended price
                    else:  # SHORT or SELL
                        if current_price >= recommended_entry:
                            order_type = 'LIMIT'  # Sell at or above recommended price
                        else:
                            order_type = 'STOP'  # Sell when price falls to recommended price
                    
                    entry_price = recommended_entry
                    self.logger.info(
                        f"🎯 HYBRID MODE: Placing {order_type} order @ {recommended_entry} "
                        f"(current: {current_price}, diff: {entry_diff_pips:.1f} pips) "
                        f"AND monitoring MACD crossover - whichever triggers first, Consensus: {consensus}/3"
                    )
                elif execution_mode == ExecutionMode.MACD_CROSSOVER:
                    # MACD_CROSSOVER mode: Wait for MACD crossover signal
                    should_trigger, reason = self.position_manager.check_macd_crossover(
                        pair, direction, self.oanda_client
                    )
                    
                    if not should_trigger:
                        # Log reason periodically to avoid spam
                        if self.check_count % 12 == 0:  # Every 12 checks (12 minutes)
                            self.logger.info(
                                f"⏳ MACD_CROSSOVER: {pair} {direction} - {reason or 'waiting for crossover'}"
                            )
                        skipped_macd_wait += 1
                        continue  # Skip this opportunity - wait for crossover
                    
                    # Crossover detected - execute immediately at market price
                    order_type = 'MARKET'
                    entry_price = current_price
                    recommended_entry = current_price
                    self.logger.info(
                        f"🎯 MACD CROSSOVER TRIGGERED: {pair} {direction} @ {current_price} "
                        f"(MACD signal: {reason}), Consensus: {consensus}/3"
                    )
                elif execution_mode == ExecutionMode.MARKET:
                    # Execute immediately at current market price
                    order_type = 'MARKET'
                    entry_price = current_price
                    recommended_entry = current_price  # Set for logging consistency
                    self.logger.info(
                        f"🎯 Placing MARKET order: {pair} {direction} @ {current_price} "
                        f"(market price execution), Consensus: {consensus}/3"
                    )
                else:
                    # RECOMMENDED mode: Place LIMIT/STOP order at recommended entry price
                    recommended_entry = opp.get('entry', current_price)
                    pip_size = 0.01 if 'JPY' in pair else 0.0001
                    entry_diff_pips = abs(current_price - recommended_entry) / pip_size
                    
                    # Determine order type based on current price vs recommended entry
                    # LONG: LIMIT if price below entry (buy at or below), STOP if price above entry (buy when rises)
                    # SHORT: LIMIT if price above entry (sell at or above), STOP if price below entry (sell when falls)
                    if direction in ['LONG', 'BUY']:
                        if current_price <= recommended_entry:
                            order_type = 'LIMIT'  # Buy at or below recommended price
                        else:
                            order_type = 'STOP'  # Buy when price rises to recommended price
                    else:  # SHORT or SELL
                        if current_price >= recommended_entry:
                            order_type = 'LIMIT'  # Sell at or above recommended price
                        else:
                            order_type = 'STOP'  # Sell when price falls to recommended price
                    
                    entry_price = recommended_entry
                    self.logger.info(
                        f"🎯 Placing {order_type} order: {pair} {direction} @ {recommended_entry} "
                        f"(current: {current_price}, diff: {entry_diff_pips:.1f} pips), "
                        f"Consensus: {consensus}/3"
                    )
                
                # Update opportunity with order type and entry price
                opp_with_order = opp.copy()
                opp_with_order['entry'] = entry_price  # Use market price or recommended entry
                opp_with_order['order_type'] = order_type  # Store order type (MARKET, LIMIT, or STOP)
                opp_with_order['current_price'] = current_price  # Store current price for reference
                # When per-opportunity SL is STRUCTURE_ATR_STAGED (LLM/Fisher), compute structure+ATR stop
                self._ensure_structure_atr_stop_if_needed(opp_with_order)
                # Attempt to open trade with LIMIT or STOP order
                trade = self._maybe_reset_run_count_and_open_trade(opp_with_order, market_state)
                
                if trade:
                    processed_count += 1
                    if self.config.trading_mode == TradingMode.AUTO:
                        self.logger.info(
                            f"✅ Placed {order_type} order: {pair} {direction} @ {recommended_entry} "
                            f"(current: {current_price})"
                        )
                    else:
                        self.logger.info(f"📋 Ready for approval in UI")
                else:
                    # Trade not opened: include reason in same log line (consol-recommend2 Phase 1.3)
                    reason = getattr(self.position_manager, '_last_reject_reason', None) or 'unknown'
                    self.logger.warning(
                        f"⚠️ Trade not opened for {pair} {direction}: reason={reason}"
                    )
                
            except Exception as e:
                errors += 1
                self.logger.error(
                    f"❌ Error checking opportunity {opp.get('pair', 'UNKNOWN')} {opp.get('direction', 'UNKNOWN')}: {e}",
                    exc_info=True
                )
        
        # Log summary of opportunity processing
        if len(opportunities) > 0:
            summary_parts = []
            if processed_count > 0:
                summary_parts.append(f"{processed_count} processed")
            if blocked_duplicate > 0:
                summary_parts.append(f"{blocked_duplicate} duplicates")
            if skipped_validation > 0:
                summary_parts.append(f"{skipped_validation} failed validation")
            if skipped_stale > 0:
                summary_parts.append(f"{skipped_stale} stale (outdated current_price)")
            if skipped_max_trades > 0:
                summary_parts.append(f"{skipped_max_trades} max trades limit")
            if skipped_no_price > 0:
                summary_parts.append(f"{skipped_no_price} no price data")
            if skipped_macd_wait > 0:
                summary_parts.append(f"{skipped_macd_wait} waiting for MACD")
            if errors > 0:
                summary_parts.append(f"{errors} errors")
            
            if summary_parts:
                self.logger.info(
                    f"📊 Opportunity processing summary: {', '.join(summary_parts)} "
                    f"(total: {len(opportunities)})"
                )
    
    def _check_fisher_opportunities(self, market_state: Dict):
        """
        Check and process Fisher opportunities (SEMI_AUTO/MANUAL only).
        Fisher opportunities NEVER execute in AUTO mode.
        In SEMI_AUTO, only process opportunities explicitly enabled in the UI.
        """
        fisher_opps = market_state.get('fisher_opportunities', [])
        if not fisher_opps:
            return
        
        # CRITICAL: Fisher never in full AUTO
        if self.config.trading_mode == TradingMode.AUTO:
            if self.check_count % 20 == 0:
                self.logger.info(
                    f"ℹ️ Fisher: {len(fisher_opps)} opportunity(ies) skipped (AUTO mode - Fisher never executes)"
                )
            return
        
        # SEMI_AUTO: only process explicitly enabled opportunities (config from API so engine sees UI choices)
        semi_auto = None
        total_fisher = len(fisher_opps)
        if self.config.trading_mode == TradingMode.SEMI_AUTO:
            try:
                from src.execution.semi_auto_controller import SemiAutoController
                semi_auto = SemiAutoController()
                fisher_opps = [o for o in fisher_opps if semi_auto.is_enabled(get_stable_opportunity_id(o, source='Fisher') if get_stable_opportunity_id else _stable_opp_id_fallback(o))]
                enabled_count = len(fisher_opps)
                self.logger.info(f"📋 SEMI_AUTO: {enabled_count} enabled Fisher opportunity(ies) (of {total_fisher} total)")
                if not fisher_opps:
                    return
            except Exception as e:
                self.logger.warning(f"⚠️ SemiAutoController unavailable: {e} - skipping Fisher in SEMI_AUTO")
                return
        
        self.logger.info(f"🎯 Checking {len(fisher_opps)} Fisher opportunity(ies) (mode: {self.config.trading_mode.value})")
        
        for opp in fisher_opps:
            try:
                opp['source'] = opp.get('source') or 'Fisher'
                pair = opp.get('pair', '')
                direction = opp.get('direction', '').upper()
                opp_id = get_stable_opportunity_id(opp, source='Fisher') if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
                trigger = (opp.get('fisher_config') or {}).get('activation_trigger', (opp.get('execution_config') or {}).get('mode', 'N/A'))
                self.logger.info(f"🎯 Fisher {pair} {direction} (trigger: {trigger})")
                
                if self.position_manager.is_pair_in_cooldown(pair):
                    self.logger.warning(f"⏸️ Fisher {pair} {direction} - pair in cooldown")
                    continue
                
                if self.position_manager.has_existing_position(pair, direction):
                    self.logger.warning(f"🚫 Fisher {pair} {direction} - already have position")
                    continue
                
                can_open, reason = self.position_manager.can_open_new_trade()
                if not can_open:
                    self.logger.info(f"⏭️ Fisher {pair} {direction} - {reason}")
                    continue
                
                current_prices = self._get_current_prices([pair])
                current_price = current_prices.get(pair)
                if not current_price:
                    self.logger.warning(f"⚠️ Fisher {pair} - no price data")
                    continue
                
                # Merge saved SemiAuto config (mode, sl_type, max_runs) into opp (use stable key so mode persists)
                if semi_auto:
                    stable_opp_id = get_stable_opportunity_id(opp, source='Fisher') if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
                    saved = semi_auto.get_opportunity_config(stable_opp_id)
                    if saved:
                        ec = dict(opp.get('execution_config') or {})
                        ec.update({k: v for k, v in saved.items() if k in ('mode', 'max_runs', 'sl_type') and v is not None})
                        opp = {**opp, 'execution_config': ec}
                        fc = dict(opp.get('fisher_config') or {})
                        if saved.get('sl_type'):
                            fc['sl_type'] = saved['sl_type']
                        # Map UI mode to fisher_config.activation_trigger for enforcer
                        mode = saved.get('mode') or ec.get('mode')
                        if mode:
                            _mode_to_trigger = {
                                'FISHER_M15_CROSSOVER': 'M15_CROSSOVER',
                                'FISHER_H1_CROSSOVER': 'H1_CROSSOVER',
                                'DMI_M15_CROSSOVER': 'DMI_M15_CROSSOVER',
                                'DMI_H1_CROSSOVER': 'DMI_H1_CROSSOVER',
                                'IMMEDIATE_MARKET': 'IMMEDIATE',
                                'RECOMMENDED_PRICE': 'RECOMMENDED_PRICE',
                                'MANUAL': 'MANUAL',
                            }
                            fc['activation_trigger'] = _mode_to_trigger.get(mode, fc.get('activation_trigger', 'MANUAL'))
                        opp['fisher_config'] = fc
                
                # Determine order type (RECOMMENDED-style: LIMIT/STOP at entry)
                entry_price = opp.get('entry', current_price)
                per_opp_mode = (opp.get('execution_config') or {}).get('mode', '') or (opp.get('fisher_config') or {}).get('activation_trigger', '')
                if 'IMMEDIATE' in str(per_opp_mode).upper() or 'MARKET' in str(per_opp_mode).upper():
                    order_type = 'MARKET'
                    entry_price = current_price
                else:
                    pip_size = 0.01 if 'JPY' in pair else 0.0001
                    if direction in ['LONG', 'BUY']:
                        order_type = 'LIMIT' if entry_price < current_price else 'STOP'
                    else:
                        order_type = 'LIMIT' if entry_price > current_price else 'STOP'
                
                opp_with_order = opp.copy()
                opp_with_order['entry'] = entry_price
                opp_with_order['order_type'] = order_type
                opp_with_order['current_price'] = current_price
                if 'exit' not in opp_with_order and opp_with_order.get('take_profit'):
                    opp_with_order['exit'] = opp_with_order['take_profit']
                
                trade = self._maybe_reset_run_count_and_open_trade(opp_with_order, market_state)
                if trade:
                    self.logger.info(f"✅ Fisher {pair} {direction} @ {entry_price} - {'ready for approval' if self.config.trading_mode == TradingMode.MANUAL else 'order placed'}")
                    
            except Exception as e:
                self.logger.error(f"❌ Fisher opportunity error {opp.get('pair', '?')}: {e}", exc_info=True)
    
    def _inject_ft_dmi_ema_opportunities(self, market_state: Dict):
        """Populate market_state['ft_dmi_ema_opportunities'] only in SEMI_AUTO/MANUAL (two-stage: setup ready + 15m trigger). In AUTO, no list is generated; trades are evaluated and opened in _check_ft_dmi_ema_opportunities."""
        if os.getenv("FT_DMI_EMA_SIGNALS_ENABLED", "false").lower() not in ("true", "1", "yes"):
            market_state["ft_dmi_ema_opportunities"] = []
            return
        # AUTO mode: do not build opportunity list; _check_ft_dmi_ema_opportunities will evaluate and open automatically (with max-trade cap).
        if self.config.trading_mode == TradingMode.AUTO:
            market_state["ft_dmi_ema_opportunities"] = []
            if getattr(self, "market_state_file", None) and os.path.exists(self.market_state_file):
                try:
                    with open(self.market_state_file, "r") as f:
                        on_disk = json.load(f)
                    on_disk["ft_dmi_ema_opportunities"] = []
                    with open(self.market_state_file, "w") as f:
                        json.dump(on_disk, f, indent=2)
                except Exception as e:
                    self.logger.debug(f"Could not clear ft_dmi_ema_opportunities on disk: {e}")
            try:
                from src.integration.fisher_market_bridge import post_ft_dmi_ema_to_api
                post_ft_dmi_ema_to_api([])
            except Exception as e:
                self.logger.debug(f"Could not POST empty FT-DMI-EMA to API: {e}")
            return
        try:
            from src.ft_dmi_ema import (
                get_setup_status,
                fetch_ft_dmi_ema_dataframes,
                InstrumentConfig as FTInstrumentConfig,
            )
            from src.ft_dmi_ema.candle_adapter import pair_to_oanda, oanda_to_pair
        except ImportError as e:
            self.logger.warning(f"FT-DMI-EMA module not available: {e}")
            market_state["ft_dmi_ema_opportunities"] = []
            return
        pairs = FTInstrumentConfig.get_monitored_pairs()
        opportunities = []
        for pair_key in pairs:
            try:
                oanda_instrument = pair_to_oanda(pair_key) if "/" in pair_key or "-" in pair_key else pair_key
                if getattr(self, "ft_candle_fetcher", None):
                    data_15m, data_1h, data_4h = self.ft_candle_fetcher.fetch_multi_timeframe(
                        oanda_instrument, granularities=["M15", "H1", "H4"], count=500
                    )
                else:
                    data_15m, data_1h, data_4h = fetch_ft_dmi_ema_dataframes(
                        lambda inst, gran, count: self.oanda_client.get_candles(inst, gran, count),
                        oanda_instrument,
                    )
                if data_15m is None or data_1h is None or data_4h is None:
                    continue
                price_data = self.oanda_client.get_current_price(oanda_instrument)
                if not price_data:
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
                    opportunities.append({
                        "id": f"FT_DMI_EMA_{pair_display}_LONG",
                        "pair": pair_display,
                        "direction": "LONG",
                        "entry": current_price,
                        "current_price": current_price,
                        "source": "FT_DMI_EMA",
                        "ft_15m_trigger_met": status.get("long_trigger_met", False),
                        "reason": "Setup ready: 4H bias + 1H confirmation; trigger when 15m Fisher bullish crossover",
                        "execution_config": {"mode": "FISHER_M15_TRIGGER"},
                    })
                if status.get("short_setup_ready"):
                    opportunities.append({
                        "id": f"FT_DMI_EMA_{pair_display}_SHORT",
                        "pair": pair_display,
                        "direction": "SHORT",
                        "entry": current_price,
                        "current_price": current_price,
                        "source": "FT_DMI_EMA",
                        "ft_15m_trigger_met": status.get("short_trigger_met", False),
                        "reason": "Setup ready: 4H bias + 1H confirmation; trigger when 15m Fisher bearish crossover",
                        "execution_config": {"mode": "FISHER_M15_TRIGGER"},
                    })
            except Exception as e:
                self.logger.debug(f"FT-DMI-EMA signal for {pair_key}: {e}")
        # Optional merge: keep enabled FT-DMI-EMA opportunities from API that we didn't compute this run (e.g. candle fetch failed)
        existing = market_state.get("ft_dmi_ema_opportunities", [])
        if existing and self.config.trading_mode == TradingMode.SEMI_AUTO:
            try:
                from src.execution.semi_auto_controller import SemiAutoController
                semi_auto = SemiAutoController()
            except Exception:
                semi_auto = None
            if semi_auto:
                try:
                    def _norm_p(p):
                        return (p or "").strip().replace("_", "/").upper()
                    def _norm_d(d):
                        d = (d or "").upper()
                        return "LONG" if d in ("BUY", "LONG") else "SHORT" if d in ("SELL", "SHORT") else d
                    computed_keys = {(_norm_p(o.get("pair")), _norm_d(o.get("direction"))) for o in opportunities}
                    merged = 0
                    for opp in existing:
                        if opp.get("source") != "FT_DMI_EMA":
                            continue
                        key = (_norm_p(opp.get("pair")), _norm_d(opp.get("direction")))
                        if key in computed_keys:
                            continue
                        opp_id = get_stable_opportunity_id(opp, source='FT_DMI_EMA') if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
                        if not semi_auto.is_enabled(opp_id):
                            continue
                        opportunities.append(dict(opp))
                        merged += 1
                    if merged > 0:
                        self.logger.info(
                            f"FT-DMI-EMA: merged {merged} enabled opportunity(ies) from API (not in this run's computed list)"
                        )
                except Exception as e:
                    self.logger.debug(f"FT-DMI-EMA merge from API: {e}")
        market_state["ft_dmi_ema_opportunities"] = opportunities
        if opportunities and self.check_count % 10 == 0:
            self.logger.info(f"FT-DMI-EMA: {len(opportunities)} opportunity(ies) (trigger met: {sum(1 for o in opportunities if o.get('ft_15m_trigger_met'))})")
        # Persist to file so UI can show and enable FT-DMI-EMA opportunities (read-modify-write)
        if getattr(self, "market_state_file", None) and os.path.exists(self.market_state_file):
            try:
                with open(self.market_state_file, "r") as f:
                    on_disk = json.load(f)
                on_disk["ft_dmi_ema_opportunities"] = opportunities
                on_disk["ft_dmi_ema_last_updated"] = datetime.utcnow().isoformat()
                with open(self.market_state_file, "w") as f:
                    json.dump(on_disk, f, indent=2)
            except Exception as e:
                self.logger.debug(f"Could not write ft_dmi_ema_opportunities to market_state file: {e}")
        # POST to market-state-api so UI (which loads from API) can show FT-DMI-EMA opportunities
        if self.market_state_api_url:
            try:
                from src.integration.fisher_market_bridge import post_ft_dmi_ema_to_api
                n = len(opportunities)
                if n > 0 or self.check_count % 10 == 0:
                    self.logger.info("FT-DMI-EMA: POSTing %s opportunity(ies) to market-state-api", n)
                ok = post_ft_dmi_ema_to_api(opportunities)
                if ok:
                    if n > 0:
                        self.logger.info("FT-DMI-EMA: POSTed %s opportunity(ies) to market-state-api", n)
                else:
                    self.logger.debug("FT-DMI-EMA: POST to market-state-api returned non-OK")
            except Exception as e:
                self.logger.warning("Could not POST FT-DMI-EMA opportunities to market-state-api: %s", e)
    
    def _inject_dmi_ema_opportunities(self, market_state: Dict):
        """Populate market_state['dmi_ema_opportunities'] when FT_DMI_EMA_SIGNALS_ENABLED (same switch as FT-DMI-EMA). 1D/4H/1H DMI+EMA alignment; confidence flags only."""
        if os.getenv("FT_DMI_EMA_SIGNALS_ENABLED", "false").lower() not in ("true", "1", "yes"):
            market_state["dmi_ema_opportunities"] = []
            return
        if self.config.trading_mode == TradingMode.AUTO:
            market_state["dmi_ema_opportunities"] = []
            if getattr(self, "market_state_file", None) and os.path.exists(self.market_state_file):
                try:
                    with open(self.market_state_file, "r") as f:
                        on_disk = json.load(f)
                    on_disk["dmi_ema_opportunities"] = []
                    with open(self.market_state_file, "w") as f:
                        json.dump(on_disk, f, indent=2)
                except Exception as e:
                    self.logger.debug(f"Could not clear dmi_ema_opportunities on disk: {e}")
            try:
                from src.integration.fisher_market_bridge import post_ft_dmi_ema_to_api
                post_ft_dmi_ema_to_api([], dmi_ema_opportunities=[])
            except Exception as e:
                self.logger.debug(f"Could not POST empty DMI-EMA to API: {e}")
            return
        try:
            from src.ft_dmi_ema import get_dmi_ema_setup_status, fetch_dmi_ema_dataframes
            from src.ft_dmi_ema import InstrumentConfig as FTInstrumentConfig
            from src.ft_dmi_ema.candle_adapter import pair_to_oanda, oanda_to_pair
        except ImportError as e:
            self.logger.warning(f"DMI-EMA module not available: {e}")
            market_state["dmi_ema_opportunities"] = []
            return
        pairs = FTInstrumentConfig.get_monitored_pairs()
        opportunities = []
        for pair_key in pairs:
            try:
                oanda_instrument = pair_to_oanda(pair_key) if "/" in pair_key or "-" in pair_key else pair_key
                if getattr(self, "ft_candle_fetcher", None):
                    get_candles = lambda inst, gran, count: self.ft_candle_fetcher.get_candles(inst, gran, count)
                else:
                    get_candles = lambda inst, gran, count: self.oanda_client.get_candles(inst, gran, count)
                data_1d, data_4h, data_1h, data_15m = fetch_dmi_ema_dataframes(get_candles, oanda_instrument)
                if data_1d is None or data_4h is None or data_1h is None or data_15m is None:
                    continue
                price_data = self.oanda_client.get_current_price(oanda_instrument)
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
                    opportunities.append({
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
                    opportunities.append({
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
                self.logger.debug(f"DMI-EMA signal for {pair_key}: {e}")
        market_state["dmi_ema_opportunities"] = opportunities
        if opportunities and self.check_count % 10 == 0:
            self.logger.info(f"DMI-EMA: {len(opportunities)} opportunity(ies) (trigger met: {sum(1 for o in opportunities if o.get('ft_15m_trigger_met'))})")
        if getattr(self, "market_state_file", None) and os.path.exists(self.market_state_file):
            try:
                with open(self.market_state_file, "r") as f:
                    on_disk = json.load(f)
                on_disk["dmi_ema_opportunities"] = opportunities
                on_disk["dmi_ema_last_updated"] = datetime.utcnow().isoformat()
                with open(self.market_state_file, "w") as f:
                    json.dump(on_disk, f, indent=2)
            except Exception as e:
                self.logger.debug(f"Could not write dmi_ema_opportunities to market_state file: {e}")
        if self.market_state_api_url:
            try:
                from src.integration.fisher_market_bridge import post_ft_dmi_ema_to_api
                n_ft = len(market_state.get("ft_dmi_ema_opportunities", []))
                n_dmi = len(opportunities)
                if n_ft > 0 or n_dmi > 0 or self.check_count % 10 == 0:
                    self.logger.info("DMI-EMA: POSTing %s DMI-EMA + %s FT-DMI-EMA to market-state-api", n_dmi, n_ft)
                ok = post_ft_dmi_ema_to_api(
                    market_state.get("ft_dmi_ema_opportunities", []),
                    dmi_ema_opportunities=opportunities,
                )
                if ok and (n_dmi > 0 or n_ft > 0):
                    self.logger.info("DMI-EMA: POSTed opportunities to market-state-api")
            except Exception as e:
                self.logger.warning("Could not POST DMI-EMA opportunities to market-state-api: %s", e)
    
    def _check_ft_dmi_ema_opportunities_auto(self, market_state: Dict):
        """AUTO mode only: evaluate FT-DMI-EMA setups on the fly; open trades when all conditions met, subject to FT_DMI_EMA_MAX_TRADES."""
        try:
            from src.ft_dmi_ema import (
                get_setup_status,
                fetch_ft_dmi_ema_dataframes,
                InstrumentConfig as FTInstrumentConfig,
            )
            from src.ft_dmi_ema.candle_adapter import pair_to_oanda, oanda_to_pair
        except ImportError as e:
            self.logger.debug(f"FT-DMI-EMA module not available: {e}")
            return
        max_ft_dmi_ema_trades = int(os.getenv("FT_DMI_EMA_MAX_TRADES", "2").strip() or "2")
        count_ft_dmi_ema = sum(
            1 for t in self.position_manager.active_trades.values()
            if getattr(t, "opportunity_source", "") == "FT_DMI_EMA"
        )
        if count_ft_dmi_ema >= max_ft_dmi_ema_trades:
            if self.check_count % 20 == 0:
                self.logger.info(f"FT-DMI-EMA (AUTO): at max ({count_ft_dmi_ema}/{max_ft_dmi_ema_trades}) - skipping new entries")
            return
        pairs = FTInstrumentConfig.get_monitored_pairs()
        trigger_met = []
        for pair_key in pairs:
            try:
                oanda_instrument = pair_to_oanda(pair_key) if "/" in pair_key or "-" in pair_key else pair_key
                if getattr(self, "ft_candle_fetcher", None):
                    data_15m, data_1h, data_4h = self.ft_candle_fetcher.fetch_multi_timeframe(
                        oanda_instrument, granularities=["M15", "H1", "H4"], count=500
                    )
                else:
                    data_15m, data_1h, data_4h = fetch_ft_dmi_ema_dataframes(
                        lambda inst, gran, count: self.oanda_client.get_candles(inst, gran, count),
                        oanda_instrument,
                    )
                if data_15m is None or data_1h is None or data_4h is None:
                    continue
                price_data = self.oanda_client.get_current_price(oanda_instrument)
                if not price_data:
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
                if status.get("long_setup_ready") and status.get("long_trigger_met"):
                    trigger_met.append({
                        "id": f"FT_DMI_EMA_{pair_display}_LONG",
                        "pair": pair_display,
                        "direction": "LONG",
                        "entry": current_price,
                        "current_price": current_price,
                        "source": "FT_DMI_EMA",
                        "ft_15m_trigger_met": True,
                        "reason": "Setup ready + 15m Fisher bullish crossover",
                        "execution_config": {"mode": "IMMEDIATE_MARKET"},
                    })
                if status.get("short_setup_ready") and status.get("short_trigger_met"):
                    trigger_met.append({
                        "id": f"FT_DMI_EMA_{pair_display}_SHORT",
                        "pair": pair_display,
                        "direction": "SHORT",
                        "entry": current_price,
                        "current_price": current_price,
                        "source": "FT_DMI_EMA",
                        "ft_15m_trigger_met": True,
                        "reason": "Setup ready + 15m Fisher bearish crossover",
                        "execution_config": {"mode": "IMMEDIATE_MARKET"},
                    })
            except Exception as e:
                self.logger.debug(f"FT-DMI-EMA AUTO signal for {pair_key}: {e}")
        if not trigger_met:
            return
        self.logger.info(f"FT-DMI-EMA (AUTO): {len(trigger_met)} setup(s) with 15m trigger met (max trades: {max_ft_dmi_ema_trades}, current: {count_ft_dmi_ema})")
        for opp in trigger_met:
            try:
                pair = opp.get("pair", "")
                direction = opp.get("direction", "").upper()
                if count_ft_dmi_ema >= max_ft_dmi_ema_trades:
                    continue
                if self.position_manager.is_pair_in_cooldown(pair):
                    continue
                if self.position_manager.has_existing_position(pair, direction):
                    continue
                can_open, reason = self.position_manager.can_open_new_trade()
                if not can_open:
                    self.logger.info(f"FT-DMI-EMA {pair} {direction}: {reason}")
                    continue
                current_prices = self._get_current_prices([pair])
                current_price = current_prices.get(pair)
                if not current_price:
                    continue
                opp_with_order = dict(opp)
                opp_with_order["entry"] = current_price
                opp_with_order["order_type"] = "MARKET"
                opp_with_order["current_price"] = current_price
                try:
                    from src.ft_dmi_ema import fetch_ft_dmi_ema_dataframes, StopLossCalculator
                    from src.ft_dmi_ema.candle_adapter import pair_to_oanda
                    oanda_instrument = pair_to_oanda(pair)
                    if getattr(self, "ft_candle_fetcher", None):
                        _, data_1h, _ = self.ft_candle_fetcher.fetch_multi_timeframe(
                            oanda_instrument, granularities=["M15", "H1", "H4"], count=500
                        )
                    else:
                        _, data_1h, _ = fetch_ft_dmi_ema_dataframes(
                            lambda inst, gran, count: self.oanda_client.get_candles(inst, gran, count),
                            oanda_instrument,
                        )
                    if data_1h is not None and len(data_1h) > 0:
                        stop_calc = StopLossCalculator()
                        stop_info = stop_calc.calculate_stop_loss(
                            data_1h=data_1h,
                            entry_price=current_price,
                            direction=direction.lower(),
                            entry_time=datetime.utcnow(),
                            instrument=oanda_instrument,
                        )
                        opp_with_order["stop_loss"] = stop_info["stop_loss_price"]
                        opp_with_order["initial_stop_loss"] = stop_info["stop_loss_price"]
                except Exception as sl_e:
                    self.logger.debug(f"FT-DMI-EMA stop calculation: {sl_e}")
                trade = self._maybe_reset_run_count_and_open_trade(opp_with_order, market_state)
                if trade:
                    count_ft_dmi_ema += 1
                    self.logger.info(f"FT-DMI-EMA (AUTO) {pair} {direction} @ {current_price} - order placed (15m trigger met)")
            except Exception as e:
                self.logger.error(f"FT-DMI-EMA AUTO opportunity error {opp.get('pair', '?')}: {e}", exc_info=True)
    
    def _maybe_reset_run_count_and_open_trade(self, opp: Dict, market_state: Dict, opp_id: Optional[str] = None):
        """
        In SEMI_AUTO, if user requested reset_run_count for this opportunity, reset run count and clear the flag, then open trade.
        Otherwise just open trade. Use this for every open_trade path so max_runs reset is user-driven only.
        Always uses stable opp ID so config lookup matches UI semi-auto key (re-enable + reset work).
        """
        oid = get_stable_opportunity_id(opp) if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
        if self.config.trading_mode == TradingMode.SEMI_AUTO and self.position_manager:
            try:
                from src.execution.semi_auto_controller import SemiAutoController
                semi_auto = SemiAutoController()
                saved = semi_auto.get_opportunity_config(oid)
                if saved and saved.get('reset_run_count_requested'):
                    self.position_manager.execution_enforcer.reset_run_count(oid)
                    semi_auto.set_opportunity_config(
                        oid,
                        enabled=saved.get('enabled', True),
                        mode=saved.get('mode', 'MANUAL'),
                        max_runs=saved.get('max_runs', 1),
                        sl_type=saved.get('sl_type'),
                        reset_run_count_requested=False
                    )
                    self.logger.info(f"🔄 Reset run count for {oid} (user requested); opening trade")
            except Exception as e:
                self.logger.debug(f"SemiAutoController check for reset_run_count: {e}")
        return self.position_manager.open_trade(opp, market_state)
    
    def _ensure_structure_atr_stop_if_needed(self, opp: Dict) -> None:
        """When opp has per-opportunity sl_type STRUCTURE_ATR_STAGED or STRUCTURE_ATR (LLM/Fisher), compute structure+ATR stop if not already set."""
        per_opp_sl = (opp.get('execution_config') or {}).get('sl_type') or (opp.get('fisher_config') or {}).get('sl_type')
        if per_opp_sl not in ('STRUCTURE_ATR_STAGED', 'STRUCTURE_ATR'):
            return
        if opp.get('source') in ('FT_DMI_EMA', 'DMI_EMA') and (opp.get('initial_stop_loss') or opp.get('stop_loss')):
            return
        pair = opp.get('pair', '')
        direction = (opp.get('direction') or '').upper()
        entry_price = opp.get('entry') or opp.get('current_price') or 0
        if not pair or not entry_price:
            return
        try:
            from src.ft_dmi_ema import fetch_ft_dmi_ema_dataframes, StopLossCalculator
            from src.ft_dmi_ema.candle_adapter import pair_to_oanda
            oanda_instrument = pair_to_oanda(pair)
            _, data_1h, _ = fetch_ft_dmi_ema_dataframes(
                lambda inst, gran, count: self.oanda_client.get_candles(inst, gran, count),
                oanda_instrument,
            )
            if data_1h is not None and len(data_1h) > 0:
                stop_calc = StopLossCalculator()
                stop_info = stop_calc.calculate_stop_loss(
                    data_1h=data_1h,
                    entry_price=entry_price,
                    direction=direction.lower(),
                    entry_time=datetime.utcnow(),
                    instrument=oanda_instrument,
                )
                opp['stop_loss'] = stop_info["stop_loss_price"]
                opp['initial_stop_loss'] = stop_info["stop_loss_price"]
                self.logger.debug(f"Structure+ATR stop for {pair} {direction} ({per_opp_sl}): {stop_info['stop_loss_price']}")
        except Exception as e:
            self.logger.debug(f"Structure+ATR stop calculation for {pair}: {e}")
    
    def _check_ft_dmi_ema_opportunities(self, market_state: Dict):
        """SEMI_AUTO/MANUAL: use opportunity list from market_state; open when ft_15m_trigger_met and (SEMI_AUTO: enabled in UI). AUTO: evaluate setups on the fly and open automatically when all conditions met, subject to FT_DMI_EMA_MAX_TRADES."""
        if os.getenv("FT_DMI_EMA_SIGNALS_ENABLED", "false").lower() not in ("true", "1", "yes"):
            return
        if self.config.trading_mode == TradingMode.AUTO:
            if not getattr(self.config, 'auto_trade_ft_dmi_ema', True):
                return
            self._check_ft_dmi_ema_opportunities_auto(market_state)
            return
        ft_opps = market_state.get("ft_dmi_ema_opportunities", [])
        if not ft_opps:
            return
        try:
            from src.execution.semi_auto_controller import SemiAutoController
            semi_auto = SemiAutoController()
        except Exception:
            semi_auto = None
        if self.config.trading_mode == TradingMode.SEMI_AUTO and semi_auto:
            total_ft = len(ft_opps)
            ft_opps = [o for o in ft_opps if semi_auto.is_enabled(get_stable_opportunity_id(o, source='FT_DMI_EMA') if get_stable_opportunity_id else _stable_opp_id_fallback(o))]
            enabled_count = len(ft_opps)
            if self.check_count % 5 == 0 or enabled_count > 0:
                self.logger.info(f"FT-DMI-EMA: {enabled_count} enabled (of {total_ft} total) from semi-auto config")
            if not ft_opps:
                return
        # Process every enabled opportunity (mirror Fisher): open_trade -> enforcer returns WAIT_SIGNAL or EXECUTE_NOW
        self.logger.info(f"FT-DMI-EMA: Checking {len(ft_opps)} enabled opportunity(ies)")
        for opp in ft_opps:
            try:
                pair = opp.get("pair", "")
                direction = opp.get("direction", "").upper()
                if self.position_manager.is_pair_in_cooldown(pair):
                    continue
                if self.position_manager.has_existing_position(pair, direction):
                    continue
                can_open, reason = self.position_manager.can_open_new_trade()
                if not can_open:
                    self.logger.info(f"FT-DMI-EMA {pair} {direction}: {reason}")
                    continue
                current_prices = self._get_current_prices([pair])
                current_price = current_prices.get(pair)
                if not current_price:
                    continue
                opp_id = get_stable_opportunity_id(opp) if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
                saved = semi_auto.get_opportunity_config(opp_id) if semi_auto else {}
                exec_cfg = dict(opp.get("execution_config") or {})
                exec_cfg["mode"] = saved.get("mode", "FISHER_M15_TRIGGER")
                if saved.get("max_runs") is not None:
                    exec_cfg["max_runs"] = saved.get("max_runs", 1)
                opp_with_order = dict(opp)
                opp_with_order["execution_config"] = exec_cfg
                opp_with_order["current_price"] = current_price
                if exec_cfg.get("mode") == "IMMEDIATE_MARKET":
                    opp_with_order["entry"] = current_price
                    opp_with_order["order_type"] = "MARKET"
                else:
                    opp_with_order["entry"] = opp.get("entry") or current_price
                    opp_with_order["order_type"] = None
                # Structure+ATR stop for FT-DMI-EMA (Phase 2)
                try:
                    from src.ft_dmi_ema import fetch_ft_dmi_ema_dataframes, StopLossCalculator
                    from src.ft_dmi_ema.candle_adapter import pair_to_oanda
                    oanda_instrument = pair_to_oanda(pair)
                    if getattr(self, "ft_candle_fetcher", None):
                        _, data_1h, _ = self.ft_candle_fetcher.fetch_multi_timeframe(
                            oanda_instrument, granularities=["M15", "H1", "H4"], count=500
                        )
                    else:
                        _, data_1h, _ = fetch_ft_dmi_ema_dataframes(
                            lambda inst, gran, count: self.oanda_client.get_candles(inst, gran, count),
                            oanda_instrument,
                        )
                    if data_1h is not None and len(data_1h) > 0:
                        stop_calc = StopLossCalculator()
                        stop_info = stop_calc.calculate_stop_loss(
                            data_1h=data_1h,
                            entry_price=opp_with_order["entry"],
                            direction=direction.lower(),
                            entry_time=datetime.utcnow(),
                            instrument=oanda_instrument,
                        )
                        opp_with_order["stop_loss"] = stop_info["stop_loss_price"]
                        opp_with_order["initial_stop_loss"] = stop_info["stop_loss_price"]
                except Exception as sl_e:
                    self.logger.debug(f"FT-DMI-EMA stop calculation: {sl_e}")
                trade = self._maybe_reset_run_count_and_open_trade(opp_with_order, market_state)
                if trade:
                    self.logger.info(f"FT-DMI-EMA {pair} {direction} @ {current_price} - order placed (15m trigger met)")
            except Exception as e:
                self.logger.error(f"FT-DMI-EMA opportunity error {opp.get('pair', '?')}: {e}", exc_info=True)
    
    def _check_dmi_ema_opportunities_auto(self, market_state: Dict):
        """AUTO mode only: evaluate DMI-EMA setups on the fly; open when setup ready and (15m trigger or IMMEDIATE); subject to combined FT_DMI_EMA_MAX_TRADES."""
        try:
            from src.ft_dmi_ema import get_dmi_ema_setup_status, fetch_dmi_ema_dataframes
            from src.ft_dmi_ema import InstrumentConfig as FTInstrumentConfig
            from src.ft_dmi_ema.candle_adapter import pair_to_oanda, oanda_to_pair
        except ImportError as e:
            self.logger.debug(f"DMI-EMA module not available: {e}")
            return
        max_trades = int(os.getenv("FT_DMI_EMA_MAX_TRADES", "2").strip() or "2")
        count_system = sum(
            1 for t in self.position_manager.active_trades.values()
            if getattr(t, "opportunity_source", "") in ("FT_DMI_EMA", "DMI_EMA")
        )
        if count_system >= max_trades:
            if self.check_count % 20 == 0:
                self.logger.info(f"DMI-EMA (AUTO): at max ({count_system}/{max_trades}) - skipping new entries")
            return
        if not getattr(self.config, "auto_trade_dmi_ema", True):
            return
        pairs = FTInstrumentConfig.get_monitored_pairs()
        trigger_met = []
        for pair_key in pairs:
            try:
                oanda_instrument = pair_to_oanda(pair_key) if "/" in pair_key or "-" in pair_key else pair_key
                if getattr(self, "ft_candle_fetcher", None):
                    get_candles = lambda inst, gran, count: self.ft_candle_fetcher.get_candles(inst, gran, count)
                else:
                    get_candles = lambda inst, gran, count: self.oanda_client.get_candles(inst, gran, count)
                data_1d, data_4h, data_1h, data_15m = fetch_dmi_ema_dataframes(get_candles, oanda_instrument)
                if data_1d is None or data_4h is None or data_1h is None or data_15m is None:
                    continue
                price_data = self.oanda_client.get_current_price(oanda_instrument)
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
                # AUTO: open when setup ready and 15m trigger met (same as FT-DMI-EMA)
                if status.get("long_setup_ready") and status.get("ft_15m_trigger_met"):
                    trigger_met.append({
                        "id": f"DMI_EMA_{pair_display}_LONG",
                        "pair": pair_display,
                        "direction": "LONG",
                        "entry": current_price,
                        "current_price": current_price,
                        "source": "DMI_EMA",
                        "ft_15m_trigger_met": True,
                        "reason": "DMI-EMA setup + 15m Fisher bullish crossover",
                        "execution_config": {"mode": "IMMEDIATE_MARKET"},
                        "confidence_flags": status.get("confidence_flags", {}),
                    })
                if status.get("short_setup_ready") and status.get("ft_15m_trigger_met"):
                    trigger_met.append({
                        "id": f"DMI_EMA_{pair_display}_SHORT",
                        "pair": pair_display,
                        "direction": "SHORT",
                        "entry": current_price,
                        "current_price": current_price,
                        "source": "DMI_EMA",
                        "ft_15m_trigger_met": True,
                        "reason": "DMI-EMA setup + 15m Fisher bearish crossover",
                        "execution_config": {"mode": "IMMEDIATE_MARKET"},
                        "confidence_flags": status.get("confidence_flags", {}),
                    })
            except Exception as e:
                self.logger.debug(f"DMI-EMA AUTO signal for {pair_key}: {e}")
        if not trigger_met:
            return
        self.logger.info(f"DMI-EMA (AUTO): {len(trigger_met)} setup(s) with 15m trigger met (max: {max_trades}, current: {count_system})")
        for opp in trigger_met:
            try:
                pair = opp.get("pair", "")
                direction = opp.get("direction", "").upper()
                if count_system >= max_trades:
                    continue
                if self.position_manager.is_pair_in_cooldown(pair):
                    continue
                if self.position_manager.has_existing_position(pair, direction):
                    continue
                can_open, reason = self.position_manager.can_open_new_trade()
                if not can_open:
                    self.logger.info(f"DMI-EMA {pair} {direction}: {reason}")
                    continue
                current_prices = self._get_current_prices([pair])
                current_price = current_prices.get(pair)
                if not current_price:
                    continue
                opp_with_order = dict(opp)
                opp_with_order["entry"] = current_price
                opp_with_order["order_type"] = "MARKET"
                opp_with_order["current_price"] = current_price
                try:
                    from src.ft_dmi_ema import fetch_dmi_ema_dataframes, StopLossCalculator
                    from src.ft_dmi_ema.candle_adapter import pair_to_oanda
                    oanda_instrument = pair_to_oanda(pair)
                    if getattr(self, "ft_candle_fetcher", None):
                        get_candles = lambda inst, gran, count: self.ft_candle_fetcher.get_candles(inst, gran, count)
                    else:
                        get_candles = lambda inst, gran, count: self.oanda_client.get_candles(inst, gran, count)
                    _, _, data_1h, _ = fetch_dmi_ema_dataframes(get_candles, oanda_instrument)
                    if data_1h is not None and len(data_1h) > 0:
                        stop_calc = StopLossCalculator()
                        stop_info = stop_calc.calculate_stop_loss(
                            data_1h=data_1h,
                            entry_price=current_price,
                            direction=direction.lower(),
                            entry_time=datetime.utcnow(),
                            instrument=oanda_instrument,
                        )
                        opp_with_order["stop_loss"] = stop_info["stop_loss_price"]
                        opp_with_order["initial_stop_loss"] = stop_info["stop_loss_price"]
                except Exception as sl_e:
                    self.logger.debug(f"DMI-EMA stop calculation: {sl_e}")
                trade = self._maybe_reset_run_count_and_open_trade(opp_with_order, market_state)
                if trade:
                    count_system += 1
                    self.logger.info(f"DMI-EMA (AUTO) {pair} {direction} @ {current_price} - order placed (15m trigger met)")
            except Exception as e:
                self.logger.error(f"DMI-EMA AUTO opportunity error {opp.get('pair', '?')}: {e}", exc_info=True)
    
    def _check_dmi_ema_opportunities(self, market_state: Dict):
        """SEMI_AUTO/MANUAL: use dmi_ema_opportunities from market_state; open when ft_15m_trigger_met and (SEMI_AUTO: enabled). AUTO: _check_dmi_ema_opportunities_auto."""
        if os.getenv("FT_DMI_EMA_SIGNALS_ENABLED", "false").lower() not in ("true", "1", "yes"):
            return
        if self.config.trading_mode == TradingMode.AUTO:
            if not getattr(self.config, "auto_trade_dmi_ema", True):
                return
            self._check_dmi_ema_opportunities_auto(market_state)
            return
        dmi_opps = market_state.get("dmi_ema_opportunities", [])
        if not dmi_opps:
            return
        try:
            from src.execution.semi_auto_controller import SemiAutoController
            semi_auto = SemiAutoController()
        except Exception:
            semi_auto = None
        if self.config.trading_mode == TradingMode.SEMI_AUTO and semi_auto:
            total = len(dmi_opps)
            dmi_opps = [o for o in dmi_opps if semi_auto.is_enabled(get_stable_opportunity_id(o, source='DMI_EMA') if get_stable_opportunity_id else _stable_opp_id_fallback(o))]
            enabled_count = len(dmi_opps)
            if self.check_count % 5 == 0 or enabled_count > 0:
                self.logger.info(f"DMI-EMA: {enabled_count} enabled (of {total} total) from semi-auto config")
            if not dmi_opps:
                return
        self.logger.info(f"DMI-EMA: Checking {len(dmi_opps)} enabled opportunity(ies)")
        for opp in dmi_opps:
            try:
                pair = opp.get("pair", "")
                direction = opp.get("direction", "").upper()
                if self.position_manager.is_pair_in_cooldown(pair):
                    continue
                if self.position_manager.has_existing_position(pair, direction):
                    continue
                can_open, reason = self.position_manager.can_open_new_trade()
                if not can_open:
                    self.logger.info(f"DMI-EMA {pair} {direction}: {reason}")
                    continue
                current_prices = self._get_current_prices([pair])
                current_price = current_prices.get(pair)
                if not current_price:
                    continue
                opp_id = get_stable_opportunity_id(opp, source='DMI_EMA') if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
                saved = semi_auto.get_opportunity_config(opp_id) if semi_auto else {}
                exec_cfg = dict(opp.get("execution_config") or {})
                exec_cfg["mode"] = saved.get("mode", "FISHER_M15_TRIGGER")
                if saved.get("max_runs") is not None:
                    exec_cfg["max_runs"] = saved.get("max_runs", 1)
                opp_with_order = dict(opp)
                opp_with_order["execution_config"] = exec_cfg
                opp_with_order["current_price"] = current_price
                if exec_cfg.get("mode") == "IMMEDIATE_MARKET":
                    opp_with_order["entry"] = current_price
                    opp_with_order["order_type"] = "MARKET"
                    opp_with_order["ft_15m_trigger_met"] = True
                else:
                    opp_with_order["entry"] = opp.get("entry") or current_price
                    opp_with_order["order_type"] = None
                try:
                    from src.ft_dmi_ema import fetch_dmi_ema_dataframes, StopLossCalculator
                    from src.ft_dmi_ema.candle_adapter import pair_to_oanda
                    oanda_instrument = pair_to_oanda(pair)
                    if getattr(self, "ft_candle_fetcher", None):
                        get_candles = lambda inst, gran, count: self.ft_candle_fetcher.get_candles(inst, gran, count)
                    else:
                        get_candles = lambda inst, gran, count: self.oanda_client.get_candles(inst, gran, count)
                    _, _, data_1h, _ = fetch_dmi_ema_dataframes(get_candles, oanda_instrument)
                    if data_1h is not None and len(data_1h) > 0:
                        stop_calc = StopLossCalculator()
                        stop_info = stop_calc.calculate_stop_loss(
                            data_1h=data_1h,
                            entry_price=opp_with_order["entry"],
                            direction=direction.lower(),
                            entry_time=datetime.utcnow(),
                            instrument=oanda_instrument,
                        )
                        opp_with_order["stop_loss"] = stop_info["stop_loss_price"]
                        opp_with_order["initial_stop_loss"] = stop_info["stop_loss_price"]
                except Exception as sl_e:
                    self.logger.debug(f"DMI-EMA stop calculation: {sl_e}")
                trade = self._maybe_reset_run_count_and_open_trade(opp_with_order, market_state)
                if trade:
                    self.logger.info(f"DMI-EMA {pair} {direction} @ {current_price} - order placed (15m trigger met)")
            except Exception as e:
                self.logger.error(f"DMI-EMA opportunity error {opp.get('pair', '?')}: {e}", exc_info=True)
    
    def _check_dmi_ema_activation_signals(self, market_state: Dict):
        """Check pending DMI-EMA signals (DMI_EMA_M15_TRIGGER = 15m Fisher; DMI_EMA_DMI_M15_TRIGGER = 15m +DI/-DI); execute and remove from pending when met."""
        if self.config.trading_mode == TradingMode.AUTO:
            return
        if not self.position_manager or not getattr(self.position_manager, "pending_signals", None):
            return
        dmi_pending = [
            (sid, data) for sid, data in self.position_manager.pending_signals.items()
            if isinstance(data, dict)
            and (data.get("directive") or {}).get("wait_for_signal") in ("DMI_EMA_M15_TRIGGER", "DMI_EMA_DMI_M15_TRIGGER")
        ]
        if not dmi_pending:
            return
        self.logger.info(f"⏳ Checking {len(dmi_pending)} pending DMI-EMA signal(s) for 15m trigger")
        try:
            from src.ft_dmi_ema import get_dmi_ema_setup_status, fetch_dmi_ema_dataframes
            from src.ft_dmi_ema.candle_adapter import pair_to_oanda
        except ImportError:
            self.logger.debug("DMI-EMA module not available for activation check")
            return
        for signal_id, data in dmi_pending:
            opportunity = dict(data.get("opportunity") or {})
            if opportunity.get("source") != "DMI_EMA":
                continue
            pair = opportunity.get("pair", "")
            direction = (opportunity.get("direction") or "").upper()
            if not pair:
                continue
            wait_for_signal = (data.get("directive") or {}).get("wait_for_signal", "")
            if self.position_manager.has_existing_position(pair, direction):
                self.position_manager.pending_signals.pop(signal_id, None)
                self.position_manager._save_pending_signals()
                self.position_manager._save_state()
                self.logger.info(f"⏭️ DMI-EMA activation skipped {pair} {direction} - already have position; removed pending")
                continue
            can_open, reason = self.position_manager.can_open_new_trade()
            if not can_open:
                self.logger.info(f"⏭️ DMI-EMA activation skipped {pair} {direction} - {reason}")
                continue
            try:
                oanda_instrument = pair_to_oanda(pair)
                if getattr(self, "ft_candle_fetcher", None):
                    get_candles = lambda inst, gran, count: self.ft_candle_fetcher.get_candles(inst, gran, count)
                else:
                    get_candles = lambda inst, gran, count: self.oanda_client.get_candles(inst, gran, count)
                data_1d, data_4h, data_1h, data_15m = fetch_dmi_ema_dataframes(get_candles, oanda_instrument)
                if data_1d is None or data_4h is None or data_1h is None or data_15m is None:
                    continue
                price_data = self.oanda_client.get_current_price(oanda_instrument)
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
                want_long = direction in ("LONG", "BUY")
                if wait_for_signal == "DMI_EMA_DMI_M15_TRIGGER":
                    trigger_met = (want_long and status.get("long_dmi_15m_trigger_met")) or (not want_long and status.get("short_dmi_15m_trigger_met"))
                else:
                    trigger_met = (want_long and status.get("long_trigger_met")) or (not want_long and status.get("short_trigger_met"))
                if not trigger_met:
                    continue
                trigger_label = "15m +DI/-DI crossover" if wait_for_signal == "DMI_EMA_DMI_M15_TRIGGER" else "15m Fisher crossover"
                self.logger.info(f"DMI-EMA activation: {trigger_label} met for {pair} {direction} (signal_id={signal_id})")
                self.position_manager.pending_signals.pop(signal_id, None)
                self.position_manager._save_pending_signals()
                opp_with_order = dict(opportunity)
                opp_with_order["ft_15m_trigger_met"] = True if wait_for_signal == "DMI_EMA_M15_TRIGGER" else opportunity.get("ft_15m_trigger_met", False)
                opp_with_order["dmi_15m_trigger_met"] = True if wait_for_signal == "DMI_EMA_DMI_M15_TRIGGER" else opportunity.get("dmi_15m_trigger_met", False)
                opp_with_order["current_price"] = current_price
                opp_with_order["entry"] = opportunity.get("entry") or current_price
                opp_with_order["execution_config"] = dict(opportunity.get("execution_config") or {})
                if opp_with_order["execution_config"].get("mode") == "IMMEDIATE_MARKET":
                    opp_with_order["order_type"] = "MARKET"
                else:
                    opp_with_order["order_type"] = None
                try:
                    from src.ft_dmi_ema import StopLossCalculator
                    if data_1h is not None and len(data_1h) > 0:
                        stop_calc = StopLossCalculator()
                        stop_info = stop_calc.calculate_stop_loss(
                            data_1h=data_1h,
                            entry_price=opp_with_order["entry"],
                            direction=direction.lower(),
                            entry_time=now,
                            instrument=oanda_instrument,
                        )
                        opp_with_order["stop_loss"] = stop_info["stop_loss_price"]
                        opp_with_order["initial_stop_loss"] = stop_info["stop_loss_price"]
                except Exception as sl_e:
                    self.logger.debug(f"DMI-EMA activation stop calculation: {sl_e}")
                trade = self._maybe_reset_run_count_and_open_trade(opp_with_order, market_state)
                if trade:
                    self.logger.info(f"✅ DMI-EMA activation executed: {pair} {direction} (was waiting for 15m trigger)")
                else:
                    self.logger.warning(f"⚠️ DMI-EMA activation failed to open trade: {pair} {direction}")
                self.position_manager._save_state()
            except Exception as e:
                self.logger.debug(f"DMI-EMA activation check for {pair} {direction}: {e}")
                continue
    
    def _clear_pending_signals_for_disabled_opportunities(self, market_state: Dict):
        """
        Remove pending signals whose (pair, direction) is no longer enabled in semi-auto config
        or no longer in market state. So when user disables a trade, logs and UI stop showing it as pending.

        Only call set_opportunity_enabled(opp_id, False) when (pair, direction) is present in the
        current market_state. When the opportunity is not in this run's market state, we remove the
        pending signal but leave the user's enabled preference unchanged so pairs reappear as
        enabled when they show up again in the list.
        """
        if not self.position_manager or not getattr(self.position_manager, 'pending_signals', None):
            return
        try:
            from src.execution.semi_auto_controller import SemiAutoController
            sac = SemiAutoController()
        except Exception:
            return
        # Build set of (pair_norm, direction_key) that are currently enabled and in market state
        def _norm_pair(p):
            return (p or '').strip().replace('_', '/').upper()
        def _norm_dir(d):
            d = (d or '').upper()
            if d in ('BUY', 'LONG'):
                return 'LONG'
            if d in ('SELL', 'SHORT'):
                return 'SHORT'
            return d
        enabled_set = set()  # (source, pair_norm, dir_key) so LLM and DMI-EMA same pair have separate state
        for opp in market_state.get('opportunities', []):
            pair = opp.get('pair', '')
            direction = opp.get('direction', '')
            stable_opp_id = get_stable_opportunity_id(opp, source='LLM') if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
            if sac.is_enabled(stable_opp_id):
                enabled_set.add(('LLM', _norm_pair(pair), _norm_dir(direction)))
        for opp in market_state.get('fisher_opportunities', []):
            pair = opp.get('pair', '')
            direction = opp.get('direction', '')
            opp_id = get_stable_opportunity_id(opp, source='Fisher') if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
            if sac.is_enabled(opp_id):
                enabled_set.add(('Fisher', _norm_pair(pair), _norm_dir(direction)))
        for opp in market_state.get('ft_dmi_ema_opportunities', []):
            opp_id = get_stable_opportunity_id(opp, source='FT_DMI_EMA') if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
            if sac.is_enabled(opp_id):
                enabled_set.add(('FT_DMI_EMA', _norm_pair(opp.get('pair')), _norm_dir(opp.get('direction'))))
        for opp in market_state.get('dmi_ema_opportunities', []):
            opp_id = get_stable_opportunity_id(opp, source='DMI_EMA') if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
            if sac.is_enabled(opp_id):
                enabled_set.add(('DMI_EMA', _norm_pair(opp.get('pair')), _norm_dir(opp.get('direction'))))
        # Build set of (source, pair_norm, dir_key) that appear in this run's market state (regardless of enabled).
        # We only set_opportunity_enabled(False) when (source, pair, dir) is in this set.
        in_market_state_set = set()
        for opp in market_state.get('opportunities', []):
            in_market_state_set.add(('LLM', _norm_pair(opp.get('pair', '')), _norm_dir(opp.get('direction', ''))))
        for opp in market_state.get('fisher_opportunities', []):
            in_market_state_set.add(('Fisher', _norm_pair(opp.get('pair', '')), _norm_dir(opp.get('direction', ''))))
        for opp in market_state.get('ft_dmi_ema_opportunities', []):
            in_market_state_set.add(('FT_DMI_EMA', _norm_pair(opp.get('pair', '')), _norm_dir(opp.get('direction', ''))))
        for opp in market_state.get('dmi_ema_opportunities', []):
            in_market_state_set.add(('DMI_EMA', _norm_pair(opp.get('pair', '')), _norm_dir(opp.get('direction', ''))))
        # Remove any pending signal not in enabled_set; only set disabled when (pair, dir) is in this run's market state
        removed_any = False
        for signal_id, data in list(getattr(self.position_manager, 'pending_signals', {}).items()):
            if not isinstance(data, dict):
                continue
            opp = data.get('opportunity') or {}
            pair_norm = _norm_pair(opp.get('pair', ''))
            dir_key = _norm_dir(opp.get('direction', ''))
            source = opp.get('source', 'LLM')
            if (source, pair_norm, dir_key) not in enabled_set:
                self.position_manager.pending_signals.pop(signal_id, None)
                removed_any = True
                self.logger.info(f"🔄 Removed pending signal {signal_id} (no longer enabled or not in market state)")
                # Only set semi-auto config to disabled when (pair, direction) is in THIS run's market state.
                # When it's not in market state, preserve user's enabled preference for when the pair reappears.
                open_position_states = (TradeState.OPEN, TradeState.AT_BREAKEVEN, TradeState.TRAILING)
                has_open_position = any(
                    (_norm_pair(getattr(t, 'pair', '')), _norm_dir(getattr(t, 'direction', ''))) == (pair_norm, dir_key)
                    and getattr(t, 'state', None) in open_position_states
                    for t in (getattr(self.position_manager, 'active_trades', None) or {}).values()
                )
                if not has_open_position and (source, pair_norm, dir_key) in in_market_state_set:
                    try:
                        opp_id = get_stable_opportunity_id(opp, source=source) if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
                        if opp_id:
                            sac.set_opportunity_enabled(opp_id, False)
                    except Exception as e:
                        self.logger.debug("Could not set opportunity to disabled in semi-auto config: %s", e)
                elif not has_open_position and (source, pair_norm, dir_key) not in in_market_state_set:
                    self.logger.debug(
                        "Left enabled state unchanged for %s %s %s (not in this run's market state)",
                        source, pair_norm, dir_key
                    )
                else:
                    self.logger.debug("Skipped setting opportunity to disabled (open position exists for %s %s)", pair_norm, dir_key)
        if removed_any:
            self.position_manager._save_pending_signals()
            self.position_manager._save_state()  # Push updated state to config-api so UI shows correct count

    def _check_fisher_activation_signals(self, market_state: Dict):
        """
        Check pending Fisher signals (WAIT_SIGNAL) for H1/M15 crossover activation.
        When crossover direction matches opportunity direction, execute trade (IMMEDIATE) and remove from pending.
        Only runs in SEMI_AUTO or MANUAL; never in AUTO.
        """
        if self.config.trading_mode == TradingMode.AUTO:
            return
        if not self.position_manager or not getattr(self.position_manager, 'pending_signals', None):
            return
        # Clear pending signals for opportunities that are no longer enabled (so disabling in UI stops log/UI count)
        self._clear_pending_signals_for_disabled_opportunities(market_state)
        pending_count = len(self.position_manager.pending_signals)
        if pending_count > 0:
            self.logger.info(f"⏳ Checking {pending_count} pending Fisher signal(s) for activation (FT crossover 15m/1h)")
        try:
            from src.execution.fisher_activation_monitor import FisherActivationMonitor
            pending_file = getattr(self.position_manager, 'pending_signals_file', '/var/data/pending_signals.json')
            monitor = FisherActivationMonitor(pending_file=pending_file)
            activated = monitor.check_activations(self.oanda_api, self.position_manager)
            if not activated:
                return
            for act in activated:
                signal_id = act.get('signal_id', '')
                opportunity = dict(act.get('opportunity', {}))
                if not opportunity or not signal_id:
                    continue
                pair = opportunity.get('pair', '')
                direction = opportunity.get('direction', '').upper()
                if self.position_manager.has_existing_position(pair, direction):
                    self.position_manager.pending_signals.pop(signal_id, None)
                    self.position_manager._save_pending_signals()
                    self.logger.info(f"⏭️ Fisher activation skipped {pair} {direction} - already have position; removed pending")
                    continue
                can_open, reason = self.position_manager.can_open_new_trade()
                if not can_open:
                    self.logger.info(f"⏭️ Fisher activation skipped {pair} {direction} - {reason}")
                    continue
                self.position_manager.pending_signals.pop(signal_id, None)
                self.position_manager._save_pending_signals()
                fc = dict(opportunity.get('fisher_config') or {})
                fc['activation_trigger'] = 'IMMEDIATE'
                opportunity['fisher_config'] = fc
                opportunity['execution_config'] = opportunity.get('execution_config') or {}
                # Ensure entry/current_price for structure+ATR; when per-opp SL is STRUCTURE_ATR_STAGED, compute stop
                if not opportunity.get('entry') and pair:
                    prices = self._get_current_prices([pair])
                    opportunity['entry'] = opportunity['current_price'] = prices.get(pair)
                self._ensure_structure_atr_stop_if_needed(opportunity)
                trade = self._maybe_reset_run_count_and_open_trade(opportunity, market_state)
                if trade:
                    self.logger.info(f"✅ Fisher activation executed: {pair} {direction} (was waiting for crossover)")
                else:
                    self.logger.warning(f"⚠️ Fisher activation failed to open trade: {pair} {direction}")
        except Exception as e:
            self.logger.warning(f"⚠️ Fisher activation check failed: {e}", exc_info=True)
    
    def _check_ft_dmi_ema_activation_signals(self, market_state: Dict):
        """
        Check pending FT-DMI-EMA signals (WAIT_SIGNAL) for 15m Fisher crossover activation.
        When get_setup_status returns trigger_met for that pair/direction, execute and remove from pending.
        Only runs in SEMI_AUTO or MANUAL; never in AUTO. Mirrors _check_fisher_activation_signals.
        """
        if self.config.trading_mode == TradingMode.AUTO:
            return
        if not self.position_manager or not getattr(self.position_manager, 'pending_signals', None):
            return
        ft_pending = [
            (sid, data) for sid, data in self.position_manager.pending_signals.items()
            if isinstance(data, dict) and (data.get('directive') or {}).get('wait_for_signal') == 'FT_DMI_EMA_M15_TRIGGER'
        ]
        if not ft_pending:
            return
        self.logger.info(f"⏳ Checking {len(ft_pending)} pending FT-DMI-EMA signal(s) for 15m trigger")
        try:
            from src.ft_dmi_ema import get_setup_status, fetch_ft_dmi_ema_dataframes
            from src.ft_dmi_ema.candle_adapter import pair_to_oanda
        except ImportError:
            self.logger.debug("FT-DMI-EMA module not available for activation check")
            return
        for signal_id, data in ft_pending:
            opportunity = dict(data.get('opportunity') or {})
            if opportunity.get('source') != 'FT_DMI_EMA':
                continue
            pair = opportunity.get('pair', '')
            direction = (opportunity.get('direction') or '').upper()
            if not pair:
                continue
            if self.position_manager.has_existing_position(pair, direction):
                self.position_manager.pending_signals.pop(signal_id, None)
                self.position_manager._save_pending_signals()
                self.position_manager._save_state()
                self.logger.info(f"⏭️ FT-DMI-EMA activation skipped {pair} {direction} - already have position; removed pending")
                continue
            can_open, reason = self.position_manager.can_open_new_trade()
            if not can_open:
                self.logger.info(f"⏭️ FT-DMI-EMA activation skipped {pair} {direction} - {reason}")
                continue
            try:
                oanda_instrument = pair_to_oanda(pair)
                if getattr(self, 'ft_candle_fetcher', None):
                    data_15m, data_1h, data_4h = self.ft_candle_fetcher.fetch_multi_timeframe(
                        oanda_instrument, granularities=["M15", "H1", "H4"], count=500
                    )
                else:
                    data_15m, data_1h, data_4h = fetch_ft_dmi_ema_dataframes(
                        lambda inst, gran, count: self.oanda_client.get_candles(inst, gran, count),
                        oanda_instrument,
                    )
                if data_15m is None or data_1h is None or data_4h is None:
                    continue
                price_data = self.oanda_client.get_current_price(oanda_instrument)
                if not price_data:
                    continue
                bid = price_data.get('bid') or 0
                ask = price_data.get('ask') or 0
                current_price = (bid + ask) / 2 if bid and ask else 0
                current_spread = float(price_data.get('spread', 0) or 0)
                if not current_price:
                    continue
                now = datetime.utcnow()
                status = get_setup_status(
                    oanda_instrument, data_15m, data_1h, data_4h,
                    current_price, current_spread, now,
                )
                want_long = direction in ('LONG', 'BUY')
                trigger_met = (want_long and status.get('long_trigger_met')) or (not want_long and status.get('short_trigger_met'))
                if not trigger_met:
                    continue
                self.logger.info(
                    f"FT-DMI-EMA activation: 15m trigger met for {pair} {direction} (signal_id={signal_id})"
                )
                self.position_manager.pending_signals.pop(signal_id, None)
                self.position_manager._save_pending_signals()
                opp_with_order = dict(opportunity)
                opp_with_order['ft_15m_trigger_met'] = True
                opp_with_order['current_price'] = current_price
                opp_with_order['entry'] = opportunity.get('entry') or current_price
                opp_with_order['execution_config'] = dict(opportunity.get('execution_config') or {})
                if opp_with_order['execution_config'].get('mode') == 'IMMEDIATE_MARKET':
                    opp_with_order['order_type'] = 'MARKET'
                else:
                    opp_with_order['order_type'] = None
                try:
                    from src.ft_dmi_ema import StopLossCalculator
                    if data_1h is not None and len(data_1h) > 0:
                        stop_calc = StopLossCalculator()
                        stop_info = stop_calc.calculate_stop_loss(
                            data_1h=data_1h,
                            entry_price=opp_with_order['entry'],
                            direction=direction.lower(),
                            entry_time=now,
                            instrument=oanda_instrument,
                        )
                        opp_with_order['stop_loss'] = stop_info['stop_loss_price']
                        opp_with_order['initial_stop_loss'] = stop_info['stop_loss_price']
                except Exception as sl_e:
                    self.logger.debug(f"FT-DMI-EMA activation stop calculation: {sl_e}")
                trade = self._maybe_reset_run_count_and_open_trade(opp_with_order, market_state)
                if trade:
                    self.logger.info(f"✅ FT-DMI-EMA activation executed: {pair} {direction} (was waiting for 15m trigger)")
                else:
                    self.logger.warning(f"⚠️ FT-DMI-EMA activation failed to open trade: {pair} {direction}")
                self.position_manager._save_state()
            except Exception as e:
                self.logger.debug(f"FT-DMI-EMA activation check for {pair} {direction}: {e}")
                continue
        return
    
    def _review_and_replace_pending_trades(self, opportunities: List[Dict], market_state: Optional[Dict] = None):
        """
        Review pending trades and replace with better entry prices and updated position sizes if available.
        Direction is NEVER changed: we only consider same-direction opportunities for replacement.
        
        STRICT RULE: Only ONE order per pair is allowed. If a better price appears for a pair
        that already has a pending order (same direction), the existing order is cancelled first,
        then a new order is placed in this path (with record_run=False so max_runs is not consumed again).
        
        This checks if any pending orders have:
        1. A better entry price available in the new opportunities (same pair, SAME direction only)
        2. A different position size due to config changes (e.g., base_position_size changed)
        3. Entry price too far from current market price (stale order - unlikely to fill)
        
        Replaces them with updated orders or cancels stale ones. Never replaces with opposite direction.
        """
        if not self.position_manager or not self.position_manager.active_trades:
            return
        
        # Find all pending trades
        pending_trades = [
            (trade_id, trade)
            for trade_id, trade in self.position_manager.active_trades.items()
            if trade.state == TradeState.PENDING
        ]
        
        if not pending_trades:
            return
        
        # Get current market prices for all pending trade pairs
        pairs_to_check = [trade.pair for _, trade in pending_trades]
        current_prices = self._get_current_prices(pairs_to_check)
        
        replaced_count = 0
        cancelled_stale_count = 0
        
        for trade_id, trade in pending_trades:
            pair = trade.pair
            direction = trade.direction
            current_entry = trade.entry_price
            current_units = trade.units
            
            # CRITICAL: Check if pending order is stale (too far from current market price)
            # This prevents orders from staying pending indefinitely when market has moved significantly
            current_market_price = current_prices.get(pair)
            if current_market_price and current_market_price > 0:
                pip_size = 0.01 if 'JPY' in pair else 0.0001
                entry_distance = abs(current_entry - current_market_price)
                entry_distance_pips = entry_distance / pip_size
                
                # Threshold: 100 pips for JPY pairs, 50 pips for others
                # Orders beyond this are extremely unlikely to fill and should be cancelled
                stale_threshold_pips = 100.0 if 'JPY' in pair else 50.0
                
                if entry_distance_pips > stale_threshold_pips:
                    self.logger.warning(
                        f"🗑️ Cancelling stale pending order {trade_id}: {pair} {direction} @ {current_entry} "
                        f"is {entry_distance_pips:.1f} pips away from current price {current_market_price:.5f} "
                        f"(threshold: {stale_threshold_pips} pips). Order is unlikely to fill."
                    )
                    
                    # Cancel the stale order
                    order_id_to_cancel = trade.trade_id if trade.trade_id else trade_id
                    if self.position_manager.executor.cancel_order(
                        order_id_to_cancel,
                        f"Stale order: {entry_distance_pips:.1f} pips from current price"
                    ):
                        # Remove from active trades
                        if trade_id in self.position_manager.active_trades:
                            del self.position_manager.active_trades[trade_id]
                        cancelled_stale_count += 1
                        self.logger.info(
                            f"✅ Cancelled stale order {trade_id} - new recommendations can now be processed for {pair}"
                        )
                    else:
                        self.logger.error(
                            f"❌ Failed to cancel stale order {trade_id} for {pair}"
                        )
                        # Order may already be gone on OANDA (e.g. ORDER_DOESNT_EXIST) - remove from our state
                        if not self.position_manager.executor.check_order_exists(order_id_to_cancel):
                            if trade_id in self.position_manager.active_trades:
                                del self.position_manager.active_trades[trade_id]
                                self.position_manager._save_state()
                                self.logger.info(
                                    f"🧹 Removed phantom pending order {trade_id} ({pair}) - no longer exists on OANDA"
                                )
                    # Skip to next trade (this one is being cancelled or cleaned up)
                    continue
            
            # Get current entry price from the pending trade
            current_entry = trade.entry_price
            
            # Normalize pending trade direction for comparison (LONG vs SHORT)
            dir_raw = (direction or '').upper()
            direction_normalized = 'LONG' if dir_raw in ['LONG', 'BUY'] else 'SHORT' if dir_raw in ['SHORT', 'SELL'] else dir_raw
            
            # Find matching opportunities: same pair AND same direction only (never change user's direction)
            matching_opps = []
            for opp in opportunities:
                if opp.get('pair', '').upper() != pair.upper():
                    continue
                opp_dir = (opp.get('direction') or '').upper()
                opp_dir_n = 'LONG' if opp_dir in ['LONG', 'BUY'] else 'SHORT' if opp_dir in ['SHORT', 'SELL'] else opp_dir
                if opp_dir_n == direction_normalized:
                    matching_opps.append(opp)
            
            # Find the best opportunity for this pair (same direction only; never change direction)
            best_opp = None
            best_entry = current_entry
            
            for opp in matching_opps:
                opp_entry = opp.get('entry', 0.0)
                if opp_entry <= 0:
                    continue
                
                opp_dir = opp.get('direction', '').upper()
                opp_dir_normalized = 'LONG' if opp_dir in ['LONG', 'BUY'] else 'SHORT' if opp_dir in ['SHORT', 'SELL'] else opp_dir
                
                # Determine if this entry is better (same direction only)
                # For LONG/BUY: lower entry is better (buy cheaper)
                # For SHORT/SELL: higher entry is better (sell higher)
                is_better = False
                if opp_dir_normalized == 'LONG':
                    is_better = opp_entry < best_entry or (best_opp is None and opp_entry > 0)
                else:
                    is_better = opp_entry > best_entry or (best_opp is None and opp_entry > 0)
                
                if is_better:
                    best_entry = opp_entry
                    best_opp = opp
            
            # Calculate new position size based on current config (may have changed)
            consensus_level = trade.consensus_level
            base_size = self.config.base_position_size
            multiplier = self.config.consensus_multiplier.get(consensus_level, 1.0)
            new_units = base_size * multiplier
            
            # Check if we should replace (consol-recommend3 Phase 3.1: only when meaningfully changed or stale)
            # Thresholds configurable via env: REPLACE_ENTRY_MIN_PIPS (default 5), REPLACE_SL_TP_MIN_PIPS (default 5)
            replace_entry_min_pips = float(os.environ.get('REPLACE_ENTRY_MIN_PIPS', '5'))
            replace_sl_tp_min_pips = float(os.environ.get('REPLACE_SL_TP_MIN_PIPS', '5'))
            should_replace = False
            reason = ""
            
            if best_opp and best_entry != current_entry:
                entry_diff = abs(best_entry - current_entry)
                pip_size = 0.01 if 'JPY' in pair else 0.0001
                entry_diff_pips = entry_diff / pip_size
                
                if entry_diff_pips >= replace_entry_min_pips:
                    should_replace = True
                    reason = f"better entry price (better by {entry_diff_pips:.1f} pips)"
            
            # Meaningful stop/target change (same pair/direction opportunity)
            if best_opp and not should_replace:
                pip_size = 0.01 if 'JPY' in pair else 0.0001
                opp_sl = best_opp.get('stop_loss') or best_opp.get('initial_stop_loss')
                opp_tp = best_opp.get('exit') or best_opp.get('take_profit')
                if opp_sl and trade.stop_loss and abs(opp_sl - trade.stop_loss) / pip_size >= replace_sl_tp_min_pips:
                    should_replace = True
                    reason = f"stop loss changed ({replace_sl_tp_min_pips:.0f}+ pips)"
                if not should_replace and opp_tp and trade.take_profit and abs(opp_tp - trade.take_profit) / pip_size >= replace_sl_tp_min_pips:
                    should_replace = True
                    reason = reason or f"take profit changed ({replace_sl_tp_min_pips:.0f}+ pips)"
            
            # Check position size change (even if no matching opportunity)
            if abs(new_units - current_units) >= 1.0:
                should_replace = True
                if reason:
                    reason += f" and updated position size ({current_units:.0f} → {new_units:.0f} units)"
                else:
                    reason = f"updated position size ({current_units:.0f} → {new_units:.0f} units)"
                # If only position size changed (no better entry), use current entry
                if not best_opp:
                    best_entry = current_entry
            
            if should_replace:
                self.logger.warning(
                    f"🔄 Replacing pending order {trade_id}: {pair} {direction} "
                    f"@ {current_entry} → {best_entry if best_opp else current_entry} ({reason})"
                )
                
                # Cancel the old order FIRST (STRICT RULE: only one order per pair)
                order_id_to_cancel = trade.trade_id if trade.trade_id else trade_id
                if self.position_manager.executor.cancel_order(order_id_to_cancel, f"Replaced: {reason}"):
                    # Remove from active trades
                    if trade_id in self.position_manager.active_trades:
                        del self.position_manager.active_trades[trade_id]
                    
                    # Place new order in this path (record_run=False so max_runs is not consumed again).
                    # Always use the pending trade's direction (never change direction).
                    if market_state:
                        if best_opp:
                            opp = dict(best_opp)
                            opp['entry'] = best_entry
                            opp['direction'] = direction
                        else:
                            opp = {
                                'pair': pair,
                                'direction': direction,
                                'entry': best_entry,
                                'execution_config': (matching_opps[0].get('execution_config') or {}) if matching_opps else {},
                                'consensus_level': trade.consensus_level,
                            }
                            if matching_opps:
                                for k in ['llm_sources', 'source', 'stop_loss', 'initial_stop_loss']:
                                    if k in matching_opps[0]:
                                        opp[k] = matching_opps[0][k]
                        new_trade = self.position_manager.open_trade(opp, market_state, record_run=False)
                        if new_trade:
                            replaced_count += 1
                            self.logger.info(
                                f"✅ Replaced pending order {trade_id} - new order placed for {pair} {direction} @ {best_entry}"
                            )
                        else:
                            self.logger.warning(
                                f"⚠️ Replaced cancelled order {trade_id} but new order for {pair} was not placed (check above)"
                            )
                    else:
                        self.logger.warning(
                            f"⚠️ Cancelled old order {trade_id} for {pair} but cannot place replacement (no market_state)"
                        )
                else:
                    self.logger.error(
                        f"❌ Failed to cancel order {trade_id} for replacement - "
                        f"RED FLAG: Multiple orders may exist for {pair}"
                    )
                    # Order may already be gone on OANDA (e.g. ORDER_DOESNT_EXIST) - remove from our state
                    if not self.position_manager.executor.check_order_exists(order_id_to_cancel):
                        if trade_id in self.position_manager.active_trades:
                            del self.position_manager.active_trades[trade_id]
                            self.position_manager._save_state()
                            self.logger.info(
                                f"🧹 Removed phantom pending order {trade_id} ({pair}) - no longer exists on OANDA; list synced"
                            )
        
        if replaced_count > 0:
            self.logger.info(
                f"✅ Replaced {replaced_count} pending order(s) with updated prices/sizes"
            )
        
        if cancelled_stale_count > 0:
            self.logger.info(
                f"🗑️ Cancelled {cancelled_stale_count} stale pending order(s) that were too far from current market price"
            )
    
    def _check_hybrid_macd_triggers(self, market_state: Dict):
        """
        Check for MACD crossover triggers on pending HYBRID orders
        
        If MACD crossover is detected for a pending HYBRID order:
        1. Cancel the pending order
        2. Open trade immediately at market price
        """
        execution_mode = getattr(self.config, 'execution_mode', ExecutionMode.RECOMMENDED)
        # Handle string from config (e.g. when loaded from JSON)
        if isinstance(execution_mode, str):
            if execution_mode.upper() != 'HYBRID':
                return
        elif execution_mode != ExecutionMode.HYBRID:
            return
        
        if not self.position_manager or not self.oanda_client:
            return
        
        # Find all pending HYBRID trades
        pending_hybrid_trades = [
            (trade_id, trade)
            for trade_id, trade in self.position_manager.active_trades.items()
            if trade.state == TradeState.PENDING
        ]
        
        if not pending_hybrid_trades:
            return
        
        triggered_count = 0
        
        for trade_id, trade in pending_hybrid_trades:
            try:
                # Check if MACD crossover has occurred
                should_trigger, reason = self.position_manager.check_macd_crossover(
                    trade.pair, trade.direction, self.oanda_client
                )
                
                if should_trigger:
                    # MACD crossover detected - cancel pending order and open market trade
                    self.logger.info(
                        f"🎯 HYBRID: MACD crossover detected for pending order {trade_id} "
                        f"({trade.pair} {trade.direction}) - cancelling pending order and opening at market"
                    )
                    
                    # Cancel the pending order
                    if self.position_manager.executor.cancel_order(trade.trade_id, 
                                                                    "MACD crossover triggered - opening at market"):
                        # Remove from active trades
                        del self.position_manager.active_trades[trade_id]
                        
                        # Get current market price
                        current_prices = self._get_current_prices([trade.pair])
                        current_price = current_prices.get(trade.pair)
                        
                        if current_price:
                            # Update trade for MARKET execution
                            trade.order_type = 'MARKET'
                            trade.entry_price = current_price
                            
                            # CRITICAL: Check for duplicates before opening (we cancelled the pending order, but be safe)
                            # STRICT RULE: Only ONE order per pair is allowed
                            if self.position_manager.has_existing_position(trade.pair, trade.direction):
                                self.logger.error(
                                    f"🚨 RED FLAG: Cannot open HYBRID market trade - {trade.pair} already has an order "
                                    f"(ONLY ONE ORDER PER PAIR ALLOWED) - skipping"
                                )
                                continue
                            
                            # Open trade immediately at market
                            new_trade_id = self.position_manager.executor.open_trade(trade)
                            if new_trade_id:
                                trade.trade_id = new_trade_id
                                trade.state = TradeState.OPEN
                                trade.opened_at = datetime.utcnow()
                                
                                # CRITICAL: Check for duplicates before adding to active_trades
                                normalized_pair = self.position_manager.normalize_pair(trade.pair)
                                duplicate_found = False
                                for existing_key, existing_trade in self.position_manager.active_trades.items():
                                    if self.position_manager.normalize_pair(existing_trade.pair) == normalized_pair:
                                        self.logger.error(
                                            f"🚨 RED FLAG: Cannot add HYBRID trade - duplicate pair detected: "
                                            f"{normalized_pair} (Existing: {existing_key}, New: {new_trade_id}) - "
                                            f"ONLY ONE ORDER PER PAIR ALLOWED - skipping"
                                        )
                                        duplicate_found = True
                                        break
                                
                                if not duplicate_found:
                                    # Add back to active trades with new trade_id
                                    self.position_manager.active_trades[new_trade_id] = trade
                                    
                                    self.logger.info(
                                        f"✅ HYBRID: Opened trade {new_trade_id} at market price {current_price} "
                                        f"due to MACD crossover ({reason})"
                                    )
                                    triggered_count += 1
                                else:
                                    # Duplicate found - close the trade we just opened
                                    self.logger.error(
                                        f"🚨 RED FLAG: Closing duplicate trade {new_trade_id} that was just opened"
                                    )
                                    try:
                                        self.position_manager.executor.close_trade(new_trade_id, 
                                                                                  "RED FLAG: Duplicate pair detected")
                                    except:
                                        pass
                            else:
                                self.logger.error(
                                    f"❌ HYBRID: Failed to open market trade after MACD trigger for {trade.pair}"
                                )
                        else:
                            self.logger.warning(
                                f"⚠️ HYBRID: Could not get current price for {trade.pair} after MACD trigger"
                            )
                    else:
                        self.logger.warning(
                            f"⚠️ HYBRID: Failed to cancel pending order {trade_id} for {trade.pair}"
                        )
                        # Order may already be gone on OANDA - remove from our state
                        if trade.trade_id and not self.position_manager.executor.check_order_exists(trade.trade_id):
                            if trade_id in self.position_manager.active_trades:
                                del self.position_manager.active_trades[trade_id]
                                self.position_manager._save_state()
                                self.logger.info(
                                    f"🧹 Removed phantom pending order {trade_id} ({trade.pair}) - no longer exists on OANDA"
                                )
            except Exception as e:
                self.logger.error(
                    f"❌ Error checking MACD for hybrid trade {trade_id}: {e}", 
                    exc_info=True
                )
        
        if triggered_count > 0:
            self.position_manager._save_state()
            self.logger.info(f"✅ HYBRID: {triggered_count} pending order(s) triggered by MACD crossover")
    
    def _monitor_positions(self, market_state: Dict):
        """Monitor and update positions"""
        # CRITICAL: Sync with OANDA FIRST, even if active_trades is empty
        # This ensures we detect trades opened manually in OANDA or trades that exist
        # but aren't in our memory (e.g., after restart)
        # Sync with OANDA every check (1 minute) to detect externally opened/closed trades quickly
        # Pass market_state so excess trades can be closed based on relevance
        self.position_manager.sync_with_oanda(market_state)
        
        # If no trades after sync, nothing to monitor
        if not self.position_manager.active_trades:
            return
        
        # Check MACD reverse crossovers for open trades (every 5 minutes = every check)
        # This closes trades when MACD crosses in opposite direction
        # IMPORTANT: This protection works for ALL execution modes, not just MACD_CROSSOVER
        # It helps protect against trend reversals
        for trade_id, trade in list(self.position_manager.active_trades.items()):
            if trade.state == TradeState.OPEN:  # Only check open trades
                if self.position_manager.check_macd_reverse_crossover(trade, self.oanda_client):
                    # Close trade due to reverse crossover
                    self.position_manager.close_trade(
                        trade_id, 
                        f"MACD reverse crossover - {trade.pair} {trade.direction}"
                    )
        
        # Get pairs from active trades
        pairs = list(set(t.pair for t in self.position_manager.active_trades.values()))
        
        # Get current prices
        current_prices = self._get_current_prices(pairs)
        
        # Monitor positions (pass oanda_client for MACD_CROSSOVER stop loss)
        self.position_manager.monitor_positions(current_prices, market_state, self.oanda_client)
    
    def run(self):
        """Main run loop"""
        self.logger.info("🚀 Starting main loop...")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("")
        
        # Track last cleanup dates to avoid multiple cancellations
        last_end_of_day_cleanup_date = None  # For end of trading hours (21:30 UTC)
        last_start_of_day_cleanup_date = None  # For start of trading hours (01:00 UTC)
        last_fisher_scan_slot = None  # (date_utc, hour_utc) for hourly Fisher scan during trading hours
        
        try:
            while True:
                self.check_count += 1
                current_time = datetime.now(pytz.UTC)
                current_date_utc = current_time.date()
                current_hour_utc = current_time.hour
                current_minute_utc = current_time.minute
                
                if AUTO_TRADER_AVAILABLE and self.position_manager:
                    weekday = current_time.weekday()
                    
                    # 1. WEEKEND SHUTDOWN ENFORCEMENT (Saturday/Sunday)
                    # Close all trades and cancel all pending orders during weekend
                    if weekday in [5, 6]:  # Saturday (5) or Sunday (6)
                        # Check if we've already logged weekend shutdown this cycle
                        if not hasattr(self, '_weekend_shutdown_logged') or self._weekend_shutdown_logged != current_date_utc:
                            self.logger.warning(
                                f"\n🚫 WEEKEND SHUTDOWN - No trading allowed (Weekday: {weekday})"
                            )
                            self._weekend_shutdown_logged = current_date_utc
                        
                        # Close all open trades (monitoring will handle this via should_close_trade)
                        # Cancel all pending orders
                        cancelled = self.position_manager.cancel_all_pending_orders(
                            reason="Weekend shutdown - cancel all pending orders"
                        )
                        if cancelled > 0:
                            # Throttle: first per window at WARNING, rest at DEBUG (suggestions cursor3 §5.7)
                            now_ts = time.time()
                            last_ts = self._weekend_cancel_last_logged
                            if last_ts is None or (now_ts - last_ts) >= self._weekend_cancel_window_seconds:
                                self.logger.warning(f"🚫 Weekend shutdown: Cancelled {cancelled} pending order(s)")
                                self._weekend_cancel_last_logged = now_ts
                            else:
                                self.logger.debug(f"🚫 Weekend shutdown: Cancelled {cancelled} pending order(s) (throttled)")
                    
                    # 2. END OF TRADING WEEK CLEANUP (Friday 21:30 UTC)
                    # Close all trades and cancel all pending orders at end of trading week
                    # Includes orphan detection and verification (Phase 1 enhancement)
                    # Only runs on Friday (weekday == 4)
                    if weekday == 4 and current_hour_utc == 21 and current_minute_utc >= 30 and last_end_of_day_cleanup_date != current_date_utc:
                        # Use enhanced cleanup with orphan detection and verification
                        cleanup_result = self.position_manager._end_of_day_cleanup(
                            reason="Friday 21:30 UTC - End of trading week"
                        )

                        # Alert if orphaned orders were detected
                        if cleanup_result["orphaned_detected"] > 0:
                            self.logger.warning(
                                f"🚨 ALERT: {cleanup_result['orphaned_detected']} orphaned order(s) "
                                f"detected on OANDA and {cleanup_result['orphaned_cancelled']} cancelled. "
                                f"Check logs for details."
                            )

                        last_end_of_day_cleanup_date = current_date_utc
                    
                    # 3. START OF TRADING WEEK SAFETY CHECK (Monday 01:00 UTC)
                    # Cancel any remaining stale pending orders before new trading begins
                    # Only runs on Monday (weekday == 0)
                    if weekday == 0 and current_hour_utc == 1 and current_minute_utc < 2 and last_start_of_day_cleanup_date != current_date_utc:
                        self.logger.info(
                            f"\n🕐 Monday 01:00 UTC - Start of trading week: Safety check - cancelling any stale pending orders"
                        )
                        cancelled = self.position_manager.cancel_all_pending_orders(
                            reason="Start of trading week - cancel stale pending orders (safety check)"
                        )
                        last_start_of_day_cleanup_date = current_date_utc
                        if cancelled > 0:
                            self.logger.warning(
                                f"⚠️ Found {cancelled} stale pending order(s) at start of trading week - cancelled to prevent trading with old market state"
                            )
                        else:
                            self.logger.info("✅ No stale pending orders found at start of trading week - safe to begin trading")
                    
                    # 3. DAILY RL LEARNING CYCLE (23:00 UTC / 11:00 PM UTC)
                    # Run daily learning to evaluate pending signals and update LLM weights
                    if current_hour_utc == 23 and current_minute_utc < 2 and not hasattr(self, 'last_learning_date'):
                        self.last_learning_date = None
                    
                    if current_hour_utc == 23 and current_minute_utc < 2 and self.last_learning_date != current_date_utc:
                        try:
                            from src.daily_learning import run_daily_learning
                            self.logger.info("\n🧠 Starting daily RL learning cycle (23:00 UTC)...")
                            run_daily_learning()
                            self.last_learning_date = current_date_utc
                            self.logger.info("✅ Daily RL learning cycle complete")
                        except Exception as e:
                            self.logger.error(f"❌ Error running daily learning cycle: {e}", exc_info=True)
                
                # 4. HOURLY FISHER SCAN (during trading hours: Mon 01:00 UTC - Fri 21:30 UTC)
                # Run Fisher Transform scanner every hour when within trading hours; results go to market_state
                _weekday = current_time.weekday()
                in_trading_hours = (
                    (_weekday in (1, 2, 3))  # Tue, Wed, Thu: full day
                    or (_weekday == 0 and (current_hour_utc > 1 or (current_hour_utc == 1 and current_minute_utc >= 0)))  # Mon from 01:00
                    or (_weekday == 4 and (current_hour_utc < 21 or (current_hour_utc == 21 and current_minute_utc <= 30)))  # Fri until 21:30
                )
                current_slot = (current_date_utc, current_hour_utc)
                if in_trading_hours and current_minute_utc < 2 and last_fisher_scan_slot != current_slot:
                    try:
                        from src.scanners.fisher_daily_scanner import FisherDailyScanner
                        from src.integration.fisher_market_bridge import FisherMarketBridge, post_fisher_to_api
                        self.logger.info("\n🎯 Starting hourly Fisher Transform scan (trading hours, Reversal Strategy)...")
                        scanner = FisherDailyScanner(self.oanda_api)
                        market_state = self._read_market_state()
                        result = scanner.scan(market_state=market_state)
                        fisher_opps = result.get('opportunities', [])
                        fisher_analysis = result.get('fisher_analysis', {})
                        if post_fisher_to_api(fisher_opps, fisher_analysis=fisher_analysis):
                            self.logger.info("✅ Fisher opportunities sent to market-state-api")
                        else:
                            bridge = FisherMarketBridge()
                            bridge.add_fisher_opportunities(fisher_opps, fisher_analysis=fisher_analysis)
                        last_fisher_scan_slot = current_slot
                        self.logger.info(f"✅ Hourly Fisher scan complete: {len(fisher_opps)} opportunities")
                    except Exception as e:
                        self.logger.error(f"❌ Error running Fisher scan: {e}", exc_info=True)

                # 5a. CHECK FOR MANUAL SYNC TRIGGER (Manual button from UI)
                # User can trigger sync check via UI manual button
                trigger_file = '/var/data/sync_check_trigger.flag'
                manual_sync_requested = False
                try:
                    if os.path.exists(trigger_file):
                        manual_sync_requested = True
                        os.remove(trigger_file)
                        self.logger.info("📞 Manual sync check requested via UI button")
                except Exception as e:
                    self.logger.error(f"❌ Error checking trigger file: {e}")

                # 5. HOURLY PERIODIC SYNC CHECK (Phase 2 Enhancement)
                # Run every hour during trading hours to detect UI/OANDA drift
                # Catches orphaned orders that appear between end-of-day cleanups
                # ALSO runs immediately if manual sync requested via UI
                should_run_periodic_sync = (
                    (in_trading_hours and current_minute_utc < 2 and last_fisher_scan_slot != current_slot)
                    or manual_sync_requested
                )
                if should_run_periodic_sync:
                    try:
                        sync_result = self.position_manager._periodic_sync_check()

                        # Alert if discrepancies found
                        if sync_result["discrepancies"] > 0:
                            self.logger.warning(
                                f"🚨 SYNC DISCREPANCY ALERT: {sync_result['discrepancies']} orphaned "
                                f"order(s) detected on OANDA. "
                                f"Cancelled: {sync_result['orphaned_cancelled']}"
                            )
                        # Note: _periodic_sync_check() logs detailed information about each order
                    except Exception as e:
                        self.logger.error(f"❌ Error during periodic sync check: {e}", exc_info=True)

                # Note: Config reload now happens in _auto_trader_mode_check() before each market state check
                # This ensures we always use the latest config (similar to Indicator-Alerts pattern)
                
                # Log status every 10 checks (10 minutes)
                if self.check_count % 10 == 0:
                    self.logger.info(f"\n=== Status Check #{self.check_count} ===")
                    self.logger.info(f"Time: {current_time.strftime('%H:%M:%S UTC')}")
                    
                    if AUTO_TRADER_AVAILABLE:
                        self.logger.info(f"Mode: {self.config.trading_mode.value}")
                        self.logger.info(f"Stop Loss Type: {self.config.stop_loss_type.value}")
                        active = len(self.position_manager.active_trades) if self.position_manager else 0
                        max_trades = self.config.max_open_trades
                        self.logger.info(f"Active Trades: {active}/{max_trades}")
                        
                        # Show pending orders count
                        if self.position_manager:
                            pending = sum(
                                1 for t in self.position_manager.active_trades.values()
                                if t.state == TradeState.PENDING
                            )
                            if pending > 0:
                                self.logger.info(f"Pending Orders: {pending}")
                
                try:
                    # ALWAYS reload config before checking mode (like Indicator-Alerts pattern)
                    # This ensures we can switch from MANUAL to AUTO when UI config changes
                    # Check config file every 30 seconds (2-5 minute range as requested)
                    current_time_check = time.time()
                    if AUTO_TRADER_AVAILABLE:
                        if (current_time_check - self.last_config_check_time) >= self.config_check_interval:
                            self._reload_config_if_changed()
                            self.last_config_check_time = current_time_check
                    
                    # Determine mode after reload
                    if AUTO_TRADER_AVAILABLE and self.config.trading_mode != TradingMode.MANUAL:
                        # Auto-trading mode
                        self._auto_trader_mode_check()
                    else:
                        # Monitor-only mode (original behavior)
                        self._monitor_mode_check()
                    
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}", exc_info=True)
                
                # Wait before next check
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            self.logger.info("\n⚠️ System stopped by user")
            
            # Close all positions if in auto mode
            if AUTO_TRADER_AVAILABLE and self.position_manager:
                self.logger.info("Closing all open positions...")
                for trade_id in list(self.position_manager.active_trades.keys()):
                    self.position_manager.close_trade(trade_id, "System shutdown")
                self.logger.info("✅ All positions closed")
            
        except Exception as e:
            self.logger.error(f"❌ Fatal error: {e}", exc_info=True)
            raise


def main():
    """Main entry point"""
    engine = ScalpEngine()
    engine.run()


if __name__ == '__main__':
    main()
