# Quick Deploy - Scalp-Engine

## 🚀 Deploy in 3 Steps

### Step 1: Push to GitHub

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine

# Commit all changes
git add .
git commit -m "Ready for deployment: Scalp-Engine automated scalping system"

# Push to GitHub (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/scalp-engine.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy to Render

1. Go to **Render Dashboard**: https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect GitHub and select `scalp-engine` repository
4. Render will detect `render.yaml` automatically
5. Click **"Apply"**

### Step 3: Configure Environment Variables

In Render Dashboard → `scalp-engine` → **Environment**, add:

```
OANDA_ACCESS_TOKEN=your-token-here
OANDA_ACCOUNT_ID=your-account-id-here
OANDA_ENV=practice
```

Click **"Save Changes"** - Render will automatically deploy!

---

## ✅ Verify Deployment

1. **Check Logs**: Render Dashboard → `scalp-engine` → **Logs**
2. **Look for**: "Scalp-Engine Started" message
3. **Status**: Should show "Live"

---

## 📋 What You'll See

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

---

## 🔗 Integration with Trade-Alerts

**Current Setup:**
- Scalp-Engine reads `market_state.json` from Trade-Alerts
- On Render, you'll need to configure the path or use a shared disk

**Options:**
1. **Deploy both in monorepo** (recommended for production)
2. **Use shared disk** (if both on Render)
3. **Manual sync** (for testing)

---

## 📚 Full Documentation

- **Complete Guide**: See `DEPLOYMENT_GUIDE.md`
- **Checklist**: See `DEPLOY_CHECKLIST.md`
- **Troubleshooting**: See `TROUBLESHOOTING.md`

---

**Ready?** Follow the 3 steps above! 🚀

