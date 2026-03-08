# Fix: Render Ephemeral Filesystem Issue

## Problem

Render's filesystem is **ephemeral** - files get wiped on every redeploy! The RL database (`trade_alerts_rl.db`) is stored in the default location, which gets wiped on redeploy, causing trained weights to be lost.

## Solution

Use Render's **persistent disk** feature to store the database. The database needs to persist across deployments.

---

## Step 1: Add Persistent Disk to Render Service

1. Go to Render Dashboard → Your `trade-alerts` service
2. Click **"Settings"** tab
3. Scroll down to **"Persistent Disk"** section
4. Click **"Create Persistent Disk"**
5. Configure:
   - **Name**: `rl-database` (or any name)
   - **Size**: 1 GB (minimum, more if needed)
   - **Mount Path**: `/var/data`
6. Click **"Create Disk"**

**Note**: This will cause the service to restart/redeploy.

---

## Step 2: Update Code to Use Persistent Disk

The database path needs to be updated to use the persistent disk location.

**Current code** (in `main.py`):
```python
self.rl_db = RecommendationDatabase(validate_entries=True)
```

**Needs to be**:
```python
import os
# Use persistent disk if available, otherwise default location
db_path = os.getenv('DATABASE_PATH', '/var/data/trade_alerts_rl.db')
if not os.path.exists('/var/data'):
    # Fallback to default location (local development)
    db_path = 'data/trade_alerts_rl.db'
self.rl_db = RecommendationDatabase(db_path=db_path, validate_entries=True)
```

---

## Step 3: Alternative - Run Training After Each Deployment

If you can't use persistent disk, you'll need to run the training script after each deployment:

1. After each deployment/restart
2. SSH into Render shell
3. Run: `python train_rl_system.py --import-csv trade-alert-eval.csv --all`

**This is not ideal** but works if persistent disk isn't available.

---

## Why This Happened

1. ✅ Training script ran successfully → Database updated with weights
2. ✅ You saw correct weights in shell → Database had data
3. ❌ CSV removed → Git commit triggered auto-deploy
4. ❌ Render redeployed → Ephemeral filesystem wiped database
5. ❌ Service restarted → Database was empty → Weights reset to 25%

---

## Recommended Solution

**Use persistent disk** - This is the proper solution for production systems.

The database will persist across deployments, so training only needs to happen once (or when you want to retrain).

---

## Quick Fix (Temporary)

If you need weights immediately while setting up persistent disk:

1. Re-run training script on Render:
   ```bash
   cd /opt/render/project/src
   python train_rl_system.py --import-csv trade-alert-eval.csv --all
   ```
2. **Don't remove the CSV file** until you have persistent disk set up
3. Weights will work until next deployment

But the proper fix is to use persistent disk!
