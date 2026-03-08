#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 4 Step 4: Backtest Validation

Simulates Phase 4 improvements on demo account history to measure impact:
1. Market Regime Detection (Step 1)
2. Direction Bias Fixes (Step 2)
3. JPY Pair Optimization (Step 3)

Outputs:
- Win rate before/after each filter
- Impact metrics (trades filtered, win rate improvement)
- Recommendations for deployment

Usage:
  python backtest_phase4_improvements.py [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD]

Example:
  python backtest_phase4_improvements.py --date-from 2026-01-15 --date-to 2026-02-22
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


def analyze_phase4_filters(db_path: str, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> Dict:
    """
    Simulate Phase 4 filters on historical data and measure impact

    Returns:
    {
        'baseline': {'total_trades': 419, 'wins': 65, 'win_rate': 0.155},
        'after_market_regime': {'filtered': 42, 'remaining': 377, 'win_rate': 0.168},
        'after_confidence': {'filtered': 23, 'remaining': 354, 'win_rate': 0.172},
        'after_jpy_rules': {'filtered': 18, 'remaining': 336, 'win_rate': 0.179},
        'impact_summary': {...}
    }
    """
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return {}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 80)
    print("PHASE 4 BACKTEST VALIDATION")
    print("=" * 80)
    print(f"\nDatabase: {db_path}")
    if date_from:
        print(f"Date Range: {date_from.date()} to {date_to.date()}")
    print()

    # Get all trades
    if date_from and date_to:
        cursor.execute("""
            SELECT id, pair, direction, entry_price, stop_loss, take_profit_1, take_profit_2,
                   outcome, timestamp, confidence, llm_source
            FROM recommendations
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        """, (date_from.isoformat(), date_to.isoformat()))
    else:
        cursor.execute("""
            SELECT id, pair, direction, entry_price, stop_loss, take_profit_1, take_profit_2,
                   outcome, timestamp, confidence, llm_source
            FROM recommendations
            ORDER BY timestamp
        """)

    all_trades = cursor.fetchall()

    if len(all_trades) == 0:
        print("⚠️  No trades found in database")
        return {}

    print(f"📊 Total trades in database: {len(all_trades)}\n")

    # Baseline metrics
    baseline_wins = sum(1 for t in all_trades if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])
    baseline_wr = baseline_wins / len(all_trades) if all_trades else 0

    print("=" * 80)
    print("BASELINE METRICS (No Filters)")
    print("=" * 80)
    print(f"Total Trades: {len(all_trades)}")
    print(f"Wins: {baseline_wins}")
    print(f"Win Rate: {baseline_wr*100:.1f}%\n")

    results = {
        'baseline': {
            'total_trades': len(all_trades),
            'wins': baseline_wins,
            'win_rate': baseline_wr,
        },
        'filters': {}
    }

    # Track trades through each filter
    remaining_trades = list(all_trades)
    cumulative_filtered = 0

    # PHASE 4 STEP 1: Market Regime Filter
    print("=" * 80)
    print("PHASE 4 STEP 1: Market Regime Detection")
    print("=" * 80)
    print("Filtering: Skip SHORT in BULLISH trend, skip LONG in BEARISH trend")
    print()

    # For backtest, assume trades have regime info in market_state
    # If not available, we can estimate based on series of price moves
    regime_filtered = 0
    regime_filter_results = []

    for trade in remaining_trades:
        # Without market_state data in DB, skip this filter for now
        # In real system, market_state would be captured with each trade
        # For now, log that this would require market_state integration
        pass

    print("⚠️  Market regime data not captured in RL database - cannot backtest")
    print("   (Would require market_state.json to be logged with each trade)")
    print()

    remaining_regime_filtered = remaining_trades  # No filtering in backtest
    regime_wins = sum(1 for t in remaining_regime_filtered if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])
    regime_wr = regime_wins / len(remaining_regime_filtered) if remaining_regime_filtered else 0

    results['filters']['market_regime'] = {
        'filtered': regime_filtered,
        'remaining': len(remaining_regime_filtered),
        'wins': regime_wins,
        'win_rate': regime_wr,
        'note': 'Requires market_state logging'
    }

    print(f"Trades Filtered: {regime_filtered}")
    print(f"Remaining: {len(remaining_regime_filtered)}")
    print(f"Win Rate: {regime_wr*100:.1f}%")
    print(f"Impact: {(regime_wr - baseline_wr)*100:+.1f}%\n")

    # PHASE 4 STEP 2: Direction Bias - Confidence Filter
    print("=" * 80)
    print("PHASE 4 STEP 2: Direction Bias - Confidence Filter")
    print("=" * 80)
    print("Filtering: Reject if consensus < 50% OR confidence < 40%")
    print()

    confidence_filtered = 0
    for trade in remaining_regime_filtered:
        # Try to parse confidence as float, default to 0.5 if invalid
        try:
            confidence = float(trade.get('confidence') or 0.5)
        except (ValueError, TypeError):
            confidence = 0.5

        # Apply confidence filter (require minimum 40% confidence)
        if confidence < 0.4:
            confidence_filtered += 1

    remaining_confidence_filtered = []
    for t in remaining_regime_filtered:
        try:
            confidence = float(t.get('confidence') or 0.5)
        except (ValueError, TypeError):
            confidence = 0.5

        if confidence >= 0.4:
            remaining_confidence_filtered.append(t)

    confidence_wins = sum(1 for t in remaining_confidence_filtered if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])
    confidence_wr = confidence_wins / len(remaining_confidence_filtered) if remaining_confidence_filtered else 0

    results['filters']['confidence'] = {
        'filtered': confidence_filtered,
        'remaining': len(remaining_confidence_filtered),
        'wins': confidence_wins,
        'win_rate': confidence_wr,
    }

    print(f"Trades Filtered: {confidence_filtered}")
    print(f"Remaining: {len(remaining_confidence_filtered)}")
    print(f"Win Rate: {confidence_wr*100:.1f}%")
    print(f"Impact: {(confidence_wr - baseline_wr)*100:+.1f}%\n")

    # PHASE 4 STEP 3: JPY Pair Direction Rules
    print("=" * 80)
    print("PHASE 4 STEP 3: JPY Pair Optimization")
    print("=" * 80)
    print("Filtering: Reject JPY pairs with 0% win rate on that direction")
    print()

    # Analyze JPY pair performance
    jpy_pairs = {}
    for trade in remaining_confidence_filtered:
        pair = trade['pair'].upper()
        if 'JPY' in pair:
            direction = trade['direction'].upper()
            key = (pair, direction)

            if key not in jpy_pairs:
                jpy_pairs[key] = {'total': 0, 'wins': 0}

            jpy_pairs[key]['total'] += 1
            if trade['outcome'] in ['WIN_TP1', 'WIN_TP2']:
                jpy_pairs[key]['wins'] += 1

    # Identify JPY pairs with 0% win rate
    jpy_block_keys = []
    for key, metrics in jpy_pairs.items():
        pair, direction = key
        win_rate = metrics['wins'] / metrics['total'] if metrics['total'] > 0 else 0

        if metrics['total'] >= 3 and win_rate == 0:
            jpy_block_keys.append(key)
            print(f"   Blocking {pair} {direction}: 0% win rate ({metrics['wins']}W {metrics['total']-metrics['wins']}L)")
        elif metrics['total'] >= 5 and win_rate < 0.15:
            jpy_block_keys.append(key)
            print(f"   Blocking {pair} {direction}: {win_rate:.0%} win rate < 15% ({metrics['wins']}W {metrics['total']-metrics['wins']}L)")

    jpy_filtered = 0
    for trade in remaining_confidence_filtered:
        pair = trade['pair'].upper()
        direction = trade['direction'].upper()
        key = (pair, direction)

        if 'JPY' in pair and key in jpy_block_keys:
            jpy_filtered += 1

    remaining_jpy_filtered = [t for t in remaining_confidence_filtered
                             if not ('JPY' in t['pair'].upper() and
                                    (t['pair'].upper(), t['direction'].upper()) in jpy_block_keys)]

    jpy_wins = sum(1 for t in remaining_jpy_filtered if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])
    jpy_wr = jpy_wins / len(remaining_jpy_filtered) if remaining_jpy_filtered else 0

    results['filters']['jpy_rules'] = {
        'filtered': jpy_filtered,
        'remaining': len(remaining_jpy_filtered),
        'wins': jpy_wins,
        'win_rate': jpy_wr,
        'jpy_pairs_blocked': len(jpy_block_keys)
    }

    print(f"\nTrades Filtered: {jpy_filtered}")
    print(f"JPY pair/direction combos blocked: {len(jpy_block_keys)}")
    print(f"Remaining: {len(remaining_jpy_filtered)}")
    print(f"Win Rate: {jpy_wr*100:.1f}%")
    print(f"Impact: {(jpy_wr - baseline_wr)*100:+.1f}%\n")

    # Summary
    print("=" * 80)
    print("PHASE 4 BACKTEST SUMMARY")
    print("=" * 80)

    total_filtered = confidence_filtered + jpy_filtered
    total_removed_trades = len(all_trades) - len(remaining_jpy_filtered)
    final_wins = jpy_wins
    final_wr = jpy_wr

    print(f"\nBaseline (No Filters):")
    print(f"  Total Trades: {len(all_trades)}")
    print(f"  Wins: {baseline_wins}")
    print(f"  Win Rate: {baseline_wr*100:.1f}%\n")

    print(f"After Phase 4 Filters:")
    print(f"  Total Trades: {len(remaining_jpy_filtered)}")
    print(f"  Wins: {final_wins}")
    print(f"  Win Rate: {final_wr*100:.1f}%\n")

    print(f"Overall Impact:")
    print(f"  Trades Removed: {total_removed_trades} ({total_removed_trades/len(all_trades)*100:.1f}%)")
    print(f"  Win Rate Improvement: {(final_wr - baseline_wr)*100:+.1f} percentage points")
    print(f"  New Win Rate Target: {final_wr*100:.1f}% (target: 25-30%)")

    if final_wr >= 0.25:
        print(f"\n✅ SUCCESS: Achieved target win rate of 25%+")
    elif final_wr >= 0.20:
        print(f"\n🟡 PARTIAL: Achieved {final_wr*100:.1f}% (need more work for 25%+)")
    else:
        print(f"\n⚠️  BELOW TARGET: {final_wr*100:.1f}% (need additional filters)")

    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    if final_wr >= 0.25:
        print("\n✅ DEPLOY PHASE 4: Win rate target achieved!")
        print("   1. All Phase 4 filters ready for production")
        print("   2. Run 5-7 days of demo testing")
        print("   3. Monitor trade quality and filter effectiveness")
    elif final_wr >= 0.20:
        print("\n🟡 DEPLOY WITH MONITORING:")
        print("   1. Deploy Phase 4 to demo")
        print("   2. Monitor for additional improvement opportunities")
        print("   3. Consider additional LLM reweighting")
        print("   4. Review trades filtered to ensure no false positives")
    else:
        print("\n⚠️  ADDITIONAL WORK NEEDED:")
        print("   1. Review backtest for filter false positives")
        print("   2. Consider tighter LLM accuracy thresholds")
        print("   3. Evaluate market regime integration")
        print("   4. Check JPY pair analysis for additional patterns")

    conn.close()

    results['impact_summary'] = {
        'baseline_win_rate': baseline_wr,
        'final_win_rate': final_wr,
        'win_rate_improvement': final_wr - baseline_wr,
        'total_trades_removed': total_removed_trades,
        'total_trades_remaining': len(remaining_jpy_filtered),
        'recommendation': 'DEPLOY' if final_wr >= 0.25 else ('MONITOR' if final_wr >= 0.20 else 'REWORK')
    }

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Backtest Phase 4 improvements")
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
        date_to = datetime.now()

    db_path = get_database_path()

    # Run backtest
    results = analyze_phase4_filters(db_path, date_from, date_to)

    # Save results to file
    output_file = 'phase4_backtest_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n💾 Results saved to {output_file}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
