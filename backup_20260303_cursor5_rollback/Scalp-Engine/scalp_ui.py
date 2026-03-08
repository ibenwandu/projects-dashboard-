"""
Scalp-Engine UI: Streamlit dashboard for viewing scalping opportunities
"""
import streamlit as st
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import pandas as pd
import requests
import time
import logging
import os

# ============================================================================
# FLASK API SERVER - REMOVED
# ============================================================================
# No longer needed - we now have a separate config-api service
# (Similar to market-state-api pattern)
# The config-api service runs on the same disk as this UI, so it can read
# the config file directly without needing Flask here.

# ============================================================================
# PATH SETUP FOR RENDER DEPLOYMENT
# ============================================================================
# On Render, the file might be at /opt/render/project/src/scalp_ui.py
# or /opt/render/project/scalp_ui.py. We need to find the actual project root.
# ============================================================================

import os

# Get the directory where this file is located
current_file_dir = Path(__file__).parent.absolute()

# CRITICAL FIX: Handle Render's incorrect path structure
# On Render, the file might be at /opt/render/project/src/Scalp-Engine/scalp_ui.py
# But it should be at /opt/render/project/Scalp-Engine/scalp_ui.py
# We need to find the actual Scalp-Engine directory

# Strategy 1: Check if we're in a nested src/Scalp-Engine structure (Render bug)
if 'src' in current_file_dir.parts and 'Scalp-Engine' in current_file_dir.parts:
    # Find the Scalp-Engine directory in the path
    parts = current_file_dir.parts
    scalp_engine_idx = parts.index('Scalp-Engine')
    # Go up to the project root, then down to Scalp-Engine
    project_root = Path(*parts[:parts.index('opt') + 2])  # /opt/render/project
    scalp_engine_dir = project_root / "Scalp-Engine"
    if scalp_engine_dir.exists():
        # We're in the wrong location, but Scalp-Engine exists at correct path
        # Set project_root to Scalp-Engine's parent and use Scalp-Engine as base
        project_root = scalp_engine_dir.parent  # /opt/render/project
        src_dir = scalp_engine_dir / "src"  # /opt/render/project/Scalp-Engine/src
    else:
        # Fallback: try to find Scalp-Engine directory
        project_root = current_file_dir.parent.parent  # Go up 2 levels
        src_dir = project_root / "Scalp-Engine" / "src"
elif current_file_dir.name == 'src':
    # We're in Scalp-Engine/src/
    project_root = current_file_dir.parent.parent  # /opt/render/project
    src_dir = current_file_dir  # Already in src/
elif current_file_dir.name == 'Scalp-Engine':
    # We're in Scalp-Engine/ directory (correct location)
    project_root = current_file_dir.parent  # /opt/render/project
    src_dir = current_file_dir / "src"  # /opt/render/project/Scalp-Engine/src
else:
    # Default: assume we're in Scalp-Engine/ directory
    project_root = current_file_dir.parent if current_file_dir.name != 'Scalp-Engine' else current_file_dir
    src_dir = project_root / "Scalp-Engine" / "src" if current_file_dir.name != 'Scalp-Engine' else current_file_dir / "src"

# Strategy 2: Verify src_dir exists, if not try alternative paths
if not src_dir.exists():
    # Try alternative: /opt/render/project/Scalp-Engine/src
    alt_src_dir = Path('/opt/render/project') / "Scalp-Engine" / "src"
    if alt_src_dir.exists():
        src_dir = alt_src_dir
        project_root = Path('/opt/render/project')

# Add Scalp-Engine directory to Python path (this allows 'from src.xxx' imports)
scalp_engine_dir = src_dir.parent if src_dir.name == 'src' else project_root / "Scalp-Engine"
if scalp_engine_dir.exists() and str(scalp_engine_dir) not in sys.path:
    sys.path.insert(0, str(scalp_engine_dir))

# Add src directory directly (fallback for direct imports)
if src_dir.exists() and str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Debug: Log paths (will show in Streamlit if there's an error)
_debug_paths = {
    'current_file': str(Path(__file__)),
    'current_dir': str(current_file_dir),
    'project_root': str(project_root),
    'src_dir': str(src_dir),
    'sys_path': sys.path[:3]  # First 3 entries
}

# ============================================================================
# LOGGER SETUP FOR UI
# ============================================================================
_ui_logger = logging.getLogger('ScalpUI')
if not _ui_logger.handlers:
    _ui_logger.addHandler(logging.StreamHandler())
    _ui_logger.setLevel(logging.INFO)

try:
    from src.logger import attach_file_handler
    print("🔍 [ScalpUI] Attempting to attach file handler...")
    attach_file_handler(['ScalpUI'], 'scalp_ui')
    print("✅ [ScalpUI] File handler attached successfully")
except ImportError as e:
    print(f"⚠️ [ScalpUI] Logger module not available - stdout only: {e}")
except Exception as e:
    print(f"❌ [ScalpUI] Failed to attach file handler: {e}")

# Push UI log file to config-api so backup agent can read it (Render disks are per-service)
try:
    config_api_url = os.getenv('CONFIG_API_URL')
    if config_api_url:
        from src.log_sync import start_log_sync_thread, COMPONENT_PREFIXES
        ui_only = [(c, p) for c, p in COMPONENT_PREFIXES if c == 'ui']
        start_log_sync_thread(config_api_url, ui_only, interval_seconds=60)
        print("[ScalpUI] Log sync to config-api started (every 60s)")
    else:
        print("[ScalpUI] CONFIG_API_URL not set - log sync disabled")
except Exception as e:
    print(f"[ScalpUI] Log sync failed to start: {e}")

logger = _ui_logger

# Stop loss type display labels (used in Semi-Auto Approval and Fisher tab)
SL_TYPE_LABELS = {
    'FIXED': 'Fixed',
    'BE_TO_TRAILING': 'BE → Trailing',
    'ATR_TRAILING': 'ATR Trailing',
    'MACD_CROSSOVER': 'MACD crossover exit',
    'DMI_CROSSOVER': 'DMI crossover exit',
    'STRUCTURE_ATR': 'ATR + structure',
    'STRUCTURE_ATR_STAGED': 'Staged: BE (+1R) → Partial (+2R) → Trail (+3R)',  # CHANGED: Now works for all opportunities
}

# Import modules - try multiple strategies
try:
    # Strategy 1: Standard import (works when project_root is in sys.path)
    from src.state_reader import MarketStateReader
    from src.scalping_rl import ScalpingRL
except ImportError as e1:
    try:
        # Strategy 2: Direct import (works when src_dir is in sys.path)
        from state_reader import MarketStateReader
        from scalping_rl import ScalpingRL
    except ImportError as e2:
        # Strategy 3: Absolute import
        import importlib.util
        state_reader_path = src_dir / "state_reader.py"
        scalping_rl_path = src_dir / "scalping_rl.py"
        
        if state_reader_path.exists() and scalping_rl_path.exists():
            spec1 = importlib.util.spec_from_file_location("state_reader", state_reader_path)
            spec2 = importlib.util.spec_from_file_location("scalping_rl", scalping_rl_path)
            state_reader_module = importlib.util.module_from_spec(spec1)
            scalping_rl_module = importlib.util.module_from_spec(spec2)
            spec1.loader.exec_module(state_reader_module)
            spec2.loader.exec_module(scalping_rl_module)
            MarketStateReader = state_reader_module.MarketStateReader
            ScalpingRL = scalping_rl_module.ScalpingRL
        else:
            # Last resort: show helpful error with all debug info
            raise ImportError(
                f"Could not import modules. Debug info: {_debug_paths}\n"
                f"Strategy 1 error: {e1}\n"
                f"Strategy 2 error: {e2}\n"
                f"Files exist: state_reader={state_reader_path.exists()}, scalping_rl={scalping_rl_path.exists()}\n"
                f"State reader path: {state_reader_path}\n"
                f"Scalping RL path: {scalping_rl_path}\n"
                f"src_dir exists: {src_dir.exists()}\n"
                f"src_dir contents: {list(src_dir.iterdir()) if src_dir.exists() else 'Directory does not exist'}"
            )

# Semi-auto controller (optional - for Fisher per-opportunity enable/mode/config)
try:
    from src.execution.semi_auto_controller import SemiAutoController
except ImportError:
    try:
        from execution.semi_auto_controller import SemiAutoController
    except ImportError:
        SemiAutoController = None

# Stable opportunity ID (must match engine opportunity_id so re-enable + reset run count work)
try:
    from src.execution.opportunity_id import get_stable_opportunity_id
except ImportError:
    try:
        from execution.opportunity_id import get_stable_opportunity_id
    except ImportError:
        get_stable_opportunity_id = None


def _normalized_stable_opp_id(opp) -> str:
    """Fallback when get_stable_opportunity_id is not available. Must match opportunity_id.py exactly."""
    pair_raw = (opp.get('pair') or '').strip().replace('_', '/')
    pair = pair_raw.upper() if pair_raw else ''
    direction_raw = (opp.get('direction') or '').strip().upper()
    direction = 'LONG' if direction_raw in ('LONG', 'BUY') else 'SHORT' if direction_raw in ('SHORT', 'SELL') else direction_raw
    return f"{pair}_{direction}" if pair and direction else (opp.get('id') or '')

# Execution mode labels (FT = Fisher Transform crossover)
EXEC_MODE_LABELS = {
    'MARKET': 'MARKET', 'RECOMMENDED': 'RECOMMENDED', 'MACD_CROSSOVER': 'MACD crossover',
    'HYBRID': 'HYBRID', 'FISHER_H1_CROSSOVER': 'FT crossover (1h)', 'FISHER_M15_CROSSOVER': 'FT crossover (15m)',
    'MANUAL': 'MANUAL', 'RECOMMENDED_PRICE': 'Recommended price', 'IMMEDIATE_MARKET': 'Immediate market',
}

# Determine database path (Render uses /var/data, local uses current dir)
DB_PATH = os.getenv('SCALP_DB_PATH', 'scalping_rl.db')
if os.path.exists('/var/data/scalping_rl.db'):
    DB_PATH = '/var/data/scalping_rl.db'

# Page configuration
st.set_page_config(
    page_title="Scalp-Engine Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .opportunity-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        background-color: #f0f2f6;
        margin-bottom: 1rem;
    }
    .timestamp {
        color: #666;
        font-size: 0.9rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.85rem;
        font-weight: bold;
    }
    .status-active {
        background-color: #28a745;
        color: white;
    }
    .status-pending {
        background-color: #ffc107;
        color: black;
    }
    .status-closed {
        background-color: #6c757d;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=30)  # Cache for 30 seconds
def load_market_state():
    """Load market state from market-state-api (preferred) or file. API-first so UI and engine share data without shared disk."""
    try:
        # Get and clean file path for fallback
        env_path_raw = os.getenv('MARKET_STATE_FILE_PATH', '/var/data/market_state.json')
        if env_path_raw:
            env_path_clean = str(env_path_raw).strip()
            if env_path_clean.endswith('.jsc'):
                env_path_clean = env_path_clean[:-4] + '.json'
            elif env_path_clean.endswith('.jsor'):
                env_path_clean = env_path_clean[:-5] + '.json'
            elif not env_path_clean.endswith('.json'):
                if '/var/data/market_state' in env_path_clean or env_path_clean == '/var/data/market_state':
                    env_path_clean = '/var/data/market_state.json'
                elif 'market_state' in env_path_clean:
                    env_path_clean = env_path_clean.split('market_state')[0] + 'market_state.json'
                elif env_path_clean.endswith('/var/data/'):
                    env_path_clean = '/var/data/market_state.json'
                else:
                    env_path_clean = '/var/data/market_state.json'
        else:
            env_path_clean = '/var/data/market_state.json'
        if not env_path_clean.endswith('.json'):
            env_path_clean = '/var/data/market_state.json'
        
        reader = MarketStateReader(state_file_path=env_path_clean)
        # API-first: load_state() tries MARKET_STATE_API_URL then file (no shared disk needed)
        state = reader.load_state()
        if state is not None:
            return state
        
        # state is None (API failed or file missing/stale)
        file_exists = reader.state_file_path.exists()
        actual_path_str = str(reader.state_file_path)
        if not file_exists:
            # File doesn't exist - show debug info
            parent_files = []
            parent_dir_str = str(reader.state_file_path.parent)
            parent_exists = reader.state_file_path.parent.exists()
            parent_writable = os.access(reader.state_file_path.parent, os.W_OK) if parent_exists else False
            
            if parent_exists:
                try:
                    all_items = list(reader.state_file_path.parent.iterdir())
                    parent_files = sorted([f.name for f in all_items if f.is_file()])
                    if not parent_files:
                        parent_files = ["(no files found in directory)"]
                except Exception as e:
                    parent_files = [f"⚠️ Error listing: {str(e)}"]
            
            with st.sidebar:
                api_note = "\n- Set MARKET_STATE_API_URL so UI loads from market-state-api (no shared disk)." if os.getenv('MARKET_STATE_API_URL') else ""
                st.error(
                    f"**Market state not available.**\n"
                    f"- Path: `{actual_path_str}`\n"
                    f"- Parent dir: `{parent_dir_str}`\n"
                    f"- Parent exists: {parent_exists}\n"
                    f"- Files in parent: {', '.join(parent_files[:10]) if parent_files else 'Cannot list'}"
                    f"{api_note}"
                )
            return None
        
        # state is None and file exists - diagnose why (stale, invalid JSON, missing fields)
        if file_exists:
            try:
                # Try to read the file directly to diagnose the issue
                with open(reader.state_file_path, 'r', encoding='utf-8') as f:
                    raw_state = json.load(f)
                
                # Check for missing required fields first
                required_fields = ['timestamp', 'global_bias', 'regime', 'approved_pairs']
                missing_fields = [f for f in required_fields if f not in raw_state]
                if missing_fields:
                    with st.sidebar:
                        st.error(f"**Missing Required Fields:** {', '.join(missing_fields)}")
                        st.json(raw_state)
                    return None
                
                # Check if state is stale (older than 4 hours)
                if 'timestamp' in raw_state:
                    try:
                        from datetime import datetime
                        import pytz
                        timestamp = datetime.fromisoformat(raw_state['timestamp'].replace('Z', '+00:00'))
                        now = datetime.now(pytz.UTC)
                        age_hours = (now - timestamp).total_seconds() / 3600
                        
                        if age_hours > 4:
                            # State is stale - show warning but still display it for debugging
                            with st.sidebar:
                                st.warning(
                                    f"**Market State is Stale:**\n"
                                    f"- File exists: ✅\n"
                                    f"- Timestamp: `{raw_state['timestamp']}`\n"
                                    f"- Age: {age_hours:.1f} hours (threshold: 4 hours)\n"
                                    f"- ⚠️ State is older than 4 hours, may not reflect current market conditions\n\n"
                                    f"**Root Cause:** Trade-Alerts scheduled analysis (4pm EST) likely didn't complete or didn't run.\n\n"
                                    f"**Temporary Workaround:**\n"
                                    f"Run from **repo root** (Trade-Alerts) in Render Shell: `python update_market_state_timestamp.py` (requires same disk as market state file, e.g. scalp-engine-ui or trade-alerts).\n\n"
                                    f"**Real Fix:** Check Trade-Alerts logs for:\n"
                                    f"1. `=== Scheduled Analysis Time: ... 16:XX:XX EST ===`\n"
                                    f"2. `Step 9 (NEW): Exporting market state...`\n"
                                    f"3. `✅ Market State exported to /var/data/market_state.json`\n\n"
                                    f"See `DIAGNOSE_MISSING_MARKET_STATE.md` for details."
                                )
                            # Return the stale state anyway for display (temporary for testing)
                            # The UI will show it with a warning
                            return raw_state
                    except (ValueError, KeyError) as e:
                        with st.sidebar:
                            st.error(f"**Invalid Timestamp Format:** `{raw_state.get('timestamp', 'N/A')}` - Error: {e}")
                        return None
                
                # If we get here, state loaded but was None for unknown reason
                with st.sidebar:
                    st.warning(
                        f"**State Not Loaded (Unknown Reason):**\n"
                        f"- File exists: ✅\n"
                        f"- File is valid JSON: ✅\n"
                        f"- Required fields present: ✅\n"
                        f"- Check reader.load_state() for other validation failures"
                    )
                
            except json.JSONDecodeError as e:
                with st.sidebar:
                    st.error(f"**Invalid JSON:** File exists but contains invalid JSON\n- Error: {e}")
                return None
            except Exception as e:
                with st.sidebar:
                    st.error(f"**Error Reading File:** {e}")
                    import traceback
                    st.code(traceback.format_exc())
                return None
        
        return None
    except Exception as e:
        st.error(f"Error loading market state: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None


def _format_fisher_scan_time_est(iso_utc: str) -> str:
    """Format Fisher last_updated (UTC ISO) for display in EST. Returns e.g. 'Feb 1, 2026, 5:00 PM EST' or 'N/A'."""
    if not iso_utc or not iso_utc.strip():
        return "N/A"
    try:
        from datetime import datetime
        import pytz
        # Parse UTC ISO (allow Z or +00:00)
        s = iso_utc.strip().replace("Z", "+00:00")
        if "." in s and "+" not in s and "Z" not in iso_utc:
            s = s + "+00:00"
        dt_utc = datetime.fromisoformat(s)
        if dt_utc.tzinfo is None:
            dt_utc = pytz.UTC.localize(dt_utc)
        est = pytz.timezone("America/New_York")
        dt_est = dt_utc.astimezone(est)
        return dt_est.strftime("%b %d, %Y, %I:%M %p EST").replace(", 0", ", ", 1)
    except Exception:
        return iso_utc[:19] if len(iso_utc) >= 19 else iso_utc


@st.cache_data(ttl=15)
def load_fisher_opportunities():
    """
    Load Fisher opportunities from market-state-api.
    Returns (fisher_opps, fisher_count, fisher_updated).
    """
    state = load_market_state()
    if state:
        opps = state.get('fisher_opportunities', [])
        return (opps, state.get('fisher_count', len(opps)), state.get('fisher_last_updated', ''))
    return ([], 0, '')


@st.cache_data(ttl=15)
def load_ft_dmi_ema_opportunities():
    """
    Load FT-DMI-EMA opportunities from market state.
    Returns (ft_dmi_ema_opps, ft_dmi_ema_count, ft_dmi_ema_last_updated).
    """
    state = load_market_state()
    if state:
        opps = state.get('ft_dmi_ema_opportunities', [])
        return (opps, len(opps), state.get('ft_dmi_ema_last_updated', ''))
    return ([], 0, '')


@st.cache_data(ttl=15)
def load_dmi_ema_opportunities():
    """
    Load DMI-EMA opportunities from market state.
    Returns (dmi_ema_opps, dmi_ema_count, dmi_ema_last_updated).
    """
    state = load_market_state()
    if state:
        opps = state.get('dmi_ema_opportunities', [])
        return (opps, len(opps), state.get('dmi_ema_last_updated', ''))
    return ([], 0, '')


@st.cache_data(ttl=30)
def load_recent_signals(limit=20):
    """Load recent signals from RL database"""
    try:
        rl = ScalpingRL(DB_PATH)
        conn = sqlite3.connect(DB_PATH)
        
        query = """
            SELECT 
                id,
                timestamp,
                pair,
                direction,
                regime,
                strength,
                ema_spread,
                outcome,
                pnl,
                position_size,
                hour
            FROM signals
            ORDER BY timestamp DESC
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        
        return df
    except Exception as e:
        st.error(f"Error loading signals: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=30)
def get_performance_stats():
    """Get overall performance statistics"""
    try:
        rl = ScalpingRL(DB_PATH)
        conn = sqlite3.connect(DB_PATH)
        
        # Overall stats
        overall = pd.read_sql_query("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                AVG(pnl) as avg_pnl,
                SUM(pnl) as total_pnl
            FROM signals
            WHERE outcome != 'PENDING'
        """, conn)
        
        # By regime
        by_regime = pd.read_sql_query("""
            SELECT 
                regime,
                COUNT(*) as total,
                ROUND(100.0 * SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
                AVG(pnl) as avg_pnl
            FROM signals
            WHERE outcome != 'PENDING'
            GROUP BY regime
        """, conn)
        
        # By pair
        by_pair = pd.read_sql_query("""
            SELECT 
                pair,
                COUNT(*) as total,
                ROUND(100.0 * SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
                AVG(pnl) as avg_pnl
            FROM signals
            WHERE outcome != 'PENDING'
            GROUP BY pair
            ORDER BY total DESC
            LIMIT 10
        """, conn)
        
        conn.close()
        
        return overall, by_regime, by_pair
    except Exception as e:
        st.error(f"Error loading performance stats: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def format_timestamp(timestamp_str):
    """Format timestamp and calculate age"""
    try:
        if isinstance(timestamp_str, str):
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            dt = timestamp_str
        
        now = datetime.now(dt.tzinfo if hasattr(dt, 'tzinfo') else None)
        age = now - dt.replace(tzinfo=None) if hasattr(dt, 'tzinfo') else now - dt
        
        if age.total_seconds() < 60:
            age_str = f"{int(age.total_seconds())} seconds ago"
        elif age.total_seconds() < 3600:
            age_str = f"{int(age.total_seconds() / 60)} minutes ago"
        elif age.total_seconds() < 86400:
            age_str = f"{int(age.total_seconds() / 3600)} hours ago"
        else:
            age_str = f"{int(age.total_seconds() / 86400)} days ago"
        
        return dt.strftime("%Y-%m-%d %H:%M:%S"), age_str
    except:
        return str(timestamp_str), "Unknown"


# ============================================================================
# AUTO-TRADER UI FUNCTIONS
# ============================================================================

def render_semi_auto_approval():
    """
    Semi-Auto Approval: Configure which LLM and Fisher opportunities to execute.
    Visible when Trading Mode is SEMI_AUTO. This is the primary configuration
    window for semi-auto mode.
    """
    st.header("✅ Semi-Auto Approval")
    st.caption("Enable or disable each opportunity for execution. Only enabled trades will be executed by the engine.")
    
    market_state = load_market_state()
    if not market_state:
        st.warning("⚠️ Could not load market state. Refresh or check that Trade-Alerts / market-state-api is running.")
        return
    
    semi_auto = SemiAutoController() if SemiAutoController else None
    if not semi_auto:
        st.error("SemiAutoController not available. Check deployment.")
        return
    
    llm_opps = market_state.get('opportunities', [])
    fisher_opps = market_state.get('fisher_opportunities', [])
    ft_dmi_ema_opps = market_state.get('ft_dmi_ema_opportunities', [])
    dmi_ema_opps = market_state.get('dmi_ema_opportunities', [])
    
    # Execution modes: value -> friendly label (FT = Fisher Transform, DMI = +DI/-DI crossover)
    EXEC_MODE_LABELS = {
        'MARKET': 'MARKET',
        'RECOMMENDED': 'RECOMMENDED',
        'MACD_CROSSOVER': 'MACD crossover',
        'HYBRID': 'HYBRID',
        'FISHER_H1_CROSSOVER': 'FT crossover (1h)',
        'FISHER_M15_CROSSOVER': 'FT crossover (15m)',
        'DMI_H1_CROSSOVER': 'DMI crossover (1h)',
        'DMI_M15_CROSSOVER': 'DMI crossover (15m)',
        'MANUAL': 'MANUAL',
        'RECOMMENDED_PRICE': 'Recommended price',
        'IMMEDIATE_MARKET': 'Immediate market',
        'FISHER_M15_TRIGGER': '15m Fisher trigger, then market',
    }
    EXEC_MODES_LLM = ['MARKET', 'RECOMMENDED', 'FISHER_H1_CROSSOVER', 'FISHER_M15_CROSSOVER', 'DMI_H1_CROSSOVER', 'DMI_M15_CROSSOVER', 'MACD_CROSSOVER', 'HYBRID']
    EXEC_MODES_FISHER = ['MANUAL', 'FISHER_H1_CROSSOVER', 'FISHER_M15_CROSSOVER', 'DMI_H1_CROSSOVER', 'DMI_M15_CROSSOVER', 'RECOMMENDED_PRICE', 'IMMEDIATE_MARKET']
    # FT-DMI-EMA: 4H+1H already done for pair to appear; final step = 15min FT-crossover (option + Enable triggers trade)
    EXEC_MODES_FT_DMI_EMA = ['FISHER_M15_TRIGGER']
    EXEC_MODE_LABELS_FT_DMI_EMA = {'FISHER_M15_TRIGGER': '15min FT-crossover'}
    # DMI-EMA: 1D/4H/1H DMI+EMA; trigger options: 15m FT, 15m +DI/-DI, or immediate
    EXEC_MODES_DMI_EMA = ['FISHER_M15_TRIGGER', 'DMI_M15_TRIGGER', 'IMMEDIATE_MARKET']
    EXEC_MODE_LABELS_DMI_EMA = {
        'FISHER_M15_TRIGGER': '15min FT-crossover',
        'DMI_M15_TRIGGER': '15min +DI/-DI crossover',
        'IMMEDIATE_MARKET': 'Immediate market',
    }
    SL_TYPES = ['FIXED', 'BE_TO_TRAILING', 'ATR_TRAILING', 'MACD_CROSSOVER', 'DMI_CROSSOVER', 'STRUCTURE_ATR', 'STRUCTURE_ATR_STAGED']
    
    # Canonical source for storage (must match engine and opportunity_id.py)
    def _canonical_source(display_source: str) -> str:
        return {'FT-DMI-EMA': 'FT_DMI_EMA', 'DMI-EMA': 'DMI_EMA'}.get(display_source, display_source)

    # Stable key for semi-auto config (source-aware so LLM and DMI-EMA same pair have separate config)
    def _stable_opp_id(opp, source: str):
        if get_stable_opportunity_id:
            return get_stable_opportunity_id(opp, source=_canonical_source(source))
        return _normalized_stable_opp_id(opp)

    all_opps = []
    for opp in llm_opps:
        all_opps.append({'opp': opp, 'opp_id': _stable_opp_id(opp, 'LLM'), 'source': 'LLM', 'exec_modes': EXEC_MODES_LLM})
    for opp in fisher_opps:
        all_opps.append({'opp': opp, 'opp_id': _stable_opp_id(opp, 'Fisher'), 'source': 'Fisher', 'exec_modes': EXEC_MODES_FISHER})
    for opp in ft_dmi_ema_opps:
        all_opps.append({'opp': opp, 'opp_id': _stable_opp_id(opp, 'FT-DMI-EMA'), 'source': 'FT-DMI-EMA', 'exec_modes': ['IMMEDIATE_MARKET']})
    for opp in dmi_ema_opps:
        all_opps.append({'opp': opp, 'opp_id': _stable_opp_id(opp, 'DMI-EMA'), 'source': 'DMI-EMA', 'exec_modes': EXEC_MODES_DMI_EMA})

    # Normalize pair/direction for dedupe: same logical (source, pair, direction) = one row
    def _norm_pair(p):
        if not p or p == 'N/A':
            return p or ''
        return (p or '').upper().replace('_', '/')

    def _norm_direction(d):
        if not d or d == 'N/A':
            return d or ''
        d = (d or '').upper()
        if d in ('LONG', 'BUY'):
            return 'LONG'
        if d in ('SHORT', 'SELL'):
            return 'SHORT'
        return d

    def _canonical_key(source: str, pair: str, direction: str):
        return (source, _norm_pair(pair), _norm_direction(direction))

    # Deduplicate by canonical (source, pair, direction) so one row per logical opportunity (market state only; no saved-only rows)
    seen_keys = set()
    deduped = []
    for item in all_opps:
        opp = item['opp']
        key = _canonical_key(item['source'], opp.get('pair', ''), opp.get('direction', ''))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(item)
    all_opps = deduped

    if not all_opps:
        st.info(
            "No opportunities to approve yet. "
            "**LLM opportunities** come from Trade-Alerts. **Fisher opportunities** come from running the Fisher scan. "
            "Enable opportunities here when they appear."
        )
        return

    st.success(f"Found **{len(all_opps)}** opportunities from market state (**{len(llm_opps)}** LLM + **{len(fisher_opps)}** Fisher + **{len(ft_dmi_ema_opps)}** FT-DMI-EMA + **{len(dmi_ema_opps)}** DMI-EMA). Enable the ones you want to execute.")
    
    for item in all_opps:
        opp, opp_id, source, exec_modes = item['opp'], item['opp_id'], item['source'], item['exec_modes']
        # Unique key for Streamlit widgets: same pair+direction can appear in multiple sources (e.g. FT-DMI-EMA and DMI-EMA)
        widget_key = (opp.get('id') or f"{source}_{opp_id}").replace("/", "_").replace(" ", "_").replace("-", "_")
        saved = semi_auto.get_opportunity_config(opp_id) or {}
        enabled = saved.get('enabled', False)
        mode = saved.get('mode', 'RECOMMENDED' if source == 'LLM' else ('FISHER_M15_TRIGGER' if source in ('FT-DMI-EMA', 'DMI-EMA') else 'IMMEDIATE_MARKET'))
        sl_type = saved.get('sl_type', 'BE_TO_TRAILING')
        max_runs = saved.get('max_runs', 1)
        
        with st.expander(
            f"[{source}] {opp.get('pair', 'N/A')} {opp.get('direction', 'N/A')} @ {opp.get('entry', 'N/A')} "
            f"{'✅ ENABLED' if enabled else '❌ DISABLED'}"
        ):
            # Fisher warning for LLM opportunities (per spec: defensive/reversal system)
            if source == 'LLM' and opp.get('fisher_warning'):
                risk = opp.get('fisher_risk_level', 'HIGH')
                st.warning(opp['fisher_warning'])
                if opp.get('original_confidence') is not None:
                    orig = opp['original_confidence'] * 100
                    adj = opp.get('confidence', 0) * 100
                    st.caption(f"Adjusted confidence: {adj:.0f}% (reduced from {orig:.0f}% due to Fisher warning)")
                if risk == 'HIGH':
                    st.caption("**RECOMMENDATION:** Consider reducing position size, using tighter stop loss, or waiting for Fisher to normalize.")
                elif risk == 'CRITICAL':
                    st.caption("**RECOMMENDATION:** Do NOT enter. Fisher reversal in progress.")
            # Fisher opportunity: show Signal Type, Status, Confirmation Stages (per spec)
            if source == 'Fisher':
                entry_type = opp.get('entry_type', '')
                fa = opp.get('fisher_analysis', {})
                setup_type = fa.get('setup_type', '') or entry_type
                if entry_type or setup_type:
                    sig = (entry_type or setup_type).replace('_', ' ').title()
                    st.caption(f"**Signal Type:** {sig} | **Timeframe:** {opp.get('timeframe', 'DAILY')}")
                conf = opp.get('confirmations', {})
                if conf:
                    ft_ok = conf.get('ft_crossover', True)
                    macd_ok = conf.get('macd_crossover', False)
                    div_ok = conf.get('divergence', False)
                    adx_1h_ok = conf.get('adx_1h_ok', False)
                    confirm_count = sum([ft_ok, macd_ok, div_ok, adx_1h_ok])
                    status = f"⏳ MONITORING ({confirm_count}/4)" if confirm_count < 4 else "✅ FULL CONFIRMATION"
                    st.caption(f"**Status:** {status} — Stage 1: {'✅' if ft_ok else '❌'} FT | Stage 2: {'✅' if macd_ok else '❌'} MACD/Signal | Stage 3: {'✅' if div_ok else '❌'} Divergence | Stage 4: {'✅' if adx_1h_ok else '❌'} 1H ADX")
                conf_pct = opp.get('confidence', 0) or 0
                if conf_pct:
                    pct = conf_pct * 100 if conf_pct <= 1 else conf_pct
                    conf_label = "VERY HIGH" if pct >= 90 else "HIGH" if pct >= 75 else "MEDIUM"
                    st.caption(f"**Confidence:** {pct:.0f}% ({conf_label})")
            if source == 'FT-DMI-EMA':
                trigger_met = opp.get('ft_15m_trigger_met', False)
                st.caption(f"**Trigger:** 15m Fisher crossover — {'✅ MET (trade can execute)' if trigger_met else '⏳ Wait for 15m crossover'}")
                st.caption(opp.get('reason', 'Setup: 4H bias + 1H confirmation.'))
            if source == 'DMI-EMA':
                if mode == 'DMI_M15_TRIGGER':
                    trigger_met = opp.get('dmi_15m_trigger_met', False)
                    st.caption(f"**Trigger:** 15m +DI/-DI crossover — {'✅ MET (trade can execute)' if trigger_met else '⏳ Wait for 15m +DI/-DI crossover'}")
                else:
                    trigger_met = opp.get('ft_15m_trigger_met', False)
                    st.caption(f"**Trigger:** 15m Fisher crossover — {'✅ MET (trade can execute)' if trigger_met else '⏳ Wait for 15m crossover'}")
                st.caption(opp.get('reason', '1D/4H/1H DMI+EMA alignment.'))
                cf = opp.get('confidence_flags') or {}
                st.caption(f"**Confidence:** FT 1H: {'✅' if cf.get('ft_1h') else '❌'} | FT 15m: {'✅' if cf.get('ft_15m') else '❌'} | DMI 15m: {'✅' if cf.get('dmi_15m') else '❌'} | ADX 15m/1H/4H>20: {'✅' if (cf.get('adx_15m') and cf.get('adx_1h') and cf.get('adx_4h')) else '❌'}")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Entry:**", opp.get('entry', 'N/A'))
                st.write("**Stop Loss:**", opp.get('stop_loss', 'N/A'))
                st.write("**Take Profit:**", opp.get('take_profit', opp.get('exit', 'N/A')))
            with col2:
                new_enabled = st.checkbox("Enable this trade", value=enabled, key=f"sa_en_{widget_key}")
                # Execution mode: LLM/Fisher have full options; FT-DMI-EMA/DMI-EMA have 15m trigger or immediate
                format_fn = (lambda x: EXEC_MODE_LABELS_FT_DMI_EMA.get(x, x)) if source == 'FT-DMI-EMA' else (
                    (lambda x: EXEC_MODE_LABELS_DMI_EMA.get(x, x)) if source == 'DMI-EMA' else (lambda x: EXEC_MODE_LABELS.get(x, x))
                )
                new_mode = st.selectbox(
                    "Trigger / Execution mode",
                    options=exec_modes,
                    index=exec_modes.index(mode) if mode in exec_modes else 0,
                    format_func=format_fn,
                    help="FT-DMI-EMA: Final step = 15min FT-crossover. When enabled and 15m crossover is met, trade executes (limit/stop at entry). LLM/Fisher: choose activation.",
                    key=f"sa_mode_{widget_key}"
                )
                new_sl = st.selectbox(
                    "Stop loss type",
                    SL_TYPES,
                    index=SL_TYPES.index(sl_type) if sl_type in SL_TYPES else 1,
                    format_func=lambda x: SL_TYPE_LABELS.get(x, x),
                    key=f"sa_sl_{widget_key}"
                )
                new_max_runs = st.number_input("Max runs", min_value=1, max_value=5, value=max_runs, key=f"sa_runs_{widget_key}")
                if st.button("💾 Save", key=f"sa_save_{widget_key}"):
                    # When user re-enables an opportunity (disabled → enabled), reset run count so it can execute again
                    reset_run_count = bool(new_enabled and not saved.get('enabled', False))
                    semi_auto.set_opportunity_config(
                        opp_id, enabled=new_enabled, mode=new_mode,
                        max_runs=new_max_runs, sl_type=new_sl,
                        reset_run_count_requested=reset_run_count
                    )
                    logger.info(f"💾 Semi-auto config saved for {opp_id} - Enabled: {new_enabled}, Mode: {new_mode}, Max runs: {new_max_runs}")
                    st.success("Saved. Engine will use this when processing." + (" Run count reset (re-enabled)." if reset_run_count else ""))
                if st.button("🔄 Reset run count", key=f"sa_reset_{widget_key}", help="Allow this opportunity to run again up to Max runs (e.g. after trade closed)."):
                    semi_auto.set_opportunity_config(
                        opp_id, enabled=enabled, mode=mode, max_runs=max_runs, sl_type=sl_type,
                        reset_run_count_requested=True
                    )
                    logger.info(f"🔄 Run count reset for {opp_id}")
                    st.success("Run count reset requested. Next time the engine processes this opportunity it will reset and can execute again.")


def render_auto_trader_controls():
    """Render auto-trader controls in the UI. Load config from config-api first (no shared disk)."""
    
    st.header("🤖 Auto-Trader Controls")
    
    config_path = "/var/data/auto_trader_config.json"
    default_config = {
        'trading_mode': 'MANUAL',
        'max_open_trades': 5,
        'stop_loss_type': 'BE_TO_TRAILING',
        'execution_mode': 'RECOMMENDED',
        'auto_trade_llm': True,
        'auto_trade_fisher': True,
        'auto_trade_ft_dmi_ema': True,
        'auto_trade_dmi_ema': True,
        'min_consensus_level': 2,
        'base_position_size': 1000,
        'hard_trailing_pips': 20.0,
        'max_daily_loss': 500.0
    }
    
    # Load config from config-api first (so UI and engine see same config)
    config = None
    config_api_url = os.getenv('CONFIG_API_URL', 'https://config-api-8n37.onrender.com/config')
    if config_api_url:
        try:
            api_base = config_api_url.rstrip('/')
            if api_base.endswith('/config'):
                api_base = api_base[:-7]
            r = requests.get(f"{api_base}/config", timeout=5)
            if r.status_code == 200:
                config = r.json()
        except Exception:
            pass
    if config is None and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception:
            config = None
    if config is None:
        config = default_config
    
    # Create two columns for layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚙️ Trading Configuration")
        # Config last updated (consol-recommend2 Phase 2.1): separate field from API; engine strips before TradeConfig
        last_updated = config.get('last_updated')
        if last_updated:
            st.caption(f"Config last updated: {last_updated}")
        # Trading Mode
        TRADING_MODES = ['MANUAL', 'SEMI_AUTO', 'AUTO']
        mode_val = config.get('trading_mode', 'MANUAL')
        mode_idx = TRADING_MODES.index(mode_val) if mode_val in TRADING_MODES else 0
        trading_mode = st.selectbox(
            "Trading Mode",
            options=TRADING_MODES,
            index=mode_idx,
            help="MANUAL: Alerts only. SEMI_AUTO: Enable trades in the Semi-Auto Approval tab. AUTO: Execute automatically."
        )
        
        # Max Open Trades
        max_trades = st.slider(
            "Max Open Trades",
            min_value=1,
            max_value=15,
            value=config.get('max_open_trades', 5),
            help="Maximum number of simultaneous positions"
        )
        
        # Auto mode: which opportunity sources may open trades (only when Trading Mode = AUTO)
        st.markdown("**Auto mode: trade from** (when Trading Mode is AUTO)")
        auto_trade_llm = st.checkbox(
            "Trade LLM opportunities",
            value=config.get('auto_trade_llm', True),
            key="auto_trade_llm",
            help="When AUTO: allow opening trades from LLM consensus opportunities"
        )
        auto_trade_fisher = st.checkbox(
            "Trade Fisher opportunities",
            value=config.get('auto_trade_fisher', True),
            key="auto_trade_fisher",
            help="When AUTO: allow opening trades from Fisher Transform opportunities"
        )
        auto_trade_ft_dmi_ema = st.checkbox(
            "Trade FT-DMI-EMA opportunities",
            value=config.get('auto_trade_ft_dmi_ema', True),
            key="auto_trade_ft_dmi_ema",
            help="When AUTO: allow opening trades from FT-DMI-EMA (4H/1H setup + 15m Fisher trigger)"
        )
        auto_trade_dmi_ema = st.checkbox(
            "Trade DMI-EMA opportunities",
            value=config.get('auto_trade_dmi_ema', True),
            key="auto_trade_dmi_ema",
            help="When AUTO: allow opening trades from DMI-EMA (1D/4H/1H DMI+EMA alignment + 15m Fisher trigger)"
        )
        if trading_mode == 'AUTO' and not (auto_trade_llm or auto_trade_fisher or auto_trade_ft_dmi_ema or auto_trade_dmi_ema):
            st.warning("At least one source should be enabled in AUTO mode, or no trades will open.")
        
        # Stop Loss Type
        # CHANGED: Added STRUCTURE_ATR_STAGED to Auto mode now that it works for all opportunities
        # (previously was hidden because it only worked for FT-DMI-EMA)
        sl_options = ['FIXED', 'TRAILING', 'BE_TO_TRAILING', 'ATR_TRAILING', 'MACD_CROSSOVER', 'DMI_CROSSOVER', 'STRUCTURE_ATR_STAGED']
        sl_type = st.selectbox(
            "Stop Loss Strategy",
            options=sl_options,
            index=sl_options.index(
                config.get('stop_loss_type', 'BE_TO_TRAILING')
            ) if config.get('stop_loss_type', 'BE_TO_TRAILING') in sl_options else 0,
            help="""
            FIXED: Standard stop loss
            TRAILING: Immediate trailing stop
            BE_TO_TRAILING: Fixed SL → Move to BE at entry → Convert to trailing
            ATR Trailing: ATR-based dynamic trailing
            MACD_CROSSOVER: Close trade when MACD crosses in opposite direction
            DMI_CROSSOVER: Close trade when +DI/-DI crosses in opposite direction
            STRUCTURE_ATR_STAGED: Staged profit protection - BE at +1R, Close 50% at +2R, Trail to EMA at +3R (works for all opportunities)
            """
        )
        
        # Execution Mode
        execution_mode = st.selectbox(
            "Execution Mode",
            options=['MARKET', 'RECOMMENDED', 'MACD_CROSSOVER', 'HYBRID'],
            index=['MARKET', 'RECOMMENDED', 'MACD_CROSSOVER', 'HYBRID'].index(
                config.get('execution_mode', 'RECOMMENDED')
            ) if config.get('execution_mode', 'RECOMMENDED') in ['MARKET', 'RECOMMENDED', 'MACD_CROSSOVER', 'HYBRID'] else 1,
            help="""
            MARKET: Execute immediately at current market price
            RECOMMENDED: Place LIMIT/STOP orders at recommended entry price
            MACD_CROSSOVER: Wait for MACD crossover signal before executing (checks every 5 minutes)
            HYBRID: Place pending order at recommended price AND check MACD crossover - whichever triggers first
            """
        )
        
        # Trailing Pips (for hard trailing)
        if sl_type in ['TRAILING', 'BE_TO_TRAILING']:
            trailing_pips = st.number_input(
                "Trailing Distance (pips)",
                min_value=5.0,
                max_value=100.0,
                value=config.get('hard_trailing_pips', 20.0),
                step=5.0,
                help="Distance for trailing stop in pips"
            )
        else:
            trailing_pips = config.get('hard_trailing_pips', 20.0)
        
        # MACD Timeframe (for MACD_CROSSOVER or HYBRID execution mode or stop loss)
        if execution_mode in ['MACD_CROSSOVER', 'HYBRID'] or sl_type == 'MACD_CROSSOVER':
            st.write("**MACD Timeframes**")
            macd_timeframe = st.selectbox(
                "Entry Timeframe (for trade entry)",
                options=['M5', 'M15', 'H1'],
                index=['M5', 'M15', 'H1'].index(
                    config.get('macd_timeframe', 'H1')
                ) if config.get('macd_timeframe', 'H1') in ['M5', 'M15', 'H1'] else 2,
                help="Timeframe for MACD entry signal: 5min (M5), 15min (M15), or 1 hour (H1)"
            )
            
            # Separate timeframe for stop loss if MACD_CROSSOVER or DMI_CROSSOVER stop loss is selected
            if sl_type == 'MACD_CROSSOVER':
                macd_sl_timeframe = st.selectbox(
                    "Stop Loss Timeframe (for trade exit)",
                    options=['M5', 'M15', 'H1', 'Same as Entry'],
                    index=['M5', 'M15', 'H1', 'Same as Entry'].index(
                        config.get('macd_sl_timeframe', 'Same as Entry')
                    ) if config.get('macd_sl_timeframe', 'Same as Entry') in ['M5', 'M15', 'H1', 'Same as Entry'] else 3,
                    help="Timeframe for MACD stop loss signal. Use 'Same as Entry' to use entry timeframe, or choose a different timeframe for faster/slower exit signals."
                )
                # Convert 'Same as Entry' to None (will use entry timeframe)
                if macd_sl_timeframe == 'Same as Entry':
                    macd_sl_timeframe = None
                dmi_sl_timeframe = config.get('dmi_sl_timeframe', 'H1')
            elif sl_type == 'DMI_CROSSOVER':
                dmi_sl_timeframe = st.selectbox(
                    "DMI Stop Loss Timeframe (for trade exit)",
                    options=['M15', 'H1'],
                    index=['M15', 'H1'].index(
                        config.get('dmi_sl_timeframe', 'H1')
                    ) if config.get('dmi_sl_timeframe', 'H1') in ['M15', 'H1'] else 1,
                    help="Timeframe for +DI/-DI stop loss signal (1h or 15m)."
                )
                macd_sl_timeframe = config.get('macd_sl_timeframe', None)
            else:
                macd_sl_timeframe = config.get('macd_sl_timeframe', None)
        else:
            macd_timeframe = config.get('macd_timeframe', 'H1')
            macd_sl_timeframe = config.get('macd_sl_timeframe', None)
    
    with col2:
        st.subheader("🎯 Consensus Filters")
        
        # Min Consensus Level
        consensus_level = st.select_slider(
            "Minimum Consensus Level",
            options=[1, 2, 3, 4],
            value=config.get('min_consensus_level', 2),
            help="""
            1: Any single LLM
            2: At least 2 LLMs agree
            3: At least 3 LLMs agree
            4: All 4 base LLMs agree (chatgpt, gemini, claude, deepseek)
            """
        )
        
        # Required LLMs (checkboxes for all LLMs)
        st.markdown("**Required LLMs** (select at least one - trades must include at least one selected LLM):")
        
        # Get LLM weights from market state to show current performance
        llm_weights = {}
        try:
            market_state = load_market_state()
            if market_state:
                llm_weights = market_state.get('llm_weights', {})
        except:
            pass

        st.subheader("💰 Risk Management")
        
        # Base Position Size
        position_size = st.number_input(
            "Base Position Size (units)",
            min_value=100,
            max_value=10000,
            value=config.get('base_position_size', 1000),
            step=100,
            help="Base position size, multiplied by consensus level"
        )
        
        # Max Daily Loss
        max_daily_loss = st.number_input(
            "Max Daily Loss (account currency)",
            min_value=100.0,
            max_value=5000.0,
            value=config.get('max_daily_loss', 500.0),
            step=50.0,
            help="Maximum acceptable daily loss"
        )
    
    # Save button
    st.markdown("---")
    
    col_save, col_reset = st.columns(2)
    
    with col_save:
        if st.button("💾 Save Configuration", type="primary"):
            # Build new config
            new_config = {
                'trading_mode': trading_mode,
                'max_open_trades': max_trades,
                'stop_loss_type': sl_type,
                'execution_mode': execution_mode,  # MARKET, RECOMMENDED, or MACD_CROSSOVER
                'auto_trade_llm': auto_trade_llm,
                'auto_trade_fisher': auto_trade_fisher,
                'auto_trade_ft_dmi_ema': auto_trade_ft_dmi_ema,
                'auto_trade_dmi_ema': auto_trade_dmi_ema,
                'min_consensus_level': consensus_level,
                'base_position_size': position_size,
                'hard_trailing_pips': trailing_pips,
                'max_daily_loss': max_daily_loss,
                'consensus_multiplier': {
                    1: 0.5,
                    2: 1.0,
                    3: 1.5,
                    4: 2.0
                },
                'be_trigger_pips': 0.0,
                'atr_multiplier_low_vol': 1.5,
                'atr_multiplier_high_vol': 3.0,
                'max_account_risk_pct': 10.0,
                'macd_timeframe': macd_timeframe,  # M5, M15, or H1
                'macd_sl_timeframe': macd_sl_timeframe if 'macd_sl_timeframe' in locals() else config.get('macd_sl_timeframe', None),  # M5, M15, H1, or None
                'dmi_sl_timeframe': dmi_sl_timeframe if 'dmi_sl_timeframe' in locals() else config.get('dmi_sl_timeframe', 'H1'),  # H1 or M15 for DMI stop loss
                'macd_fast_period': config.get('macd_fast_period', 12),
                'macd_slow_period': config.get('macd_slow_period', 26),
                'macd_signal_period': config.get('macd_signal_period', 9),
                'macd_close_on_reverse': config.get('macd_close_on_reverse', True)
            }
            
            # Save to file
            try:
                # Ensure directory exists
                config_dir = os.path.dirname(config_path)
                if not os.path.exists(config_dir):
                    os.makedirs(config_dir, exist_ok=True)
                    st.info(f"📁 Created directory: {config_dir}")
                
                # Verify directory is writable
                if not os.access(config_dir, os.W_OK):
                    st.error(f"❌ Directory is not writable: {config_dir}")
                    st.error("Please check disk mount permissions in Render Dashboard")
                    return
                
                # Save config file with explicit flush and sync
                with open(config_path, 'w') as f:
                    json.dump(new_config, f, indent=2)
                    f.flush()  # Force write to disk
                    os.fsync(f.fileno())  # Force OS to write to disk
                
                # Verify file was written
                if not os.path.exists(config_path):
                    st.error(f"❌ File was not created: {config_path}")
                    return
                
                # Get file mtime after write for verification
                import time
                file_mtime = os.path.getmtime(config_path)
                file_size = os.path.getsize(config_path)
                
                # Verify file contents match what we saved
                with open(config_path, 'r') as f:
                    saved_data = json.load(f)
                    if saved_data.get('trading_mode') != new_config['trading_mode']:
                        st.error(f"❌ File contents mismatch! Saved: {new_config['trading_mode']}, File has: {saved_data.get('trading_mode')}")
                        st.error(f"📄 File path: {config_path}")
                        st.error(f"📄 File mtime: {file_mtime} ({datetime.fromtimestamp(file_mtime).isoformat()})")
                        st.code(json.dumps(saved_data, indent=2))
                        return
                    if saved_data.get('stop_loss_type') != new_config['stop_loss_type']:
                        st.error(f"❌ File contents mismatch! Saved: {new_config['stop_loss_type']}, File has: {saved_data.get('stop_loss_type')}")
                        st.error(f"📄 File path: {config_path}")
                        st.error(f"📄 File mtime: {file_mtime} ({datetime.fromtimestamp(file_mtime).isoformat()})")
                        st.code(json.dumps(saved_data, indent=2))
                        return
                
                # Success message with file details
                file_mtime_str = datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M:%S UTC')
                st.success(f"✅ Configuration saved to disk!")
                st.info(f"📄 File: {config_path}")
                st.info(f"📊 Size: {file_size} bytes")
                st.info(f"⏰ Modified: {file_mtime_str} (mtime: {file_mtime})")
                st.info(f"💾 Saved values - Mode: {new_config['trading_mode']}, Stop Loss: {new_config['stop_loss_type']}, Max Trades: {new_config['max_open_trades']}")
                logger.info(f"⚙️ Config saved - Mode: {new_config['trading_mode']}, Stop Loss: {new_config['stop_loss_type']}, Max Trades: {new_config['max_open_trades']}")
                
                # POST to config-api (bypasses disk sharing issues)
                config_api_url = os.getenv('CONFIG_API_URL', 'https://config-api-8n37.onrender.com/config')
                if config_api_url:
                    try:
                        # Ensure URL ends with /config
                        api_url = config_api_url.rstrip('/')
                        if not api_url.endswith('/config'):
                            api_url = f"{api_url}/config"
                        
                        response = requests.post(
                            api_url,
                            json=new_config,
                            headers={'Content-Type': 'application/json'},
                            timeout=10
                        )
                        response.raise_for_status()
                        st.success(f"✅ Configuration sent to API: {api_url}")
                        st.success("🚀 Changes will apply immediately (within 30 seconds).")
                        logger.info(f"✅ Config sent to API: {api_url}")
                    except requests.exceptions.RequestException as e:
                        st.warning(f"⚠️ Saved to disk but failed to send to API: {e}")
                        st.info("💡 Config will be available after next API check (30-60 seconds).")
                        logger.warning(f"⚠️ Config not sent to API: {e}")
                else:
                    st.info("💡 Changes will apply on next check (within 30-60 seconds).")
                
            except PermissionError as e:
                st.error(f"❌ Permission denied saving configuration to {config_path}")
                st.error(f"Error: {e}")
                st.warning("💡 Check Render Dashboard → scalp-engine-ui → Disk mount permissions")
            except Exception as e:
                st.error(f"❌ Error saving configuration: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    with col_reset:
        if st.button("🔄 Reset to Defaults"):
            st.rerun()
    
    # Display position sizing table
    st.markdown("---")
    st.subheader("📊 Position Sizing by Consensus")
    
    sizing_data = {
        "Consensus Level": ["1 LLM", "2 LLMs Agree", "3 LLMs Agree", "4 LLMs Agree (ALL_AGREE)"],
        "Win Rate": ["Variable", "67%", "217%", "TBD"],
        "Position Multiplier": ["0.5x", "1.0x", "1.5x", "2.0x"],
        "Actual Size (units)": [
            f"{position_size * 0.5:.0f}",
            f"{position_size * 1.0:.0f}",
            f"{position_size * 1.5:.0f}",
            f"{position_size * 2.0:.0f}"
        ]
    }
    
    st.table(sizing_data)
    
    st.info("""
    **💡 Recommended Settings for Beginners:**
    - Mode: MANUAL (approve each trade)
    - Max Trades: 3-5
    - Stop Loss: BE_TO_TRAILING (protect profits)
    - Min Consensus: 2 (require agreement)
    - Require Gemini: ✓ (highest accuracy)
    """)


def _format_trade_source(opportunity_source: str) -> str:
    """Map raw opportunity_source to a human-readable label."""
    _map = {
        "FT_DMI_EMA": "FT-DMI-EMA",
        "DMI_EMA":    "DMI-EMA",
        "FISHER":     "Fisher",
        "LLM":        "LLM",
    }
    return _map.get((opportunity_source or "").upper(), "LLM")


def _format_sl_type(sl_type: str) -> str:
    """Map raw sl_type value to a short readable label."""
    _map = {
        "STRUCTURE_ATR_STAGED": "ATR-Staged",
        "STRUCTURE_ATR":        "ATR-Structure",
        "ATR_TRAILING":         "ATR-Trail",
        "BE_TO_TRAILING":       "BE→Trail",
        "TRAILING":             "Trailing",
        "MACD_CROSSOVER":       "MACD-X",
        "DMI_CROSSOVER":        "DMI-X",
        "FIXED":                "Fixed",
    }
    return _map.get((sl_type or "").upper(), sl_type or "Fixed")


def render_active_trades_monitor():
    """Render active trades monitoring section"""
    
    st.header("📈 Active Trades Monitor")

    # ========================================================================
    # SYSTEM SYNC STATUS (Phase 3 Enhancement)
    # ========================================================================
    st.subheader("🔄 System Sync Status")

    sync_col1, sync_col2, sync_col3, sync_col4 = st.columns(4)

    # Initialize sync status in session state if not present
    if 'sync_status' not in st.session_state:
        st.session_state.sync_status = "UNKNOWN"
    if 'last_sync_check' not in st.session_state:
        st.session_state.last_sync_check = None
    if 'orphaned_orders_detected' not in st.session_state:
        st.session_state.orphaned_orders_detected = 0

    with sync_col1:
        st.metric(
            "Sync Status",
            st.session_state.sync_status,
            delta="Clean" if st.session_state.sync_status == "CLEAN" else None,
            delta_color="off" if st.session_state.sync_status != "CLEAN" else "normal"
        )

    with sync_col2:
        st.metric(
            "Orphaned Orders",
            st.session_state.orphaned_orders_detected,
            delta="-1" if st.session_state.orphaned_orders_detected > 0 else "None",
            delta_color="inverse" if st.session_state.orphaned_orders_detected > 0 else "off"
        )

    with sync_col3:
        last_check_text = "Never"
        if st.session_state.last_sync_check:
            try:
                last_check_dt = st.session_state.last_sync_check
                if isinstance(last_check_dt, str):
                    last_check_dt = datetime.fromisoformat(last_check_dt.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                if last_check_dt.tzinfo is None:
                    last_check_dt = last_check_dt.replace(tzinfo=timezone.utc)
                age = now - last_check_dt
                if age < timedelta(minutes=1):
                    last_check_text = "Just now"
                elif age < timedelta(hours=1):
                    minutes = int(age.total_seconds() / 60)
                    last_check_text = f"{minutes}m ago"
                else:
                    hours = int(age.total_seconds() / 3600)
                    last_check_text = f"{hours}h ago"
            except:
                last_check_text = "Recently"

        st.metric("Last Sync Check", last_check_text)

    with sync_col4:
        # Manual sync button
        if st.button("🔄 Manual Sync Check", key="manual_sync_button"):
            st.info("Triggering manual sync check...")
            try:
                import requests
                config_api_url = os.getenv('CONFIG_API_URL', 'https://config-api-8n37.onrender.com/config')
                if config_api_url:
                    api_base = config_api_url.rstrip('/')
                    if api_base.endswith('/config'):
                        api_base = api_base[:-7]
                    sync_url = f"{api_base}/sync-check"

                    response = requests.post(sync_url, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.orphaned_orders_detected = result.get('orphaned_detected', 0)
                        st.session_state.last_sync_check = datetime.now(timezone.utc).isoformat() + "Z"

                        if result.get('orphaned_detected', 0) > 0:
                            st.warning(
                                f"⚠️ **Sync Check Results:**\n\n"
                                f"• Orphaned orders detected: {result['orphaned_detected']}\n"
                                f"• Orders cancelled: {result['orphaned_cancelled']}\n"
                                f"• Status: {result.get('status', 'Unknown')}"
                            )
                            st.session_state.sync_status = "ISSUES"
                        else:
                            st.success(
                                f"✅ **Sync Check Results:**\n\n"
                                f"UI and OANDA are in perfect sync\n"
                                f"No orphaned orders detected"
                            )
                            st.session_state.sync_status = "CLEAN"
                        st.rerun()
                    else:
                        st.error(f"Sync check failed: {response.status_code}")
            except Exception as e:
                st.error(f"Error triggering sync check: {str(e)[:100]}")

    # Display sync status explanation
    if st.session_state.sync_status == "ISSUES":
        st.error(
            "⚠️ **Sync Issues Detected**\n\n"
            "The system detected orphaned orders on OANDA that are not in the UI. "
            "This can happen when orders are placed outside the UI system. "
            "Click the 'Manual Sync Check' button to investigate and cancel stale orders."
        )
    elif st.session_state.sync_status == "CLEAN":
        st.success(
            "✅ **UI and OANDA in Sync**\n\n"
            "The system regularly checks for orphaned orders. "
            "No discrepancies detected."
        )
    else:
        st.info(
            "ℹ️ **Sync Status Unknown**\n\n"
            "The system has not performed a sync check yet. "
            "Click 'Manual Sync Check' to verify UI/OANDA alignment, "
            "or the system will automatically check every hour during trading hours."
        )

    st.divider()

    # Try to load from API first (bypasses disk sharing issues)
    # Always fetch fresh data - no caching
    trades = []
    pending_signals = []
    last_updated_iso = None
    api_success = False
    try:
        config_api_url = os.getenv('CONFIG_API_URL', 'https://config-api-8n37.onrender.com/config')
        if config_api_url:
            try:
                import requests
                # Construct trades API URL (e.g., https://config-api-8n37.onrender.com/trades)
                api_base = config_api_url.rstrip('/')
                # Remove '/config' from end if present
                if api_base.endswith('/config'):
                    api_base = api_base[:-7]
                trades_api_url = f"{api_base}/trades"
                
                # Add timestamp to prevent browser/API caching
                # Use current time in milliseconds for better cache busting
                timestamp = int(time.time() * 1000)
                trades_api_url_with_cache_bust = f"{trades_api_url}?t={timestamp}&_={timestamp}"
                
                # Add headers to prevent caching
                headers = {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
                response = requests.get(trades_api_url_with_cache_bust, timeout=5, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    trades = data.get('trades', [])
                    pending_signals = data.get('pending_signals', [])
                    last_updated_iso = data.get('last_updated')
                    api_success = True
                    if trades:
                        st.success(f"✅ Loaded {len(trades)} trades from API")
                    elif pending_signals:
                        st.success(f"✅ Loaded 0 active trades, **{len(pending_signals)}** pending signal(s) from API")
                    else:
                        st.info("ℹ️ No active trades (from API)")
            except Exception as e:
                # Fall back to file
                st.warning(f"⚠️ API unavailable, using file fallback: {str(e)[:50]}")
    except:
        pass
    
    # Fallback to file if API failed or not configured
    if not trades:
        state_path = "/var/data/trade_states.json"
        
        if not os.path.exists(state_path):
            st.info("No active trades")
            return
        
        try:
            with open(state_path, 'r') as f:
                data = json.load(f)
                trades = data.get('trades', [])
                pending_signals = data.get('pending_signals', [])
            
            if not trades and not pending_signals:
                st.info("No active trades")
                return
        except Exception as e:
            st.error(f"Error loading trades: {e}")
            return
    
    if not trades and not pending_signals:
        st.info("No active trades")
        return
    
    # Pending signals: enabled opportunities waiting for trigger (e.g. 15m FT crossover)
    if pending_signals:
        st.subheader("⏳ Pending signals (waiting for trigger)")
        st.caption("These are enabled opportunities stored by the engine; they will execute when the trigger (e.g. 15m Fisher crossover) is detected.")
        for ps in pending_signals:
            pair = ps.get('pair', 'N/A')
            direction = ps.get('direction', 'N/A')
            wait = ps.get('wait_for_signal', '') or ps.get('reason', '')
            st.write(f"• **{pair}** {direction} — {wait}")
        st.write("")
    
    st.write(f"**Total Active Trades:** {len(trades)}")
    if not trades and pending_signals:
        st.caption("No open positions yet; pending signal(s) will execute when trigger is met.")
    
    # Show when list was last updated (set by engine when it syncs with OANDA and POSTs)
    if last_updated_iso:
        try:
            last_updated_dt = datetime.fromisoformat(last_updated_iso.replace('Z', '+00:00'))
            if last_updated_dt.tzinfo is None:
                last_updated_dt = last_updated_dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            age_seconds = (now - last_updated_dt).total_seconds()
            age_min = max(0, int(age_seconds / 60))
            st.caption(f"List last updated {age_min} min ago. Updates when the engine syncs with OANDA and POSTs to this server.")
            if age_min >= 2:
                st.warning(
                    "⚠️ **Trade list may be stale.** If this timestamp is old, the engine may not be running or may not be syncing with OANDA. "
                    "Click **Refresh Data** to fetch the latest from the server."
                )
        except Exception:
            st.caption(f"Last updated: {last_updated_iso}")
    else:
        st.caption("List updates when the engine syncs with OANDA and POSTs. Click **Refresh Data** to fetch the latest.")
    
    # Display each trade
    for trade in trades:
        _src_label = _format_trade_source(trade.get('opportunity_source', ''))
        _sl_label  = _format_sl_type(trade.get('sl_type', ''))
        with st.expander(
            f"{trade['pair']} {trade['direction']} "
            f"({trade['state']}) · {_src_label} | {_sl_label}  "
            f"{'🟢' if trade.get('unrealized_pnl', 0) > 0 else '🔴'} "
            f"{trade.get('unrealized_pnl', 0):.1f} pips"
        ):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.write("**Trade Details**")
                st.write(f"ID: `{trade.get('trade_id', 'N/A')}`")
                st.write(f"Entry: {trade.get('entry_price', 'N/A')}")
                st.write(f"Current SL: {trade.get('current_sl', 'N/A')}")
                if trade.get('take_profit'):
                    st.write(f"TP: {trade.get('take_profit')}")
            
            with col2:
                st.write("**Intelligence**")
                st.write(f"Consensus: {trade.get('consensus_level', 1)}/{trade.get('available_llm_count', 4)}")
                llm_sources = trade.get('llm_sources', [])
                st.write(f"LLMs: {', '.join(llm_sources) if llm_sources else 'N/A'}")
                confidence = trade.get('confidence', 0.5)
                st.write(f"Confidence: {confidence*100:.0f}%")
            
            with col3:
                st.write("**Performance**")
                pnl_pips = trade.get('unrealized_pnl', 0)
                st.write(f"P&L: {pnl_pips:.1f} pips")
                # Show OANDA actual P/L in account currency if available
                oanda_pl = trade.get('oanda_unrealized_pl')
                if oanda_pl is not None:
                    st.write(f"OANDA P/L: ${oanda_pl:.2f}")
                st.write(f"State: {trade.get('state', 'N/A')}")
                if trade.get('opened_at'):
                    try:
                        opened_str = trade['opened_at']
                        if opened_str.endswith('Z'):
                            opened_str = opened_str.replace('Z', '+00:00')
                        opened = datetime.fromisoformat(opened_str)
                        now = datetime.now(opened.tzinfo) if opened.tzinfo else datetime.utcnow()
                        duration = now - opened
                        st.write(f"Duration: {duration.total_seconds()/3600:.1f}h")
                    except Exception as e:
                        st.write(f"Opened: {trade.get('opened_at', 'N/A')}")

            with col4:
                st.write("**Strategy**")
                st.write(f"Source: **{_src_label}**")
                st.write(f"SL Type: **{_sl_label}**")
                # Show staged phase progress for STRUCTURE_ATR_STAGED
                if trade.get('sl_type', '').upper() == 'STRUCTURE_ATR_STAGED':
                    be   = "✅" if trade.get('breakeven_applied')    else "⬜"
                    part = "✅" if trade.get('partial_profit_taken') else "⬜"
                    trl  = "✅" if trade.get('trailing_active')      else "⬜"
                    st.write(f"{be} Breakeven")
                    st.write(f"{part} Partial TP")
                    st.write(f"{trl} Trailing")

            # Show rationale
            if trade.get('rationale'):
                st.markdown("**Rationale:**")
                st.caption(trade['rationale'][:200] + "...")


def render_market_intelligence():
    """Render market intelligence from Trade-Alerts"""
    
    st.header("🧠 Market Intelligence (from Trade-Alerts)")
    
    # Use the same load_market_state() function as other tabs (handles disk sharing issues)
    market_state = load_market_state()
    
    if not market_state:
        st.warning("No market state available. Waiting for Trade-Alerts...")
        return
    
    try:
        
        # Display timestamp
        last_update = market_state.get('timestamp', 'Unknown')
        st.caption(f"Last Updated: {last_update}")
        
        # Display market context
        col1, col2, col3 = st.columns(3)
        
        with col1:
            bias = market_state.get('global_bias', 'NEUTRAL')
            bias_emoji = "📈" if bias == "BULLISH" else "📉" if bias == "BEARISH" else "↔️"
            st.metric("Market Bias", f"{bias_emoji} {bias}")
        
        with col2:
            regime = market_state.get('regime', 'NORMAL')
            regime_emoji = "⚡" if regime == "HIGH_VOL" else "😌"
            st.metric("Volatility Regime", f"{regime_emoji} {regime}")
        
        with col3:
            opportunities = market_state.get('opportunities', [])
            st.metric("Active Opportunities", len(opportunities))
        
        # Display LLM weights
        st.subheader("🎯 LLM Performance Weights")
        weights = market_state.get('llm_weights', {})
        
        if weights:
            weight_data = {
                "LLM": [],
                "Weight": [],
                "Bar": []
            }
            
            for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
                weight_data["LLM"].append(llm.upper())
                weight_data["Weight"].append(f"{weight*100:.0f}%")
                weight_data["Bar"].append("█" * int(weight * 20))
            
            st.table(weight_data)
        
        # Display opportunities with consensus info
        if opportunities:
            st.subheader("🎯 Current Opportunities")
            
            # consol-recommend4 Phase 2.1: display consensus as X/available_llm_count (not fixed /4)
            available_denom = market_state.get('available_llm_count', 4) if isinstance(market_state, dict) else 4
            for opp in opportunities:
                consensus = opp.get('consensus_level', 1)
                denom = opp.get('available_llm_count', available_denom)
                consensus_badge = "🟢" if consensus >= 3 else "🟡" if consensus == 2 else "⚪"

                with st.expander(
                    f"{consensus_badge} {opp['pair']} {opp['direction']} "
                    f"@ {opp['entry']} (Consensus: {consensus}/{denom})"
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Entry:** {opp['entry']}")
                        st.write(f"**Stop Loss:** {opp.get('stop_loss', 'N/A')}")
                        if opp.get('exit'):
                            st.write(f"**Take Profit:** {opp['exit']}")
                        st.write(f"**Timeframe:** {opp.get('timeframe', 'N/A')}")
                    
                    with col2:
                        st.write(f"**Consensus:** {consensus}/{denom}")
                        llm_sources = opp.get('llm_sources', [])
                        st.write(f"**Agreeing LLMs:** {', '.join(llm_sources) if llm_sources else 'N/A'}")
                        confidence = opp.get('confidence', 0.5)
                        st.write(f"**Confidence:** {confidence*100:.0f}%")
                    
                    if opp.get('recommendation'):
                        st.markdown("**Rationale:**")
                        st.caption(opp['recommendation'][:300] + "...")
        
    except Exception as e:
        st.error(f"Error loading market intelligence: {e}")


def main():
    # Log page load
    logger.info("📊 UI page loaded")

    # Initialize session state for auto-refresh
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()

    # Header
    st.markdown('<div class="main-header">📈 Scalp-Engine Dashboard</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # Refresh button
        if st.button("🔄 Refresh Data", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.session_state.last_refresh = datetime.now()
            st.rerun()
        
        st.divider()
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto_refresh
        
        if auto_refresh:
            # Check if 30 seconds have passed since last refresh
            time_since_refresh = (datetime.now() - st.session_state.last_refresh).total_seconds()
            if time_since_refresh >= 30:
                st.session_state.last_refresh = datetime.now()
                st.cache_data.clear()
                # Use st.rerun() to refresh the page
                st.rerun()
            else:
                remaining = int(30 - time_since_refresh)
                st.info(f"🔄 Auto-refresh in {remaining}s")
                # Use JavaScript to auto-refresh after remaining seconds
                st.markdown(
                    f'<meta http-equiv="refresh" content="{remaining}">',
                    unsafe_allow_html=True
                )
        
        # Force refresh indicator - show when data might be stale
        if 'last_refresh' in st.session_state:
            time_since_refresh = (datetime.now() - st.session_state.last_refresh).total_seconds()
            if time_since_refresh > 60 and not auto_refresh:
                st.warning("⚠️ Data may be stale - enable auto-refresh or click Refresh Data")
        
        st.divider()
        
        # Settings
        st.subheader("Settings")
        show_pending = st.checkbox("Show Pending Trades", value=True)
        show_closed = st.checkbox("Show Closed Trades", value=True)
        signal_limit = st.slider("Recent Signals Limit", 10, 50, 20)
    
    # Main content
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Opportunities", "🎯 Fisher Opportunities", "📐 FT-DMI-EMA Opportunities", "📐 DMI-EMA Opportunities",
        "📈 Recent Signals", "📉 Performance", "ℹ️ Market State", "🤖 Auto-Trader"
    ])
    
    # Tab 1: Opportunities
    with tab1:
        st.header("Current Scalping Opportunities")
        
        market_state = load_market_state()
        
        if market_state:
            # Market state info
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Regime", market_state.get('regime', 'N/A'))
            
            with col2:
                st.metric("Bias", market_state.get('global_bias', 'N/A'))
            
            with col3:
                approved_pairs = market_state.get('approved_pairs', [])
                st.metric("Approved Pairs", len(approved_pairs))
            
            with col4:
                timestamp_str = market_state.get('timestamp', '')
                if timestamp_str:
                    formatted_time, age = format_timestamp(timestamp_str)
                    st.metric("Last Updated", age)
                    st.caption(formatted_time)
            
            st.divider()
            
            # Approved pairs
            if approved_pairs:
                st.subheader("✅ Approved Trading Pairs")
                
                for pair in approved_pairs:
                    with st.container():
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.markdown(f"### {pair}")
                        
                        with col2:
                            # Get recent performance for this pair
                            rl = ScalpingRL(DB_PATH)
                            perf = rl.get_historical_performance_by_pair(pair)
                            
                            if perf['total_trades'] > 0:
                                st.metric("Win Rate", f"{perf['win_rate']:.1%}")
                                st.caption(f"{perf['total_trades']} trades")
                        
                        with col3:
                            st.metric("Avg PnL", f"${perf['avg_pnl']:.2f}")
                        
                        st.divider()
                
                # Opportunities from market state
                opportunities = market_state.get('opportunities', [])
                if opportunities:
                    st.subheader("🎯 Trading Opportunities")
                    
                    for opp in opportunities:
                        with st.expander(f"{opp.get('pair', 'N/A')} - {opp.get('direction', 'N/A')}"):
                            if opp.get('fisher_warning'):
                                st.warning(opp['fisher_warning'])
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**Pair:**", opp.get('pair', 'N/A'))
                                st.write("**Direction:**", opp.get('direction', 'N/A'))
                                st.write("**Entry:**", opp.get('entry', 'N/A'))
                                st.write("**Stop Loss:**", opp.get('stop_loss', 'N/A'))
                                st.write("**Take Profit:**", opp.get('take_profit', 'N/A'))
                            with col2:
                                st.write("**Confidence:**", f"{opp.get('confidence', 0)*100:.0f}%" if isinstance(opp.get('confidence'), (int, float)) else opp.get('confidence', 'N/A'))
                                st.write("**Reason:**", opp.get('reason', 'N/A'))
            else:
                st.info("⚠️ No approved pairs available. Waiting for Trade-Alerts to provide opportunities.")
        else:
            st.warning("⚠️ Could not load market state. Make sure Trade-Alerts is running and has generated market_state.json")
    
    # Tab 2: Fisher Opportunities (reversal from extremes, per user spec)
    with tab2:
        st.header("🎯 Fisher Transform Opportunities")
        st.caption("Trend exhaustion detector & reversal signals. Daily only. Semi-Auto / Manual — never full-auto.")
        
        # Use dedicated loader: tries main state, falls back to direct file read (bypasses staleness)
        fisher_opps, fisher_count, fisher_updated = load_fisher_opportunities()
        last_scan_est = _format_fisher_scan_time_est(fisher_updated) if fisher_updated else "N/A"
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Fisher Opportunities", fisher_count)
        with col2:
            st.metric("Last scan (EST)", last_scan_est)
        with col3:
            st.caption("Mode: Semi-Auto / Manual only")
        
        st.info("**Scheduled:** Every hour during trading hours (Mon 01:00 UTC – Fri 21:30 UTC). Use the timestamp above to confirm today’s scan ran.")
        
        if fisher_opps:
            semi_auto = SemiAutoController() if SemiAutoController else None
            EXEC_MODES = [
                "MANUAL",
                "FISHER_H1_CROSSOVER",
                "FISHER_M15_CROSSOVER",
                "DMI_H1_CROSSOVER",
                "DMI_M15_CROSSOVER",
                "RECOMMENDED_PRICE",
                "IMMEDIATE_MARKET"
            ]
            SL_TYPES = ["FIXED", "BE_TO_TRAILING", "ATR_TRAILING", "MACD_CROSSOVER", "DMI_CROSSOVER", "STRUCTURE_ATR", "STRUCTURE_ATR_STAGED"]
            for opp in fisher_opps:
                stable_opp_id = get_stable_opportunity_id(opp, source='Fisher') if get_stable_opportunity_id else _normalized_stable_opp_id(opp)
                fc = opp.get('fisher_config', {})
                ec = opp.get('execution_config', {})
                saved = (semi_auto.get_opportunity_config(stable_opp_id) if semi_auto else None) or {}
                enabled = saved.get('enabled', fc.get('enabled', False))
                mode = saved.get('mode', ec.get('activation_trigger', 'MANUAL'))
                sl_type = saved.get('sl_type', fc.get('sl_type', 'BE_TO_TRAILING'))
                max_runs = saved.get('max_runs', ec.get('max_runs', 1))
                with st.expander(
                    f"🔄 {opp.get('pair', 'N/A')} {opp.get('direction', 'N/A')} @ {opp.get('entry', 'N/A')} "
                    f"{'✅ ENABLED' if enabled else '❌ DISABLED'}"
                ):
                    # Per spec: Signal Type, Timeframe, Status
                    entry_type = opp.get('entry_type', '')
                    if entry_type:
                        st.caption(f"**Signal Type:** {entry_type.replace('_', ' ').title()} | **Timeframe:** {opp.get('timeframe', 'DAILY')}")
                    conf = opp.get('confirmations', {})
                    ft_ok = conf.get('ft_crossover', True)
                    macd_ok = conf.get('macd_crossover', False)
                    div_ok = conf.get('divergence', False)
                    adx_1h_ok = conf.get('adx_1h_ok', False)
                    confirm_count = sum([ft_ok, macd_ok, div_ok, adx_1h_ok])
                    status = f"⏳ MONITORING ({confirm_count}/4 confirmations)" if confirm_count < 4 else "✅ FULL CONFIRMATION"
                    st.caption(f"**Status:** {status}")
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                    with col1:
                        st.write("**Trade Details**")
                        st.write("Entry:", opp.get('entry', 'N/A'))
                        st.write("Stop Loss:", opp.get('stop_loss', 'N/A'))
                        st.write("Take Profit:", opp.get('take_profit', 'N/A'))
                        fa = opp.get('fisher_analysis', {})
                        st.write("**Setup:**", fa.get('setup_type', opp.get('entry_type', 'N/A')))
                        conf_pct = opp.get('confidence', 0) * 100
                        conf_label = "VERY HIGH" if conf_pct >= 90 else "HIGH" if conf_pct >= 75 else "MEDIUM"
                        st.write("**Confidence:**", f"{conf_pct:.0f}% ({conf_label})")
                    with col2:
                        st.write("**Confirmation Stages**")
                        st.write(f"{'✅' if ft_ok else '❌'} Stage 1: FT Crossover (Fisher/Trigger)")
                        st.write(f"{'✅' if macd_ok else '❌'} Stage 2: MACD / Signal Crossover")
                        st.caption("OANDA: MACD = blue line, Signal = red line; crossover = MACD line × Signal line")
                        st.write(f"{'✅' if div_ok else '❌'} Stage 3: Divergence")
                        st.write(f"{'✅' if adx_1h_ok else '❌'} Stage 4: 1H ADX >20 or rising 4 candles")
                        fd = opp.get('fisher_data', {})
                        fisher_val = fa.get('daily_fisher') if fa else fd.get('fisher')
                        trigger_val = fd.get('trigger')
                        if fisher_val is not None:
                            st.write("**Fisher:**", f"{fisher_val:.2f}" + (f" | Trigger: {trigger_val:.2f}" if trigger_val is not None else ""))
                        if opp.get('rationale'):
                            st.caption(opp['rationale'][:120] + ("..." if len(opp.get('rationale', '')) > 120 else ""))
                    with col3:
                        st.write("**Semi-Auto Configuration**")
                        if semi_auto:
                            new_enabled = st.checkbox("Enable this trade", value=enabled, key=f"en_{stable_opp_id}")
                            new_mode = st.selectbox(
                                "Execution mode", EXEC_MODES,
                                index=EXEC_MODES.index(mode) if mode in EXEC_MODES else 0,
                                format_func=lambda x: EXEC_MODE_LABELS.get(x, x),
                                key=f"mode_{stable_opp_id}"
                            )
                            new_sl = st.selectbox("Stop loss type", SL_TYPES, index=SL_TYPES.index(sl_type) if sl_type in SL_TYPES else 1, format_func=lambda x: SL_TYPE_LABELS.get(x, x), key=f"sl_{stable_opp_id}")
                            new_max_runs = st.number_input("Max runs", min_value=1, max_value=5, value=max_runs, key=f"runs_{stable_opp_id}")
                            if st.button("💾 Save config", key=f"save_{stable_opp_id}"):
                                reset_run_count = new_enabled and not saved.get('enabled', False)
                                semi_auto.set_opportunity_config(stable_opp_id, enabled=new_enabled, mode=new_mode, max_runs=new_max_runs, sl_type=new_sl, reset_run_count_requested=reset_run_count)
                                st.success("Config saved. Engine will use this when processing this opportunity." + (" Run count reset (re-enabled)." if reset_run_count else ""))
                            if st.button("🔄 Reset run count", key=f"reset_{stable_opp_id}", help="Allow this opportunity to run again up to Max runs."):
                                semi_auto.set_opportunity_config(stable_opp_id, enabled=enabled, mode=mode, max_runs=max_runs, sl_type=sl_type, reset_run_count_requested=True)
                                st.success("Run count reset requested. Next time the engine processes this opportunity it will reset and can execute again.")
                        else:
                            st.write("Activation:", fc.get('activation_trigger', 'N/A'))
                            st.write("Max runs:", ec.get('max_runs', 1))
                            st.caption("SemiAutoController not available (check deployment).")
                    with col4:
                        st.write("**Execution**")
                        st.write("Activation:", fc.get('activation_trigger', 'N/A'))
                        st.write("Max runs:", ec.get('max_runs', 1))
                    if opp.get('warnings'):
                        for w in opp['warnings']:
                            st.warning(w)
        else:
            st.info(
                "No Fisher opportunities yet. Fisher scan runs every hour during trading hours. "
                "Run `cd Scalp-Engine && python run_fisher_scan.py` in the Render shell for an immediate scan. "
                "Once opportunities appear here, you will see **Semi-Auto** controls: **Enable this trade**, **Execution mode**, **Stop loss type**, and **Save config**."
            )
    
    # Tab 3: FT-DMI-EMA Opportunities (4H/1H setup + 15m Fisher trigger)
    with tab3:
        st.header("📐 FT-DMI-EMA Opportunities")
        st.caption("4H trend + 1H confirmation + 15m Fisher trigger. Enable/configure in **Semi-Auto Approval**.")
        
        ft_dmi_ema_opps, ft_dmi_ema_count, ft_dmi_ema_updated = load_ft_dmi_ema_opportunities()
        last_updated_est = _format_fisher_scan_time_est(ft_dmi_ema_updated) if ft_dmi_ema_updated else "N/A"
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("FT-DMI-EMA Opportunities", ft_dmi_ema_count)
        with col2:
            st.metric("Last updated (EST)", last_updated_est)
        with col3:
            st.caption("Enable in Semi-Auto Approval tab")
        
        st.info("**Source:** Engine (SEMI_AUTO/MANUAL) or manual scan: `cd Scalp-Engine && python run_ft_dmi_ema_scan.py`. Requires **FT_DMI_EMA_SIGNALS_ENABLED=true**.")
        
        if ft_dmi_ema_opps:
            for opp in ft_dmi_ema_opps:
                trigger_met = opp.get("ft_15m_trigger_met", False)
                with st.expander(
                    f"📐 {opp.get('pair', 'N/A')} {opp.get('direction', 'N/A')} @ {opp.get('entry', 'N/A')} "
                    f"{'✅ 15m trigger met' if trigger_met else '⏳ Setup ready, wait for 15m trigger'}"
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Trade Details**")
                        st.write("Entry:", opp.get('entry', 'N/A'))
                        st.write("Stop Loss:", opp.get('stop_loss', 'N/A'))
                        st.write("Take Profit:", opp.get('take_profit', 'N/A'))
                        st.write("**15m trigger met:**", "Yes" if trigger_met else "No (setup ready)")
                    with col2:
                        st.write("**Reason**")
                        st.caption(opp.get('reason', '4H bias + 1H confirmation; trigger when 15m Fisher crossover'))
                    st.caption("Enable and set execution/stop loss in **Semi-Auto Approval** tab.")
        else:
            st.info(
                "No FT-DMI-EMA opportunities yet. Set **FT_DMI_EMA_SIGNALS_ENABLED=true** and run "
                "`cd Scalp-Engine && python run_ft_dmi_ema_scan.py` for a manual scan, or ensure the engine is running in SEMI_AUTO/MANUAL. "
                "Enable and configure opportunities in the **Semi-Auto Approval** tab when they appear here."
            )
    
    # Tab 4: DMI-EMA Opportunities (1D/4H/1H DMI+EMA alignment + confidence flags)
    with tab4:
        st.header("📐 DMI-EMA Opportunities")
        st.caption("1D/4H/1H +DI>-DI (or -DI>+DI) + 1H EMA9/26 not intertwined. Enable/configure in **Semi-Auto Approval**.")
        
        dmi_ema_opps, dmi_ema_count, dmi_ema_updated = load_dmi_ema_opportunities()
        last_updated_est = _format_fisher_scan_time_est(dmi_ema_updated) if dmi_ema_updated else "N/A"
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("DMI-EMA Opportunities", dmi_ema_count)
        with col2:
            st.metric("Last updated (EST)", last_updated_est)
        with col3:
            st.caption("Enable in Semi-Auto Approval tab")
        
        st.info("**Source:** Engine (SEMI_AUTO/MANUAL) or manual scan: `cd Scalp-Engine && python run_ft_dmi_ema_scan.py`. Requires **FT_DMI_EMA_SIGNALS_ENABLED=true**.")
        
        if dmi_ema_opps:
            for opp in dmi_ema_opps:
                trigger_met = opp.get("ft_15m_trigger_met", False)
                cf = opp.get("confidence_flags") or {}
                with st.expander(
                    f"📐 {opp.get('pair', 'N/A')} {opp.get('direction', 'N/A')} @ {opp.get('entry', 'N/A')} "
                    f"{'✅ 15m trigger met' if trigger_met else '⏳ Setup ready, wait for 15m trigger'}"
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Trade Details**")
                        st.write("Entry:", opp.get('entry', 'N/A'))
                        st.write("Stop Loss:", opp.get('stop_loss', 'N/A'))
                        st.write("**15m trigger met:**", "Yes" if trigger_met else "No (setup ready)")
                    with col2:
                        st.write("**Reason**")
                        st.caption(opp.get('reason', '1D/4H/1H DMI+EMA alignment.'))
                        st.write("**Confidence flags**")
                        st.caption(f"FT 1H: {'✅' if cf.get('ft_1h') else '❌'} | FT 15m: {'✅' if cf.get('ft_15m') else '❌'} | ADX 15m: {'✅' if cf.get('adx_15m') else '❌'} | ADX 1H: {'✅' if cf.get('adx_1h') else '❌'} | ADX 4H: {'✅' if cf.get('adx_4h') else '❌'}")
                    st.caption("Enable and set execution/stop loss in **Semi-Auto Approval** tab.")
        else:
            st.info(
                "No DMI-EMA opportunities yet. Set **FT_DMI_EMA_SIGNALS_ENABLED=true** and run "
                "`cd Scalp-Engine && python run_ft_dmi_ema_scan.py` (same scan posts both FT-DMI-EMA and DMI-EMA), or ensure the engine is running in SEMI_AUTO/MANUAL. "
                "Enable and configure opportunities in the **Semi-Auto Approval** tab when they appear here."
            )
    
    # Tab 5: Recent Signals
    with tab5:
        st.header("Recent Trading Signals")
        
        signals_df = load_recent_signals(limit=signal_limit)
        
        if not signals_df.empty:
            # Filter options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                outcome_filter = st.selectbox(
                    "Filter by Outcome",
                    ["All", "PENDING", "WIN", "LOSS"]
                )
            
            with col2:
                pair_filter = st.selectbox(
                    "Filter by Pair",
                    ["All"] + list(signals_df['pair'].unique())
                )
            
            with col3:
                regime_filter = st.selectbox(
                    "Filter by Regime",
                    ["All"] + list(signals_df['regime'].unique())
                )
            
            # Apply filters
            filtered_df = signals_df.copy()
            
            if outcome_filter != "All":
                filtered_df = filtered_df[filtered_df['outcome'] == outcome_filter]
            
            if pair_filter != "All":
                filtered_df = filtered_df[filtered_df['pair'] == pair_filter]
            
            if regime_filter != "All":
                filtered_df = filtered_df[filtered_df['regime'] == regime_filter]
            
            # Display signals
            st.dataframe(
                filtered_df.style.format({
                    'strength': '{:.2f}',
                    'ema_spread': '{:.2f}',
                    'pnl': '${:.2f}',
                    'position_size': '{:.0f}'
                }),
                use_container_width=True,
                hide_index=True
            )
            
            # Summary stats
            if not filtered_df.empty:
                st.subheader("Summary")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Signals", len(filtered_df))
                
                with col2:
                    pending = len(filtered_df[filtered_df['outcome'] == 'PENDING'])
                    st.metric("Pending", pending)
                
                with col3:
                    wins = len(filtered_df[filtered_df['outcome'] == 'WIN'])
                    st.metric("Wins", wins)
                
                with col4:
                    losses = len(filtered_df[filtered_df['outcome'] == 'LOSS'])
                    st.metric("Losses", losses)
        else:
            st.info("No signals found in database yet.")
    
    # Tab 6: Performance
    with tab6:
        st.header("Performance Statistics")
        
        overall, by_regime, by_pair = get_performance_stats()
        
        if not overall.empty and overall.iloc[0]['total_trades'] > 0:
            # Overall metrics
            st.subheader("Overall Performance")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            total = int(overall.iloc[0]['total_trades'])
            wins = int(overall.iloc[0]['wins'])
            losses = int(overall.iloc[0]['losses'])
            win_rate = (wins / total * 100) if total > 0 else 0
            avg_pnl = overall.iloc[0]['avg_pnl'] or 0
            total_pnl = overall.iloc[0]['total_pnl'] or 0
            
            with col1:
                st.metric("Total Trades", total)
            
            with col2:
                st.metric("Win Rate", f"{win_rate:.1f}%")
            
            with col3:
                st.metric("Wins", wins)
            
            with col4:
                st.metric("Avg PnL", f"${avg_pnl:.2f}")
            
            with col5:
                st.metric("Total PnL", f"${total_pnl:.2f}")
            
            st.divider()
            
            # By regime
            if not by_regime.empty:
                st.subheader("Performance by Regime")
                st.dataframe(by_regime, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # By pair
            if not by_pair.empty:
                st.subheader("Performance by Pair")
                st.dataframe(by_pair, use_container_width=True, hide_index=True)
        else:
            st.info("No performance data available yet. Execute some trades to see statistics.")
    
    # Tab 7: Market State
    with tab7:
        st.header("Market State Information")

        market_state = load_market_state()
        
        if market_state:
            # Display full market state
            st.json(market_state)
            
            # Timestamp info
            timestamp_str = market_state.get('timestamp', '')
            if timestamp_str:
                formatted_time, age = format_timestamp(timestamp_str)
                st.info(f"**Last Updated:** {formatted_time} ({age})")
        else:
            st.warning("Market state not available")
    
    # Tab 7: Auto-Trader
    with tab8:
        st.title("🤖 Auto-Trader Dashboard")
        
        # Status indicator: load from config-api first (no shared disk)
        config_path = "/var/data/auto_trader_config.json"
        config_mode = "MANUAL"
        config_exists = False
        config_api_url = os.getenv('CONFIG_API_URL', 'https://config-api-8n37.onrender.com/config')
        if config_api_url:
            try:
                api_base = config_api_url.rstrip('/')
                if api_base.endswith('/config'):
                    api_base = api_base[:-7]
                r = requests.get(f"{api_base}/config", timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    config_mode = data.get('trading_mode', 'MANUAL')
                    config_exists = True
            except Exception:
                pass
        if not config_exists and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    config_mode = data.get('trading_mode', 'MANUAL')
                    config_exists = True
            except Exception:
                pass
        
        col_status1, col_status2 = st.columns(2)
        with col_status1:
            if config_mode == "AUTO":
                st.success("✅ Auto-Trader is ACTIVE (AUTO mode)")
            elif config_mode == "SEMI_AUTO":
                st.info("ℹ️ Auto-Trader is in SEMI-AUTO mode — use **Semi-Auto Approval** tab to enable trades")
            elif config_mode == "MANUAL":
                st.info("ℹ️ Auto-Trader is in MANUAL mode (alerts only)")
            else:
                st.warning("⚠️ Auto-Trader status unknown")
        
        with col_status2:
            if config_exists:
                st.success("✅ Configuration loaded (from API)" if config_api_url else "✅ Configuration file exists")
            else:
                st.info("ℹ️ Configuration will be created on first save")
        
        # Create sub-tabs within Auto-Trader tab
        # Semi-Auto Approval tab is first when in SEMI_AUTO mode
        tab_labels = ["⚙️ Configuration", "📈 Active Trades", "🧠 Market Intelligence"]
        if config_mode == "SEMI_AUTO":
            tab_labels.insert(0, "✅ Semi-Auto Approval")
        
        sub_tabs = st.tabs(tab_labels)
        tab_idx = 0
        if config_mode == "SEMI_AUTO":
            with sub_tabs[0]:
                render_semi_auto_approval()
            tab_idx = 1
        
        with sub_tabs[tab_idx]:
            render_auto_trader_controls()
        with sub_tabs[tab_idx + 1]:
            render_active_trades_monitor()
        with sub_tabs[tab_idx + 2]:
            render_market_intelligence()

if __name__ == "__main__":
    main()
