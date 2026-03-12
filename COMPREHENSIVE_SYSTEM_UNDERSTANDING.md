# COMPREHENSIVE SYSTEM UNDERSTANDING
## Trade-Alerts + Scalp-Engine Architecture & Dependencies

**Document Created**: March 9, 2026
**Scope**: Complete codebase analysis, dependencies, data flows, and critical constraints
**Status**: Foundation for accurate future planning

---

## EXECUTIVE SUMMARY

The Trade-Alerts system is a **sophisticated two-engine forex trading platform**:

1. **Trade-Alerts (Root)** — "The General"
   - Analyzes market data every 1-4 hours using 4 LLMs (ChatGPT, Gemini, Claude, DeepSeek)
   - Generates trading opportunities with consensus scoring
   - Learns from outcomes daily and updates LLM weights
   - Exports `market_state.json` for Scalp-Engine

2. **Scalp-Engine** — "The Sniper"
   - Reads `market_state.json` from Trade-Alerts
   - Executes trades in real-time based on LLM opportunities OR technical indicators
   - Monitors entry points continuously (every 60 seconds)
   - Manages open positions and applies risk management

**Critical Dependency**: Scalp-Engine fundamentally depends on Trade-Alerts' `market_state.json` for LLM-based trades.

---

## SYSTEM ARCHITECTURE

### Component Hierarchy

```
TRADE-ALERTS (Independent Execution)
├── Google Drive Integration
│   ├── drive_reader.py
│   ├── OAuth2 credentials
│   └── Forex tracker folder
│
├── LLM Analysis Pipeline (Parallel)
│   ├── data_formatter.py
│   ├── llm_analyzer.py (ChatGPT, Gemini, Claude, DeepSeek)
│   ├── gemini_synthesizer.py
│   └── recommendation_parser.py
│
├── Reinforcement Learning System
│   ├── trade_alerts_rl.py (Database + Evaluator + Learning Engine)
│   ├── daily_learning.py (11pm UTC learning cycle)
│   ├── trade_alerts_rl.db (SQLite)
│   └── LLM weight calculation
│
├── Market State Export
│   ├── market_bridge.py
│   ├── market_state.json (Output for Scalp-Engine)
│   └── llm_weights (Dynamic from RL system)
│
├── Price Monitoring
│   ├── price_monitor.py (OANDA live prices)
│   ├── alert_manager.py (Pushover notifications)
│   └── alert_history.py
│
└── Execution Coordination
    ├── main.py (Entry point + main loop)
    ├── scheduler.py (Analysis times)
    └── email_sender.py (Notifications)


SCALP-ENGINE (Dependent Execution)
├── Market State Reader
│   ├── state_reader.py
│   ├── market_state_api.py
│   └── Reads market_state.json (from Trade-Alerts)
│
├── Trading Strategies
│   ├── LLM_ONLY (uses Trade-Alerts opportunities)
│   ├── FISHER_H1/M15 (Fisher Transform indicators)
│   ├── DMI_H1/M15 (DMI-EMA indicators)
│   └── FT_DMI_EMA (Combined strategy)
│
├── Execution Engine (auto_trader_core.py)
│   ├── TradeExecutor (Places orders with OANDA)
│   ├── PositionManager (Trade lifecycle management)
│   └── RiskController (Position sizing)
│
├── Reinforcement Learning (Scalp-Engine specific)
│   ├── scalping_rl.py / scalping_rl_enhanced.py
│   ├── scalping_rl.db (SQLite)
│   └── Fisher/DMI signal tracking
│
├── UI & APIs
│   ├── scalp_ui.py (Streamlit monitoring)
│   ├── config_api_server.py (Config + trade sync)
│   └── Trade state persistence
│
└── OANDA Integration
    ├── oanda_client.py
    └── Live forex execution
```

---

## CRITICAL DATA FLOWS

### Main Analysis Cycle (Scheduled - every 1-4 hours)

```
Trade-Alerts/main.py (Scheduled time: 7am, 9am, 12pm, 4pm EST)
    ↓
[1] drive_reader.py
    ├── Download latest forex analysis from Google Drive
    ├── Extract raw market data
    └── Cache locally

[2] data_formatter.py
    ├── Format data for LLM consumption
    └── Prepare prompt

[3] llm_analyzer.py (PARALLEL)
    ├── ChatGPT → analysis (gpt-4)
    ├── Gemini → analysis (pro)
    ├── Claude → analysis (opus)
    └── DeepSeek → analysis (optional)

[4] gemini_synthesizer.py
    ├── Synthesize 4 analyses
    ├── Consensus detection
    └── Final recommendation

[5] recommendation_parser.py
    ├── Parse text → structured opportunities
    ├── Entry/SL/TP calculation
    └── Confidence assignment

[6] Entry Price Validation
    ├── Fetch live OANDA prices
    ├── Compare LLM entries to current market (±5%)
    └── Mark unrealistic entries

[7] trade_alerts_rl.py (Log to database)
    ├── Log all recommendations
    ├── Include entry/exit/SL targets
    └── Store in SQLite

[8] market_bridge.py (EXPORT)
    ├─ Load current LLM weights (from last learning cycle)
    ├─ Calculate consensus per opportunity
    ├─ Export market_state.json
    │  {
    │    "global_bias": "BULLISH|BEARISH",
    │    "regime": "TRENDING|RANGING",
    │    "opportunities": [...],
    │    "llm_weights": {
    │      "chatgpt": 0.25,
    │      "gemini": 0.25,
    │      "claude": 0.25,
    │      "deepseek": 0.25
    │    },
    │    "timestamp": "2026-03-09T12:00:00Z"
    │  }
    └─ Available to Scalp-Engine

[9] Email notification
    ├── Send market analysis summary
    └── Recommended opportunities

[10] price_monitor.py (Continuous - every 60 seconds)
    ├── Check if entry prices hit
    └── Send Pushover alert if hit
```

### Daily Learning Cycle (11pm UTC)

```
Daily Learning Trigger
    ↓
[1] trade_alerts_rl.py - OutcomeEvaluator
    ├── Query recommendations from last 24 hours
    ├── For each: Find matching OANDA closed trade
    ├── Mark: WIN (profit), LOSS (loss), PENDING (still open), MISSED (not traded)
    └── Store outcomes in database

[2] LLMLearningEngine
    ├── Calculate per-LLM accuracy
    │   accuracy = wins / (wins + losses)
    ├── Adjust dynamic weights based on accuracy
    └── Save to learning_checkpoints table

[3] Weights Update
    ├── New weights: {"chatgpt": 0.28, "gemini": 0.25, "claude": 0.22, "deepseek": 0.25}
    └── Available for next analysis cycle

[4] Hourly Reload
    ├── main.py reloads weights every hour
    └── Next analysis cycle picks up latest weights
```

### Scalp-Engine Execution Cycle

```
scalp_engine.py - Main Loop (Every 60 seconds)
    ↓
[1] Check Trading Mode
    ├── AUTO: Automatic execution
    ├── SEMI_AUTO: Proposals for UI approval
    └── MONITOR: Watch-only

[2] Sync with OANDA
    ├── Position_manager.sync_with_oanda()
    ├── Detect existing trades
    ├── Update active_trades dict
    ├── Save to trade_states.json
    └── Push to UI

[3] Load market_state.json
    ├── If file available: Read opportunities
    ├── If not: Skip LLM-based trades
    └── Continue with other strategies

[4] For Each Opportunity:
    ├─ Validate against current prices (±50-200 pips, ±0.5-2.0%)
    ├─ Apply per-opportunity execution_mode (LLM_ONLY, FISHER, DMI, etc.)
    ├─ Check trading hours enforcement
    ├─ Check max_runs limit (auto-reset if no open position)
    ├─ Check duplicate blocking (RED FLAG once per 15 min)
    ├─ Call position_manager.open_trade()
    │  └─ TradeExecutor.open_trade()
    │     └─ OANDA API → Place order
    └─ If trade opened:
       └─ Add to active_trades dict

[5] Monitor Active Positions
    ├─ Check for SL triggers (auto-execution by OANDA)
    ├─ Check for TP triggers (auto-execution by OANDA)
    ├─ Update position status
    └─ Sync back to OANDA

[6] Technical Indicator Scanning
    ├─ Fisher Transform (H1, M15)
    ├─ DMI-EMA alignment (H1, M15)
    ├─ EMA Ribbon signals
    └─ If signal triggered: Execute based on strategy mode
```

---

## CRITICAL DEPENDENCIES

### Trade-Alerts Dependencies

| Component | Type | Dependency | Impact if Missing |
|-----------|------|-----------|------------------|
| **Google Drive** | External | OAuth2 credentials + Forex tracker folder | Cannot download analysis files → No opportunities generated |
| **ChatGPT API** | External | OpenAI API key | 1/4 LLM unavailable, consensus drops from /4 to /3 |
| **Gemini API** | External | Google API key | 1/4 LLM unavailable, consensus drops from /4 to /3 |
| **Claude API** | External | Anthropic API key | 1/4 LLM unavailable, consensus drops from /4 to /3 |
| **OANDA API** | External | OANDA token (for price checks) | Cannot validate entry prices → Unrealistic entries not filtered |
| **RL Database** | Internal | `/var/data/trade_alerts_rl.db` or `data/trade_alerts_rl.db` | Cannot log recommendations → No learning cycle |
| **market_state.json** | Internal | Write permission to root dir | Cannot export for Scalp-Engine → Scalp-Engine has no LLM trades |
| **Email/SMTP** | External | Gmail OAuth + SMTP settings | Cannot send notifications (non-critical) |
| **Pushover API** | External | Pushover token | Cannot send price alerts (non-critical) |

### Scalp-Engine Dependencies

| Component | Type | Dependency | Impact if Missing |
|-----------|------|-----------|------------------|
| **market_state.json** | Trade-Alerts | Updated every 1-4 hours | LLM-based trades unavailable; technical strategies still work |
| **OANDA API** | External | OANDA token + account ID | Cannot place orders or check prices → System non-functional |
| **RL Database** | Internal | `/var/data/scalping_rl.db` or `Scalp-Engine/data/scalping_rl.db` | Cannot track Fisher/DMI signal performance (non-critical) |
| **Config API** | Internal | Running on Render (for Render deployment) | Trades not synced to UI; local operation still works |
| **Trading Hours Manager** | Internal | Code logic (no external dep) | May trade during closed hours (critical for live trading) |

### Render Deployment Specific

| Component | Type | Issue | Impact |
|-----------|------|-------|--------|
| **Persistent Disk** | Render | Each service gets own disk (/var/data) | RL databases not shared between services if multiple instances |
| **Config API** | Render Service | HTTP server on separate service | Market state needs to be served via API; local file not accessible |
| **Log Sync** | Internal | log_sync.py pushes logs to config-api | If config-api down, logs not synced to central location |
| **ENV Variable** | Render Config | Set ENV=production | Logger detects Render and uses /var/data path automatically |

---

## EXECUTION MODES & STRATEGY

### Scalp-Engine Trading Modes

```
TRADING_MODE = "AUTO" | "SEMI_AUTO" | "MONITOR"

AUTO Mode:
├─ Opportunities automatically executed
├─ Minimal user intervention
├─ Risk: No approval before trade
└─ Used for: Fully automated trading

SEMI_AUTO Mode:
├─ Opportunities proposed in UI
├─ User clicks to approve/reject
├─ Risk: Delayed execution (seconds/minutes)
└─ Used for: Controlled automation

MONITOR Mode:
├─ Watch only, no execution
├─ All strategies run, trades not placed
├─ Risk: None (paper trading)
└─ Used for: Testing/verification
```

### Per-Opportunity Execution Strategies

```
Each opportunity can use a different strategy:

LLM_ONLY
├─ Execute Trade-Alerts opportunities directly
└─ No technical analysis required

FISHER_H1_CROSSOVER
├─ Use Fisher Transform on 1H timeframe
├─ Only trade when Fisher confirms signal
└─ Ignores LLM opportunities

FISHER_M15_CROSSOVER
├─ Use Fisher Transform on 15M timeframe
└─ Tighter, faster signals

DMI_H1_CROSSOVER
├─ Use DMI-EMA alignment on 1H
└─ Waits for DMI confirmation

DMI_M15_CROSSOVER
├─ Use DMI-EMA alignment on 15M
└─ Faster execution

FT_DMI_EMA_ONLY
├─ Combined Fisher + DMI-EMA strategy
├─ Requires alignment of multiple indicators
└─ Higher confidence, fewer trades
```

### Execution Enforcer Logic (execution_mode_enforcer.py)

```
For each opportunity in market_state.json:

[1] Get directive (EXECUTE_NOW, PLACE_PENDING, REJECT, etc.)
    ├─ Check max_runs (per-opportunity limit, default=1)
    ├─ Check for duplicates (same pair/direction in last 15 min)
    ├─ Check consensus (requires min_consensus_level, default=2)
    ├─ Check staleness (entry within tolerance)
    ├─ Check trading hours (Mon-Fri, 17:00-21:00 UTC)
    └─ Return directive

[2] Execute or Propose
    ├─ If EXECUTE_NOW: Place order immediately (AUTO/SEMI_AUTO)
    ├─ If PLACE_PENDING: Modify pending order (SEMI_AUTO)
    ├─ If REJECT: Skip this opportunity
    ├─ If MONITOR: Log but don't trade (MONITOR mode)
    └─ Store execution record
```

---

## CRITICAL CONSTRAINTS & GOTCHAS

### Constraint 1: market_state.json is the Single Source of Truth

**What it means**:
- Scalp-Engine reads market_state.json to get LLM-based opportunities
- If Trade-Alerts stops or market_state.json becomes stale, LLM trades stop

**Implication**:
- Suspending Trade-Alerts on Render immediately stops LLM-based trades
- But technical strategies (Fisher, DMI-EMA) can still run independently
- **CRITICAL**: Scalp-Engine needs a way to fetch market_state.json (local file OR HTTP API)

**Current Status on Render**:
- Trade-Alerts writes to /var/data/market_state.json
- Scalp-Engine reads via market_state_server.py (HTTP API)
- If Trade-Alerts service stops → No updates to market_state.json

---

### Constraint 2: RL Database Paths Vary by Environment

**Local Development**:
- Trade-Alerts: `data/trade_alerts_rl.db`
- Scalp-Engine: `Scalp-Engine/data/scalping_rl.db`

**Render Production**:
- Both: `/var/data/trade_alerts_rl.db` (if ENV=production set)
- But EACH SERVICE has its OWN persistent disk!
- Services can't share /var/data databases directly

**Implication**:
- Local: Both services can access shared DB files
- Render: Each service has isolated disk; sync required for shared data

**Current Status**:
- log_sync.py pushes logs from services to config-api
- But RL databases not synced between services
- Learning cycle on Trade-Alerts; Scalp-Engine RL is separate

---

### Constraint 3: Google Drive Authentication Requires New Credentials

**Problem** (Mar 9, 2026):
- Original credentials (for Forex Tracker) don't work for Trade-Alerts
- "invalid_client: The OAuth client was not found"
- **Required**: Create separate OAuth app for Trade-Alerts-OAuth

**Solution Applied**:
- New OAuth app created
- New credentials in .env
- New refresh token generated via get_refresh_token.py

**Current Status**:
- ✅ New credentials configured
- ✅ drive_reader.py can authenticate
- ✅ Trade-Alerts can download from Google Drive

---

### Constraint 4: Consensus Denominator Changes Dynamically

**What it means**:
```
If 4 LLMs available: consensus shows as /4 (need 2/4 minimum)
If 3 LLMs available (Claude down): consensus shows as /3 (need 2/3 minimum)
If 2 LLMs available: consensus shows as /2 (need 2/2 minimum - all must agree!)
```

**Implication**:
- If Claude/Gemini API down, opportunities become harder to trade
- Consensus threshold effectively rises as LLMs drop
- With only 1 LLM, opportunities can't be traded (no consensus possible)

**Current Status** (Mar 9, 2026):
- 4 LLMs available (ChatGPT, Gemini, Claude, DeepSeek)
- Minimum consensus: 2 LLMs
- Base LLMs: ['chatgpt', 'gemini', 'claude']
- Deepseek optional (parser broken as of Feb 28)

---

### Constraint 5: Scalp-Engine Resilience to Trade-Alerts Downtime

**Scenario**: Trade-Alerts on Render is suspended

**What Still Works**:
- ✅ Technical strategies (Fisher, DMI-EMA, EMA Ribbon)
- ✅ Monitoring existing open positions
- ✅ SL/TP auto-execution by OANDA
- ✅ Price monitoring

**What Stops**:
- ❌ LLM-based trades (market_state.json not updated)
- ❌ LLM consensus scoring
- ❌ Market regime analysis

**Implication**:
- System can continue trading technical signals alone
- But loses macro intelligence from LLMs
- Risk: Technical-only trades may ignore broader market context

---

### Constraint 6: Daily Learning Cycle Dependencies

**For daily_learning.py to work**:

1. ✅ trade_alerts_rl.db must exist and be accessible
2. ✅ OutcomeEvaluator must be able to query OANDA closed trades
3. ✅ OANDA API must be working
4. ✅ Recommendations must have been logged in last 24 hours
5. ✅ RL database schema must have all required columns

**If any fails**:
- Learning cycle skipped or errors out
- LLM weights not recalculated
- Old weights continue to be used
- System degrades gracefully (weights don't get worse, just stale)

**Current Status** (Mar 9, 2026):
- ✅ All dependencies met
- ⚠️ DeepSeek learning may be broken (parser issue not outputting JSON)
- ⚠️ Claude API unavailable (credits exhausted)
- Impact: Only ChatGPT + Gemini data for learning (but system still works with 2 LLMs)

---

## SESSION CONTEXT & CURRENT STATE

### What Just Happened (Mar 9, 2026)

1. **New OAuth Credentials Created**
   - New Trade-Alerts-OAuth app in Google Cloud
   - New credentials configured in .env
   - Refresh token generated
   - ✅ Google Drive authentication working

2. **System Status When Started**
   - ✅ Trade-Alerts running locally (python main.py)
   - ✅ OAuth2 authenticated successfully
   - ✅ Drive reader initialized
   - ✅ All components initialized
   - ✅ Main loop running, next analysis scheduled

3. **Trade-Alerts Suspended on Render** (to avoid conflicts)
   - Local instance now has exclusive access to Google Drive
   - market_state.json being written locally
   - Scalp-Engine on Render cannot read local market_state.json

4. **Scalp-Engine on Render Now Broken**
   - Getting database errors: "no such column: pnl_pips"
   - Cannot read local Trade-Alerts' market_state.json
   - Losing LLM opportunity pipeline

---

## WHAT WENT WRONG & WHY

**The Mistake**: I suspended Trade-Alerts without realizing Scalp-Engine depends on it for:
1. market_state.json updates (LLM opportunities)
2. Shared database access (if using same /var/data)
3. Coordinated execution

**Correct Approach**:
- Run Trade-Alerts + Scalp-Engine TOGETHER (not one at a time)
- Both on Render OR both locally
- Not mixed (local Trade-Alerts + Render Scalp-Engine)

---

## CORRECT PATHS FORWARD

### Option A: Run BOTH on Render (Current Production Setup)
**Pros**:
- Both services coordinated on same platform
- Both access same /var/data for persistent storage
- market_state.json immediately available
- This is the tested, working configuration

**Cons**:
- No local visibility during development
- Harder to debug locally
- But it's stable and working

**Action**:
- ✅ Resume Trade-Alerts on Render
- ✅ Scalp-Engine continues running
- ✅ Monitor via Render logs
- ✅ Test Phase 1 remotely

---

### Option B: Run BOTH Locally (Development Testing)
**Pros**:
- Full local visibility
- Easy to debug
- Can run in MONITOR mode safely

**Cons**:
- Requires local OANDA access
- Both must use same paths
- More setup complexity

**Action**:
- Run Trade-Alerts locally (already started)
- Run Scalp-Engine locally (separate terminal)
- Both read/write to same local directories
- Set TRADING_MODE=MONITOR for safety

---

### Option C: Mixed (NOT RECOMMENDED)
**Why it doesn't work**:
- Local Trade-Alerts writes to C:\...\market_state.json (Windows)
- Render Scalp-Engine can't access Windows filesystem
- market_state.json updates never reach Render
- This is why it failed

---

## RECOMMENDED NEXT STEP

**Resume Trade-Alerts on Render immediately** to restore the system to working state.

Then for **Phase 1 Testing (Verify SL/TP Works)**:
- Keep both services running on Render
- Monitor via Render logs
- Verify that at least one trade opens with proper SL/TP
- If issues, we can then decide to move to local testing

This minimizes risk while ensuring the system is functional.

---

## SUMMARY OF CRITICAL INSIGHTS

1. **Trade-Alerts → market_state.json → Scalp-Engine** is the core architecture
2. **Both services must run on the same platform** (both local OR both Render, not mixed)
3. **market_state.json is the single source of truth** for LLM-based opportunities
4. **Technical strategies (Fisher, DMI) work independently** even if Trade-Alerts is down
5. **Scalp-Engine resilience** depends on sync_with_oanda() running continuously
6. **Google Drive credentials** required complete refresh (new OAuth app)
7. **Consensus denominator changes dynamically** based on available LLMs
8. **Database isolation on Render** requires explicit sync mechanisms
9. **Daily learning cycle** improves LLM weights but isn't critical for trading
10. **Configuration is complex but modular** — changes to one component don't break others if dependencies are met

---

**This document provides the foundation for accurate, safe planning of Phase 1 (SL/TP Verification) and beyond.**
