# Unified Blueprint Solution - Simpler Implementation

## ✅ Problem Solved

**Trade-Alerts and Scalp-Engine are in different Blueprints** → Cannot share disk
**Solution**: Add Scalp-Engine services to Trade-Alerts Blueprint → Share same disk ✅

## 🚀 Simple Solution

Instead of using API/webhook, we'll:
1. Add Scalp-Engine as a **subdirectory** in Trade-Alerts repository
2. Update Trade-Alerts `render.yaml` to include Scalp-Engine services using `rootDir`
3. All services in **same Blueprint** = **same shared disk** ✅
4. Deactivate the separate Scalp-Engine Blueprint

**Benefits**:
- ✅ Much simpler (no API needed)
- ✅ True file-based sync (shared disk)
- ✅ No code changes needed (just deployment config)
- ✅ Trade-Alerts service keeps running (no disruption)

---

## 📦 Implementation Steps

### Step 1: Add Scalp-Engine to Trade-Alerts Repository

We have two options:

#### Option A: Git Submodule (Recommended - Keeps Separate Repos)

Add Scalp-Engine as a submodule in Trade-Alerts:

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
git submodule add https://github.com/ibenwandu/Scalp-Engine.git Scalp-Engine
git add .gitmodules Scalp-Engine
git commit -m "Add Scalp-Engine as submodule for unified Blueprint"
git push
```

#### Option B: Copy Files (Simpler - All in One Repo)

Copy Scalp-Engine files into Trade-Alerts:

```powershell
# Copy Scalp-Engine directory
xcopy ..\Scalp-Engine Trade-Alerts\Scalp-Engine\ /E /I /H

cd C:\Users\user\projects\personal\Trade-Alerts
git add Scalp-Engine
git commit -m "Add Scalp-Engine for unified Blueprint deployment"
git push
```

**I recommend Option B (copy files)** - simpler and doesn't require submodule management.

---

### Step 2: Update Trade-Alerts render.yaml

Add Scalp-Engine services to Trade-Alerts Blueprint with `rootDir`:

```yaml
services:
  # Trade-Alerts: LLM Analysis and Market State Generator
  - type: worker
    name: trade-alerts
    rootDir: .  # Current directory (Trade-Alerts root)
    runtime: python
    plan: starter
    buildCommand: |
      pip install --upgrade pip setuptools wheel
      pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      # ... Trade-Alerts config ...
      - key: MARKET_STATE_FILE_PATH
        value: /var/data/market_state.json
    disk:
      name: shared-data
      mountPath: /var/data
      sizeGB: 1

  # Scalp-Engine: Automated Scalping Worker (NEW - Same Blueprint)
  - type: worker
    name: scalp-engine
    rootDir: Scalp-Engine  # Scalp-Engine subdirectory
    runtime: python
    plan: starter
    buildCommand: |
      pip install --upgrade pip setuptools wheel
      pip install -r requirements.txt
    startCommand: python scalp_engine.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.10.0
      - key: ENV
        value: production
      - key: OANDA_ACCESS_TOKEN
        sync: false
      - key: OANDA_ACCOUNT_ID
        sync: false
      - key: OANDA_ENV
        value: practice
      - key: MARKET_STATE_FILE_PATH
        value: /var/data/market_state.json  # Same path as Trade-Alerts
    disk:
      name: shared-data  # SAME disk name = shared ✅
      mountPath: /var/data
      sizeGB: 1

  # Scalp-Engine UI: Streamlit Dashboard (NEW - Same Blueprint)
  - type: web
    name: scalp-engine-ui
    rootDir: Scalp-Engine  # Scalp-Engine subdirectory
    runtime: python
    plan: starter
    buildCommand: |
      pip install --upgrade pip setuptools wheel
      pip install -r requirements.txt
    startCommand: streamlit run scalp_ui.py --server.port $PORT --server.address 0.0.0.0
    envVars:
      - key: PYTHON_VERSION
        value: 3.10.0
      - key: OANDA_ACCESS_TOKEN
        sync: false
      - key: OANDA_ACCOUNT_ID
        sync: false
      - key: OANDA_ENV
        value: practice
      - key: MARKET_STATE_FILE_PATH
        value: /var/data/market_state.json  # Same path as Trade-Alerts
    disk:
      name: shared-data  # SAME disk name = shared ✅
      mountPath: /var/data
      sizeGB: 1
```

**Key Points**:
- ✅ All services use **same disk name**: `shared-data`
- ✅ All services use **same mount path**: `/var/data`
- ✅ All services use **same file path**: `/var/data/market_state.json`
- ✅ Trade-Alerts uses `rootDir: .` (current directory)
- ✅ Scalp-Engine services use `rootDir: Scalp-Engine` (subdirectory)

---

### Step 3: Deploy Updated Blueprint

1. **Push updated Trade-Alerts repository**:
   ```powershell
   cd C:\Users\user\projects\personal\Trade-Alerts
   git add render.yaml Scalp-Engine  # or just render.yaml if using submodule
   git commit -m "Add Scalp-Engine services to unified Blueprint"
   git push
   ```

2. **Render will auto-detect changes**:
   - Go to Render Dashboard → `trade-alerts` Blueprint
   - Click **"Manual sync"** or **"Apply"**
   - Render will add `scalp-engine` and `scalp-engine-ui` services

3. **Set environment variables for new services**:
   - Render will prompt you to set:
     - `OANDA_ACCESS_TOKEN` for `scalp-engine` and `scalp-engine-ui`
     - `OANDA_ACCOUNT_ID` for `scalp-engine` and `scalp-engine-ui`
   - Or they'll sync automatically from Blueprint

---

### Step 4: Deactivate Separate Scalp-Engine Blueprint

Once the unified Blueprint is working:

1. Go to Render Dashboard → `Scalp-Engine` Blueprint
2. Click **Settings** → **Delete Blueprint** (or just pause/stop services)
3. Services are now in Trade-Alerts Blueprint ✅

---

## ✅ Verification

### Check All Services Are in Same Blueprint

1. Go to Render Dashboard → `trade-alerts` Blueprint
2. Should see:
   - ✅ `trade-alerts` (worker)
   - ✅ `scalp-engine` (worker) - NEW
   - ✅ `scalp-engine-ui` (web) - NEW

### Check Disk Sharing Works

1. Go to Render Dashboard → `trade-alerts` → Shell
2. Run: `echo "test" > /var/data/test_file.txt`
3. Go to Render Dashboard → `scalp-engine` → Shell
4. Run: `cat /var/data/test_file.txt` → Should show "test" ✅

### Check Market State Sync

1. Wait for Trade-Alerts analysis (or trigger manually)
2. Check Trade-Alerts logs: `✅ Market State exported to /var/data/market_state.json`
3. Check Scalp-Engine logs: Should see market state loaded successfully
4. Check Scalp-Engine UI: Should show market state without errors ✅

---

## 📊 Architecture After Unification

```
Trade-Alerts Blueprint (Single Blueprint)
    ↓
Shared Disk: shared-data at /var/data
    ↓
    ├─→ trade-alerts (worker)
    │   └─→ Writes: /var/data/market_state.json
    │
    ├─→ scalp-engine (worker)
    │   └─→ Reads: /var/data/market_state.json ✅
    │
    └─→ scalp-engine-ui (web)
        └─→ Reads: /var/data/market_state.json ✅
```

**All in same Blueprint** = **All share same disk** ✅

---

## 🎯 Benefits

1. ✅ **Much simpler** - No API/webhook needed
2. ✅ **True file-based sync** - Direct disk access
3. ✅ **No code changes** - Just deployment config
4. ✅ **Trade-Alerts keeps running** - No disruption
5. ✅ **All services together** - Easier management
6. ✅ **Single Blueprint** - Easier to monitor

---

## ⚠️ Considerations

### Option A: Git Submodule
- ✅ Keeps repositories separate
- ✅ Can still update Scalp-Engine independently
- ⚠️ Requires submodule management
- ⚠️ More complex deployment

### Option B: Copy Files
- ✅ Simplest approach
- ✅ No submodule management
- ⚠️ Scalp-Engine updates need to be copied manually
- ⚠️ Single repository for both projects

**Recommendation**: Use **Option B (copy files)** for simplicity, unless you need to keep Scalp-Engine updates synced automatically (then use submodule).

---

## 📝 Summary

**Problem**: Different Blueprints cannot share disks

**Solution**: Add Scalp-Engine services to Trade-Alerts Blueprint using `rootDir`

**Steps**:
1. Add Scalp-Engine to Trade-Alerts repository (copy files or submodule)
2. Update `render.yaml` with Scalp-Engine services using `rootDir: Scalp-Engine`
3. Deploy updated Blueprint
4. Deactivate separate Scalp-Engine Blueprint

**Result**: All services in same Blueprint = shared disk = file-based sync works! ✅
