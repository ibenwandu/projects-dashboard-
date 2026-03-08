# How to Check if Daily RL Learning is Running (11pm UTC)

## Problem: Weights Not Updating Since Jan 13th

If you're seeing **identical LLM weights** between Jan 13th and today, this guide will help you diagnose why.

---

## Quick Diagnostic Checklist

### Step 1: Check if Daily Learning is Running ✅

**Render Dashboard → `trade-alerts` → Logs**

**Search for messages around 11pm UTC (6-7pm EST):**

Look for:
```
🧠 DAILY LEARNING TIME (11pm UTC)
================================================================================
DAILY LEARNING CYCLE - 2026-01-XX 23:XX:XX UTC
```

**If you see this:** ✅ Daily learning is triggering
**If you DON'T see this:** ❌ Daily learning is not running (see troubleshooting below)

---

### Step 2: Check What Daily Learning Found ✅

**Look for these log messages:**

#### ✅ If Working Correctly:
```
Step 1: Fetching pending recommendations...
Found X recommendations ready for evaluation

Step 2: Evaluating outcomes...
[1/X] chatgpt - EUR/USD LONG @ 1.0850
  ✅ WIN_TP1: +50.0 pips in 12 bars
```

#### ❌ If No New Data:
```
Step 1: Fetching pending recommendations...
Found 0 recommendations ready for evaluation

ℹ️  No new recommendations to evaluate
   This is normal if system hasn't generated recommendations in last 24 hours
```

**If you see "Found 0 recommendations":**
- No new recommendations have been generated since last evaluation
- OR all new recommendations are < 4 hours old (need to wait)
- **This would explain why weights haven't changed!**

---

### Step 3: Check Recommendation Counts ✅

**Render Dashboard → `trade-alerts` → Shell**

```bash
cd /opt/render/project
python -c "
from src.trade_alerts_rl import RecommendationDatabase
from datetime import datetime, timedelta
db = RecommendationDatabase()

# Count all recommendations
all_recs = db.get_all_recommendations()
print(f'Total recommendations: {len(all_recs)}')

# Count by status
pending = all_recs[all_recs['outcome'] == 'PENDING']
evaluated = all_recs[all_recs['evaluated'] == 1]
print(f'Pending (not evaluated): {len(pending)}')
print(f'Evaluated: {len(evaluated)}')

# Check recent recommendations (last 7 days)
recent_cutoff = datetime.utcnow() - timedelta(days=7)
recent_recs = all_recs[all_recs['timestamp'] >= recent_cutoff.isoformat()]
print(f'Recommendations in last 7 days: {len(recent_recs)}')

# Check by LLM
for llm in ['chatgpt', 'gemini', 'claude', 'synthesis']:
    llm_recs = all_recs[all_recs['llm_source'] == llm]
    llm_evaluated = llm_recs[llm_recs['evaluated'] == 1]
    print(f'{llm}: {len(llm_recs)} total, {len(llm_evaluated)} evaluated')
"
```

**Expected:**
- If weights haven't changed, you might see **no new evaluated recommendations** since Jan 13th
- This means either:
  1. No new analysis has run (no new recommendations logged)
  2. New recommendations exist but are still PENDING (< 4 hours old)
  3. Daily learning ran but found nothing to evaluate

---

### Step 4: Check Analysis Runs ✅

**Render Dashboard → `trade-alerts` → Logs**

**Search for scheduled analysis runs since Jan 13th:**

Look for:
```
=== Scheduled Analysis Time: 2026-01-XX XX:XX:XX EST ===
Step 7: Logging recommendations to RL database...
✅ Logged X recommendations to RL database
```

**If you see this:** ✅ New recommendations are being logged
**If you DON'T see this:** ❌ Analysis hasn't run or isn't logging recommendations

---

### Step 5: Check Evaluation Status ✅

**Render Dashboard → `trade-alerts` → Shell**

```bash
cd /opt/render/project
python -c "
from src.trade_alerts_rl import RecommendationDatabase
from datetime import datetime
db = RecommendationDatabase()

# Get all recommendations since Jan 13
cutoff = datetime(2026, 1, 13, 0, 0, 0)
all_recs = db.get_all_recommendations()
all_recs['timestamp_dt'] = all_recs['timestamp'].apply(lambda x: datetime.fromisoformat(x))
recent = all_recs[all_recs['timestamp_dt'] >= cutoff]

print(f'Recommendations since Jan 13: {len(recent)}')
print(f'Status breakdown:')
print(recent['outcome'].value_counts())
print()
print('Pending recommendations older than 4 hours:')
from datetime import timedelta
now = datetime.utcnow()
pending = recent[recent['outcome'] == 'PENDING']
for idx, rec in pending.iterrows():
    rec_time = datetime.fromisoformat(rec['timestamp'])
    hours_old = (now - rec_time).total_seconds() / 3600
    if hours_old >= 4:
        print(f'  {rec[\"llm_source\"]} - {rec[\"pair\"]} {rec[\"direction\"]} ({hours_old:.1f} hours old) - SHOULD BE EVALUATED')
"
```

**This will show:**
- How many recommendations exist since Jan 13th
- How many are still PENDING vs evaluated
- If any PENDING recommendations are > 4 hours old (should have been evaluated)

---

## Common Reasons Why Weights Don't Change

### Reason 1: No New Evaluated Recommendations ⚠️

**Symptoms:**
- Daily learning runs but finds "0 recommendations ready for evaluation"
- No new analysis runs since Jan 13th
- OR new recommendations exist but are < 4 hours old

**Solution:**
- Wait for next scheduled analysis (should create new recommendations)
- Wait for recommendations to age to 4+ hours
- Check if scheduled analysis is running

---

### Reason 2: Daily Learning Not Running ❌

**Symptoms:**
- No "🧠 DAILY LEARNING TIME (11pm UTC)" messages in logs
- No "DAILY LEARNING CYCLE" messages

**Possible causes:**
1. Service crashed before 11pm UTC
2. `should_run_learning()` function not detecting 11pm UTC correctly
3. Service stopped/paused

**Solution:**
- Check service status around 11pm UTC (6-7pm EST)
- Verify service is "Live" (not stopped)
- Check logs for errors before 11pm UTC

---

### Reason 3: Evaluations Not Changing Outcomes ⚠️

**Symptoms:**
- Daily learning runs
- Evaluates recommendations
- But all outcomes are the same (all wins, all losses, all missed)
- Weights don't change because performance is same

**This is NORMAL** if:
- LLM performance hasn't changed
- Same patterns continue (e.g., Synthesis still best, Claude still worst)
- No new data points to shift weights

**However**, weights should still update if:
- More recommendations are evaluated
- Sample sizes change
- Even if performance stays similar, counts should update

---

## Manual Trigger (For Testing)

**To test if daily learning works:**

**Render Dashboard → `trade-alerts` → Shell**

```bash
cd /opt/render/project
python -c "
from src.daily_learning import run_daily_learning
run_daily_learning()
"
```

**Expected output:**
```
================================================================================
DAILY LEARNING CYCLE - 2026-01-XX XX:XX:XX UTC
================================================================================

Step 1: Fetching pending recommendations...
Found X recommendations ready for evaluation

Step 2: Evaluating outcomes...
...
✅ Weights updated
```

---

## Check Current Weights vs Historical

**Render Dashboard → `trade-alerts` → Shell**

```bash
cd /opt/render/project
python -c "
from src.trade_alerts_rl import RecommendationDatabase, LLMLearningEngine
db = RecommendationDatabase()
engine = LLMLearningEngine(db)

# Get current weights
weights = engine.calculate_llm_weights()
print('Current weights:')
for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
    print(f'  {llm}: {weight*100:.1f}%')

# Get performance stats
report = engine.generate_performance_report()
print()
print('LLM Performance:')
for llm, perf in report['llm_performance'].items():
    if perf['total_recs'] > 0:
        print(f'  {llm.upper()}:')
        print(f'    Total: {perf[\"total_recs\"]}')
        print(f'    Win Rate: {perf[\"win_rate\"]*100:.1f}%')
        print(f'    Avg PnL: {perf[\"avg_pnl\"]:.1f} pips')
"
```

**Compare this to Jan 13th data:**
- If numbers are **identical** → No new data has been evaluated
- If numbers are **different** → Learning is working, but weights might be same if performance patterns unchanged

---

## What to Check in Logs (Timeline)

### Around 11pm UTC (6-7pm EST):

**Look for:**
1. `🧠 DAILY LEARNING TIME (11pm UTC)` - Learning triggered
2. `DAILY LEARNING CYCLE` - Learning started
3. `Found X recommendations ready for evaluation` - Recommendations found
4. `[X/Y] llm_source - pair direction` - Evaluations happening
5. `✅ Weights updated` - Weights recalculated

**If missing step 1-2:** Learning not triggering
**If missing step 3:** No recommendations to evaluate
**If missing step 4:** Evaluation failing
**If missing step 5:** Weight update failing

---

## Next Steps

1. **Check logs around 11pm UTC** (last few days) - Is daily learning running?
2. **Count recommendations** - Are new ones being created?
3. **Check evaluation status** - Are PENDING recommendations being evaluated?
4. **Compare current vs Jan 13th data** - Are counts/performance different?

**Most likely issue:** No new recommendations have been evaluated since Jan 13th, either because:
- No new analysis runs (check scheduled times)
- New recommendations are < 4 hours old (need to wait)
- Daily learning isn't running (check 11pm UTC logs)
