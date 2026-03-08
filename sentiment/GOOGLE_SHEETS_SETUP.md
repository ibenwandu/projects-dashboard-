# Google Sheets Database Setup Guide

## Why Google Sheets?

- ✅ **Simple setup** - No database server needed
- ✅ **Easy to view/edit** - View data directly in Google Sheets
- ✅ **Shared access** - Both Hugging Face and Render can use the same sheet
- ✅ **Free** - No database hosting costs

## Step 1: Create Google Sheet

1. Go to https://sheets.google.com
2. Create a new blank spreadsheet
3. Name it: `Sentiment Monitor Data` (or any name you prefer)
4. **Copy the Spreadsheet ID** from the URL:
   - URL format: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
   - Copy the `SPREADSHEET_ID` part

## Step 2: Create Google Service Account

1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. Enable **Google Sheets API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Sheets API"
   - Click "Enable"
4. Enable **Google Drive API**:
   - Search for "Google Drive API"
   - Click "Enable"
5. Create Service Account:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "Service Account"
   - Name: `sentiment-monitor`
   - Click "Create and Continue"
   - Skip role assignment (optional)
   - Click "Done"
6. Create Key:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose "JSON"
   - Download the JSON file

## Step 3: Share Sheet with Service Account

1. Open your Google Sheet
2. Click "Share" button (top right)
3. Add the service account email (found in the JSON file as `client_email`)
   - Example: `sentiment-monitor@your-project.iam.gserviceaccount.com`
4. Give it **Editor** permissions
5. Click "Send"

## Step 4: Get Credentials JSON String

1. Open the downloaded JSON file
2. Copy the entire content
3. You'll need this for environment variables

## Step 5: Set Environment Variables

### For Hugging Face:

1. Go to Hugging Face Space → "Settings" → "Repository secrets"
2. Add:
   - **Key:** `GOOGLE_SHEETS_ID`
   - **Value:** Your spreadsheet ID (from Step 1)
3. Add:
   - **Key:** `GOOGLE_SHEETS_CREDENTIALS_JSON`
   - **Value:** The entire JSON content from Step 4 (paste as-is)

### For Render:

1. Go to Render Dashboard → `sentiment-forex-monitor` → "Environment"
2. Add:
   - **Key:** `GOOGLE_SHEETS_ID`
   - **Value:** Your spreadsheet ID
3. Add:
   - **Key:** `GOOGLE_SHEETS_CREDENTIALS_JSON`
   - **Value:** The entire JSON content (paste as-is)
   - **Note:** For multi-line JSON, Render supports it, but you might need to escape it properly

## Step 6: Update Code to Use Google Sheets

The code has been updated to use Google Sheets instead of PostgreSQL. You just need to:

1. Install dependencies: `pip install gspread google-auth`
2. Set environment variables (Step 5)
3. The code will automatically use Google Sheets if `GOOGLE_SHEETS_ID` is set

## Step 7: Deploy

1. **Hugging Face:**
   - Push updated code
   - Factory rebuild
   - Check logs for: `✅ Connected to Google Sheets`

2. **Render:**
   - Push updated code
   - Auto-deploys
   - Check logs for: `✅ Connected to Google Sheets`

## Testing

1. Add a trade via Hugging Face UI
2. Check Google Sheet - you should see it appear in the `watchlist` tab
3. Check Render worker logs - it should see the same trade

## Troubleshooting

### "GOOGLE_SHEETS_ID not set"
- Make sure environment variable is set correctly
- Check spelling (case-sensitive)

### "Failed to connect to Google Sheets"
- Verify service account email has access to the sheet
- Check that Google Sheets API is enabled
- Verify JSON credentials are correct

### "Worksheet not found"
- The code will create worksheets automatically
- Check that service account has Editor permissions

## Benefits

- **View data easily** - Just open Google Sheets
- **Manual edits** - You can edit data directly if needed
- **No database setup** - Works immediately
- **Shared access** - Both services see the same data






