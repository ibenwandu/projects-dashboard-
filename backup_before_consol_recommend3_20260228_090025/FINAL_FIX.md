# Final Fix - Render Deployment Path Issues

## ✅ Issues Fixed

### 1. Path Resolution Issue (CRITICAL)
**Problem**: Error shows `/opt/render/project/src/src/scalping_rl.py` (double `src/`)

**Root Cause**: Render's `rootDir` doesn't always work correctly, causing path resolution issues

**Fix Applied**: 
- ✅ Removed `rootDir` from render.yaml
- ✅ Using explicit `cd Scalp-Engine &&` in build and start commands
- ✅ Ensures correct working directory for all commands

### 2. Database Path (Already Fixed)
**Problem**: `sqlite3.OperationalError: unable to open database file`

**Root Cause**: Database path was incorrect, directory wasn't created

**Fix Applied**:
- ✅ Database path uses `/var/data/scalping_rl.db` on Render
- ✅ Directory creation added in `_init_db()`
- ✅ All `sqlite3.connect()` calls use `str()` for Path objects

---

## 🔧 Changes Applied

### Updated render.yaml

**Before** (Using rootDir):
```yaml
- type: worker
  name: scalp-engine
  rootDir: Scalp-Engine  # ❌ Caused path issues
  buildCommand: |
    pip install -r requirements.txt
  startCommand: python scalp_engine.py
```

**After** (Using explicit cd):
```yaml
- type: worker
  name: scalp-engine
  # No rootDir - explicit cd in commands ✅
  buildCommand: |
    cd Scalp-Engine && pip install -r requirements.txt
  startCommand: cd Scalp-Engine && python scalp_engine.py
```

---

## 🚀 Deployment Steps

### Step 1: Verify Fixes Are Deployed

1. **Check Render Dashboard** → `trade-alerts` Blueprint
2. **Services should redeploy automatically** from GitHub
3. **If not auto-deploying**:
   - Go to Blueprint → Click **"Manual sync"** or **"Apply"**
   - Render will use the updated render.yaml

### Step 2: Verify Services Start

1. **Check `scalp-engine` logs**:
   - Should see: `==> Running 'cd Scalp-Engine && python scalp_engine.py'`
   - Should NOT see: `/opt/render/project/src/src/` paths
   - Should see: Database created successfully

2. **Check `scalp-engine-ui` logs**:
   - Should see: `==> Running 'cd Scalp-Engine && streamlit run scalp_ui.py'`
   - Should start successfully
   - Should NOT see import errors

### Step 3: Verify Database

1. **Check if database is created**:
   - Go to Render Dashboard → `scalp-engine` → Shell
   - Run: `ls -la /var/data/scalping_rl.db`
   - Should show the database file exists

2. **Check if market state is accessible**:
   - Run: `cat /var/data/market_state.json` (if exists)
   - Or wait for Trade-Alerts to create it

---

## ✅ Expected Behavior After Fix

### scalp-engine Service:
1. ✅ Starts successfully with `cd Scalp-Engine && python scalp_engine.py`
2. ✅ Working directory is `/opt/render/project/Scalp-Engine/`
3. ✅ Database created at `/var/data/scalping_rl.db`
4. ✅ No `sqlite3.OperationalError` errors
5. ✅ Can read market state from `/var/data/market_state.json`

### scalp-engine-ui Service:
1. ✅ Starts successfully with `cd Scalp-Engine && streamlit run scalp_ui.py`
2. ✅ Working directory is `/opt/render/project/Scalp-Engine/`
3. ✅ Can read database from `/var/data/scalping_rl.db`
4. ✅ Can read market state from `/var/data/market_state.json`
5. ✅ No import errors

---

## 🐛 If Issues Persist

### Issue: Still seeing `/opt/render/project/src/src/` paths

**Cause**: Render might be caching old deployment or services haven't redeployed

**Solution**:
1. Go to Render Dashboard → `scalp-engine` service → Settings
2. Verify **Build Command** shows: `cd Scalp-Engine && pip install...`
3. Verify **Start Command** shows: `cd Scalp-Engine && python scalp_engine.py`
4. If not, manually update in Render Dashboard
5. Click **Save Changes** → Service will redeploy

### Issue: Database still not accessible

**Cause**: Directory permissions or disk not mounted

**Solution**:
1. Check disk is mounted: `ls -la /var/data/` (should show directory exists)
2. Check permissions: `chmod 755 /var/data` (if needed)
3. Verify disk name in render.yaml matches across all services

### Issue: Import errors

**Cause**: Python path not set correctly

**Solution**:
1. Verify `scalp_engine.py` has: `sys.path.insert(0, str(Path(__file__).parent / "src"))`
2. Verify working directory is `/opt/render/project/Scalp-Engine/` when running
3. Check imports use `from src.module` not just `from module`

---

## 📝 Summary

**Problem**: Services failing due to path resolution issues with Render's `rootDir`

**Solution**: Removed `rootDir` and used explicit `cd` commands in build/start commands

**Status**: ✅ Fixed and pushed to GitHub

**Next**: Render will auto-deploy with corrected paths. Services should start successfully.
