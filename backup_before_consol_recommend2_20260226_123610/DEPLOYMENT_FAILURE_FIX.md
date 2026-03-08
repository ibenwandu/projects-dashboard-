# Critical Fix: Deployment Failures for Scalp-Engine Services

## 🚨 Current Status

Both `scalp-engine` and `scalp-engine-ui` services are **failing to deploy**:
- ❌ `scalp-engine`: Failed deploy (14h ago)
- ❌ `scalp-engine-ui`: Failed deploy (14h ago)
- ✅ `trade-alerts`: Deployed successfully (<1m ago)

## 🔍 Root Cause Analysis

The most likely causes for deployment failures:

### 1. Blueprint Not Synced (MOST LIKELY)
**Problem**: The `render.yaml` has been updated in the repository, but Render hasn't synced the Blueprint yet.

**Evidence**:
- Services were last deployed 14 hours ago
- Recent commits to `render.yaml` haven't triggered redeployment
- Blueprint might still be using old configuration

**Solution**: Manually sync the Blueprint in Render Dashboard

### 2. Nested Directory Structure
**Problem**: There's a nested `Scalp-Engine/Scalp-Engine/` directory that could cause path confusion.

**Evidence**:
- Found `Trade-Alerts/Scalp-Engine/Scalp-Engine/` directory exists
- This could cause the `cd Scalp-Engine &&` command to fail if Render gets confused

**Solution**: Remove nested directory or ensure path resolution works correctly

### 3. Build Command Failure
**Problem**: The `cd Scalp-Engine &&` command in `buildCommand` might be failing if the directory doesn't exist or path is wrong.

**Evidence**:
- Both services use `cd Scalp-Engine &&` in build/start commands
- If the directory doesn't exist, the build will fail immediately

**Solution**: Ensure directory exists and path is correct

### 4. Missing Dependencies or Import Errors
**Problem**: Python import errors or missing dependencies during build.

**Evidence**:
- `scalp_engine.py` imports from `src` directory
- If Python path isn't set correctly, imports will fail

**Solution**: Verify imports and dependencies are correct

---

## ✅ IMMEDIATE FIXES

### Fix 1: Manually Sync Blueprint (CRITICAL)

**Steps**:
1. Go to **Render Dashboard** → **Blueprints**
2. Find the Blueprint that contains `trade-alerts`, `scalp-engine`, and `scalp-engine-ui`
3. Click **"Manual sync"** or **"Apply"** button
4. Wait for Render to sync the updated `render.yaml`
5. Services should automatically redeploy

**Expected Result**:
- Blueprint will read the latest `render.yaml` from GitHub
- Services will redeploy with correct configuration
- Build/start commands will be updated

### Fix 2: Verify Build Commands in Render Dashboard

**Steps**:
1. Go to **Render Dashboard** → `scalp-engine` service → **Settings**
2. Check **Build Command**:
   ```
   cd Scalp-Engine && pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
   ```
3. Check **Start Command**:
   ```
   cd Scalp-Engine && python scalp_engine.py
   ```
4. If commands are different, manually update them
5. Click **Save Changes** → Service will redeploy

**Repeat for `scalp-engine-ui`**:
- **Build Command**: `cd Scalp-Engine && pip install --upgrade pip setuptools wheel && pip install -r requirements.txt`
- **Start Command**: `cd Scalp-Engine && streamlit run scalp_ui.py --server.port=$PORT --server.address=0.0.0.0`

### Fix 3: Check Deployment Logs

**Steps**:
1. Go to **Render Dashboard** → `scalp-engine` service → **Logs**
2. Look for **Build logs** or **Deploy logs**
3. Identify the specific error message:
   - `cd: Scalp-Engine: No such file or directory` → Directory path issue
   - `ModuleNotFoundError: No module named '...'` → Missing dependency
   - `ImportError: cannot import name '...'` → Import path issue
   - `FileNotFoundError: [Errno 2] No such file or directory: '...'` → File path issue
4. Report the specific error for targeted fix

### Fix 4: Verify Repository and Branch

**Steps**:
1. Go to **Render Dashboard** → Blueprint → **Settings**
2. Verify **Repository** is set to: `ibenwandu/Trade-Alerts`
3. Verify **Branch** is set to: `main`
4. Verify **Root Directory** is set to: `/` (root) or blank
5. If any are different, update them and sync

---

## 🔧 ALTERNATIVE FIX: Use rootDir (If cd fails)

If the `cd Scalp-Engine &&` approach continues to fail, we can use Render's `rootDir` property:

```yaml
# SERVICE 2: Scalp-Engine (The Trader)
- type: worker
  name: scalp-engine
  runtime: python
  plan: starter
  rootDir: Scalp-Engine  # Set root directory to Scalp-Engine subfolder
  buildCommand: |
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
  startCommand: python scalp_engine.py
  # ... rest of configuration ...
```

**However**, this approach had issues before (double `src/` paths), so use only if `cd` approach fails.

---

## 📋 Verification Checklist

After applying fixes, verify:

- [ ] Blueprint is synced with latest `render.yaml`
- [ ] `scalp-engine` build command includes `cd Scalp-Engine &&`
- [ ] `scalp-engine` start command includes `cd Scalp-Engine &&`
- [ ] `scalp-engine-ui` build command includes `cd Scalp-Engine &&`
- [ ] `scalp-engine-ui` start command includes `cd Scalp-Engine &&`
- [ ] Repository is set to `ibenwandu/Trade-Alerts`
- [ ] Branch is set to `main`
- [ ] All environment variables are set correctly
- [ ] Disk `shared-market-data` is mounted at `/var/data` for all services
- [ ] Build logs show successful pip install
- [ ] Start logs show successful Python/Streamlit startup
- [ ] No import errors in logs
- [ ] Database can be created/accessed at `/var/data/scalping_rl.db`

---

## 🚀 Next Steps

1. **IMMEDIATE**: Manually sync the Blueprint in Render Dashboard
2. **VERIFY**: Check build/start commands in Render Dashboard Settings
3. **REVIEW**: Check deployment logs for specific error messages
4. **REPORT**: Share specific error messages if issues persist
5. **FIX**: Apply targeted fixes based on error messages

---

## 📝 Summary

**Problem**: Both Scalp-Engine services are failing to deploy

**Most Likely Cause**: Blueprint not synced with updated `render.yaml`

**Solution**: Manually sync Blueprint and verify build/start commands

**Status**: ⏳ Waiting for manual Blueprint sync and error logs

---

**Last Updated**: 2025-01-10
**Priority**: 🔴 CRITICAL - Services are failing to deploy