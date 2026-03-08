"""
Simple HTTP server to serve market_state.json for Scalp-Engine
Runs in a separate thread to avoid blocking the main analysis loop
"""
import os
import json
import threading
from pathlib import Path
from typing import Optional
from src.logger import setup_logger

logger = setup_logger()

# Try to import Flask
try:
    from flask import Flask, jsonify, send_file
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logger.warning("⚠️ Flask not available - market state API server disabled")

class MarketStateServer:
    """Simple HTTP server to serve market_state.json"""
    
    def __init__(self, port: Optional[int] = None):
        """
        Initialize market state server
        
        Args:
            port: Port to run the server on. If None, uses PORT env var (for Render web services) or defaults to 5001
        """
        # For Render web services, use PORT environment variable
        # For workers or local dev, use provided port or default to 5001
        if port is None:
            port = int(os.getenv('PORT', 5001))
        self.port = port
        self.app = None
        self.server_thread = None
        self.running = False
        
        if not FLASK_AVAILABLE:
            logger.warning("⚠️ Flask not available - market state server cannot start")
            return
        
        # Get market state file path
        self.market_state_path = Path(
            os.getenv('MARKET_STATE_FILE_PATH', '/var/data/market_state.json')
        )
        
        # Create Flask app
        self.app = Flask(__name__)
        
        @self.app.route('/', methods=['GET', 'HEAD'])
        def root():
            """Root endpoint for Render health checks"""
            return jsonify({
                'status': 'ok',
                'service': 'trade-alerts',
                'endpoints': {
                    'market_state': '/market-state',
                    'health': '/health'
                }
            }), 200
        
        @self.app.route('/market-state', methods=['GET'])
        def get_market_state():
            """Serve market state JSON file"""
            try:
                if not self.market_state_path.exists():
                    return jsonify({
                        'error': 'Market state file not found',
                        'path': str(self.market_state_path)
                    }), 404
                
                with open(self.market_state_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                return jsonify(state), 200
            except json.JSONDecodeError as e:
                return jsonify({
                    'error': 'Invalid JSON in market state file',
                    'details': str(e)
                }), 500
            except Exception as e:
                logger.error(f"Error serving market state: {e}", exc_info=True)
                return jsonify({
                    'error': 'Error reading market state file',
                    'details': str(e)
                }), 500
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            file_exists = self.market_state_path.exists()
            return jsonify({
                'status': 'ok',
                'file_exists': file_exists,
                'file_path': str(self.market_state_path)
            }), 200

        @self.app.route('/download-database', methods=['GET'])
        def download_database():
            """Download RL database for local development"""
            try:
                # Determine database path (Render uses /var/data, local uses data/)
                db_path = Path(os.getenv('RL_DATABASE_PATH', '/var/data/trade_alerts_rl.db'))

                if not db_path.exists():
                    return jsonify({
                        'error': 'Database file not found',
                        'path': str(db_path)
                    }), 404

                logger.info(f"📥 Downloading RL database from {db_path}")

                # Send binary file
                return send_file(
                    db_path,
                    as_attachment=True,
                    download_name='trade_alerts_rl.db',
                    mimetype='application/octet-stream'
                )
            except Exception as e:
                logger.error(f"❌ Error downloading database: {e}", exc_info=True)
                return jsonify({
                    'error': 'Error reading database file',
                    'details': str(e)
                }), 500
    
    def start(self):
        """Start the server in a background thread"""
        if not FLASK_AVAILABLE:
            logger.warning("⚠️ Cannot start market state server - Flask not available")
            return False
        
        if self.running:
            logger.warning("⚠️ Market state server already running")
            return True
        
        def run_server():
            try:
                logger.info(f"🚀 Starting market state server on port {self.port}")
                logger.info(f"   Endpoint: http://0.0.0.0:{self.port}/market-state")
                logger.info(f"   File path: {self.market_state_path}")
                self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
            except Exception as e:
                logger.error(f"❌ Market state server error: {e}", exc_info=True)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.running = True
        
        # Give it a moment to start
        import time
        time.sleep(0.5)
        
        logger.info("✅ Market state server started")
        return True
    
    def stop(self):
        """Stop the server (not typically needed for daemon thread)"""
        self.running = False
        logger.info("🛑 Market state server stopped")
