# Training RL System on Render

## Problem

You trained the RL system locally, but Render has its own separate database. The weights show 25% each because Render's database doesn't have the training data.

## Solution

Run the training script on Render to import the CSV data into Render's database.

---

## Method 1: Using Render Shell (Recommended)

### Step 1: Upload CSV to Render

**Option A: Use Render Web Shell (Recommended for Windows)**

1. Go to Render Dashboard → Your Service → Shell
2. In the web shell, navigate to the project directory:
   ```bash
   cd /opt/render/project/src
   ```
3. Create the CSV file using `nano` or `vi`:
   ```bash
   nano trade-alert-eval.csv
   ```
4. Copy the entire CSV content from your local file (`C:\Users\user\Downloads\trade-alert-eval - Sheet1.csv`)
5. Paste it into the editor (right-click or Ctrl+Shift+V)
6. Save and exit:
   - For `nano`: Press `Ctrl+X`, then `Y`, then `Enter`
   - For `vi`: Press `Esc`, type `:wq`, then `Enter`

**Option B: Use PowerShell with PSCP (if you have PuTTY installed)**

If you have PuTTY installed, you can use `pscp`:
```powershell
pscp "C:\Users\user\Downloads\trade-alert-eval - Sheet1.csv" YOUR_RENDER_USERNAME@YOUR_SERVICE.onrender.com:/opt/render/project/src/trade-alert-eval.csv
```

**Option C: Temporarily Commit to Git (Quick Alternative)**

If the CSV is not too large and not sensitive, you can:
1. Copy the CSV to your project directory temporarily
2. Commit and push it
3. Run training on Render
4. Delete and commit the deletion after training

### Step 2: Run Training Script

Once you're in the Render shell:

```bash
cd /opt/render/project/src

# Run training with CSV import
python train_rl_system.py --import-csv "trade-alert-eval - Sheet1.csv" --all

# OR if you uploaded with a different name:
python train_rl_system.py --import-csv "trade-alert-eval - Sheet1.csv" --all
```

### Step 3: Verify Weights Updated

After training completes, check the weights:

```bash
python -c "
from src.trade_alerts_rl import RecommendationDatabase, LLMLearningEngine
db = RecommendationDatabase()
engine = LLMLearningEngine(db)
weights = engine.calculate_llm_weights()
print('\n📊 Current LLM Weights:')
for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
    print(f'   {llm}: {weight*100:.1f}%')
"
```

Expected output:
```
📊 Current LLM Weights:
   synthesis: 39.0%
   gemini: 34.8%
   chatgpt: 22.6%
   claude: 3.5%
```

### Step 4: Restart Service

After training, restart the service so it loads the new weights:

1. Go to Render Dashboard → Your Service
2. Click "Manual Deploy" → "Clear build cache & deploy"
3. Or just restart the service

---

## Method 2: One-Time Job (Alternative)

If you prefer, you can create a one-time job in Render:

1. Go to Render Dashboard → Your Service → Jobs
2. Create a new job
3. Command: `python train_rl_system.py --import-csv "trade-alert-eval - Sheet1.csv" --all`
4. Run the job

---

## Method 3: Use Environment Variable for CSV Path

If you can't upload the CSV directly, you can:

1. Copy CSV content
2. Paste it into a file on Render using the shell
3. Run the training script

---

## Troubleshooting

### CSV File Not Found

Make sure the CSV file is in the same directory as `train_rl_system.py`:

```bash
cd /opt/render/project/src
ls -la *.csv
```

If the file isn't there, upload it first (see Step 1).

### Database Path

The database is at:
```
/opt/render/project/src/data/trade_alerts_rl.db
```

You can verify the database has data:

```bash
python -c "
from src.trade_alerts_rl import RecommendationDatabase
import sqlite3
db = RecommendationDatabase()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM recommendations')
total = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM recommendations WHERE evaluated = 1')
evaluated = cursor.fetchone()[0]
print(f'Total recommendations: {total}')
print(f'Evaluated: {evaluated}')
"
```

### Weights Still 25%

If weights are still 25% after training:

1. Check that you have 5+ evaluated recommendations per LLM:
   ```bash
   python -c "
   from src.trade_alerts_rl import RecommendationDatabase
   import sqlite3
   db = RecommendationDatabase()
   conn = sqlite3.connect(db.db_path)
   cursor = conn.cursor()
   for llm in ['chatgpt', 'gemini', 'claude', 'synthesis']:
       cursor.execute('SELECT COUNT(*) FROM recommendations WHERE llm_source = ? AND evaluated = 1', (llm,))
       count = cursor.fetchone()[0]
       print(f'{llm}: {count} evaluated recommendations')
   "
   ```

2. If any LLM has less than 5, the weights will default to 25%
3. Make sure the CSV import completed successfully

---

## Expected Results

After training on Render:

- **Total Recommendations**: 43+ (or however many are in your CSV)
- **Evaluated**: All imported recommendations should be evaluated
- **Weights**: Should show:
  - Synthesis: ~39%
  - Gemini: ~35%
  - ChatGPT: ~23%
  - Claude: ~4%

After restarting the service, the logs should show:
```
⚖️  Current LLM Weights: synthesis: 39%, gemini: 35%, chatgpt: 23%, claude: 4%
```

Instead of:
```
⚖️  Current LLM Weights: chatgpt: 25%, gemini: 25%, claude: 25%, synthesis: 25%
```

---

## Summary

**The key issue**: Weights are calculated dynamically from the database, not stored. Your local training didn't update Render's database.

**The solution**: Run the training script on Render to import the CSV data into Render's database.

**After training**: Restart the service, and it will load the new weights on startup.
