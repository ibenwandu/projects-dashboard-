# Simple Unified Blueprint Solution

## ✅ Problem Solved

**Different Blueprints cannot share disks** → Use **same Blueprint** for all services ✅

## 🎯 Simple Solution

Add Scalp-Engine services to **Trade-Alerts Blueprint** using `rootDir`:
- ✅ All services in **same Blueprint** = **shared disk** works
- ✅ No API/webhook needed - just file-based sync
- ✅ Much simpler implementation
- ✅ Trade-Alerts keeps running (no disruption)

---

## 📦 Step-by-Step Implementation

### Step 1: Copy Scalp-Engine to Trade-Alerts

Run the setup script (or manually copy):

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
.\setup_unified_blueprint.ps1
```

**Or manually**:
```powershell
# Copy Scalp-Engine directory (exclude .git, .env, etc.)
xcopy ..\Scalp-Engine Scalp-Engine\ /E /I /XD .git __pycache__ /XF .env *.db *.sqlite market_state.json
```

This copies Scalp-Engine files into Trade-Alerts repository as a subdirectory.

---

### Step 2: Updated render.yaml is Ready ✅

The `render.yaml` has been updated to include:
- ✅ `trade-alerts` service (existing - keeps running)
- ✅ `scalp-engine` service (NEW - same Blueprint)
- ✅ `scalp-engine-ui` service (NEW - same Blueprint)

**Key**: All services use **same disk name** (`shared-data`) = **shared disk** ✅

---

### Step 3: Commit and Push

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
git add Scalp-Engine render.yaml UNIFIED_BLUEPRINT_SOLUTION.md SIMPLE_UNIFIED_SOLUTION.md
git commit -m "Add Scalp-Engine services to unified Blueprint for shared disk"
git push
```

---

### Step 4: Deploy on Render

1. **Go to Render Dashboard** → `trade-alerts` Blueprint
2. **Click "Manual sync"** or **"Apply"**
3. **Render will detect new services**:
   - `scalp-engine` (worker) - will be added
   - `scalp-engine-ui` (web) - will be added
4. **Set environment variables** for new services:
   - `OANDA_ACCESS_TOKEN` (required)
   - `OANDA_ACCOUNT_ID` (required)
   - `OANDA_ENV` = `practice` (default, or set to `live`)
5. **Deploy** → Services will start automatically

---

### Step 5: Deactivate Separate Scalp-Engine Blueprint (After Verification)

Once unified Blueprint is working:

1. **Verify all services are running**:
   - ✅ `trade-alerts` - still running
   - ✅ `scalp-engine` - new, running
   - ✅ `scalp-engine-ui` - new, running

2. **Test disk sharing**:
   - Go to `trade-alerts` → Shell
   - Run: `echo "test" > /var/data/test_file.txt`
   - Go to `scalp-engine` → Shell
   - Run: `cat /var/data/test_file.txt` → Should show "test" ✅

3. **Test market state sync**:
   - Wait for Trade-Alerts analysis (or trigger manually)
   - Check Trade-Alerts logs: `✅ Market State exported to /var/data/market_state.json`
   - Check Scalp-Engine logs: Should see market state loaded
   - Check Scalp-Engine UI: Should show market state without errors ✅

4. **Deactivate separate Blueprint**:
   - Go to Render Dashboard → `Scalp-Engine` Blueprint
   - Click **Settings** → **Delete Blueprint** (or pause/stop services)
   - ✅ All services now in Trade-Alerts Blueprint

---

## ✅ Architecture After Unification

```
Trade-Alerts Blueprint (Single Blueprint)
    ↓
Shared Disk: shared-data at /var/data
    ↓
    ├─→ trade-alerts (worker)
    │   rootDir: . (Trade-Alerts root)
    │   └─→ Writes: /var/data/market_state.json
    │
    ├─→ scalp-engine (worker)
    │   rootDir: Scalp-Engine (subdirectory)
    │   └─→ Reads: /var/data/market_state.json ✅
    │
    └─→ scalp-engine-ui (web)
        rootDir: Scalp-Engine (subdirectory)
        └─→ Reads: /var/data/market_state.json ✅
```

**All in same Blueprint** = **All share same disk** = **File sync works!** ✅

---

## 🎯 Benefits

1. ✅ **Much simpler** - No API/webhook needed
2. ✅ **True file-based sync** - Direct disk access
3. ✅ **No code changes** - Just deployment config
4. ✅ **Trade-Alerts keeps running** - No disruption
5. ✅ **All services together** - Easier management
6. ✅ **Single Blueprint** - Easier monitoring

---

## 📝 Summary

**Problem**: Different Blueprints cannot share disks

**Solution**: Add Scalp-Engine services to Trade-Alerts Blueprint using `rootDir`

**Steps**:
1. ✅ Copy Scalp-Engine to Trade-Alerts (or use setup script)
2. ✅ Updated `render.yaml` is ready
3. ⏳ Commit and push changes
4. ⏳ Deploy on Render (manual sync)
5. ⏳ Set environment variables for new services
6. ⏳ Verify disk sharing works
7. ⏳ Deactivate separate Scalp-Engine Blueprint

**Result**: All services in same Blueprint = shared disk = file-based sync works! ✅
