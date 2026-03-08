"""
Quick script to run Trade-Alerts analysis immediately
This will generate market_state.json for Scalp-Engine
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import pytz
import json
from src.drive_reader import DriveReader
from src.data_formatter import DataFormatter
from src.llm_analyzer import LLMAnalyzer
from src.gemini_synthesizer import GeminiSynthesizer
from src.recommendation_parser import RecommendationParser
from src.trade_alerts_rl import (
    RecommendationDatabase,
    LLMLearningEngine
)
from src.market_bridge import MarketBridge
from src.logger import setup_logger

load_dotenv()
logger = setup_logger()

def _convert_opportunity_to_recommendation(opportunity: dict, timestamp: datetime, llm_source: str = 'synthesis') -> dict:
    """
    Convert Step 5 opportunity format to Step 7 recommendation format
    
    Step 5 format:
    {
        'pair': 'GBP/USD',
        'entry': 1.2650,
        'exit': None,
        'stop_loss': 1.2600,
        'direction': 'BUY' or 'SELL',
        'position_size': None,
        'timeframe': 'INTRADAY',
        'recommendation': '...',
        'source': 'text_parsing'
    }
    
    Step 7 format:
    {
        'timestamp': '2026-01-12T03:06:00',
        'date_generated': '2026-01-12',
        'llm_source': 'synthesis',
        'pair': 'GBPUSD',  # No slash
        'direction': 'LONG' or 'SHORT',
        'entry_price': 1.2650,
        'stop_loss': 1.2600,
        'take_profit_1': None,
        'take_profit_2': None,
        'position_size_pct': 2.0,
        'confidence': None,
        'rationale': '...',
        'timeframe': 'INTRADAY',
        'source_file': ''
    }
    """
    # Convert pair format: GBP/USD -> GBPUSD
    pair = opportunity.get('pair', '').replace('/', '').replace('-', '').upper()
    
    # Convert direction: BUY -> LONG, SELL -> SHORT
    direction = opportunity.get('direction', '').upper()
    if direction in ['BUY', 'LONG']:
        direction = 'LONG'
    elif direction in ['SELL', 'SHORT']:
        direction = 'SHORT'
    else:
        direction = 'LONG'  # Default
    
    # Extract exit price as take_profit_1 if available
    tp1 = opportunity.get('exit')
    
    # Convert position_size to position_size_pct (default 2.0)
    position_size = opportunity.get('position_size')
    position_size_pct = 2.0  # Default
    if position_size:
        try:
            # If it's a string with %, extract the number
            if isinstance(position_size, str) and '%' in position_size:
                position_size_pct = float(position_size.replace('%', '').strip())
            else:
                position_size_pct = float(position_size)
        except (ValueError, TypeError):
            position_size_pct = 2.0
    
    timestamp_str = timestamp.isoformat()
    
    return {
        'timestamp': timestamp_str,
        'date_generated': timestamp_str.split('T')[0],
        'llm_source': llm_source.lower(),
        'pair': pair,
        'direction': direction,
        'entry_price': opportunity.get('entry'),
        'stop_loss': opportunity.get('stop_loss'),
        'take_profit_1': tp1,
        'take_profit_2': None,  # Step 5 doesn't extract TP2
        'position_size_pct': position_size_pct,
        'confidence': None,
        'rationale': opportunity.get('recommendation', '')[:500] if opportunity.get('recommendation') else '',
        'timeframe': opportunity.get('timeframe', 'INTRADAY'),
        'source_file': ''
    }

def run_immediate_analysis():
    """Run analysis immediately without waiting for schedule - uses full workflow with consensus"""
    try:
        logger.info("="*80)
        logger.info("🚀 Running IMMEDIATE Analysis (Full Workflow with Consensus)")
        logger.info("="*80)
        
        # Use the main TradeAlertSystem to get the full workflow with consensus calculation
        from main import TradeAlertSystem
        
        # Initialize system (this sets up all components)
        logger.info("Initializing Trade Alert System...")
        system = TradeAlertSystem()
        
        # Run the full analysis workflow (includes consensus calculation)
        logger.info("Running full analysis workflow with RL integration...")
        system._run_full_analysis_with_rl()
        
        logger.info("")
        logger.info("="*80)
        logger.info("✅ IMMEDIATE ANALYSIS COMPLETE")
        logger.info("="*80)
        logger.info(f"Total Opportunities: {len(system.opportunities)}")
        if system.opportunities:
            logger.info("Opportunities with consensus:")
            for opp in system.opportunities:
                consensus = opp.get('consensus_level', 1)
                logger.info(f"  - {opp.get('pair')} {opp.get('direction')} @ {opp.get('entry')} (Consensus: {consensus}/4)")
        logger.info("="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in immediate analysis: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = run_immediate_analysis()
    sys.exit(0 if success else 1)
