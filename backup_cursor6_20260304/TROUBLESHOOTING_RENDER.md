# Troubleshooting Render Deployment - Trade Alerts

## Service Status: Failed

If your `trade-alerts` service shows "Failed service" on Render, follow these steps:

## Step 1: Check Render Logs

1. Go to Render Dashboard → `trade-alerts` service
2. Click on **"Logs"** tab
3. Look for error messages (usually at the bottom)
4. Common errors to look for:
   - Import errors
   - Missing environment variables
   - Module not found
   - Authentication errors
   - Syntax errors

## Step 2: Common Issues & Fixes

### Issue 1: Missing Dependencies
**Error:** `ModuleNotFoundError: No module named 'X'`

**Fix:**
- Check `requirements.txt` includes all packages
- Ensure `PyDrive2` and `oauth2client` are listed
- Redeploy after updating requirements.txt

### Issue 2: Missing Environment Variables
**Error:** `GOOGLE_DRIVE_FOLDER_ID not set` or similar

**Fix:**
- Go to Render Dashboard → Your Service → Environment
- Add ALL required environment variables:
  - `GOOGLE_DRIVE_FOLDER_ID`
  - `GOOGLE_DRIVE_CREDENTIALS_JSON` (full JSON)
  - `GOOGLE_DRIVE_REFRESH_TOKEN`
  - `OPENAI_API_KEY`
  - `GOOGLE_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `SENDER_EMAIL`
  - `SENDER_PASSWORD`
  - `RECIPIENT_EMAIL`
  - `PUSHOVER_API_TOKEN`
  - `PUSHOVER_USER_KEY`

### Issue 3: Import Errors
**Error:** `ImportError` or `ModuleNotFoundError`

**Fix:**
- Check `requirements.txt` is complete
- Verify all imports in code are correct
- Check for typos in module names

### Issue 4: Authentication Errors
**Error:** Google Drive authentication failures

**Fix:**
- Verify `GOOGLE_DRIVE_CREDENTIALS_JSON` is valid JSON
- Check `GOOGLE_DRIVE_REFRESH_TOKEN` is correct
- Ensure credentials have proper permissions

### Issue 5: File Path Issues
**Error:** File not found or path errors

**Fix:**
- Render uses Linux paths (forward slashes)
- Check code uses `os.path.join()` for paths
- Verify directory creation logic

### Issue 6: Model Name Errors
**Error:** Model not found (404 errors)

**Fix:**
- Verify model names are correct:
  - Gemini: `gemini-pro`
  - Claude: `claude-3-5-sonnet-20240229`
  - ChatGPT: `gpt-4o-mini`
- Check API keys are valid

## Step 3: Verify Configuration Files

### Check render.yaml
```yaml
services:
  - type: worker
    name: trade-alerts
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
```

### Check Procfile
```
worker: python main.py
```

### Check requirements.txt
Ensure it includes:
- PyDrive2
- oauth2client
- openai
- google-generativeai
- anthropic
- python-dotenv
- requests
- (all other dependencies)

## Step 4: Manual Deployment Check

1. **Check Build Logs:**
   - Render Dashboard → Service → "Events" tab
   - Look for build errors

2. **Check Runtime Logs:**
   - Render Dashboard → Service → "Logs" tab
   - Look for runtime errors

3. **Test Locally First:**
   ```powershell
   python main.py
   ```
   If it fails locally, it will fail on Render

## Step 5: Quick Fixes

### Fix 1: Force Redeploy
1. Render Dashboard → Service → "Manual Deploy"
2. Click "Clear build cache & deploy"
3. Wait for deployment

### Fix 2: Check Python Version
- Render defaults to Python 3.11
- If you need a specific version, add to `runtime.txt`:
  ```
  python-3.11.0
  ```

### Fix 3: Verify Start Command
- Should be: `python main.py`
- Check `Procfile` or `render.yaml` startCommand

## Step 6: Debugging Steps

1. **Add Debug Logging:**
   - Check `src/logger.py` outputs to stdout
   - Render captures stdout/stderr

2. **Test Environment Variables:**
   - Use Render Shell to test:
     ```bash
     echo $GOOGLE_DRIVE_FOLDER_ID
     ```

3. **Check File Structure:**
   - Ensure `main.py` is in root directory
   - Verify `src/` directory exists
   - Check all files are committed to git

## Step 7: Common Error Messages

### "No such file or directory"
- **Cause:** Missing file or wrong path
- **Fix:** Check file paths, use relative paths

### "Permission denied"
- **Cause:** File permissions issue
- **Fix:** Check file permissions in git

### "Module not found"
- **Cause:** Missing dependency
- **Fix:** Add to requirements.txt and redeploy

### "Environment variable not set"
- **Cause:** Missing env var in Render
- **Fix:** Add to Render Dashboard → Environment

### "Authentication failed"
- **Cause:** Invalid credentials
- **Fix:** Verify API keys and tokens

## Step 8: Get Help

If still failing:
1. Copy the exact error from Render logs
2. Check the last 50 lines of logs
3. Verify all environment variables are set
4. Test locally to reproduce the error
5. Check Render status page for outages

## Quick Checklist

- [ ] All environment variables set in Render
- [ ] requirements.txt includes all dependencies
- [ ] render.yaml or Procfile is correct
- [ ] main.py exists in root directory
- [ ] Code runs locally without errors
- [ ] Build logs show successful build
- [ ] Runtime logs show service starting
- [ ] No import errors in logs
- [ ] No authentication errors
- [ ] Model names are correct







