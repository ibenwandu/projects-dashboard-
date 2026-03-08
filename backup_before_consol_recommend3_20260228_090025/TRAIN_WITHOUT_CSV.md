# Train RL System Without CSV in Git

## Situation

You've already removed the CSV file from git, but need to train the RL system on Render. Here's how to do it without re-adding the CSV to git.

---

## Method: Create CSV Directly in Render Shell

### Step 1: Wait for Persistent Disk Fix to Deploy

Wait for Render to deploy the persistent disk fix (the code update that uses `/var/data/trade_alerts_rl.db`).

Check Render Dashboard → Your Service → Logs to see when deployment completes.

### Step 2: Open Render Shell

1. Go to Render Dashboard → Your Service → **Shell**
2. Wait for shell to connect

### Step 3: Create CSV File Using `cat` (Easier than `nano`)

In the Render shell:

```bash
cd /opt/render/project/src
cat > trade-alert-eval.csv << 'ENDOFFILE'
```

Then:
1. Open your local CSV file: `C:\Users\user\Downloads\trade-alert-eval - Sheet1.csv`
2. **Select All** (Ctrl+A) and **Copy** (Ctrl+C)
3. Go back to Render shell
4. **Right-click** in the terminal window to paste (or Ctrl+Shift+V)
5. Press **Enter**
6. Type `ENDOFFILE` and press **Enter** (to close the heredoc)

**Note**: The `cat > file << 'ENDOFFILE'` command waits for you to paste content, then type `ENDOFFILE` to finish.

### Step 4: Verify CSV File

```bash
ls -lh trade-alert-eval.csv
head -5 trade-alert-eval.csv  # Show first 5 lines
wc -l trade-alert-eval.csv    # Count lines (should be ~48 for 47 recommendations)
```

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

### Step 7: Clean Up (Optional)

You can delete the CSV file from Render after training:

```bash
rm trade-alert-eval.csv
```

The database is now on the persistent disk (`/var/data/trade_alerts_rl.db`), so it will survive future deployments!

---

## Why This Works

1. ✅ CSV file is created directly on Render (no git needed)
2. ✅ Training imports data into database
3. ✅ Database is now on persistent disk (`/var/data/trade_alerts_rl.db`)
4. ✅ Database persists across deployments
5. ✅ Weights will survive future redeploys

---

## Alternative: Re-Add CSV to Git (If Paste Doesn't Work)

If the paste method is too difficult, you can temporarily re-add the CSV to git:

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
copy "C:\Users\user\Downloads\trade-alert-eval - Sheet1.csv" trade-alert-eval.csv
git add trade-alert-eval.csv
git commit -m "Temporary: Re-add CSV for training"
git push
```

Then after training:
```powershell
git rm trade-alert-eval.csv
git commit -m "Remove temporary CSV"
git push
```

---

## Summary

**Recommended**: Create CSV directly in Render shell using `cat` heredoc method.

**Why**: No git commits needed, faster, and database will persist on persistent disk.

**After training**: Database persists on `/var/data/`, so weights survive deployments!
