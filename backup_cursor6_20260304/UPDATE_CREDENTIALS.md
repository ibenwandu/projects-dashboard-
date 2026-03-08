# How to Update Google Drive Credentials

## Step 1: Get Credentials from Working Program

### Option A: From Render Dashboard (if deployed)
1. Go to Render Dashboard
2. Navigate to a service where Google Drive works (e.g., `forex-trends-tracker`, `assets-tracker`)
3. Go to **Environment** tab
4. Find `GOOGLE_DRIVE_CREDENTIALS_JSON`
5. Click the eye icon to reveal the value
6. Copy the entire JSON string

### Option B: From Local .env File
1. Open the `.env` file from a working program (e.g., `personal/Forex/.env` or `personal/Assets/.env`)
2. Find the `GOOGLE_DRIVE_CREDENTIALS_JSON` line
3. Copy the entire value (the JSON string)

## Step 2: Update Trade-Alerts .env File

1. Open `personal/Trade-Alerts/.env`
2. Find the line: `GOOGLE_DRIVE_CREDENTIALS_JSON=...`
3. Replace the value with the one from the working program
4. Make sure the JSON is on a single line (no line breaks)
5. Save the file

## Step 3: Test

Run the test script:
```bash
python test_drive_auth.py
```

You should see:
- ✅ DriveReader initialized successfully!
- ✅ Successfully listed X files

## Step 4: Run Historical Backfill

Once authentication works:
```bash
python historical_backfill.py
```

---

## Important Notes

- The refresh token (`GOOGLE_DRIVE_REFRESH_TOKEN`) stays the same
- Only update `GOOGLE_DRIVE_CREDENTIALS_JSON`
- Both must be from the same OAuth app (same client_id/client_secret)
- The JSON should be a single line (no line breaks)





