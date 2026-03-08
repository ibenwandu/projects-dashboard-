"""
Manual Daily Learning Trigger
Run this script to manually trigger the daily learning cycle
This will evaluate pending recommendations and update LLM weights
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.daily_learning import run_daily_learning
from src.logger import setup_logger

logger = setup_logger()

if __name__ == '__main__':
    logger.info("="*80)
    logger.info("🚀 MANUAL DAILY LEARNING TRIGGER")
    logger.info("="*80)
    logger.info("")
    logger.info("This will:")
    logger.info("  1. Evaluate pending recommendations (4+ hours old)")
    logger.info("  2. Calculate updated LLM performance weights")
    logger.info("  3. Save learning checkpoint")
    logger.info("")
    
    try:
        run_daily_learning()
        logger.info("")
        logger.info("✅ Daily learning completed successfully!")
        logger.info("   LLM weights have been updated based on evaluated recommendations")
    except Exception as e:
        logger.error(f"❌ Error running daily learning: {e}", exc_info=True)
        sys.exit(1)
