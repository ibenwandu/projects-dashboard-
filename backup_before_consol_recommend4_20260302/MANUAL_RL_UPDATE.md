# Manual RL Update from Google Drive

## Quick Guide: Update RL Weights from Updated Trade-Alert-Eval Sheet

Since the automated daily learning isn't working, use this manual process to update RL weights from your Google Drive evaluation sheet.

---

## Step 1: Download Updated CSV from Google Drive

1. **Go to Google Drive**: Open the "Trade-Alert-Eval" folder
2. **Open** the "trade-alert-eval" sheet
3. **File → Download → Comma-separated values (.csv)**
4. **Save** the file (it will download as `trade-alert-eval - Sheet1.csv` or similar)

---

## Step 2: Upload CSV to Render (Easiest Method)

### Option A: Temporary Git Commit (Recommended)

**On your local Windows machine:**

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts

# Copy downloaded CSV to project directory
# (adjust path if your download location is different)
copy "C:\Users\user\Downloads\trade-alert-eval*.csv" trade-alert-eval.csv

# Commit and push
git add trade-alert-eval.csv
git commit -m "Manual RL update: Import latest evaluation data"
git push
```

**Wait 1-2 minutes** for Render to auto-deploy.

---

## Step 3: Run Training on Render

**Render Dashboard → `trade-alerts` → Shell:**

```bash
cd /opt/render/project/src
python train_rl_system.py --import-csv trade-alert-eval.csv --all

# OR if CSV is in src/ directory:
python train_rl_system.py --import-csv /opt/render/project/src/trade-alert-eval.csv --all
```

**Expected output:**
```
📥 Importing recommendations from: trade-alert-eval.csv
✅ Successfully imported X recommendations
✅ Evaluated X recommendations
✅ Updated LLM Weights
🎯 Updated LLM Weights (will be used in next analysis):
   SYNTHESIS: 39.0%
   GEMINI: 34.8%
   CHATGPT: 22.6%
   CLAUDE: 3.5%
```

---

## Step 4: Verify Weights Updated

**Still in Render Shell:**

```bash
python -c "
from src.trade_alerts_rl import RecommendationDatabase, LLMLearningEngine
db = RecommendationDatabase()
engine = LLMLearningEngine(db)
weights = engine.calculate_llm_weights()
print('\n📊 Current LLM Weights:')
for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
    print(f'   {llm.upper()}: {weight*100:.1f}%')
"
```

**Should show updated weights** (NOT all 25%).

---

## Step 5: Clean Up (Optional)

**Remove CSV from git** (if you don't want it in version control):

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
git rm trade-alert-eval.csv
git commit -m "Remove temporary CSV file"
git push
```

---

## Alternative: Download Directly in Render Shell

If you prefer not to commit to git:

### Step 1: Get Google Drive Download Link

1. **Right-click** the CSV file in Google Drive
2. **Get link** → **Anyone with the link** → **Copy link**
3. Replace `/view?usp=sharing` with `/export?format=csv&gid=0`
   - Example: `https://drive.google.com/file/d/FILE_ID/view?usp=sharing`
   - Becomes: `https://drive.google.com/uc?export=download&id=FILE_ID`

### Step 2: Download in Render Shell

**Render Dashboard → `trade-alerts` → Shell:**

```bash
cd /opt/render/project

# Download CSV (replace FILE_ID with actual ID from your link)
wget "https://drive.google.com/uc?export=download&id=YOUR_FILE_ID" -O trade-alert-eval.csv

# Verify download
ls -lh trade-alert-eval.csv
head -5 trade-alert-eval.csv

# Run training
python train_rl_system.py --import-csv trade-alert-eval.csv --all
```

---

## Troubleshooting

### CSV Not Found

**If you see "CSV file not found":**

```bash
# Check current directory
pwd

# List files
ls -la *.csv

# If CSV is in a different location, provide full path:
python train_rl_system.py --import-csv /opt/render/project/trade-alert-eval.csv --all
```

### Import Shows 0 Recommendations

**Check CSV format:**
- Must have headers: `timestamp`, `llm_source`, `pair`, `direction`, `entry_price`, etc.
- Must be comma-separated (not semicolon or tab)

**Verify CSV:**
```bash
head -10 trade-alert-eval.csv
```

---

## Quick Reference

**Complete workflow (when you update the Google Drive sheet):**

1. **Download** CSV from Google Drive
2. **Copy** to Trade-Alerts project directory
3. **Commit & Push** to git
4. **Wait** for Render deployment
5. **Run** `python train_rl_system.py --import-csv trade-alert-eval.csv --all`
6. **Verify** weights updated
7. **Clean up** (remove CSV from git)

**Time:** ~5-10 minutes total

---

## What Gets Updated

When you run the training script with `--all`:

1. ✅ **Imports** all recommendations from CSV (new + existing)
2. ✅ **Evaluates** outcomes using price data from CSV
3. ✅ **Calculates** new LLM weights based on performance
4. ✅ **Saves** weights to database
5. ✅ **Generates** performance report

**Next analysis run will use the updated weights!**
