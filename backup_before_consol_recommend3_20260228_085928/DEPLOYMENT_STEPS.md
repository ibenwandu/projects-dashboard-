# Deployment Steps for Trade-Alerts

## Step 1: Initialize Git (if not done)

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
git init
git add .
git commit -m "Initial commit: Trade Alerts with updated models and Frankfurter.app"
```

## Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `trade-alerts` (or your preferred name)
3. **Don't** initialize with README, .gitignore, or license (you already have these)
4. Click "Create repository"

## Step 3: Push to GitHub

```powershell
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/trade-alerts.git
git branch -M main
git push -u origin main
```

## Step 4: Deploy to Render

### Option A: Using Blueprint (Recommended - Automatic)

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub account (if not already connected)
4. Select your `trade-alerts` repository
5. Render will automatically detect `render.yaml`
6. Click **"Apply"**

### Option B: Manual Setup

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Worker"**
3. Connect GitHub repository
4. Select `trade-alerts` repository
5. Configure:
   - **Name**: `trade-alerts`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Branch**: `main`

## Step 5: Configure Environment Variables in Render

In Render Dashboard → Your Service → Environment, add ALL these variables:

### Google Drive
```
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-from-forex-tracker
GOOGLE_DRIVE_CREDENTIALS_JSON=<paste-full-json-content-here>
GOOGLE_DRIVE_REFRESH_TOKEN=your-refresh-token
```

**Important**: For `GOOGLE_DRIVE_CREDENTIALS_JSON`, paste the ENTIRE JSON content as a single value. You can use the same credentials from your Forex tracker project.

### LLM API Keys
```
OPENAI_API_KEY=your-openai-key
GOOGLE_API_KEY=your-google-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### Optional Model Configuration (has defaults)
```
OPENAI_MODEL=gpt-4o-mini
GEMINI_MODEL=gemini-3.0-pro
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```

### Email
```
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-gmail-app-password
RECIPIENT_EMAIL=your-email@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### Pushover
```
PUSHOVER_API_TOKEN=your-pushover-token
PUSHOVER_USER_KEY=your-pushover-user-key
```

### Optional Configuration (has defaults)
```
ANALYSIS_TIMES=07:00,09:00,12:00,16:00
CHECK_INTERVAL=60
ENTRY_TOLERANCE_PIPS=10
ENTRY_TOLERANCE_PERCENT=0.1
```

## Step 6: Deploy and Verify

1. Click **"Create"** or **"Save Changes"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Start the service
3. Check the **Logs** tab:
   - Should see: "✅ Trade Alert System initialized"
   - Should see: "Waiting for scheduled analysis time..."
   - No errors

## Step 7: Test the System

### Option 1: Wait for Scheduled Time
- System will run analysis at: 7am, 9am, 12pm, 4pm UTC
- Check logs at those times

### Option 2: Trigger Manually (Recommended for Testing)
1. Go to Render Dashboard → Your Service → **Shell**
2. Run: `python run_analysis_now.py`
3. Check logs for results
4. Check your email for recommendations

## Step 8: Monitor

- **Logs**: View real-time logs in Render Dashboard
- **Status**: Service should show "Live"
- **Email**: Check for recommendations at scheduled times
- **Pushover**: Test alerts when entry points are hit

## Troubleshooting

### Service won't start
- Check logs for errors
- Verify all environment variables are set
- Check that `requirements.txt` is correct

### No files found in Google Drive
- Verify `GOOGLE_DRIVE_FOLDER_ID` matches your Forex tracker folder
- Check that credentials are valid
- Ensure folder is accessible

### LLM errors
- Check API keys are valid and have credits
- Verify model names are correct
- Check logs for specific error messages

### No price data
- Frankfurter.app is free and should work automatically
- Check logs for API errors
- Verify currency pairs are valid

## Cost Considerations

**Free Tier:**
- 750 hours/month
- Service may spin down after 15 minutes of inactivity

**Paid Tier ($7/month):**
- Always-on service (recommended for 24/7 monitoring)
- No spin-down
- Better for continuous price monitoring

## Next Steps After Deployment

1. ✅ Monitor first scheduled analysis
2. ✅ Verify email recommendations are received
3. ✅ Test Pushover alerts (when entry points are hit)
4. ✅ Adjust `ANALYSIS_TIMES` if needed (timezone is UTC)
5. ✅ Monitor costs (especially LLM API usage)







