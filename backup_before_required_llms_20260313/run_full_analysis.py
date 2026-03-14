"""
Run full Trade-Alerts analysis immediately (including email)
This script runs the complete workflow: Drive → LLMs → Synthesis → RL Enhancement → Email
"""

import os
import sys
from dotenv import load_dotenv
from src.logger import setup_logger

load_dotenv()
logger = setup_logger()

def run_full_analysis():
    """Run complete analysis workflow including email"""
    try:
        logger.info("="*80)
        logger.info("🚀 Running FULL Analysis (Complete Workflow with Email)")
        logger.info("="*80)
        logger.info("")
        
        # Import here to ensure environment is loaded
        from main import TradeAlertSystem
        
        # Initialize the full system
        logger.info("Initializing Trade-Alerts system...")
        system = TradeAlertSystem()
        logger.info("✅ System initialized")
        logger.info("")
        
        # Run the full analysis workflow (includes email)
        logger.info("Starting full analysis workflow...")
        logger.info("This includes:")
        logger.info("  - Reading from Google Drive")
        logger.info("  - LLM analysis (ChatGPT, Gemini, Claude)")
        logger.info("  - Synthesis with Gemini")
        logger.info("  - RL enhancement")
        logger.info("  - Email sending")
        logger.info("  - RL database logging")
        logger.info("  - Market state export")
        logger.info("")
        
        # Run the analysis
        system._run_full_analysis_with_rl()
        
        logger.info("")
        logger.info("="*80)
        logger.info("✅ Full analysis completed successfully!")
        logger.info("="*80)
        logger.info("")
        logger.info("📧 Check your email for recommendations")
        logger.info("📊 Check market_state.json for Scalp-Engine")
        logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in full analysis: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = run_full_analysis()
    sys.exit(0 if success else 1)
