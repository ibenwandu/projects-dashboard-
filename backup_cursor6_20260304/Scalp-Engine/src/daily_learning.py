"""
Daily Learning Cycle for Scalp-Engine RL System
Runs daily to evaluate pending signals and update LLM weights
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from scalping_rl_enhanced import (
    ScalpingRLEnhanced,
    OutcomeEvaluator,
    LLMLearningEngine
)


def run_daily_learning(db_path: str = None):
    """
    Daily learning cycle:
    1. Evaluate pending signals (both executed and simulated) that are 4+ hours old
    2. Calculate new performance metrics for each LLM
    3. Update LLM weights based on performance
    4. Save learning checkpoint
    5. Generate performance report
    """
    
    print("="*80)
    print(f"DAILY LEARNING CYCLE - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("="*80)
    print("")
    
    # Initialize database path
    if db_path is None:
        # Use persistent disk on Render, default location for local development
        if os.path.exists('/var/data'):
            db_path = '/var/data/scalping_rl.db'
            print(f"📦 Using persistent disk for RL database: {db_path}")
        else:
            # Local development - use data directory
            data_dir = Path(__file__).parent.parent / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / 'scalping_rl.db')
            print(f"📦 Using local database for RL: {db_path}")
    
    # Initialize components
    db = ScalpingRLEnhanced(db_path=db_path)
    evaluator = OutcomeEvaluator()
    learning_engine = LLMLearningEngine(db)
    
    # Step 1: Get pending signals (4+ hours old)
    print("Step 1: Fetching pending signals...")
    print("-" * 80)
    
    pending = db.get_pending_signals(min_age_minutes=240)  # 4 hours = 240 minutes
    print(f"Found {len(pending)} signals ready for evaluation")
    print("")
    
    if len(pending) == 0:
        print("ℹ️  No new signals to evaluate")
        print("   This is normal if system hasn't generated signals in last 4 hours")
        print("")
        return
    
    # Step 2: Evaluate outcomes
    print("Step 2: Evaluating outcomes...")
    print("-" * 80)
    
    evaluated_count = 0
    wins = 0
    losses = 0
    missed = 0
    
    for idx, signal in enumerate(pending):
        try:
            signal_id = signal['id']
            pair = signal['pair']
            direction = signal['direction']
            executed = signal['executed']
            
            print(f"[{idx+1}/{len(pending)}] {'EXECUTED' if executed else 'SIMULATED'} - {pair} {direction} @ {signal['entry_price']}")
            
            # For executed trades, we should already have the outcome from OANDA
            # But we can still simulate to verify or if outcome wasn't recorded
            if executed:
                # Check if outcome already recorded
                # If not, simulate to get outcome
                result = evaluator.evaluate_signal(signal)
                if result:
                    db.update_outcome_simulated(
                        signal_id=signal_id,
                        outcome=result['outcome'],
                        exit_price=result['exit_price'],
                        pnl_pips=result['pnl_pips'],
                        bars_held=result.get('bars_held'),
                        max_favorable_pips=result.get('max_favorable_pips'),
                        max_adverse_pips=result.get('max_adverse_pips')
                    )
                    evaluated_count += 1
                    if result['outcome'] == 'WIN':
                        wins += 1
                    elif result['outcome'] == 'LOSS':
                        losses += 1
                    elif result['outcome'] == 'MISSED':
                        missed += 1
                    print(f"   ✅ Evaluated: {result['outcome']} ({result['pnl_pips']:.2f} pips)")
                else:
                    print(f"   ⚠️  Could not evaluate signal {signal_id}")
            else:
                # Simulated opportunity - evaluate using market data
                result = evaluator.evaluate_signal(signal)
                if result:
                    db.update_outcome_simulated(
                        signal_id=signal_id,
                        outcome=result['outcome'],
                        exit_price=result['exit_price'],
                        pnl_pips=result['pnl_pips'],
                        bars_held=result.get('bars_held'),
                        max_favorable_pips=result.get('max_favorable_pips'),
                        max_adverse_pips=result.get('max_adverse_pips')
                    )
                    evaluated_count += 1
                    if result['outcome'] == 'WIN':
                        wins += 1
                    elif result['outcome'] == 'LOSS':
                        losses += 1
                    elif result['outcome'] == 'MISSED':
                        missed += 1
                    print(f"   ✅ Simulated: {result['outcome']} ({result['pnl_pips']:.2f} pips)")
                else:
                    print(f"   ⚠️  Could not evaluate signal {signal_id}")
            
        except Exception as e:
            print(f"   ❌ Error evaluating signal {signal.get('id', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()
    
    print("")
    print(f"✅ Evaluated {evaluated_count} signals: {wins} wins, {losses} losses, {missed} missed")
    print("")
    
    # Step 3: Calculate new weights
    print("Step 3: Calculating LLM weights...")
    print("-" * 80)
    
    weights = learning_engine.calculate_llm_weights()
    
    for llm, weight in weights.items():
        print(f"   {llm.upper()}: {weight:.1%}")
    
    print("")
    
    # Step 4: Generate performance report
    print("Step 4: Generating performance report...")
    print("-" * 80)
    
    report = learning_engine.generate_performance_report()
    
    print(f"Overall Performance:")
    print(f"   Total signals evaluated: {evaluated_count}")
    print(f"   Win rate: {wins / (wins + losses) * 100:.1f}%" if (wins + losses) > 0 else "   Win rate: N/A")
    print("")
    
    print("LLM Performance:")
    for llm, perf in report.get('llm_performance', {}).items():
        print(f"   {llm.upper()}:")
        print(f"      Total signals: {perf.get('total_signals', 0)}")
        print(f"      Executed: {perf.get('executed_count', 0)}, Simulated: {perf.get('simulated_count', 0)}")
        print(f"      Win rate: {perf.get('win_rate', 0) * 100:.1f}%")
        print(f"      Avg P&L: {perf.get('avg_pnl', 0):.2f} pips")
        print(f"      Profit factor: {perf.get('profit_factor', 0):.2f}")
    
    print("")
    
    # Step 5: Save checkpoint
    print("Step 5: Saving learning checkpoint...")
    print("-" * 80)
    
    # Save checkpoint to database
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    c = conn.cursor()
    c.execute('''
        INSERT INTO learning_checkpoints (
            timestamp, total_signals, total_evaluated,
            gemini_weight, synthesis_weight, chatgpt_weight, claude_weight, deepseek_weight,
            overall_win_rate, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.utcnow().isoformat(),
        len(pending),
        evaluated_count,
        weights.get('gemini', 0.2),
        weights.get('synthesis', 0.2),
        weights.get('chatgpt', 0.2),
        weights.get('claude', 0.2),
        weights.get('deepseek', 0.2),
        wins / (wins + losses) if (wins + losses) > 0 else 0,
        f"Daily learning cycle - {evaluated_count} signals evaluated"
    ))
    conn.commit()
    conn.close()
    
    print("✅ Learning checkpoint saved")
    print("")
    print("="*80)
    print("DAILY LEARNING CYCLE COMPLETE")
    print("="*80)


if __name__ == "__main__":
    # Can be run manually for testing
    run_daily_learning()
