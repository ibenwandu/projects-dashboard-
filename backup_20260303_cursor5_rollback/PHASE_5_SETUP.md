# Phase 5: Demo Testing - Setup & Execution Guide

**Date**: February 23, 2026
**Status**: Ready for implementation
**Duration**: 5-7 days of demo trading
**Goal**: Validate Phase 4 improvements and measure win rate improvement

---

## Overview

Phase 5 runs the complete trading system on a demo OANDA account with:
- ✅ Phase 3 safety systems (SL, TP, circuit breaker, position cap)
- ✅ Phase 4 quality filters (confidence, LLM accuracy, JPY fixes)
- 📊 Real-time monitoring of trade performance
- 📈 Daily reports showing win rate vs baseline

**Success Criteria**:
- Achieve ≥25% win rate (up from 15.5% baseline)
- Phase 4 filters removing ~10-15% of worst trades
- No false positives (legitimate trades being blocked)

---

## Architecture

### System Components

```
Trade-Alerts                    Scalp-Engine
(LLM Analysis)                 (Execution)
      ↓                              ↓
market_state.json ← ← ← ← ← ← → open_trade() [Phase 4 Filters]
      ↓                              ↓
      └──→ RL Database ←────────→ OANDA API
                 ↓
           Phase 5 Monitor
         (Tracking Trades)
                 ↓
         phase5_test.db
                 ↓
    ┌────────────┼────────────┐
    ↓            ↓            ↓
Daily Report  Dashboard   Analytics
```

### Data Flow

1. **Trade-Alerts** → Generates market state and recommendations
2. **Scalp-Engine** → Applies Phase 4 filters → Executes via OANDA
3. **Phase 5 Monitor** → Captures trades and rejections
4. **Reporting** → Daily reports, live dashboard, JSON exports

---

## Pre-Test Checklist

### 1. System Configuration

- [ ] OANDA demo account credentials configured in `.env`
  ```bash
  OANDA_ACCESS_TOKEN=...
  OANDA_ACCOUNT_ID=...
  OANDA_ENV=practice  # Must be practice for demo
  ```

- [ ] Trade-Alerts configured
  ```bash
  GOOGLE_DRIVE_FOLDER_ID=...
  OPENAI_API_KEY=...
  # All LLM keys configured
  ```

- [ ] Scalp-Engine trading mode set
  ```bash
  TRADING_MODE=AUTO  # or MANUAL for manual approval
  ```

### 2. Database Setup

- [ ] Phase 5 database initialized
  ```bash
  python phase5_monitor.py
  # Creates: data/phase5_test.db
  ```

- [ ] RL database ready
  ```bash
  python historical_backfill.py  # (if not already done)
  # Creates: data/trade_alerts_rl.db
  ```

### 3. Code Verification

- [ ] Phase 4 filters compiled without errors
  ```bash
  python -m py_compile Scalp-Engine/auto_trader_core.py
  ```

- [ ] Monitoring tools ready
  ```bash
  python phase5_monitor.py --help
  python phase5_daily_report.py --help
  ```

- [ ] Dashboard dependencies installed
  ```bash
  pip install streamlit pandas
  ```

---

## Starting Phase 5

### Option A: Manual Trading (Recommended for First Day)

**1. Terminal 1 - Trade-Alerts (Market Analysis)**
```bash
# Start Trade-Alerts to generate market state
cd /c/Users/user/projects/personal/Trade-Alerts
python main.py
```

**Expected Output**:
```
[INFO] 2026-02-23 14:00:00 - Market analysis starting
[INFO] 2026-02-23 14:05:00 - ChatGPT analysis complete
[INFO] 2026-02-23 14:10:00 - Gemini analysis complete
[INFO] 2026-02-23 14:15:00 - Claude analysis complete
[INFO] 2026-02-23 14:20:00 - Synthesis complete
[INFO] 2026-02-23 14:25:00 - Market state exported: market_state.json
```

**2. Terminal 2 - Scalp-Engine (Trade Execution)**
```bash
# Start Scalp-Engine in MANUAL mode for first day
cd Scalp-Engine
python scalp_ui.py
# or for automation:
python scalp_engine.py
```

**Expected Output**:
```
[INFO] 2026-02-23 14:30:00 - Scalp-Engine started
[INFO] 2026-02-23 14:31:00 - Loaded market state from market_state.json
[INFO] 2026-02-23 14:32:00 - EUR/USD LONG: Confidence 75%, Consensus 80% ✅ PASSED Phase 4
[INFO] 2026-02-23 14:33:00 - GBP/JPY SHORT: Confidence 35%, Consensus 40% ❌ REJECTED Low confidence
```

**3. Terminal 3 - Phase 5 Monitor (Live Tracking)**
```bash
# Monitor trades in real-time
watch -n 30 'python phase5_monitor.py --cumulative 1'
# Or check specific date:
python phase5_monitor.py --report 2026-02-23
```

### Option B: Automated Trading (After First Day)

```bash
# Set TRADING_MODE=AUTO in .env
export TRADING_MODE=AUTO

# Terminal 1
python main.py

# Terminal 2
cd Scalp-Engine
python scalp_engine.py

# Terminal 3 - Optional dashboard
streamlit run phase5_dashboard.py
# Browse to: http://localhost:8501
```

---

## Daily Workflow

### Morning (Before Market Opens)

1. **Check overnight trades** (if trading 24h)
   ```bash
   python phase5_daily_report.py --date 2026-02-23
   ```

2. **Start systems**
   ```bash
   # Terminal 1
   cd Trade-Alerts
   python main.py

   # Terminal 2
   cd Scalp-Engine
   python scalp_engine.py

   # Terminal 3 (optional)
   streamlit run phase5_dashboard.py
   ```

### During Market Hours

1. **Monitor trades** in real-time via:
   - Streamlit dashboard (http://localhost:8501)
   - Or live monitor: `watch -n 30 'python phase5_monitor.py'`

2. **Watch for Phase 4 filters**:
   - How many trades are being rejected?
   - Are rejections legitimate or false positives?
   - Is win rate improving?

3. **Manual override if needed** (if in MANUAL mode):
   - Review trades in Scalp-Engine UI
   - Approve high-confidence trades
   - Reject questionable ones

### End of Day

1. **Generate daily report**
   ```bash
   python phase5_daily_report.py --detailed --html phase5_report_2026-02-23.html
   ```

2. **Check metrics**
   ```bash
   python phase5_daily_report.py --date 2026-02-23
   ```

3. **Email report** (optional)
   - Attach HTML report to email
   - Share with stakeholders

4. **Save logs**
   ```bash
   # Archive logs for the day
   mkdir -p logs_archive/$(date +%Y%m%d)
   cp logs/*.log logs_archive/$(date +%Y%m%d)/
   ```

---

## Monitoring Tools

### 1. Real-Time Dashboard (Best for Live Monitoring)

```bash
streamlit run phase5_dashboard.py
```

**Features**:
- Live win rate display
- Phase 4 filter effectiveness
- Daily breakdown
- Recent trades list
- Auto-refreshes every 60 seconds

**Access**: http://localhost:8501

### 2. Daily Report (Best for Analysis)

```bash
# Text report
python phase5_daily_report.py --date 2026-02-23 --detailed

# HTML report (for email)
python phase5_daily_report.py --date 2026-02-23 --html report.html
```

**Output**:
- Trading performance (win rate, P&L)
- Phase 4 filter breakdown
- Detailed trade list
- Detailed rejection list

### 3. Monitor Script (Best for Automation)

```bash
# Check last 7 days
python phase5_monitor.py --cumulative 7

# Export to JSON for external analysis
python phase5_monitor.py --export phase5_metrics.json
```

**Outputs**:
- JSON with all metrics
- Can be imported to spreadsheet
- Useful for trend analysis

---

## What to Watch For

### Good Signs ✅

- Win rate increasing trend (15.5% → 20%+)
- Phase 4 filters removing consistent % of trades (10-15%)
- Rejected trades would have lost money (validate accuracy)
- No false positives (legitimate trades being blocked)
- Stable P&L over days

### Warning Signs ⚠️

- Win rate staying flat at 15.5%
- Phase 4 filters removing too many trades (>30%)
- Rejected trades would have won
- Inconsistent performance day-to-day
- System errors or missing logs

### Stop Conditions 🛑

If any of these occur, pause testing:
- Win rate drops below 10% (indicates regression)
- Consecutive 3+ days of losses
- Phase 4 filters causing obvious false positives
- System crashes or database corruption

---

## Phase 4 Filter Integration

### How Filters Work in Execution

```python
# In Scalp-Engine/auto_trader_core.py open_trade():

# PHASE 3: Check circuit breaker
if circuit_breaker_active:
    return None  # No more trades for today

# PHASE 4 STEP 1: Check market regime
if should_filter_by_market_regime():
    log_rejection("MARKET_REGIME", reason)
    return None

# PHASE 4 STEP 2: Check confidence
if should_filter_by_low_confidence():
    log_rejection("CONFIDENCE", reason)
    return None

# PHASE 4 STEP 2: Check LLM accuracy
if should_filter_by_llm_accuracy():
    log_rejection("LLM_ACCURACY", reason)
    return None

# PHASE 4 STEP 3: Check JPY direction rules
if should_apply_jpy_direction_rules():
    log_rejection("JPY_DIRECTION", reason)
    return None

# All filters passed
log_trade_executed(trade_data)
execute_trade()
```

### Expected Filter Behavior

**Confidence Filter**:
- Rejects: <50% consensus OR <40% confidence
- Expected rejection rate: 5-8% of opportunities
- Reason: Eliminates weak consensus trades

**LLM Accuracy Filter**:
- Activates when RL database populated
- Rejects: Trades from LLMs with <25% accuracy
- Expected rejection rate: 2-3% of opportunities
- Reason: Eliminates broken LLM recommendations

**JPY Filters**:
- Entry validation: Rejects >2% deviation
- Direction rules: Blocks 0% win-rate directions
- Expected rejection rate: 3-5% of JPY opportunities
- Reason: Improves JPY pair quality

**Market Regime**:
- Rejects: SHORT in BULLISH, LONG in BEARISH trends
- Expected rejection rate: 2-5% of opportunities
- Reason: Prevents trading against trends

**Total Expected**: 10-15% of opportunities rejected

---

## Interpreting Results

### Win Rate Benchmarks

| Win Rate | Status | Action |
|----------|--------|--------|
| ≥25% | ✅ SUCCESS | Proceed to live trading |
| 20-25% | 🟡 GOOD | Continue testing a few more days |
| 15-20% | ⚠️ PARTIAL | Phase 4 is helping but needs more data |
| <15% | 🔴 FAILED | Debug - Phase 4 may be too aggressive |

### Filter Effectiveness Benchmarks

| Rejection Rate | Status | Meaning |
|----------------|--------|---------|
| 10-15% | ✅ GOOD | Correct filtering of poor trades |
| 15-25% | 🟡 CAUTION | May be over-filtering |
| >25% | 🔴 PROBLEM | Too aggressive - missing good trades |
| <5% | ⚠️ LOOSE | Filters not effective enough |

### P&L Benchmarks (Per Trade)

| Avg P&L | Status | Meaning |
|---------|--------|---------|
| +20+ pips | ✅ EXCELLENT | Trades are large and winning |
| +5 to +20 pips | ✅ GOOD | Steady profits |
| 0 to +5 pips | 🟡 MARGINAL | Barely profitable |
| Negative | 🔴 LOSING | System is losing money |

---

## Example: First Day of Testing

**Morning Setup (9:00 AM)**
```bash
# Start systems
Terminal 1: python main.py
Terminal 2: python scalp_ui.py (MANUAL mode)
Terminal 3: streamlit run phase5_dashboard.py
```

**Mid-Day Check (12:00 PM)**
```bash
# Dashboard shows:
# - 6 trades executed
# - 2 wins, 4 pending
# - 2 rejections (confidence filter)
# - Win rate: 33% (but small sample)
```

**End of Day Report (6:00 PM)**
```bash
python phase5_daily_report.py --date 2026-02-23 --detailed

# Output shows:
# - 12 total trades
# - 3 wins, 9 losses
# - Win rate: 25%
# - 5 rejections (confidence × 3, JPY entry × 2)
# - Status: ✅ GOOD - Win rate improved over baseline!
```

---

## Troubleshooting

### Issue: No trades being executed

**Possible causes**:
1. Market is closed
2. All trades are being rejected (filters too strict)
3. OANDA connection failed

**Fix**:
```bash
# Check logs
tail -50 Scalp-Engine/logs/scalp_engine.log

# Verify OANDA connection
python Scalp-Engine/test_oanda_connection.py

# Check if trades are being rejected
grep "REJECTING\|BLOCKED" Scalp-Engine/logs/scalp_engine.log
```

### Issue: All trades are losing

**Possible causes**:
1. Poor market conditions
2. Phase 4 filters rejecting good trades
3. Entry timing off

**Fix**:
```bash
# Check rejection patterns
grep "REJECTION" Scalp-Engine/logs/scalp_engine.log | sort | uniq -c

# Compare rejected vs executed
python phase5_daily_report.py --detailed
# Look for patterns in what's being rejected
```

### Issue: Dashboard not loading

**Fix**:
```bash
# Install streamlit
pip install streamlit

# Run with verbose output
streamlit run phase5_dashboard.py --logger.level=debug
```

### Issue: Database locked

**Fix**:
```bash
# Stop all Phase 5 tools
# Restart Trade-Alerts and Scalp-Engine
# Phase5 database will auto-recover
```

---

## Success Criteria

### Minimum Requirements to Proceed to Live Trading

- [ ] Tested for minimum 5 days
- [ ] Achieved ≥20% win rate (preferably ≥25%)
- [ ] Phase 4 filters removing 10-15% of opportunities
- [ ] No major system crashes or errors
- [ ] Logs complete and traceable
- [ ] Can explain every trade decision

### Recommended for Live Trading

- [ ] Tested for 7 days
- [ ] Achieved ≥25% win rate consistently
- [ ] Phase 4 filters validated (not over-filtering)
- [ ] Zero false positives (rejected trades checked)
- [ ] Ready with $100 CAD test account
- [ ] Daily monitoring procedures in place

---

## Next Steps After Phase 5

### If Win Rate ≥25%
1. ✅ Proceed to Phase 6: Live Trading
2. Set up $100 CAD test account
3. Start with $20/trade risk (2% of $1000)
4. Monitor for first week live

### If Win Rate 20-25%
1. ⏳ Extended demo testing (another 3-5 days)
2. Analyze phase 4 filter effectiveness
3. Consider minor tuning:
   - Confidence threshold adjustment
   - JPY filter tweaks
4. Then proceed to live trading

### If Win Rate <20%
1. 🔴 Debug Phase 4 implementation
2. Check if filters are too aggressive
3. Run detailed analysis:
   ```bash
   python analyze_llm_direction_bias.py
   python analyze_jpy_pairs.py
   python backtest_phase4_improvements.py
   ```
4. Review individual trades for patterns
5. Consider Phase 4 adjustment

---

## Files & Commands Reference

### Monitoring Tools

```bash
# Dashboard (real-time)
streamlit run phase5_dashboard.py

# Daily report (detailed)
python phase5_daily_report.py --detailed

# HTML report (email)
python phase5_daily_report.py --html report.html

# JSON export (analysis)
python phase5_monitor.py --export metrics.json

# Cumulative metrics
python phase5_monitor.py --cumulative 7
```

### System Control

```bash
# Start Trade-Alerts
python main.py

# Start Scalp-Engine (auto)
cd Scalp-Engine
python scalp_engine.py

# Start Scalp-Engine UI (manual)
python scalp_ui.py

# Force analysis run
python run_immediate_analysis.py

# Sync RL database
python sync_database_from_render.py
```

### Analysis Tools (if needed)

```bash
# LLM analysis
python analyze_llm_direction_bias.py

# JPY analysis
python analyze_jpy_pairs.py

# Backtest validation
python backtest_phase4_improvements.py
```

---

## Quick Start

**Complete Phase 5 setup in 5 minutes**:

```bash
# 1. Verify databases exist
ls data/phase5_test.db data/trade_alerts_rl.db

# 2. Check code syntax
python -m py_compile Scalp-Engine/auto_trader_core.py

# 3. Start Trade-Alerts
python main.py &

# 4. Start Scalp-Engine
cd Scalp-Engine
python scalp_engine.py &

# 5. Start dashboard
streamlit run phase5_dashboard.py
```

**Navigate to**: http://localhost:8501

---

## Summary

**Phase 5 is ready to run**. Use the monitoring tools provided to track:
- Win rate improvement vs 15.5% baseline
- Phase 4 filter effectiveness
- Daily performance trends

**Success = ≥25% win rate after 5-7 days of demo trading**

Then proceed to Phase 6: Live Trading with $100 CAD test account.

