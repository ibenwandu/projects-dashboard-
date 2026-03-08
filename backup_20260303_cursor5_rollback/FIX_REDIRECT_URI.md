# Fix redirect_uri_mismatch Error - Direct Solution

## The Problem
When you check "Use your own OAuth credentials" in OAuth2 Playground, you MUST add `https://developers.google.com/oauthplayground` as an authorized redirect URI in Google Cloud Console.

## The Fix (3 Steps)

### Step 1: Go to Google Cloud Console
1. Go to: https://console.cloud.google.com/
2. Select your project (the one with Client ID `650371239489-9d8d91l...`)

### Step 2: Add Redirect URI
1. Go to: **APIs & Services** → **Credentials**
2. Find your OAuth 2.0 Client ID (the one starting with `650371239489-9d8d91l...`)
3. Click on it to edit
4. Under **"Authorized redirect URIs"**, click **"+ ADD URI"**
5. Add exactly this: `https://developers.google.com/oauthplayground`
6. Click **"SAVE"**

### Step 3: Try OAuth2 Playground Again
1. Go back to: https://developers.google.com/oauthplayground/
2. Click ⚙️ (Settings)
3. Check "Use your own OAuth credentials"
4. Enter your Client ID and Secret
5. Click "Close"
6. Select `https://www.googleapis.com/auth/drive` scope
7. Click "Authorize APIs"
8. This should work now ✅

---

## Alternative: Don't Use Your Own Credentials

If you can't access Google Cloud Console, you can use OAuth2 Playground WITHOUT your own credentials:

1. Go to: https://developers.google.com/oauthplayground/
2. **DO NOT check "Use your own OAuth credentials"** (leave it unchecked)
3. Select `https://www.googleapis.com/auth/drive` scope
4. Click "Authorize APIs"
5. Sign in and allow
6. Click "Exchange authorization code for tokens"
7. Copy the `refresh_token`

**Note:** This method works but the token might expire faster. The first method (adding redirect URI) is better for long-term use.
