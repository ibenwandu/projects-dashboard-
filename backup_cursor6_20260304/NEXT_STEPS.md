# Next Steps After Running Analysis

## ✅ Current Status

From your latest analysis run:
- ✅ Google Drive connection working
- ✅ Files downloaded successfully (3 files)
- ✅ ChatGPT analysis completed
- ⚠️ Gemini and Claude models need fixing
- ⚠️ Email not configured

## Step 1: Fix Model Names (Just Fixed!)

I've updated the model names to use available models:
- **Gemini**: `gemini-pro` (standard model)
- **Claude**: `claude-3-5-sonnet-20240229` (correct date format)

You can test again:
```powershell
python run_analysis_now.py
```

## Step 2: Configure Email (Recommended)

To receive recommendations via email, add to your `.env` file:

```env
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-gmail-app-password
RECIPIENT_EMAIL=your-email@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

**To get Gmail App Password:**
1. Enable 2FA on your Gmail account
2. Go to: https://myaccount.google.com/apppasswords
3. Generate password for "Mail"
4. Use it as `SENDER_PASSWORD`

## Step 3: Test Full Workflow

After configuring email, run again:
```powershell
python run_analysis_now.py
```

This will:
1. ✅ Read data from Google Drive
2. ✅ Run LLM analysis (ChatGPT, Gemini, Claude)
3. ✅ Synthesize final recommendations (Gemini)
4. ✅ Send email with all recommendations
5. ✅ Extract entry/exit points
6. ✅ Start monitoring prices

## Step 4: Run Continuous Monitoring

To run the system continuously (24/7):
```powershell
python main.py
```

This will:
- Run analysis at scheduled times (7am, 9am, 12pm, 4pm UTC)
- Monitor entry points every 60 seconds
- Send Pushover alerts when entry points are hit

## Step 5: Deploy to Render (For 24/7 Operation)

### 5.1 Commit Your Changes
```powershell
git add .
git commit -m "Fix model names and update configuration"
```

### 5.2 Push to GitHub
```powershell
git push origin main
```

### 5.3 Deploy to Render
1. Go to https://dashboard.render.com
2. Click "New +" → "Blueprint"
3. Connect your GitHub repository
4. Render will detect `render.yaml` automatically
5. Add all environment variables from your `.env` file
6. Click "Create"

### 5.4 Environment Variables for Render

Add these in Render Dashboard → Environment:

**Required:**
- `GOOGLE_DRIVE_FOLDER_ID`
- `GOOGLE_DRIVE_CREDENTIALS_JSON` (full JSON content)
- `GOOGLE_DRIVE_REFRESH_TOKEN`
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `ANTHROPIC_API_KEY`
- `SENDER_EMAIL`
- `SENDER_PASSWORD`
- `RECIPIENT_EMAIL`
- `PUSHOVER_API_TOKEN`
- `PUSHOVER_USER_KEY`

**Optional (has defaults):**
- `GEMINI_MODEL=gemini-pro`
- `OPENAI_MODEL=gpt-4o-mini`
- `ANTHROPIC_MODEL=claude-3-5-sonnet-20240229`
- `ANALYSIS_TIMES=07:00,09:00,12:00,16:00`

## Step 6: Verify Deployment

After deployment:
1. Check Render logs for "✅ Trade Alert System initialized"
2. Wait for scheduled analysis time OR trigger manually:
   - Go to Render Dashboard → Your Service → Shell
   - Run: `python run_analysis_now.py`
3. Check your email for recommendations
4. Verify Pushover alerts work when entry points are hit

## Troubleshooting

### Models Not Working
- Check API keys are valid
- Verify model names are correct
- Check API credits/quotas

### Email Not Sending
- Verify Gmail app password is correct
- Check SMTP settings
- Check logs for email errors

### No Entry Points Extracted
- Ensure Gemini synthesis completed
- Check recommendation format
- Review logs for parsing errors

### Google Drive Errors
- Verify folder ID is correct
- Check credentials are valid
- Ensure folder is accessible

## What Happens Next?

Once everything is configured:
1. **Scheduled Analysis**: Runs at 7am, 9am, 12pm, 4pm UTC
2. **Email Recommendations**: Sent after each analysis
3. **Price Monitoring**: Checks entry points every 60 seconds
4. **Pushover Alerts**: Sent when entry points are hit
5. **24/7 Operation**: Runs continuously on Render

## Need Help?

- Check logs: `logs/trade_alerts_YYYYMMDD.log`
- Test configuration: `python test_config.py`
- Run manual analysis: `python run_analysis_now.py`







