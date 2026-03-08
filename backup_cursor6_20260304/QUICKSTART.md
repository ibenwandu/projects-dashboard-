# Quick Start Guide - Trade Alerts System

## Overview

This system automates the full workflow:
1. Reads raw forex data from Google Drive
2. Analyzes with 3 LLMs (ChatGPT, Gemini, Claude)
3. Synthesizes with Gemini (final recommendation)
4. Emails all recommendations
5. Monitors entry points and sends Pushover alerts

## Step 1: Setup

```bash
python setup.py
```

## Step 2: Configure Environment Variables

Edit `.env` and add:

### Google Drive (for reading raw data)
- `GOOGLE_DRIVE_FOLDER_ID` - Your "Forex tracker" folder ID
- `GOOGLE_DRIVE_CREDENTIALS_JSON` - Full JSON from credentials.json
- `GOOGLE_DRIVE_REFRESH_TOKEN` - OAuth2 refresh token

### LLM API Keys
- `GOOGLE_API_KEY` - For Gemini (get from Google AI Studio) - also used for final synthesis
- `ANTHROPIC_API_KEY` - For Claude (get from console.anthropic.com)
- `OPENAI_API_KEY` - For ChatGPT (get from platform.openai.com)
- `GEMINI_MODEL` - Optional (default: gemini-2.0-flash-exp)
- `OPENAI_MODEL` - Optional (default: gpt-4o-mini)

### Email (for sending recommendations)
- `SENDER_EMAIL` - Your email
- `SENDER_PASSWORD` - App password (Gmail)
- `RECIPIENT_EMAIL` - Where to send recommendations
- `SMTP_SERVER` - smtp.gmail.com
- `SMTP_PORT` - 587

### Pushover (for entry point alerts)
- `PUSHOVER_API_TOKEN` - From pushover.net
- `PUSHOVER_USER_KEY` - From pushover.net

### Optional Configuration
- `ANALYSIS_TIMES` - Comma-separated times (default: 07:00,09:00,12:00,16:00)
- `CHECK_INTERVAL` - Seconds between price checks (default: 60)
- `ENTRY_TOLERANCE_PIPS` - Pips tolerance (default: 10)
- `OPENAI_MODEL` - ChatGPT model (default: gpt-4)

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Run

```bash
python main.py
```

The system will:
- Run analysis at scheduled times (7am, 9am, 12pm, 4pm)
- Email all recommendations
- Monitor entry points continuously
- Send Pushover alerts when entry points are hit

## Workflow

1. **Scheduled Analysis** (7am, 9am, 12pm, 4pm):
   - Reads latest reports from Google Drive
   - Sends to ChatGPT, Gemini, Claude
   - Gemini synthesizes final recommendations
   - Emails all 4 recommendations
   - Extracts entry/exit points for monitoring

2. **Continuous Monitoring**:
   - Checks prices every 60 seconds
   - Compares against entry points
   - Sends Pushover alerts when hit

## Notes

- Analysis runs at scheduled times only
- Price monitoring runs continuously
- Alerts are one-time per entry point
- All recommendations are emailed for your review
