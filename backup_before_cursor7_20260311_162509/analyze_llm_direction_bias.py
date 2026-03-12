#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 4 Step 2: LLM Direction Bias Analysis

Analyzes all 5 LLMs (ChatGPT, Gemini, Claude, Deepseek, Synthesis) to identify
direction bias and accuracy issues.

Usage:
  python analyze_llm_direction_bias.py [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD]

Example:
  python analyze_llm_direction_bias.py --date-from 2026-01-15 --date-to 2026-02-22
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def get_database_path() -> str:
    """Get RL database path (local or Render)"""
    if os.path.exists('/var/data'):
        return '/var/data/trade_alerts_rl.db'
    else:
        data_dir = Path(__file__).parent / 'data'
        return str(data_dir / 'trade_alerts_rl.db')

def analyze_llm_accuracy(db_path: str, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> Dict:
    """
    Analyze accuracy of all 5 LLMs for direction prediction

    Returns:
    {
        'chatgpt': {
            'total_recs': 100,
            'correct_direction': 45,
            'accuracy': 0.45,
            'long_recommendations': 55,
            'short_recommendations': 45,
            'bias': 'BULLISH (55% LONG)'
        },
        ...
    }
    """
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return {}

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    results = {}
    llm_sources = ['chatgpt', 'gemini', 'claude', 'deepseek', 'synthesis']

    print("=" * 80)
    print("LLM DIRECTION BIAS ANALYSIS")
    print("=" * 80)
    print(f"\nDatabase: {db_path}")
    if date_from:
        print(f"Date Range: {date_from.date()} to {date_to.date()}")
    print()

    for llm in llm_sources:
        try:
            # Get all recommendations from this LLM
            if date_from and date_to:
                cursor.execute("""
                    SELECT id, pair, direction, outcome, timestamp
                    FROM recommendations
                    WHERE llm_source = ? AND timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp
                """, (llm, date_from.isoformat(), date_to.isoformat()))
            else:
                cursor.execute("""
                    SELECT id, pair, direction, outcome, timestamp
                    FROM recommendations
                    WHERE llm_source = ?
                    ORDER BY timestamp
                """, (llm,))

            recs = cursor.fetchall()

            if len(recs) == 0:
                print(f"\n⚠️  {llm.upper()}: No recommendations found")
                results[llm] = {'total_recs': 0, 'error': 'No data'}
                continue

            # Count directions
            long_count = sum(1 for r in recs if r['direction'].upper() in ['LONG', 'BUY'])
            short_count = sum(1 for r in recs if r['direction'].upper() in ['SHORT', 'SELL'])

            # Count wins/losses per direction
            long_wins = sum(1 for r in recs if r['direction'].upper() in ['LONG', 'BUY'] and r['outcome'] in ['WIN_TP1', 'WIN_TP2'])
            long_losses = sum(1 for r in recs if r['direction'].upper() in ['LONG', 'BUY'] and r['outcome'] == 'LOSS_SL')

            short_wins = sum(1 for r in recs if r['direction'].upper() in ['SHORT', 'SELL'] and r['outcome'] in ['WIN_TP1', 'WIN_TP2'])
            short_losses = sum(1 for r in recs if r['direction'].upper() in ['SHORT', 'SELL'] and r['outcome'] == 'LOSS_SL')

            # Calculate accuracy per direction
            long_accuracy = long_wins / (long_wins + long_losses) if (long_wins + long_losses) > 0 else 0
            short_accuracy = short_wins / (short_wins + short_losses) if (short_wins + short_losses) > 0 else 0
            total_accuracy = (long_wins + short_wins) / len(recs) if len(recs) > 0 else 0

            # Determine bias
            bias_pct = (long_count / len(recs)) * 100
            if bias_pct > 55:
                bias = f"BULLISH ({bias_pct:.0f}% LONG)"
            elif bias_pct < 45:
                bias = f"BEARISH ({100-bias_pct:.0f}% SHORT)"
            else:
                bias = f"NEUTRAL ({bias_pct:.0f}% LONG)"

            # Store results
            results[llm] = {
                'total_recs': len(recs),
                'long_count': long_count,
                'short_count': short_count,
                'long_wins': long_wins,
                'long_losses': long_losses,
                'short_wins': short_wins,
                'short_losses': short_losses,
                'long_accuracy': long_accuracy,
                'short_accuracy': short_accuracy,
                'total_accuracy': total_accuracy,
                'bias': bias,
                'recommendation': get_recommendation(llm, total_accuracy, long_accuracy, short_accuracy, bias_pct)
            }

            # Print results
            print(f"\n📊 {llm.upper()}")
            print(f"   Total Recommendations: {len(recs)}")
            print(f"   Direction Bias: {bias}")
            print(f"   LONG:  {long_wins}W {long_losses}L ({long_accuracy*100:.1f}% accuracy)")
            print(f"   SHORT: {short_wins}W {short_losses}L ({short_accuracy*100:.1f}% accuracy)")
            print(f"   Overall Accuracy: {total_accuracy*100:.1f}%")
            print(f"   🔧 Action: {results[llm]['recommendation']}")

        except Exception as e:
            print(f"\n❌ {llm.upper()}: Error - {e}")
            results[llm] = {'total_recs': 0, 'error': str(e)}

    conn.close()

    # Summary and actions
    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDED ACTIONS")
    print("=" * 80)

    broken_llms = []
    for llm, data in results.items():
        if 'total_recs' in data and data['total_recs'] > 0:
            if data['total_accuracy'] < 0.40:
                broken_llms.append((llm, data['total_accuracy']))

    if broken_llms:
        print("\n🔴 BROKEN LLMs (< 40% accuracy):")
        for llm, accuracy in sorted(broken_llms, key=lambda x: x[1]):
            print(f"   {llm.upper()}: {accuracy*100:.1f}% accuracy")
            print(f"   → RECOMMEND: Disable or reduce weight significantly")

    print("\n✅ NEXT STEPS:")
    print("   1. Disable broken LLMs (set weight to 0 or 0.05)")
    print("   2. Reduce weight of lower-accuracy LLMs")
    print("   3. Keep high-accuracy LLMs at normal weight")
    print("   4. Re-run backtest with adjusted weights")

    return results

def get_recommendation(llm: str, accuracy: float, long_acc: float, short_acc: float, bias_pct: float) -> str:
    """Get recommendation for LLM based on accuracy metrics"""
    if accuracy < 0.25:
        return "❌ DISABLE - Worse than random (25%)"
    elif accuracy < 0.35:
        return "🔴 DISABLE - Very poor accuracy"
    elif accuracy < 0.40:
        return "🟠 REDUCE WEIGHT - Below threshold"
    elif accuracy < 0.45:
        return "🟡 INVESTIGATE - Low accuracy"
    elif accuracy >= 0.50:
        return "✅ KEEP - Good accuracy"
    else:
        return "⚠️  MONITOR - Marginal accuracy"

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze LLM direction bias")
    parser.add_argument('--date-from', type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument('--date-to', type=str, help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    # Parse dates
    date_from = None
    date_to = None

    if args.date_from:
        try:
            date_from = datetime.strptime(args.date_from, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Invalid date format: {args.date_from}")
            return 1

    if args.date_to:
        try:
            date_to = datetime.strptime(args.date_to, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Invalid date format: {args.date_to}")
            return 1

    # Default to all data if not specified
    if not date_from:
        date_from = datetime(2026, 1, 1)
    if not date_to:
        date_to = datetime.utcnow()

    db_path = get_database_path()

    # Run analysis
    results = analyze_llm_accuracy(db_path, date_from, date_to)

    # Save results to file
    output_file = 'llm_direction_bias_analysis.json'
    with open(output_file, 'w') as f:
        # Convert datetime objects to strings for JSON serialization
        json_results = {}
        for llm, data in results.items():
            json_results[llm] = data
        json.dump(json_results, f, indent=2, default=str)

    print(f"\n💾 Results saved to {output_file}")

    return 0

if __name__ == '__main__':
    sys.exit(main())
