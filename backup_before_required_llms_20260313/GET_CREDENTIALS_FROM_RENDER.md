# Getting Google Drive Credentials from Render

## Step-by-Step Instructions

### Step 1: Access Render Dashboard
1. Go to https://dashboard.render.com
2. Log in to your account

### Step 2: Find a Working Service
Look for one of these services that uses Google Drive:
- `forex-trends-tracker` (or similar Forex-related service)
- `assets-tracker` (or similar Assets-related service)
- Any other service that successfully uses Google Drive

### Step 3: Get the Credentials JSON
1. Click on the service name to open it
2. Go to the **Environment** tab (in the left sidebar)
3. Scroll down to find `GOOGLE_DRIVE_CREDENTIALS_JSON`
4. Click the **eye icon** (👁️) next to it to reveal the value
5. **Copy the entire JSON string** (it's all on one line)

### Step 4: Update Your .env File
1. Open `personal/Trade-Alerts/.env` in a text editor
2. Find the line: `GOOGLE_DRIVE_CREDENTIALS_JSON=...`
3. Replace everything after the `=` with the value you copied from Render
4. Make sure:
   - The JSON is on a single line (no line breaks)
   - There are no extra quotes around it
   - The line looks like: `GOOGLE_DRIVE_CREDENTIALS_JSON={"installed":{"client_id":"...`
5. Save the file

### Step 5: Test
Run the test script:
```bash
cd personal/Trade-Alerts
python test_drive_auth.py
```

You should see:
- ✅ Authenticated with Google Drive
- ✅ Successfully listed X files

### Step 6: Run Historical Backfill
Once authentication works:
```bash
python historical_backfill.py
```

---

## Important Notes

- Keep the same `GOOGLE_DRIVE_REFRESH_TOKEN` - don't change it
- Only update `GOOGLE_DRIVE_CREDENTIALS_JSON`
- The JSON must be on a single line in the .env file
- Make sure there are no extra spaces or quotes

---

## Troubleshooting

If you still get an error after updating:
1. Verify the JSON is valid by running: `python verify_credentials.py`
2. Check that the client_id matches (it should start with the same numbers)
3. If it still fails, the refresh token might need to be regenerated (Option 2)

