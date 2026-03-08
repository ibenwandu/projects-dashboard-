# Market State Path Fix - Summary

## ✅ Issue Identified

The UI is displaying paths with **corrupted extensions**:
- Path shows: `/var/data/market_state.jsc` (should be `.json`)
- Env var shows: `/var/data/market_state.jsor` (should be `.json`)

**This is NOT truncation** - the paths are fully visible, but the extensions are wrong.

## 🔍 Root Cause

The environment variable `MARKET_STATE_FILE_PATH` in Render Dashboard may be:
1. **Manually set incorrectly** (overriding the `render.yaml` value)
2. **Corrupted during deployment**
3. **Not properly synced** from `render.yaml`

## ✅ Fixes Applied

### 1. **state_reader.py** - Always Use Shared Disk Path on Render
- **Priority 1**: If `/var/data` exists and is writable → Use `/var/data/market_state.json` directly
- **Priority 2**: Only check environment variable if NOT on Render (local dev)
- **Priority 3**: Fix any corruption (`.jsc`, `.jsor` → `.json`) if env var is checked
- **Final**: Always ensure path ends with `.json`

### 2. **scalp_ui.py** - Clean Path Before Use
- Clean environment variable before passing to `MarketStateReader`
- Fix corruption patterns (`.jsc`, `.jsor` → `.json`)
- Always ensure cleaned path ends with `.json`
- Enhanced debug output shows raw env var vs cleaned path

### 3. **Comprehensive Path Validation**
- Multiple layers of path cleaning
- Always defaults to `/var/data/market_state.json` if path is invalid
- Handles both string and Path object inputs

## 🚀 Current Status

- ✅ **Code Fixes**: Applied and committed
- ⏳ **Deployment**: Waiting for Render to redeploy with fixes
- ⚠️ **Environment Variable**: May need manual check in Render Dashboard

## 📋 Next Steps

### Step 1: Wait for Deployment
Render should automatically redeploy after the latest commit. Wait a few minutes for deployment to complete.

### Step 2: Verify Environment Variable in Render Dashboard

**For `scalp-engine-ui` service:**
1. Go to **Render Dashboard** → `scalp-engine-ui` → **Environment**
2. Find `MARKET_STATE_FILE_PATH` environment variable
3. **Verify value is exactly**: `/var/data/market_state.json`
4. If it's different (e.g., `/var/data/market_state.jsc` or `/var/data/market_state.jsor`):
   - Click **Edit** or **Update**
   - Change value to: `/var/data/market_state.json`
   - Click **Save Changes**
   - Service will redeploy automatically

### Step 3: Verify File Exists

**In Render Shell for `scalp-engine-ui` or `trade-alerts`:**
```bash
ls -la /var/data/
cat /var/data/market_state.json
```

**Expected output:**
```
-rw-rw-r-- 1 render render  XXXX Jan 10 XX:XX market_state.json  ← Should be here
```

**If file doesn't exist:**
- Trade-Alerts hasn't generated it yet (wait for scheduled analysis)
- OR Trade-Alerts encountered an error (check Trade-Alerts logs)

## 🎯 Expected Behavior After Fix

Once fixes are deployed:

1. **Path Resolution**:
   - Code will use `/var/data/market_state.json` directly (bypassing potentially corrupted env var)
   - Any corruption in env var will be fixed automatically
   - Path will always end with `.json`

2. **UI Display**:
   - Debug info will show correct path: `/var/data/market_state.json`
   - If file exists, market state will load successfully
   - If file doesn't exist, debug info will show files in `/var/data/` directory

3. **File Loading**:
   - If `market_state.json` exists → Loads successfully
   - If file doesn't exist → Shows warning with file list in parent directory
   - If file is stale (>4 hours old) → Shows as not found

## 🔍 Verification Checklist

After deployment, verify:

- [ ] Services redeploy successfully
- [ ] UI shows correct path: `/var/data/market_state.json` (not `.jsc` or `.jsor`)
- [ ] Environment variable in Render Dashboard is: `/var/data/market_state.json`
- [ ] File exists at `/var/data/market_state.json` (if Trade-Alerts has run)
- [ ] Market state loads successfully in UI (if file exists)
- [ ] Debug info shows files in `/var/data/` directory (if file doesn't exist)

## 📝 Summary

**Problem**: Paths showing `.jsc` and `.jsor` instead of `.json`

**Root Cause**: Environment variable corruption or incorrect value in Render Dashboard

**Solution**: 
1. ✅ Code now always uses `/var/data/market_state.json` on Render (bypasses env var)
2. ✅ Comprehensive path cleaning fixes any corruption
3. ✅ Enhanced debug output for troubleshooting

**Status**: ✅ Fixes committed and pushed. Waiting for Render to redeploy.

---

**Last Updated**: 2025-01-10
**Priority**: 🔴 **CRITICAL** - Path corruption must be fixed for market state to load