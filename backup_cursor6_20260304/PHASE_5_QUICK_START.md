# Phase 5: Demo Testing - Quick Start Guide

**Goal**: Run 5-7 days of demo trading and measure Phase 4 improvements
**Target**: Achieve ≥25% win rate (up from 15.5% baseline)
**Status**: ✅ All tools ready

---

## Pre-Flight Checklist (5 minutes)

```bash
# 1. Verify databases exist
ls -la data/phase5_test.db data/trade_alerts_rl.db

# 2. Test Phase 5 monitor
python phase5_monitor.py

# 3. Verify Scalp-Engine code
python -m py_compile Scalp-Engine/auto_trader_core.py

# 4. Check OANDA credentials
grep "OANDA" .env

# 5. Verify Trade-Alerts config
grep "GOOGLE_DRIVE\|OPENAI_API" .env
```

---

## Launch Phase 5 (5 minutes)

### Terminal 1: Start Trade-Alerts
```bash
python main.py
# Watch for: "Market state exported: market_state.json"
```

### Terminal 2: Start Scalp-Engine
```bash
cd Scalp-Engine
python scalp_engine.py  # AUTO mode (or scalp_ui.py for MANUAL)
# Watch for: "✅ [TRADE-OPENED]" or "⏭️ SKIPPING"
```

### Terminal 3: Start Dashboard (Optional)
```bash
pip install streamlit  # If not already installed
streamlit run phase5_dashboard.py
# Navigate to: http://localhost:8501
```

---

## Daily Monitoring (2 minutes)

### Morning
```bash
# Check overnight results
python phase5_daily_report.py --date $(date +%Y-%m-%d)
```

### During Trading
```bash
# Option A: Real-time dashboard
# http://localhost:8501

# Option B: Monitor script (refresh every 30 seconds)
watch -n 30 'python phase5_monitor.py --cumulative 1'

# Option C: Check logs
tail -50 Scalp-Engine/logs/scalp_engine.log
```

### End of Day
```bash
# Generate detailed report
python phase5_daily_report.py --date $(date +%Y-%m-%d) --detailed

# HTML report for email
python phase5_daily_report.py --date $(date +%Y-%m-%d) --html report.html

# Export metrics
python phase5_monitor.py --export phase5_metrics_$(date +%Y%m%d).json
```

---

## What to Watch For

### ✅ Good Signs
- Win rate trending upward
- Phase 4 rejecting 10-15% of trades
- Rejected trades would have lost money
- System running smoothly without errors
- Consistent daily metrics

### ⚠️ Warning Signs
- Win rate flat or declining
- Phase 4 rejecting >30% (too aggressive)
- Rejected trades would have won (false positives)
- System errors or missing trades
- Database full or connection issues

### 🛑 Stop Conditions
- Win rate drops below 10%
- 3+ consecutive losing days
- Obvious false positives from Phase 4
- System crashes requiring restart

---

## Report Examples

### Quick Status Check
```bash
python phase5_monitor.py --cumulative 7
```

**Output**:
```
Trading Activity:
  Trading Days: 5/7
  Total Trades: 42
  Wins: 11 (26.2%)
  Losses: 31
  Total P&L: +45 pips

Phase 4 Filter Effectiveness:
  Pass Rate: 85.7% (42 of 49 opportunities)
  Rejections: 7
    - CONFIDENCE: 4
    - JPY_DIRECTION: 3

Comparison to Baseline:
  Baseline: 15.5%
  Current: 26.2%
  Improvement: +10.7% ✅
```

### Detailed Daily Report
```bash
python phase5_daily_report.py --date 2026-02-23 --detailed
```

**Shows**:
- Today's trades with entry/exit/P&L
- Detailed rejection list with reasons
- Per-filter effectiveness
- Comparison to baseline

### HTML Report
```bash
python phase5_daily_report.py --date 2026-02-23 --html report.html
# Share report.html via email
```

---

## Integration with Trading Systems

### For Automatic Logging (Recommended)

**In Scalp-Engine/auto_trader_core.py close_trade():**
```python
# Log trade to Phase 5
from phase5_monitor import Phase5Monitor
monitor = Phase5Monitor()
monitor.log_trade({
    'pair': trade.pair,
    'direction': trade.direction,
    'entry_price': trade.entry_price,
    'outcome': trade.outcome,  # WIN_TP1, LOSS_SL, etc
    'pnl_pips': trade.pnl_pips,
})
```

**In Scalp-Engine/auto_trader_core.py open_trade():**
```python
# When trade is rejected:
if should_filter_by_low_confidence():
    monitor.log_rejection({
        'pair': opportunity['pair'],
        'filter_type': 'CONFIDENCE',
        'reason': 'Low consensus'
    })
    return None
```

### For Log Parsing (If No Code Modification)

```bash
# Parse existing logs every 30 seconds
watch -n 30 'python phase5_log_parser.py'
```

See PHASE_5_INTEGRATION.md for detailed code examples.

---

## Decision Tree

```
Is Phase 5 showing ≥25% win rate?
  ├─ YES → Proceed to Phase 6 (Live Trading)
  │        └─ Start with $100 CAD test account
  │
  └─ NO (20-25%) → Continue testing
      │            └─ Another 3-5 days
      │            └─ Check filter effectiveness
      │
      └─ NO (<20%) → Debug Phase 4
                    ├─ Are filters too aggressive?
                    ├─ Run: analyze_llm_direction_bias.py
                    ├─ Run: analyze_jpy_pairs.py
                    └─ Consider filter threshold adjustments
```

---

## Common Commands

### Daily Reporting
```bash
# Today's report
python phase5_daily_report.py

# Specific date
python phase5_daily_report.py --date 2026-02-23

# Detailed with trades
python phase5_daily_report.py --detailed

# HTML for email
python phase5_daily_report.py --html report.html
```

### Metrics & Analysis
```bash
# Last 7 days
python phase5_monitor.py --cumulative 7

# Last 14 days
python phase5_monitor.py --cumulative 14

# Export to JSON
python phase5_monitor.py --export metrics.json

# Specific date
python phase5_monitor.py --report 2026-02-23
```

### Dashboard
```bash
# Start real-time dashboard
streamlit run phase5_dashboard.py

# Dashboard available at: http://localhost:8501
# Auto-refreshes every 60 seconds
```

### System Control
```bash
# Trade-Alerts
python main.py

# Scalp-Engine (auto)
cd Scalp-Engine && python scalp_engine.py

# Scalp-Engine (manual approval)
cd Scalp-Engine && python scalp_ui.py

# Immediate analysis
python run_immediate_analysis.py
```

---

## 5-Day Testing Plan

### Day 1 - Setup & Validation
```bash
# Start systems in MANUAL mode
Terminal 1: python main.py
Terminal 2: python scalp_ui.py
Terminal 3: streamlit run phase5_dashboard.py

# Manually review and approve first 5-10 trades
# Verify Phase 4 filters are working
# Check database is getting populated
```

**Success**: 5+ trades executed, dashboard shows data

### Day 2-3 - AUTO Mode Validation
```bash
# Switch to AUTO mode (TRADING_MODE=AUTO in .env)
Terminal 1: python main.py
Terminal 2: python scalp_engine.py

# Monitor Phase 4 filter effectiveness
# Watch for false positives/negatives
# Check win rate trend
```

**Success**: Win rate trending 15-20%, filters working

### Day 4-5 - Full Demo Testing
```bash
# Continue AUTO mode
# Run full monitoring suite
# Generate daily reports
# Validate Phase 4 improvements
```

**Success**: Win rate 20%+, filters effective, ready for decision

### Day 6-7 (Optional) - Extended Validation
```bash
# If win rate 20-25%, continue for validation
# Collect more data for statistical significance
# Fine-tune any problematic filters
```

**Success**: Win rate 25%+, ready for live trading

---

## Next Steps

### If Phase 5 Succeeds (≥25% win rate)
```bash
# Prepare for Phase 6: Live Trading
1. Review all Phase 5 reports
2. Set up $100 CAD OANDA account
3. Configure trading parameters
4. Run Phase 6 with $20 per trade risk (2%)
5. Monitor for 1 week before increasing size
```

### If Phase 5 Marginal (20-25% win rate)
```bash
# Continue demo testing
1. Run 3-5 more days
2. Analyze Phase 4 filter effectiveness
3. Consider minor tweaks (confidence threshold, etc)
4. Validate improvements
5. Then proceed to Phase 6
```

### If Phase 5 Below Target (<20% win rate)
```bash
# Debug Phase 4 implementation
1. Run LLM analysis: python analyze_llm_direction_bias.py
2. Run JPY analysis: python analyze_jpy_pairs.py
3. Review individual trade rejections
4. Check if filters are too aggressive
5. Consider Phase 4 adjustments
6. Re-run Phase 5 with corrections
```

---

## Files Reference

### Monitoring Tools
- `phase5_monitor.py` - Core monitoring engine
- `phase5_daily_report.py` - Report generator
- `phase5_dashboard.py` - Live dashboard

### Documentation
- `PHASE_5_SETUP.md` - Complete setup guide (all details)
- `PHASE_5_INTEGRATION.md` - Integration with Scalp-Engine
- `PHASE_5_QUICK_START.md` - This file (quick reference)

### Database
- `data/phase5_test.db` - Phase 5 trades and rejections
- `data/trade_alerts_rl.db` - RL system database

### Logs
- `Scalp-Engine/logs/scalp_engine.log` - Trade execution log
- `logs/trade_alerts_*.log` - Trade-Alerts analysis logs

---

## Success Checklist

By end of Phase 5, you should have:

- [ ] 5+ days of trading data
- [ ] ≥20% win rate (preferably ≥25%)
- [ ] Phase 4 filters removing 10-15% of trades
- [ ] No major system crashes
- [ ] Validated rejected trades are poor quality
- [ ] Daily reports showing trends
- [ ] Database with complete trade history
- [ ] Confidence to proceed to live trading

---

## Immediate Next Action

```bash
# 1. Choose integration method (see PHASE_5_INTEGRATION.md)
# 2. Implement trade logging in Scalp-Engine
# 3. Start Trade-Alerts and Scalp-Engine
# 4. Monitor with Phase 5 tools for 5-7 days
# 5. Generate final report and decide on Phase 6
```

**Estimated Duration**: 5-7 days
**Expected Outcome**: Validated Phase 4 improvements, ready for live trading

---

## Need Help?

See the full guides:
- **Complete Setup**: PHASE_5_SETUP.md
- **Integration Help**: PHASE_5_INTEGRATION.md
- **System Status**: phase5_monitor.py --cumulative 7

