"""
Flask API server for Scalp-Engine UI
Serves /api/config endpoint alongside Streamlit

This runs in a background thread when scalp_ui.py is imported
"""
import os
import json
import threading
import logging

try:
    from flask import Flask, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config file path
CONFIG_FILE = "/var/data/auto_trader_config.json"

if FLASK_AVAILABLE:
    # Create Flask app
    api_app = Flask(__name__)
    
    @api_app.route('/api/config', methods=['GET'])
    def get_config():
        """API endpoint to serve auto-trader configuration"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                logger.info(f"✅ Config served from {CONFIG_FILE}")
                return jsonify(config), 200
            else:
                # Return default config if file doesn't exist
                default_config = {
                    'trading_mode': 'MANUAL',
                    'max_open_trades': 5,
                    'stop_loss_type': 'BE_TO_TRAILING',
                    'min_consensus_level': 2,
                    'base_position_size': 1000,
                    'hard_trailing_pips': 20.0,
                    'max_daily_loss': 500.0,
                    'consensus_multiplier': {
                        '1': 0.5,
                        '2': 1.0,
                        '3': 1.5
                    },
                    'be_trigger_pips': 0.0,
                    'atr_multiplier_low_vol': 1.5,
                    'atr_multiplier_high_vol': 3.0,
                    'max_account_risk_pct': 10.0
                }
                logger.info(f"ℹ️ Config file not found, returning default config")
                return jsonify(default_config), 200
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in config file: {e}")
            return jsonify({'error': 'Invalid JSON in config file'}), 500
        except Exception as e:
            logger.error(f"❌ Error reading config file: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @api_app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({'status': 'healthy', 'service': 'scalp-ui-api'}), 200
    
    def run_api_server():
        """Run Flask API server in background thread"""
        # Use a high port number for internal API
        # On Render, this won't be directly accessible from outside,
        # but we can use it if we set up a reverse proxy or use Streamlit's query routing
        # For now, we'll use port 8501 (internal)
        port = int(os.getenv('API_PORT', 8501))
        try:
            logger.info(f"🚀 Starting Flask API server on port {port}")
            api_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            logger.error(f"❌ Failed to start API server: {e}")
