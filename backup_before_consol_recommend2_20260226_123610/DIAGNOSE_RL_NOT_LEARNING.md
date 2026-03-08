# Diagnosing Why RL Weights Stay at 25% Each

## Problem: Weights Remain Equal After 3+ Days

If your emails consistently show `25%, 25%, 25%, 25%` for multiple days, the RL system isn't learning. Let's diagnose why.

---

## 🔍 Step 1: Quick Diagnosis Script

**Run this diagnostic script to identify the issue:**

```bash
cd /opt/render/project/src
python << 'EOF'
from src.trade_alerts_rl import RecommendationDatabase, LLMLearningEngine
import sqlite3
from datetime import datetime, timedelta

db = RecommendationDatabase()
engine = LLMLearningEngine(db)

print("="*70)
print("RL DIAGNOSIS: Why Weights Stay at 25%")
print("="*70)

# Check current weights
weights = engine.calculate_llm_weights()
print("\n📊 Current LLM Weights:")
all_equal = len(set(weights.values())) == 1
for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
    print(f"   {llm}: {weight*100:.1f}%")

if all_equal:
    print("   ⚠️  ALL WEIGHTS EQUAL - RL not learning")

# Check database
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

# Total recommendations
cursor.execute('SELECT COUNT(*) FROM recommendations')
total = cursor.fetchone()[0]
print(f"\n📈 Total Recommendations Logged: {total}")

# Recommendations by LLM
cursor.execute('''
    SELECT llm_source, COUNT(*) as count
    FROM recommendations
    GROUP BY llm_source
    ORDER BY count DESC
''')
print("\n📋 Recommendations by LLM:")
for row in cursor.fetchall():
    print(f"   {row[0]}: {row[1]}")

# Evaluated recommendations (have outcomes)
cursor.execute('SELECT COUNT(*) FROM recommendations WHERE evaluated = 1')
evaluated = cursor.fetchone()[0]
print(f"\n✅ Recommendations with Outcomes (evaluated = 1): {evaluated}")

# Pending recommendations (no outcomes yet)
cursor.execute('SELECT COUNT(*) FROM recommendations WHERE evaluated = 0 OR outcome = "PENDING"')
pending = cursor.fetchone()[0]
print(f"⏳ Pending Recommendations (no outcomes yet): {pending}")

# Check if we have enough data per LLM (need 5+ evaluated per LLM)
cursor.execute('''
    SELECT llm_source, COUNT(*) as count
    FROM recommendations
    WHERE evaluated = 1
    GROUP BY llm_source
''')
llm_counts = cursor.fetchall()
print("\n📊 Evaluated Recommendations per LLM:")
for llm, count in llm_counts:
    status = "✅ OK" if count >= 5 else "❌ NEED MORE DATA (< 5)"
    print(f"   {llm}: {count} {status}")

# Check outcomes breakdown
if evaluated > 0:
    cursor.execute('''
        SELECT outcome, COUNT(*) as count
        FROM recommendations
        WHERE evaluated = 1
        GROUP BY outcome
    ''')
    print("\n🎯 Outcomes Breakdown:")
    for outcome, count in cursor.fetchall():
        print(f"   {outcome}: {count}")

# Check age of pending recommendations
cursor.execute('''
    SELECT COUNT(*) as count,
           MIN(timestamp) as oldest,
           MAX(timestamp) as newest
    FROM recommendations
    WHERE evaluated = 0 OR outcome = "PENDING"
''')
pending_info = cursor.fetchone()
if pending_info and pending_info[0] > 0:
    oldest_str = pending_info[1][:19] if pending_info[1] else "N/A"
    newest_str = pending_info[2][:19] if pending_info[2] else "N/A"
    print(f"\n⏳ Pending Recommendations Info:")
    print(f"   Oldest pending: {oldest_str}")
    print(f"   Newest pending: {newest_str}")
    
    # Calculate age
    if pending_info[1]:
        try:
            oldest_dt = datetime.fromisoformat(pending_info[1])
            age_hours = (datetime.utcnow() - oldest_dt).total_seconds() / 3600
            print(f"   Age: {age_hours:.1f} hours (need 4+ hours for evaluation)")

# Check learning checkpoints
cursor.execute('SELECT COUNT(*) FROM learning_checkpoints')
checkpoint_count = cursor.fetchone()[0]
print(f"\n📚 Learning Checkpoints (Daily Learning Runs): {checkpoint_count}")

if checkpoint_count > 0:
    cursor.execute('''
        SELECT timestamp, notes
        FROM learning_checkpoints
        ORDER BY timestamp DESC
        LIMIT 3
    ''')
    print("\n📅 Recent Learning Checkpoints:")
    for ts, notes in cursor.fetchall():
        ts_short = ts[:19] if ts else "N/A"
        print(f"   {ts_short}: {notes}")

conn.close()

# DIAGNOSIS SUMMARY
print("\n" + "="*70)
print("🔍 DIAGNOSIS:")
print("="*70)

if total == 0:
    print("❌ ISSUE: No recommendations logged")
    print("   → Recommendations aren't being saved to database")
    print("   → Check if analysis is running successfully")
elif evaluated == 0:
    print("❌ ISSUE: No outcomes evaluated")
    print("   → Recommendations are logged but outcomes aren't being evaluated")
    print("   → Daily learning may not be running")
    print("   → Check daily learning logs at 11pm UTC")
elif evaluated < 20:  # Need at least 5 per LLM * 4 LLMs = 20 minimum
    print("❌ ISSUE: Not enough evaluated recommendations")
    print(f"   → Only {evaluated} recommendations evaluated")
    print("   → Need at least 5 evaluated per LLM (20 total minimum)")
    print("   → Wait for more outcomes or check if evaluation is working")
else:
    # Check if all LLMs have enough data
    has_enough = all(count >= 5 for _, count in llm_counts)
    if not has_enough:
        print("❌ ISSUE: Some LLMs don't have enough data")
        print("   → Need at least 5 evaluated recommendations per LLM")
        for llm, count in llm_counts:
            if count < 5:
                print(f"   → {llm}: only {count} evaluated (need 5+)")
    elif checkpoint_count == 0:
        print("❌ ISSUE: Daily learning never ran")
        print("   → No learning checkpoints found")
        print("   → Daily learning should run at 11pm UTC")
        print("   → Check if daily learning is scheduled/running")
    else:
        print("✅ Data looks sufficient - weights should be calculated")
        print("   → If weights are still 25%, all LLMs may be performing equally")
        print("   → Check performance metrics above")

print("\n" + "="*70)
EOF
```

---

## 🎯 Common Issues & Solutions

### Issue 1: No Recommendations Logged

**Symptom:** `Total Recommendations Logged: 0`

**Cause:** Recommendations aren't being saved to database

**Solution:**
1. Check if analysis is running: Look for "Step 7 (NEW): Logging recommendations to RL database..." in logs
2. Check for errors during recommendation logging
3. Verify database file exists: `ls -la /opt/render/project/src/trade_alerts_rl.db`

---

### Issue 2: No Outcomes Evaluated

**Symptom:** `Evaluated: 0` but `Total: X` (where X > 0)

**Cause:** Daily learning isn't running or evaluation is failing

**Solution:**
1. **Check if daily learning is running:**
   - Look for "DAILY LEARNING CYCLE" in logs around 11pm UTC
   - Check if `should_run_learning()` is being called in main loop

2. **Check evaluation logic:**
   - Recommendations need to be 4+ hours old to evaluate
   - Check if `OutcomeEvaluator` is working

3. **Manually trigger daily learning:**
   ```bash
   cd /opt/render/project/src
   python -c "from src.daily_learning import run_daily_learning; run_daily_learning()"
   ```

---

### Issue 3: Not Enough Data Per LLM

**Symptom:** Some LLMs have < 5 evaluated recommendations

**Cause:** Need minimum 5 evaluated recommendations per LLM for weight calculation

**Solution:**
1. Wait for more recommendations to be evaluated
2. Check if recommendations are being generated for all LLMs
3. Verify all 4 LLMs (chatgpt, gemini, claude, synthesis) are generating recommendations

---

### Issue 4: Daily Learning Not Running

**Symptom:** `Learning Checkpoints: 0` or no recent checkpoints

**Cause:** Daily learning job not executing

**Solution:**
1. **Check main.py loop:**
   - Verify `should_run_learning()` is being checked
   - Verify `run_daily_learning()` is being called

2. **Manually run daily learning to test:**
   ```bash
   cd /opt/render/project/src
   python src/daily_learning.py
   ```

3. **Check logs for errors:**
   - Look for errors during learning execution
   - Check if database is accessible

---

### Issue 5: All LLMs Performing Equally

**Symptom:** Enough data but weights stay at 25%

**Cause:** All LLMs have similar win rates/profit factors

**Solution:**
- This is actually normal! If all LLMs perform equally well, weights remain equal
- Check performance metrics to verify
- System is working correctly, just no differentiation yet

---

## 🔧 Quick Fixes

### Fix 1: Manually Trigger Daily Learning

```bash
cd /opt/render/project/src
python -c "
from src.daily_learning import run_daily_learning
run_daily_learning()
"
```

### Fix 2: Check if Recommendations Are Being Logged

```bash
cd /opt/render/project/src
python -c "
from src.trade_alerts_rl import RecommendationDatabase
import sqlite3

db = RecommendationDatabase()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM recommendations')
total = cursor.fetchone()[0]
print(f'Total recommendations: {total}')

# Check recent recommendations
cursor.execute('''
    SELECT timestamp, llm_source, pair, direction, outcome, evaluated
    FROM recommendations
    ORDER BY timestamp DESC
    LIMIT 10
''')
print('\nRecent recommendations:')
for row in cursor.fetchall():
    print(f'  {row[0][:19]}: {row[1]} {row[2]} {row[3]} - outcome={row[4]}, evaluated={row[5]}')

conn.close()
"
```

### Fix 3: Check Daily Learning Schedule

Look in main.py logs for:
- "🕚 Daily learning: 11:00 PM UTC"
- "🧠 DAILY LEARNING TIME (11pm UTC)"

---

## 📝 Next Steps After Diagnosis

1. **Run the diagnosis script** to identify the specific issue
2. **Apply the appropriate fix** based on diagnosis
3. **Wait 24 hours** and check again
4. **Verify daily learning runs** at next 11pm UTC

---

**Last Updated**: 2025-01-11  
**Status**: Diagnostic guide for RL not learning
