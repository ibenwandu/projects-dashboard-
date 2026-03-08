# Fix: Google Drive Refresh Token Expiring After 7 Days

## Why Is This Happening?

Your refresh token is expiring because your **OAuth app is in "Testing" mode** in Google Cloud Console. Google has a policy that refresh tokens expire after **7 days** for apps in Testing mode.

This is NOT a bug - it's a Google security policy to prevent abuse of OAuth tokens from unverified apps.

---

## ✅ The Solution: Publish Your App to Production

Publishing your app to Production mode will make refresh tokens **permanent** (they only expire if you revoke them or don't use them for 6 months).

### Step 1: Go to OAuth Consent Screen

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (the one with your OAuth credentials)
3. Navigate to: **APIs & Services** → **OAuth consent screen**

### Step 2: Check Current Status

Look at the top of the page - you'll see:
- **Publishing status**: "Testing" ❌ (this is the problem!)
- **User type**: Probably "External"

### Step 3: Publish to Production

1. Scroll down to the bottom of the OAuth consent screen page
2. Click the **"PUBLISH APP"** button
3. You'll see a warning about verification - **click "CONFIRM"**
4. The status will change to **"In production"** ✅

### Step 4: Generate a New Refresh Token

**Important:** You need to generate a NEW refresh token AFTER publishing to production. Tokens generated before publishing will still expire.

1. Go to [OAuth2 Playground](https://developers.google.com/oauthplayground/)
2. Click ⚙️ (Settings) → Check "Use your own OAuth credentials"
3. Enter your Client ID and Client Secret
4. Select scope: `https://www.googleapis.com/auth/drive`
5. Click "Authorize APIs" → Sign in → Allow
6. Click "Exchange authorization code for tokens"
7. **Copy the new `refresh_token`**

### Step 5: Update Render

1. Go to Render Dashboard → `trade-alerts` → Environment
2. Update `GOOGLE_DRIVE_REFRESH_TOKEN` with the new token
3. Save changes (will auto-redeploy)

---

## ⚠️ Important Notes

### Verification Requirements (If Needed)

If you see a warning about "Verification required" when publishing:
- **For personal use:** You can usually skip verification by clicking through the warnings
- **For production apps with many users:** Google may require app verification (privacy policy, terms of service, etc.)

### Token Longevity After Publishing

Once published to Production:
- ✅ Refresh tokens will **NOT expire** after 7 days
- ✅ They only expire if:
  - You manually revoke them in Google Account settings
  - They're not used for **6 months**
  - You change your OAuth credentials (Client ID/Secret)

### Scopes Used

Your app uses: `https://www.googleapis.com/auth/drive`

This is a **sensitive scope** but usually doesn't require verification for personal use apps. If Google asks for verification, you can:
1. Accept the risks and publish anyway (for personal use)
2. Complete the verification process (for production apps)

---

## Quick Checklist

- [ ] Open Google Cloud Console
- [ ] Go to OAuth consent screen
- [ ] Check status is "Testing"
- [ ] Click "PUBLISH APP"
- [ ] Generate NEW refresh token (after publishing)
- [ ] Update `GOOGLE_DRIVE_REFRESH_TOKEN` in Render
- [ ] Verify token works in logs

---

## Why This Happens

Google limits refresh tokens for unverified apps to prevent:
- Malicious apps from getting permanent access
- Token abuse from unauthorized apps
- Security risks from untested apps

Once your app is in Production, Google trusts it more and allows permanent refresh tokens.

---

## Need Help?

If you run into issues:
1. Make sure you're using the correct Google Cloud project
2. Check that your OAuth consent screen is configured properly
3. Verify your Client ID and Secret are correct
4. Try generating a new token after publishing

The key is: **Publish first, then generate a new token!**
