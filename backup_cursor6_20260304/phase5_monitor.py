#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 5: Demo Testing - Trade Monitoring System

Tracks all trades and filter rejections in real-time:
- Win rate by day
- Filter effectiveness (how many trades rejected by each filter)
- Reasons for rejections
- Comparison to baseline (15.5%)

Architecture:
- Monitors logs from Scalp-Engine and Trade-Alerts
- Extracts trades and rejections
- Stores in SQLite database
- Generates daily reports

Usage:
  # Start monitoring (runs continuously)
  python phase5_monitor.py

  # Generate report for specific date
  python phase5_monitor.py --report 2026-02-23

  # Show real-time stats
  python phase5_monitor.py --stats
"""

import os
import sys
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import time

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class Phase5Monitor:
    """Monitor Phase 5 demo testing"""

    def __init__(self):
        self.db_path = self._get_db_path()
        self._init_database()
        self.baseline_win_rate = 0.155  # 15.5% from Phase 3 analysis

    def _get_db_path(self) -> str:
        """Get Phase 5 database path"""
        if os.path.exists('/var/data'):
            return '/var/data/phase5_test.db'
        else:
            data_dir = Path(__file__).parent / 'data'
            data_dir.mkdir(parents=True, exist_ok=True)
            return str(data_dir / 'phase5_test.db')

    def _init_database(self):
        """Initialize Phase 5 tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                date TEXT NOT NULL,
                pair TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                outcome TEXT,
                pnl_pips REAL,
                confidence REAL,
                consensus_level REAL,
                source TEXT,
                phase4_filters_passed INTEGER DEFAULT 1,
                notes TEXT
            )
        """)

        # Rejections table (trades blocked by Phase 4 filters)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rejections (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                date TEXT NOT NULL,
                pair TEXT NOT NULL,
                direction TEXT NOT NULL,
                filter_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                confidence REAL,
                consensus_level REAL,
                llm_sources TEXT
            )
        """)

        # Daily metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_metrics (
                date TEXT PRIMARY KEY,
                total_trades INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                avg_pnl_pips REAL DEFAULT 0,
                confidence_rejects INTEGER DEFAULT 0,
                llm_accuracy_rejects INTEGER DEFAULT 0,
                jpy_entry_rejects INTEGER DEFAULT 0,
                jpy_direction_rejects INTEGER DEFAULT 0,
                market_regime_rejects INTEGER DEFAULT 0,
                other_rejects INTEGER DEFAULT 0,
                total_rejects INTEGER DEFAULT 0,
                phase4_filter_effectiveness REAL DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    def log_trade(self, trade_data: Dict) -> bool:
        """
        Log a completed trade to the database

        Args:
            trade_data: {
                'timestamp': '2026-02-23T10:30:00',
                'pair': 'EUR/USD',
                'direction': 'LONG',
                'entry_price': 1.0850,
                'stop_loss': 1.0800,
                'take_profit': 1.0900,
                'outcome': 'WIN_TP1' | 'LOSS_SL' | 'MISSED',
                'pnl_pips': 50.0,
                'confidence': 0.75,
                'consensus_level': 0.8,
                'source': 'LLM' | 'FISHER' | 'DMI_EMA',
                'phase4_filters_passed': True,
                'notes': 'Any additional notes'
            }
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            timestamp = trade_data.get('timestamp', datetime.utcnow().isoformat())
            date = timestamp.split('T')[0]

            cursor.execute("""
                INSERT INTO trades (
                    timestamp, date, pair, direction, entry_price, stop_loss,
                    take_profit, outcome, pnl_pips, confidence, consensus_level,
                    source, phase4_filters_passed, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                date,
                trade_data.get('pair', ''),
                trade_data.get('direction', '').upper(),
                trade_data.get('entry_price'),
                trade_data.get('stop_loss'),
                trade_data.get('take_profit'),
                trade_data.get('outcome', 'PENDING'),
                trade_data.get('pnl_pips'),
                trade_data.get('confidence'),
                trade_data.get('consensus_level'),
                trade_data.get('source', 'UNKNOWN'),
                1 if trade_data.get('phase4_filters_passed', True) else 0,
                trade_data.get('notes', '')
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Error logging trade: {e}")
            return False

    def log_rejection(self, rejection_data: Dict) -> bool:
        """
        Log a trade rejection (blocked by Phase 4 filter)

        Args:
            rejection_data: {
                'timestamp': '2026-02-23T10:30:00',
                'pair': 'EUR/USD',
                'direction': 'LONG',
                'filter_type': 'CONFIDENCE' | 'LLM_ACCURACY' | 'JPY_ENTRY' | 'JPY_DIRECTION' | 'MARKET_REGIME',
                'reason': 'Low consensus (40% < 50%)',
                'confidence': 0.35,
                'consensus_level': 0.4,
                'llm_sources': 'ChatGPT, Gemini'
            }
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            timestamp = rejection_data.get('timestamp', datetime.utcnow().isoformat())
            date = timestamp.split('T')[0]

            cursor.execute("""
                INSERT INTO rejections (
                    timestamp, date, pair, direction, filter_type, reason,
                    confidence, consensus_level, llm_sources
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                date,
                rejection_data.get('pair', ''),
                rejection_data.get('direction', '').upper(),
                rejection_data.get('filter_type', 'UNKNOWN'),
                rejection_data.get('reason', ''),
                rejection_data.get('confidence'),
                rejection_data.get('consensus_level'),
                rejection_data.get('llm_sources', '')
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Error logging rejection: {e}")
            return False

    def get_daily_metrics(self, date: str) -> Dict:
        """
        Get metrics for a specific date

        Args:
            date: 'YYYY-MM-DD'

        Returns:
            Metrics dictionary
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get trades for date
            cursor.execute("""
                SELECT outcome, pnl_pips FROM trades WHERE date = ?
            """, (date,))
            trades = cursor.fetchall()

            # Get rejections by type
            cursor.execute("""
                SELECT filter_type, COUNT(*) as count FROM rejections
                WHERE date = ?
                GROUP BY filter_type
            """, (date,))
            rejections = cursor.fetchall()

            conn.close()

            # Calculate metrics
            total_trades = len(trades)
            wins = sum(1 for t in trades if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])
            win_rate = wins / total_trades if total_trades > 0 else 0
            avg_pnl = sum(t['pnl_pips'] or 0 for t in trades) / total_trades if total_trades > 0 else 0

            # Rejection breakdown
            rejection_dict = {r['filter_type']: r['count'] for r in rejections}
            total_rejects = sum(r['count'] for r in rejections)

            # Filter effectiveness (% of opportunities that passed Phase 4)
            total_opportunities = total_trades + total_rejects
            pass_rate = total_trades / total_opportunities * 100 if total_opportunities > 0 else 0

            return {
                'date': date,
                'total_trades': total_trades,
                'wins': wins,
                'losses': total_trades - wins,
                'win_rate': win_rate,
                'avg_pnl_pips': avg_pnl,
                'rejections': {
                    'CONFIDENCE': rejection_dict.get('CONFIDENCE', 0),
                    'LLM_ACCURACY': rejection_dict.get('LLM_ACCURACY', 0),
                    'JPY_ENTRY': rejection_dict.get('JPY_ENTRY', 0),
                    'JPY_DIRECTION': rejection_dict.get('JPY_DIRECTION', 0),
                    'MARKET_REGIME': rejection_dict.get('MARKET_REGIME', 0),
                    'OTHER': rejection_dict.get('OTHER', 0),
                    'TOTAL': total_rejects,
                },
                'phase4_filter_pass_rate': pass_rate,
                'vs_baseline': (win_rate - self.baseline_win_rate) * 100,
            }

        except Exception as e:
            print(f"❌ Error getting daily metrics: {e}")
            return {}

    def get_cumulative_metrics(self, days: int = 7) -> Dict:
        """
        Get cumulative metrics for last N days

        Args:
            days: Number of days to include

        Returns:
            Cumulative metrics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get all trades in period
            date_from = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT outcome, pnl_pips FROM trades WHERE date >= ?
            """, (date_from,))
            trades = cursor.fetchall()

            # Get all rejections in period
            cursor.execute("""
                SELECT filter_type, COUNT(*) as count FROM rejections
                WHERE date >= ?
                GROUP BY filter_type
            """, (date_from,))
            rejections = cursor.fetchall()

            # Get daily breakdown
            cursor.execute("""
                SELECT date, COUNT(*) as count FROM trades WHERE date >= ?
                GROUP BY date ORDER BY date
            """, (date_from,))
            daily_counts = cursor.fetchall()

            conn.close()

            # Calculate metrics
            total_trades = len(trades)
            wins = sum(1 for t in trades if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])
            losses = sum(1 for t in trades if t['outcome'] == 'LOSS_SL')
            missed = total_trades - wins - losses
            win_rate = wins / total_trades if total_trades > 0 else 0
            total_pnl = sum(t['pnl_pips'] or 0 for t in trades)

            # Rejection breakdown
            rejection_dict = {r['filter_type']: r['count'] for r in rejections}
            total_rejects = sum(r['count'] for r in rejections)

            # Filter effectiveness
            total_opportunities = total_trades + total_rejects
            pass_rate = total_trades / total_opportunities * 100 if total_opportunities > 0 else 0

            # Days of trading
            days_with_trades = len([d for d in daily_counts if d['count'] > 0])

            return {
                'period_days': days,
                'trading_days': days_with_trades,
                'total_trades': total_trades,
                'wins': wins,
                'losses': losses,
                'missed': missed,
                'win_rate': win_rate,
                'total_pnl_pips': total_pnl,
                'avg_pnl_pips': total_pnl / total_trades if total_trades > 0 else 0,
                'rejections': {
                    'CONFIDENCE': rejection_dict.get('CONFIDENCE', 0),
                    'LLM_ACCURACY': rejection_dict.get('LLM_ACCURACY', 0),
                    'JPY_ENTRY': rejection_dict.get('JPY_ENTRY', 0),
                    'JPY_DIRECTION': rejection_dict.get('JPY_DIRECTION', 0),
                    'MARKET_REGIME': rejection_dict.get('MARKET_REGIME', 0),
                    'OTHER': rejection_dict.get('OTHER', 0),
                    'TOTAL': total_rejects,
                },
                'phase4_filter_pass_rate': pass_rate,
                'vs_baseline': (win_rate - self.baseline_win_rate) * 100,
                'baseline_win_rate': self.baseline_win_rate,
            }

        except Exception as e:
            print(f"❌ Error getting cumulative metrics: {e}")
            return {}

    def print_daily_report(self, date: str = None):
        """Print daily report for a specific date"""
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        metrics = self.get_daily_metrics(date)

        if not metrics:
            print(f"❌ No data for {date}")
            return

        print("\n" + "=" * 80)
        print(f"PHASE 5 DAILY REPORT - {date}")
        print("=" * 80)

        print(f"\nTrades:")
        print(f"  Total: {metrics['total_trades']}")
        print(f"  Wins: {metrics['wins']}")
        print(f"  Losses: {metrics['losses']}")
        print(f"  Win Rate: {metrics['win_rate']*100:.1f}%")
        print(f"  Avg P&L: {metrics['avg_pnl_pips']:.1f} pips")

        print(f"\nPhase 4 Filter Effectiveness:")
        print(f"  Trades Executed: {metrics['total_trades']}")
        print(f"  Total Rejections: {metrics['rejections']['TOTAL']}")
        print(f"  Pass Rate: {metrics['phase4_filter_pass_rate']:.1f}%")
        print(f"  Breakdown:")
        for filter_type, count in metrics['rejections'].items():
            if filter_type != 'TOTAL' and count > 0:
                print(f"    - {filter_type}: {count}")

        print(f"\nComparison to Baseline:")
        baseline_pct = self.baseline_win_rate * 100
        current_pct = metrics['win_rate'] * 100
        improvement = metrics['vs_baseline']
        status = "✅ BETTER" if improvement > 0 else "⚠️  WORSE" if improvement < 0 else "➡️  SAME"
        print(f"  Baseline Win Rate: {baseline_pct:.1f}%")
        print(f"  Current Win Rate: {current_pct:.1f}%")
        print(f"  Improvement: {improvement:+.1f}% {status}")

    def print_cumulative_report(self, days: int = 7):
        """Print cumulative report for last N days"""
        metrics = self.get_cumulative_metrics(days)

        if not metrics.get('total_trades', 0) == 0:
            print(f"⚠️  No trades recorded yet")
            return

        print("\n" + "=" * 80)
        print(f"PHASE 5 CUMULATIVE REPORT - Last {days} days")
        print("=" * 80)

        print(f"\nTrading Activity:")
        print(f"  Trading Days: {metrics['trading_days']}/{metrics['period_days']}")
        print(f"  Total Trades: {metrics['total_trades']}")
        print(f"  Wins: {metrics['wins']}")
        print(f"  Losses: {metrics['losses']}")
        print(f"  Missed: {metrics['missed']}")
        print(f"  Win Rate: {metrics['win_rate']*100:.1f}%")
        print(f"  Total P&L: {metrics['total_pnl_pips']:+.1f} pips")
        print(f"  Avg P&L/trade: {metrics['avg_pnl_pips']:.1f} pips")

        print(f"\nPhase 4 Filter Effectiveness:")
        print(f"  Total Opportunities: {metrics['total_trades'] + metrics['rejections']['TOTAL']}")
        print(f"  Executed: {metrics['total_trades']}")
        print(f"  Rejected: {metrics['rejections']['TOTAL']}")
        print(f"  Pass Rate: {metrics['phase4_filter_pass_rate']:.1f}%")
        print(f"  Breakdown:")
        for filter_type, count in metrics['rejections'].items():
            if filter_type != 'TOTAL' and count > 0:
                print(f"    - {filter_type}: {count}")

        print(f"\nComparison to Baseline:")
        baseline_pct = self.baseline_win_rate * 100
        current_pct = metrics['win_rate'] * 100
        improvement = metrics['vs_baseline']
        status = "✅ BETTER" if improvement > 0 else "⚠️  WORSE" if improvement < 0 else "➡️  SAME"
        print(f"  Baseline Win Rate: {baseline_pct:.1f}%")
        print(f"  Current Win Rate: {current_pct:.1f}%")
        print(f"  Improvement: {improvement:+.1f}% {status}")

        if current_pct >= 25:
            print(f"\n✅ TARGET ACHIEVED: {current_pct:.1f}% >= 25% (ready for live trading)")
        elif current_pct >= 20:
            print(f"\n🟡 APPROACHING TARGET: {current_pct:.1f}% (need more data)")
        else:
            print(f"\n⚠️  BELOW TARGET: {current_pct:.1f}% (continue demo testing)")

    def export_to_json(self, output_file: str = 'phase5_metrics.json'):
        """Export metrics to JSON"""
        try:
            metrics = self.get_cumulative_metrics(days=30)
            with open(output_file, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
            print(f"✅ Metrics exported to {output_file}")
            return True
        except Exception as e:
            print(f"❌ Error exporting metrics: {e}")
            return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Phase 5 monitoring system")
    parser.add_argument('--report', type=str, help="Show daily report for date (YYYY-MM-DD)")
    parser.add_argument('--cumulative', type=int, default=7, help="Show cumulative report for N days")
    parser.add_argument('--export', type=str, help="Export metrics to JSON file")
    args = parser.parse_args()

    monitor = Phase5Monitor()

    if args.report:
        monitor.print_daily_report(args.report)
    elif args.export:
        monitor.export_to_json(args.export)
    else:
        monitor.print_cumulative_report(args.cumulative)

    return 0


if __name__ == '__main__':
    sys.exit(main())
