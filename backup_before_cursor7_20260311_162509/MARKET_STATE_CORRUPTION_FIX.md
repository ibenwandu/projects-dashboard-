# Market State File Corruption Fix

## Problem
The Scalp-Engine service encountered invalid JSON in `/var/data/market_state.json`, with errors like:
- `Invalid JSON in market state file`
- `Expecting value: line 18 column 29 (char 505)`

## Root Cause
The market state file was being corrupted due to non-atomic writes in `src/market_bridge.py`:
- If the write operation was interrupted (process crash, disk full, network error)
- The file would be left in a partially-written or corrupted state
- Subsequent reads would fail with JSON parse errors

## Solution

### 1. **Atomic Writes with Temporary Files**
Changed `src/market_bridge.py` to use atomic write pattern:
```python
# Before: Direct write (vulnerable to corruption on interruption)
with open(self.filepath, 'w', encoding='utf-8') as f:
    json.dump(state, f, indent=4)

# After: Atomic write (safe from interruption)
temp_fd, temp_path = tempfile.mkstemp(...)
with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
    f.write(json_str)
shutil.move(temp_path, str(self.filepath))  # Atomic rename on same filesystem
```

### 2. **JSON Serialization Validation**
Added pre-write validation to catch non-serializable data:
- Validates JSON before writing to prevent corrupted output
- Detects data type issues early
- Prevents partial writes of invalid data

### 3. **State Sanitization**
Added `_sanitize_state()` method to handle invalid values:
- Removes NaN and Infinity values (JSON incompatible)
- Recursively sanitizes nested structures
- Logs sanitization for debugging

### 4. **Existing Auto-Recovery** (Already in place)
Scalp-Engine already has recovery for corrupt files:
- Detects JSON parse errors (line 780-803 in scalp_engine.py)
- Repairs file with minimal valid state structure
- Allows Trade-Alerts to repopulate with fresh data

## Changes Made

### File: `src/market_bridge.py`

**Method `_write_to_file()`:**
- ✅ Changed from direct write to atomic writes
- ✅ Added JSON serialization validation before write
- ✅ Improved error handling with temp file cleanup
- ✅ Applied same safety to fallback writes

**New Method `_sanitize_state()`:**
- ✅ Recursively processes state dictionary
- ✅ Detects and replaces NaN/Infinity values
- ✅ Handles nested dictionaries and lists
- ✅ Logs sanitization for debugging

## Benefits

1. **Prevents File Corruption**: Atomic writes guarantee file is never in partially-written state
2. **Data Integrity**: Pre-validation prevents invalid JSON from being written
3. **Resilience**: Fallback writes also use atomic pattern
4. **Debuggability**: Sanitization logging helps identify problematic data
5. **Zero Downtime**: Existing auto-recovery handles any residual corrupted files

## How It Works

```
Normal Write Flow:
1. Validate JSON serializability
2. Create temp file in same directory
3. Write JSON to temp file
4. Atomically rename temp → final (one system call)
5. Delete temp on failure (fallback cleanup)

If Write Interrupted:
- Temp file left behind (safe to ignore)
- Original file untouched (still valid)
- Next write creates new temp file
- Service continues normally
```

## Testing

To verify the fix:
1. Monitor logs for "Attempting to export market state"
2. Check for absence of "Invalid JSON" errors
3. Verify market_state.json is always valid JSON
4. Test on Render with real data

## Related Configuration

Environment variables used:
- `MARKET_STATE_FILE_PATH`: Path to market_state.json (default: `/var/data/market_state.json`)
- `MARKET_STATE_API_URL`: Optional API endpoint for state synchronization

## Files Modified

- `src/market_bridge.py`: Added atomic writes and sanitization

## Backward Compatibility

✅ Fully backward compatible - no changes to file format or API
✅ No deployment configuration changes needed
✅ Works with existing Scalp-Engine auto-recovery
