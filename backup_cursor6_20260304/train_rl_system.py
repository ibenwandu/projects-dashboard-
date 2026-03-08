#!/usr/bin/env python3
"""
RL System Training Script
Improves LLM performance by:
1. Backfilling historical recommendations from CSV
2. Evaluating pending recommendations
3. Calculating and updating LLM weights
4. Generating performance reports
"""

import os
import sys
import csv
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from io import StringIO
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.trade_alerts_rl import (
    RecommendationDatabase,
    RecommendationParser,
    OutcomeEvaluator,
    LLMLearningEngine
)
from src.logger import setup_logger

logger = setup_logger()

class RLTrainingSystem:
    """Training system for RL"""
    
    def __init__(self, db_path: str = None):
        # Use same database path logic as main.py
        if db_path is None:
            # Use persistent disk on Render, default location for local development
            if os.path.exists('/var/data'):
                db_path = '/var/data/trade_alerts_rl.db'
                logger.info(f"📦 Using persistent disk for RL database: {db_path}")
            else:
                # Local development - use data directory
                data_dir = Path(__file__).parent / 'data'
                data_dir.mkdir(exist_ok=True)
                db_path = str(data_dir / 'trade_alerts_rl.db')
                logger.info(f"📦 Using local database for RL: {db_path}")
        
        # Disable entry validation for CSV imports (historical prices will differ from current)
        self.db = RecommendationDatabase(db_path=db_path, validate_entries=False)
        self.parser = RecommendationParser()
        self.evaluator = OutcomeEvaluator()
        self.learning_engine = LLMLearningEngine(self.db)
    
    def import_csv_recommendations(self, csv_path: str) -> int:
        """
        Import recommendations from CSV evaluation file
        
        CSV Format:
        Date,Time (UTC),Pair,Timeframe,Entry,Exit Price,Stop Loss,Lowest Price (UTC),Highest Price (UTC),Analyst
        """
        imported = 0
        evaluated = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                # Read all lines
                all_lines = f.readlines()
                
                # Find header row (contains 'Pair' and 'Entry')
                header_idx = None
                for i, line in enumerate(all_lines):
                    if 'Pair' in line and 'Entry' in line:
                        header_idx = i
                        break
                
                if header_idx is None:
                    logger.error("Could not find header row in CSV")
                    return 0
                
                # Create StringIO from header onwards
                from io import StringIO
                csv_content = ''.join(all_lines[header_idx:])
                
                # Create reader starting from header
                reader = csv.DictReader(StringIO(csv_content))
                
                for row in reader:
                    try:
                        # Skip empty rows or rows with missing critical data
                        pair_val = row.get('Pair', '').strip() if row.get('Pair') else ''
                        entry_val = row.get('Entry', '').strip() if row.get('Entry') else ''
                        
                        if not pair_val or not entry_val:
                            continue
                        
                        # Parse date/time
                        date_str = row.get('Date', '').strip()
                        time_str = row.get('Time (UTC)', '').strip()
                        
                        if not date_str or not time_str:
                            continue
                        
                        # Combine date and time
                        datetime_str = f"{date_str} {time_str}"
                        try:
                            timestamp = datetime.strptime(datetime_str, "%Y-%m-%d %I:%M:%S %p")
                        except ValueError:
                            try:
                                timestamp = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                logger.warning(f"Could not parse datetime: {datetime_str}")
                                continue
                        
                        # Extract data
                        pair = pair_val.replace('/', '').replace('-', '').upper()
                        llm_source = row.get('Analyst', '').strip().lower()
                        
                        # Map analyst names to LLM sources
                        llm_mapping = {
                            'chatgpt': 'chatgpt',
                            'gemini': 'gemini',
                            'claude': 'claude',
                            'final gemini': 'synthesis',
                            'gemini final': 'synthesis'
                        }
                        
                        llm_source = llm_mapping.get(llm_source, 'synthesis')
                        
                        # Extract prices
                        try:
                            entry_price = float(entry_val)
                            exit_price_str = row.get('Exit Price', '').strip()
                            stop_loss_str = row.get('Stop Loss', '').strip()
                            
                            exit_price = float(exit_price_str) if exit_price_str else None
                            stop_loss = float(stop_loss_str) if stop_loss_str else None
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Could not parse prices for {pair}: {e}")
                            continue
                        
                        if entry_price == 0:
                            continue
                        
                        # Determine direction from entry/exit/stop_loss
                        # For LONG: TP > Entry, SL < Entry
                        # For SHORT: TP < Entry, SL > Entry
                        direction = 'LONG'  # Default
                        if exit_price and stop_loss:
                            # If TP is below entry and SL is above entry, it's SHORT
                            if exit_price < entry_price and stop_loss > entry_price:
                                direction = 'SHORT'
                            # If TP is above entry and SL is below entry, it's LONG
                            elif exit_price > entry_price and stop_loss < entry_price:
                                direction = 'LONG'
                            # Fallback: use TP position relative to entry
                            elif exit_price < entry_price:
                                direction = 'SHORT'
                        elif exit_price:
                            # Use TP position relative to entry
                            if exit_price < entry_price:
                                direction = 'SHORT'
                        
                        # Extract timeframe
                        timeframe = row.get('Timeframe', 'INTRADAY').upper()
                        if timeframe not in ['INTRADAY', 'SWING']:
                            timeframe = 'INTRADAY'
                        
                        # Create recommendation dict
                        rec = {
                            'timestamp': timestamp.isoformat(),
                            'date_generated': date_str,
                            'llm_source': llm_source,
                            'pair': pair,
                            'direction': direction,
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit_1': exit_price,
                            'take_profit_2': None,
                            'position_size_pct': 2.0,
                            'confidence': None,
                            'rationale': f"Imported from CSV evaluation",
                            'timeframe': timeframe,
                            'source_file': csv_path
                        }
                        
                        # Log to database (use INSERT OR IGNORE to avoid duplicates)
                        try:
                            rec_id = self.db.log_recommendation(rec)
                            if rec_id:
                                imported += 1
                                
                                # If we have historical price data, evaluate immediately
                                if exit_price and stop_loss:
                                    try:
                                        self._evaluate_recommendation(rec_id, rec, row)
                                        evaluated += 1
                                    except Exception as e:
                                        logger.warning(f"Could not evaluate imported recommendation {rec_id}: {e}")
                            else:
                                # Duplicate (INSERT OR IGNORE returned 0)
                                logger.debug(f"Skipped duplicate: {pair} {direction} @ {entry_price} from {llm_source}")
                        except Exception as e:
                            logger.error(f"Error logging recommendation to database: {e}")
                            continue
                        
                    except Exception as e:
                        logger.error(f"Error importing row: {e}", exc_info=True)
                        continue
            
            logger.info(f"✅ Imported {imported} recommendations from CSV")
            if evaluated > 0:
                logger.info(f"✅ Immediately evaluated {evaluated} recommendations using CSV price data")
            return imported
            
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            return 0
    
    def _evaluate_recommendation(self, rec_id: int, rec: Dict, csv_row: Dict):
        """Evaluate recommendation using CSV outcome data"""
        try:
            # Get historical prices from CSV
            lowest_price = float(csv_row.get('Lowest Price (UTC)', 0)) if csv_row.get('Lowest Price (UTC)') else None
            highest_price = float(csv_row.get('Highest Price (UTC)', 0)) if csv_row.get('Highest Price (UTC)') else None
            
            if not lowest_price or not highest_price:
                return
            
            entry = rec['entry_price']
            stop_loss = rec['stop_loss']
            take_profit = rec['take_profit_1']
            direction = rec['direction']
            
            if not stop_loss or not take_profit:
                return
            
            # Determine outcome
            outcome = 'PENDING'
            exit_price = None
            pnl_pips = None
            
            if direction == 'LONG':
                # Check if stop loss was hit
                if lowest_price <= stop_loss:
                    outcome = 'LOSS_SL'
                    exit_price = stop_loss
                    pips_per_unit = 0.0001 if 'JPY' not in rec['pair'] else 0.01
                    pnl_pips = (stop_loss - entry) / pips_per_unit
                # Check if take profit was hit
                elif highest_price >= take_profit:
                    outcome = 'WIN_TP1'
                    exit_price = take_profit
                    pips_per_unit = 0.0001 if 'JPY' not in rec['pair'] else 0.01
                    pnl_pips = (take_profit - entry) / pips_per_unit
            else:  # SHORT
                # Check if stop loss was hit
                if highest_price >= stop_loss:
                    outcome = 'LOSS_SL'
                    exit_price = stop_loss
                    pips_per_unit = 0.0001 if 'JPY' not in rec['pair'] else 0.01
                    pnl_pips = (entry - stop_loss) / pips_per_unit
                # Check if take profit was hit
                elif lowest_price <= take_profit:
                    outcome = 'WIN_TP1'
                    exit_price = take_profit
                    pips_per_unit = 0.0001 if 'JPY' not in rec['pair'] else 0.01
                    pnl_pips = (entry - take_profit) / pips_per_unit
            
            # Update recommendation with outcome
            if outcome != 'PENDING':
                outcome_data = {
                    'outcome': outcome,
                    'exit_price': exit_price,
                    'pnl_pips': pnl_pips,
                    'bars_held': None,  # Not available from CSV
                    'max_favorable_pips': None,
                    'max_adverse_pips': None,
                    'timestamp': datetime.utcnow().isoformat()
                }
                self.db.update_outcome(rec_id, outcome_data)
                logger.info(f"✅ Evaluated recommendation {rec_id}: {outcome} @ {exit_price} ({pnl_pips:.1f} pips)")
        
        except Exception as e:
            logger.error(f"Error evaluating recommendation {rec_id}: {e}")
    
    def evaluate_pending_recommendations(self, min_age_hours: int = 4) -> int:
        """Evaluate all pending recommendations"""
        logger.info(f"Evaluating pending recommendations (min age: {min_age_hours} hours)...")
        
        pending = self.db.get_pending_recommendations(min_age_hours=min_age_hours)
        
        if len(pending) == 0:
            logger.info("No pending recommendations to evaluate")
            return 0
        
        logger.info(f"Found {len(pending)} pending recommendations")
        
        evaluated = 0
        for _, rec in pending.iterrows():
            try:
                outcome = self.evaluator.evaluate_recommendation(rec.to_dict())
                if outcome and outcome.get('outcome') != 'PENDING':
                    self.db.update_outcome(rec['id'], outcome)
                    evaluated += 1
                    logger.info(f"✅ Evaluated recommendation {rec['id']}: {outcome['outcome']}")
            except Exception as e:
                logger.error(f"Error evaluating recommendation {rec['id']}: {e}")
        
        logger.info(f"✅ Evaluated {evaluated} recommendations")
        return evaluated
    
    def calculate_and_save_weights(self) -> Dict[str, float]:
        """Calculate and save new LLM weights"""
        logger.info("Calculating LLM weights...")
        
        weights = self.learning_engine.calculate_llm_weights()
        
        # Get statistics
        stats = self._get_overall_stats()
        
        # Save checkpoint
        self.db.save_learning_checkpoint(weights, stats)
        
        logger.info("✅ Updated LLM weights:")
        for llm, weight in weights.items():
            logger.info(f"   {llm}: {weight*100:.1f}%")
        
        return weights
    
    def _get_overall_stats(self) -> Dict:
        """Get overall statistics"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Total recommendations
            cursor.execute('SELECT COUNT(*) FROM recommendations')
            total_recs = cursor.fetchone()[0]
            
            # Evaluated recommendations
            cursor.execute('SELECT COUNT(*) FROM recommendations WHERE evaluated = 1')
            total_evaluated = cursor.fetchone()[0]
            
            # Win rate
            cursor.execute('''
                SELECT COUNT(*) FROM recommendations 
                WHERE evaluated = 1 AND outcome IN ('WIN_TP1', 'WIN_TP2')
            ''')
            wins = cursor.fetchone()[0]
            win_rate = wins / total_evaluated if total_evaluated > 0 else 0.0
            
            return {
                'total_recommendations': total_recs,
                'total_evaluated': total_evaluated,
                'overall_win_rate': win_rate,
                'notes': 'Training script update'
            }
    
    def generate_performance_report(self) -> str:
        """Generate performance report"""
        report = []
        report.append("="*80)
        report.append("RL SYSTEM PERFORMANCE REPORT")
        report.append("="*80)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        # Overall stats
        stats = self._get_overall_stats()
        report.append("OVERALL STATISTICS:")
        report.append(f"  Total Recommendations: {stats['total_recommendations']}")
        report.append(f"  Evaluated: {stats['total_evaluated']}")
        report.append(f"  Win Rate: {stats['overall_win_rate']*100:.1f}%")
        report.append("")
        
        # Per-LLM stats
        report.append("PER-LLM PERFORMANCE:")
        for llm in ['chatgpt', 'gemini', 'claude', 'synthesis']:
            df = self.db.get_llm_performance(llm_source=llm)
            if len(df) > 0:
                evaluated = df[df['evaluated'] == 1]
                if len(evaluated) > 0:
                    wins = evaluated[evaluated['outcome'].isin(['WIN_TP1', 'WIN_TP2'])]
                    win_rate = len(wins) / len(evaluated) if len(evaluated) > 0 else 0.0
                    avg_pnl = evaluated['pnl_pips'].mean() if 'pnl_pips' in evaluated.columns else 0.0
                    
                    report.append(f"  {llm.upper()}:")
                    report.append(f"    Total: {len(df)} recommendations")
                    report.append(f"    Evaluated: {len(evaluated)}")
                    report.append(f"    Win Rate: {win_rate*100:.1f}%")
                    report.append(f"    Avg PnL: {avg_pnl:.1f} pips")
        
        report.append("")
        
        # Current weights
        weights = self.learning_engine.calculate_llm_weights()
        report.append("CURRENT LLM WEIGHTS:")
        for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            report.append(f"  {llm}: {weight*100:.1f}%")
        
        report.append("")
        report.append("="*80)
        
        return "\n".join(report)


def main():
    """Main training function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train RL System')
    parser.add_argument('--import-csv', type=str, help='Import recommendations from CSV file')
    parser.add_argument('--evaluate', action='store_true', help='Evaluate pending recommendations')
    parser.add_argument('--calculate-weights', action='store_true', help='Calculate and save weights')
    parser.add_argument('--report', action='store_true', help='Generate performance report')
    parser.add_argument('--all', action='store_true', help='Run all training steps')
    
    args = parser.parse_args()
    
    trainer = RLTrainingSystem()
    
    # If --all or --import-csv, import CSV first
    if args.all or args.import_csv:
        csv_path = args.import_csv or 'trade-alert-eval - Sheet1.csv'
        
        # Try multiple possible locations
        possible_paths = [
            csv_path,
            os.path.join(os.getcwd(), csv_path),
            os.path.join(os.path.expanduser('~'), 'Downloads', csv_path),
            os.path.join(os.path.expanduser('~'), 'Downloads', 'trade-alert-eval - Sheet1.csv'),
            'trade-alert-eval - Sheet1.csv'
        ]
        
        csv_found = None
        for path in possible_paths:
            if os.path.exists(path):
                csv_found = path
                break
        
        if csv_found:
            logger.info(f"📥 Importing recommendations from: {csv_found}")
            imported = trainer.import_csv_recommendations(csv_found)
            if imported > 0:
                logger.info(f"✅ Successfully imported {imported} recommendations")
            else:
                logger.warning("⚠️  No recommendations were imported. Check CSV format.")
        else:
            logger.error(f"❌ CSV file not found. Tried:")
            for path in possible_paths:
                logger.error(f"   - {path}")
            logger.error("Please provide full path with --import-csv")
    
    # Evaluate any remaining pending recommendations
    if args.all or args.evaluate:
        trainer.evaluate_pending_recommendations()
    
    # Calculate and save weights (IMPORTANT: Do this after import/evaluation)
    if args.all or args.calculate_weights:
        weights = trainer.calculate_and_save_weights()
        if weights:
            logger.info("")
            logger.info("🎯 Updated LLM Weights (will be used in next analysis):")
            for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"   {llm.upper()}: {weight*100:.1f}%")
    
    # Generate performance report
    if args.all or args.report:
        report = trainer.generate_performance_report()
        print("")
        print(report)
        print("")
        
        # Save to file
        report_file = f"rl_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        logger.info(f"✅ Report saved to: {report_file}")


if __name__ == '__main__':
    main()
