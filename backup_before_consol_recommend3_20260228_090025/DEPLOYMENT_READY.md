# ✅ Unified Blueprint - Ready for Deployment

## 🎯 Consolidation Complete

All services are now in **ONE unified Blueprint** with a **single render.yaml** file.

---

## ✅ What Was Done

1. **✅ Created unified render.yaml** in `Trade-Alerts/` root directory
2. **✅ Deleted conflicting render.yaml** from `Trade-Alerts/Scalp-Engine/` subfolder
3. **✅ Verified directory structure** - Scalp-Engine files are in `Scalp-Engine/` subfolder
4. **✅ Updated build commands** - Added `cd Scalp-Engine &&` to build and start commands
5. **✅ Fixed Streamlit command** - Using `--server.port=$PORT` (equals sign for proper parsing)
6. **✅ Unified disk name** - All services use `shared-market-data` (same name = shared disk)
7. **✅ Unified file path** - All services use `/var/data/market_state.json`

---

## 📋 Unified Blueprint Structure

### Repository: Trade-Alerts
```
Trade-Alerts/
├── main.py                    # Trade-Alerts worker (runs from root)
├── requirements.txt           # Trade-Alerts dependencies (runs from root)
├── render.yaml                # ✅ UNIFIED Blueprint (single file)
└── Scalp-Engine/              # Scalp-Engine subfolder
    ├── scalp_engine.py        # Scalp-Engine worker (requires cd Scalp-Engine)
    ├── scalp_ui.py            # Scalp-Engine UI (requires cd Scalp-Engine)
    ├── requirements.txt       # Scalp-Engine dependencies (requires cd Scalp-Engine)
    └── src/                   # Source modules
```

### Services in Blueprint:
1. **trade-alerts** (worker) - Runs from root, writes `/var/data/market_state.json`
2. **scalp-engine** (worker) - Runs from `Scalp-Engine/`, reads `/var/data/market_state.json`, writes `/var/data/scalping_rl.db`
3. **scalp-engine-ui** (web) - Runs from `Scalp-Engine/`, reads both files

---

## ✅ Key Configuration

### Shared Disk (Critical for File Sharing)
```yaml
disk:
  name: shared-market-data  # SAME for all 3 services ✅
  mountPath: /var/data      # SAME for all 3 services ✅
  sizeGB: 1
```

### Shared File Paths
- **Market State**: `/var/data/market_state.json` (all services use this)
- **Database**: `/var/data/scalping_rl.db` (worker writes, UI reads)

### Build Commands (Directory Aware)
- **Trade-Alerts**: `pip install ...` (runs from root)
- **Scalp-Engine**: `cd Scalp-Engine && pip install ...` (cd to subfolder)
- **Scalp-UI**: `cd Scalp-Engine && pip install ...` (cd to subfolder)

### Start Commands (Directory Aware)
- **Trade-Alerts**: `python main.py` (runs from root)
- **Scalp-Engine**: `cd Scalp-Engine && python scalp_engine.py` (cd to subfolder)
- **Scalp-UI**: `cd Scalp-Engine && streamlit run scalp_ui.py --server.port=$PORT --server.address=0.0.0.0` (cd to subfolder, using = for port)

---

## 🚀 Next Steps: Deploy on Render

### Step 1: Connect Blueprint to Repository
1. Go to Render Dashboard
2. Create new Blueprint (or use existing Trade-Alerts Blueprint)
3. Connect to repository: `Trade-Alerts` repository
4. Render will detect `render.yaml` in root
5. All 3 services will be automatically created ✅

### Step 2: Verify Environment Variables
**For `trade-alerts` service:**
- Set: `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_DRIVE_CREDENTIALS_JSON`, `GOOGLE_DRIVE_REFRESH_TOKEN`
- Set: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`
- Set: `SENDER_EMAIL`, `SENDER_PASSWORD`, `RECIPIENT_EMAIL`
- ✅ `MARKET_STATE_FILE_PATH` is already set in render.yaml (`/var/data/market_state.json`)

**For `scalp-engine` service:**
- Set: `OANDA_ACCESS_TOKEN`, `OANDA_ACCOUNT_ID`
- ✅ `MARKET_STATE_FILE_PATH` is already set in render.yaml (`/var/data/market_state.json`)
- ✅ `PYTHONUNBUFFERED=1` is already set in render.yaml

**For `scalp-engine-ui` service:**
- Set: `OANDA_ACCESS_TOKEN`, `OANDA_ACCOUNT_ID` (optional, same as worker)
- ✅ `MARKET_STATE_FILE_PATH` is already set in render.yaml (`/var/data/market_state.json`)
- ✅ `PYTHONUNBUFFERED=1` is already set in render.yaml

### Step 3: Verify Shared Disk
After deployment, check that all services show:
- **Disk name**: `shared-market-data` (must be EXACTLY the same)
- **Mount path**: `/var/data` (must be EXACTLY the same)

If disk names don't match exactly, Render creates separate disks (not shared)!

---

## ✅ Verification Checklist

After deployment:

- [ ] All 3 services deployed in same Blueprint
- [ ] All services show disk name: `shared-market-data`
- [ ] All services show mount path: `/var/data`
- [ ] Trade-Alerts logs show: `✅ Market State exported to /var/data/market_state.json`
- [ ] Scalp-Engine logs show: `✅ RL Database connected at shared path: /var/data/scalping_rl.db`
- [ ] Scalp-Engine UI shows market state (no warning banner)
- [ ] Scalp-Engine UI shows trade data (when worker executes trades)

---

## 🎯 Expected Behavior

### File Sharing (Now Works ✅)
- **Trade-Alerts** writes to `/var/data/market_state.json`
- **Scalp-Engine worker** reads from `/var/data/market_state.json` ✅
- **Scalp-Engine UI** reads from `/var/data/market_state.json` ✅
- **Scalp-Engine worker** writes to `/var/data/scalping_rl.db`
- **Scalp-Engine UI** reads from `/var/data/scalping_rl.db` ✅

### No More Split-Brain Issue
- ✅ All services in ONE Blueprint
- ✅ All services use SAME disk name
- ✅ Files are truly shared
- ✅ No more "file not found" errors

---

## 📝 Important Notes

1. **Disk Name Must Match Exactly**: All services must use `shared-market-data` (exactly, case-sensitive)
2. **Mount Path Must Match Exactly**: All services must use `/var/data` (exactly)
3. **Directory Structure**: Scalp-Engine files are in `Scalp-Engine/` subfolder, so commands use `cd Scalp-Engine &&`
4. **Streamlit Command**: Using `--server.port=$PORT` with equals sign (prevents parsing errors)

---

**Status**: ✅ Ready for deployment! All services consolidated into unified Blueprint with shared disk.
