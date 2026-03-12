# Render Deployment Checklist

## Pre-Deployment

- [ ] Code is in a GitHub repository
- [ ] All files committed and pushed
- [ ] `render.yaml` exists
- [ ] `Procfile` exists
- [ ] `.renderignore` exists
- [ ] `requirements.txt` is up to date

## Render Setup

- [ ] Created Render account
- [ ] Connected GitHub account to Render
- [ ] Created new service (Worker type)
- [ ] Connected repository

## Environment Variables (Add in Render Dashboard)

### Google Drive
- [ ] `GOOGLE_DRIVE_FOLDER_ID`
- [ ] `GOOGLE_DRIVE_CREDENTIALS_JSON` (full JSON content)
- [ ] `GOOGLE_DRIVE_REFRESH_TOKEN`

### LLM API Keys
- [ ] `OPENAI_API_KEY`
- [ ] `GOOGLE_API_KEY`
- [ ] `ANTHROPIC_API_KEY`

### Email
- [ ] `SENDER_EMAIL`
- [ ] `SENDER_PASSWORD` (Gmail app password)
- [ ] `RECIPIENT_EMAIL`
- [ ] `SMTP_SERVER=smtp.gmail.com`
- [ ] `SMTP_PORT=587`

### Pushover
- [ ] `PUSHOVER_API_TOKEN`
- [ ] `PUSHOVER_USER_KEY`

### Optional (have defaults)
- [ ] `ANALYSIS_TIMES=07:00,09:00,12:00,16:00`
- [ ] `CHECK_INTERVAL=60`
- [ ] `OPENAI_MODEL=gpt-4`
- [ ] `ANTHROPIC_MODEL=claude-haiku-4-5-20251001`

## Post-Deployment

- [ ] Service shows "Live" status
- [ ] Logs show "✅ Trade Alert System initialized"
- [ ] No errors in logs
- [ ] Wait for scheduled analysis time OR trigger manually
- [ ] Verify email received with recommendations
- [ ] Verify entry points are being monitored

## Quick Test

After deployment, you can test immediately using Render Shell:

1. Go to Render Dashboard → Your Service → Shell
2. Run: `python run_analysis_now.py`
3. Check logs for results

## Troubleshooting

- **Service won't start**: Check logs, verify all env vars set
- **Import errors**: Check `requirements.txt` includes all packages
- **No files found**: Verify Google Drive folder ID and credentials
- **LLM errors**: Check API keys are valid and have credits

