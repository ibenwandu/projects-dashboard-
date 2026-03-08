# Quick Deploy UI to Render - 3 Steps

## ✅ You're Already Set Up!

Since you have Scalp-Engine running on Render with environment variables configured, deploying the UI is super simple.

---

## 🚀 3-Step Deployment

### Step 1: Push Updated Code

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
git add render.yaml scalp_ui.py requirements.txt
git commit -m "Add Streamlit UI dashboard"
git push
```

### Step 2: Deploy on Render

1. Go to **Render Dashboard**: https://dashboard.render.com
2. Find your **Blueprint** (the one with `scalp-engine` worker)
3. Click **"Manual sync"** or **"Apply"**
4. Render will automatically create the `scalp-engine-ui` web service

### Step 3: Access Your UI

1. Go to **Resources** in Render Dashboard
2. Click on **`scalp-engine-ui`** service
3. Copy the URL (e.g., `https://scalp-engine-ui.onrender.com`)
4. Open in browser - your dashboard is live! 🎉

---

## ✅ That's It!

The UI will automatically:
- ✅ Use the same environment variables (OANDA credentials)
- ✅ Access the same database (shared disk)
- ✅ Show real-time opportunities and performance
- ✅ Update every 30 seconds (auto-refresh)

---

## 📊 What You'll See

- **Opportunities Tab**: Current approved pairs with timestamps
- **Recent Signals Tab**: Last 20 trading signals
- **Performance Tab**: Win rates, PnL, statistics
- **Market State Tab**: Raw market data

---

## 🔄 Updates

After pushing code changes:
- Render auto-deploys (if enabled)
- Or manually: `scalp-engine-ui` → **Manual Deploy**

---

**Total Time**: ~5 minutes  
**Cost**: FREE (UI runs on free tier)  
**Status**: Ready to deploy! 🚀
