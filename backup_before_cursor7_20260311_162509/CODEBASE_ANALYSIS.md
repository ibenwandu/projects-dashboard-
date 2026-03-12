# Trade-Alerts Codebase Analysis
**Date**: February 22, 2026
**Purpose**: Complete architectural documentation for safe modifications

---

## 1. SYSTEM ARCHITECTURE OVERVIEW

### High-Level Data Flow

```
Trade-Alerts (Root)
├── main.py (Main orchestrator)
│   ├── Drive Reader → Reads .txt/.json analysis from Google Drive
│   ├── Data Formatter → Converts raw data to structured format
│   ├── LLM Analyzer → Sends to ChatGPT, Gemini, Claude in parallel
│   ├── Gemini Synthesizer → Creates final recommendation from all LLMs
│   ├── Recommendation Parser → Extracts trades from LLM text
│   ├── Price Monitor → Gets live OANDA prices
│   ├── RL System (trade_alerts_rl.py) → Logs recommendations + evaluates outcomes
│   ├── Learning Engine → Calculates LLM weights based on performance
│   ├── Market Bridge → Exports market_state.json
│   └── Email Sender → Sends recommendations
│
└── market_state.json (Communication bridge)
    └── Scalp-Engine (Sub-directory)
        ├── scalp_engine.py (Main auto-trader loop)
        ├── auto_trader_core.py (Trade execution logic)
        ├── risk_manager.py (Position sizing)
        └── src/ (Supporting modules)
            └── execution/
                ├── opportunity_id.py (Stable ID generation)
                └── execution_mode_enforcer.py (Per-opportunity modes)
```

### Data Exchange Between Systems

1. **Trade-Alerts → Scalp-Engine**: `market_state.json`
   - Contains: opportunities, global_bias, regime, llm_weights, consensus
   - Updated: Every analysis cycle (2am, 4am, 7am, 9am, 11am, 12pm, 4pm EST)

2. **Scalp-Engine → OANDA**: Real trade execution via OANDA API
   - Creates market/limit orders with stop losses and take profits

3. **OANDA → RL System**: Closed trade outcomes
   - Used for evaluating recommendation accuracy
   - Input for LLM weight calculations

---

## 2. REINFORCEMENT LEARNING SYSTEM (Critical - Recently Broken)

### Location
`src/trade_alerts_rl.py` (1,860+ lines)

### Core Components

#### A. RecommendationDatabase (Lines 264-620)
**Purpose**: Central SQLite database for tracking all recommendations

**Schema**:
```sql
recommendations (
  id, timestamp, date_generated,
  llm_source (chatgpt|gemini|claude|synthesis|deepseek),
  pair, direction (LONG|SHORT),
  entry_price, stop_loss, take_profit_1, take_profit_2,
  position_size_pct, confidence,
  timeframe (INTRADAY|SWING),
  outcome (WIN_TP1|WIN_TP2|LOSS_SL|NEUTRAL|PENDING|MISSED),
  exit_price, pnl_pips, bars_held,
  max_favorable_pips, max_adverse_pips,
  evaluated (0|1)
)

llm_performance (
  timestamp, llm_source, pair, timeframe,
  total_recommendations, total_evaluated,
  win_rate, avg_pnl_pips, profit_factor,
  avg_bars_to_tp, avg_bars_to_sl, accuracy_weight
)

learning_checkpoints (
  timestamp,
  chatgpt_weight, gemini_weight, claude_weight,
  synthesis_weight, deepseek_weight,
  total_recommendations, total_evaluated,
  overall_win_rate, notes
)

consensus_analysis (
  timestamp, consensus_type, win_rate,
  sample_size, avg_pnl_pips
)
```

**Key Methods**:
- `log_recommendation(rec: Dict)` - Line 380: Logs new recommendations
  - Validates entry price against current market (±50-200 pips depending on timeframe)
  - Returns recommendation ID or None if duplicate

- `update_outcome(rec_id, outcome_data)` - Line 512: Marks recommendation as evaluated

- `get_pending_recommendations()` - Line 483: Gets recs waiting evaluation (>4 hrs old)

- `get_llm_performance(llm_source, pair)` - Line 538: Gets performance data by LLM

**Important**: Database auto-detects if running on Render (persistent disk `/var/data/`) or locally (`data/`)

#### B. EntryPriceValidator (Lines 145-262)
**Purpose**: Validates that LLM entry prices are realistic

**Logic**:
- INTRADAY trades: Entry within 50 pips or 0.5% of current
- SWING trades: Entry within 200 pips or 2.0% of current
- Marks unrealistic entries with confidence='UNREALISTIC' for tracking

**Used By**: `log_recommendation()` to filter bad LLM outputs

#### C. RecommendationParser (Lines 624-1696)
**Purpose**: Parses LLM text output into structured recommendations

**Complexity**: High - supports 7 different text patterns for different LLMs
- Pattern 1: ChatGPT "Currency Pair:" format
- Pattern 2-7: Various Gemini, Claude formats

**Key Method**: `_parse_recommendations(text, llm_source, timestamp, filename)` - Line 854
- Returns list of Dict with: pair, direction, entry_price, stop_loss, take_profit_1, etc.
- Uses regex patterns to extract trade details
- Normalizes LLM source names (ChatGPT→chatgpt, etc.)

**Risk**: If LLM output format changes, parser may not extract trades correctly

#### D. LLMLearningEngine (Lines 1699-1857)
**Purpose**: Calculates dynamic LLM weights based on performance

**Key Method**: `calculate_llm_weights()` - Line 1705
```python
For each LLM:
  1. Get evaluated recommendations from database
  2. Calculate win_rate = wins / evaluated_trades
  3. Count MISSED trades and apply penalty: 1.0 - (missed_rate * 0.5)
  4. Calculate profit_factor = total_wins / total_losses
  5. accuracy_score = (win_rate * 0.6) + (min(PF/2, 0.5) * 0.4)
  6. accuracy_score *= missed_penalty
  7. weight = max(accuracy_score, 0.05)  [minimum 5%]
Normalize all weights to sum to 1.0
```

**Critical**: If this calculation is wrong, bad LLMs won't be penalized

---

## 3. MAIN SYSTEM (main.py - Lines 1-249)

### Initialization Sequence
```python
__init__():
  1. Load environment variables (.env)
  2. Initialize logger
  3. Build components (drives, formatters, LLMs, etc.)
  4. Initialize RL database and learning engine
  5. Load initial LLM weights: self.llm_weights = self._load_llm_weights()
  6. Initialize state variables
```

**Important**: Line 96 initializes RL with `validate_entries=True` (entry price validation enabled)

### Main Loop (run())
```python
while True:
  1. Check if it's time for analysis (scheduler.should_run_analysis)
  2. If yes, run_analysis():
     a. Fetch files from Google Drive
     b. Format data
     c. Send to all LLMs in parallel
     d. Synthesize responses
     e. Parse recommendations
     f. Monitor entry prices
     g. Log to RL database
     h. Export market_state.json
     i. Send email
  3. Check if it's time to learn (daily @ 11pm UTC)
  4. If yes, reload LLM weights (Line 102: Hourly weight reload check)
  5. Sleep for check_interval seconds (default 60)
```

**Constants**:
- `WEIGHT_RELOAD_INTERVAL = 3600` (Line 56): Reload weights every hour
- `LEARNING_CHECK_INTERVAL = 3600` (Line 57): Check learning trigger every hour
- `STATUS_LOG_INTERVAL = 10` (Line 55): Log status every 10 checks

**Key Method**: `_load_llm_weights()` - Line 189
- Calls `self.learning_engine.calculate_llm_weights()`
- Falls back to default 0.25 weights if learning has <5 samples per LLM

---

## 4. MARKET BRIDGE (market_bridge.py)

### Purpose
Converts Trade-Alerts recommendations into `market_state.json` for Scalp-Engine

### Data Output Format
```json
{
  "timestamp": "ISO8601",
  "global_bias": "BULLISH|BEARISH|NEUTRAL",
  "regime": "TRENDING|RANGING|HIGH_VOL",
  "opportunities": [
    {
      "pair": "EUR/USD",
      "direction": "LONG",
      "entry": 1.0850,
      "exit": 1.0900,
      "stop_loss": 1.0800,
      "confidence": 0.85,
      "source": "synthesis",
      "consensus": 0.75
    }
  ],
  "llm_weights": {
    "chatgpt": 0.25,
    "gemini": 0.25,
    "claude": 0.25,
    "synthesis": 0.25
  },
  "consensus": {
    "EUR/USD_LONG": { "agreement": 3, "sources": ["chatgpt", "gemini", "claude"] }
  }
}
```

### Location
`src/market_bridge.py`

**Key Method**: `export_market_state()` - Line 103
- Normalizes all opportunities to USD exposure (handles USD as base vs quote)
- Calculates global bias from opportunity consensus
- Exports to either file (`market_state.json`) or API

---

## 5. SCALP-ENGINE (Execution System)

### Architecture
```
Scalp-Engine/
├── scalp_engine.py (Main loop - 200+ lines)
├── auto_trader_core.py (Trade execution - 800+ lines)
├── risk_manager.py (Position sizing)
└── src/
    ├── execution/
    │   ├── opportunity_id.py (Stable opportunity IDs)
    │   ├── execution_mode_enforcer.py (Per-opportunity trading modes)
    │   └── semi_auto_controller.py
    └── indicators/
        ├── fisher_transform.py
        └── dmi_analyzer.py
```

### Key Components

#### A. ScalpEngine (Lines 67-200 of scalp_engine.py)
**Purpose**: Main trading loop

**Key Features**:
- Reads `market_state.json` for opportunities
- Monitors entry prices continuously
- Executes trades based on trading mode (MONITOR, MANUAL, AUTO)

#### B. TradeConfig (auto_trader_core.py, Line 129)
**Configuration dataclass**:
```python
@dataclass
class TradeConfig:
  trading_mode: TradingMode  # MANUAL|SEMI_AUTO|AUTO
  stop_loss_type: StopLossType  # FIXED|TRAILING|BE_TO_TRAILING|ATR_TRAILING|etc.
  execution_mode: ExecutionMode  # MARKET|RECOMMENDED
  max_open_trades: int = 5
  max_daily_loss: float = 500.0
  auto_trade_llm: bool = True
  auto_trade_fisher: bool = True
  auto_trade_ft_dmi_ema: bool = True
  auto_trade_dmi_ema: bool = True
```

#### C. ManagedTrade (auto_trader_core.py, Line 179)
**Represents a single trade**:
```python
@dataclass
class ManagedTrade:
  trade_id: str  # OANDA trade ID
  pair: str
  direction: str  # LONG|SHORT
  entry_price: float
  stop_loss: float
  take_profit: Optional[float]
  units: float
  state: TradeState  # PENDING|OPEN|AT_BREAKEVEN|TRAILING|CLOSED_WIN|etc.
```

### Stop Loss Types (auto_trader_core.py, Lines 84-94)
1. **FIXED**: Standard fixed stop loss
2. **TRAILING**: Immediate trailing (hard_trailing_pips)
3. **BE_TO_TRAILING**: Fixed → Breakeven → Trailing
4. **ATR_TRAILING**: ATR-based dynamic trailing (atr_multiplier_low_vol/high_vol)
5. **AI_TRAILING**: Deprecated (alias for ATR_TRAILING, kept for backward compatibility)
6. **STRUCTURE_ATR_STAGED**: FT-DMI-EMA specialized (structure+ATR entry, BE +1R, partial +2R, trail +3R)
7. **STRUCTURE_ATR**: LLM/Fisher specialized (structure+ATR entry, BE +1R, trail to 1H EMA 26)

### Critical Issue: Stop Loss Coverage
**Current Status**: 0% of trades have stop losses!
- OANDA trades show no SL parameters
- Execution logic accepts trades without SLs
- System relies entirely on manual exit decisions

---

## 6. CRITICAL DATA FLOW POINTS

### A. Recommendation Logging (main.py → RL Database)
**Lines 450-500 (main.py)**:
```python
# After parsing recommendations from LLMs
for rec in opportunities:
  rec_id = self.rl_db.log_recommendation(rec)
  # rec must contain: timestamp, llm_source, pair, direction,
  #                  entry_price, stop_loss (validated if enabled)
```

**Validation**: `validate_entries=True` at line 96 means:
- Entry prices are checked against current market
- Unrealistic entries marked with confidence='UNREALISTIC'
- Still logged (not rejected) but flagged for learning

### B. Outcome Evaluation
**Lines 512-536 (trade_alerts_rl.py)**:
```python
# After trade closes on OANDA
update_outcome(rec_id, {
  'outcome': 'WIN_TP1|WIN_TP2|LOSS_SL|MISSED',
  'exit_price': float,
  'pnl_pips': float,
  'bars_held': int,
  'max_favorable_pips': float,
  'max_adverse_pips': float,
  'timestamp': ISO8601
})
```

**Missing**: Currently no code automatically evaluates closed OANDA trades!
- This is likely WHY RL system is broken
- Need to implement evaluation loop

### C. Weight Reload
**Line 101 (main.py)**:
```python
# Every WEIGHT_RELOAD_INTERVAL (3600 seconds = 1 hour)
self.llm_weights = self._load_llm_weights()
```

**Critical**: Weights only reload hourly
- Force reload required after manual learning run
- Requires restarting main.py to apply immediately

### D. Market State Export
**Line 150+ (main.py)**:
```python
# After all LLM analysis complete
bridge = MarketBridge()
bridge.export_market_state(
  opportunities=self.opportunities,
  synthesized_text=final_synthesis,
  llm_weights=self.llm_weights,
  all_opportunities=llm_recommendations
)
# Writes to: market_state.json (or API if configured)
```

---

## 7. DATABASE SCHEMA CRITICAL DETAILS

### recommendations table (Lines 278-314)
**UNIQUE constraint** (Line 312):
```sql
UNIQUE(timestamp, llm_source, pair, direction, entry_price)
```

**Impact**: Identical recommendations from same LLM are treated as duplicates
- Same timestamp + LLM + pair + direction + entry = INSERT OR IGNORE (skipped)
- Different entry_price = treated as new recommendation

### learning_checkpoints table (Lines 346-358)
**Migration Issue** (Lines 373-376):
```python
try:
  conn.execute("ALTER TABLE learning_checkpoints ADD COLUMN deepseek_weight REAL")
except sqlite3.OperationalError:
  pass  # Column already exists
```

**Only has deepseek_weight column added via migration**
- Older databases may be missing this column
- Affects weight saving if deepseek is used

### Evaluated Flag (Line 307)
```sql
evaluated INTEGER DEFAULT 0
```

**Critical for filtering**:
- `get_pending_recommendations()` only returns rows with `evaluated=0`
- Must set `evaluated=1` when calling `update_outcome()`
- If not set, recommendations stay "pending" forever

---

## 8. KNOWN ISSUES & RECENT BREAKAGE

### Issue 1: RL System Broken (Primary Reason for Session)
**Symptoms**:
- trade_alerts_review shows 0 recommendations despite system running
- RL database on Render is populated, but local database is empty
- LLM weights not updating

**Root Causes**:
1. **No outcome evaluation loop**:
   - OANDA trades close, but RL database never gets outcomes
   - Recommendations stay PENDING forever
   - Learning engine never calculates weights properly

2. **Database location mismatch**:
   - Trade-Alerts on Render: writes to `/var/data/trade_alerts_rl.db`
   - Local system: reads from `data/trade_alerts_rl.db` (empty)
   - Syncing not working

3. **Weight reload timing**:
   - Weights only reload hourly
   - If you fix RL, changes won't apply for up to 60 minutes

**Fix Required**:
- Implement outcome evaluation loop in main.py (check OANDA closed trades daily)
- Map OANDA closed trade results back to RL database recommendations
- Ensure local database syncs from Render

### Issue 2: Stop Loss Coverage at 0%
**Symptom**: All 419 demo trades have no stop losses
**Root Cause**: OANDA trades executed without SL parameters
**Impact**: Single trade can wipe out entire account
**Status**: CRITICAL - blocks live trading

### Issue 3: Parser Fragility
**Complexity**: 7 different regex patterns for LLM formats
**Risk**: If LLM output format changes slightly, parser may miss trades
**Mitigation**: Test parser with each LLM output format

### Issue 4: Direction Bias (68-100% SHORT when trending UP)
**Indicates**: LLM recommendations are systematically wrong in certain conditions
**Root Cause**: Unknown (need logs from loss streaks to diagnose)
**Related to**: Market regime detection not implemented

---

## 9. SAFE MODIFICATION POINTS

### A. Can Safely Modify Without Breaking System:

1. **LLM Weights Formula** (Lines 1705-1777)
   - Adjust win_rate multiplier (currently 0.6)
   - Adjust profit_factor multiplier (currently 0.4)
   - Add/remove LLM sources
   - Safe because: Only affects weight calculation, no schema changes

2. **Entry Price Validation Thresholds** (Lines 227-238)
   - INTRADAY max_distance_pips (currently 50)
   - SWING max_distance_pips (currently 200)
   - Safe because: Only filters logging, doesn't break execution

3. **Market State Export Logic** (Lines 103-200)
   - USD exposure calculation
   - Bias/regime determination
   - Opportunity filtering
   - Safe because: Output-only, doesn't affect input systems

4. **Scalp-Engine Configuration** (TradeConfig dataclass)
   - Stop loss type selection
   - Position sizing
   - Daily loss limits
   - Safe because: Runtime configuration, no database changes

### B. MUST NOT MODIFY Without Careful Planning:

1. **RecommendationDatabase schema** (Lines 278-378)
   - Any column additions/changes require migration
   - Affects all code using `log_recommendation()` and `update_outcome()`
   - High risk: Data corruption possible

2. **Recommendation logging logic** (Lines 380-481)
   - UNIQUE constraint on (timestamp, llm_source, pair, direction, entry_price)
   - If you change this, duplicates behavior changes
   - Risk: May create duplicate records or miss recommendations

3. **LLM source normalization** (Lines 768-778)
   - Changes affect which recommendations are grouped together
   - Risk: Split one LLM into multiple sources or vice versa

4. **Parser regex patterns** (Lines 859-941)
   - 7 patterns must work together without overlap
   - Changes may miss trades or extract wrong fields
   - Risk: Silent failures where trades aren't parsed

5. **Market Bridge data structure** (market_state.json format)
   - Scalp-Engine expects specific fields
   - Changes break opportunity execution
   - Risk: Scalp-Engine can't read market state

---

## 10. RISK AREAS TO AVOID

### High-Risk Modifications

1. **Database schema changes**
   - Requires migration scripts
   - Can cause data loss
   - Affects all downstream analysis

2. **Recommendation parser changes**
   - 7 patterns with complex regex
   - Test thoroughly with real LLM outputs
   - One mistake = trades silently missed

3. **Weight calculation formula**
   - Small changes in formula → large changes in LLM behavior
   - Always A/B test on historical data first

4. **Stop loss logic modifications**
   - Currently at 0% coverage (broken)
   - Must implement carefully to avoid unintended behavior
   - Test in MONITOR mode for 48+ hours first

5. **Market state export format**
   - Scalp-Engine depends on exact JSON structure
   - Changes break opportunity execution
   - Must coordinate with Scalp-Engine when changing

### Low-Risk Modifications

1. Adding new LLM sources (if parser supports format)
2. Adjusting thresholds (max_distance_pips, missed_rate penalty)
3. Adding new metrics/logging
4. Scalp-Engine configuration (TradeConfig)
5. Email formatting

---

## 11. TESTING CHECKLIST BEFORE CHANGES

Before modifying any core logic:

```
1. BACKUP
   [ ] Export current RL database
   [ ] Git commit before changes

2. UNDERSTAND
   [ ] Read all related code sections
   [ ] Trace data flow through all affected components
   [ ] Identify all callers of modified functions

3. DESIGN
   [ ] Write out the change clearly
   [ ] Document what you're changing and why
   [ ] Identify potential side effects

4. IMPLEMENT
   [ ] Make minimal change (don't refactor unrelated code)
   [ ] Add logging to track behavior
   [ ] Test locally first if possible

5. TEST
   [ ] Run existing tests (if any)
   [ ] Test with sample data
   [ ] Monitor logs for errors
   [ ] Check database for data corruption

6. VALIDATE
   [ ] Verify recommendation logging still works
   [ ] Verify market state export is valid
   [ ] Check LLM weights are calculated correctly
   [ ] Confirm no silent failures

7. MONITOR
   [ ] Run for 24+ hours if possible
   [ ] Check that LLM analysis completes fully
   [ ] Verify Scalp-Engine can read market state
   [ ] Confirm no errors in logs
```

---

## 12. KEY FILE REFERENCE

| File | Purpose | Lines | Risk Level |
|------|---------|-------|-----------|
| main.py | Main orchestrator | 249+ | HIGH - touches everything |
| src/trade_alerts_rl.py | RL system | 1860 | CRITICAL - recently broken |
| src/market_bridge.py | Bridge to Scalp-Engine | 300+ | HIGH - output format critical |
| src/llm_analyzer.py | Multi-LLM calls | 200+ | MEDIUM - API calls only |
| src/recommendation_parser.py | Regex parsing | 500+ | HIGH - complex patterns |
| Scalp-Engine/auto_trader_core.py | Trade execution | 800+ | CRITICAL - 0% stop losses |
| Scalp-Engine/scalp_engine.py | Main loop | 500+ | HIGH - orchestrates execution |
| src/scheduler.py | Analysis scheduling | 100+ | LOW - config only |
| src/email_sender.py | Email notifications | 100+ | LOW - output only |
| src/price_monitor.py | Live prices | 200+ | MEDIUM - OANDA API |

---

## SUMMARY

**Key Takeaway**: The system is architecturally sound but has critical implementation gaps:

1. ✅ **Working**: LLM analysis pipeline, Market state export, Basic execution
2. ❌ **Broken**: RL outcome evaluation, Stop loss implementation, Market regime detection
3. ⚠️ **Fragile**: Recommendation parser (7 complex patterns), Weight calculation formula

**Before making ANY changes**:
1. Understand the data flow end-to-end
2. Know all callers of the function you're modifying
3. Backup the database
4. Test with monitoring enabled
5. Verify no silent failures

---

**Created**: February 22, 2026 at 23:50 EST
**Last Updated**: (Keep this file updated as you make changes)
