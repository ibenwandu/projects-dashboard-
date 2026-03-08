# EASIEST Method: Train RL System on Render (Windows)

## Problem with `nano` in Web Shell

Pasting large CSV files into `nano` in Render's web shell is unreliable and can cause issues (stale processes, paste not working, etc.).

## ✅ BEST Solution: Temporary Git Commit

This is the **easiest and most reliable** method for Windows users.

---

## Step-by-Step Instructions

### Step 1: Copy CSV to Project Directory

**On your local Windows machine:**

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
copy "C:\Users\user\Downloads\trade-alert-eval - Sheet1.csv" trade-alert-eval.csv
```

### Step 2: Commit and Push CSV

```powershell
git add trade-alert-eval.csv
git commit -m "Temporary: Add CSV for RL training"
git push
```

### Step 3: Wait for Render to Deploy

- Go to Render Dashboard → Your Service
- Wait for auto-deploy to complete (or manually trigger deploy)
- This should only take 1-2 minutes

### Step 4: Run Training on Render

Once deployed, use Render's web shell:

1. Go to Render Dashboard → Your Service → **Shell**
2. Run:
   ```bash
   cd /opt/render/project/src
   python train_rl_system.py --import-csv trade-alert-eval.csv --all
   ```

Wait for it to complete. You should see:
- "Imported X recommendations"
- "Evaluated X recommendations"
- "Updated LLM Weights: ..."

### Step 5: Verify Weights Updated

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

Expected output (should NOT be all 25%):
```
📊 Current LLM Weights:
   synthesis: 39.0%
   gemini: 34.8%
   chatgpt: 22.6%
   claude: 3.5%
```

### Step 6: Remove CSV from Git

**Back on your local machine:**

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
git rm trade-alert-eval.csv
git commit -m "Remove temporary CSV file"
git push
```

This removes the CSV from the repository (but Render still has it locally for training).

### Step 7: Restart Service

1. Go back to Render Dashboard → Your Service
2. Click **"Manual Deploy"** → **"Clear build cache & deploy"**
3. Or click **"Restart"** if available

### Step 8: Check Logs

After restart, check the logs. You should see:
```
⚖️  Current LLM Weights: synthesis: 39%, gemini: 35%, chatgpt: 23%, claude: 4%
```

Instead of:
```
⚖️  Current LLM Weights: chatgpt: 25%, gemini: 25%, claude: 25%, synthesis: 25%
```

---

## Why This Method is Best

✅ **No paste issues** - File is already on server after deploy  
✅ **No stale processes** - No need for `nano`  
✅ **Works reliably** - Git push/pull is standard workflow  
✅ **Easy cleanup** - Just remove file from git  
✅ **Windows-friendly** - Uses standard PowerShell commands  

---

## Troubleshooting

### File Not Found on Render

If the CSV file isn't found:
```bash
cd /opt/render/project/src
ls -la trade-alert-eval.csv  # Check if file exists
```

If it doesn't exist, make sure:
1. Git push completed successfully
2. Render deployment completed
3. File is in the root of the project (same directory as `train_rl_system.py`)

### Weights Still 25%

Check that you have enough evaluated recommendations:
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
    print(f'{llm}: {count} evaluated')
"
```

Each LLM needs 5+ evaluated recommendations.

---

## Summary

**Use Git commit method** - It's the easiest and most reliable for Windows users.

**No `nano` needed** - Avoids paste issues and stale processes.

**Quick and simple** - Just copy, commit, push, train, remove.
