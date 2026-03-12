# Deploy RL System to Render - Quick Checklist

## ✅ Step 1: Verify Backfill Results

Check that the backfill completed successfully:
- ✅ Processed files
- ✅ Extracted recommendations  
- ✅ Evaluated outcomes
- ✅ LLM weights calculated
- ✅ Database created: `trade_alerts_rl.db`

---

## ✅ Step 2: Commit and Push Code

```bash
cd C:\Users\user\projects\personal\Trade-Alerts
git add .
git commit -m "Add RL system: enhanced parser, dual format saving, free-form text extraction"
git push origin main
```

**Files being deployed:**
- `src/trade_alerts_rl.py` (enhanced parser)
- `src/daily_learning.py` (daily learning job)
- `historical_backfill.py` (one-time setup)
- `main.py` (updated with RL integration)
- `requirements.txt` (includes yfinance, pandas, numpy)

---

## ✅ Step 3: Update Render Environment Variables

Go to **Render Dashboard** → **trade-alerts** service → **Environment** tab

### Update Google Drive Token (if needed):
- `GOOGLE_DRIVE_REFRESH_TOKEN` - Use your new token (if you generated one)

### Verify All Required Variables Are Set:
- ✅ `GOOGLE_DRIVE_FOLDER_ID`
- ✅ `GOOGLE_DRIVE_CREDENTIALS_JSON`
- ✅ `GOOGLE_DRIVE_REFRESH_TOKEN`
- ✅ `OPENAI_API_KEY`
- ✅ `GOOGLE_API_KEY`
- ✅ `ANTHROPIC_API_KEY`
- ✅ `SENDER_EMAIL`
- ✅ `SENDER_PASSWORD`
- ✅ `RECIPIENT_EMAIL`
- ✅ `PUSHOVER_API_TOKEN` (optional)
- ✅ `PUSHOVER_USER_KEY` (optional)

**No new environment variables needed** - the RL system uses existing ones!

---

## ✅ Step 4: Deploy to Render

### Option A: Automatic (if connected to GitHub)
- Render will auto-deploy when you push
- Check **Render Dashboard** → **trade-alerts** → **Events** tab
- Wait for deployment to complete (2-5 minutes)

### Option B: Manual Deploy
- Go to **Render Dashboard** → **trade-alerts** service
- Click **"Manual Deploy"** → **"Deploy latest commit"**

---

## ✅ Step 5: Verify Main Worker Deployment

After deployment completes, check **Logs** tab:

**Look for:**
- ✅ "🧠 RL System: Active" (or "RL System: Active")
- ✅ "⚖️ Current LLM Weights: ..."
- ✅ "Step 7 (NEW): Logging recommendations to RL database..."
- ✅ "✅ Logged X recommendations for future learning"

**If you see errors:**
- Check that all dependencies are installed
- Verify environment variables are set
- Review error messages in logs

---

## ✅ Step 6: Set Up Daily Learning Scheduled Job

**This is critical!** The daily learning job updates LLM weights every day.

### On Render Dashboard:

1. **Go to "Cron Jobs" or "Scheduled Jobs"** section
   - (If you don't see this, you may need to use a different approach - see Alternative below)

2. **Create New Cron Job:**
   - **Name:** `trade-alerts-daily-learning`
   - **Schedule:** `0 23 * * *` (11pm UTC daily)
   - **Command:** `python src/daily_learning.py`
   - **Working Directory:** Leave empty (uses project root)

3. **Copy Environment Variables:**
   - Copy ALL environment variables from your main worker service
   - Especially important:
     - `GOOGLE_DRIVE_FOLDER_ID`
     - `GOOGLE_DRIVE_CREDENTIALS_JSON`
     - `GOOGLE_DRIVE_REFRESH_TOKEN`
     - All LLM API keys
     - Email settings

4. **Save and Enable**

### Alternative: If Render Doesn't Have Cron Jobs

If Render doesn't have a Cron Jobs feature, you can:

**Option 1: Add to main.py** (simpler, but runs in same process)
- The daily learning check is already in `main.py`
- It will run automatically when `should_run_learning()` returns True
- Check logs at 11pm UTC to verify it runs

**Option 2: Use External Cron Service**
- Use a service like cron-job.org or EasyCron
- Schedule: `0 23 * * *` (11pm UTC)
- URL: Your Render service webhook (if you add one)
- Or use Render's API to trigger the job

---

## ✅ Step 7: Upload Database (Optional but Recommended)

If you want to start with historical data on Render:

1. **Download your local database:**
   ```bash
   # The file is: trade_alerts_rl.db
   ```

2. **Upload to Render:**
   - Go to Render Dashboard → **trade-alerts** → **Shell**
   - Or use Render's file upload feature
   - Upload `trade_alerts_rl.db` to the project root

**Note:** This is optional. The system will work without it, but will start fresh. The daily learning will build up data over time.

---

## ✅ Step 8: Verify Everything Works

### Check Main Worker (Next Analysis Run):
1. Wait for next scheduled analysis (or trigger manually)
2. Check logs for:
   - ✅ "Step 7 (NEW): Logging recommendations to RL database..."
   - ✅ "✅ Logged X recommendations for future learning"

### Check Daily Learning (Wait until 11pm UTC):
1. Check logs the next day
2. Look for:
   - ✅ "DAILY LEARNING CYCLE"
   - ✅ "Found X recommendations ready for evaluation"
   - ✅ "Evaluated X new recommendations"
   - ✅ "Updated LLM Weights: ..."

### Check Email Enhancements:
1. Check your next recommendation email
2. Should include:
   - ✅ "🧠 MACHINE LEARNING INSIGHTS" section
   - ✅ LLM Performance Weights
   - ✅ Best Performing LLM
   - ✅ Consensus Analysis (if available)

---

## 🎯 Success Indicators

After 24-48 hours, you should see:

1. **Main Worker:**
   - Recommendations being logged after each analysis
   - RL system active in logs

2. **Daily Learning:**
   - Running at 11pm UTC
   - Evaluating recommendations
   - Updating weights

3. **Emails:**
   - ML insights section appearing
   - Performance metrics showing

4. **Database:**
   - Recommendations accumulating
   - Outcomes being evaluated
   - Weights updating over time

---

## 🚨 Troubleshooting

### Issue: "Module not found: trade_alerts_rl"
- **Fix:** Ensure `src/trade_alerts_rl.py` is committed and pushed
- **Check:** Render build logs show the file is included

### Issue: "yfinance not found"
- **Fix:** Check `requirements.txt` includes `yfinance>=0.2.35`
- **Fix:** Rebuild service on Render

### Issue: Daily learning not running
- **Fix:** Verify cron job is enabled and schedule is correct
- **Fix:** Check environment variables are copied to cron job
- **Fix:** Review cron job logs

### Issue: No recommendations being logged
- **Fix:** Verify main worker is running
- **Fix:** Check that analysis is completing successfully
- **Fix:** Review logs for errors in `_run_full_analysis_with_rl()`

---

## 📋 Quick Deployment Checklist

- [ ] Historical backfill completed locally
- [ ] All code committed and pushed to GitHub
- [ ] Render environment variables updated (especially refresh token)
- [ ] Render deployment successful
- [ ] Main worker shows "RL System: Active" in logs
- [ ] Daily learning cron job created (or added to main.py)
- [ ] Daily learning has correct schedule (`0 23 * * *`)
- [ ] Daily learning has all environment variables
- [ ] Verified recommendations are being logged
- [ ] Verified email includes ML insights section

---

## ✅ You're Deployed!

Once all steps are complete, your RL system will:
- ✅ Learn from every recommendation automatically
- ✅ Update weights daily at 11pm UTC
- ✅ Provide insights in emails
- ✅ Continuously improve over time

**The system is now fully automated!**

