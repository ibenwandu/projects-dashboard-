# Codebase Comparison: Original vs Current
**Date**: February 22, 2026
**Purpose**: Identify what changed and why RL system broke

---

## 1. ORIGINAL SYSTEM (Trade-Alerts_backup)

### Working Architecture (Original)
```
main.py:
  1. Load environment + components
  2. Every analysis cycle:
     - Fetch files from Google Drive
     - Analyze with LLMs
     - Synthesize recommendations
     - Parse and extract opportunities
     - Log recommendations to RL database (SIMPLE)
  3. Every day @ 11pm UTC:
     - Call run_daily_learning()
       ├── Get pending recommendations (4+ hours old)
       ├── For each: evaluator.evaluate_recommendation(rec)
       ├── Update outcome in database
       ├── Recalculate LLM weights
       └── Reload weights in main loop

daily_learning.py:
  1. Get pending recommendations from database
  2. For EACH recommendation:
     - evaluator.evaluate_recommendation(rec) ← CRITICAL
     - Update outcome with: WIN_TP1, WIN_TP2, LOSS_SL, MISSED
     - database.update_outcome(rec_id, outcome)
  3. Recalculate weights
  4. Save checkpoint to database

OutcomeEvaluator class (Lines 705+):
  - evaluates_recommendation(rec) → Dict with outcome
  - Checks if trade was ever triggered
  - Determines if WIN/LOSS/MISSED
  - Calculates PnL in pips

trade_alerts_rl.py:
  RecommendationDatabase:
    __init__(db_path):
      - Just takes db_path, no validation
    log_recommendation(rec):
      - Simple INSERT OR IGNORE
      - Returns lastrowid
      - NO VALIDATION
```

### Original RL Flow (WORKING)
```
Recommendations Logged:
  └─ main.py._run_full_analysis_with_rl()
     └─ for rec in parsed_recs:
        └─ self.rl_db.log_recommendation(rec)
           └─ INSERT INTO recommendations
              └─ outcome = 'PENDING'
              └─ evaluated = 0

Outcomes Evaluated (Daily):
  └─ main.py (daily @ 11pm UTC)
     └─ run_daily_learning()
        └─ pending = db.get_pending_recommendations()
        └─ for rec in pending:
           └─ outcome = evaluator.evaluate_recommendation(rec)
           └─ db.update_outcome(rec_id, outcome)
              └─ UPDATE recommendations
                 └─ outcome = 'WIN_TP1'|'LOSS_SL'|'MISSED'
                 └─ evaluated = 1
                 └─ pnl_pips, bars_held, etc.

Weights Recalculated:
  └─ learning_engine.calculate_llm_weights()
     └─ Gets ALL evaluated recommendations from database
     └─ Calculates win_rate, profit_factor, missed_rate
     └─ Applies penalties for missed trades
     └─ Normalizes weights
     └─ Saves checkpoint
```

**Key Characteristic**: SIMPLE log_recommendation(), SEPARATE outcome evaluation in daily cycle

---

## 2. CURRENT SYSTEM (What I Changed)

### New Architecture Changes
```
main.py (CHANGED):
  - Added validation flag: self.rl_db = RecommendationDatabase(db_path=..., validate_entries=True)
  - Calls log_recommendation() which now includes validation
  - Hourly weight reload check (new)
  - Database path auto-detection for Render vs local (new)

daily_learning.py (MOSTLY SAME):
  - Still imports OutcomeEvaluator
  - Still calls evaluate_recommendation()
  - Still updates outcomes
  - Added db_path auto-detection to match main.py

trade_alerts_rl.py (SIGNIFICANTLY CHANGED):
  RecommendationDatabase:
    __init__(db_path, validate_entries=True):
      - NEW: Added entry validation parameter
      - NEW: Creates EntryPriceValidator instance
      - NEW: Creates CurrentPriceValidator instance

    log_recommendation(rec):
      - NEW: Validates entry price IF validate_entries=True
      - NEW: Marks bad entries with confidence='UNREALISTIC'
      - NEW: Still logs (INSERT OR IGNORE) even if validation fails
      - Returns recommendation ID or None if duplicate

  NEW CLASSES ADDED:
    EntryPriceValidator:
      - Checks if LLM entry price is realistic
      - Compares to current market price
      - Thresholds: INTRADAY ±50 pips, SWING ±200 pips

    CurrentPriceValidator:
      - Validates "current price" field in recommendation
      - Checks for stale data
```

---

## 3. ROOT CAUSE ANALYSIS: Why RL Broke

### Change 1: Entry Price Validation Added
**File**: `src/trade_alerts_rl.py` (NEW Classes Lines 32-262)

**Original**:
```python
class RecommendationDatabase:
    def __init__(self, db_path: str = "trade_alerts_rl.db"):
        self.db_path = db_path
        self._init_database()

    def log_recommendation(self, rec: Dict) -> int:
        # Just insert without validation
        cursor = conn.execute('INSERT OR IGNORE INTO recommendations (...) VALUES (...)')
        return cursor.lastrowid
```

**Current**:
```python
class RecommendationDatabase:
    def __init__(self, db_path: str = "trade_alerts_rl.db", validate_entries: bool = True):
        self.validate_entries = validate_entries
        self.entry_validator = EntryPriceValidator() if validate_entries else None
        ...

    def log_recommendation(self, rec: Dict) -> Optional[int]:
        # NEW: Validate entry price
        if self.validate_entries and self.entry_validator:
            validation = self.entry_validator.validate_entry_price(...)
            if not validation['is_valid']:
                # Mark as UNREALISTIC but still log
                rec['confidence'] = 'UNREALISTIC'

        # Then insert (same as before)
        cursor = conn.execute('INSERT OR IGNORE INTO recommendations (...) VALUES (...)')
```

**Impact**:
- ✅ Recommendations still get logged
- ✅ Bad entries marked for tracking
- ❌ Entry validator requires PriceMonitor to work
- ⚠️ If PriceMonitor fails, returns None (recommendation not logged)

### Change 2: Database Path Auto-Detection (RENDER vs LOCAL)
**File**: `main.py` (Lines 84-95)

**Original**:
```python
self.rl_db = RecommendationDatabase()  # Uses hardcoded "trade_alerts_rl.db"
```

**Current**:
```python
db_path = os.getenv('RL_DATABASE_PATH')
if not db_path:
    if os.path.exists('/var/data'):
        db_path = '/var/data/trade_alerts_rl.db'  # Render persistent disk
    else:
        db_path = str(Path(__file__).parent / 'data' / 'trade_alerts_rl.db')  # Local
self.rl_db = RecommendationDatabase(db_path=db_path, validate_entries=True)
```

**Impact**:
- ✅ Works correctly on Render (writes to persistent disk)
- ❌ **Local machine gets EMPTY database**
  - Trade-Alerts on Render → `/var/data/trade_alerts_rl.db` (populated)
  - Local machine → `data/trade_alerts_rl.db` (empty!)
  - No syncing between them
  - trade-alerts-review queries empty local database

### Change 3: Weight Reload Timing Added
**File**: `main.py` (Lines 56, 102, 108)

**Original**:
```python
# Weights only loaded once at startup
self.llm_weights = self._load_llm_weights()

# Daily learning reloads them
if should_run_learning():
    run_daily_learning()
    self.llm_weights = self._load_llm_weights()
```

**Current**:
```python
WEIGHT_RELOAD_INTERVAL = 3600  # 1 hour
self.last_weight_reload = None

# Reload weights hourly (NEW)
if (self.last_weight_reload is None or
    (current_time - self.last_weight_reload).total_seconds() > self.WEIGHT_RELOAD_INTERVAL):
    self.llm_weights = self._load_llm_weights()
    self.last_weight_reload = current_time
```

**Impact**:
- ✅ Weights update hourly instead of waiting for daily learning
- ✅ Faster feedback loop
- ⚠️ If learning_engine is broken, won't help
- ❌ Relies on daily_learning() to evaluate outcomes first

### Change 4: Entry/Current Price Validators Added
**File**: `src/trade_alerts_rl.py` (NEW - Lines 32-262)

**Original**: NO VALIDATION

**Current**:
```python
class EntryPriceValidator:
    - Checks if entry price is realistic
    - Requires PriceMonitor to work
    - Silently skips if PriceMonitor unavailable

class CurrentPriceValidator:
    - Checks if "current price" field matches live market
    - Also requires PriceMonitor
```

**Impact**:
- ✅ Filters obviously bad LLM entries
- ❌ **If PriceMonitor fails/unavailable, validation fails silently**
- ❌ **Broken PriceMonitor could prevent recommendations from being logged**

---

## 4. THE CHAIN OF FAILURES

### Hypothesis: Why RL System Appears Broken

**Scenario 1: Database Location Mismatch (MOST LIKELY)**
```
Render Production:
  main.py detects /var/data exists
  └─ Creates RL database at /var/data/trade_alerts_rl.db
  └─ Logs recommendations there
  └─ Daily learning @ 11pm UTC evaluates them
  └─ Weights calculated and saved

Local Machine (When Running trade-alerts-review):
  main.py not running (Trade-Alerts is on Render)
  └─ trade-alerts-review script runs
  └─ Checks for RL database at data/trade_alerts_rl.db
  └─ Database is EMPTY (different from /var/data on Render)
  └─ Shows "0 recommendations"

RESULT: RL database exists and works on Render, but local analysis shows empty
```

**Scenario 2: PriceMonitor Failure (SECONDARY)**
```
If PriceMonitor.get_rate() fails:
  log_recommendation():
    ├─ entry_validator tries to validate
    ├─ get_rate() returns None
    ├─ validation['is_valid'] = True (fallback: don't reject if can't validate)
    └─ Still logs recommendation ✅

BUT if PriceMonitor() initialization fails in __init__:
  ├─ Recommendation not validated
  ├─ Recommendation still logged
  └─ Should still work ✅

So this is unlikely to be the issue
```

**Scenario 3: OutcomeEvaluator Not Being Called (POSSIBLE)**
```
If daily_learning() never runs or doesn't get called:
  ├─ Recommendations stay PENDING forever
  ├─ evaluated = 0 always
  ├─ learning_engine.calculate_llm_weights() has no data
  ├─ Returns default weights (0.25 each)
  └─ No learning happens

Check: Does main.py actually call run_daily_learning()?
  └─ Lines 148-162: YES, should be called
  └─ But only if should_run_learning() returns True
  └─ And if /var/data database is being used
  └─ Local machine: Calls daily_learning on LOCAL empty database
```

---

## 5. SPECIFIC CODE DIFFERENCES

### main.py Initialization
**Original**:
```python
self.rl_db = RecommendationDatabase()
self.rl_parser = RLRecommendationParser()
self.learning_engine = LLMLearningEngine(self.rl_db)
```

**Current**:
```python
db_path = os.getenv('RL_DATABASE_PATH')
if not db_path:
    if os.path.exists('/var/data'):
        db_path = '/var/data/trade_alerts_rl.db'
    else:
        db_path = str(Path(__file__).parent / 'data' / 'trade_alerts_rl.db')
self.rl_db = RecommendationDatabase(db_path=db_path, validate_entries=True)
self.rl_parser = RLRecommendationParser()
self.learning_engine = LLMLearningEngine(self.rl_db)
```

**Change Impact**: ⚠️ HIGH - Different database paths on Render vs local

### RecommendationDatabase.__init__
**Original**:
```python
def __init__(self, db_path: str = "trade_alerts_rl.db"):
    self.db_path = db_path
    self._init_database()
```

**Current**:
```python
def __init__(self, db_path: str = "trade_alerts_rl.db", validate_entries: bool = True):
    self.db_path = db_path
    self.validate_entries = validate_entries
    self.entry_validator = EntryPriceValidator() if validate_entries else None
    self.current_price_validator = CurrentPriceValidator()
    self._init_database()
```

**Change Impact**: ⚠️ MEDIUM - Added validation logic, but should still work

### RecommendationDatabase.log_recommendation
**Original**:
```python
def log_recommendation(self, rec: Dict) -> int:
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.execute('''INSERT OR IGNORE INTO recommendations (...)
        VALUES (...)''', (...))
        conn.commit()
        return cursor.lastrowid
```

**Current**:
```python
def log_recommendation(self, rec: Dict) -> Optional[int]:
    # Validate entry price if enabled
    if self.validate_entries and self.entry_validator:
        validation = self.entry_validator.validate_entry_price(...)
        if not validation['is_valid']:
            # Still log but mark as unrealistic
            rec['rationale'] = f"[UNREALISTIC_ENTRY: ...] {original_rationale}"
            rec['confidence'] = 'UNREALISTIC'

    # Validate current price if provided
    if current_price and self.current_price_validator:
        price_validation = self.current_price_validator.validate_current_price(...)
        if price_validation['warning']:
            # Log warning and mark in rationale

    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.execute('''INSERT OR IGNORE INTO recommendations (...)
        VALUES (...)''', (...))
        conn.commit()
        if cursor.lastrowid == 0:
            return None  # Was a duplicate (NEW)
        return cursor.lastrowid
```

**Change Impact**: ⚠️ MEDIUM
- Still logs recommendations
- Returns None if duplicate (changed return value handling)
- Adds validation that requires PriceMonitor

---

## 6. CRITICAL FINDINGS

### What DIDN'T Break (Still Works)
✅ **Recommendation Logging**
- Database still accepts recommendations
- Validation is permissive (doesn't reject, just marks)
- Duplicates still handled via UNIQUE constraint

✅ **Schema**
- No schema changes that would break compatibility
- Added columns would require ALTER TABLE (didn't happen)

✅ **Daily Learning**
- OutcomeEvaluator still exists and is imported
- run_daily_learning() still gets called
- Should still evaluate outcomes

### What DID Break (or Appears Broken)
❌ **Local Database Access**
- Trade-Alerts on Render uses `/var/data/trade_alerts_rl.db` (persistent)
- Local analysis uses `data/trade_alerts_rl.db` (empty!)
- No syncing mechanism → trade-alerts-review shows 0 recommendations

❌ **Outcome Evaluation Evidence**
- Looking at Render logs would show if outcomes are being evaluated
- But we can't access Render logs directly
- Database shows recommendations but not outcomes

❌ **Recommendation Sync**
- Need to copy `/var/data/trade_alerts_rl.db` from Render to local `data/`
- OR point local code to Render database via remote access

---

## 7. WHAT NEEDS TO BE VERIFIED

### On Render (Production)
```
1. Does /var/data/trade_alerts_rl.db exist and have data?
2. Are recommendations being logged daily?
3. Is daily_learning() being called at 11pm UTC?
4. Are outcomes being evaluated?
5. Are LLM weights being calculated?
6. Check logs: Are there errors in validation?
```

### Locally
```
1. data/trade_alerts_rl.db is empty (expected - Trade-Alerts not running locally)
2. Can we sync database from Render to local?
3. Can we run daily_learning.py against Render database?
4. Can trade-alerts-review access Render database?
```

---

## 8. RECOMMENDED FIXES

### Priority 1: Database Sync (IMMEDIATE)
```python
# Option A: Copy database from Render
# Copy /var/data/trade_alerts_rl.db to data/trade_alerts_rl.db

# Option B: Create sync script
agents/sync_render_results.py should also sync the RL database
```

### Priority 2: Add Logging to Verify RL Flow
```python
# In main.py log_recommendation():
logger.info(f"Logging recommendation: {rec['pair']} {rec['direction']} from {rec['llm_source']}")

# In daily_learning.py:
logger.info(f"Evaluating {len(pending)} pending recommendations")
logger.info(f"Updated {evaluated_count} outcomes")
logger.info(f"New weights: {weights}")

# In LLMLearningEngine.calculate_llm_weights():
logger.info(f"Calculating weights for {len(llm_sources)} LLMs")
for llm in llm_sources:
    df = self.db.get_llm_performance(llm)
    logger.info(f"  {llm}: {len(df)} evaluated recommendations")
```

### Priority 3: Verify OutcomeEvaluator (CRITICAL)
```python
# Check if OutcomeEvaluator.evaluate_recommendation() is actually working
# Add detailed logging to see what it returns
# Verify it's finding OANDA closed trades

# In daily_learning.py:
outcome = evaluator.evaluate_recommendation(rec)
logger.info(f"Evaluated {rec['pair']} {rec['direction']}: outcome={outcome}")
if outcome is None:
    logger.warning(f"Evaluation returned None for {rec['pair']}")
```

---

## SUMMARY: What Changed and Why

| Component | Original | Current | Impact |
|-----------|----------|---------|--------|
| Database Path | Hardcoded "trade_alerts_rl.db" | Auto-detected /var/data vs data/ | HIGH - Local/Render mismatch |
| Entry Validation | None | Added (EntryPriceValidator) | MEDIUM - Filters bad entries, needs PriceMonitor |
| log_recommendation() | Simple insert | Insert + validation | LOW - Still logs, just marks bad ones |
| Weight Reload | Daily only | Hourly + daily | LOW - Positive change |
| OutcomeEvaluator | Present and used | Still present, but... | UNKNOWN - Appears broken but code is there |
| daily_learning.py | Auto-detects db path? | Now auto-detects | MEDIUM - Must match main.py |

**Root Cause**: Database location mismatch + no verification that OutcomeEvaluator is actually evaluating outcomes

---

**Created**: February 22, 2026 at 00:15 EST
**Status**: Analysis complete, fixes pending verification
