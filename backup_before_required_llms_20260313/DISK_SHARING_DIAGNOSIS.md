# Disk Sharing Diagnosis - Services Not Sharing Disk

## 🔴 Problem Confirmed

**The file exists in `trade-alerts` service but is NOT visible from `scalp-engine-ui` service!**

This confirms that the services are **NOT actually sharing the same disk**, even though `render.yaml` specifies the same disk name.

## 🎯 Root Cause

**Services in DIFFERENT Blueprints have SEPARATE disks, even with the same disk name!**

On Render, disk sharing only works when:
1. Services are in the **SAME Blueprint**
2. Services use the **SAME disk name** in `render.yaml`
3. Services are deployed from the **SAME Blueprint**

If services are in different Blueprints, they get **separate disks** with the same name.

---

## ✅ Solution 1: Verify Blueprint Configuration (CRITICAL)

### Step 1: Check if Services Are in Same Blueprint

**In Render Dashboard:**

1. **Go to each service and check "Blueprint managed" tag:**
   - `trade-alerts` → Look for "Blueprint managed" badge
   - `scalp-engine` → Look for "Blueprint managed" badge
   - `scalp-engine-ui` → Look for "Blueprint managed" badge

2. **Check the Blueprint name:**
   - If all 3 services show the **SAME Blueprint name** → They SHOULD share disk (if Blueprint was deployed correctly)
   - If different Blueprint names or some not "Blueprint managed" → They have SEPARATE disks

### Step 2: If Services Are NOT in Same Blueprint

**RECOMMENDED: Redeploy from Unified Blueprint**

1. **Go to Render Dashboard → Blueprints**
2. **Click "New Blueprint"**
3. **Connect to repository:** `Trade-Alerts`
4. **Branch:** `main`
5. **Render will detect the unified `render.yaml`** with all 3 services
6. **Click "Apply"**

This will:
- Create a NEW Blueprint with all 3 services
- Deploy all services from the same Blueprint
- Ensure they share the same disk (`shared-market-data`)

**⚠️ IMPORTANT**: If services already exist, you may need to:
- Delete existing services first (or detach them from their current Blueprint)
- Then create the new Blueprint from the unified `render.yaml`

### Step 3: Verify Disk Sharing After Redeploy

**Test 1: Create file in Trade-Alerts**
```bash
# In trade-alerts shell
echo "test" > /var/data/test_file.txt
ls -la /var/data/
```

**Test 2: Verify file in Scalp-Engine UI**
```bash
# In scalp-engine-ui shell
ls -la /var/data/
# MUST see test_file.txt (same file!)
```

**If Test 2 fails:** Services are still not sharing disk. Repeat Step 2.

---

## 🔧 Solution 2: Manual File Copy (TEMPORARY FIX)

If you can't redeploy immediately, you can manually copy the file to the UI service:

### Step 1: Get File Content from Trade-Alerts

**In Trade-Alerts Shell:**
```bash
cat /var/data/market_state.json
```

### Step 2: Copy File to Scalp-Engine UI

**In Scalp-Engine UI Shell:**
```bash
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

### Step 3: Refresh UI

- Wait 30 seconds (Streamlit cache TTL)
- Refresh the browser page
- Or restart the UI service to clear cache

**⚠️ WARNING**: This is only a temporary fix. You'll need to manually copy the file every time Trade-Alerts updates it. The proper solution is to ensure all services are in the same Blueprint.

---

## 🔍 Solution 3: Check Disk Configuration in Render Dashboard

If services are in the same Blueprint but still not sharing disk:

1. **Go to Render Dashboard → `trade-alerts` → Disk tab**
   - Check disk name: Should be `shared-market-data`
   - Check mount path: Should be `/var/data`

2. **Go to Render Dashboard → `scalp-engine-ui` → Disk tab**
   - Check disk name: Should be `shared-market-data` (SAME as trade-alerts)
   - Check mount path: Should be `/var/data` (SAME as trade-alerts)

3. **If disk names are DIFFERENT:**
   - Services are NOT sharing the same disk
   - You need to redeploy from the unified Blueprint (Solution 1)

---

## ✅ Expected Result After Fix

Once all services are in the SAME Blueprint:

1. ✅ File created in `trade-alerts` → Visible in `scalp-engine-ui` shell
2. ✅ Database created in `scalp-engine` → Visible in `scalp-engine-ui` shell
3. ✅ UI shows "File exists: True" (not "False")
4. ✅ UI shows files in parent: `market_state.json, scalping_rl.db`
5. ✅ No warning message in UI
6. ✅ Market state data displayed in dashboard

---

## 📝 Verification Checklist

After fixing the Blueprint:

- [ ] All 3 services show "Blueprint managed" with SAME Blueprint name
- [ ] All 3 services use disk name: `shared-market-data` (verified in Dashboard)
- [ ] All 3 services use mount path: `/var/data` (verified in Dashboard)
- [ ] File created in `trade-alerts` is visible in `scalp-engine-ui` shell
- [ ] Database created in `scalp-engine` is visible in `scalp-engine-ui` shell
- [ ] UI shows "File exists: True"
- [ ] UI shows files in parent: `market_state.json, scalping_rl.db`
- [ ] No warning message in UI

---

## 🎯 Next Steps

1. **Verify Blueprint configuration** (Check Render Dashboard)
2. **If services are in different Blueprints:** Redeploy from unified Blueprint (Solution 1 - RECOMMENDED)
3. **If you can't redeploy immediately:** Use manual file copy (Solution 2 - TEMPORARY)
4. **Verify disk sharing** (Test 1 & 2)
5. **Verify UI can read file** (should work automatically after fix)

---

**Last Updated**: 2025-01-10
**Status**: 🔴 **CRITICAL - Services Not Sharing Disk - Blueprint Configuration Issue**