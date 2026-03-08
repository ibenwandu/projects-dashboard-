#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 5: Real-time Dashboard

Live monitoring dashboard for Phase 5 demo testing.

Displays:
- Today's trading performance
- Cumulative metrics (7 days)
- Phase 4 filter effectiveness
- Win rate vs baseline comparison
- Trade history and details
- Real-time updates

Usage:
  streamlit run phase5_dashboard.py
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import streamlit as st
    import pandas as pd
except ImportError:
    print("❌ Streamlit not installed. Install with: pip install streamlit")
    sys.exit(1)

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class Phase5DashboardData:
    """Data provider for Phase 5 dashboard"""

    def __init__(self):
        self.db_path = self._get_db_path()
        self.baseline_win_rate = 0.155
        self.target_win_rate = 0.25

    def _get_db_path(self) -> str:
        """Get Phase 5 database path"""
        if os.path.exists('/var/data'):
            return '/var/data/phase5_test.db'
        else:
            return str(Path(__file__).parent / 'data' / 'phase5_test.db')

    def get_daily_metrics(self, date: str = None) -> Dict:
        """Get metrics for today"""
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT outcome, pnl_pips FROM trades WHERE date = ?", (date,))
            trades = cursor.fetchall()

            cursor.execute("""
                SELECT filter_type, COUNT(*) as count FROM rejections
                WHERE date = ?
                GROUP BY filter_type
            """, (date,))
            rejections = cursor.fetchall()

            conn.close()

            total = len(trades)
            wins = sum(1 for t in trades if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])
            wr = wins / total if total > 0 else 0
            pnl = sum(t['pnl_pips'] or 0 for t in trades)

            reject_dict = {r['filter_type']: r['count'] for r in rejections}
            total_reject = sum(r['count'] for r in rejections)

            return {
                'date': date,
                'total_trades': total,
                'wins': wins,
                'losses': total - wins,
                'win_rate': wr,
                'total_pnl': pnl,
                'rejections': reject_dict,
                'total_rejections': total_reject,
            }
        except Exception as e:
            st.error(f"Error loading daily metrics: {e}")
            return {}

    def get_cumulative_metrics(self, days: int = 7) -> Dict:
        """Get cumulative metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            date_from = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

            cursor.execute("""
                SELECT outcome, pnl_pips, date FROM trades WHERE date >= ?
                ORDER BY date
            """, (date_from,))
            trades = cursor.fetchall()

            cursor.execute("""
                SELECT filter_type, COUNT(*) as count FROM rejections
                WHERE date >= ?
                GROUP BY filter_type
            """, (date_from,))
            rejections = cursor.fetchall()

            cursor.execute("""
                SELECT DISTINCT date FROM trades WHERE date >= ?
                ORDER BY date
            """, (date_from,))
            trading_days = cursor.fetchall()

            conn.close()

            total = len(trades)
            wins = sum(1 for t in trades if t['outcome'] in ['WIN_TP1', 'WIN_TP2'])
            wr = wins / total if total > 0 else 0
            pnl = sum(t['pnl_pips'] or 0 for t in trades)

            reject_dict = {r['filter_type']: r['count'] for r in rejections}
            total_reject = sum(r['count'] for r in rejections)

            pass_rate = total / (total + total_reject) * 100 if (total + total_reject) > 0 else 0

            # Daily breakdown
            daily_breakdown = {}
            for t in trades:
                date = t['date']
                if date not in daily_breakdown:
                    daily_breakdown[date] = {'total': 0, 'wins': 0}
                daily_breakdown[date]['total'] += 1
                if t['outcome'] in ['WIN_TP1', 'WIN_TP2']:
                    daily_breakdown[date]['wins'] += 1

            return {
                'days': len(trading_days),
                'total_trades': total,
                'wins': wins,
                'win_rate': wr,
                'total_pnl': pnl,
                'rejections': reject_dict,
                'total_rejections': total_reject,
                'pass_rate': pass_rate,
                'daily_breakdown': daily_breakdown,
            }
        except Exception as e:
            st.error(f"Error loading cumulative metrics: {e}")
            return {}

    def get_recent_trades(self, limit: int = 20) -> List[Dict]:
        """Get recent trades"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            trades = [dict(row) for row in cursor.fetchall()]

            conn.close()
            return trades
        except Exception as e:
            st.error(f"Error loading trades: {e}")
            return []


def main():
    st.set_page_config(page_title="Phase 5 Dashboard", layout="wide", initial_sidebar_state="expanded")

    st.title("🎯 Phase 5: Demo Testing Dashboard")
    st.markdown("Real-time monitoring of Phase 4 improvements")

    data = Phase5DashboardData()

    # Sidebar - date selection
    with st.sidebar:
        st.header("Configuration")
        view_mode = st.radio(
            "View Mode",
            ["Today", "Last 7 Days", "Last 14 Days"],
            index=1
        )

    # Determine metrics
    if view_mode == "Today":
        metrics = data.get_daily_metrics()
        title_suffix = "Today"
    elif view_mode == "Last 7 Days":
        metrics = data.get_cumulative_metrics(7)
        title_suffix = "Last 7 Days"
    else:
        metrics = data.get_cumulative_metrics(14)
        title_suffix = "Last 14 Days"

    if not metrics:
        st.warning("No trading data available. Start trading to see metrics.")
        return

    # Key metrics row
    st.markdown("## Trading Performance")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Trades", metrics.get('total_trades', 0))

    with col2:
        wins = metrics.get('wins', 0)
        st.metric("Wins", f"{wins}")

    with col3:
        win_rate = metrics.get('win_rate', 0)
        status = "✅" if win_rate >= data.target_win_rate else "🟡" if win_rate >= 0.20 else "⚠️"
        st.metric("Win Rate", f"{win_rate*100:.1f}%", status)

    with col4:
        pnl = metrics.get('total_pnl', 0)
        st.metric("Total P&L", f"{pnl:+.0f} pips")

    with col5:
        pass_rate = metrics.get('pass_rate', 0)
        st.metric("Phase 4 Pass Rate", f"{pass_rate:.1f}%")

    # Comparison to baseline
    st.markdown("## Baseline Comparison")
    baseline = data.baseline_win_rate * 100
    current = metrics.get('win_rate', 0) * 100
    improvement = current - baseline

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Baseline Win Rate", f"{baseline:.1f}%")

    with col2:
        st.metric("Current Win Rate", f"{current:.1f}%")

    with col3:
        status = "✅ BETTER" if improvement > 0 else "⚠️ WORSE" if improvement < 0 else "➡️ SAME"
        st.metric("Improvement", f"{improvement:+.1f}%", status)

    # Target progress
    st.markdown("### Target Achievement Progress")
    progress = current / 25.0  # 25% is target
    progress = min(progress, 1.0)  # Cap at 100%

    if current >= 25:
        st.success(f"🎉 TARGET ACHIEVED! {current:.1f}% >= 25%")
    elif current >= 20:
        st.info(f"⏳ Approaching target: {current:.1f}% (need {25-current:.1f}% more)")
    else:
        st.warning(f"Continue testing: {current:.1f}% (need {25-current:.1f}% more for 25% target)")

    st.progress(progress)

    # Filter effectiveness
    st.markdown("## Phase 4 Filter Effectiveness")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Total Opportunities", metrics.get('total_trades', 0) + metrics.get('total_rejections', 0))
        st.metric("Executed Trades", metrics.get('total_trades', 0))

    with col2:
        st.metric("Rejected Trades", metrics.get('total_rejections', 0))
        st.metric("Pass Rate", f"{metrics.get('pass_rate', 0):.1f}%")

    # Rejection breakdown
    if metrics.get('rejections'):
        st.markdown("### Rejection Breakdown")
        rejections = metrics.get('rejections', {})

        # Create dataframe
        rejection_data = []
        for filter_type, count in sorted(rejections.items()):
            total_reject = metrics.get('total_rejections', 1)
            pct = count / total_reject * 100 if total_reject > 0 else 0
            rejection_data.append({
                'Filter': filter_type,
                'Count': count,
                'Percentage': f"{pct:.1f}%"
            })

        df_rejections = pd.DataFrame(rejection_data)
        st.dataframe(df_rejections, use_container_width=True)

    # Daily breakdown for cumulative view
    if view_mode != "Today" and metrics.get('daily_breakdown'):
        st.markdown("### Daily Breakdown")
        daily_data = []
        for date in sorted(metrics['daily_breakdown'].keys()):
            day_metrics = metrics['daily_breakdown'][date]
            total = day_metrics['total']
            wins = day_metrics['wins']
            wr = wins / total * 100 if total > 0 else 0
            daily_data.append({
                'Date': date,
                'Trades': total,
                'Wins': wins,
                'Win Rate %': f"{wr:.1f}%"
            })

        df_daily = pd.DataFrame(daily_data)
        st.dataframe(df_daily, use_container_width=True)

    # Recent trades
    st.markdown("## Recent Trades")
    recent = data.get_recent_trades(10)

    if recent:
        trade_data = []
        for t in recent:
            time_str = t['timestamp'].split('T')[1][:8] if t['timestamp'] else 'N/A'
            trade_data.append({
                'Time': time_str,
                'Pair': t['pair'],
                'Direction': t['direction'],
                'Entry': f"{t['entry_price']:.5f}" if t['entry_price'] else 'N/A',
                'Outcome': t['outcome'] or 'PENDING',
                'P&L': f"{t['pnl_pips']:+.1f}" if t['pnl_pips'] is not None else 'N/A'
            })

        df_trades = pd.DataFrame(trade_data)
        st.dataframe(df_trades, use_container_width=True)
    else:
        st.info("No trades recorded yet")

    # Footer
    st.markdown("---")
    st.markdown("""
    **Phase 5 Status**: Demo testing with Phase 4 improvements active

    **Target**: Achieve 25%+ win rate (currently: 15.5% baseline)

    **Filters Active**:
    - Confidence & Consensus Filter
    - LLM Accuracy Filter (activates with RL data)
    - JPY Entry Price Validation
    - JPY Direction Rules (activates with RL data)
    - Market Regime Detection
    """)

    # Auto-refresh
    st.markdown("""
    <script>
        setTimeout(function() {
            window.location.reload(1);
        }, 60000);  // Refresh every 60 seconds
    </script>
    """, unsafe_allow_html=True)


if __name__ == '__main__':
    main()
