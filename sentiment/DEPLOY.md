# Deployment Guide - Render

## Deploy to Render

### Step 1: Push to GitHub

Make sure your code is in a GitHub repository.

### Step 2: Create Services on Render

The system requires TWO services on Render:
1. **Web Service** - For the UI
2. **Worker Service** - For background monitoring

#### Create Web Service

1. Go to Render Dashboard → "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name:** `sentiment-monitor-web`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Environment:** Python 3

#### Create Worker Service

1. Go to Render Dashboard → "New +" → "Background Worker"
2. Connect the same GitHub repository
3. Configure:
   - **Name:** `sentiment-monitor-worker`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python worker.py`
   - **Environment:** Python 3

### Step 3: Set Environment Variables

Set these environment variables for BOTH services:

#### Required:
```
# LLM Provider (choose one)
OPENAI_API_KEY=your-openai-key
# OR
ANTHROPIC_API_KEY=your-anthropic-key
# OR
GOOGLE_API_KEY=your-google-key

# Email Alerts
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your-gmail-app-password
EMAIL_RECIPIENT=your_email@gmail.com

# Web Service Only
SECRET_KEY=your-secret-key-here
```

#### Optional:
```
NEWSAPI_KEY=your-newsapi-key
```

### Step 4: Deploy

Render will automatically deploy both services. The worker will start running checks every 15 minutes.

### Step 5: Access Web UI

Once deployed, access the web UI at:
- `https://sentiment-monitor-web.onrender.com` (or your custom domain)

You can now:
- Add trades to watchlist via the UI
- View recent alerts
- See last alert times and sentiment directions
- Monitor active high-impact events

## Using render.yaml (Alternative)

If you want to use `render.yaml` for easier setup:

1. Render will auto-detect `render.yaml`
2. It will create both services automatically
3. You still need to set environment variables in the Render dashboard

## Environment Variables Summary

| Variable | Required For | Description |
|----------|-------------|-------------|
| `OPENAI_API_KEY` | Both | OpenAI API key (or use Anthropic/Gemini) |
| `SENDER_EMAIL` | Both | Email address for sending alerts |
| `SENDER_PASSWORD` | Both | Gmail App Password |
| `EMAIL_RECIPIENT` | Both | Email address to receive alerts |
| `SECRET_KEY` | Web only | Flask secret key (generate random string) |
| `NEWSAPI_KEY` | Both (optional) | NewsAPI key for additional news sources |

## Database Storage

The database file (`data/sentiment_monitor.db`) is stored on Render's disk. Data persists across deployments.

## Monitoring

- **Web UI:** Access at your Render web service URL
- **Worker Logs:** Check Render dashboard → Worker service → Logs
- **Alerts:** Sent via email when sentiment shifts are detected






