# Unified Blueprint Consolidation - Complete

## ✅ Consolidation Complete

All services are now in **ONE unified Blueprint** with a **single render.yaml** file in the Trade-Alerts root directory.

---

## 📋 What Was Done

### 1. ✅ Deleted Conflicting render.yaml Files
- ❌ Deleted: `Trade-Alerts/Scalp-Engine/render.yaml` (subfolder)
- ✅ Kept: `Trade-Alerts/render.yaml` (root - unified Blueprint)
- ℹ️ Note: `Scalp-Engine/render.yaml` (separate repo) still exists for standalone deployment, but is not used in unified Blueprint

### 2. ✅ Created Unified render.yaml
- **Location**: `Trade-Alerts/render.yaml` (root directory)
- **Contains**: All 3 services (trade-alerts, scalp-engine, scalp-engine-ui)
- **Disk**: All use `shared-market-data` (same name = shared disk) ✅
- **Path**: All use `/var/data/market_state.json` (same path) ✅

### 3. ✅ Verified Directory Structure
- **Trade-Alerts files**: Root directory (`main.py`, `requirements.txt`)
- **Scalp-Engine files**: `Scalp-Engine/` subfolder (`scalp_engine.py`, `scalp_ui.py`, `requirements.txt`)
- **Build commands**: Updated to use `cd Scalp-Engine &&` since files are in subfolder ✅

---

## 🎯 Unified Blueprint Configuration

### Service 1: Trade-Alerts (Worker)
```yaml
name: trade-alerts
buildCommand: pip install ... (runs from root)
startCommand: python main.py (runs from root)
disk: shared-market-data at /var/data
MARKET_STATE_FILE_PATH: /var/data/market_state.json
```

### Service 2: Scalp-Engine (Worker)
```yaml
name: scalp-engine
buildCommand: cd Scalp-Engine && pip install ... (cd to subfolder)
startCommand: cd Scalp-Engine && python scalp_engine.py (cd to subfolder)
disk: shared-market-data at /var/data (SAME as Service 1) ✅
MARKET_STATE_FILE_PATH: /var/data/market_state.json (SAME as Service 1) ✅
```

### Service 3: Scalp-Engine UI (Web)
```yaml
name: scalp-engine-ui
buildCommand: cd Scalp-Engine && pip install ... (cd to subfolder)
startCommand: cd Scalp-Engine && streamlit run scalp_ui.py --server.port=$PORT --server.address=0.0.0.0
disk: shared-market-data at /var/data (SAME as Service 1) ✅
MARKET_STATE_FILE_PATH: /var/data/market_state.json (SAME as Service 1) ✅
```

---

## ✅ Key Features

### 1. Single Shared Disk
- **Disk name**: `shared-market-data` (same for all services)
- **Mount path**: `/var/data` (same for all services)
- **Result**: All services can read/write to the same files ✅

### 2. Shared Files
- **Market state**: `/var/data/market_state.json`
  - Trade-Alerts writes to this file
  - Scalp-Engine worker reads from this file
  - Scalp-Engine UI reads from this file
- **Database**: `/var/data/scalping_rl.db`
  - Scalp-Engine worker writes to this file
  - Scalp-Engine UI reads from this file

### 3. Correct Directory Structure
- Files in `Scalp-Engine/` subfolder → Build commands use `cd Scalp-Engine &&`
- This ensures commands run from the correct directory

---

## 📋 Deployment Steps

### Step 1: Commit and Push (Done ✅)
- Unified `render.yaml` created and committed
- Conflicting `render.yaml` deleted
- Changes pushed to GitHub

### Step 2: Deploy on Render
1. Go to Render Dashboard → **Trade-Alerts** Blueprint (or create new Blueprint)
2. Connect to repository: `Trade-Alerts` repository
3. Render will detect the unified `render.yaml` with all 3 services
4. All services will be deployed from the same Blueprint ✅

### Step 3: Verify Environment Variables
**For `trade-alerts` service:**
- Set Google Drive, LLM API keys, Email config in Render Dashboard
- `MARKET_STATE_FILE_PATH` is already set in render.yaml ✅

**For `scalp-engine` service:**
- Set `OANDA_ACCESS_TOKEN` and `OANDA_ACCOUNT_ID` in Render Dashboard
- `MARKET_STATE_FILE_PATH` is already set in render.yaml ✅

**For `scalp-engine-ui` service:**
- Set `OANDA_ACCESS_TOKEN` and `OANDA_ACCOUNT_ID` in Render Dashboard (optional, same as worker)
- `MARKET_STATE_FILE_PATH` is already set in render.yaml ✅

### Step 4: Verify Shared Disk
All services should show:
- **Disk name**: `shared-market-data`
- **Mount path**: `/var/data`
- **Files visible to all**: `market_state.json`, `scalping_rl.db`

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] All 3 services are in the same Blueprint
- [ ] All services use disk name `shared-market-data`
- [ ] All services use mount path `/var/data`
- [ ] Trade-Alerts writes to `/var/data/market_state.json`
- [ ] Scalp-Engine reads from `/var/data/market_state.json`
- [ ] Scalp-Engine UI reads from `/var/data/market_state.json`
- [ ] Scalp-Engine worker writes to `/var/data/scalping_rl.db`
- [ ] Scalp-Engine UI reads from `/var/data/scalping_rl.db`

---

## 🎯 Result

**Before**:
- ❌ Trade-Alerts and Scalp-Engine in different Blueprints
- ❌ Different disk names (even if same name, different Blueprints = different disks)
- ❌ Files not shared between services
- ❌ Market state file not accessible to Scalp-Engine

**After**:
- ✅ All 3 services in ONE Blueprint
- ✅ Same disk name (`shared-market-data`) = TRUE shared disk
- ✅ Files shared between all services
- ✅ Market state file accessible to all services ✅

---

## 📝 Notes

- The separate `Scalp-Engine` repository's `render.yaml` is not used in this unified Blueprint
- All services deploy from the `Trade-Alerts` repository
- Scalp-Engine files are in the `Scalp-Engine/` subfolder
- Build commands include `cd Scalp-Engine &&` to navigate to subfolder

---

**Status**: ✅ Unified Blueprint created and ready for deployment!
