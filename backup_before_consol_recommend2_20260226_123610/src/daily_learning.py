"""
Daily Learning Job
Runs at 11pm UTC every day to evaluate recent recommendations and update weights
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from src.trade_alerts_rl import (
    RecommendationDatabase,
    OutcomeEvaluator,
    LLMLearningEngine
)
from src.logger import setup_logger

load_dotenv()
logger = setup_logger()


def run_daily_learning():
    """
    Daily learning cycle:
    1. Evaluate recommendations from last 24 hours (that are 4+ hours old)
    2. Retrain models with new outcomes
    3. Update LLM weights
    4. Generate performance report
    """
    
    logger.info("="*80)
    logger.info(f"DAILY LEARNING CYCLE - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    logger.info("="*80)
    logger.info("")

    # Initialize components
    # Use same database path as main.py (persistent disk on Render)
    import os
    from pathlib import Path
    db_path = os.getenv('RL_DATABASE_PATH')
    if not db_path:
        # On Render, use persistent disk
        if os.path.exists('/var/data'):
            db_path = '/var/data/trade_alerts_rl.db'
            logger.info("DATABASE: Using Render persistent disk (/var/data)")
        else:
            # Local development
            data_dir = Path(__file__).parent.parent / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / 'trade_alerts_rl.db')
            logger.info("DATABASE: Using local development directory (data/)")
    else:
        logger.info(f"DATABASE: Using custom path from RL_DATABASE_PATH ({db_path})")

    logger.info(f"DATABASE PATH: {db_path}")
    logger.info(f"DATABASE EXISTS: {os.path.exists(db_path)}")
    logger.info("")

    db = RecommendationDatabase(db_path=db_path)
    evaluator = OutcomeEvaluator()
    learning_engine = LLMLearningEngine(db)

    logger.info("COMPONENTS INITIALIZED: RecommendationDatabase, OutcomeEvaluator, LLMLearningEngine")
    logger.info("")
    
    # Step 1: Get pending recommendations (4+ hours old)
    logger.info("Step 1: Fetching pending recommendations...")
    logger.info("-" * 80)
    
    pending = db.get_pending_recommendations(min_age_hours=4)
    logger.info(f"Found {len(pending)} recommendations ready for evaluation")
    logger.info("")
    
    if len(pending) == 0:
        logger.info("ℹ️  No new recommendations to evaluate")
        logger.info("   This is normal if system hasn't generated recommendations in last 24 hours")
        logger.info("")
        return
    
    # Step 2: Evaluate outcomes
    logger.info("Step 2: Evaluating outcomes...")
    logger.info("-" * 80)
    
    evaluated_count = 0
    evaluation_errors = 0
    wins = 0
    losses = 0
    missed = 0
    pending_still = 0

    for idx, rec in pending.iterrows():
        try:
            logger.info(f"[{idx+1}/{len(pending)}] Evaluating {rec['llm_source'].upper()} - {rec['pair']} {rec['direction']} @ {rec['entry_price']:.5f}")

            # Check if trade is expired (24+ hours old and never triggered)
            rec_time = datetime.fromisoformat(rec['timestamp'])
            # Ensure both datetimes are timezone-aware (or both naive) for subtraction
            if rec_time.tzinfo is None:
                # rec_time is naive, use naive datetime.utcnow()
                rec_time_aware = rec_time
                now_aware = datetime.utcnow()
            else:
                # rec_time is aware, convert to UTC-aware for comparison
                from datetime import timezone
                now_aware = datetime.now(timezone.utc)
                # Ensure rec_time is also UTC-aware (convert if it has different timezone)
                if rec_time.tzinfo != timezone.utc:
                    rec_time_aware = rec_time.astimezone(timezone.utc)
                else:
                    rec_time_aware = rec_time
            hours_old = (now_aware - rec_time_aware).total_seconds() / 3600

            logger.debug(f"  Age: {hours_old:.1f} hours, ID: {rec['id']}")

            # If recommendation is 24+ hours old, check if it was ever triggered
            if hours_old >= 24:
                logger.debug(f"  Expired rec (24+ hrs old) - checking if was triggered")
                outcome = evaluator.evaluate_recommendation(rec)
            else:
                # Normal evaluation for trades that might still trigger
                logger.debug(f"  Active rec - evaluating")
                outcome = evaluator.evaluate_recommendation(rec)

            if outcome:
                logger.debug(f"  evaluate_recommendation() returned: {outcome['outcome']}")
                db.update_outcome(rec['id'], outcome)
                evaluated_count += 1

                if outcome['outcome'] in ['WIN_TP1', 'WIN_TP2']:
                    wins += 1
                    logger.info(f"    UPDATE: {outcome['outcome']} - +{outcome['pnl_pips']:.1f} pips in {outcome['bars_held']} bars")
                elif outcome['outcome'] == 'LOSS_SL':
                    losses += 1
                    logger.info(f"    UPDATE: LOSS_SL - {outcome['pnl_pips']:.1f} pips in {outcome['bars_held']} bars")
                elif outcome['outcome'] == 'MISSED':
                    missed += 1
                    logger.info(f"    UPDATE: MISSED - Trade never triggered (entry too far from market)")
                else:
                    logger.info(f"    UPDATE: {outcome['outcome']} - {outcome.get('pnl_pips', 0):.1f} pips")
            else:
                logger.warning(f"    PENDING: evaluate_recommendation() returned None (needs more time or data)")
                pending_still += 1

        except Exception as e:
            evaluation_errors += 1
            logger.error(f"    ERROR: {type(e).__name__}: {e}", exc_info=True)
            continue
    
    logger.info("")
    logger.info("="*80)
    logger.info("EVALUATION SUMMARY")
    logger.info("="*80)
    logger.info(f"Total pending recommendations: {len(pending)}")
    logger.info(f"Evaluated (outcomes updated): {evaluated_count}")
    logger.info(f"Still pending (no outcome yet): {pending_still}")
    logger.info(f"Evaluation errors: {evaluation_errors}")
    logger.info("")

    if evaluated_count > 0:
        logger.info(f"OUTCOMES:")
        logger.info(f"  Wins (WIN_TP1/WIN_TP2): {wins}")
        logger.info(f"  Losses (LOSS_SL): {losses}")
        logger.info(f"  Missed (never triggered): {missed}")

        if (wins + losses) > 0:
            daily_win_rate = wins / (wins + losses)
            logger.info(f"  Win Rate (excluding missed): {daily_win_rate*100:.1f}%")
        else:
            logger.info(f"  No wins/losses to calculate rate (all missed)")

        if missed > 0:
            logger.info(f"  NOTE: {missed} trades never triggered - LLM weights will be penalized")
    else:
        logger.info("No new outcomes to learn from")

    logger.info("")

    if evaluated_count == 0:
        logger.info("No new recommendations were evaluated")
        if pending_still > 0:
            logger.info(f"  ({pending_still} still pending - may need more time)")
        if evaluation_errors > 0:
            logger.info(f"  ({evaluation_errors} errors during evaluation)")
        logger.info("Keeping existing weights")
        logger.info("")
        return
    
    # Step 3: Recalculate LLM weights
    logger.info("Step 3: Recalculating LLM performance weights...")
    logger.info("-" * 80)
    
    weights = learning_engine.calculate_llm_weights()
    
    logger.info("🎯 Updated LLM Weights:")
    for llm, weight in weights.items():
        logger.info(f"  {llm.upper()}: {weight*100:.1f}%")
    
    logger.info("")
    
    # Step 4: Consensus analysis
    logger.info("Step 4: Analyzing consensus patterns...")
    logger.info("-" * 80)
    
    consensus = learning_engine.analyze_consensus()
    
    if consensus:
        logger.info("📊 Consensus Performance:")
        for consensus_type, stats in consensus.items():
            logger.info(f"  {consensus_type}:")
            logger.info(f"    Win Rate: {stats['win_rate']*100:.1f}%")
            logger.info(f"    Sample Size: {stats['sample_size']}")
            logger.info(f"    Avg P&L: {stats['avg_pnl']:.1f} pips")
        logger.info("")
    
    # Step 5: Calculate and save updated weights (AFTER evaluations)
    logger.info("Step 5: Calculating updated LLM weights...")
    logger.info("-" * 80)
    
    weights = learning_engine.calculate_llm_weights()
    
    logger.info("🎯 Updated LLM Weights (after evaluation):")
    for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"   {llm.upper()}: {weight*100:.1f}%")
    logger.info("")
    
    # Step 6: Generate performance report
    logger.info("Step 6: Generating performance report...")
    logger.info("-" * 80)
    
    report = learning_engine.generate_performance_report()
    
    logger.info("📈 Individual LLM Performance (All-Time):")
    for llm, stats in report['llm_performance'].items():
        if stats['total_recs'] > 0:
            logger.info(f"  {llm.upper()}:")
            logger.info(f"    Total: {stats['total_recs']} recommendations")
            logger.info(f"    Win Rate: {stats['win_rate']*100:.1f}%")
            logger.info(f"    Avg P&L: {stats['avg_pnl']:.1f} pips")
            logger.info(f"    Profit Factor: {stats['profit_factor']:.2f}")
            logger.info("")
    
    # Step 7: Save checkpoint (with updated weights)
    logger.info("Step 7: Saving learning checkpoint...")
    logger.info("-" * 80)
    
    # Get total stats
    all_recs = db.get_llm_performance()
    total_evaluated = len(all_recs)
    overall_win_rate = len(all_recs[all_recs['outcome'].isin(['WIN_TP1', 'WIN_TP2'])]) / total_evaluated if total_evaluated > 0 else 0
    
    db.save_learning_checkpoint(
        weights,
        {
            'total_recommendations': total_evaluated,
            'total_evaluated': total_evaluated,
            'overall_win_rate': overall_win_rate,
            'notes': f'Daily learning: evaluated {evaluated_count} new recommendations'
        }
    )
    
    # Save individual LLM snapshots
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
    
    logger.info("✅ Checkpoint saved")
    logger.info("")
    
    # Summary
    logger.info("="*80)
    logger.info("✅ DAILY LEARNING CYCLE COMPLETE")
    logger.info("="*80)
    logger.info("")
    logger.info("📊 Summary:")
    logger.info(f"  • Evaluated {evaluated_count} new recommendations")
    logger.info(f"  • Total evaluated (all-time): {total_evaluated}")
    logger.info(f"  • Overall win rate: {overall_win_rate*100:.1f}%")
    logger.info("")
    
    if weights:
        best_llm = max(weights, key=weights.get)
        logger.info(f"🏆 Best Performing LLM: {best_llm.upper()} ({weights[best_llm]*100:.1f}%)")
    
    logger.info("")
    logger.info("💡 These weights will be used in tomorrow's recommendations")
    logger.info("")


def should_run_learning() -> bool:
    """Check if it's time to run learning (around 11pm UTC)"""
    now = datetime.utcnow()
    
    # Run if it's between 23:00 and 23:59 UTC
    if now.hour == 23:
        return True
    
    return False


if __name__ == '__main__':
    try:
        # Can be run manually anytime, or scheduled for 11pm UTC
        run_daily_learning()
    except Exception as e:
        logger.error(f"Fatal error in daily learning: {e}", exc_info=True)
        sys.exit(1)





