# Check RL Database Status

## Quick Check: Are Recommendations Being Logged?

Run this to see if recommendations exist in the database:

```bash
cd /opt/render/project/src
python -c "
from src.trade_alerts_rl import RecommendationDatabase
import sqlite3

db = RecommendationDatabase()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

# Total recommendations
cursor.execute('SELECT COUNT(*) FROM recommendations')
total = cursor.fetchone()[0]
print(f'📊 Total Recommendations in Database: {total}')

if total > 0:
    # By LLM
    cursor.execute('''
        SELECT llm_source, COUNT(*) as count
        FROM recommendations
        GROUP BY llm_source
    ''')
    print('\n📋 Recommendations by LLM:')
    for llm, count in cursor.fetchall():
        print(f'   {llm}: {count}')
    
    # Status breakdown
    cursor.execute('''
        SELECT evaluated, COUNT(*) as count
        FROM recommendations
        GROUP BY evaluated
    ''')
    print('\n📊 Status:')
    for evaluated, count in cursor.fetchall():
        status = 'Evaluated' if evaluated == 1 else 'Pending'
        print(f'   {status}: {count}')
    
    # Recent recommendations
    cursor.execute('''
        SELECT timestamp, llm_source, pair, direction, evaluated, outcome
        FROM recommendations
        ORDER BY timestamp DESC
        LIMIT 10
    ''')
    print('\n📅 Recent Recommendations:')
    for ts, llm, pair, direction, evaluated, outcome in cursor.fetchall():
        eval_status = '✅ Evaluated' if evaluated == 1 else '⏳ Pending'
        print(f'   {ts[:19]}: {llm} {pair} {direction} - {eval_status} ({outcome})')
else:
    print('\n❌ NO RECOMMENDATIONS IN DATABASE!')
    print('   → Recommendations are NOT being logged')
    print('   → Check if analysis is running and logging recommendations')
    print('   → Look for \"Step 7 (NEW): Logging recommendations\" in logs')

conn.close()
"
```

---

## If Total = 0: Recommendations Not Being Logged

**Problem:** The analysis runs but recommendations aren't being saved to the database.

**Check logs for:**
- "Step 7 (NEW): Logging recommendations to RL database..."
- "✅ Logged X recommendations for future learning"

**If you see errors, check:**
- Database file permissions
- Database file path
- Errors during logging

---

## If Total > 0 but All Pending: Too New

**Problem:** Recommendations exist but are all < 4 hours old.

**Solution:** Wait for recommendations to age (need 4+ hours old for evaluation)

**Check age:**
```bash
cd /opt/render/project/src
python -c "
from src.trade_alerts_rl import RecommendationDatabase
import sqlite3
from datetime import datetime, timedelta

db = RecommendationDatabase()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM recommendations WHERE evaluated = 0')
row = cursor.fetchone()
if row and row[0]:
    oldest = datetime.fromisoformat(row[0])
    newest = datetime.fromisoformat(row[1]) if row[1] else datetime.utcnow()
    age_hours = (datetime.utcnow() - oldest).total_seconds() / 3600
    print(f'Oldest pending recommendation: {age_hours:.1f} hours old')
    print(f'Need 4+ hours old for evaluation')
    print(f'Wait {max(0, 4 - age_hours):.1f} more hours')
else:
    print('No pending recommendations')

conn.close()
"
```

---

## Next Steps

1. **Run the check script above** to see total recommendations
2. **If 0:** Check if analysis is logging recommendations (Step 7 in logs)
3. **If > 0 but all pending:** Wait for them to age (4+ hours)
4. **If some evaluated but weights still 25%:** Need 5+ evaluated per LLM
