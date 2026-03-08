"""
Market State Server: Simple Flask API to receive market state from Trade-Alerts
Deploy as a separate web service on Render, or integrate into existing service
"""

import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import logging
from src.market_state_api import MarketStateAPI

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize market state API
state_api = MarketStateAPI()

# Simple API key authentication (optional but recommended)
API_KEY = os.getenv('MARKET_STATE_API_KEY', 'change-me-in-production')

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'market-state-api'}), 200

@app.route('/market-state', methods=['POST'])
def receive_market_state():
    """
    Receive market state from Trade-Alerts
    
    Expected JSON payload:
    {
        "timestamp": "2026-01-09T20:00:00Z",
        "global_bias": "BULLISH",
        "regime": "TRENDING",
        "approved_pairs": ["EUR/USD", "GBP/USD"],
        "opportunities": [...]
    }
    
    Optional: Include API key in header:
    X-API-Key: your-api-key
    """
    try:
        # Optional: Check API key (if set)
        if API_KEY != 'change-me-in-production':
            api_key_header = request.headers.get('X-API-Key')
            if api_key_header != API_KEY:
                logger.warning(f"Unauthorized request from {request.remote_addr}")
                return jsonify({'error': 'Unauthorized'}), 401
        
        # Get JSON payload
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        state = request.get_json()
        
        if not state:
            return jsonify({'error': 'Empty payload'}), 400
        
        # Validate required fields
        required_fields = ['timestamp', 'global_bias', 'regime', 'approved_pairs']
        missing_fields = [field for field in required_fields if field not in state]
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {missing_fields}',
                'received': list(state.keys())
            }), 400
        
        # Save state
        success = state_api.save_state(state)
        
        if success:
            logger.info(f"✅ Market state received: {state.get('global_bias')} {state.get('regime')} - {len(state.get('approved_pairs', []))} pairs")
            return jsonify({
                'status': 'success',
                'message': 'Market state saved successfully',
                'received': {
                    'bias': state.get('global_bias'),
                    'regime': state.get('regime'),
                    'pairs': state.get('approved_pairs')
                }
            }), 200
        else:
            return jsonify({'error': 'Failed to save market state'}), 500
            
    except Exception as e:
        logger.error(f"❌ Error receiving market state: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/market-state', methods=['GET'])
def get_market_state():
    """Get current market state (for debugging)"""
    state = state_api.load_state()
    if state:
        return jsonify(state), 200
    else:
        return jsonify({'error': 'Market state not available'}), 404


@app.route('/fisher-opportunities', methods=['POST'])
def receive_fisher_opportunities():
    """
    Receive Fisher opportunities from Fisher scan (HTTP instead of shared disk).
    Use when disk is not shared between scalp-engine and market-state-api.
    
    Expected JSON: {"fisher_opportunities": [...], "fisher_count": N, "fisher_last_updated": "ISO8601"}
    """
    try:
        if API_KEY != 'change-me-in-production':
            api_key_header = request.headers.get('X-API-Key')
            if api_key_header != API_KEY:
                return jsonify({'error': 'Unauthorized'}), 401
        
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        if not data or 'fisher_opportunities' not in data:
            return jsonify({'error': 'Missing fisher_opportunities'}), 400
        
        success = state_api.merge_fisher_opportunities(data)
        if success:
            logger.info(f"✅ Fisher opportunities received: {len(data.get('fisher_opportunities', []))} opportunities")
            return jsonify({'status': 'success', 'fisher_count': data.get('fisher_count', 0)}), 200
        return jsonify({'error': 'Failed to merge Fisher opportunities'}), 500
    except Exception as e:
        logger.error(f"❌ Error receiving Fisher opportunities: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/ft-dmi-ema-opportunities', methods=['POST'])
def receive_ft_dmi_ema_opportunities():
    """
    Receive FT-DMI-EMA opportunities from Scalp-Engine (so UI can show them).
    Expected JSON: {"ft_dmi_ema_opportunities": [...], "ft_dmi_ema_last_updated": "ISO8601"}
    """
    try:
        if API_KEY != 'change-me-in-production':
            api_key_header = request.headers.get('X-API-Key')
            if api_key_header != API_KEY:
                return jsonify({'error': 'Unauthorized'}), 401

        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json()
        if not data or 'ft_dmi_ema_opportunities' not in data:
            return jsonify({'error': 'Missing ft_dmi_ema_opportunities'}), 400

        success = state_api.merge_ft_dmi_ema_opportunities(data)
        if success:
            count = len(data.get('ft_dmi_ema_opportunities', []))
            logger.info(f"✅ FT-DMI-EMA opportunities received: {count} opportunities")
            return jsonify({'status': 'success', 'ft_dmi_ema_count': count}), 200
        return jsonify({'error': 'Failed to merge FT-DMI-EMA opportunities'}), 500
    except Exception as e:
        logger.error(f"❌ Error receiving FT-DMI-EMA opportunities: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('ENV', 'production') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)
