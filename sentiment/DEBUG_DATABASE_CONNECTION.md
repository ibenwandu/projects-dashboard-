# Debug Database Connection Issue

## Problem
- Trade added via Hugging Face UI 5+ minutes ago
- Render worker still shows "Watchlist is empty"
- They're not sharing the same database

## Diagnosis Steps

### Step 1: Check if DATABASE_URL is Set in Render Worker

1. Go to Render Dashboard → **`sentiment-forex-monitor`** service
2. Click **"Environment"** tab
3. Look for **`DATABASE_URL`** in the list
4. **If it's NOT there:**
   - Click **"Add Environment Variable"**
   - **Key:** `DATABASE_URL`
   - **Value:** Copy the **Internal Database URL** from `sentiment-monitor-db` service
   - Click **"Save Changes"**
   - Wait for auto-redeploy

### Step 2: Check Worker Logs for Database Connection

After redeploy, check logs for:
- `✅ DATABASE_URL is set (PostgreSQL)` ← Good!
- `⚠️ DATABASE_URL not set` ← Problem!

### Step 3: Verify Database Connection String

1. Go to **`sentiment-monitor-db`** → **"Info"** tab
2. Copy the **Internal Database URL**
3. Go to **`sentiment-forex-monitor`** → **"Environment"** tab
4. Make sure `DATABASE_URL` matches exactly

### Step 4: Test Connection

1. Add a NEW trade via Hugging Face UI
2. Wait 1-2 minutes
3. Check Render worker logs
4. Should see the trade in the watchlist

## Common Issues

### Issue 1: DATABASE_URL Not Set
**Symptom:** Worker logs show `⚠️ DATABASE_URL not set`
**Fix:** Add `DATABASE_URL` environment variable to Render worker

### Issue 2: Wrong Database URL
**Symptom:** Connection errors in logs
**Fix:** Use **Internal Database URL** (not External) for Render services

### Issue 3: Code Not Deployed
**Symptom:** No database connection messages in logs
**Fix:** Push latest code to GitHub, trigger redeploy

### Issue 4: Different Databases
**Symptom:** Trades in Hugging Face but not in worker
**Fix:** Ensure both use the same `DATABASE_URL` value

## Quick Fix Command

If you want to verify the connection in Render Shell:

1. Go to **`sentiment-forex-monitor`** → **"Shell"** tab
2. Run: `echo $DATABASE_URL`
3. Should show the PostgreSQL connection string
4. If empty, the environment variable isn't set






