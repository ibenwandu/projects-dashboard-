# Fix Google Drive Token Expiration

## Problem
The Google Drive refresh token has expired or been revoked, causing this error:
```
Failed to refresh token: Access token refresh failed: invalid_grant: Token has been expired or revoked.
```

## Solution: Regenerate Refresh Token

You need to generate a new refresh token. Here's how:

### Option 1: Using Python Script (Recommended)

1. **Create a script to generate new token:**

```python
# regenerate_drive_token.py
import os
import json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# Load credentials from environment or file
credentials_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON', '')
if not credentials_json:
    # Try to load from file
    if os.path.exists('credentials.json'):
        with open('credentials.json', 'r') as f:
            creds_data = json.load(f)
    else:
        print("❌ GOOGLE_DRIVE_CREDENTIALS_JSON not set and credentials.json not found")
        exit(1)
else:
    creds_data = json.loads(credentials_json)

# Write credentials to file (required by PyDrive2)
with open('client_secrets.json', 'w') as f:
    json.dump(creds_data, f)

# Authenticate
gauth = GoogleAuth()
gauth.LoadCredentialsFile("mycreds.txt")

if gauth.credentials is None:
    # Authenticate user if no credentials found
    gauth.LocalWebserverAuth()  # Opens browser for authentication
elif gauth.access_token_expired:
    # Refresh token if expired
    gauth.Refresh()
else:
    # Initialize the saved creds
    gauth.Authorize()

# Save credentials
gauth.SaveCredentialsFile("mycreds.txt")

# Get the refresh token
refresh_token = gauth.credentials.refresh_token
print(f"\n✅ New Refresh Token:")
print(f"{refresh_token}")
print(f"\n📋 Copy this token and update GOOGLE_DRIVE_REFRESH_TOKEN in Render Dashboard → Environment")
```

2. **Run the script locally:**
```bash
cd personal/Trade-Alerts
python regenerate_drive_token.py
```

3. **Update Render environment variable:**
   - Go to Render Dashboard → `trade-alerts` service → Environment
   - Update `GOOGLE_DRIVE_REFRESH_TOKEN` with the new token from step 2
   - Save and redeploy

### Option 2: Using Google OAuth2 Playground (Easier)

1. **Go to Google OAuth2 Playground:**
   - Visit: https://developers.google.com/oauthplayground/

2. **Configure OAuth2:**
   - Click the gear icon (⚙️) in top right
   - Check "Use your own OAuth credentials"
   - Enter your `Client ID` and `Client Secret` (from `GOOGLE_DRIVE_CREDENTIALS_JSON`)

3. **Authorize:**
   - In left panel, find "Drive API v3"
   - Select scope: `https://www.googleapis.com/auth/drive`
   - Click "Authorize APIs"
   - Sign in with your Google account
   - Click "Allow" to grant permissions

4. **Get Refresh Token:**
   - Click "Exchange authorization code for tokens"
   - Copy the `refresh_token` value from the response

5. **Update Render:**
   - Go to Render Dashboard → `trade-alerts` → Environment
   - Update `GOOGLE_DRIVE_REFRESH_TOKEN` with the new token
   - Save and redeploy

### Option 3: Quick Fix Script (Run on Render Shell)

If you have access to Render Shell, you can test authentication:

```bash
cd /opt/render/project
python << 'PYTHON_SCRIPT'
import os
import json
from pydrive2.auth import GoogleAuth

# Check environment variables
refresh_token = os.getenv('GOOGLE_DRIVE_REFRESH_TOKEN', '')
credentials_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON', '')

print(f"Refresh Token Length: {len(refresh_token) if refresh_token else 0}")
print(f"Credentials JSON Length: {len(credentials_json) if credentials_json else 0}")

if credentials_json:
    # Write credentials file
    creds_data = json.loads(credentials_json)
    with open('client_secrets.json', 'w') as f:
        json.dump(creds_data, f)
    
    # Try to authenticate
    gauth = GoogleAuth()
    try:
        # Try to load existing credentials
        gauth.LoadCredentialsFile("mycreds.txt")
        if gauth.credentials is None:
            print("❌ No saved credentials found")
            print("   → Need to regenerate refresh token using Option 1 or 2")
        elif gauth.access_token_expired:
            print("⏳ Access token expired, attempting refresh...")
            gauth.Refresh()
            print("✅ Token refreshed successfully!")
        else:
            print("✅ Credentials are valid")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   → Refresh token is invalid or expired")
        print("   → Need to regenerate using Option 1 or 2")
else:
    print("❌ GOOGLE_DRIVE_CREDENTIALS_JSON not set")
PYTHON_SCRIPT
```

---

## ⚠️ IMPORTANT: If You See "redirect_uri_mismatch" Error

If you're seeing `Error 400: redirect_uri_mismatch` when running `regenerate_drive_token.py`, this means:
- The script is trying to use `http://localhost:8080/` as redirect URI
- But this URI is not authorized in your Google Cloud Console

**Solution: Use OAuth2 Playground instead** (it doesn't have redirect URI issues) - see "Step-by-Step: Using OAuth2 Playground" below.

**OR** add the redirect URI to Google Cloud Console:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to "APIs & Services" → "Credentials"
4. Click on your OAuth 2.0 Client ID
5. Under "Authorized redirect URIs", add: `http://localhost:8080/`
6. Save and try the script again

---

## Step-by-Step: Using OAuth2 Playground (Easiest - Recommended)

### Step 1: Get Your Client ID and Secret

1. Go to Render Dashboard → `trade-alerts` → Environment
2. Copy the value of `GOOGLE_DRIVE_CREDENTIALS_JSON`
3. Parse it to get `client_id` and `client_secret`:
   ```python
   import json
   creds = json.loads('YOUR_CREDENTIALS_JSON_VALUE')
   print(f"Client ID: {creds['installed']['client_id']}")
   print(f"Client Secret: {creds['installed']['client_secret']}")
   ```

### Step 2: Use OAuth2 Playground

1. Go to: https://developers.google.com/oauthplayground/
2. Click ⚙️ (Settings) in top right
3. Check "Use your own OAuth credentials"
4. Paste your `Client ID` and `Client Secret`
5. In left panel, find "Drive API v3"
6. Select: `https://www.googleapis.com/auth/drive`
7. Click "Authorize APIs"
8. Sign in and click "Allow"
9. Click "Exchange authorization code for tokens"
10. Copy the `refresh_token` from the response

### Step 3: Update Render

1. Go to Render Dashboard → `trade-alerts` → Environment
2. Find `GOOGLE_DRIVE_REFRESH_TOKEN`
3. Replace the value with the new refresh token from Step 2
4. Save changes
5. The service will automatically redeploy

---

## Verify Fix

After updating the token, check the logs:

```bash
# In Render Shell or logs
# Look for:
✅ Drive reader initialized for folder: ...
```

If you still see errors, the token might still be invalid. Try regenerating again.

---

## Prevention

Refresh tokens can expire if:
- User revokes access in Google Account settings
- Token hasn't been used for 6 months
- App credentials are changed

**Best Practice:** Set up monitoring to alert when Drive reader fails to initialize.
