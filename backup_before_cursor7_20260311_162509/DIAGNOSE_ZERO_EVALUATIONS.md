# Diagnosing Zero Evaluations After 3 Weeks

## 🔍 Problem
The FX Engine dashboard shows:
- **0 evaluated signals**
- **0.0% Win Rate**
- **Total Trades: 2** (but 3 weeks of operation)

This indicates the RL system is **not evaluating recommendations** despite running for weeks.

---

## 📋 How RL System Is Supposed To Work

### 1. **Recommendation Logging** (Real-Time, During Analysis)
**When**: Every scheduled analysis (8 times per day: 2am, 4am, 7am, 9am, 11am, 12pm, 4pm, 8pm EST)

**What Happens**:
- Step 7 of analysis logs ALL LLM recommendations to database:
  - ChatGPT recommendations
  - Gemini recommendations  
  - Claude recommendations
  - Synthesis (final) recommendations

**Database Fields**:
- `outcome = 'PENDING'` (initial status)
- `evaluated = 0` (not yet evaluated)
- `timestamp` = when recommendation was made

**Expected Log Output**:
```
Step 7 (NEW): Logging recommendations to RL database...
✅ Logged 8 recommendations for future learning
```

---

### 2. **Outcome Evaluation** (Daily at 11pm UTC)
**When**: Every day at **11:00 PM UTC** (6-7pm EST/EDT depending on daylight saving)

**What Happens**:
1. Fetches all recommendations that are:
   - Status: `PENDING`
   - Age: **4+ hours old** (gives market time to move)
   - Not yet evaluated (`evaluated = 0`)

2. For each recommendation, `OutcomeEvaluator`:
   - Fetches historical price data from `yfinance`
   - Checks if price hit:
     - **TP1** (Take Profit 1) → `WIN_TP1`
     - **TP2** (Take Profit 2) → `WIN_TP2`
     - **SL** (Stop Loss) → `LOSS_SL`
     - **MISSED** (entry price too far, never triggered)
   - Updates database with outcome

3. Calculates new LLM weights based on performance

4. Saves learning checkpoint

**Expected Log Output** (at 11pm UTC):
```
🧠 DAILY LEARNING TIME (11pm UTC)
================================================================================
DAILY LEARNING CYCLE - 2026-01-17 23:00:00 UTC
================================================================================

Step 1: Fetching pending recommendations...
Found 12 recommendations ready for evaluation

Step 2: Evaluating outcomes...
[1/12] chatgpt - GBPUSD LONG @ 1.2650
  ✅ WIN_TP1: +30.0 pips in 4 bars
[2/12] gemini - EURUSD SHORT @ 1.0950
  ❌ LOSS_SL: -25.0 pips in 2 bars
...

✅ Evaluated 12 new recommendations
📊 Today's Results: 6 wins, 4 losses, 2 missed
📊 Win Rate (excluding missed): 60.0%

Step 5: Calculating updated LLM weights...
🎯 Updated LLM Weights (after evaluation):
   GEMINI: 35.6%
   SYNTHESIS: 32.4%
   CHATGPT: 25.4%
   CLAUDE: 6.6%
```

---

## 🔍 Diagnostic Steps

### Step 1: Check if Recommendations Are Being Logged

**On Render → Shell:**
```bash
cd /opt/render/project
python -c "
from src.trade_alerts_rl import RecommendationDatabase
from datetime import datetime

db = RecommendationDatabase(db_path='/var/data/trade_alerts_rl.db')
conn = db._get_connection()
cursor = conn.cursor()

# Count total recommendations
cursor.execute('SELECT COUNT(*) FROM recommendations')
total = cursor.fetchone()[0]

print(f'📊 Total Recommendations: {total}')

# Count by status
cursor.execute('SELECT outcome, COUNT(*) FROM recommendations GROUP BY outcome')
statuses = cursor.fetchall()
print('\n📊 By Status:')
for status, count in statuses:
    print(f'  {status}: {count}')

# Count by LLM
cursor.execute('SELECT llm_source, COUNT(*) FROM recommendations GROUP BY llm_source')
llms = cursor.fetchall()
print('\n📊 By LLM:')
for llm, count in llms:
    print(f'  {llm}: {count}')

# Most recent recommendations
cursor.execute('SELECT timestamp, llm_source, pair, outcome FROM recommendations ORDER BY timestamp DESC LIMIT 5')
recent = cursor.fetchall()
print('\n📊 Most Recent (last 5):')
for ts, llm, pair, outcome in recent:
    print(f'  {ts} | {llm} | {pair} | {outcome}')

conn.close()
"
```

**Expected if working:**
- Total > 0 (should have many after 3 weeks)
- Multiple LLM sources (chatgpt, gemini, claude, synthesis)
- Mix of PENDING and evaluated outcomes

**If total = 0 or very low:**
→ **Recommendations are NOT being logged** (Step 7 not working)

**Check logs for:**
- "Step 7 (NEW): Logging recommendations to RL database..."
- "✅ Logged X recommendations for future learning"

---

### Step 2: Check Age of Pending Recommendations

**On Render → Shell:**
```bash
cd /opt/render/project
python -c "
from src.trade_alerts_rl import RecommendationDatabase
from datetime import datetime, timedelta

db = RecommendationDatabase(db_path='/var/data/trade_alerts_rl.db')
pending = db.get_pending_recommendations(min_age_hours=0)  # Get all pending

print(f'📊 Pending Recommendations: {len(pending)}')

if len(pending) > 0:
    now = datetime.utcnow()
    print('\n📊 Age of Pending Recommendations:')
    for idx, rec in pending.iterrows():
        rec_time = datetime.fromisoformat(rec['timestamp'])
        age_hours = (now - rec_time).total_seconds() / 3600
        status = '✅ Ready (>4h)' if age_hours >= 4 else f'⏳ Waiting ({age_hours:.1f}h old)'
        print(f'  {rec[\"llm_source\"]} - {rec[\"pair\"]} ({age_hours:.1f} hours old) - {status}')
    
    # Count ready for evaluation
    ready = pending[pending['timestamp'] < (now - timedelta(hours=4)).isoformat()]
    print(f'\n✅ Ready for evaluation (>4 hours old): {len(ready)}')
else:
    print('❌ No pending recommendations found')
"
```

**Expected if working:**
- Some recommendations > 4 hours old (ready for evaluation)
- Mix of ages (new and old)

**If all pending are < 4 hours old:**
→ Wait for recommendations to age

**If many > 4 hours old but not evaluated:**
→ **Daily learning is NOT running or evaluation is failing**

---

### Step 3: Check if Daily Learning Is Running

**On Render → Logs:**
Search for these messages around **11pm UTC** (6-7pm EST):

```
🧠 DAILY LEARNING TIME (11pm UTC)
DAILY LEARNING CYCLE - 2026-01-XX 23:00:00 UTC
Step 1: Fetching pending recommendations...
Step 2: Evaluating outcomes...
```

**If you DON'T see these messages:**
→ **Daily learning is NOT running**

**Possible causes:**
1. Service crashed/stopped before 11pm UTC
2. `should_run_learning()` function not detecting 11pm UTC correctly
3. Service timezone mismatch
4. Code bug in learning trigger

**Check service status:**
- Render Dashboard → `trade-alerts` → Status should be "Live"
- Check for errors before 11pm UTC

---

### Step 4: Check if Evaluation Is Failing

**On Render → Logs:**
Search for:
- "Error evaluating recommendation"
- "Error fetching data for"
- "Could not evaluate yet"

**If you see errors:**
→ **OutcomeEvaluator is failing** (likely `yfinance` data issues)

**Common errors:**
- `yfinance` API timeout/failure
- Pair format issues (EUR/USD vs EURUSD=X)
- Insufficient historical data
- Network issues on Render

---

### Step 5: Check Database Path

**CRITICAL**: Make sure database path is correct!

**On Render → Shell:**
```bash
ls -la /var/data/trade_alerts_rl.db
```

**Should show:**
- File exists
- Recent modification time (updated today)
- Non-zero file size

**If file doesn't exist or is empty:**
→ **Database path mismatch** (using wrong database)

**Check code for:**
```python
db = RecommendationDatabase(db_path='/var/data/trade_alerts_rl.db')
```

vs default:
```python
db = RecommendationDatabase()  # Uses 'trade_alerts_rl.db' in current directory
```

**In `daily_learning.py` and `main.py`:**
- Should use `/var/data/trade_alerts_rl.db` (persistent disk)
- NOT `trade_alerts_rl.db` (ephemeral storage)

---

## 🐛 Most Likely Issues (After 3 Weeks)

### Issue 1: Daily Learning Not Running ⚠️
**Symptom**: Zero evaluations after 3 weeks, no "DAILY LEARNING CYCLE" messages

**Check**: Look for "🧠 DAILY LEARNING TIME" in logs at 11pm UTC

**Fix**: Verify `should_run_learning()` function and service uptime

---

### Issue 2: Recommendations Not Being Logged ⚠️
**Symptom**: Very few recommendations in database (< 10 after 3 weeks)

**Check**: Look for "Step 7 (NEW): Logging recommendations" in analysis logs

**Fix**: Verify Step 7 code execution in `main.py` `_run_full_analysis_with_rl()`

---

### Issue 3: Evaluation Failing Silently ⚠️
**Symptom**: Many PENDING recommendations > 4 hours old, but evaluations failing

**Check**: Look for "Error evaluating recommendation" in logs

**Fix**: Debug `OutcomeEvaluator._get_price_data()` (yfinance issues)

---

### Issue 4: Wrong Database Path ❌
**Symptom**: Recommendations exist but in wrong location

**Check**: Verify `/var/data/trade_alerts_rl.db` exists and has data

**Fix**: Ensure all code uses `/var/data/trade_alerts_rl.db`

---

## ✅ Quick Test: Force Manual Evaluation

**To test if evaluation works manually:**

```bash
cd /opt/render/project
python -c "
from src.daily_learning import run_daily_learning
run_daily_learning()
"
```

**This will:**
1. Fetch all pending recommendations (>4 hours old)
2. Evaluate them
3. Update weights
4. Save checkpoint

**If this works but daily learning doesn't:**
→ Issue is with the 11pm UTC trigger

**If this also fails:**
→ Issue is with `OutcomeEvaluator` or database

---

## 📝 Summary Checklist

After 3 weeks, you should have:
- [ ] **100+ recommendations** logged (8 analyses/day × 8 recs/analysis × 21 days ≈ 1344)
- [ ] **Daily evaluations** happening at 11pm UTC (21 evaluations over 3 weeks)
- [ ] **Many evaluated recommendations** (should accumulate over time)
- [ ] **Updated LLM weights** (changing based on performance)

**If any are missing:**
→ Use diagnostic steps above to identify the issue
