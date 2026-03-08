# Quick Fix: Get Google Drive Refresh Token (OAuth2 Playground)

## Why OAuth2 Playground?
- ✅ No redirect URI configuration needed
- ✅ Works immediately without Google Cloud Console changes
- ✅ Simple web interface - no scripts needed

---

## Step-by-Step Instructions

### Step 1: Get Your Client ID and Secret from Render

1. Go to **Render Dashboard** → `trade-alerts` service → **Environment**
2. Find `GOOGLE_DRIVE_CREDENTIALS_JSON`
3. Copy the entire JSON value
4. Parse it to get Client ID and Secret:

**Option A: Use Python (Quick)**
```python
import json

# Paste your GOOGLE_DRIVE_CREDENTIALS_JSON here:
creds_json = '{"installed":{"client_id":"650371239489-9d8d91l...","client_secret":"GOCSPX-9Fl...",...}}'

creds = json.loads(creds_json)
client_id = creds['installed']['client_id']
client_secret = creds['installed']['client_secret']

print(f"Client ID: {client_id}")
print(f"Client Secret: {client_secret}")
```

**Option B: From Logs (You already have these)**
- Client ID: `650371239489-9d8d91l...` (from your error logs)
- Client Secret: `GOCSPX-9Fl...` (from your error logs)

---

### Step 2: Use OAuth2 Playground

1. **Open OAuth2 Playground:**
   - Go to: https://developers.google.com/oauthplayground/

2. **Configure Settings:**
   - Click the **⚙️ (Settings)** icon in the top right corner
   - Check the box: **"Use your own OAuth credentials"**
   - Enter:
     - **OAuth Client ID**: `650371239489-9d8d91l...` (your Client ID)
     - **OAuth Client secret**: `GOCSPX-9Fl...` (your Client Secret)
   - Click **"Close"**

3. **Select API Scope:**
   - In the left panel, scroll down to find **"Drive API v3"**
   - Expand it and check: **`https://www.googleapis.com/auth/drive`**
   - (You can also type it directly in the box at the top)

4. **Authorize:**
   - Click the blue **"Authorize APIs"** button
   - Sign in with your Google account (`ibenwandu@gmail.com`)
   - Click **"Allow"** to grant permissions
   - You'll see a success message

5. **Get Refresh Token:**
   - Click the **"Exchange authorization code for tokens"** button
   - You'll see a JSON response with tokens
   - **Copy the `refresh_token` value** (it's a long string starting with `1//...`)

---

### Step 3: Update Render

1. Go to **Render Dashboard** → `trade-alerts` service → **Environment**
2. Find `GOOGLE_DRIVE_REFRESH_TOKEN`
3. **Replace** the entire value with the new refresh token from Step 2
4. Click **"Save Changes"**
5. Wait for automatic redeploy (usually 1-2 minutes)

---

### Step 4: Verify It Works

After redeploy, check the logs for:
```
✅ Drive reader initialized for folder: ...
```

If you see this, the token is working! ✅

---

## Troubleshooting

### If OAuth2 Playground shows an error:
- Make sure you clicked "Use your own OAuth credentials" in Settings
- Verify Client ID and Secret are correct (no extra spaces)
- Try clearing browser cache and trying again

### If token still doesn't work:
- Make sure you copied the **entire** refresh_token (it's very long, ~100+ characters)
- Check for any extra spaces or line breaks when pasting
- Try generating a new token again

---

## Why This Works

OAuth2 Playground uses its own redirect URI (`https://developers.google.com/oauthplayground/`) which is already authorized by Google, so you don't need to configure anything in Google Cloud Console. This bypasses the `redirect_uri_mismatch` error completely.
