# Render Deployment Guide

Deploy your Trade Alerts system to Render for 24/7 operation.

## Prerequisites

1. **GitHub Account** - Your code needs to be in a GitHub repository
2. **Render Account** - Sign up at https://render.com (free tier available)

## Step 1: Push Code to GitHub

If you haven't already:

```bash
cd C:\Users\user\projects\personal\Trade-Alerts
git init
git add .
git commit -m "Initial commit: Trade Alerts system"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/trade-alerts.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

## Step 2: Create Render Service

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +"** → **"Blueprint"** (or "Worker" if Blueprint not available)
3. **Connect your GitHub repository**
4. **Select your repository** (`trade-alerts`)

### If using Blueprint (render.yaml):

1. Render will detect `render.yaml`
2. Click **"Apply"**
3. Render will create the service automatically

### If using Manual Setup:

1. **Service Type**: Worker
2. **Name**: `trade-alerts`
3. **Environment**: Python 3
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `python main.py`
6. **Branch**: `main`

## Step 3: Configure Environment Variables

In Render Dashboard → Your Service → Environment, add these variables:

### Google Drive
```
GOOGLE_DRIVE_FOLDER_ID=your-folder-id
GOOGLE_DRIVE_CREDENTIALS_JSON=<paste-full-json-content>
GOOGLE_DRIVE_REFRESH_TOKEN=your-refresh-token
```

### LLM API Keys
```
OPENAI_API_KEY=your-openai-key
GOOGLE_API_KEY=your-google-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### Email
```
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
RECIPIENT_EMAIL=your-email@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### Pushover
```
PUSHOVER_API_TOKEN=your-pushover-token
PUSHOVER_USER_KEY=your-pushover-user-key
```

### Optional Configuration
```
ANALYSIS_TIMES=07:00,09:00,12:00,16:00
CHECK_INTERVAL=60
ENTRY_TOLERANCE_PIPS=10
ENTRY_TOLERANCE_PERCENT=0.1
OPENAI_MODEL=gpt-4
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```

**Important Notes:**
- For `GOOGLE_DRIVE_CREDENTIALS_JSON`, paste the ENTIRE JSON content as a single line (or use Render's multi-line support)
- Use the same Google Drive credentials from your Forex tracker project
- Use the same email settings if you want recommendations sent to the same email

## Step 4: Deploy

1. Click **"Create"** or **"Save Changes"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Start the service
3. Check the **Logs** tab to see it running

## Step 5: Verify Deployment

1. **Check Logs**: Should see "✅ Trade Alert System initialized"
2. **Wait for scheduled time**: System will run analysis at 7am, 9am, 12pm, 4pm
3. **Or trigger manually**: Use Render Shell to run `python run_analysis_now.py`

## Monitoring

- **Logs**: View real-time logs in Render Dashboard
- **Status**: Service should show "Live" status
- **Activity**: Check logs for analysis runs and alerts

## Troubleshooting

### Service won't start
- Check logs for errors
- Verify all environment variables are set
- Check that `requirements.txt` is correct

### Analysis not running
- Check logs for scheduled time messages
- Verify `ANALYSIS_TIMES` is set correctly
- Check timezone (Render uses UTC by default)

### No files found in Google Drive
- Verify `GOOGLE_DRIVE_FOLDER_ID` is correct
- Check that folder is accessible
- Verify credentials are valid

### LLM errors
- Check API keys are set correctly
- Verify API keys are valid and have credits
- Check logs for specific error messages

## Cost Considerations

**Free Tier:**
- 750 hours/month (enough for 24/7 operation)
- Service spins down after 15 minutes of inactivity (not ideal for this use case)

**Paid Tier ($7/month):**
- Always-on service
- No spin-down
- Recommended for 24/7 monitoring

## Next Steps

After deployment:
1. Monitor logs for first scheduled analysis
2. Check email for recommendations
3. Verify Pushover alerts work when entry points are hit
4. System will run automatically at scheduled times







