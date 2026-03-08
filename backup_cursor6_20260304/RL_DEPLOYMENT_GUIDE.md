# RL System Deployment Guide

## 🚀 Step-by-Step Deployment

### Step 1: Run Historical Backfill Locally (One Time)

First, initialize the RL system by processing all historical files:

```bash
cd personal/Trade-Alerts
python historical_backfill.py
```

**What to expect:**
- Downloads all historical files from Google Drive
- Parses recommendations
- Evaluates outcomes
- Calculates initial LLM weights
- Creates `trade_alerts_rl.db` database

**Success indicators:**
- ✅ Processed X files
- ✅ Logged X recommendations
- ✅ Evaluated X outcomes
- ✅ LLM weights calculated

**Note:** This may take 10-30 minutes depending on how many historical files you have.

---

### Step 2: Install/Update Dependencies

Make sure all new dependencies are installed:

```bash
pip install yfinance pandas numpy
```

Or reinstall all:
```bash
pip install -r requirements.txt
```

---

### Step 3: Test Locally (Optional but Recommended)

Test that the enhanced system works:

```bash
python main.py
```

**What to check:**
- System starts without errors
- Shows "🧠 RL System: Active"
- Shows current LLM weights
- Logs recommendations when analysis runs

Press `Ctrl+C` to stop after verifying it works.

---

### Step 4: Commit and Push Changes

Commit all the new RL files:

```bash
git add .
git commit -m "Add RL system: learning from historical and ongoing recommendations"
git push origin main
```

**Files to commit:**
- `src/trade_alerts_rl.py` (NEW)
- `src/daily_learning.py` (NEW)
- `historical_backfill.py` (NEW)
- `main.py` (MODIFIED)
- `requirements.txt` (MODIFIED)
- `RL_*.md` documentation files (NEW)

---

### Step 5: Deploy to Render

#### Option A: If Using Render Web Service

1. **Go to Render Dashboard**
   - Navigate to your Trade-Alerts service
   - Go to "Settings" → "Build & Deploy"

2. **Update Build Command** (if needed)
   ```bash
   pip install -r requirements.txt
   ```

3. **Deploy**
   - Render will automatically detect the push
   - Wait for deployment to complete (2-5 minutes)

#### Option B: If Using Render Background Worker

1. **Go to Render Dashboard**
   - Navigate to your Trade-Alerts worker service
   - The `Procfile` should already have: `worker: python main.py`

2. **Verify Environment Variables**
   - All existing env vars should still be set
   - No new env vars needed for RL system

3. **Deploy**
   - Render will auto-deploy on push
   - Check logs to verify RL system is active

---

### Step 6: Add Daily Learning Scheduled Job

**This is critical!** The daily learning job updates weights every day.

#### On Render:

1. **Go to Render Dashboard**
2. **Create New Cron Job:**
   - **Name:** `trade-alerts-daily-learning`
   - **Schedule:** `0 23 * * *` (11pm UTC daily)
   - **Command:** `cd /opt/render/project/src && python src/daily_learning.py`
   
   OR if your working directory is the project root:
   - **Command:** `python src/daily_learning.py`

3. **Set Environment Variables:**
   - Copy all env vars from your main worker service
   - Especially: `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_DRIVE_REFRESH_TOKEN`, `GOOGLE_DRIVE_CREDENTIALS_JSON`

4. **Save and Enable**

#### Alternative: Using Render's Scheduled Jobs Feature

If Render has a "Scheduled Jobs" section:
- Create new scheduled job
- Same schedule: `0 23 * * *`
- Same command: `python src/daily_learning.py`
- Same environment variables

---

### Step 7: Verify Deployment

#### Check Main Worker Logs:

```bash
# In Render Dashboard → Logs
```

**Look for:**
- ✅ "🧠 RL System: Active"
- ✅ "⚖️ Current LLM Weights: ..."
- ✅ "Step 7 (NEW): Logging recommendations to RL database..."
- ✅ "✅ Logged X recommendations for future learning"

#### Check Daily Learning Job:

Wait until 11pm UTC, then check logs:

**Look for:**
- ✅ "DAILY LEARNING CYCLE"
- ✅ "Found X recommendations ready for evaluation"
- ✅ "Evaluated X new recommendations"
- ✅ "Updated LLM Weights: ..."
- ✅ "Checkpoint saved"

#### Check Database (if accessible):

The RL database (`trade_alerts_rl.db`) should be created automatically. If you have shell access:

```bash
sqlite3 trade_alerts_rl.db
```

```sql
-- Check recommendations logged
SELECT COUNT(*) FROM recommendations;

-- Check evaluated outcomes
SELECT COUNT(*) FROM recommendations WHERE evaluated = 1;

-- Check latest weights
SELECT * FROM learning_checkpoints ORDER BY timestamp DESC LIMIT 1;
```

---

### Step 8: Monitor and Verify

#### Week 1:
- ✅ System logs recommendations automatically
- ✅ Daily learning runs at 11pm UTC
- ✅ Weights start adjusting (may still be equal if not enough data)

#### Week 2-3:
- ✅ 30-50 recommendations evaluated
- ✅ Weights start differentiating
- ✅ Best-performing LLM emerges

#### Month 1+:
- ✅ 100+ evaluated recommendations
- ✅ Stable, optimized weights
- ✅ Clear performance insights in emails

---

## 🔍 Troubleshooting Deployment

### Issue: "Module not found: trade_alerts_rl"
**Solution:** 
- Ensure `src/trade_alerts_rl.py` is committed and pushed
- Check that Render build includes the file
- Verify file structure in Render logs

### Issue: "yfinance not found"
**Solution:**
- Check `requirements.txt` includes `yfinance>=0.2.35`
- Rebuild service on Render
- Check build logs for pip install errors

### Issue: "Daily learning not running"
**Solution:**
- Verify cron job is enabled
- Check schedule is correct: `0 23 * * *`
- Verify command path is correct
- Check environment variables are set
- Review cron job logs

### Issue: "Database not persisting"
**Solution:**
- On Render, databases persist in the service's file system
- If using ephemeral storage, consider using Render's persistent disk
- Check that database file is being created in logs

### Issue: "No recommendations being logged"
**Solution:**
- Verify main worker is running
- Check that analysis is running on schedule
- Review main worker logs for errors
- Ensure `_run_full_analysis_with_rl()` is being called

---

## 📋 Deployment Checklist

- [ ] Historical backfill run successfully locally
- [ ] Dependencies installed (`yfinance`, `pandas`, `numpy`)
- [ ] Tested locally (optional)
- [ ] All files committed and pushed to git
- [ ] Render deployment successful
- [ ] Main worker shows "RL System: Active" in logs
- [ ] Daily learning cron job created
- [ ] Daily learning job has correct schedule (`0 23 * * *`)
- [ ] Daily learning job has all environment variables
- [ ] Verified recommendations are being logged
- [ ] Verified daily learning runs at 11pm UTC
- [ ] Checked email enhancements (ML insights section)

---

## 🎯 Success Criteria

After deployment, you should see:

1. **In Main Worker Logs:**
   - "🧠 RL System: Active"
   - "⚖️ Current LLM Weights: ..."
   - Recommendations being logged after each analysis

2. **In Daily Learning Logs (11pm UTC):**
   - "DAILY LEARNING CYCLE"
   - Recommendations being evaluated
   - Weights being updated

3. **In Emails:**
   - New "🧠 MACHINE LEARNING INSIGHTS" section
   - LLM performance weights
   - Consensus analysis
   - Best-performing LLM identified

4. **In Database (if accessible):**
   - `recommendations` table populated
   - `learning_checkpoints` table has entries
   - `llm_performance` table has snapshots

---

## 🚨 Important Notes

1. **Historical Backfill:** Run this ONCE locally before deploying. It initializes the system with historical data.

2. **Daily Learning:** Must be set up as a separate scheduled job. It won't run automatically in the main worker.

3. **Database Location:** The `trade_alerts_rl.db` file is created in the project root. On Render, this persists as long as the service is running.

4. **Time Zone:** Daily learning runs at 11pm UTC. Adjust if needed for your timezone.

5. **First Week:** Weights may be equal (0.25 each) until enough data is collected. This is normal.

---

## 📞 Need Help?

- Check logs: Render Dashboard → Logs
- Review documentation: `RL_SETUP_GUIDE.md`
- Quick reference: `RL_QUICK_REFERENCE.md`
- Database queries: See `RL_QUICK_REFERENCE.md`

---

## ✅ You're Deployed!

Once all steps are complete, your RL system will:
- ✅ Learn from every recommendation
- ✅ Update weights daily
- ✅ Provide insights in emails
- ✅ Continuously improve over time

**The system is now fully automated and requires no manual intervention!**





