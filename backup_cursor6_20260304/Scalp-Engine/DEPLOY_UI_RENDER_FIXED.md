# Deploy Streamlit UI to Render - Fixed Configuration

## ✅ Issue Resolved

The error "disks are not supported for free tier services" has been fixed by upgrading the UI service to **Starter plan** ($7/month), which allows disk access.

---

## 💰 Cost Update

**Previous (with error):**
- Worker: $7/month (Starter)
- UI: FREE (but couldn't access database)

**Current (fixed):**
- Worker: $7/month (Starter)
- UI: $7/month (Starter) - **Now can share disk with worker**

**Total**: $14/month for both services with shared database access

---

## 🚀 Deploy Steps

### Step 1: Push Updated Code

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
git add render.yaml
git commit -m "Fix UI service: Upgrade to starter plan for disk access"
git push
```

### Step 2: Sync on Render

1. Go to **Render Dashboard** → Your Blueprint
2. Click **"Manual sync"** or **"Apply"**
3. Render will update the UI service to Starter plan
4. The disk will now be accessible

### Step 3: Verify

1. Check **Resources** → `scalp-engine-ui`
2. Should show **"Starter"** plan
3. Should have disk mounted at `/var/data`
4. Can now access the same database as worker

---

## ✅ Benefits of Starter Plan for UI

1. **Shared Database**: UI and worker use the same `scalping_rl.db`
2. **Real-time Data**: UI sees trades as they happen
3. **Persistent Storage**: Data survives service restarts
4. **Better Performance**: Starter plan has more resources

---

## 🔄 Alternative: Keep UI on Free Tier

If you want to keep costs down, you can:

1. **Remove disk from UI** (already done in previous version)
2. **UI creates its own database** (separate from worker)
3. **UI shows market state only** (from Trade-Alerts)
4. **No shared trade history** (worker and UI have separate databases)

**Cost**: $7/month total (only worker on Starter)

---

## 📊 Current Configuration

### Worker Service (`scalp-engine`)
- ✅ Plan: Starter ($7/month)
- ✅ Disk: `/var/data` (1GB)
- ✅ Database: `scalping_rl.db` on disk
- ✅ Runs 24/7

### UI Service (`scalp-engine-ui`)
- ✅ Plan: Starter ($7/month) - **Updated**
- ✅ Disk: `/var/data` (1GB) - **Shared with worker**
- ✅ Database: Same `scalping_rl.db` as worker
- ✅ Accessible via web URL

---

## 🎯 Recommendation

**Use Starter plan for UI** if you want:
- ✅ Real-time trade data in dashboard
- ✅ Historical performance tracking
- ✅ Shared database between services

**Use Free tier for UI** if you want:
- ✅ Lower cost ($7/month total)
- ✅ Market state viewing only
- ✅ Separate databases (less ideal)

---

**Status**: Configuration fixed! Push and sync to deploy. 🚀
