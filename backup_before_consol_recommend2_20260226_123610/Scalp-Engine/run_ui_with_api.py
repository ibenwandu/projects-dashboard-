#!/usr/bin/env python3
"""
Wrapper script to run Streamlit with Flask API on the same port
Routes /api/* to Flask, everything else to Streamlit

On Render, this replaces: streamlit run scalp_ui.py
"""
import os
import sys
import subprocess
import threading
import time
from flask import Flask, jsonify, request
import requests

# Create Flask app for API endpoints
api_app = Flask(__name__)

# Config file path
CONFIG_FILE = "/var/data/auto_trader_config.json"

@api_app.route('/api/config', methods=['GET'])
def get_config():
    """API endpoint to serve auto-trader configuration"""
    import json
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            return jsonify(config), 200
        else:
            # Return default config
            default_config = {
                'trading_mode': 'MANUAL',
                'max_open_trades': 5,
                'stop_loss_type': 'BE_TO_TRAILING',
                'min_consensus_level': 2,
                'base_position_size': 1000,
                'hard_trailing_pips': 20.0,
                'max_daily_loss': 500.0,
                'consensus_multiplier': {'1': 0.5, '2': 1.0, '3': 1.5},
                'be_trigger_pips': 0.0,
                'atr_multiplier_low_vol': 1.5,
                'atr_multiplier_high_vol': 3.0,
                'max_account_risk_pct': 10.0
            }
            return jsonify(default_config), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'scalp-ui-api'}), 200

# Streamlit runs on a different internal port
STREAMLIT_PORT = 8502
STREAMLIT_URL = f"http://127.0.0.1:{STREAMLIT_PORT}"

def run_streamlit():
    """Run Streamlit on internal port"""
    os.environ['STREAMLIT_SERVER_PORT'] = str(STREAMLIT_PORT)
    cmd = [sys.executable, "-m", "streamlit", "run", "scalp_ui.py", 
           "--server.port", str(STREAMLIT_PORT),
           "--server.address", "127.0.0.1",
           "--server.headless", "true"]
    subprocess.run(cmd)

def proxy_to_streamlit(path):
    """Proxy request to Streamlit"""
    try:
        url = f"{STREAMLIT_URL}{path}"
        response = requests.get(url, timeout=5)
        return response.content, response.status_code, dict(response.headers)
    except Exception as e:
        return str(e), 500, {}

@api_app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@api_app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def catch_all(path):
    """Route /api/* to Flask, everything else to Streamlit"""
    # Check if this is an API route (should be handled by Flask routes above)
    # If we get here for an API route, it means it wasn't matched above
    if path.startswith('api/'):
        return jsonify({'error': f'API endpoint not found: /{path}'}), 404
    
    # All other routes: proxy to Streamlit
    full_path = '/' + path if path else '/'
    try:
        content, status, headers = proxy_to_streamlit(full_path)
        # Remove content-encoding and transfer-encoding headers that might break the response
        headers.pop('Content-Encoding', None)
        headers.pop('Transfer-Encoding', None)
        return content, status, headers
    except Exception as e:
        return f"Error proxying to Streamlit: {str(e)}", 500, {}

if __name__ == '__main__':
    # Start Streamlit in background thread
    streamlit_thread = threading.Thread(target=run_streamlit, daemon=True)
    streamlit_thread.start()
    
    # Wait for Streamlit to start
    time.sleep(3)
    
    # Run Flask on main port (this is what Render will expose)
    port = int(os.getenv('PORT', 8501))
    print(f"🚀 Starting Flask proxy on port {port} (Streamlit on {STREAMLIT_PORT})")
    api_app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
