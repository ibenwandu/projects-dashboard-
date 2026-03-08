# How to Manually Rebuild Hugging Face Space

## Method 1: Via Settings (Recommended)

1. Go to your **Hugging Face Space** page
2. Click on **"Settings"** tab (in the top navigation)
3. Scroll down to **"Rebuild Space"** section
4. Click **"Rebuild Space"** button
5. Wait for the rebuild to complete (usually 2-5 minutes)

## Method 2: Via Files Tab

1. Go to your **Hugging Face Space** page
2. Click on **"Files"** tab
3. Click the **"..."** (three dots) menu in the top right
4. Select **"Rebuild Space"** from the dropdown
5. Confirm the rebuild

## Method 3: Push a New Commit (Automatic Rebuild)

If you have the Space connected to Git:

1. Make a small change to any file (e.g., add a comment)
2. Commit and push to the repository
3. Hugging Face will automatically rebuild

**Quick way:**
```bash
git commit --allow-empty -m "Trigger rebuild"
git push
```

## Method 4: Via API (Advanced)

You can also trigger a rebuild via Hugging Face API, but the Settings method is easier.

## What Happens During Rebuild

1. **Builds the container** with your latest code
2. **Installs dependencies** from `requirements.txt`
3. **Sets environment variables** from Repository secrets
4. **Starts the application**
5. **Updates the live Space**

## After Rebuild

1. Check the **"Logs"** tab to see:
   - Build progress
   - Any errors
   - Application startup messages
   - Database connection status

2. Look for:
   - `✅ DATABASE_URL is set (PostgreSQL)` ← Good!
   - `✅ Using PostgreSQL database` ← Good!
   - Any connection errors

## Troubleshooting

### Rebuild Fails
- Check **"Logs"** tab for error messages
- Verify `requirements.txt` is correct
- Check environment variables are set correctly

### Rebuild Takes Too Long
- Normal rebuild time: 2-5 minutes
- If >10 minutes, check for errors in logs

### Changes Not Reflecting
- Make sure you saved changes before rebuilding
- Check if the file was actually updated
- Try clearing browser cache

## Quick Steps Summary

1. **Space page** → **Settings** tab
2. Scroll to **"Rebuild Space"**
3. Click **"Rebuild Space"** button
4. Wait 2-5 minutes
5. Check **"Logs"** tab for status






