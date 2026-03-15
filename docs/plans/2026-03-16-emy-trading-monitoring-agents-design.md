# Emy Trading System Monitoring Agents — Design Document

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Enable Emy to autonomously monitor trading system compliance, analyze performance, enforce trading hours rules, and provide profitability recommendations through natural language instructions.

**Architecture:** Three independent agents (TradingHoursMonitorAgent, LogAnalysisAgent, ProfitabilityAgent) scheduled via Celery Beat, each with Claude-powered analysis and autonomous enforcement/reporting capabilities.

**Tech Stack:** Celery Beat scheduling, OANDA API, EMyDatabase, Claude (Haiku/Sonnet), Pushover alerts, EMySubAgent framework

---

## Overview

### Vision
Emy acts as an autonomous trading system supervisor:
- User gives natural language instructions: "Monitor trading hours, close non-compliant trades daily"
- Emy delegates to specialized monitoring agents
- Agents execute autonomously on schedules, enforce compliance, and report results
- User receives alerts for critical issues, reviews reports on demand

### Three Monitoring Agents

| Agent | Purpose | Schedule | Key Action |
|-------|---------|----------|-----------|
| **TradingHoursMonitorAgent** | Monitor & enforce trading hours compliance | Friday 21:30, Mon-Thu 23:00 (enforce) + every 6h (monitor) | Close non-compliant trades via OANDA, send alert |
| **LogAnalysisAgent** | Periodic review of trading activity | Daily 23:00 UTC | Detect anomalies, store report, alert if critical |
| **ProfitabilityAgent** | Analyze profitability patterns, generate recommendations | Weekly Sunday 22:00 UTC | Use Claude to suggest optimizations, store insights |

---

## Detailed Design

### 1. TradingHoursMonitorAgent

**Responsibility:** Monitor trading hours compliance against TradingHoursManager rules and autonomously close non-compliant trades.

**Rules Enforced (UTC):**
- Trading window: Monday 01:00 – Friday 21:30
- Friday: All trades close at 21:30 (no exceptions)
- Mon-Thu: Non-runners close at 21:30, runners (≥25 pips profit) hold until 23:00 or EMA exit
- Weekend: No trades allowed (Saturday/Sunday)
- Before Monday 01:00: No trades allowed

**Two Execution Modes:**

**Mode A: Enforcement (Scheduled at 21:30 Fri, 23:00 Mon-Thu)**
1. Fetch all open trades from OANDA API
2. For each trade, determine compliance status:
   - Saturday/Sunday → Non-compliant (close immediately)
   - Friday after 21:30 → Non-compliant (close immediately)
   - Mon-Thu after 23:00 → Non-compliant (close immediately)
   - Mon-Thu 21:30-23:00 with <25 pips profit → Non-compliant (close)
   - Mon-Thu 21:30-23:00 with ≥25 pips, no EMA exit → Compliant (runner, hold)
3. Close each non-compliant trade via `OandaClient.close_trade(trade_id, reason)`
4. Record closure in `enforcement_audit` table with trade details and P&L
5. Use Claude (Haiku) to analyze closure summary: "N trades closed, total P&L impact"
6. Send Pushover critical alert: "Trading Hours Enforcement 21:30 UTC: Closed 2 trades (EUR/USD +$45, USD/JPY -$12). Total: +$33"
7. Store complete report in `monitoring_reports` table

**Mode B: Monitoring (Scheduled every 6 hours: 00:00, 06:00, 12:00, 18:00 UTC)**
1. Fetch all open trades from OANDA API
2. Check for any trades that SHOULD have been closed but remain open (detection of missed enforcement)
3. Use Claude to interpret findings: "X trades are open outside normal hours — investigation needed"
4. Alert if violations detected
5. Store monitoring report in database

**Data Sources:**
- OANDA API: `list_open_trades()`, `get_trade_details(trade_id)`
- TradingHoursManager rules (imported from Scalp-Engine)

**Results Storage:**
```json
{
  "report_type": "trading_hours_enforcement",
  "timestamp": "2026-03-16T21:30:00Z",
  "enforcement_action": true,
  "trades_closed": [
    {
      "trade_id": "123456",
      "pair": "EUR/USD",
      "direction": "LONG",
      "entry_price": 1.0950,
      "close_price": 1.0965,
      "realized_pnl": 45.00,
      "closure_reason": "Trading window closed - non-compliant hold"
    }
  ],
  "total_pnl": 33.00,
  "alert_sent": true,
  "alert_message": "Trading Hours Enforcement 21:30 UTC: Closed 2 trades..."
}
```

---

### 2. LogAnalysisAgent

**Responsibility:** Periodic analysis of all trading activity logs to detect anomalies and identify concerning patterns.

**Data Sources:**
- Scalp-Engine RL database: `signals` table (all trades with outcomes)
- Trade-Alerts RL database: `recommendations` table (all LLM recommendations with results)
- Scalp-Engine log files: Execution logs for errors/warnings

**Execution Logic:**
1. Query signals since last analysis (default: last 24 hours)
2. Calculate metrics:
   - Total trades, wins, losses, pending
   - Win rate (%), average P&L
   - Closure reason distribution (SL %, TP %, runner exit %, time-based %)
   - Error/warning count in logs
3. Query recommendations from Trade-Alerts RL:
   - Recommendations by LLM
   - Hit rate by LLM (did recommendation hit TP, SL, or still pending?)
4. Detect anomalies:
   - Win rate dropped >20% from previous period → Flag
   - SL closure rate >70% → Flag (too many losses)
   - Error rate >10% → Flag
   - LLM accuracy divergence (one LLM suddenly <40%) → Flag
5. Use Claude (Haiku) to interpret:
   - Prompt: "Review this trading activity summary. What are the key findings? Identify concerning trends and positive patterns."
   - Output: Structured interpretation for human review
6. Send Pushover critical alert if anomalies detected
7. Store report in `monitoring_reports` table

**Report Format:**
```json
{
  "report_type": "log_analysis",
  "timestamp": "2026-03-16T23:00:00Z",
  "period": "2026-03-15 to 2026-03-16",
  "metrics": {
    "total_trades": 24,
    "wins": 15,
    "losses": 9,
    "win_rate": 0.625,
    "avg_pnl": 45.50,
    "closure_reasons": {
      "SL": 0.25,
      "TP": 0.50,
      "runner_exit": 0.15,
      "time_based": 0.10
    }
  },
  "llm_analysis": {
    "chatgpt": { "recommendations": 8, "hit_rate": 0.625 },
    "gemini": { "recommendations": 6, "hit_rate": 0.667 },
    "claude": { "recommendations": 5, "hit_rate": 0.800 }
  },
  "anomalies": [],
  "analysis": "Solid performance week. Win rate 62.5%, consistently profitable.",
  "alert_sent": false
}
```

**Schedule:** Daily at 23:00 UTC (end of trading day)

---

### 3. ProfitabilityAgent

**Responsibility:** Deep analysis of what makes trades profitable and generate specific, actionable recommendations for improvement.

**Data Sources:**
- Scalp-Engine RL database: P&L by pair, hour, regime, signal strength
- Trade-Alerts RL database: LLM accuracy and weighting

**Execution Logic:**
1. Analyze Scalp-Engine RL by dimensions:
   - **By Pair:** Which pairs have highest win rate? Which are losing?
   - **By Hour:** Which trading hours are most profitable (08:00-12:00 vs 16:00-20:00)?
   - **By Regime:** TRENDING vs RANGING vs HIGH_VOL performance
   - **By Strength:** Low vs medium vs high signal strength win rates
2. Identify patterns:
   - "EUR/USD: 68% win rate 08:00-12:00, only 35% 16:00-20:00"
   - "HIGH_VOL regime: 42% win rate (lower than TRENDING at 61%)"
   - "Strong signals (>0.7 strength): 72% win rate vs weak (<0.4): 38%"
3. Analyze Trade-Alerts RL:
   - Current LLM weights and accuracy
   - Which LLM is most reliable?
   - Which has declined recently?
4. Use Claude (Sonnet — more capable for complex analysis):
   - Prompt: "Based on this profitability analysis, generate 3-5 specific, actionable recommendations to improve trading performance. Consider pair selection, trading hour windows, regime-based strategy adjustments, and LLM weighting optimization."
   - Output: Numbered recommendations with rationale
5. Send Pushover critical alert if any metric is critically low (e.g., win rate <40%)
6. Store detailed analysis in `monitoring_reports` table

**Report Format:**
```json
{
  "report_type": "profitability",
  "timestamp": "2026-03-16T22:00:00Z",
  "period": "Week of 2026-03-09 to 2026-03-15",
  "profitability_analysis": {
    "by_pair": {
      "EUR/USD": {
        "trades": 12,
        "win_rate": 0.667,
        "avg_pnl": 52.50,
        "by_hour": {
          "08:00-12:00": { "trades": 6, "win_rate": 0.833 },
          "16:00-20:00": { "trades": 6, "win_rate": 0.500 }
        }
      }
    },
    "by_regime": {
      "TRENDING": { "trades": 18, "win_rate": 0.722 },
      "RANGING": { "trades": 8, "win_rate": 0.500 },
      "HIGH_VOL": { "trades": 5, "win_rate": 0.400 }
    }
  },
  "llm_analysis": {
    "claude": { "weight": 0.45, "accuracy": 0.800 },
    "chatgpt": { "weight": 0.35, "accuracy": 0.620 },
    "gemini": { "weight": 0.20, "accuracy": 0.580 }
  },
  "recommendations": [
    {
      "priority": 1,
      "title": "Focus EUR/USD trading on morning hours (08:00-12:00)",
      "rationale": "68% win rate in morning vs 35% afternoon. Avoid afternoon window.",
      "expected_impact": "+15% win rate if implemented"
    },
    {
      "priority": 2,
      "title": "Reduce trading in HIGH_VOL regime",
      "rationale": "Only 40% win rate in high volatility vs 72% in trends. Consider sit-out during spikes.",
      "expected_impact": "+20% overall win rate"
    },
    {
      "priority": 3,
      "title": "Increase Claude weight to 60%",
      "rationale": "Claude achieving 80% accuracy vs ChatGPT 62%. Shift more weight to better performer.",
      "expected_impact": "+5% consensus recommendation quality"
    }
  ],
  "alert_sent": false
}
```

**Schedule:** Weekly Sunday at 22:00 UTC (end of week)

---

## Database Schema

### monitoring_reports Table
```sql
CREATE TABLE monitoring_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type TEXT NOT NULL,  -- 'trading_hours', 'log_analysis', 'profitability'
    timestamp DATETIME NOT NULL,
    period_start DATETIME,
    period_end DATETIME,
    enforcement_action BOOLEAN DEFAULT 0,  -- true if trades were closed
    trades_affected TEXT,  -- JSON: list of closed trades
    total_pnl REAL,  -- P&L from enforcement actions
    findings TEXT,  -- JSON: anomalies, metrics, patterns
    analysis TEXT,  -- Claude's interpretation/recommendations
    recommendations TEXT,  -- JSON: for profitability reports
    critical BOOLEAN DEFAULT 0,  -- true if alert was sent
    alert_message TEXT,  -- Alert content if sent
    data_sources TEXT,  -- JSON: which tables/logs were queried
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (report_type) REFERENCES agents(name)
);

CREATE INDEX idx_monitoring_timestamp ON monitoring_reports(timestamp DESC);
CREATE INDEX idx_monitoring_type ON monitoring_reports(report_type);
```

### enforcement_audit Table
```sql
CREATE TABLE enforcement_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    trade_id TEXT NOT NULL,
    pair TEXT NOT NULL,
    direction TEXT NOT NULL,  -- BUY/SELL
    entry_price REAL,
    close_price REAL,
    realized_pnl REAL,
    closure_reason TEXT NOT NULL,
    closed_by TEXT DEFAULT 'Emy',
    report_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (report_id) REFERENCES monitoring_reports(id)
);

CREATE INDEX idx_audit_timestamp ON enforcement_audit(timestamp DESC);
CREATE INDEX idx_audit_pair ON enforcement_audit(pair);
```

---

## Integration with Emy

### Natural Language Interface
Users give instructions via Emy chat:

```
"Monitor trading hours daily, close any non-compliant trades, and notify me"
→ Emy creates Celery Beat schedules (21:30 Fri, 23:00 Mon-Thu)

"Review trading logs every Friday at 11 PM UTC"
→ LogAnalysisAgent added to schedule Friday 23:00

"Give me profitability recommendations weekly on Sunday"
→ ProfitabilityAgent scheduled Sunday 22:00

"Email me the weekly profitability analysis"
→ ProfitabilityAgent output piped to email when report is ready
```

### TaskRouter / DelegationEngine Integration
1. User provides instruction
2. TaskRouter parses: agent type, schedule, parameters
3. Creates Celery Beat task with schedule
4. Agent executes on schedule
5. Results stored in database
6. Pushover alerts sent for critical issues
7. User can request email or view in database

### Data Flow
```
User Instruction
    ↓
TaskRouter / DelegationEngine
    ↓
Create Celery Beat Schedule
    ↓
Agent Executes at Scheduled Time
    ├─ Fetch data (OANDA, logs, databases)
    ├─ Analyze with Claude (Haiku/Sonnet)
    ├─ Take action if needed (close trades)
    ├─ Store in monitoring_reports table
    └─ Send alert if critical
    ↓
User receives:
    • Real-time Pushover alerts
    • Email reports (on request)
    • Database records (view anytime)
```

---

## Implementation Approach

### Three Independent Tasks (Subagent-Driven Development)
Each agent is implemented as a separate task with:
1. Write failing tests (TDD)
2. Implement agent class inheriting from EMySubAgent
3. Implement core methods (execute, analyze, report)
4. Implement OANDA integration if needed
5. Implement database storage
6. Create Celery task wrapper
7. Test end-to-end

### Key Implementation Files
- `emy/agents/trading_hours_monitor_agent.py` — TradingHoursMonitorAgent
- `emy/agents/log_analysis_agent.py` — LogAnalysisAgent
- `emy/agents/profitability_agent.py` — ProfitabilityAgent
- `emy/tasks/monitoring_tasks.py` — Celery task definitions
- `emy/core/database.py` — Schema additions (monitoring_reports, enforcement_audit)
- `emy/tools/api_client.py` — Add `close_trade()` method to OandaClient
- `tests/test_trading_hours_monitor_agent.py`, etc. — Unit and integration tests

---

## Success Criteria

✅ TradingHoursMonitorAgent:
- Monitors trading hours compliance continuously
- Closes non-compliant trades at 21:30 Friday and 23:00 Mon-Thu
- Sends critical alerts with closure summary
- Stores audit trail of all closures

✅ LogAnalysisAgent:
- Analyzes trading activity daily
- Detects anomalies (win rate drops, high errors, etc.)
- Sends alerts only if critical
- Stores detailed reports in database

✅ ProfitabilityAgent:
- Generates profitability analysis by pair, hour, regime
- Analyzes LLM accuracy and weighting
- Uses Claude Sonnet to generate 3-5 specific recommendations
- Sends alerts only if metrics are critically low
- Stores actionable insights in database

✅ Integration:
- User can request monitoring via natural language
- Emy parses instructions and creates Celery Beat schedules
- All agents run autonomously on schedule
- Results flow back to user via alerts and database

---

## Testing Strategy

**Unit Tests:**
- TradingHoursMonitorAgent: compliance detection logic, closure logic
- LogAnalysisAgent: anomaly detection, metric calculation
- ProfitabilityAgent: profitability analysis, Claude prompt generation

**Integration Tests:**
- OANDA API interaction: fetch trades, close trades
- Database: store/retrieve reports
- Celery Beat: schedule creation and execution
- Claude analysis: prompt generation and parsing

**End-to-End Tests:**
- Full enforcement cycle: detect non-compliant trade → close via OANDA → store audit → send alert
- Full analysis cycle: query databases → analyze → generate insights → store report

---

## Notes

- All times are UTC unless otherwise specified
- Enforcement is autonomous (no user approval needed) — critical design choice for autonomy
- Full audit trail maintained for compliance review
- Database schema extensible for future monitoring needs
- Claude usage: Haiku for routine analysis (cheap), Sonnet for complex optimization recommendations
- All agents follow existing EMySubAgent pattern for consistency

