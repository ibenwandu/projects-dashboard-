# CRITICAL: Disk Sharing Issue - Services Not Sharing Same Disk

## 🔴 Problem Identified

**The file `market_state.json` exists in `trade-alerts` service but is NOT visible from `scalp-engine-ui` service!**

This means the services are **NOT actually sharing the same disk**, even though the `render.yaml` specifies the same disk name (`shared-market-data`).

## 🎯 Root Cause

**Services in DIFFERENT Blueprints CANNOT share disks, even with the same disk name!**

Even though all services have `disk.name: shared-market-data` in `render.yaml`, if they're deployed from different Blueprints, they will have **SEPARATE disks** with the same name.

## ✅ Solution: Verify Blueprint Configuration

### Step 1: Verify All Services Are in the SAME Blueprint

**In Render Dashboard:**

1. **Check Trade-Alerts service:**
   - Go to Render Dashboard → `trade-alerts` service
   - Look for a "Blueprint managed" tag or badge
   - Note the Blueprint name (if any)

2. **Check Scalp-Engine services:**
   - Go to Render Dashboard → `scalp-engine` service
   - Look for a "Blueprint managed" tag or badge
   - Note the Blueprint name (if any)
   
   - Go to Render Dashboard → `scalp-engine-ui` service
   - Look for a "Blueprint managed" tag or badge
   - Note the Blueprint name (if any)

3. **Check if they're in the SAME Blueprint:**
   - If all 3 services show "Blueprint managed" and the **SAME Blueprint name** → ✅ They SHOULD share the disk
   - If different Blueprint names or some not "Blueprint managed" → ❌ They have SEPARATE disks

### Step 2: If Services Are NOT in Same Blueprint

**Option A: Redeploy from Unified Blueprint (RECOMMENDED)**

1. **Delete existing services** (or detach from current Blueprint):
   - Go to Render Dashboard → `scalp-engine` → Settings → Delete Service
   - Go to Render Dashboard → `scalp-engine-ui` → Settings → Delete Service
   - **KEEP `trade-alerts`** (or redeploy it too if needed)

2. **Create NEW Blueprint from Unified render.yaml:**
   - Go to Render Dashboard → **Blueprints**
   - Click **"New Blueprint"**
   - Connect to repository: `Trade-Alerts`
   - Branch: `main`
   - Render will detect the unified `render.yaml` with all 3 services
   - Click **"Apply"**

3. **Verify all services are deployed:**
   - You should see all 3 services (`trade-alerts`, `scalp-engine`, `scalp-engine-ui`) in the new Blueprint
   - All should show "Blueprint managed" with the SAME Blueprint name

4. **Verify shared disk:**
   - All services should show disk name: `shared-market-data`
   - All services should show mount path: `/var/data`
   - Files created in one service should be visible in all services

**Option B: Manually Attach Services to Same Blueprint**

If services already exist:
1. Go to Render Dashboard → **Blueprints**
2. Select the Blueprint containing `trade-alerts`
3. Click **"Add Service"** or **"Import Service"**
4. Add `scalp-engine` and `scalp-engine-ui` to the same Blueprint
5. Ensure they use the same disk name (`shared-market-data`)

### Step 3: Verify Disk Sharing After Fix

**Test 1: Create file in Trade-Alerts**
- Go to Render Dashboard → `trade-alerts` → Shell
- Run:
  ```bash
  echo "test" > /var/data/test_file.txt
  ls -la /var/data/
  ```
- Should see `test_file.txt` and `market_state.json`

**Test 2: Verify file in Scalp-Engine UI**
- Go to Render Dashboard → `scalp-engine-ui` → Shell
- Run:
  ```bash
  ls -la /var/data/
  ```
- **MUST see** `test_file.txt` and `market_state.json` (same files!)

**If Test 2 fails:** Services are still not sharing the same disk. Repeat Step 2.

---

## 🐛 Alternative: Manual File Copy (TEMPORARY FIX)

If you can't redeploy immediately, you can manually copy the file:

**In Trade-Alerts Shell:**
```bash
# Read the file content
cat /var/data/market_state.json
```

**In Scalp-Engine UI Shell:**
```bash
# Create the file with the same content
cat > /var/data/market_state.json << 'EOF'
{
    "timestamp": "2025-01-10T12:00:00Z",
    "global_bias": "NEUTRAL",
    "regime": "NORMAL",
    "approved_pairs": ["EUR/USD", "USD/JPY"],
    "opportunities": [],
    "long_count": 0,
    "short_count": 0,
    "total_opportunities": 0
}
EOF

# Verify it was created
ls -la /var/data/
cat /var/data/market_state.json
```

**⚠️ WARNING**: This is only a temporary fix. The file will need to be manually copied every time Trade-Alerts updates it. The proper solution is to ensure all services are in the same Blueprint.

---

## ✅ Expected Result After Fix

Once all services are in the SAME Blueprint:

1. **File created in Trade-Alerts** → **Visible in Scalp-Engine UI** ✅
2. **Database created in Scalp-Engine** → **Visible in Scalp-Engine UI** ✅
3. **UI can read market_state.json** → **No warning message** ✅
4. **All services share same `/var/data/` directory** → **True shared disk** ✅

---

## 📝 Verification Checklist

After fixing the Blueprint configuration:

- [ ] All 3 services show "Blueprint managed" with SAME Blueprint name
- [ ] All 3 services use disk name: `shared-market-data`
- [ ] All 3 services use mount path: `/var/data`
- [ ] File created in `trade-alerts` is visible in `scalp-engine-ui` shell
- [ ] Database created in `scalp-engine` is visible in `scalp-engine-ui` shell
- [ ] UI shows "File exists: True" (not "False")
- [ ] UI shows files in parent: `market_state.json, scalping_rl.db`
- [ ] No warning message in UI

---

## 🎯 Next Steps

1. **Verify Blueprint configuration** (Step 1)
2. **Redeploy from unified Blueprint** (Step 2, Option A - RECOMMENDED)
3. **Test disk sharing** (Step 3)
4. **Verify UI can read file** (should work automatically)

---

**Last Updated**: 2025-01-10
**Status**: 🔴 **CRITICAL - Services Not Sharing Disk**