# Fix: config-api and scalp-engine-ui Disk Sharing

## 🔴 Problem Confirmed

- **UI saves config** to `/var/data/auto_trader_config.json` (AUTO/TRAILING mode)
- **config-api health** shows `"file_exists": false` and `"dir_files": []`
- **scalp-engine** loads from API but gets default config (MANUAL/BE_TO_TRAILING)

**Root Cause:** `scalp-engine-ui` and `config-api` are on **separate disk instances**, even though both use `shared-market-data` in `render.yaml`.

## ✅ Solution: Manual Blueprint Sync

### Step 1: Verify Services Are in Same Blueprint

1. Go to Render Dashboard → **Blueprints**
2. Find the Blueprint that contains `scalp-engine-ui` and `config-api`
3. Verify both services show "Blueprint managed" with the same Blueprint name

### Step 2: Manual Sync Blueprint

1. Go to Render Dashboard → Your Blueprint (e.g., "trade-alerts")
2. Click **"Manual sync"** button (top right)
3. Render will reapply all configurations from `render.yaml`, including disk attachments
4. This should attach both services to the **same disk instance**

### Step 3: Verify Disk Sharing (After Sync)

1. Wait 2-3 minutes for services to redeploy
2. Check `config-api` health: `https://config-api-8n37.onrender.com/health`
3. Look for:
   - `"file_exists": true` ✅
   - `"dir_files"` should list `auto_trader_config.json` ✅

### Step 4: Re-save Config from UI (If Needed)

1. Open Scalp-Engine UI
2. Go to Auto-Trader → Configuration
3. Click "💾 Save Configuration" (even if settings are already correct)
4. Wait 30 seconds
5. Check `/health` again - should show `file_exists: true`

### Step 5: Verify Auto-Trader Activation

1. Check `scalp-engine` logs
2. Should see: `✅ Config loaded from API - Mode: AUTO, Stop Loss: TRAILING`
3. Auto-trader should activate within 30-60 seconds

## Alternative: Manual Disk Attachment (If Sync Doesn't Work)

If Manual Sync doesn't fix it:

1. **Identify the correct disk:**
   - Go to `scalp-engine-ui` → **Disk** tab
   - Note the disk name/ID (should be `shared-market-data`)

2. **Attach config-api to same disk:**
   - Go to `config-api` → **Disk** tab
   - If a disk is attached, **detach it first**
   - Click **"Attach Existing Disk"**
   - Select the same disk that `scalp-engine-ui` uses
   - Ensure mount path is `/var/data`
   - Save changes

3. **Verify:**
   - Check `/health` endpoint
   - Should show `file_exists: true` after UI saves config

## Expected Result

After fixing disk sharing:
- ✅ `config-api` `/health` shows `"file_exists": true`
- ✅ `config-api` `/config` returns AUTO/TRAILING config
- ✅ `scalp-engine` logs show `Mode: AUTO, Stop Loss: TRAILING`
- ✅ Auto-trader activates and starts monitoring for trades
