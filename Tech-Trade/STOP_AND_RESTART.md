# How to Stop Old Process and Restart with Fix

## Quick Instructions

### Step 1: Stop the Old Process

**Option A: In the terminal window (easiest)**
1. Switch to the terminal window where the download is running
2. Press `Ctrl + C` to stop the process
3. Wait for it to finish stopping

**Option B: If Ctrl+C doesn't work**
1. Open PowerShell or Command Prompt
2. Find the process:
   ```powershell
   Get-Process python | Select-Object Id, ProcessName, Path
   ```
3. Kill the process (replace `<ProcessId>` with the actual ID):
   ```powershell
   Stop-Process -Id <ProcessId> -Force
   ```

**Option C: Kill all Python processes (nuclear option)**
```powershell
Get-Process python | Stop-Process -Force
```
⚠️ Warning: This will kill ALL Python processes running on your computer

### Step 2: Verify It's Stopped

Check if the process is stopped:
```powershell
Get-Process python -ErrorAction SilentlyContinue
```
If no output, all Python processes are stopped.

### Step 3: Restart with Fix

1. Navigate to Tech-Trade directory:
   ```powershell
   cd C:\Users\user\projects\personal\Tech-Trade
   ```

2. Run the download with the new fix:
   ```powershell
   python main.py --download
   ```

3. Watch for yfinance fallback messages:
   - Look for: "No data retrieved from Dukascopy for..."
   - Look for: "Attempting yfinance fallback for..."
   - Look for: "✅ Successfully fetched X records using yfinance fallback"

### Step 4: Verify Data Downloaded

Check if files were created:
```powershell
Get-ChildItem data\raw | Select-Object Name, Length, LastWriteTime
```

## What You'll See

### Old Process (with errors):
```
Downloading EUR/USD: 13%|...| 246/1825 [02:05<13:18]
Error: 403 Forbidden
Error: 403 Forbidden
...
```

### New Process (with fix):
```
Downloading EUR/USD: 100% [10/10 days]
No data retrieved from Dukascopy for EUR/USD
Attempting yfinance fallback for EUR/USD...
✅ Successfully fetched 7 records using yfinance fallback
💾 Cached to: data/raw/EURUSD_1DAY_20251229_20260108.csv
```

## Tips

1. **Let it finish**: The new process will be much faster (seconds vs hours)
2. **Watch the logs**: You'll see yfinance fallback messages
3. **Check files**: Verify files are created in `data/raw/`
4. **Don't worry**: The old failed downloads won't interfere

## Troubleshooting

**If Ctrl+C doesn't work:**
- Close the terminal window (will kill the process)
- Or use Task Manager (Ctrl+Shift+Esc) to end the Python process

**If you see "file in use" errors:**
- The old process may still be writing
- Wait a few seconds, then try again
- Or restart your computer (nuclear option)

**If download still fails:**
- Check internet connection
- Verify yfinance is installed: `pip install yfinance`
- Check logs for specific errors

