# How to Check RL Improvement in Trade-Alerts

## Overview

Trade-Alerts uses a **Reinforcement Learning (RL) system** that:
1. **Tracks all recommendations** from ChatGPT, Gemini, Claude, and Synthesis
2. **Evaluates outcomes** (wins/losses) after 4+ hours
3. **Calculates performance weights** for each LLM based on win rate and profit factor
4. **Updates weights daily** at 11pm UTC
5. **Uses adjusted weights** to emphasize better-performing LLMs in recommendations

**Key Indicator of Improvement:** LLM weights change from equal (25% each) to weighted based on performance (e.g., 40%, 30%, 20%, 10%).

---

## 🔍 Method 1: Check Current LLM Weights (Quick Check)

The RL system adjusts weights for ChatGPT, Gemini, Claude, and the Synthesis (Gemini final). Weights indicate which LLM has performed better.

### Via Logs (Automatic Display)

**In Render Dashboard → `trade-alerts` → Logs:**

Look for initialization messages showing current weights:
```
⚖️  Current LLM Weights: chatgpt: 25%, gemini: 25%, claude: 25%, synthesis: 25%
```

**If weights are NOT equal (e.g., `chatgpt: 40%, gemini: 30%, claude: 20%, synthesis: 10%`):**
- ✅ RL has learned from past performance
- ✅ Higher weights = better historical performance
- ✅ System is adapting based on results
- **This is the PRIMARY indicator of improvement**

**If weights ARE equal (25% each):**
- ⚠️ Either no learning has occurred yet (need < 5 evaluated recommendations per LLM), OR
- ⚠️ All LLMs performed equally, OR
- ⚠️ Not enough data to differentiate

### Via Email (Easiest Method!)

**Check your Trade-Alerts email** - The RL insights are included in every email:

Look for the section at the bottom:
```
================================================================================
🧠 MACHINE LEARNING INSIGHTS (Based on Historical Performance)
================================================================================

📊 LLM Performance Weights (Based on Past Accuracy):
  • CHATGPT: 40% weight (Win Rate: 65%, Avg P&L: 45 pips)
  • GEMINI: 30% weight (Win Rate: 58%, Avg P&L: 32 pips)
  • CLAUDE: 20% weight (Win Rate: 52%, Avg P&L: 18 pips)
  • SYNTHESIS: 10% weight (Win Rate: 48%, Avg P&L: 12 pips)

🎯 Consensus Analysis:
  • ALL_AGREE: 72.0% win rate (45 historical trades)
  • 2_AGREE: 58.0% win rate (32 historical trades)

🏆 Highest Accuracy: CHATGPT (40% confidence weight)

💡 Recommendation:
  Based on historical performance, prioritize trades where:
  1. CHATGPT agrees (highest accuracy)
  2. All 3 LLMs agree (best win rate)
  3. Consider reducing position size when LLMs disagree
```

**This shows:**
- Current weights (if not 25% each, RL is working!)
- Win rates per LLM
- Consensus analysis
- Recommendations based on performance

---

## 🔍 Method 2: Query RL Database Directly

### Step 1: Access Render Shell

**In Render Dashboard → `trade-alerts` → Shell:**

### Step 2: Query the Database

```bash
cd /opt/render/project/src
python -c "
from src.trade_alerts_rl import RecommendationDatabase
import sqlite3

db = RecommendationDatabase()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

# Get total recommendations logged
cursor.execute('SELECT COUNT(*) FROM recommendations')
total = cursor.fetchone()[0]
print(f'Total recommendations logged: {total}')

# Get recommendations by LLM
cursor.execute('''
    SELECT llm_source, COUNT(*) as count
    FROM recommendations
    GROUP BY llm_source
    ORDER BY count DESC
''')
print('\nRecommendations by LLM:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')

# Get recommendations with outcomes (evaluated = 1)
cursor.execute('''
    SELECT llm_source, 
           COUNT(*) as total,
           SUM(CASE WHEN outcome IN ('WIN_TP1', 'WIN_TP2') THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN outcome = 'LOSS_SL' THEN 1 ELSE 0 END) as losses,
           SUM(CASE WHEN outcome = 'MISSED' THEN 1 ELSE 0 END) as missed
    FROM recommendations
    WHERE evaluated = 1
    GROUP BY llm_source
''')
results = cursor.fetchall()
if results:
    print('\nPerformance by LLM (with outcomes):')
    for row in results:
        llm, total, wins, losses, missed = row
        win_rate = (wins / total * 100) if total > 0 else 0
        print(f'  {llm}: {wins} wins, {losses} losses, {missed} missed (Win Rate: {win_rate:.1f}%)')
else:
    print('\n⚠️  No outcomes recorded yet (recommendations logged but not evaluated)')

conn.close()
"
```

---

## 🔍 Method 3: Check Learning Engine Statistics (Best Method)

### Query Learning Engine Stats

```bash
cd /opt/render/project/src
python -c "
from src.trade_alerts_rl import RecommendationDatabase, LLMLearningEngine

db = RecommendationDatabase()
engine = LLMLearningEngine(db)

# Get current weights
weights = engine.calculate_llm_weights()
print('Current LLM Weights (from RL):')
for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
    print(f'  {llm}: {weight*100:.1f}%')

# Generate performance report
report = engine.generate_performance_report()
print('\n📊 LLM Performance Statistics:')
for llm, stats in report['llm_performance'].items():
    if stats['total_recs'] > 0:
        print(f'\n  {llm.upper()}:')
        print(f'    Total Recommendations: {stats[\"total_recs\"]}')
        print(f'    Win Rate: {stats[\"win_rate\"]*100:.1f}%')
        print(f'    Avg P&L: {stats[\"avg_pnl\"]:.1f} pips')
        print(f'    Profit Factor: {stats[\"profit_factor\"]:.2f}')

print('\n🎯 Consensus Analysis:')
for consensus_type, stats in report['consensus_analysis'].items():
    if stats['sample_size'] > 0:
        print(f'  {consensus_type}:')
        print(f'    Win Rate: {stats[\"win_rate\"]*100:.1f}%')
        print(f'    Sample Size: {stats[\"sample_size\"]}')
        print(f'    Avg P&L: {stats[\"avg_pnl\"]:.1f} pips')
"
```

---

## 🔍 Method 4: Check Daily Learning Runs & Weight History

The system runs daily learning at 11pm UTC to update weights based on new outcomes.

### Check Learning Logs

**In Render Dashboard → `trade-alerts` → Logs:**

Look for daily learning messages (around 11pm UTC / 6-7pm EST):
```
================================================================================
DAILY LEARNING CYCLE - 2026-01-11 23:00:00 UTC
================================================================================

Step 1: Fetching pending recommendations...
Step 2: Evaluating outcomes...
✅ Evaluated X new recommendations

Step 3: Recalculating LLM performance weights...
🎯 Updated LLM Weights:
  chatgpt: 35.0%
  gemini: 30.0%
  claude: 20.0%
  synthesis: 15.0%
```

### Check Learning Checkpoints (Weight History)

**Query weight history to see improvements over time:**

```bash
cd /opt/render/project/src
python -c "
from src.trade_alerts_rl import RecommendationDatabase
import sqlite3

db = RecommendationDatabase()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

# Get all learning checkpoints (weight history)
cursor.execute('''
    SELECT timestamp, 
           chatgpt_weight, gemini_weight, claude_weight, synthesis_weight,
           overall_win_rate, total_evaluated, notes
    FROM learning_checkpoints
    ORDER BY timestamp DESC
    LIMIT 10
''')

checkpoints = cursor.fetchall()
if checkpoints:
    print('📚 Learning Checkpoint History (Weight Changes Over Time):')
    print('='*80)
    for row in checkpoints:
        ts, cg, gm, cl, syn, win_rate, total, notes = row
        ts_short = ts[:19] if ts else 'N/A'
        print(f'\n{ts_short} UTC:')
        print(f'  Weights: ChatGPT={cg*100:.0f}%, Gemini={gm*100:.0f}%, Claude={cl*100:.0f}%, Synthesis={syn*100:.0f}%')
        print(f'  Overall Win Rate: {win_rate*100:.1f}% (Total Evaluated: {total})')
        if notes:
            print(f'  Notes: {notes}')
    
    # Show improvement trend
    if len(checkpoints) > 1:
        latest = checkpoints[0]
        oldest = checkpoints[-1]
        print('\n📈 Improvement Trend:')
        print(f'  Oldest Checkpoint: ChatGPT={oldest[1]*100:.0f}%, Gemini={oldest[2]*100:.0f}%')
        print(f'  Latest Checkpoint: ChatGPT={latest[1]*100:.0f}%, Gemini={latest[2]*100:.0f}%')
        print(f'  Change: ChatGPT {((latest[1]-oldest[1])*100):+.0f}%, Gemini {((latest[2]-oldest[2])*100):+.0f}%')
else:
    print('⚠️  No learning checkpoints found yet (daily learning may not have run)')

conn.close()
"
```

---

## 📊 Method 5: Compare Weights Over Time

### Check Database for Weight History (if stored)

The system may not store weight history, but you can track changes by:

1. **Saving current weights periodically** (manual tracking)
2. **Checking logs for weight changes**
3. **Comparing current weights to initial (25% each)**

---

## ✅ Signs of Improvement

### Indicators that RL is working:

1. **Weights are NOT equal (25% each)**
   - Example: `chatgpt: 40%, gemini: 30%, claude: 20%, synthesis: 10%`
   - Higher weights = better historical performance
   - ✅ **This is the primary indicator of improvement**

2. **Weights change over time**
   - Compare current weights to previous checkpoints
   - Check `learning_checkpoints` table for weight history
   - If weights shift toward better-performing LLMs, RL is working

3. **Database has logged recommendations**
   - Check total count: `SELECT COUNT(*) FROM recommendations`
   - More data = more reliable learning

4. **Recommendations have outcomes recorded**
   - Outcomes (WIN_TP1, WIN_TP2, LOSS_SL, MISSED) are needed for RL to learn
   - Check: `SELECT COUNT(*) FROM recommendations WHERE evaluated = 1`
   - More evaluated recommendations = better learning

5. **Daily learning runs successfully**
   - Check logs for daily learning execution (11pm UTC)
   - Look for: "DAILY LEARNING CYCLE" messages
   - Should see weight updates after learning runs

6. **Performance metrics show differentiation**
   - If one LLM has significantly higher win rate than others
   - If profit factors differ between LLMs
   - RL should increase weights for better performers

---

## ⚠️ Common Issues

### No Improvement Detected?

**Possible reasons:**

1. **Not enough data**
   - Need sufficient recommendations logged
   - Need outcomes (win/loss) recorded
   - RL needs time to learn

2. **No outcomes recorded**
   - Recommendations are logged, but outcomes aren't being recorded
   - Check if outcome tracking is implemented

3. **All LLMs performing equally**
   - If all LLMs have similar performance, weights remain equal

4. **Daily learning not running**
   - Check if `daily_learning.py` is being called
   - Check logs for learning execution

---

## 🔧 Check Database Location

The RL database is stored at:
- **On Render**: `/opt/render/project/src/trade_alerts_rl.db` (or project root)
- **Check database file:**
  ```bash
  cd /opt/render/project/src
  ls -la *.db
  ```

---

## 📋 Quick Check Script (Recommended)

**Run this comprehensive check script:**

```bash
cd /opt/render/project/src
python << 'EOF'
from src.trade_alerts_rl import RecommendationDatabase, LLMLearningEngine
import sqlite3

db = RecommendationDatabase()
engine = LLMLearningEngine(db)

print("="*60)
print("RL System Status Check")
print("="*60)

# Get current weights
weights = engine.calculate_llm_weights()
print("\n📊 Current LLM Weights:")
for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
    print(f"   {llm}: {weight*100:.1f}%")

# Check database
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM recommendations')
total = cursor.fetchone()[0]
print(f"\n📈 Total Recommendations Logged: {total}")

cursor.execute('SELECT COUNT(*) FROM recommendations WHERE evaluated = 1')
with_outcomes = cursor.fetchone()[0]
print(f"✅ Recommendations with Outcomes: {with_outcomes}")

if with_outcomes > 0:
    cursor.execute('''
        SELECT llm_source,
               COUNT(*) as total,
               SUM(CASE WHEN outcome IN ('WIN_TP1', 'WIN_TP2') THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN outcome = 'LOSS_SL' THEN 1 ELSE 0 END) as losses,
               SUM(CASE WHEN outcome = 'MISSED' THEN 1 ELSE 0 END) as missed,
               AVG(CASE WHEN outcome IN ('WIN_TP1', 'WIN_TP2', 'LOSS_SL') THEN pnl_pips ELSE NULL END) as avg_pnl
        FROM recommendations
        WHERE evaluated = 1
        GROUP BY llm_source
        ORDER BY wins DESC
    ''')
    
    print("\n🎯 Performance by LLM:")
    for row in cursor.fetchall():
        llm, total, wins, losses, missed, avg_pnl = row
        win_rate = (wins / total * 100) if total > 0 else 0
        avg_pnl_str = f"{avg_pnl:.1f}" if avg_pnl else "N/A"
        print(f"   {llm}: {wins}W / {losses}L / {missed}M (Win Rate: {win_rate:.1f}%, Avg P&L: {avg_pnl_str} pips)")

# Check learning checkpoints (weight history)
cursor.execute('SELECT COUNT(*) FROM learning_checkpoints')
checkpoint_count = cursor.fetchone()[0]
print(f"\n📚 Learning Checkpoints (Weight History): {checkpoint_count}")

if checkpoint_count > 0:
    cursor.execute('''
        SELECT timestamp, chatgpt_weight, gemini_weight, claude_weight, synthesis_weight, overall_win_rate
        FROM learning_checkpoints
        ORDER BY timestamp DESC
        LIMIT 5
    ''')
    print("\n📈 Recent Weight History:")
    for row in cursor.fetchall():
        ts, cg, gm, cl, syn, win_rate = row
        ts_short = ts[:10] if ts else "N/A"
        print(f"   {ts_short}: ChatGPT={cg*100:.0f}%, Gemini={gm*100:.0f}%, Claude={cl*100:.0f}%, Synthesis={syn*100:.0f}% (Win Rate: {win_rate*100:.1f}%)")

conn.close()

# Generate performance report
report = engine.generate_performance_report()
if report['llm_performance']:
    print("\n📊 Detailed Performance Report:")
    for llm, stats in report['llm_performance'].items():
        if stats['total_recs'] > 0:
            print(f"\n   {llm.upper()}:")
            print(f"     Total: {stats['total_recs']} recommendations")
            print(f"     Win Rate: {stats['win_rate']*100:.1f}%")
            print(f"     Avg P&L: {stats['avg_pnl']:.1f} pips")
            print(f"     Profit Factor: {stats['profit_factor']:.2f}")

print("\n" + "="*60)
EOF
```

---

## 📝 Next Steps

1. **Run the quick check script** (Method 3 or the script above) to see current RL status
2. **Monitor weights over time** - Check weights periodically and compare to see if they're changing
3. **Check daily learning logs** - Verify learning is running at 11pm UTC and updating weights
4. **Review weight history** - Use Method 4 to see how weights have changed over time
5. **Check for outcomes** - Ensure recommendations have outcomes recorded (evaluated = 1)

---

## 🎯 How to Interpret Results

### ✅ RL is Improving If:

1. **Weights differ from 25% each** - Shows RL has learned which LLMs perform better
2. **Weights change over time** - Shows RL is adapting to new performance data
3. **Higher-weighted LLMs have better metrics** - Validates that RL is correctly identifying good performers
4. **Overall win rate increases over time** - Shows system is improving

### ⚠️ RL Not Improving If:

1. **Weights remain 25% each** - Either:
   - Not enough data (< 5 evaluated recommendations per LLM)
   - All LLMs performing equally
   - Outcomes not being recorded
   - Daily learning not running

2. **Weights don't change** - Either:
   - Daily learning not running
   - No new outcomes to learn from
   - Performance remains stable

---

## 💡 Quick Summary Command

**One command to check everything:**

```bash
cd /opt/render/project/src && python -c "from src.trade_alerts_rl import RecommendationDatabase, LLMLearningEngine; db = RecommendationDatabase(); engine = LLMLearningEngine(db); weights = engine.calculate_llm_weights(); print('Current Weights:'); [print(f'  {k}: {v*100:.1f}%') for k, v in sorted(weights.items(), key=lambda x: x[1], reverse=True)]; report = engine.generate_performance_report(); print('\nPerformance:'); [print(f'{llm}: {stats[\"win_rate\"]*100:.1f}% win rate ({stats[\"total_recs\"]} recs)') for llm, stats in report['llm_performance'].items() if stats['total_recs'] > 0]"
```

---

**Last Updated**: 2025-01-11  
**Status**: ✅ Complete guide for checking RL improvement
