"""
Historical Backfill Script
ONE-TIME RUN: Process all historical recommendation files from Google Drive
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from src.drive_reader import DriveReader
from src.trade_alerts_rl import (
    RecommendationDatabase,
    RecommendationParser,
    OutcomeEvaluator,
    LLMLearningEngine
)
from src.logger import setup_logger

load_dotenv()
logger = setup_logger()


def run_historical_backfill():
    """Process all historical files and evaluate outcomes"""
    
    logger.info("="*80)
    logger.info("HISTORICAL BACKFILL - ONE-TIME LEARNING INITIALIZATION")
    logger.info("="*80)
    logger.info("")
    
    # Initialize components
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')
    if not folder_id:
        logger.error("GOOGLE_DRIVE_FOLDER_ID not set")
        sys.exit(1)
    
    drive_reader = DriveReader(folder_id)
    db = RecommendationDatabase()
    parser = RecommendationParser()
    evaluator = OutcomeEvaluator()
    learning_engine = LLMLearningEngine(db)
    
    logger.info("✅ Components initialized")
    logger.info(f"📁 Google Drive Folder: {folder_id}")
    logger.info(f"💾 Database: trade_alerts_rl.db")
    logger.info("")
    
    # Step 1: Get ALL historical files (both .txt and .json)
    logger.info("Step 1: Fetching ALL historical files from Google Drive...")
    logger.info("-" * 80)
    
    # Get all files (no pattern filter to get both .txt and .json)
    all_files = drive_reader.list_files()
    
    # Filter for relevant files (summary .txt files and report .json files)
    relevant_files = [
        f for f in all_files 
        if ('summary' in f['title'].lower() and f['title'].lower().endswith('.txt')) or
           ('report' in f['title'].lower() and f['title'].lower().endswith('.json'))
    ]
    
    # Sort by modification date (newest first)
    relevant_files.sort(key=lambda x: x['modifiedDate'], reverse=True)
    
    logger.info(f"Found {len(all_files)} total files in folder")
    logger.info(f"Found {len(relevant_files)} relevant files (.txt summaries and .json reports)")
    
    if len(all_files) == 0:
        logger.error("No files found in Google Drive folder")
        return
    
    # Show date range
    if len(relevant_files) > 0:
        dates = [f['title'] for f in relevant_files]
        logger.info(f"Date range: {dates[-1]} to {dates[0]}")
    
    if len(relevant_files) == 0:
        logger.error("No relevant files found in Google Drive folder")
        return
    
    all_files = relevant_files  # Use filtered list
    
    logger.info("")
    
    # Step 2: Download and parse all files
    logger.info("Step 2: Downloading and parsing files...")
    logger.info("-" * 80)
    
    total_recommendations = 0
    files_processed = 0
    
    for i, file_info in enumerate(all_files, 1):
        try:
            logger.info(f"[{i}/{len(all_files)}] Processing: {file_info['title']}")
            
            # Download file
            file_path = drive_reader.download_file(file_info['id'], file_info['title'])
            
            if not file_path:
                logger.warning(f"  ⚠️  Failed to download")
                continue
            
            # Parse recommendations
            recommendations = parser.parse_file(file_path)
            
            if len(recommendations) == 0:
                logger.warning(f"  ⚠️  No recommendations found in file")
                continue
            
            # Log to database
            for rec in recommendations:
                try:
                    db.log_recommendation(rec)
                    total_recommendations += 1
                except Exception as e:
                    logger.error(f"  ❌ Error logging recommendation: {e}")
            
            logger.info(f"  ✅ Found {len(recommendations)} recommendations")
            files_processed += 1
            
        except Exception as e:
            logger.error(f"  ❌ Error processing file: {e}")
            continue
    
    logger.info("")
    logger.info(f"✅ Processed {files_processed}/{len(all_files)} files")
    logger.info(f"✅ Logged {total_recommendations} recommendations")
    logger.info("")
    
    # Step 3: Evaluate all recommendations
    logger.info("Step 3: Evaluating outcomes using historical market data...")
    logger.info("-" * 80)
    
    # Get all pending recommendations (should be all of them)
    pending = db.get_pending_recommendations(min_age_hours=0)  # Get all
    logger.info(f"Found {len(pending)} recommendations to evaluate")
    logger.info("")
    
    evaluated_count = 0
    wins = 0
    losses = 0
    
    for idx, rec in pending.iterrows():
        try:
            logger.info(f"[{idx+1}/{len(pending)}] Evaluating {rec['llm_source']} - {rec['pair']} {rec['direction']}")
            
            # Evaluate outcome
            outcome = evaluator.evaluate_recommendation(rec)
            
            if outcome:
                db.update_outcome(rec['id'], outcome)
                evaluated_count += 1
                
                if outcome['outcome'] in ['WIN_TP1', 'WIN_TP2']:
                    wins += 1
                    logger.info(f"  ✅ {outcome['outcome']}: +{outcome['pnl_pips']:.1f} pips in {outcome['bars_held']} bars")
                elif outcome['outcome'] == 'LOSS_SL':
                    losses += 1
                    logger.info(f"  ❌ LOSS_SL: {outcome['pnl_pips']:.1f} pips in {outcome['bars_held']} bars")
                else:
                    logger.info(f"  ⚪ NEUTRAL: {outcome['pnl_pips']:.1f} pips")
            else:
                logger.warning(f"  ⚠️  Could not evaluate (insufficient data)")
        
        except Exception as e:
            logger.error(f"  ❌ Error evaluating: {e}")
            continue
    
    logger.info("")
    logger.info(f"✅ Evaluated {evaluated_count}/{len(pending)} recommendations")
    
    if evaluated_count > 0:
        overall_win_rate = wins / evaluated_count
        logger.info(f"📊 Overall Win Rate: {overall_win_rate*100:.1f}% ({wins} wins, {losses} losses)")
    
    logger.info("")
    
    # Step 4: Train initial models and calculate weights
    logger.info("Step 4: Training initial ML models and calculating LLM weights...")
    logger.info("-" * 80)
    
    # Calculate LLM weights
    weights = learning_engine.calculate_llm_weights()
    
    logger.info("🎯 LLM Performance Weights:")
    for llm, weight in weights.items():
        logger.info(f"  {llm.upper()}: {weight*100:.1f}%")
    
    logger.info("")
    
    # Consensus analysis
    consensus = learning_engine.analyze_consensus()
    
    if consensus:
        logger.info("📊 Consensus Analysis:")
        for consensus_type, stats in consensus.items():
            logger.info(f"  {consensus_type}:")
            logger.info(f"    Win Rate: {stats['win_rate']*100:.1f}%")
            logger.info(f"    Sample Size: {stats['sample_size']}")
            logger.info(f"    Avg P&L: {stats['avg_pnl']:.1f} pips")
        logger.info("")
    
    # Generate full performance report
    report = learning_engine.generate_performance_report()
    
    logger.info("📈 Individual LLM Performance:")
    for llm, stats in report['llm_performance'].items():
        if stats['total_recs'] > 0:
            logger.info(f"  {llm.upper()}:")
            logger.info(f"    Total Recommendations: {stats['total_recs']}")
            logger.info(f"    Win Rate: {stats['win_rate']*100:.1f}%")
            logger.info(f"    Avg P&L: {stats['avg_pnl']:.1f} pips")
            logger.info(f"    Profit Factor: {stats['profit_factor']:.2f}")
            logger.info(f"    Avg Bars Held: {stats['avg_bars_held']:.0f}")
            logger.info("")
    
    # Save learning checkpoint
    db.save_learning_checkpoint(
        weights,
        {
            'total_recommendations': total_recommendations,
            'total_evaluated': evaluated_count,
            'overall_win_rate': overall_win_rate if evaluated_count > 0 else 0,
            'notes': 'Initial historical backfill'
        }
    )
    
    # Save individual LLM performance
    for llm, stats in report['llm_performance'].items():
        if stats['total_recs'] > 0:
            db.save_performance_snapshot(llm, {
                'pair': None,
                'total_recommendations': stats['total_recs'],
                'total_evaluated': stats['total_recs'],
                'win_rate': stats['win_rate'],
                'avg_pnl_pips': stats['avg_pnl'],
                'profit_factor': stats['profit_factor'],
                'avg_bars_to_tp': stats['avg_bars_held'],
                'avg_bars_to_sl': stats['avg_bars_held'],
                'accuracy_weight': weights.get(llm, 0.25)
            })
    
    logger.info("="*80)
    logger.info("✅ HISTORICAL BACKFILL COMPLETE")
    logger.info("="*80)
    logger.info("")
    logger.info("💡 Key Findings:")
    logger.info(f"  • Processed {files_processed} historical files")
    logger.info(f"  • Extracted {total_recommendations} recommendations")
    logger.info(f"  • Evaluated {evaluated_count} outcomes")
    if evaluated_count > 0:
        logger.info(f"  • Overall win rate: {overall_win_rate*100:.1f}%")
    logger.info("")
    
    # Recommendations
    if weights:
        best_llm = max(weights, key=weights.get)
        logger.info(f"🏆 Best Performing LLM: {best_llm.upper()} ({weights[best_llm]*100:.1f}%)")
    
    if consensus:
        if 'ALL_AGREE' in consensus and consensus['ALL_AGREE']['sample_size'] > 0:
            all_agree_wr = consensus['ALL_AGREE']['win_rate']
            logger.info(f"✅ When all LLMs agree: {all_agree_wr*100:.1f}% win rate")
    
    logger.info("")
    logger.info("📌 Next Steps:")
    logger.info("  1. Review the performance report above")
    logger.info("  2. System will now use these weights for future recommendations")
    logger.info("  3. Daily learning runs at 11pm UTC to update weights")
    logger.info("")
    logger.info("🗄️  Database saved: trade_alerts_rl.db")
    logger.info("")


if __name__ == '__main__':
    try:
        run_historical_backfill()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

