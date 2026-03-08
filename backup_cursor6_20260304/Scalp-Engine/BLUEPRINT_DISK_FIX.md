# Blueprint Disk Sharing Fix

## Problem

Both `scalp-engine` and `scalp-engine-ui` have `disk: name: shared-market-data` in `render.yaml`, but they're on **different physical devices**:
- `scalp-engine-ui`: `/dev/nvme9n1`
- `scalp-engine`: `/dev/nvme7n1`

They're **NOT sharing the same disk instance**, even though `render.yaml` specifies the same disk name.

## Root Cause

In Render's Blueprint system:
- Services in the **same Blueprint** with the same disk name **SHOULD** share the disk
- Services deployed **separately** or at **different times** might get separate disk instances even with the same name
- Blueprint-managed services don't show disk attach/detach options in the Disk tab

## Solution: Check Blueprint Status

### Step 1: Verify Blueprint Management

1. **Check `scalp-engine` service:**
   - Go to Render Dashboard → `scalp-engine` service
   - Look for "Blueprint managed" tag in the service header
   - Note the Blueprint name (if shown)

2. **Check `scalp-engine-ui` service:**
   - Go to Render Dashboard → `scalp-engine-ui` service  
   - Look for "Blueprint managed" tag in the service header
   - Note the Blueprint name (if shown)

3. **Compare:**
   - ✅ If both show **"Blueprint managed"** and **same Blueprint name** → They should share the disk
   - ❌ If different Blueprint names or one not managed → They're separate deployments

### Step 2: If Services Are in Same Blueprint

If both services are in the same Blueprint but still have different disks:

**Option A: Manual Blueprint Sync (Recommended)**

1. Go to Render Dashboard → **Blueprints** (or your Blueprint name)
2. Find the Blueprint that manages `scalp-engine` and `scalp-engine-ui`
3. Click **"Manual Sync"** or **"Apply Changes"**
4. Render will reapply the disk configuration from `render.yaml`
5. This should attach both services to the same disk instance

**Option B: Redeploy from Blueprint**

1. Go to Render Dashboard → Your Blueprint
2. Click **"Redeploy"** or **"Apply Changes"**
3. Wait for services to redeploy
4. This should recreate disk attachments based on `render.yaml`

### Step 3: If Services Are in Different Blueprints

If services are managed by different Blueprints or separately:

**Fix: Merge Services into Same Blueprint**

1. Ensure `render.yaml` has both services:
   - `scalp-engine` (worker)
   - `scalp-engine-ui` (web)
   - Both with `disk: name: shared-market-data`

2. Deploy from the **same Blueprint**:
   - Go to Render Dashboard → **Blueprints** → **Create Blueprint**
   - OR update existing Blueprint with `render.yaml`
   - Connect to your Git repo with `render.yaml`
   - Render will deploy both services from the same Blueprint
   - Services in the same Blueprint deployment should share the disk

### Step 4: Verify Fix

After syncing/redeploying, run this in both Shells:

```bash
df -h /var/data/ | grep Filesystem
ls -lh /var/data/auto_trader_config.json
```

**Expected Result After Fix:**
- Both services should show **SAME filesystem device** (e.g., `/dev/nvme9n1`)
- Both should show **SAME file size** (427 bytes)
- Both should show **SAME modification time** (Jan 18 22:25)

## Alternative: Check Render API/Disks Section

If Blueprint sync doesn't work, try:

1. Go to Render Dashboard → Look for **"Disks"** in left sidebar (top level)
   - OR: `https://dashboard.render.com/disks`
2. This shows ALL disks with their names and attached services
3. Verify if `scalp-engine` and `scalp-engine-ui` are on the same disk
4. If different, you might need Render support to merge them

## Important Note

Since both services are Blueprint-managed, the disk configuration is controlled by `render.yaml`. The fix is to ensure both services are deployed from the **same Blueprint** and the Blueprint is synced/redeployed so Render applies the shared disk configuration correctly.
