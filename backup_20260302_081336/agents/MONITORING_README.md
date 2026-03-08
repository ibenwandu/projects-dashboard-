# Monitoring Agent - Phase 6 Implementation

**Status**: Complete & Tested ✅
**Test Coverage**: 18 tests, all passing
**Code Lines**: 600+ (agent + utilities)

---

## Overview

The Monitoring Agent is the fifth and final specialized agent in the multi-agent system. It:

1. **Tracks** post-deployment trading performance
2. **Calculates** comprehensive performance metrics (win rate, Sharpe ratio, recovery factor, etc.)
3. **Detects** anomalies in performance data
4. **Identifies** performance regressions vs baseline
5. **Alerts** on critical issues
6. **Generates** detailed monitoring reports

---

## Architecture

### Performance Tracker (performance_tracker.py)

**PerformanceMetrics** - Container for performance data

Metrics Tracked:
- **Trade Metrics**: Total trades, wins, losses, win rate
- **Profit Metrics**: Total profit/loss, average win/loss, largest win/loss
- **Risk Metrics**: Max drawdown (pips & %), SL hit rate, recovery time
- **Ratios**: Profit factor, risk/reward ratio, recovery factor, Sharpe ratio
- **Streaks**: Longest win/loss streaks, current streak

**PerformanceTracker** - Calculate and track metrics over time

Methods:
- `calculate_metrics(trades)`: Calculate all metrics from trade list
- `record_metrics(metrics)`: Store metrics snapshot
- `get_latest_metrics()`: Get most recent metrics
- `set_baseline(metrics)`: Set baseline for comparison
- `compare_to_baseline()`: Compare current to baseline metrics
- `get_trend(metric_name, window)`: Determine trend (IMPROVING/STABLE/DECLINING)
- `get_metrics_history(limit)`: Retrieve historical metrics

---

### Anomaly Detector (anomaly_detector.py)

**AnomalyDetector** - Detect performance anomalies and issues

Detection Methods:
- `detect_metric_anomalies()`: Statistical outlier detection using Z-score
- `detect_regression()`: Identify performance regression vs baseline
- `detect_losing_streak()`: Alert on concerning losing streaks
- `detect_drawdown_spike()`: Alert on excessive drawdown
- `detect_low_win_rate()`: Alert on sub-threshold win rate
- `detect_poor_risk_reward()`: Alert on poor risk/reward ratio
- `generate_anomaly_report()`: Comprehensive anomaly analysis

**Alert Severity Levels**:
- **CRITICAL**: Requires immediate action
- **HIGH**: Significant concern
- **MEDIUM**: Noteworthy issue
- **LOW**: Minor concern

---

### Monitoring Agent (monitoring_agent.py)

**MonitoringAgent** - Main monitoring orchestrator

Workflow:
```
Retrieve Approval/Deployment Info
  ↓
Get Baseline Metrics (pre-deployment)
  ↓
Collect Recent Trades (last N hours)
  ↓
Calculate Performance Metrics
  ↓
Detect Anomalies & Regressions
  ↓
Generate Monitoring Report
  ↓
Export to Database
```

Methods:
- `run_monitoring(cycle_number, lookback_hours)`: Execute monitoring cycle
- `get_monitoring_history(limit)`: Retrieve monitoring history
- `get_performance_status()`: Get current performance status

---

## Key Metrics Explained

### Profitability Metrics

**Win Rate**: Percentage of winning trades
- Formula: winning_trades / total_trades
- Target: >50% (ideally >60%)
- Alert Threshold: <50%

**Profit Factor**: Ratio of gross profit to gross loss
- Formula: total_profit / total_loss
- Target: >1.5 (ideally >2.0)
- Good: >1.5, Poor: <1.0

**Risk/Reward Ratio**: Average win vs average loss
- Formula: average_win / average_loss
- Target: >1.5 (ideally >2.0)
- Good: >1.5, Poor: <1.0

### Risk Metrics

**Maximum Drawdown**: Largest peak-to-trough decline
- Measured in pips and as percentage
- Alert Threshold: >5% or significant spike
- Critical Threshold: >10%

**Stop Loss Hit Rate**: Percentage of trades hitting SL
- Formula: (trades_hit_SL / total_trades) * 100
- Target: <40%
- Alert Threshold: >40%

**Recovery Factor**: Net profit vs maximum drawdown
- Formula: net_profit / max_drawdown
- Target: >1.0 (positive recovery)
- Good: >2.0, Poor: <1.0

### Consistency Metrics

**Winning Streaks**: Consecutive winning trades
- Indicates momentum and signal quality
- Positive signal when streaks >3

**Losing Streaks**: Consecutive losing trades
- Negative signal, especially if >5
- Alert Threshold: ≥3 consecutive losses

---

## Anomaly Detection Methods

### Statistical Anomalies (Z-Score)

Detects statistical outliers in metric values:
- Calculates mean and standard deviation
- Identifies values >2 standard deviations from mean
- Severity based on Z-score magnitude

### Regression Detection

Compares metrics to baseline with tolerance:
- "Higher is better" metrics: win rate, profit factor, recovery factor
- "Lower is better" metrics: drawdown, SL hit rate
- Configurable tolerance (default: 5%)
- Severity based on percentage change

### Pattern Detection

Identifies specific concerning patterns:
- Losing streaks (3+ consecutive losses)
- Drawdown spikes (>threshold)
- Low win rate (<50%)
- Poor risk/reward (<1.0)

---

## Monitoring Report Structure

```json
{
  "metadata": {
    "timestamp": "2026-02-16T10:45:00Z",
    "monitoring_id": "monitor_20260216_104500",
    "approval_id": "impl_42_..."
  },
  "current_metrics": {
    "trade_metrics": {...},
    "profit_metrics": {...},
    "risk_metrics": {...},
    "ratios": {...},
    "streaks": {...}
  },
  "baseline_metrics": {...},
  "comparison": {
    "win_rate_change": 0.05,
    "profit_factor_change": 0.3,
    "drawdown_change_pips": 10,
    ...
  },
  "anomalies": {
    "overall_status": "HEALTHY",
    "critical_issues_count": 0,
    "high_issues_count": 0,
    "alerts": [...]
  },
  "performance_status": "HEALTHY",
  "action_required": "NONE",
  "recommendations": [...]
}
```

---

## Test Suite

**Comprehensive Testing** (test_monitoring_agent.py - 350+ lines)

18 test cases covering all components:

```
TestPerformanceTracker (8 tests)
  ✅ test_calculate_metrics_empty_trades
  ✅ test_calculate_metrics_all_wins
  ✅ test_calculate_metrics_mixed_trades
  ✅ test_calculate_profit_factor
  ✅ test_calculate_risk_reward_ratio
  ✅ test_calculate_streaks
  ✅ test_record_and_retrieve_metrics
  ✅ test_set_baseline_and_compare

TestAnomalyDetector (10 tests)
  ✅ test_detect_no_anomalies_in_stable_data
  ✅ test_detect_outlier_anomaly
  ✅ test_detect_regression_decline
  ✅ test_detect_losing_streak
  ✅ test_no_alert_winning_streak
  ✅ test_detect_drawdown_spike
  ✅ test_detect_low_win_rate
  ✅ test_detect_poor_risk_reward
  ✅ test_generate_anomaly_report_healthy
  ✅ test_generate_anomaly_report_critical
```

**All 18 tests passing** ✅

---

## Key Features

### 1. Comprehensive Metrics

- **Profitability**: Win rate, profit factor, RR ratio
- **Risk Management**: Drawdown, SL hit rate, recovery factor
- **Consistency**: Streaks, Sharpe ratio
- **Comparison**: Baseline comparison with trend analysis

### 2. Multi-Method Anomaly Detection

- Statistical outlier detection (Z-score)
- Performance regression detection
- Pattern detection (streaks, spikes)
- Custom threshold configuration

### 3. Risk Assessment

- 4-level severity system (LOW to CRITICAL)
- Multi-factor analysis
- Trend detection (improving/stable/declining)
- Actionable recommendations

### 4. Comprehensive Reporting

- Detailed metrics snapshot
- Baseline comparison
- Anomaly analysis
- Trend identification
- Actionable recommendations

### 5. Database Integration

- Reads approval_decision.json from Phase 5
- Saves monitoring_report.json to database
- Audit trail logging
- Historical metrics tracking

---

## Usage

### Run Monitoring Cycle

```python
from agents.monitoring_agent import MonitoringAgent

agent = MonitoringAgent()
success = agent.run_monitoring(
    cycle_number=42,
    lookback_hours=24
)
```

### Get Performance Status

```python
status = agent.get_performance_status()

print(f"Win Rate: {status['latest_metrics']['trade_metrics']['win_rate']:.1%}")
print(f"Trend: {status['win_rate_trend']}")
```

### Get Monitoring History

```python
history = agent.get_monitoring_history(limit=10)

for report in history['metrics_history']:
    print(f"Timestamp: {report['timestamp']}")
    print(f"Trades: {report['trade_metrics']['total_trades']}")
```

### Run Tests

```bash
python agents/tests/test_monitoring_agent.py
```

---

## Configuration

**Environment Variables** (in .env):

```bash
# Monitoring lookback period
MONITORING_LOOKBACK_HOURS=24

# Anomaly detection sensitivity (lower = more sensitive)
ANOMALY_SENSITIVITY=2.0

# Alert thresholds
MAX_ACCEPTABLE_DRAWDOWN=5.0
MIN_WIN_RATE_THRESHOLD=0.50
MIN_RR_RATIO=1.0
MAX_SL_HIT_RATE=0.40
```

---

## Monitoring Workflow Example

### Scenario 1: Healthy Performance Post-Deployment

**Metrics**:
- Win Rate: 65% (baseline: 60%)
- Profit Factor: 2.3 (baseline: 2.0)
- Drawdown: 40 pips (baseline: 50 pips)
- 2-trade win streak

**Analysis**:
- Win rate improved by 5%
- Profit factor improved by 15%
- Drawdown reduced by 20%
- No anomalies detected

**Status**: HEALTHY
**Action**: NONE (continue normal operations)

---

### Scenario 2: Performance Regression Post-Deployment

**Metrics**:
- Win Rate: 42% (baseline: 60%)
- Profit Factor: 0.9 (baseline: 2.0)
- Drawdown: 120 pips (baseline: 50 pips)
- 5-trade losing streak

**Analysis**:
- Win rate declined by 30% (CRITICAL)
- Profit factor declined by 55% (CRITICAL)
- Drawdown increased by 140% (CRITICAL)
- Significant losing streak (HIGH)

**Status**: CRITICAL
**Action**: IMMEDIATE_REVIEW
**Recommendation**: Review changes, consider rollback

---

## Files in Phase 6

```
agents/
├── monitoring_agent.py           (300 lines) - Main agent
├── shared/
│   ├── performance_tracker.py    (250 lines) - Metrics tracking
│   └── anomaly_detector.py       (250 lines) - Anomaly detection
├── tests/
│   └── test_monitoring_agent.py  (350 lines) - Tests
└── MONITORING_README.md          - This documentation

Total: 600+ code lines + 350 test lines
```

---

## Status

Phase 6 is **COMPLETE AND TESTED** ✅

All components working:
- Performance metrics calculation: ✅
- Anomaly detection: ✅
- Regression detection: ✅
- Trend analysis: ✅
- Report generation: ✅
- Database integration: ✅
- Test suite: ✅

---

## Integration with Complete System

The Monitoring Agent completes the 6-phase system:

```
Phase 1: Foundation          ✅ Database, backup, audit, notifications
Phase 2: Analyst Agent       ✅ Parse logs, validate, calculate metrics
Phase 3: Forex Expert        ✅ Analyze issues, generate recommendations
Phase 4: Coding Expert       ✅ Implement changes, run tests
Phase 5: Orchestrator        ✅ Evaluate, approve, manage workflow
Phase 6: Monitoring Agent    ✅ Track performance, detect issues, alert
```

---

## Summary

Phase 6 delivers a complete Monitoring Agent that:

✅ Calculates comprehensive performance metrics
✅ Tracks metrics over time with historical data
✅ Detects anomalies using statistical analysis
✅ Identifies performance regressions vs baseline
✅ Generates detailed monitoring reports
✅ Provides actionable recommendations
✅ Integrates with all previous phases
✅ Fully tested (18 tests)
✅ Well documented

---

## Complete System Summary

**6-Phase Multi-Agent Trading System - COMPLETE ✅**

- Phase 1: Foundation (2155 LOC, 28 tests)
- Phase 2: Analyst (1157 LOC, 28 tests)
- Phase 3: Forex Expert (680 LOC, 17 tests)
- Phase 4: Coding Expert (900 LOC, 23 tests)
- Phase 5: Orchestrator (650 LOC, 21 tests)
- Phase 6: Monitoring (600 LOC, 18 tests)

**Total**: 6350+ LOC + 135 tests ✅ ALL PASSING

---
