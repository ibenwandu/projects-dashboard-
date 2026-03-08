# Verify OAuth Client ID - Step by Step

## The Problem
You're getting "Error 401: invalid_client - The OAuth client was not found." This means the Client ID in your `GOOGLE_DRIVE_CREDENTIALS_JSON` doesn't exist in Google Cloud Console.

## Step-by-Step Verification

### Step 1: Go to Google Cloud Console
1. Go to: https://console.cloud.google.com/
2. **Make sure you're in the correct project**: Look at the top - it should say **"Finance"** (project ID: `finance-463213`)
3. If it shows a different project, click the project name and select **"Finance"**

### Step 2: Check Your OAuth Clients
1. Go to: **APIs & Services** → **Credentials**
2. Look for **"OAuth 2.0 Client IDs"** section
3. You should see a list of OAuth clients

### Step 3: Find the Correct Client ID
Look for a client with Client ID ending in:
- `n5slvo6u2t802ugfvdmf5tabmrpq7fl7` (from your downloaded file)
- OR `n5slvo6u2t802ugfvdmf5tabmrpq7f17` (from your environment variable)

**Important**: Check if there's a typo difference between:
- Your downloaded file: `...7fl7` (ends with lowercase 'l' then '7')
- Your environment variable: `...7f17` (ends with 'f' then '17')

### Step 4: Verify Client Type
1. Click on the OAuth client to open it
2. Check the **"Application type"**:
   - Should be **"Web application"** (not "Desktop app")
   - If it's "Desktop app", that's the problem - you need a "Web application" client

### Step 5: Check Authorized Redirect URIs
Make sure the client has this redirect URI:
- `https://developers.google.com/oauthplayground`

### Step 6: If Client ID Doesn't Exist
If you can't find the Client ID:
1. **Create a new OAuth 2.0 Client ID**:
   - Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
   - Application type: **"Web application"**
   - Name: "Trade Alerts Drive Access"
   - Authorized redirect URIs: Add `https://developers.google.com/oauthplayground`
   - Click **"CREATE"**
2. **Download the JSON** (click the download icon)
3. **Update your environment variables** with the new Client ID and Secret

### Step 7: Generate New Refresh Token
After verifying/fixing the Client ID:
1. Go to: https://developers.google.com/oauthplayground/
2. Click ⚙️ (Settings)
3. Check "Use your own OAuth credentials"
4. Enter the **correct** Client ID and Secret
5. Click "Close"
6. Select `https://www.googleapis.com/auth/drive` scope
7. Click "Authorize APIs"
8. Sign in and allow
9. Click "Exchange authorization code for tokens"
10. Copy the `refresh_token`

### Step 8: Update Render Environment Variables
1. Go to Render Dashboard → `trade-alerts` → **Environment**
2. Update `GOOGLE_DRIVE_CREDENTIALS_JSON` with the **exact** JSON from the downloaded file (make sure Client ID matches exactly)
3. Update `GOOGLE_DRIVE_REFRESH_TOKEN` with the new refresh token
4. Save and wait for redeploy

---

## Common Issues

### Issue 1: Client ID Typo
- Check for typos: `7fl7` vs `7f17` vs `7f1l`
- Copy the Client ID directly from Google Cloud Console (don't type it manually)

### Issue 2: Wrong Project
- Make sure you're in the **"Finance"** project
- The Client ID must be from the same project

### Issue 3: Client Was Deleted
- If the client was deleted, create a new one
- Generate a new refresh token with the new client

### Issue 4: Desktop App vs Web Application
- **Web application** clients work better for server-side use
- If you have a "Desktop app" client, create a new "Web application" client instead

---

## Quick Check: What's Your Current Client ID?

From your environment variable screenshot, your Client ID should be:
```
650371239489-n5slvo6u2t802ugfvdmf5tabmrpq7f17.apps.googleusercontent.com
```

**Verify this exact Client ID exists in Google Cloud Console!**
