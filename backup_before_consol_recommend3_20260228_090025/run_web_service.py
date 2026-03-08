"""
Web Service Wrapper for Trade-Alerts
Runs both the Flask API server (on main thread) and the analysis loop (in background thread)
This allows Trade-Alerts to be deployed as a web service on Render
"""
import os
import threading
import time
from src.logger import setup_logger

logger = setup_logger()

def run_analysis_loop():
    """Run the main Trade-Alerts analysis loop in a background thread"""
    try:
        from main import TradeAlertSystem
        
        logger.info("🔄 Starting Trade-Alerts analysis loop in background thread...")
        system = TradeAlertSystem()
        
        # Don't start the market state server here (it's started in main thread)
        # Just run the analysis loop
        system.run()
    except Exception as e:
        logger.error(f"❌ Error in analysis loop: {e}", exc_info=True)

def main():
    """Main entry point - runs Flask server on main thread, analysis loop in background"""
    logger.info("=" * 80)
    logger.info("🚀 Trade-Alerts Web Service Starting")
    logger.info("=" * 80)
    
    # Get port from environment (Render provides this for web services)
    port = int(os.getenv('PORT', 5001))
    logger.info(f"📡 Starting Flask API server on port {port}")
    
    # Import and initialize market state server
    try:
        from src.market_state_server import MarketStateServer
        
        # Create server instance (will use PORT env var)
        server = MarketStateServer(port=port)
        
        if not server.app:
            logger.error("❌ Failed to initialize Flask app - Flask may not be available")
            logger.error("   Checking if Flask is installed...")
            try:
                import flask
                logger.error(f"   Flask version: {flask.__version__}")
                logger.error("   Flask is installed but app creation failed - this is a critical error")
            except ImportError:
                logger.error("   Flask is NOT installed - add 'flask>=3.0.0' to requirements.txt")
            logger.error("   Falling back to worker mode (analysis only)")
            # Fall back to running just the analysis loop
            run_analysis_loop()
            return
        
        # Start analysis loop in background thread
        analysis_thread = threading.Thread(target=run_analysis_loop, daemon=True)
        analysis_thread.start()
        
        # Give analysis thread a moment to start
        time.sleep(1)
        
        logger.info("✅ Analysis loop started in background thread")
        logger.info("✅ Flask API server starting on main thread")
        logger.info(f"   API endpoint: http://0.0.0.0:{port}/market-state")
        logger.info(f"   Health check: http://0.0.0.0:{port}/health")
        logger.info(f"   Binding to port {port} (from PORT env var: {os.getenv('PORT', 'NOT SET')})")
        logger.info("")
        logger.info("🛑 Press Ctrl+C to stop")
        logger.info("=" * 80)
        
        # Run Flask server on main thread (blocks)
        # This MUST bind to the port for Render to detect it
        try:
            server.app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
            logger.info(f"✅ Flask server started successfully on port {port}")
        except Exception as e:
            logger.error(f"❌ Failed to start Flask server on port {port}: {e}", exc_info=True)
            logger.error("   This will cause 'No open ports detected' error on Render")
            raise
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("   Falling back to worker mode (analysis only)")
        run_analysis_loop()
    except Exception as e:
        logger.error(f"❌ Error starting web service: {e}", exc_info=True)
        logger.error("   Falling back to worker mode (analysis only)")
        run_analysis_loop()

if __name__ == '__main__':
    main()
