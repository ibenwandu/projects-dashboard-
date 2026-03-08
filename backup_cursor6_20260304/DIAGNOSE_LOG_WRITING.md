# Diagnosing Why Log Files Aren't Being Written

## Current Situation

✅ **Services ARE running** (confirmed from Render dashboard screenshots):
- `scalp-engine` - Active, generating console logs
- `scalp-engine-ui` - Active, generating console logs

❌ **Log files NOT accessible via API**:
- `/logs/engine` returns 500 (should return 404 if no files, or 200 if files exist)
- `/logs/oanda` returns 500
- `/logs/ui` returns 500

## Root Cause Analysis

### Issue 1: Environment Detection

**Logger Code** (`src/logger.py` line 22):
```python
if os.getenv('ENV') == 'production' or os.getenv('RENDER'):
    log_dir = '/var/data/logs'
```

**Render Config** (`render.yaml`):
- ✅ `scalp-engine` has `ENV: production` (line 69)
- ✅ `trade-alerts` has `ENV: production` (line 17)
- ❓ `config-api` - **NEEDS TO BE CHECKED**

**Action**: Verify `config-api` service has `ENV=production` or `RENDER` env var set.

### Issue 2: Disk Mounting

**All services MUST share the same disk**:
- `scalp-engine` → `shared-market-data` mounted at `/var/data`
- `scalp-engine-ui` → `shared-market-data` mounted at `/var/data`
- `config-api` → `shared-market-data` mounted at `/var/data` ✅ (confirmed in render.yaml line 142)

**Status**: ✅ All services share the same disk.

### Issue 3: Logger Module Import

**Services call** (`scalp_engine.py` lines 92-98):
```python
from src.logger import attach_file_handler
attach_file_handler(['ScalpEngine', ...], 'scalp_engine')
```

**Possible Issues**:
1. Import fails silently (caught by `except ImportError`)
2. Logger module not in Python path
3. File handler attachment fails silently

**Action**: Check Render service logs for import errors or warnings.

### Issue 4: File Write Permissions

**Even if logger attaches**, services might not have write access to `/var/data/logs/`.

**Action**: Check if directory exists and is writable.

## Diagnostic Steps

### Step 1: Check config-api Environment Variables

1. Go to Render Dashboard → `config-api` service → Environment
2. Verify:
   - `ENV=production` OR `RENDER` is set
   - If missing, add it

### Step 2: Check Service Logs for Logger Errors

1. Go to Render Dashboard → `scalp-engine` service → Logs
2. Search for:
   - "Logger module not available"
   - "File handler attached"
   - "Failed to create log directory"
   - Any ImportError messages

### Step 3: Test Log Directory Access

**Option A: Use Render Shell** (if available):
1. Render Dashboard → `scalp-engine` → Shell
2. Run:
   ```bash
   ls -la /var/data/logs/
   touch /var/data/logs/test.txt
   rm /var/data/logs/test.txt
   ```

**Option B: Add Diagnostic Endpoint**:
Add to `config_api_server.py`:
```python
@app.route('/debug/log-dir', methods=['GET'])
def debug_log_dir():
    log_dir = _get_log_dir()
    exists = os.path.exists(log_dir)
    writable = os.access(log_dir, os.W_OK) if exists else False
    
    files = []
    if exists:
        try:
            files = os.listdir(log_dir)
        except Exception as e:
            files = [f"Error: {e}"]
    
    return jsonify({
        'log_dir': log_dir,
        'exists': exists,
        'writable': writable,
        'files': files,
        'env_ENV': os.getenv('ENV'),
        'env_RENDER': os.getenv('RENDER'),
    })
```

### Step 4: Verify Logger is Being Called

**Add explicit logging** to `src/logger.py`:
```python
def attach_file_handler(logger_names: list, log_filename: str):
    log_dir = get_log_dir()
    print(f"🔍 [LOGGER] Attaching file handler - dir: {log_dir}, filename: {log_filename}")
    # ... rest of function
    print(f"✅ [LOGGER] File handler attached: {log_file}")
```

This will show in Render console logs if logger is being called.

## Most Likely Issues

### Issue A: Logger Not Being Called
- Services are running but `attach_file_handler` isn't being executed
- Check if import succeeds
- Check if code path reaches the attach call

### Issue B: Environment Detection Failing
- `ENV` or `RENDER` not set on services
- Logger defaults to local `Scalp-Engine/logs/` instead of `/var/data/logs/`
- Files written to wrong location

### Issue C: Write Permissions
- Directory exists but not writable
- Services can't create files in `/var/data/logs/`

## Immediate Actions

1. **Check config-api environment** - Add `ENV=production` if missing
2. **Check service logs** - Look for logger-related errors
3. **Add diagnostic endpoint** - Test log directory access
4. **Add debug logging** - Verify logger is being called

## Expected Outcome

After fixes:
- Services write logs to `/var/data/logs/scalp_engine_YYYYMMDD.log`
- API can read logs from `/var/data/logs/`
- Backup agent can fetch logs via API

