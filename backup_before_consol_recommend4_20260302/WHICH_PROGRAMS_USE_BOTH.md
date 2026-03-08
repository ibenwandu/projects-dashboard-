# Programs That Use Both Refresh Token AND Credentials JSON

Based on the codebase analysis, these programs use **both** `GOOGLE_DRIVE_REFRESH_TOKEN` and `GOOGLE_DRIVE_CREDENTIALS_JSON`:

## ✅ Programs Using Both:

1. **`Forex`** (personal/Forex/)
   - File: `src/drive_sync.py`
   - Uses: `GOOGLE_DRIVE_REFRESH_TOKEN` + `GOOGLE_DRIVE_CREDENTIALS_JSON`
   - Fallback: `credentials.json` file if JSON env var not set
   - **Render service name**: Likely `forex-trends-tracker` or similar

2. **`Assets`** (personal/Assets/)
   - File: `src/drive_sync.py`
   - Uses: `GOOGLE_DRIVE_REFRESH_TOKEN` + `GOOGLE_DRIVE_CREDENTIALS_JSON`
   - Fallback: `credentials.json` file if JSON env var not set
   - **Render service name**: Likely `assets-tracker` or similar

3. **`Trade-Alerts`** (personal/Trade-Alerts/)
   - File: `src/drive_reader.py`
   - Uses: `GOOGLE_DRIVE_REFRESH_TOKEN` + `GOOGLE_DRIVE_CREDENTIALS_JSON`
   - **No fallback** - requires both to be set

---

## How to Get Credentials from Render:

### For Forex or Assets Services:

1. Go to https://dashboard.render.com
2. Look for services named:
   - `forex-trends-tracker` (or similar Forex-related name)
   - `assets-tracker` (or similar Assets-related name)
3. Click on the service
4. Go to **Environment** tab
5. Find `GOOGLE_DRIVE_CREDENTIALS_JSON`
6. Click the eye icon (👁️) to reveal it
7. Copy the entire JSON string
8. Paste it into `personal/Trade-Alerts/.env` as `GOOGLE_DRIVE_CREDENTIALS_JSON=...`

---

## Note:

Both `Forex` and `Assets` programs have the **same authentication pattern** as `Trade-Alerts`:
- They require a refresh token
- They use credentials JSON (from env var or file)
- They create OAuth2Credentials with both

So the credentials JSON from either of these programs should work with your refresh token in Trade-Alerts!

