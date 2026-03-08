#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 5: Daily Report Generator

Generates comprehensive daily reports from Phase 5 monitoring data.

Reports include:
- Trading performance (win rate, P&L, trades executed)
- Filter effectiveness (how many trades rejected by each filter)
- Detailed trade analysis
- Comparison to baseline and daily progress tracking
- Recommendations for adjustments

Usage:
  # Generate report for today
  python phase5_daily_report.py

  # Generate report for specific date
  python phase5_daily_report.py --date 2026-02-23

  # Generate report with detailed trade list
  python phase5_daily_report.py --detailed

  # Generate HTML report for email
  python phase5_daily_report.py --html phase5_report.html
"""

import os
import sys
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class Phase5ReportGenerator:
    """Generate Phase 5 test reports"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            if os.path.exists('/var/data'):
                db_path = '/var/data/phase5_test.db'
            else:
                db_path = str(Path(__file__).parent / 'data' / 'phase5_test.db')

        self.db_path = db_path
        self.baseline_win_rate = 0.155  # 15.5%
        self.target_win_rate = 0.25  # 25%

    def _get_trades_for_date(self, date: str) -> List[Dict]:
        """Get all trades for a specific date"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM trades WHERE date = ? ORDER BY timestamp
            """, (date,))

            trades = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return trades
        except Exception as e:
            print(f"❌ Error fetching trades: {e}")
            return []

    def _get_rejections_for_date(self, date: str) -> List[Dict]:
        """Get all rejections for a specific date"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM rejections WHERE date = ? ORDER BY timestamp
            """, (date,))

            rejections = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rejections
        except Exception as e:
            print(f"❌ Error fetching rejections: {e}")
            return []

    def generate_text_report(self, date: str = None, detailed: bool = False) -> str:
        """Generate a text report"""
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        trades = self._get_trades_for_date(date)
        rejections = self._get_rejections_for_date(date)

        # Calculate metrics
        total_trades = len(trades)
        wins = sum(1 for t in trades if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])
        losses = sum(1 for t in trades if t['outcome'] == 'LOSS_SL')
        missed = total_trades - wins - losses
        win_rate = wins / total_trades if total_trades > 0 else 0
        avg_pnl = sum(t['pnl_pips'] or 0 for t in trades) / total_trades if total_trades > 0 else 0

        # Rejection breakdown
        rejection_summary = {}
        for r in rejections:
            filter_type = r['filter_type']
            if filter_type not in rejection_summary:
                rejection_summary[filter_type] = 0
            rejection_summary[filter_type] += 1

        total_rejections = len(rejections)
        total_opportunities = total_trades + total_rejections
        pass_rate = total_trades / total_opportunities * 100 if total_opportunities > 0 else 0

        # Build report
        report = []
        report.append("=" * 100)
        report.append(f"PHASE 5 DAILY REPORT - {date}")
        report.append("=" * 100)

        report.append("\nTRADING PERFORMANCE")
        report.append("-" * 100)
        report.append(f"  Total Trades:      {total_trades}")
        report.append(f"  Wins:              {wins} ({win_rate*100:5.1f}%)")
        report.append(f"  Losses:            {losses}")
        report.append(f"  Missed/Pending:    {missed}")
        report.append(f"  Avg P&L:           {avg_pnl:+.1f} pips")
        report.append(f"  Total P&L:         {sum(t['pnl_pips'] or 0 for t in trades):+.1f} pips")

        report.append("\nCOMPARISON TO BASELINE (15.5%)")
        report.append("-" * 100)
        improvement = (win_rate - self.baseline_win_rate) * 100
        if improvement > 0:
            status = "✅ BETTER"
        elif improvement < 0:
            status = "⚠️  WORSE"
        else:
            status = "➡️  SAME"
        report.append(f"  Baseline Win Rate: {self.baseline_win_rate*100:.1f}%")
        report.append(f"  Current Win Rate:  {win_rate*100:.1f}%")
        report.append(f"  Improvement:       {improvement:+.1f}% {status}")

        if win_rate >= self.target_win_rate:
            report.append(f"\n  ✅ TARGET ACHIEVED: {win_rate*100:.1f}% >= 25%")
        else:
            report.append(f"\n  ⏳ PROGRESS: {win_rate*100:.1f}% towards 25% target")

        report.append("\nPHASE 4 FILTER EFFECTIVENESS")
        report.append("-" * 100)
        report.append(f"  Total Opportunities:  {total_opportunities}")
        report.append(f"  Trades Executed:      {total_trades}")
        report.append(f"  Trades Rejected:      {total_rejections}")
        report.append(f"  Pass Rate:            {pass_rate:.1f}%")
        report.append("\n  Rejections by Filter:")
        for filter_type in sorted(rejection_summary.keys()):
            count = rejection_summary[filter_type]
            pct = count / total_rejections * 100 if total_rejections > 0 else 0
            report.append(f"    - {filter_type:20s}: {count:3d} ({pct:5.1f}%)")

        if detailed and total_trades > 0:
            report.append("\nDETAILED TRADES")
            report.append("-" * 100)
            report.append(f"{'Time':<20} {'Pair':<10} {'Dir':<6} {'Entry':<10} {'SL':<10} {'TP':<10} {'Outcome':<15} {'P&L':<10}")
            report.append("-" * 100)

            for trade in trades:
                time_str = trade['timestamp'].split('T')[1][:8] if trade['timestamp'] else 'N/A'
                pair = trade['pair']
                direction = trade['direction'][:3].upper()
                entry = f"{trade['entry_price']:.5f}" if trade['entry_price'] else 'N/A'
                sl = f"{trade['stop_loss']:.5f}" if trade['stop_loss'] else 'N/A'
                tp = f"{trade['take_profit']:.5f}" if trade['take_profit'] else 'N/A'
                outcome = trade['outcome'] or 'PENDING'
                pnl = f"{trade['pnl_pips']:+.1f}" if trade['pnl_pips'] is not None else 'N/A'

                report.append(f"{time_str:<20} {pair:<10} {direction:<6} {entry:<10} {sl:<10} {tp:<10} {outcome:<15} {pnl:<10}")

        if detailed and total_rejections > 0:
            report.append("\nDETAILED REJECTIONS")
            report.append("-" * 100)
            report.append(f"{'Time':<20} {'Pair':<10} {'Dir':<6} {'Filter':<20} {'Reason':<50}")
            report.append("-" * 100)

            for rejection in rejections:
                time_str = rejection['timestamp'].split('T')[1][:8] if rejection['timestamp'] else 'N/A'
                pair = rejection['pair']
                direction = rejection['direction'][:3].upper()
                filter_type = rejection['filter_type']
                reason = rejection['reason'][:50]

                report.append(f"{time_str:<20} {pair:<10} {direction:<6} {filter_type:<20} {reason:<50}")

        report.append("\n" + "=" * 100)

        return "\n".join(report)

    def generate_html_report(self, date: str = None, output_file: str = 'phase5_report.html'):
        """Generate an HTML report"""
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        trades = self._get_trades_for_date(date)
        rejections = self._get_rejections_for_date(date)

        # Calculate metrics
        total_trades = len(trades)
        wins = sum(1 for t in trades if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])
        losses = sum(1 for t in trades if t['outcome'] == 'LOSS_SL')
        missed = total_trades - wins - losses
        win_rate = wins / total_trades if total_trades > 0 else 0
        avg_pnl = sum(t['pnl_pips'] or 0 for t in trades) / total_trades if total_trades > 0 else 0

        # Rejection breakdown
        rejection_summary = {}
        for r in rejections:
            filter_type = r['filter_type']
            if filter_type not in rejection_summary:
                rejection_summary[filter_type] = 0
            rejection_summary[filter_type] += 1

        total_rejections = len(rejections)
        total_opportunities = total_trades + total_rejections
        pass_rate = total_trades / total_opportunities * 100 if total_opportunities > 0 else 0

        improvement = (win_rate - self.baseline_win_rate) * 100
        status_color = "green" if improvement > 0 else ("red" if improvement < 0 else "gray")

        # Build HTML
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html>")
        html.append("<head>")
        html.append(f"  <title>Phase 5 Report - {date}</title>")
        html.append("  <style>")
        html.append("    body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }")
        html.append("    h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }")
        html.append("    h2 { color: #555; margin-top: 30px; border-bottom: 1px solid #ddd; }")
        html.append("    .metric { margin: 10px 0; padding: 10px; background-color: white; border-radius: 5px; }")
        html.append("    .metric-label { font-weight: bold; color: #666; }")
        html.append("    .metric-value { font-size: 1.2em; color: #007bff; }")
        html.append("    .good { color: green; font-weight: bold; }")
        html.append("    .bad { color: red; font-weight: bold; }")
        html.append("    .neutral { color: gray; }")
        html.append("    table { width: 100%; border-collapse: collapse; margin: 10px 0; background-color: white; }")
        html.append("    th { background-color: #007bff; color: white; padding: 10px; text-align: left; }")
        html.append("    td { padding: 8px; border-bottom: 1px solid #ddd; }")
        html.append("    tr:hover { background-color: #f9f9f9; }")
        html.append("  </style>")
        html.append("</head>")
        html.append("<body>")

        html.append(f"  <h1>Phase 5 Daily Report - {date}</h1>")

        # Summary
        html.append("  <h2>Trading Performance</h2>")
        html.append(f"  <div class='metric'><span class='metric-label'>Total Trades:</span> <span class='metric-value'>{total_trades}</span></div>")
        html.append(f"  <div class='metric'><span class='metric-label'>Wins:</span> <span class='metric-value good'>{wins} ({win_rate*100:.1f}%)</span></div>")
        html.append(f"  <div class='metric'><span class='metric-label'>Losses:</span> <span class='metric-value bad'>{losses}</span></div>")
        html.append(f"  <div class='metric'><span class='metric-label'>Avg P&L:</span> <span class='metric-value'>{avg_pnl:+.1f} pips</span></div>")

        # Comparison
        html.append("  <h2>Comparison to Baseline</h2>")
        html.append(f"  <div class='metric'><span class='metric-label'>Baseline Win Rate:</span> <span class='metric-value'>{self.baseline_win_rate*100:.1f}%</span></div>")
        html.append(f"  <div class='metric'><span class='metric-label'>Current Win Rate:</span> <span class='metric-value {status_color}'>{win_rate*100:.1f}%</span></div>")
        html.append(f"  <div class='metric'><span class='metric-label'>Improvement:</span> <span class='metric-value {status_color}'>{improvement:+.1f}%</span></div>")

        # Filter Effectiveness
        html.append("  <h2>Phase 4 Filter Effectiveness</h2>")
        html.append(f"  <div class='metric'><span class='metric-label'>Total Opportunities:</span> <span class='metric-value'>{total_opportunities}</span></div>")
        html.append(f"  <div class='metric'><span class='metric-label'>Executed:</span> <span class='metric-value'>{total_trades}</span></div>")
        html.append(f"  <div class='metric'><span class='metric-label'>Rejected:</span> <span class='metric-value'>{total_rejections}</span></div>")
        html.append(f"  <div class='metric'><span class='metric-label'>Pass Rate:</span> <span class='metric-value'>{pass_rate:.1f}%</span></div>")

        # Rejection table
        if total_rejections > 0:
            html.append("  <h3>Rejections by Filter</h3>")
            html.append("  <table>")
            html.append("    <tr><th>Filter Type</th><th>Count</th><th>Percentage</th></tr>")
            for filter_type in sorted(rejection_summary.keys()):
                count = rejection_summary[filter_type]
                pct = count / total_rejections * 100 if total_rejections > 0 else 0
                html.append(f"    <tr><td>{filter_type}</td><td>{count}</td><td>{pct:.1f}%</td></tr>")
            html.append("  </table>")

        # Trades table
        if total_trades > 0:
            html.append("  <h3>Detailed Trades</h3>")
            html.append("  <table>")
            html.append("    <tr><th>Time</th><th>Pair</th><th>Direction</th><th>Entry</th><th>SL</th><th>TP</th><th>Outcome</th><th>P&L</th></tr>")
            for trade in trades:
                time_str = trade['timestamp'].split('T')[1][:8] if trade['timestamp'] else 'N/A'
                outcome_class = 'good' if trade['outcome'] in ['WIN_TP1', 'WIN_TP2'] else 'bad' if trade['outcome'] == 'LOSS_SL' else 'neutral'
                html.append(f"    <tr>")
                html.append(f"      <td>{time_str}</td>")
                html.append(f"      <td>{trade['pair']}</td>")
                html.append(f"      <td>{trade['direction']}</td>")
                html.append(f"      <td>{trade['entry_price']:.5f if trade['entry_price'] else 'N/A'}</td>")
                html.append(f"      <td>{trade['stop_loss']:.5f if trade['stop_loss'] else 'N/A'}</td>")
                html.append(f"      <td>{trade['take_profit']:.5f if trade['take_profit'] else 'N/A'}</td>")
                html.append(f"      <td><span class='{outcome_class}'>{trade['outcome']}</span></td>")
                html.append(f"      <td>{trade['pnl_pips']:+.1f if trade['pnl_pips'] is not None else 'N/A'}</td>")
                html.append(f"    </tr>")
            html.append("  </table>")

        html.append("</body>")
        html.append("</html>")

        # Write file
        with open(output_file, 'w') as f:
            f.write("\n".join(html))

        print(f"✅ HTML report generated: {output_file}")
        return output_file


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Phase 5 report generator")
    parser.add_argument('--date', type=str, help="Report date (YYYY-MM-DD)")
    parser.add_argument('--detailed', action='store_true', help="Include detailed trade list")
    parser.add_argument('--html', type=str, help="Generate HTML report to file")
    args = parser.parse_args()

    generator = Phase5ReportGenerator()

    if args.html:
        generator.generate_html_report(args.date, args.html)
    else:
        text_report = generator.generate_text_report(args.date, args.detailed)
        print(text_report)

    return 0


if __name__ == '__main__':
    sys.exit(main())
