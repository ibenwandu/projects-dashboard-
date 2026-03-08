# CRITICAL FIX: Services Not Sharing Same Disk

## Problem

The diagnostic output shows:
- **scalp-ui** sees: `/var/data/auto_trader_config.json` (427 bytes, modified 22:25, AUTO/AI_TRAILING)
- **scalp-engine** sees: `/var/data/auto_trader_config.json` (432 bytes, modified 19:34, MANUAL/BE_TO_TRAILING)

**They are NOT sharing the same disk!** Each service has its own separate disk instance.

## Root Cause

Even though `render.yaml` specifies `name: shared-market-data` for both services, Render created **separate disk instances** when services were deployed. The disk name is not a shared identifier - each service gets its own disk unless manually connected.

## Solution: Manual Fix in Render Dashboard

### Step 1: Verify Current Disk Status

1. Go to Render Dashboard → **Disks** section
2. Look for disk instances:
   - `shared-market-data` (attached to `scalp-engine-ui`)
   - `shared-market-data` (attached to `scalp-engine`) - **might be a separate instance**

### Step 2: Identify the Correct Disk

Check which service has the correct config file:
- **scalp-ui** has: `AUTO` / `AI_TRAILING` (the current UI settings)
- **scalp-engine** has: `MANUAL` / `BE_TO_TRAILING` (old config)

**We want `scalp-engine` to use the same disk as `scalp-ui`** (the one with AUTO/AI_TRAILING).

### Step 3: Fix Disk Attachment

**Option A: Attach `scalp-engine` to `scalp-ui`'s disk (Recommended)**

1. Go to Render Dashboard → `scalp-engine-ui` service
2. Go to **Disks** tab
3. Note the disk name (should be `shared-market-data`)
4. Copy the disk ID or name

5. Go to Render Dashboard → `scalp-engine` service
6. Go to **Disks** tab
7. **Detach** the current disk (if it has one attached)
8. **Attach Existing Disk** → Select the same disk that `scalp-ui` uses
   - Should show: `shared-market-data`
   - Should show it's already attached to `scalp-engine-ui`

9. Ensure mount path is `/var/data` for both

**Option B: Create Single Shared Disk Manually (If Option A doesn't work)**

1. Go to Render Dashboard → **Disks** → **Create Disk**
2. Name: `shared-market-data`
3. Size: 1 GB
4. Create the disk

5. Go to `scalp-engine-ui` service → **Disks** → **Attach Existing Disk** → Select `shared-market-data`
6. Mount path: `/var/data`

7. Go to `scalp-engine` service → **Disks** → **Attach Existing Disk** → Select `shared-market-data` (same one)
8. Mount path: `/var/data`

### Step 4: Verify After Fix

Run this command in both Render Shells:

```bash
echo "=== DISK CHECK ==="; ls -lah /var/data/auto_trader_config.json 2>&1; echo ""; cat /var/data/auto_trader_config.json 2>&1 | head -10
```

**Expected Result After Fix:**
- Both services should show **SAME file size**
- Both services should show **SAME modification time**
- Both services should show **SAME file contents** (AUTO/AI_TRAILING)

### Step 5: Restart Services

After fixing disk attachment:
1. Go to `scalp-engine` → **Manual Deploy** → **Deploy latest commit**
2. Go to `scalp-engine-ui` → **Manual Deploy** → **Deploy latest commit**

Wait for both to restart, then verify they're now reading the same file.

## Why This Happened

In Render, disk names in `render.yaml` don't automatically share disks. When you deploy:
- First service creates disk `shared-market-data`
- Second service also tries to create `shared-market-data` but gets a separate instance
- Result: Two separate disks with the same name

**The fix must be done manually in Render Dashboard** to connect both services to the same physical disk.

## Verification Checklist

After fix, both services should show:
- ✅ Same file size for `auto_trader_config.json`
- ✅ Same modification timestamp
- ✅ Same file contents (trading_mode: AUTO, stop_loss_type: AI_TRAILING)
- ✅ Same files visible in `/var/data/` directory listing

If any of these differ, the services are still on separate disks and the fix didn't work.
