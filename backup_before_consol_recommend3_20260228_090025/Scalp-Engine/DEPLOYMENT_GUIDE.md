# Scalp-Engine Deployment Guide

Complete guide to deploy Scalp-Engine to GitHub and Render for 24/7 automated trading.

---

## Prerequisites

1. ✅ Scalp-Engine is working locally (you've tested it)
2. ✅ OANDA account credentials ready
3. ✅ GitHub account
4. ✅ Render account (sign up at https://render.com)

---

## Part 1: Deploy to GitHub

### Step 1: Initialize Git Repository

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Scalp-Engine automated scalping system"
```

### Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `scalp-engine` (or your preferred name)
3. **Don't** initialize with README, .gitignore, or license (you already have these)
4. Click **"Create repository"**

### Step 3: Push to GitHub

```powershell
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/scalp-engine.git
git branch -M main
git push -u origin main
```

**Note:** If you get authentication errors, you may need to:
- Use a Personal Access Token instead of password
- Or use SSH: `git remote add origin git@github.com:YOUR_USERNAME/scalp-engine.git`

---

## Part 2: Deploy to Render

### Step 1: Connect Repository to Render

1. Go to **Render Dashboard**: https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"** (recommended) or **"Worker"**
3. Connect your GitHub account (if not already connected)
4. Select your `scalp-engine` repository

### Step 2A: Using Blueprint (Automatic - Recommended)

If you're using `render.yaml`:

1. Render will automatically detect `render.yaml`
2. Click **"Apply"**
3. Render will create the service automatically
4. Skip to **Step 3: Configure Environment Variables**

### Step 2B: Manual Setup (If not using Blueprint)

1. **Service Type**: Worker
2. **Name**: `scalp-engine`
3. **Environment**: Python 3
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `python scalp_engine.py`
6. **Branch**: `main`
7. **Plan**: Starter ($7/month) - Required for always-on service

### Step 3: Configure Environment Variables

In Render Dashboard → Your Service → **Environment**, add these variables:

#### Required OANDA Credentials

```
OANDA_ACCESS_TOKEN=your-oanda-access-token-here
OANDA_ACCOUNT_ID=your-oanda-account-id-here
OANDA_ENV=practice
```

**Important Notes:**
- `OANDA_ENV` should be `practice` for testing, `live` for production
- Get these from your OANDA account dashboard
- Never commit these to GitHub (they're in `.gitignore`)

#### Optional Configuration

```
PYTHON_VERSION=3.10.0
ENV=production
```

### Step 4: Configure Persistent Disk (Important!)

Scalp-Engine needs access to `market_state.json` from Trade-Alerts. You have two options:

#### Option A: Shared Disk (If Trade-Alerts is on Render)

If Trade-Alerts is deployed on Render in the same account:
1. Use the same disk name as Trade-Alerts
2. Or create a shared disk that both services can access
3. Update `state_reader.py` to read from the shared path

#### Option B: Separate Deployment (Recommended for now)

For now, Scalp-Engine will wait for Trade-Alerts to generate `market_state.json`. 

**Future Enhancement:** You can:
- Deploy both in a monorepo
- Use a shared disk
- Or have Trade-Alerts write to a shared location

### Step 5: Deploy

1. Click **"Create"** or **"Save Changes"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies (`pip install -r requirements.txt`)
   - Start the service (`python scalp_engine.py`)
3. Check the **Logs** tab to see it running

---

## Part 3: Verify Deployment

### Step 1: Check Logs

In Render Dashboard → `scalp-engine` → **Logs**, you should see:

```
================================================================================
Scalp-Engine Started
================================================================================
Environment: practice
Trading Pairs: EUR/USD, USD/JPY, USD/CAD
Max Spread: 1.5 pips
================================================================================

Market State Updated:
   Regime: NORMAL
   Bias: NEUTRAL
   Approved Pairs: 

PAUSED: No approved pairs. Waiting for Trade-Alerts to provide pairs...
```

**This is NORMAL** - Scalp-Engine is waiting for Trade-Alerts to generate trading pairs.

### Step 2: Verify OANDA Connection

Look for these messages in logs:
- `[OK] OANDA connection successful`
- `Account Balance: [your balance]`

If you see connection errors, check:
- OANDA credentials are correct
- OANDA account is active
- Network connectivity

### Step 3: Test with Real Market State

1. Make sure Trade-Alerts is running and generating `market_state.json`
2. Scalp-Engine will automatically pick up new pairs every 60 seconds
3. Watch logs for:
   - `Market State Updated`
   - `Approved Pairs: EUR/USD, USD/JPY`
   - `Signal: BUY EUR/USD (Strength: 0.75)`
   - `EXECUTING: BUY EUR/USD - Size: 1000 units`

---

## Part 4: Integration with Trade-Alerts

### Current Setup

Scalp-Engine reads `market_state.json` from Trade-Alerts. For this to work on Render:

### Option 1: Deploy Both in Monorepo (Recommended)

1. Add Scalp-Engine to your `trading-systems-monorepo`
2. Update `render.yaml` to include both services
3. Use shared disk for `market_state.json`

### Option 2: Separate Deployments (Current)

1. Trade-Alerts generates `market_state.json` locally or on Render
2. Scalp-Engine reads from a shared location (needs configuration)
3. Or use a file sync service

### Option 3: API Integration (Future)

1. Trade-Alerts exposes an API endpoint
2. Scalp-Engine polls the API for market state
3. More robust but requires additional development

**For now:** Deploy Scalp-Engine separately. It will wait for market state. You can manually sync `market_state.json` or set up automated sync later.

---

## Monitoring & Maintenance

### View Logs

- **Render Dashboard** → `scalp-engine` → **Logs**
- Real-time log streaming
- Search and filter capabilities

### Check Status

- **Status**: Should show "Live"
- **Uptime**: Should show continuous operation
- **Last Deploy**: Shows when last updated

### Common Issues

#### Service Won't Start
- Check logs for errors
- Verify all environment variables are set
- Check that `requirements.txt` is correct
- Verify Python version compatibility

#### No Trading Activity
- Check if `market_state.json` exists and has approved pairs
- Verify Trade-Alerts is generating market state
- Check logs for "No approved pairs" messages (this is normal if Trade-Alerts hasn't run)

#### OANDA Connection Errors
- Verify OANDA credentials are correct
- Check OANDA account status
- Verify `OANDA_ENV` is set correctly (practice vs live)
- Check OANDA API status page

#### Missing Dependencies
- Check build logs for installation errors
- Verify `requirements.txt` includes all dependencies
- Check Python version compatibility

---

## Cost Considerations

### Render Pricing

**Free Tier:**
- ❌ Not suitable - services spin down after 15 minutes
- ❌ Scalp-Engine needs to run 24/7

**Starter Plan ($7/month):**
- ✅ Always-on service
- ✅ 512 MB RAM
- ✅ 0.5 CPU
- ✅ 1 GB disk space
- ✅ Perfect for Scalp-Engine

### OANDA Costs

- **Practice Account**: Free (for testing)
- **Live Account**: Spread costs only (no commission on most pairs)

---

## Security Best Practices

1. ✅ **Never commit credentials** - All secrets in `.gitignore`
2. ✅ **Use environment variables** - Never hardcode API keys
3. ✅ **Start with practice account** - Test thoroughly before going live
4. ✅ **Monitor logs regularly** - Check for unauthorized activity
5. ✅ **Use strong passwords** - For GitHub and Render accounts
6. ✅ **Enable 2FA** - On GitHub and Render accounts

---

## Next Steps After Deployment

1. ✅ **Monitor for 24 hours** - Watch logs and verify behavior
2. ✅ **Test with practice account** - Verify trades execute correctly
3. ✅ **Check OANDA dashboard** - Confirm trades are being placed
4. ✅ **Review risk settings** - Ensure position sizing is appropriate
5. ✅ **Set up alerts** - Configure notifications for errors or issues
6. ✅ **Document any issues** - Keep notes for future improvements

---

## Troubleshooting

### Deployment Fails

**Check:**
- Build logs for errors
- `requirements.txt` syntax
- Python version compatibility
- Repository access permissions

### Service Keeps Restarting

**Check:**
- Logs for crash errors
- Memory usage (may need to upgrade plan)
- Infinite loop in code
- Missing dependencies

### No Trades Executing

**Check:**
- Market state file exists and has approved pairs
- OANDA connection is working
- Spread is within limits
- Signal strength meets thresholds
- Account has sufficient balance

---

## Support Resources

- **Render Docs**: https://render.com/docs
- **OANDA API Docs**: https://developer.oanda.com
- **Scalp-Engine README**: See `README.md` in project
- **Troubleshooting Guide**: See `TROUBLESHOOTING.md`

---

## Quick Reference

### Render Dashboard
- **URL**: https://dashboard.render.com
- **Service**: `scalp-engine`
- **Type**: Worker

### GitHub Repository
- **URL**: `https://github.com/YOUR_USERNAME/scalp-engine`
- **Branch**: `main`

### OANDA
- **Practice**: https://www.oanda.com/us-en/trading/accounts/practice/
- **Live**: https://www.oanda.com/us-en/trading/accounts/
- **API Docs**: https://developer.oanda.com/rest-live-v20/introduction/

---

**Ready to deploy?** Follow the steps above, and Scalp-Engine will be running 24/7 on Render! 🚀

