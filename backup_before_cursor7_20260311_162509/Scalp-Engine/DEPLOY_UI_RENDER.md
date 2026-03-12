# Deploy Streamlit UI to Render

## Overview

Since you already have Scalp-Engine running on Render with environment variables configured, deploying the UI is straightforward. The UI will automatically use the same environment variables and shared disk.

---

## 🚀 Quick Deploy

### Step 1: Update render.yaml

The `render.yaml` has been updated to include a web service for the Streamlit UI. It will:
- ✅ Use the same environment variables (auto-synced)
- ✅ Share the same disk for database access
- ✅ Run on free tier (sufficient for UI)

### Step 2: Push to GitHub

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
git add render.yaml scalp_ui.py requirements.txt
git commit -m "Add Streamlit UI for Scalp-Engine dashboard"
git push
```

### Step 3: Deploy on Render

**Option A: Using Blueprint (Automatic)**

1. Go to **Render Dashboard**: https://dashboard.render.com
2. Navigate to your **Blueprint** (the one with `scalp-engine` worker)
3. Click **"Manual sync"** or **"Apply"**
4. Render will detect the new web service in `render.yaml`
5. It will create `scalp-engine-ui` service automatically
6. Environment variables will sync from the worker service

**Option B: Manual Service Creation**

1. Go to **Render Dashboard**
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Settings:
   - **Name**: `scalp-engine-ui`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run scalp_ui.py --server.port $PORT --server.address 0.0.0.0`
5. **Environment Variables**: 
   - They should auto-sync, but verify:
     - `OANDA_ACCESS_TOKEN` (sync from worker)
     - `OANDA_ACCOUNT_ID` (sync from worker)
     - `OANDA_ENV` (sync from worker)
6. **Disk**: Use the same disk as worker (`scalp-engine-data`)
7. Click **"Create Web Service"**

---

## ✅ Verify Deployment

### Check Service Status

1. Go to **Render Dashboard** → **Resources**
2. You should see:
   - `scalp-engine` (worker) - Running
   - `scalp-engine-ui` (web) - Running

### Access the UI

1. Click on `scalp-engine-ui` service
2. You'll see a URL like: `https://scalp-engine-ui.onrender.com`
3. Click the URL to open the dashboard

### Check Logs

1. Go to `scalp-engine-ui` → **Logs**
2. You should see:
   ```
   You can now view your Streamlit app in your browser.
   Local URL: http://localhost:8501
   Network URL: http://0.0.0.0:8501
   ```

---

## 🔧 Configuration

### Environment Variables

The UI service will automatically use the same environment variables as the worker:
- ✅ `OANDA_ACCESS_TOKEN` - Auto-synced
- ✅ `OANDA_ACCOUNT_ID` - Auto-synced  
- ✅ `OANDA_ENV` - Auto-synced

**No additional configuration needed!**

### Database Access

The UI reads from `scalping_rl.db` which is stored on the shared disk (`/var/data`). Both services use the same disk, so:
- ✅ Worker writes to database
- ✅ UI reads from database
- ✅ Both access the same file

### Market State Access

The UI reads `market_state.json` from Trade-Alerts. Make sure:
- ✅ `MARKET_STATE_FILE_PATH` is set correctly (if using custom path)
- ✅ Or the default path is accessible

---

## 📊 UI Features on Render

Once deployed, you'll have:

1. **Live Dashboard**: Accessible from anywhere
2. **Real-time Updates**: Auto-refresh every 30 seconds
3. **Performance Stats**: View win rates, PnL, etc.
4. **Current Opportunities**: See approved pairs and signals
5. **Historical Data**: View past trades and performance

---

## 🔄 Updating the UI

### After Code Changes

1. Push to GitHub:
   ```powershell
   git add .
   git commit -m "Update UI"
   git push
   ```

2. Render will auto-deploy (if auto-deploy is enabled)
3. Or manually trigger: Render Dashboard → `scalp-engine-ui` → **Manual Deploy**

---

## 💰 Cost

- **Worker Service**: $7/month (Starter plan - always-on)
- **UI Service**: **FREE** (Free tier is sufficient for dashboard)

**Total**: $7/month for both services

---

## 🐛 Troubleshooting

### UI shows "No data available"

**Check:**
1. Database exists: Worker should create `scalping_rl.db`
2. Market state exists: Trade-Alerts should create `market_state.json`
3. Disk is mounted: Both services should use same disk
4. File paths are correct

### UI won't start

**Check logs for:**
- Missing dependencies: `pip install -r requirements.txt`
- Port binding: Should use `$PORT` environment variable
- Streamlit errors: Check error messages in logs

### Environment variables not syncing

**Solution:**
1. Go to `scalp-engine-ui` → **Environment**
2. Manually add variables (copy from worker service)
3. Or use Render's "Sync from" feature if available

### Database not accessible

**Solution:**
1. Verify both services use same disk
2. Check disk mount path: `/var/data`
3. Verify database file path in code matches disk path

---

## 📝 Files Updated

- ✅ `render.yaml` - Added web service for UI
- ✅ `scalp_ui.py` - Streamlit dashboard
- ✅ `requirements.txt` - Added Streamlit dependency

---

## 🎯 Next Steps

1. ✅ Push updated `render.yaml` to GitHub
2. ✅ Deploy on Render (auto or manual)
3. ✅ Access UI at the provided URL
4. ✅ Monitor both services
5. ✅ Enjoy your live dashboard!

---

## 🔗 Quick Links

- **Render Dashboard**: https://dashboard.render.com
- **Your UI URL**: `https://scalp-engine-ui.onrender.com` (after deployment)
- **Worker Logs**: Render Dashboard → `scalp-engine` → Logs
- **UI Logs**: Render Dashboard → `scalp-engine-ui` → Logs

---

**Status**: Ready to deploy! The UI will automatically use your existing Render configuration. 🚀
