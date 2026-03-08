# Quick Training Guide - Import CSV and Train Immediately

## Overview

This guide shows you how to import your CSV file with 47 recommendations and train the RL system immediately.

---

## Step 1: Run Training Script

### Option A: Run All Steps (Recommended)

```bash
cd /opt/render/project/src  # On Render
# or
cd c:\Users\user\projects\personal\Trade-Alerts  # Locally

python train_rl_system.py --all
```

This will:
1. ✅ Import CSV recommendations
2. ✅ Evaluate them immediately using CSV price data
3. ✅ Calculate and save LLM weights
4. ✅ Generate performance report

### Option B: Step by Step

```bash
# 1. Import CSV
python train_rl_system.py --import-csv "trade-alert-eval - Sheet1.csv"

# 2. Evaluate any remaining pending recommendations
python train_rl_system.py --evaluate

# 3. Calculate weights
python train_rl_system.py --calculate-weights

# 4. Generate report
python train_rl_system.py --report
```

---

## Step 2: Verify Import

After running, check the database:

```python
python -c "
from src.trade_alerts_rl import RecommendationDatabase
db = RecommendationDatabase()
import sqlite3
conn = sqlite3.connect('trade_alerts_rl.db')
cursor = conn.cursor()

# Count total recommendations
cursor.execute('SELECT COUNT(*) FROM recommendations')
print(f'Total recommendations: {cursor.fetchone()[0]}')

# Count by LLM
cursor.execute('SELECT llm_source, COUNT(*) FROM recommendations GROUP BY llm_source')
print('\nBy LLM:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')

# Count evaluated
cursor.execute('SELECT COUNT(*) FROM recommendations WHERE evaluated = 1')
print(f'\nEvaluated: {cursor.fetchone()[0]}')

# Count by outcome
cursor.execute('SELECT outcome, COUNT(*) FROM recommendations WHERE evaluated = 1 GROUP BY outcome')
print('\nBy outcome:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')
"
```

---

## Step 3: Check Weights

After training, weights should be calculated:

```python
python -c "
from src.trade_alerts_rl import RecommendationDatabase, LLMLearningEngine
db = RecommendationDatabase()
engine = LLMLearningEngine(db)
weights = engine.calculate_llm_weights()
print('\nCurrent LLM Weights:')
for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
    print(f'  {llm}: {weight*100:.1f}%')
"
```

---

## Expected Results

After importing 47 recommendations:

- **Total Recommendations**: ~47 (or more if duplicates exist)
- **Evaluated**: ~47 (all should be evaluated immediately using CSV price data)
- **By LLM**: 
  - ChatGPT: ~13
  - Gemini: ~11
  - Claude: ~10
  - Synthesis: ~12
- **By Outcome**: Mix of WIN_TP1, LOSS_SL, MISSED, NEUTRAL
- **Weights**: Should be calculated (not all 25% anymore)

---

## Troubleshooting

### CSV Not Found

If you get "CSV file not found":
1. Provide full path: `--import-csv "C:\Users\user\Downloads\trade-alert-eval - Sheet1.csv"`
2. Or copy CSV to project directory first

### No Recommendations Imported

Check:
1. CSV format matches expected format
2. Date/Time format is correct
3. Entry prices are valid numbers
4. Check logs for specific errors

### Weights Still Equal (25%)

This means:
- Less than 5 evaluated recommendations per LLM
- Or evaluation didn't work properly
- Check evaluation logs for errors

---

## Next Steps

After training:
1. ✅ System will use new weights in next analysis
2. ✅ Daily learning will continue to update weights
3. ✅ New recommendations will be logged automatically
4. ✅ System will learn from new data going forward

---

## Running on Render

If running on Render:

```bash
# SSH into Render service
# Then:
cd /opt/render/project/src
python train_rl_system.py --all
```

Or add to a one-time script/job in Render dashboard.
