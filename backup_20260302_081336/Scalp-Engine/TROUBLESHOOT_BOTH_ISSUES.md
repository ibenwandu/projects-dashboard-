# Troubleshooting: GitHub Actions + Market State Issues

## Issue 1: GitHub Actions Workflow Failure

### Problem
The workflow fails at "Check UI" step because it tries to import `main` function.

### Fix Applied
✅ Updated `.github/workflows/deploy.yml` to import the module instead of the function.

**Before:**
```python
python -c "from scalp_ui import main; print('✅ UI imports successfully')"
```

**After:**
```python
python -c "import scalp_ui; print('✅ UI imports successfully')"
```

### Deploy Fix
```powershell
git add .github/workflows/deploy.yml
git commit -m "Fix GitHub Actions: Import module instead of function"
git push
```

---

## Issue 2: Market State Not Loading (Even After Setting Path)

### Possible Causes

#### Cause 1: File Doesn't Exist at That Path
**Check:**
1. Go to Render Dashboard → `scalp-engine-ui` → **Shell**
2. Run: `ls -la /var/data/`
3. Check if `market_state.json` exists

**If missing:**
- Trade-Alerts needs to generate it
- Or create it manually (see below)

#### Cause 2: Trade-Alerts Not Writing to Shared Disk
**Check:**
1. Go to Trade-Alerts service (if on Render)
2. Verify it's configured to write to `/var/data/market_state.json`
3. Check Trade-Alerts logs to see where it's actually writing

#### Cause 3: Environment Variable Not Applied
**Check:**
1. Go to `scalp-engine-ui` → **Environment**
2. Verify `MARKET_STATE_FILE_PATH` is set
3. **Important:** After setting, the service must restart
4. Check if service restarted automatically (should show in logs)

#### Cause 4: Path Mismatch
**Check:**
- UI is looking at: `/var/data/market_state.json`
- Trade-Alerts is writing to: Different location?
- They must match!

### Quick Test: Create File Manually

1. Go to Render Dashboard → `scalp-engine-ui` → **Shell**
2. Create test file:
   ```bash
   cat > /var/data/market_state.json << 'EOF'
   {
     "timestamp": "2026-01-09T20:00:00Z",
     "global_bias": "BULLISH",
     "regime": "TRENDING",
     "approved_pairs": ["EUR/USD", "USD/JPY"],
     "opportunities": [
       {
         "pair": "EUR/USD",
         "direction": "BUY",
         "entry": "1.0850",
         "stop_loss": "1.0845",
         "take_profit": "1.0858",
         "confidence": "HIGH"
       }
     ],
     "long_count": 2,
     "short_count": 0,
     "total_opportunities": 2
   }
   EOF
   ```

3. Refresh UI - should now show data!

### Verify Path in UI

The UI now shows debug info in the sidebar when market state can't be loaded:
- Path being checked
- Whether file exists
- Environment variable value

**Look for this in the sidebar** when you see the warning.

---

## Step-by-Step Verification

### 1. Check Environment Variable
```bash
# In Render Shell
echo $MARKET_STATE_FILE_PATH
```

### 2. Check File Exists
```bash
# In Render Shell
ls -la /var/data/market_state.json
cat /var/data/market_state.json  # If exists
```

### 3. Check File Permissions
```bash
# In Render Shell
ls -la /var/data/
```

### 4. Check UI Logs
Look for:
- Path being used
- File not found errors
- Permission errors

### 5. Test with Manual File
Create the file manually (see above) and refresh UI.

---

## Expected Behavior After Fix

### GitHub Actions
- ✅ Workflow should pass all checks
- ✅ No import errors
- ✅ Deployment package created

### Market State
- ✅ UI shows debug info in sidebar
- ✅ File path displayed
- ✅ File existence shown
- ✅ Once file exists, data displays correctly

---

## Next Steps

1. ✅ Push GitHub Actions fix
2. ✅ Check Render Shell for file existence
3. ✅ Verify environment variable is set
4. ✅ Create test file if needed
5. ✅ Check UI sidebar for debug info

---

**Status**: Both issues identified and fixes provided! 🚀
