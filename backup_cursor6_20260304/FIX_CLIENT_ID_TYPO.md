# Fix Client ID Typo

## The Problem
Your actual Client ID is:
```
GOOGLE_CLIENT_ID_REMOVED
```
(ends with `7fl7` - lowercase 'l' then '7')

But your environment variable has:
```
650371239489-n5slvo6u2t802ugfvdmf5tabmrpq7f17.apps.googleusercontent.com
```
(ends with `7f17` - 'f' then '17')

This typo is causing the "invalid_client" error!

## The Fix

### Step 1: Get the Correct JSON
Your downloaded file has the correct Client ID. Use this exact JSON format:

```json
{"installed":{"client_id":"GOOGLE_CLIENT_ID_REMOVED","client_secret":"GOOGLE_CLIENT_SECRET_REMOVED","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","redirect_uris":["https://developers.google.com/oauthplayground"]}}
```

**OR** if you prefer the `web` format (which the code now supports):

```json
{"web":{"client_id":"GOOGLE_CLIENT_ID_REMOVED","client_secret":"GOOGLE_CLIENT_SECRET_REMOVED","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","redirect_uris":["https://developers.google.com/oauthplayground"]}}
```

### Step 2: Generate New Refresh Token
Since you need a refresh token that matches this Client ID:

1. Go to: https://developers.google.com/oauthplayground/
2. Click ⚙️ (Settings)
3. Check "Use your own OAuth credentials"
4. Enter:
   - **Client ID**: `GOOGLE_CLIENT_ID_REMOVED`
   - **Client Secret**: `GOOGLE_CLIENT_SECRET_REMOVED`
5. Click "Close"
6. In the left panel, find and select: `https://www.googleapis.com/auth/drive`
7. Click "Authorize APIs"
8. Sign in with `ibenwandu@gmail.com` and allow
9. Click "Exchange authorization code for tokens"
10. Copy the `refresh_token` value (it's a long string starting with `1//...`)

### Step 3: Update Render Environment Variables
1. Go to Render Dashboard → `trade-alerts` → **Environment**
2. Find `GOOGLE_DRIVE_CREDENTIALS_JSON`
3. **Replace** the entire value with the JSON from Step 1 (make sure it has `7fl7` not `7f17`)
4. Find `GOOGLE_DRIVE_REFRESH_TOKEN`
5. **Replace** the entire value with the new refresh token from Step 2
6. Click **"Save Changes"**
7. Wait for automatic redeploy (usually 1-2 minutes)

### Step 4: Verify
After redeploy, check the logs. You should see:
```
✅ Drive reader initialized for folder: ...
```

Instead of:
```
❌ Failed to initialize Drive reader: invalid_client
```

---

## Quick Copy-Paste JSON

Use this exact JSON (with `installed` format):

```json
{"installed":{"client_id":"GOOGLE_CLIENT_ID_REMOVED","client_secret":"GOOGLE_CLIENT_SECRET_REMOVED","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","redirect_uris":["https://developers.google.com/oauthplayground"]}}
```

**Important**: Make sure the Client ID ends with `7fl7` (lowercase 'l' then '7'), NOT `7f17`!
