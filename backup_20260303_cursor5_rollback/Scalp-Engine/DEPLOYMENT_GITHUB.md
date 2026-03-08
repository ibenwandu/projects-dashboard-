# GitHub Deployment Guide for Scalp-Engine

## Overview

This guide explains how to deploy Scalp-Engine to GitHub and set up continuous operation.

---

## 📋 Prerequisites

1. **GitHub Repository** - Your Scalp-Engine code in a GitHub repo
2. **GitHub Secrets** - OANDA credentials stored as secrets
3. **Python 3.11+** - Required Python version

---

## 🔐 Setting Up GitHub Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

### Required Secrets:
- `OANDA_ACCESS_TOKEN` - Your OANDA API access token
- `OANDA_ACCOUNT_ID` - Your OANDA account ID
- `OANDA_ENV` - `practice` or `live` (default: `practice`)

### Optional Secrets:
- `MARKET_STATE_FILE_PATH` - Custom path to market_state.json (if not using default)

---

## 🚀 Deployment Options

### Option 1: GitHub Actions (Recommended for Testing)

GitHub Actions can run the engine periodically, but note:
- ⚠️ **Limitations:** Free tier has 2000 minutes/month
- ⚠️ **Not Continuous:** Runs on schedule, not 24/7
- ✅ **Good for:** Testing, scheduled runs, monitoring

**Workflow:** `.github/workflows/run_engine.yml`
- Runs every 5 minutes
- Executes for up to 1 hour per run
- Can be triggered manually

### Option 2: External Hosting (Recommended for Production)

For **24/7 continuous operation**, use:
- **Render.com** (Free tier available)
- **Railway.app** (Free tier available)
- **Heroku** (Paid)
- **AWS EC2** (Pay-as-you-go)
- **DigitalOcean** (Pay-as-you-go)

---

## 📦 Deployment Steps

### Step 1: Push Code to GitHub

```bash
cd C:\Users\user\projects\personal\Scalp-Engine
git init  # If not already a git repo
git add .
git commit -m "Initial Scalp-Engine deployment"
git remote add origin https://github.com/yourusername/scalp-engine.git
git push -u origin main
```

### Step 2: Set Up Secrets

1. Go to GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Add all required secrets (see above)

### Step 3: Enable GitHub Actions

1. Go to **Actions** tab in GitHub
2. Workflows will appear automatically
3. Click on a workflow → **Run workflow** to test

---

## 🖥️ Running the UI Locally

The Streamlit UI can run locally or be deployed separately:

### Local Run:

```bash
cd C:\Users\user\projects\personal\Scalp-Engine
streamlit run scalp_ui.py
```

This will:
- Start a local web server (usually `http://localhost:8501`)
- Display the Scalp-Engine dashboard
- Auto-refresh every 30 seconds (if enabled)

### Deploy UI to Streamlit Cloud:

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set main file: `scalp_ui.py`
5. Add secrets in Streamlit Cloud dashboard:
   - Database path (if using cloud storage)
   - Market state file path

---

## 🔄 Continuous Operation Setup

### For 24/7 Operation:

**Option A: Render.com (Recommended)**

1. Create account at [render.com](https://render.com)
2. New → **Web Service**
3. Connect GitHub repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python scalp_engine.py`
   - **Environment:** Python 3
5. Add environment variables:
   - `OANDA_ACCESS_TOKEN`
   - `OANDA_ACCOUNT_ID`
   - `OANDA_ENV=practice`
6. Deploy

**Option B: Railway.app**

1. Create account at [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Select your repo
4. Add environment variables
5. Deploy

**Option C: Self-Hosted (VPS/Server)**

```bash
# On your server
git clone https://github.com/yourusername/scalp-engine.git
cd scalp-engine
pip install -r requirements.txt

# Run as background service
nohup python scalp_engine.py > scalp_engine.log 2>&1 &

# Or use systemd service (Linux)
sudo systemctl enable scalp-engine
sudo systemctl start scalp-engine
```

---

## 📊 Monitoring

### Check GitHub Actions:

1. Go to **Actions** tab
2. View workflow runs
3. Check logs for errors

### Check UI:

- Open Streamlit UI
- View **Opportunities** tab for current pairs
- View **Recent Signals** for activity
- View **Performance** for statistics

### Check Logs:

If running on external service:
- Render: View logs in dashboard
- Railway: View logs in dashboard
- Self-hosted: Check log files

---

## 🔧 Troubleshooting

### Issue: GitHub Actions not running

**Solution:**
- Check if Actions are enabled: **Settings** → **Actions** → **General**
- Verify secrets are set correctly
- Check workflow file syntax

### Issue: Engine stops after 1 hour

**Solution:**
- This is expected for GitHub Actions (timeout limit)
- Use external hosting for 24/7 operation
- Or modify workflow to restart automatically

### Issue: UI can't find database

**Solution:**
- Ensure `scalping_rl.db` exists in same directory
- Check file permissions
- If using cloud, mount persistent storage

### Issue: Market state not updating

**Solution:**
- Verify Trade-Alerts is running
- Check `market_state.json` path
- Ensure file is accessible to Scalp-Engine

---

## 📝 Files Created

1. **`.github/workflows/deploy.yml`** - Deployment workflow
2. **`.github/workflows/run_engine.yml`** - Engine execution workflow
3. **`scalp_ui.py`** - Streamlit dashboard
4. **`DEPLOYMENT_GITHUB.md`** - This guide

---

## ✅ Next Steps

1. ✅ Push code to GitHub
2. ✅ Set up secrets
3. ✅ Test GitHub Actions
4. ✅ Deploy UI (local or Streamlit Cloud)
5. ✅ Set up external hosting for 24/7 operation
6. ✅ Monitor performance

---

## 🎯 Quick Start Commands

```bash
# Run UI locally
streamlit run scalp_ui.py

# Run engine locally
python scalp_engine.py

# Check GitHub Actions
# Go to: https://github.com/yourusername/scalp-engine/actions
```

---

**Status:** Ready for deployment! 🚀
