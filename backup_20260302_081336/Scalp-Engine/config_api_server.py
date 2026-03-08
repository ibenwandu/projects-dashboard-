"""
Config API Server for Scalp-Engine
Serves auto-trader configuration via HTTP API

Similar to market_state_server.py pattern
"""
import os
import json
import logging
from flask import Flask, jsonify, request, send_file
from datetime import datetime
from pathlib import Path
import glob

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Config file path (on config-api's disk - persists across restarts)
CONFIG_FILE = os.getenv('CONFIG_FILE_PATH', '/var/data/auto_trader_config.json')

# In-memory config storage (primary source, loaded from disk on startup)
_in_memory_config = None
_config_timestamp = None

# In-memory trade states storage (posted by scalp-engine, served to UI)
_in_memory_trade_states = None
_trade_states_timestamp = None
TRADE_STATES_FILE = os.getenv('TRADE_STATES_FILE_PATH', '/var/data/trade_states.json')

# Semi-auto per-opportunity config (UI enables trades; engine reads same data via API)
_in_memory_semi_auto_config = None
_semi_auto_config_timestamp = None
SEMI_AUTO_CONFIG_FILE = os.getenv('SEMI_AUTO_CONFIG_FILE_PATH', '/var/data/semi_auto_config.json')

def _load_config_from_disk():
    """Load config from disk into memory (called on startup and as fallback)"""
    global _in_memory_config, _config_timestamp
    
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            _in_memory_config = config
            _config_timestamp = datetime.utcnow().isoformat()
            logger.info(f"✅ Loaded config from disk into memory - Mode: {config.get('trading_mode', 'UNKNOWN')}")
            return True
    except Exception as e:
        logger.warning(f"⚠️ Could not load config from disk: {e}")
    
    return False

def _save_config_to_disk(config):
    """Save config to disk (persists across restarts)"""
    try:
        # Ensure directory exists
        config_dir = os.path.dirname(CONFIG_FILE)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        # Save to disk
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk
        
        logger.info(f"✅ Saved config to disk: {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving config to disk: {e}")
        return False

# Load config from disk on startup (if available)
_load_config_from_disk()

@app.route('/config', methods=['GET'])
def get_config():
    """
    Get auto-trader configuration
    
    Priority:
    1. In-memory config (from POST /config)
    2. Disk file (fallback)
    3. Default config (last resort)
    """
    global _in_memory_config, _config_timestamp
    
    try:
        # Priority 1: Return in-memory config if available (consol-recommend2 Phase 2.1: last_updated as separate field)
        if _in_memory_config is not None:
            out = dict(_in_memory_config)
            out['last_updated'] = _config_timestamp  # separate field; engine must strip before TradeConfig
            logger.info(f"✅ Config served from memory (Mode: {_in_memory_config.get('trading_mode', 'UNKNOWN')}, updated: {_config_timestamp})")
            return jsonify(out), 200

        # Priority 2: Try loading from disk (fallback - should have been loaded on startup)
        if _load_config_from_disk():
            out = dict(_in_memory_config)
            out['last_updated'] = _config_timestamp
            logger.info(f"✅ Config loaded from disk and served - Mode: {_in_memory_config.get('trading_mode', 'UNKNOWN')}")
            return jsonify(out), 200
        
        # Priority 3: Default config
        default_config = {
            'trading_mode': 'MANUAL',
            'max_open_trades': 5,
            'stop_loss_type': 'BE_TO_TRAILING',
            'auto_trade_llm': True,
            'auto_trade_fisher': True,
            'auto_trade_ft_dmi_ema': True,
            'auto_trade_dmi_ema': True,
            'min_consensus_level': 2,
            'base_position_size': 1000,
            'hard_trailing_pips': 20.0,
            'max_daily_loss': 500.0,
            'consensus_multiplier': {
                '1': 0.5,
                '2': 1.0,
                '3': 1.5,
                '4': 2.0
            },
            'be_trigger_pips': 0.0,
            'atr_multiplier_low_vol': 1.5,
            'atr_multiplier_high_vol': 3.0,
            'max_account_risk_pct': 10.0
        }
        logger.warning(f"⚠️ No config in memory or disk, returning default (MANUAL mode)")
        default_config['last_updated'] = None
        return jsonify(default_config), 200
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in config file: {e}")
        return jsonify({'error': 'Invalid JSON in config file'}), 500
    except Exception as e:
        logger.error(f"❌ Error reading config: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/config', methods=['POST'])
def update_config():
    """
    Update auto-trader configuration (called by scalp-engine-ui when saving)
    
    This bypasses disk sharing issues by storing config in memory
    """
    global _in_memory_config, _config_timestamp
    
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        config = request.get_json()
        
        # Validate required fields
        if 'trading_mode' not in config:
            return jsonify({'error': 'Missing required field: trading_mode'}), 400
        
        # Store in memory AND save to disk (persists across restarts)
        _in_memory_config = config
        _config_timestamp = datetime.utcnow().isoformat()
        
        # Save to disk so it persists across service restarts
        _save_config_to_disk(config)
        
        logger.info(f"✅ Config updated in memory and saved to disk - Mode: {config.get('trading_mode')}, Stop Loss: {config.get('stop_loss_type')}, Max Trades: {config.get('max_open_trades')}")
        
        return jsonify({
            'status': 'success',
            'message': 'Configuration updated and persisted',
            'config': config,
            'timestamp': _config_timestamp
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating config: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/trades', methods=['GET'])
def get_trade_states():
    """
    Get active trade states (for UI to display)
    
    Only in-memory state (from POST /trades by scalp-engine) is served.
    We do NOT fall back to disk: config-api and engine are often separate
    (e.g. different Render services), so disk here can be stale and would
    show phantom trades. Empty in-memory => return empty trades.
    """
    global _in_memory_trade_states, _trade_states_timestamp
    
    try:
        if _in_memory_trade_states is not None:
            logger.info(f"✅ Trade states served from memory ({len(_in_memory_trade_states.get('trades', []))} trades, updated: {_trade_states_timestamp})")
            return jsonify(_in_memory_trade_states), 200
        
        # No in-memory state (e.g. after restart or engine never POSTed).
        # Return empty so UI never shows phantom trades from stale disk.
        empty_trades = {
            'trades': [],
            'pending_signals': [],
            'last_updated': datetime.utcnow().isoformat()
        }
        logger.info("ℹ️ No trade states in memory, returning empty (no disk fallback to avoid stale data)")
        return jsonify(empty_trades), 200
            
    except Exception as e:
        logger.error(f"❌ Error reading trade states: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/trades', methods=['POST'])
def update_trade_states():
    """
    Update trade states (called by scalp-engine when trades change)
    
    This bypasses disk sharing issues by storing trade states in memory
    """
    global _in_memory_trade_states, _trade_states_timestamp
    
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        trade_states = request.get_json()
        
        # Validate required fields
        if 'trades' not in trade_states:
            return jsonify({'error': 'Missing required field: trades'}), 400
        
        # Store in memory AND save to disk (persists across restarts)
        _in_memory_trade_states = trade_states
        _trade_states_timestamp = datetime.utcnow().isoformat()
        
        # Save to disk so it persists across service restarts
        try:
            # Ensure directory exists
            trade_states_dir = os.path.dirname(TRADE_STATES_FILE)
            if not os.path.exists(trade_states_dir):
                os.makedirs(trade_states_dir, exist_ok=True)
            
            # Save to disk
            with open(TRADE_STATES_FILE, 'w') as f:
                json.dump(trade_states, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk

            logger.debug(f"Trade states saved to disk: {TRADE_STATES_FILE}")
        except Exception as e:
            logger.warning(f"⚠️ Could not save trade states to disk: {e}")

        num_trades = len(trade_states.get('trades', []))
        logger.debug(f"Trade states updated in memory - {num_trades} trades (timestamp: {_trade_states_timestamp})")
        
        return jsonify({
            'status': 'success',
            'message': 'Trade states updated and persisted',
            'trades_count': num_trades,
            'timestamp': _trade_states_timestamp
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating trade states: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/semi-auto-config', methods=['GET'])
def get_semi_auto_config():
    """
    Get semi-auto per-opportunity config (enabled, mode, max_runs, etc.).
    Used by scalp-engine and UI so both see the same enabled trades (no shared disk).
    """
    global _in_memory_semi_auto_config, _semi_auto_config_timestamp
    try:
        if _in_memory_semi_auto_config is not None:
            n = len(_in_memory_semi_auto_config.get('opportunities', {}))
            logger.info(f"✅ Semi-auto config served from memory ({n} opportunities, updated: {_semi_auto_config_timestamp})")
            return jsonify(_in_memory_semi_auto_config), 200
        if os.path.exists(SEMI_AUTO_CONFIG_FILE):
            try:
                with open(SEMI_AUTO_CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                n = len(data.get('opportunities', {}))
                logger.info(f"✅ Semi-auto config loaded from disk ({n} opportunities)")
                return jsonify(data), 200
            except Exception as e:
                logger.warning(f"⚠️ Could not load semi-auto config from disk: {e}")
        empty = {'opportunities': {}, 'updated': None}
        logger.info("ℹ️ No semi-auto config, returning empty")
        return jsonify(empty), 200
    except Exception as e:
        logger.error(f"❌ Error reading semi-auto config: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/semi-auto-config', methods=['POST'])
def update_semi_auto_config():
    """
    Update semi-auto config (called by UI when user enables/disables trades).
    Engine will GET this so it sees the same enabled list.
    """
    global _in_memory_semi_auto_config, _semi_auto_config_timestamp
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type: application/json required'}), 400
        data = request.get_json()
        if data is None:
            return jsonify({'error': 'Invalid JSON'}), 400
        if 'opportunities' not in data:
            data = {'opportunities': data if isinstance(data, dict) else {}, 'updated': datetime.utcnow().isoformat()}
        _in_memory_semi_auto_config = data
        _in_memory_semi_auto_config['updated'] = datetime.utcnow().isoformat()
        _semi_auto_config_timestamp = _in_memory_semi_auto_config['updated']
        try:
            os.makedirs(os.path.dirname(SEMI_AUTO_CONFIG_FILE) or '.', exist_ok=True)
            with open(SEMI_AUTO_CONFIG_FILE, 'w') as f:
                json.dump(_in_memory_semi_auto_config, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            logger.info(f"✅ Semi-auto config saved to disk: {SEMI_AUTO_CONFIG_FILE}")
        except Exception as e:
            logger.warning(f"⚠️ Could not save semi-auto config to disk: {e}")
        n = len(_in_memory_semi_auto_config.get('opportunities', {}))
        enabled = sum(1 for o in _in_memory_semi_auto_config.get('opportunities', {}).values() if o.get('enabled'))
        logger.info(f"✅ Semi-auto config updated - {n} opportunities, {enabled} enabled")
        return jsonify({'status': 'success', 'opportunities': n, 'enabled': enabled}), 200
    except Exception as e:
        logger.error(f"❌ Error updating semi-auto config: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def _get_log_dir() -> str:
    """Get log directory path (same logic as src/logger.py)"""
    if os.path.exists('/var/data') and os.access('/var/data', os.W_OK):
        log_dir = '/var/data/logs'
    else:
        # Assume we're running from Scalp-Engine directory
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    
    # Ensure directory exists (critical fix - was missing before)
    try:
        os.makedirs(log_dir, exist_ok=True)
        logger.debug(f"Log directory ensured: {log_dir}")
    except Exception as e:
        logger.error(f"Failed to create log directory {log_dir}: {e}")
        # Don't fail completely - return directory anyway, let caller handle errors
    
    return log_dir


# Map API component name to log filename prefix (for ingest)
LOG_INGEST_COMPONENT_PREFIX = {
    'engine': 'scalp_engine',
    'oanda': 'oanda',
    'ui': 'scalp_ui',
}


@app.route('/logs/ingest', methods=['POST'])
def logs_ingest():
    """
    Ingest log content from other Render services (engine, UI).

    Render does not share disks across services, so scalp-engine and scalp-engine-ui
    push their log content here. We write to config-api's own disk so GET /logs/<component>
    and the backup agent can read it.

    Body: { "component": "engine"|"oanda"|"ui", "content": "full log text" }
    Overwrites the file for that component and today's date.
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid or empty JSON'}), 400

        component = (data.get('component') or '').strip().lower()
        if component not in LOG_INGEST_COMPONENT_PREFIX:
            return jsonify({
                'error': f'Invalid component: {component}',
                'valid': list(LOG_INGEST_COMPONENT_PREFIX.keys())
            }), 400

        content = data.get('content')
        if content is None:
            return jsonify({'error': 'Missing field: content'}), 400
        if not isinstance(content, str):
            content = str(content)

        log_dir = _get_log_dir()
        today = datetime.utcnow().strftime('%Y%m%d')
        prefix = LOG_INGEST_COMPONENT_PREFIX[component]
        filename = f'{prefix}_{today}.log'
        log_file = os.path.join(log_dir, filename)

        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            logger.error(f"Failed to write ingest log file {log_file}: {e}")
            return jsonify({'error': f'Could not write log file: {str(e)}'}), 500

        # consol-recommend3 Phase 1.5: routine successful ingest at DEBUG; 0 chars at DEBUG
        if len(content) == 0:
            logger.debug(f"Log ingest: {component} -> {filename} (0 chars)")
        else:
            logger.debug(f"Log ingest: {component} -> {filename} ({len(content)} chars)")
        return jsonify({
            'status': 'ok',
            'component': component,
            'filename': filename,
            'bytes': len(content.encode('utf-8'))
        }), 200

    except Exception as e:
        logger.error(f"Error in logs/ingest: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/logs', methods=['GET'])
def get_logs():
    """
    List available log files

    Returns JSON with log files metadata
    """
    try:
        log_dir = _get_log_dir()

        if not os.path.exists(log_dir):
            return jsonify({
                'log_dir': log_dir,
                'files': []
            }), 200

        # Scan for log files
        files = []
        for log_file in sorted(glob.glob(os.path.join(log_dir, '*.log')), reverse=True):
            if not os.path.isfile(log_file):
                continue

            try:
                filename = os.path.basename(log_file)
                file_size = os.path.getsize(log_file)
                file_mtime = os.path.getmtime(log_file)
                modified = datetime.fromtimestamp(file_mtime).isoformat()

                # Determine component from filename
                if 'scalp_engine' in filename:
                    component = 'engine'
                elif 'oanda' in filename:
                    component = 'oanda'
                elif 'scalp_ui' in filename:
                    component = 'ui'
                elif 'trade_alerts' in filename:
                    component = 'trade_alerts'
                else:
                    component = 'unknown'

                files.append({
                    'name': filename,
                    'component': component,
                    'size_kb': round(file_size / 1024, 1),
                    'modified': modified
                })
            except Exception as e:
                logger.warning(f"Skipping log file {log_file}: {e}")
                continue

        logger.info(f"Log list requested - {len(files)} files found in {log_dir}")
        return jsonify({
            'log_dir': log_dir,
            'files': files
        }), 200

    except Exception as e:
        logger.error(f"Error listing logs: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/logs/<component>', methods=['GET'])
def get_log_content(component):
    """
    Get log file content for a component

    Args:
        component: 'engine', 'oanda', 'ui', or 'trade_alerts'

    Query params:
        lines: Number of lines to return (default: 500, max: 5000)
        download: If 'true', return as attachment for download

    Returns:
        Plain text log content (last N lines)
    """
    try:
        # Validate component
        valid_components = {'engine', 'oanda', 'ui', 'trade_alerts'}
        if component not in valid_components:
            return jsonify({
                'error': f'Invalid component: {component}. Valid: {valid_components}'
            }), 400

        # Parse query params with error handling
        try:
            lines_param = request.args.get('lines', '500')
            lines = int(lines_param) if lines_param else 500
            lines = min(max(lines, 1), 5000)  # Clamp 1-5000
        except (ValueError, TypeError):
            lines = 500  # Default to 500 if invalid
        
        download = request.args.get('download', 'false').lower() == 'true'

        # Map component to log filename patterns
        component_map = {
            'engine': ['scalp_engine_*.log'],
            'oanda': ['oanda_*.log', 'oanda_trades_*.log'],
            'ui': ['scalp_ui_*.log'],
            'trade_alerts': ['trade_alerts_*.log']
        }

        log_dir = _get_log_dir()
        patterns = component_map[component]

        # Ensure log directory exists (safety check)
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to ensure log directory exists: {e}")
            return jsonify({
                'error': f'Could not access log directory: {str(e)}',
                'log_dir': log_dir
            }), 500

        # Find the most recent log file for this component
        log_files = []
        try:
            for pattern in patterns:
                pattern_path = os.path.join(log_dir, pattern)
                found_files = glob.glob(pattern_path)
                log_files.extend(found_files)
                logger.debug(f"Pattern {pattern} found {len(found_files)} files")
        except Exception as e:
            logger.error(f"Error searching for log files: {e}", exc_info=True)
            return jsonify({
                'error': f'Error searching for log files: {str(e)}',
                'log_dir': log_dir,
                'patterns': patterns
            }), 500

        log_files = sorted(log_files, reverse=True)

        if not log_files:
            # No log files found - return 404 with clear message for UI (consol-recommend2 Phase 3.4)
            logger.warning(f"No log files found for {component} in {log_dir} with patterns {patterns}")
            return jsonify({
                'error': f'No log file found for component: {component}',
                'log_dir': log_dir,
                'patterns': patterns,
                'message': 'Logs not available. Log files may not exist yet (services need to write logs first, or log sync may not have run).'
            }), 404

        log_file = log_files[0]
        
        # Additional safety check
        if not os.path.exists(log_file):
            logger.error(f"Log file {log_file} does not exist (was in glob results but missing)")
            return jsonify({
                'error': f'Log file not found: {os.path.basename(log_file)}',
                'log_dir': log_dir,
                'component': component
            }), 404

        # Read last N lines from the file
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()

        last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        content = ''.join(last_lines)

        logger.info(f"Log content requested - {component} ({len(last_lines)} lines from {os.path.basename(log_file)})")

        if download:
            # Return as file download
            return send_file(
                log_file,
                mimetype='text/plain',
                as_attachment=True,
                download_name=os.path.basename(log_file)
            )
        else:
            # Return as plain text
            return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except IOError as e:
        logger.error(f"IO Error reading log: {e}", exc_info=True)
        # Use variables if they exist, otherwise use defaults
        error_info = {
            'error': f'Could not read log file: {str(e)}',
            'component': component if 'component' in locals() else 'unknown'
        }
        if 'log_dir' in locals():
            error_info['log_dir'] = log_dir
        if 'patterns' in locals():
            error_info['patterns'] = patterns
        return jsonify(error_info), 500
    except Exception as e:
        logger.error(f"Error getting log content: {str(e)}", exc_info=True)
        # Use variables if they exist, otherwise use defaults
        error_info = {
            'error': str(e),
            'component': component if 'component' in locals() else 'unknown'
        }
        if 'log_dir' in locals():
            error_info['log_dir'] = log_dir
        return jsonify(error_info), 500


@app.route('/', methods=['GET'])
def root():
    """Root endpoint - redirects to /config"""
    return jsonify({
        'service': 'config-api',
        'endpoints': {
            '/config': 'GET/POST - Auto-trader configuration',
            '/trades': 'GET/POST - Active trade states',
            '/semi-auto-config': 'GET/POST - Semi-auto per-opportunity config (enabled trades)',
            '/logs': 'GET - List available log files',
            '/logs/ingest': 'POST - Ingest log content from engine/UI (body: component, content)',
            '/logs/<component>': 'GET - Get log content for component (engine, oanda, ui). Query: ?lines=500 ?download=true',
            '/health': 'GET - Health check'
        }
    }), 200

@app.route('/debug/log-dir', methods=['GET'])
def debug_log_dir():
    """Debug endpoint to check log directory status"""
    log_dir = _get_log_dir()
    exists = os.path.exists(log_dir)
    writable = os.access(log_dir, os.W_OK) if exists else False
    
    files = []
    if exists:
        try:
            files = sorted(os.listdir(log_dir))[:20]  # First 20 files
        except Exception as e:
            files = [f"Error listing: {str(e)}"]
    
    # Check what services would use
    from pathlib import Path
    local_log_dir = str(Path(__file__).parent / 'logs')
    local_exists = os.path.exists(local_log_dir)
    
    return jsonify({
        'log_dir': log_dir,
        'exists': exists,
        'writable': writable,
        'files_count': len(files),
        'files': files,
        'env_ENV': os.getenv('ENV'),
        'env_RENDER': os.getenv('RENDER'),
        'local_log_dir': local_log_dir,
        'local_exists': local_exists,
        'detection_method': 'file_check' if os.path.exists('/var/data') else 'env_check'
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    global _in_memory_config, _config_timestamp
    
    config_dir = os.path.dirname(CONFIG_FILE)
    dir_exists = os.path.exists(config_dir)
    dir_readable = os.access(config_dir, os.R_OK) if dir_exists else False
    file_exists = os.path.exists(CONFIG_FILE)
    
    # List files in directory
    dir_files = []
    if dir_exists:
        try:
            dir_files = [f for f in os.listdir(config_dir) if os.path.isfile(os.path.join(config_dir, f))]
        except Exception as e:
            dir_files = [f"Error listing: {str(e)}"]
    
    # Check log directory status
    log_dir = _get_log_dir()
    log_dir_exists = os.path.exists(log_dir)
    log_dir_readable = os.access(log_dir, os.R_OK) if log_dir_exists else False
    log_dir_writable = os.access(log_dir, os.W_OK) if log_dir_exists else False
    
    # List log files
    log_files = []
    if log_dir_exists:
        try:
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')][:10]
        except Exception as e:
            log_files = [f"Error listing: {str(e)}"]
    
    return jsonify({
        'status': 'healthy',
        'service': 'config-api',
        'config_source': 'memory' if _in_memory_config is not None else ('disk' if file_exists else 'default'),
        'config_in_memory': _in_memory_config is not None,
        'config_timestamp': _config_timestamp,
        'config_file': CONFIG_FILE,
        'file_exists': file_exists,
        'config_dir': config_dir,
        'dir_exists': dir_exists,
        'dir_readable': dir_readable,
        'dir_files': dir_files[:10],  # First 10 files for debugging
        'log_dir': log_dir,
        'log_dir_exists': log_dir_exists,
        'log_dir_readable': log_dir_readable,
        'log_dir_writable': log_dir_writable,
        'log_files_count': len(log_files),
        'log_files': log_files,
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/sync-check', methods=['POST'])
def sync_check():
    """
    Manual trigger for periodic sync check
    Detects orphaned orders on OANDA and attempts to cancel stale ones

    This endpoint is called from the UI when user clicks "Manual Sync Check" button
    It triggers the _periodic_sync_check() method in the scalp_engine process via a flag file
    """
    try:
        logger.info("📞 Manual sync check requested from UI")

        # Write a trigger file to tell scalp_engine to run sync check immediately
        trigger_file = '/var/data/sync_check_trigger.flag'
        try:
            with open(trigger_file, 'w') as f:
                f.write(str(datetime.utcnow().isoformat()))
            logger.info(f"✅ Sync check trigger written: {trigger_file}")
        except Exception as e:
            logger.error(f"❌ Failed to write trigger file: {e}")

        return jsonify({
            'status': 'ok',
            'message': 'Manual sync check triggered. Scalp-Engine will check immediately and log results.',
            'orphaned_detected': 0,
            'orphaned_cancelled': 0,
            'note': 'Check Scalp-Engine logs for detailed results. Results will be available in 1-2 seconds.'
        }), 200

    except Exception as e:
        logger.error(f"❌ Error in sync-check endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    logger.info(f"🚀 Starting Config API Server on port {port}")
    logger.info(f"📄 Config file path: {CONFIG_FILE}")
    
    # Load config from disk on startup (if available)
    if _in_memory_config:
        logger.info(f"✅ Config loaded from disk on startup - Mode: {_in_memory_config.get('trading_mode', 'UNKNOWN')}")
    else:
        logger.info(f"ℹ️ No config file found on startup, will use defaults until UI saves config")
    
    app.run(host='0.0.0.0', port=port, debug=False)
