# Render Deployment Fix Checklist

## Service Status: Failed ❌

Follow these steps to fix your deployment:

## Step 1: Check Render Logs (CRITICAL)

1. Go to **Render Dashboard** → **trade-alerts** service
2. Click **"Logs"** tab
3. Scroll to the **bottom** (most recent errors)
4. **Copy the exact error message**

Common errors you might see:
- `GOOGLE_DRIVE_FOLDER_ID not set`
- `ModuleNotFoundError: No module named 'X'`
- `ImportError`
- `Authentication failed`
- `File not found`

## Step 2: Verify Environment Variables

Go to **Render Dashboard** → **trade-alerts** → **Environment** tab

### Required Variables (MUST be set):

✅ **Google Drive:**
- `GOOGLE_DRIVE_FOLDER_ID` - Your folder ID
- `GOOGLE_DRIVE_CREDENTIALS_JSON` - Full JSON content (paste entire JSON)
- `GOOGLE_DRIVE_REFRESH_TOKEN` - Your refresh token

✅ **LLM API Keys:**
- `OPENAI_API_KEY` - Your OpenAI key
- `GOOGLE_API_KEY` - Your Google/Gemini key
- `ANTHROPIC_API_KEY` - Your Anthropic/Claude key

✅ **Email (Optional but recommended):**
- `SENDER_EMAIL` - Your email
- `SENDER_PASSWORD` - Gmail app password
- `RECIPIENT_EMAIL` - Where to send recommendations
- `SMTP_SERVER` - smtp.gmail.com (already set)
- `SMTP_PORT` - 587 (already set)

✅ **Pushover (Optional):**
- `PUSHOVER_API_TOKEN` - Your Pushover token
- `PUSHOVER_USER_KEY` - Your Pushover user key

### Optional Variables (have defaults):
- `GEMINI_MODEL` - Default: gemini-pro
- `OPENAI_MODEL` - Default: gpt-4o-mini
- `ANTHROPIC_MODEL` - Default: claude-3-5-sonnet-20240229
- `ANALYSIS_TIMES` - Default: 07:00,09:00,12:00,16:00
- `CHECK_INTERVAL` - Default: 60

## Step 3: Common Fixes

### Fix 1: Missing Environment Variable
**If you see:** `GOOGLE_DRIVE_FOLDER_ID not set`

**Solution:**
1. Go to Render Dashboard → Environment
2. Add `GOOGLE_DRIVE_FOLDER_ID` with your folder ID
3. Click "Save Changes"
4. Service will auto-redeploy

### Fix 2: Missing Dependencies
**If you see:** `ModuleNotFoundError: No module named 'X'`

**Solution:**
1. Check `requirements.txt` includes the module
2. If missing, add it to `requirements.txt`
3. Commit and push to GitHub
4. Render will auto-redeploy

### Fix 3: Invalid JSON
**If you see:** JSON parsing errors

**Solution:**
1. For `GOOGLE_DRIVE_CREDENTIALS_JSON`:
   - Paste the ENTIRE JSON content
   - Make sure it's valid JSON (no extra quotes)
   - Use Render's multi-line support if needed

### Fix 4: Authentication Errors
**If you see:** Google Drive authentication failed

**Solution:**
1. Verify `GOOGLE_DRIVE_CREDENTIALS_JSON` is correct
2. Check `GOOGLE_DRIVE_REFRESH_TOKEN` is valid
3. Ensure credentials have proper permissions

## Step 4: Force Redeploy

After fixing environment variables:

1. Go to **Render Dashboard** → **trade-alerts**
2. Click **"Manual Deploy"** (top right)
3. Select **"Clear build cache & deploy"**
4. Wait for deployment to complete
5. Check logs for success

## Step 5: Verify Deployment

After redeploy:

1. **Check Status:**
   - Should show "Deployed" (green) instead of "Failed"

2. **Check Logs:**
   - Should see: "✅ Trade Alert System initialized"
   - No error messages

3. **Test (Optional):**
   - Go to Render Dashboard → trade-alerts → Shell
   - Run: `python run_analysis_now.py`
   - Check for errors

## Quick Diagnostic Commands

If you have access to Render Shell:

```bash
# Check environment variables
echo $GOOGLE_DRIVE_FOLDER_ID

# Test imports
python -c "from src.drive_reader import DriveReader; print('OK')"

# Check Python version
python --version

# List installed packages
pip list | grep -i pydrive
```

## Still Not Working?

If service still fails after these steps:

1. **Copy the exact error** from Render logs
2. **Check all environment variables** are set
3. **Verify requirements.txt** is complete
4. **Test locally first:**
   ```powershell
   python main.py
   ```
   If it fails locally, it will fail on Render

5. **Check Render Status:**
   - https://status.render.com
   - Ensure no outages

## Expected Success Logs

When working correctly, you should see:
```
✅ Authenticated with Google Drive
✅ Drive reader initialized
✅ ChatGPT enabled
✅ Gemini enabled
✅ Claude enabled
✅ Trade Alert System initialized
🚀 Starting Trade Alert System...
```

## Need More Help?

1. Check `TROUBLESHOOTING_RENDER.md` for detailed troubleshooting
2. Review Render documentation: https://render.com/docs
3. Check service logs for specific error messages







