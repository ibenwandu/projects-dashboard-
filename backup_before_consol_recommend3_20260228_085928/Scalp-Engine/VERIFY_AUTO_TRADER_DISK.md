# Verify Auto-Trader Disk Sharing

## Problem
- `trade-alerts` ↔ `scalp-ui`: ✅ **WORKING** (market_state.json syncs correctly)
- `scalp-ui` ↔ `scalp-engine`: ❌ **NOT WORKING** (auto_trader_config.json not syncing)

## Root Cause
`scalp-engine` (worker) and `scalp-engine-ui` (web) are on **different disk instances** despite both using `/var/data/auto_trader_config.json`.

## Solution: Check `scalp-engine` Disk Settings

### Step 1: Check `scalp-engine-ui` Disk
1. Go to Render Dashboard → `scalp-engine-ui` service
2. Go to **Settings** → **Disk** tab
3. Note the disk details:
   - Mount path: `/var/data`
   - Disk name: (likely `shared-market-data` or similar)

### Step 2: Check `scalp-engine` Disk
1. Go to Render Dashboard → `scalp-engine` service (the worker, not the UI)
2. Go to **Settings** → **Disk** tab
3. **Verify**:
   - Is it using the **SAME disk** as `scalp-engine-ui`?
   - Mount path: `/var/data` (must match)
   - Disk name: Should be the same as `scalp-engine-ui`

### Step 3: Fix if Different
If `scalp-engine` has a different disk than `scalp-engine-ui`:

1. In `scalp-engine` service → **Settings** → **Disk** tab:
   - **Detach** current disk (if different from UI's disk)
   - **Attach Existing Disk** → Select the **same disk** that `scalp-engine-ui` uses
   - Mount path: `/var/data`
   - Click **Save**

2. **Restart** `scalp-engine` service:
   - Go to `scalp-engine` → **Manual Deploy** → **Deploy latest commit**

### Step 4: Verify Fix
Run this command in both Render Shells:

**In `scalp-engine-ui` Shell:**
```bash
echo "=== UI DISK CHECK ==="; ls -lh /var/data/auto_trader_config.json 2>&1; echo ""; cat /var/data/auto_trader_config.json 2>&1 | head -5
```

**In `scalp-engine` Shell:**
```bash
echo "=== ENGINE DISK CHECK ==="; ls -lh /var/data/auto_trader_config.json 2>&1; echo ""; cat /var/data/auto_trader_config.json 2>&1 | head -5
```

**Expected Result After Fix:**
- Both should show **SAME file size**
- Both should show **SAME modification time**
- Both should show **SAME contents** (trading_mode: AUTO, stop_loss_type: AI_TRAILING)

## Why This Happened
In Render, `scalp-engine` (worker) and `scalp-engine-ui` (web) were deployed separately, so each got its own disk instance even though both are named `shared-market-data`. They need to be manually attached to the same physical disk.

## Important Note
`trade-alerts` and `scalp-ui` are working correctly, which confirms the shared disk concept works. The issue is only with `scalp-engine` worker needing to match `scalp-engine-ui` web service's disk.
