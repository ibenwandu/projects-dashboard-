# Step-by-Step: Publish OAuth App to Production

## Overview
This guide will walk you through publishing your Google OAuth app from "Testing" to "Production" status. This will fix the 7-day refresh token expiration issue.

---

## Step 1: Go to OAuth Consent Screen

1. **Open Google Cloud Console**
   - Go to: https://console.cloud.google.com/
   - Make sure you're signed in with the correct Google account

2. **Select Your Project**
   - Click the project dropdown at the top
   - Select the project that contains your OAuth credentials
   - (The one with Client ID `650371239489-9d8d91l...`)

3. **Navigate to OAuth Consent Screen**
   - In the left sidebar, click **"APIs & Services"**
   - Click **"OAuth consent screen"**
   - You should see the page with "Publishing status: Testing"

---

## Step 2: Review Your App Information

Before publishing, verify these settings are correct:

### Check These Sections:

1. **App Information**
   - App name: Should be something like "Trade Alerts" or your app name
   - User support email: Your email
   - App logo: Optional

2. **App Domain** (if shown)
   - Homepage link: Optional
   - Privacy policy link: Optional (can skip for personal use)
   - Terms of service link: Optional (can skip for personal use)

3. **Authorized Domains**
   - Usually empty for personal apps (that's fine)

4. **Developer Contact Information**
   - Your email address

---

## Step 3: Publish the App

1. **Scroll Down to "Publishing Status" Section**
   - You should see: **"Publishing status: Testing"**
   - Below it, there's a blue button: **"PUBLISH APP"**

2. **Click "PUBLISH APP"**
   - A confirmation dialog will appear
   - It may show warnings about:
     - "Your app isn't verified"
     - "Users may see an unverified app warning"
     - This is **NORMAL** for personal use apps

3. **Confirm Publishing**
   - Click **"CONFIRM"** or **"PUBLISH"** in the dialog
   - The status should change to **"In production"** ✅

---

## Step 4: Handle Verification Warnings (If Shown)

If Google shows warnings about verification:

### For Personal Use Apps:
- **You can skip verification** for personal use
- Click through any warnings
- Accept that users (just you) will see an "unverified app" warning
- This is fine - you're the only one using it

### What the Warning Means:
- Google will show a warning screen when you authorize
- It says "Google hasn't verified this app"
- You can click "Advanced" → "Go to [Your App] (unsafe)"
- This is acceptable for personal use

---

## Step 5: Verify Status Changed

After publishing:

1. **Check the Status**
   - The "Publishing status" should now say: **"In production"** ✅
   - The "PUBLISH APP" button should be gone or grayed out

2. **Note the Changes**
   - "OAuth user cap" section may change
   - Test users section may still be there (that's fine)

---

## Step 6: Generate a NEW Refresh Token

**IMPORTANT:** You MUST generate a NEW refresh token AFTER publishing. Tokens generated before publishing still have the 7-day expiry.

### Option A: Using OAuth2 Playground (Easiest)

1. **Go to OAuth2 Playground**
   - Visit: https://developers.google.com/oauthplayground/

2. **Configure Settings**
   - Click the ⚙️ (gear icon) in the top right
   - Check **"Use your own OAuth credentials"**
   - Enter your **Client ID** (from `GOOGLE_DRIVE_CREDENTIALS_JSON`)
   - Enter your **Client Secret** (from `GOOGLE_DRIVE_CREDENTIALS_JSON`)

3. **Authorize**
   - In the left panel, find **"Drive API v3"**
   - Select scope: `https://www.googleapis.com/auth/drive`
   - Click **"Authorize APIs"**
   - Sign in with your Google account
   - You may see the "unverified app" warning - click **"Advanced"** → **"Go to [Your App] (unsafe)"**
   - Click **"Allow"**

4. **Get Refresh Token**
   - Click **"Exchange authorization code for tokens"**
   - In the response, find the **`refresh_token`** field
   - **Copy the entire refresh token** (it's a long string starting with `1//...`)

### Option B: Using Python Script

1. **Run the script locally:**
   ```bash
   cd personal/Trade-Alerts
   python regenerate_drive_token.py
   ```

2. **Follow the prompts:**
   - Browser will open for authorization
   - Sign in and allow access
   - Copy the refresh token displayed

---

## Step 7: Update Render Environment Variable

1. **Go to Render Dashboard**
   - Go to: https://dashboard.render.com/
   - Navigate to your `trade-alerts` service

2. **Update Environment Variable**
   - Click **"Environment"** tab
   - Find **`GOOGLE_DRIVE_REFRESH_TOKEN`**
   - Click to edit
   - **Replace** the entire value with the NEW refresh token from Step 6
   - Click **"Save Changes"**

3. **Wait for Redeploy**
   - Render will automatically redeploy (usually 1-2 minutes)
   - Watch the logs to confirm it works

---

## Step 8: Verify It Works

After redeploy, check the logs:

1. **Go to Render Dashboard** → `trade-alerts` → **"Logs"**

2. **Look for:**
   ```
   ✅ OAuth2 authenticated using refresh token
   ✅ Drive reader initialized for folder: ...
   ```

3. **If you see errors:**
   - Make sure you copied the ENTIRE refresh token (it's very long)
   - Check for any extra spaces or line breaks
   - Try generating a new token again

---

## Troubleshooting

### "Unverified App" Warning
- **This is normal** for personal use apps
- Click "Advanced" → "Go to [Your App] (unsafe)"
- This won't affect functionality

### Token Still Expires
- Make sure you generated the token **AFTER** publishing
- Old tokens from Testing mode still expire
- Generate a completely new token

### Can't Find "PUBLISH APP" Button
- Make sure you're on the **OAuth consent screen** page
- Check that status shows "Testing"
- Try refreshing the page

### Verification Required Warning
- For personal use, you can usually skip this
- Click through the warnings
- Accept the risks (you're the only user)

---

## What Changed?

### Before (Testing Mode):
- ❌ Refresh tokens expire after 7 days
- ❌ Only test users can authorize
- ❌ Limited to 100 users total

### After (Production Mode):
- ✅ Refresh tokens don't expire (unless unused 6+ months)
- ✅ Any user can authorize (but app isn't publicly listed)
- ✅ No user limit
- ✅ Permanent tokens for your use case

---

## Summary Checklist

- [ ] Opened Google Cloud Console
- [ ] Navigated to OAuth consent screen
- [ ] Clicked "PUBLISH APP"
- [ ] Confirmed publishing
- [ ] Verified status changed to "In production"
- [ ] Generated NEW refresh token (after publishing)
- [ ] Updated `GOOGLE_DRIVE_REFRESH_TOKEN` in Render
- [ ] Verified it works in logs

---

## Next Steps

Once published and new token is set:
- ✅ Your refresh token should NOT expire after 7 days
- ✅ You won't need to regenerate tokens frequently
- ✅ The app will work reliably long-term

**Note:** The app is still private - only you can authorize it. Publishing just removes the 7-day token expiration limit.
