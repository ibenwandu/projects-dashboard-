# Render API Fix - Log Endpoints 500 Error

## Problem Identified

The `/logs/<component>` endpoints were returning 500 errors because:

1. **Missing directory creation**: The `_get_log_dir()` function didn't create the log directory if it didn't exist
2. **Insufficient error handling**: Errors didn't provide enough diagnostic information
3. **Health check incomplete**: Health endpoint didn't report log directory status

## Fixes Applied

### 1. Fixed `_get_log_dir()` Function

**Before:**
```python
def _get_log_dir() -> str:
    """Get log directory path (same logic as src/logger.py)"""
    if os.path.exists('/var/data') and os.access('/var/data', os.W_OK):
        log_dir = '/var/data/logs'
    else:
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    return log_dir
```

**After:**
```python
def _get_log_dir() -> str:
    """Get log directory path (same logic as src/logger.py)"""
    if os.path.exists('/var/data') and os.access('/var/data', os.W_OK):
        log_dir = '/var/data/logs'
    else:
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    
    # Ensure directory exists (critical fix - was missing before)
    try:
        os.makedirs(log_dir, exist_ok=True)
        logger.debug(f"Log directory ensured: {log_dir}")
    except Exception as e:
        logger.error(f"Failed to create log directory {log_dir}: {e}")
        # Don't fail completely - return directory anyway, let caller handle errors
    
    return log_dir
```

**Why this fixes it:**
- Now matches the behavior of `src/logger.py` which creates the directory
- Prevents IOError when trying to read from non-existent directory
- Handles permission errors gracefully

### 2. Enhanced Error Messages

**Before:**
```python
except IOError as e:
    logger.error(f"IO Error reading log: {e}")
    return jsonify({'error': f'Could not read log file: {str(e)}'}), 500
```

**After:**
```python
except IOError as e:
    logger.error(f"IO Error reading log: {e}", exc_info=True)
    return jsonify({
        'error': f'Could not read log file: {str(e)}',
        'log_dir': log_dir,
        'component': component,
        'patterns': patterns
    }), 500
```

**Why this helps:**
- Provides diagnostic information for troubleshooting
- Shows exactly which directory and patterns were tried
- Includes full stack trace in logs

### 3. Enhanced Health Endpoint

Added log directory status to health check:
- `log_dir`: Path to log directory
- `log_dir_exists`: Whether directory exists
- `log_dir_readable`: Whether directory is readable
- `log_dir_writable`: Whether directory is writable
- `log_files_count`: Number of log files found
- `log_files`: List of log files (first 10)

**Why this helps:**
- Can diagnose issues without hitting error endpoints
- Shows log directory status at a glance
- Helps verify configuration is correct

## Deployment Steps

### Step 1: Commit and Push Changes

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
git add Scalp-Engine/config_api_server.py
git commit -m "Fix: Create log directory in config API server to prevent 500 errors"
git push
```

### Step 2: Deploy on Render

1. Go to **Render Dashboard** → Your Blueprint
2. Find the **config-api** service
3. Click **"Manual Deploy"** or wait for auto-deploy
4. Monitor deployment logs for any errors

### Step 3: Verify Fix

**Test Health Endpoint:**
```bash
curl https://config-api-8n37.onrender.com/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "log_dir": "/var/data/logs",
  "log_dir_exists": true,
  "log_dir_readable": true,
  "log_dir_writable": true,
  "log_files_count": 3,
  "log_files": ["scalp_engine_20260223.log", "oanda_trades_20260223.log", "scalp_ui_20260223.log"]
}
```

**Test Log Endpoints:**
```bash
# Test engine logs
curl https://config-api-8n37.onrender.com/logs/engine

# Test OANDA logs
curl https://config-api-8n37.onrender.com/logs/oanda

# Test UI logs
curl https://config-api-8n37.onrender.com/logs/ui
```

**Expected Response:**
- Should return log content (plain text)
- Should NOT return 500 errors
- Should return 404 if no log files exist (but directory should exist)

### Step 4: Verify Backup System

After deployment, wait 15 minutes and check:

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
python get_backup_stats.py
```

**Expected:**
- Latest backup should show files backed up from all 4 sources
- Session logs should show `files_backed_up: 4` (not just 1)
- No errors in session metadata

## Root Cause Analysis

The issue occurred because:

1. **Services write logs** → Scalp-Engine, UI, OANDA write to `/var/data/logs/`
2. **Config API reads logs** → Tries to read from `/var/data/logs/`
3. **Directory might not exist** → If services haven't written logs yet, directory doesn't exist
4. **API fails** → Returns 500 error when trying to read from non-existent directory

**The fix ensures:**
- Directory is created before trying to read
- Matches behavior of services that create directory when writing
- Handles edge cases gracefully

## Additional Improvements

### Better Error Handling
- All exceptions now include diagnostic information
- Stack traces logged for debugging
- Error responses include context (log_dir, component, patterns)

### Health Monitoring
- Health endpoint now reports log directory status
- Can proactively detect issues
- Useful for monitoring and alerting

## Testing Checklist

- [ ] Health endpoint shows log directory exists
- [ ] `/logs/engine` returns log content (or 404 if no files)
- [ ] `/logs/oanda` returns log content (or 404 if no files)
- [ ] `/logs/ui` returns log content (or 404 if no files)
- [ ] Backup system successfully backs up all 4 sources
- [ ] Session logs show `files_backed_up: 4` when all sources working
- [ ] No 500 errors in backup session metadata

## Rollback Plan

If issues occur after deployment:

1. **Check Render logs** for config-api service
2. **Verify disk mount** - ensure `/var/data` is accessible
3. **Check permissions** - ensure config-api service can write to `/var/data/logs`
4. **Revert if needed** - git revert the commit and redeploy

## Notes

- This fix is **backward compatible** - doesn't break existing functionality
- **Safe to deploy** - only adds directory creation and better error handling
- **No breaking changes** - API responses remain the same format

