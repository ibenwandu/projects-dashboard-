# Fix: ModuleNotFoundError on Render

## Problem

The Streamlit UI shows this error on Render:
```
ModuleNotFoundError: No module named 'src.scalping_rl'
```

## Root Cause

On Render, the working directory structure is different from local development. The Python path needs to be set up correctly to find the `src` module.

## Solution Applied

Updated `scalp_ui.py` to:
1. Add project root to `sys.path`
2. Add `src` directory to `sys.path` 
3. Use absolute paths for reliability

## Files Changed

- ✅ `scalp_ui.py` - Fixed import path setup

## Deploy Fix

```powershell
git add scalp_ui.py
git commit -m "Fix import paths for Render deployment"
git push
```

Render will auto-deploy the fix.

## Verify

After deployment:
1. Check Render logs for any import errors
2. Access UI URL - should load without errors
3. Verify all tabs work correctly

---

**Status**: Fixed! Push and deploy. 🚀
