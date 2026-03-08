# Quick Guide: Training on Render (Windows)

## The Easiest Method: Use Render Web Shell

Since you're on Windows and `scp` isn't available, use Render's web shell to upload the CSV.

---

## Step-by-Step Instructions

### Step 1: Open Render Shell

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click on your `trade-alerts` service
3. Click on **"Shell"** tab (in the left sidebar)
4. Wait for the shell to connect

### Step 2: Navigate to Project Directory

In the Render shell, type:
```bash
cd /opt/render/project/src
pwd  # Should show: /opt/render/project/src
```

### Step 3: Create CSV File

**Method A: Using `nano` (Easier for beginners)**

```bash
nano trade-alert-eval.csv
```

1. This opens the `nano` editor
2. Open your local CSV file: `C:\Users\user\Downloads\trade-alert-eval - Sheet1.csv`
3. **Select All** (Ctrl+A) and **Copy** (Ctrl+C)
4. Go back to the Render shell (click in the browser window)
5. **Paste** the CSV content (Right-click → Paste, or Ctrl+Shift+V)
6. Save and exit:
   - Press `Ctrl+X`
   - Press `Y` (to confirm)
   - Press `Enter`

**Method B: Using `cat` with heredoc**

```bash
cat > trade-alert-eval.csv << 'EOF'
[paste your CSV content here]
EOF
```

Then paste your CSV content, and press `Ctrl+D` twice when done.

### Step 4: Verify File Uploaded

```bash
ls -lh trade-alert-eval.csv
head -5 trade-alert-eval.csv  # Show first 5 lines
```

You should see the CSV file and its content.

### Step 5: Run Training Script

```bash
python train_rl_system.py --import-csv trade-alert-eval.csv --all
```

Wait for it to complete. You should see:
- "Imported X recommendations"
- "Evaluated X recommendations"
- "Updated LLM Weights: ..."

### Step 6: Verify Weights Updated

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

## Troubleshooting

### File Not Found

If you get "CSV file not found":
```bash
cd /opt/render/project/src
ls -la *.csv  # Check if file exists
pwd  # Make sure you're in the right directory
```

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

Each LLM needs 5+ evaluated recommendations. If any has less, weights default to 25%.

### CSV Content Issues

If the CSV has issues, try opening it in a text editor first and:
1. Remove any BOM (Byte Order Mark)
2. Ensure proper line endings
3. Check for special characters

---

## ⭐ RECOMMENDED: Temporary Git Commit (Easier than `nano`)

**This is the easiest method for Windows users** - avoids paste issues in `nano`:

1. **On your local machine:**
   ```powershell
   cd C:\Users\user\projects\personal\Trade-Alerts
   copy "C:\Users\user\Downloads\trade-alert-eval - Sheet1.csv" trade-alert-eval.csv
   git add trade-alert-eval.csv
   git commit -m "Temporary: Add CSV for training"
   git push
   ```

2. **On Render:**
   - Wait for auto-deploy (or manually deploy)
   - Run: `python train_rl_system.py --import-csv trade-alert-eval.csv --all`

3. **Clean up (after training):**
   ```powershell
   git rm trade-alert-eval.csv
   git commit -m "Remove temporary CSV"
   git push
   ```

---

## Summary

**Recommended Method**: Use Render's web shell with `nano` editor to paste CSV content.

**Why it works**: Render's web shell gives you direct access to the server, and `nano` is the easiest editor for copying/pasting content.

**After training**: Restart the service to load the new weights.
