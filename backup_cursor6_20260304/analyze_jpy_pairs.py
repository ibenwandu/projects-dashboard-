#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 4 Step 3: JPY Pair Optimization - Option C (Fix Entry Logic)

Analyzes JPY pair trades to identify root cause of failures:
- Entry price accuracy
- Volatility handling
- Spread issues
- Direction bias on JPY pairs

Usage:
  python analyze_jpy_pairs.py
"""

import os
import sys
import sqlite3
from datetime import datetime
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

def analyze_jpy_pairs(db_path: str) -> Dict:
    """
    Analyze all JPY pair trades to identify root causes of failures

    Returns:
    {
        'USD/JPY': {
            'total_trades': 56,
            'win_rate': 0.214,
            'avg_entry_distance': 0.08,
            'avg_sl_distance_pips': 45,
            'recommendation': 'Keep - profitable'
        },
        ...
    }
    """
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return {}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 80)
    print("JPY PAIR OPTIMIZATION ANALYSIS - OPTION C (Fix Entry Logic)")
    print("=" * 80)
    print(f"\nDatabase: {db_path}\n")

    # Get all JPY pair trades
    cursor.execute("""
        SELECT id, pair, direction, entry_price, stop_loss, take_profit_1, take_profit_2,
               outcome, timestamp, source_file
        FROM recommendations
        WHERE pair LIKE '%JPY%'
        ORDER BY timestamp
    """)

    all_trades = cursor.fetchall()

    if len(all_trades) == 0:
        print("⚠️  No JPY pair trades found in database")
        return {}

    # Group by pair
    pairs = {}
    for trade in all_trades:
        pair = trade['pair']
        if pair not in pairs:
            pairs[pair] = []
        pairs[pair].append(trade)

    results = {}

    print("📊 JPY PAIR ANALYSIS:\n")

    for pair in sorted(pairs.keys()):
        trades = pairs[pair]

        # Calculate metrics
        total = len(trades)
        wins = sum(1 for t in trades if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])
        losses = sum(1 for t in trades if t['outcome'] == 'LOSS_SL')
        missed = sum(1 for t in trades if t['outcome'] == 'MISSED')
        pending = sum(1 for t in trades if t['outcome'] is None)

        win_rate = wins / total if total > 0 else 0

        # Analyze entry prices (check if they match market at time)
        # Note: For now, we'll note this as a todo since we need OANDA data
        entry_distances = []
        for trade in trades:
            if trade['entry_price']:
                # This would require fetching actual market price at trade time
                # For now, just flag it
                entry_distances.append(trade['entry_price'])

        # Analyze SL distances
        sl_distances_pips = []
        for trade in trades:
            if trade['entry_price'] and trade['stop_loss']:
                if 'JPY' in pair:
                    pip_size = 0.01  # JPY pip size
                else:
                    pip_size = 0.0001
                distance = abs(trade['entry_price'] - trade['stop_loss']) / pip_size
                sl_distances_pips.append(distance)

        avg_sl_distance = sum(sl_distances_pips) / len(sl_distances_pips) if sl_distances_pips else 0

        # Determine recommendations
        if win_rate > 0.25:
            recommendation = "✅ KEEP - Acceptable accuracy"
            action = "Optimize entry logic"
        elif win_rate > 0.15:
            recommendation = "🟡 NEEDS WORK - Below 25%"
            action = "Investigate entry prices and volatility"
        else:
            recommendation = "🔴 CRITICAL - Below 15%"
            action = "Fix or disable - too many losses"

        results[pair] = {
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'missed': missed,
            'pending': pending,
            'win_rate': win_rate,
            'avg_sl_distance_pips': avg_sl_distance,
            'recommendation': recommendation,
            'action': action
        }

        # Print results
        print(f"📈 {pair}")
        print(f"   Total Trades: {total}")
        print(f"   Win Rate: {win_rate*100:.1f}% ({wins}W {losses}L {missed}M)")
        print(f"   Avg SL Distance: {avg_sl_distance:.1f} pips")
        print(f"   {recommendation}")
        print(f"   → {action}")
        print()

    # Summary
    print("=" * 80)
    print("ROOT CAUSE INVESTIGATION")
    print("=" * 80)

    print("\n🔍 POTENTIAL ISSUES TO INVESTIGATE:\n")

    print("1. ENTRY PRICE ACCURACY")
    print("   Question: Are LLM entry prices realistic vs actual market?")
    print("   How to check: Compare LLM entry vs market price at recommendation time")
    print("   Fix if needed: Tighten entry tolerance (reject if >2% deviation)")

    print("\n2. VOLATILITY HANDLING")
    print("   Question: Are JPY pairs being treated like normal pairs?")
    print("   How to check: Compare win rates vs other pairs, check SL distances")
    print("   Fix if needed: Adjust position sizing multiplier for JPY")
    print("   Current multipliers to consider:")
    print("      EUR/JPY: 0.8x (reduce size 20% for higher volatility)")
    print("      GBP/JPY: 0.6x (reduce size 40% for extreme volatility)")
    print("      USD/JPY: 1.0x (keep normal)")

    print("\n3. SPREAD ADJUSTMENT")
    print("   Question: Are stops wide enough to account for wider spreads?")
    print("   How to check: Check if trades are getting stopped out at entry")
    print("   Fix if needed: Add 5-10 pip padding for JPY pairs")

    print("\n4. DIRECTION BIAS ON JPY PAIRS")
    print("   Question: Are certain JPY pairs consistently SHORT or LONG biased?")
    print("   How to check: See below for per-pair direction breakdown")
    print("   Fix if needed: Add direction-specific rules (e.g., don't short GBP/JPY)")

    # Direction breakdown per pair
    print("\n" + "=" * 80)
    print("DIRECTION BREAKDOWN PER PAIR")
    print("=" * 80)

    for pair in sorted(pairs.keys()):
        trades = pairs[pair]
        long_trades = [t for t in trades if t['direction'].upper() in ['LONG', 'BUY']]
        short_trades = [t for t in trades if t['direction'].upper() in ['SHORT', 'SELL']]

        long_wins = sum(1 for t in long_trades if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])
        short_wins = sum(1 for t in short_trades if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])

        long_wr = long_wins / len(long_trades) * 100 if long_trades else 0
        short_wr = short_wins / len(short_trades) * 100 if short_trades else 0

        print(f"\n{pair}:")
        print(f"   LONG:  {len(long_trades):2d} trades, {long_wr:5.1f}% win rate")
        print(f"   SHORT: {len(short_trades):2d} trades, {short_wr:5.1f}% win rate")

        if long_wr > 0 and short_wr == 0:
            print(f"   ⚠️  SHORT side has 0% win rate - avoid SHORT on {pair}")
        elif short_wr > 0 and long_wr == 0:
            print(f"   ⚠️  LONG side has 0% win rate - avoid LONG on {pair}")

    conn.close()

    return results

def main():
    db_path = get_database_path()
    results = analyze_jpy_pairs(db_path)

    # Save results
    output_file = 'jpy_pair_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n💾 Results saved to {output_file}")

    print("\n" + "=" * 80)
    print("NEXT STEPS FOR PHASE 4 STEP 3")
    print("=" * 80)
    print("""
1. Check which JPY pairs have 0% win rate on one direction
   → Add rules to disable that direction if problematic

2. For pairs with low overall win rate:
   → Tighten entry price tolerance
   → Reduce position size (0.6x - 0.8x multiplier)
   → Widen stops by 5-10 pips

3. For pairs with good win rate (USD/JPY):
   → Keep and optimize
   → Use as baseline for fixing others

4. Consider disabling worst performers entirely if unfixable
   → But try Option C fixes first (we're not giving up!)
    """)

    return 0

if __name__ == '__main__':
    sys.exit(main())
