# Quick Start Guide

## 5-Minute Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run Setup Script
```bash
python setup.py
```

This will:
- Create necessary directories
- Create `.env` file template
- Check for required files

### Step 3: Configure Environment

Edit `.env` file and add:
- `OPENAI_API_KEY` - Your OpenAI API key
- `SENDER_EMAIL` - Your Gmail address
- `SENDER_PASSWORD` - Gmail App Password (see below)
- `RECIPIENT_EMAIL` - Where to send summaries (usually same as SENDER_EMAIL)

### Step 4: Get Gmail App Password

1. Enable 2FA on Gmail
2. Go to: https://myaccount.google.com/apppasswords
3. Generate password for "Mail"
4. Copy to `SENDER_PASSWORD` in `.env`

### Step 5: Gmail API Credentials

1. Go to: https://console.cloud.google.com/
2. Create project → Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download as `credentials.json` in project root

### Step 6: Prepare Data Files

Ensure these files exist in `data/`:
- `resume_template.txt` - Your resume template
- `linkedin.pdf` - Your LinkedIn profile PDF
- `skills_summary.txt` - Your projects/skills summary

### Step 7: Test Run

```bash
python main.py
```

On first run, it will open browser for Gmail authentication.

## Daily Usage

Once set up, the system runs automatically at 7pm daily. You can also:

**Run immediately:**
Edit `main.py` and uncomment:
```python
automation.process_daily_emails()  # Uncomment to test
```

**Check logs:**
```bash
# View today's log
cat logs/automation_$(date +%Y%m%d).log
```

## Troubleshooting

**"credentials.json not found"**
→ Download from Google Cloud Console

**"OPENAI_API_KEY not set"**
→ Add to `.env` file

**"Gmail authentication failed"**
→ Delete `token.json` and re-run

**"Resume generation failed"**
→ Check that `data/resume_template.txt`, `data/linkedin.pdf`, and `data/skills_summary.txt` exist

## What Happens Daily at 7pm?

1. ✅ Fetches emails from last 24 hours
2. ✅ Classifies: recruiter / task / other
3. ✅ For recruiters: Generates response + customized resume
4. ✅ For tasks: Creates 3-sentence summaries
5. ✅ Sends you:
   - One summary email (tasks + other emails)
   - Separate emails for each recruiter (with response + resume)

## Next Steps

- Review generated responses before sending
- Customize resume template in `data/resume_template.txt`
- Adjust classification in `src/email_classifier.py`
- Change schedule time in `.env` (`SUMMARY_TIME=19:00`)



