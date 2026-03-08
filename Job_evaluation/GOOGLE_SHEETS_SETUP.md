# Google Sheets Setup Guide

## 🎯 Overview
This guide will help you set up Google Sheets integration for the Job Evaluation System.

## 📋 Prerequisites
- Google account with access to Google Sheets
- Google Cloud Console access (for API credentials)

## 🔧 Step-by-Step Setup

### Step 1: Create a Google Sheet

1. **Go to Google Sheets**: https://sheets.google.com
2. **Create a new spreadsheet** with a descriptive name like "Job Evaluation System"
3. **Copy the Sheet ID** from the URL:
   - URL format: `https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit`
   - The Sheet ID is the long string between `/d/` and `/edit`

### Step 2: Update Environment Configuration

1. **Open the `.env` file** in your project directory
2. **Replace the placeholder** with your actual Google Sheets ID:
   ```
   GOOGLE_SHEETS_ID=your_actual_sheet_id_here
   ```

### Step 3: Set Up Google Sheets Headers

The system will automatically create these columns in your sheet:

| Column | Description |
|--------|-------------|
| Score | AI match score (1-100) |
| Job Title | Extracted job title |
| Company | Company name |
| Location | Job location |
| Application Link | Direct application URL |
| **Sender** | **Email sender info** |
| Match Reasoning | AI evaluation feedback |
| Apply | Checkbox for resume generation |
| Resume Status | Generation status |
| Generated Date | When resume was created |
| Resume Link | Google Drive link to resume |
| Email Date | When job alert was received |
| Source Type | Job board source |

### Step 4: Configure API Credentials

1. **Ensure credentials exist** in `config/credentials/`:
   - `gmail_credentials.json` (should already exist)
   - `drive_credentials.json` (should already exist)

2. **The system uses the same credentials** for Gmail, Drive, and Sheets APIs

### Step 5: Test the Configuration

1. **Run the system** to test Google Sheets integration:
   ```bash
   python main.py --run-gmail
   ```

2. **Check for success messages** in the logs:
   - "Google Sheets API authentication successful"
   - "Updated sheet headers with sender column"
   - "Added X jobs to Google Sheets"

## 🔍 Troubleshooting

### Common Issues:

1. **"Google Sheets authentication failed"**
   - Solution: Run the system once to authenticate
   - The system will open a browser window for OAuth

2. **"No such file or directory: sheets_token.json"**
   - Solution: This is normal on first run
   - The token will be created automatically

3. **"Failed to access Google Sheets"**
   - Check: Sheet ID is correct in `.env`
   - Check: Sheet is shared with your Google account

### Verification Steps:

1. **Check your Google Sheet** after running the system
2. **Look for the headers** being created automatically
3. **Verify job data** is being populated (if any high-scoring jobs found)

## 📊 Expected Results

After successful setup, you should see:

- ✅ **Headers created** in your Google Sheet
- ✅ **Job data populated** (for jobs scoring 85+)
- ✅ **Sender column** with email source information
- ✅ **Apply checkboxes** for manual job selection

## 🚀 Next Steps

Once Google Sheets is working:

1. **Mark jobs for application** by checking the "Apply" column
2. **Run resume generation**: `python main.py --run-resume`
3. **Monitor the sheet** for status updates and resume links

## 📞 Support

If you encounter issues:
1. Check the logs in `logs/system.log`
2. Verify your Google Sheets ID is correct
3. Ensure your Google account has access to the sheet 