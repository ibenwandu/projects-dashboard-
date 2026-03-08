# Project Summary: Recruiter Email Automation System

## Overview

This system automates your response to recruiter emails by:
1. **Daily Email Review**: Scans Gmail for emails from the past 24 hours
2. **Smart Classification**: Uses AI to categorize emails as recruiter, task, or other
3. **Automated Responses**: Generates professional responses with customized resumes for recruiters
4. **Daily Summaries**: Sends consolidated summaries of task emails and other emails by 7pm daily
5. **Duplicate Prevention**: Tracks processed emails to avoid reprocessing

## Key Features

### ✅ Email Processing
- Fetches emails from Gmail API (last 24 hours)
- Filters out already processed emails
- Uses AI to classify emails into three categories

### ✅ Recruiter Email Handling
- Identifies recruiter emails automatically
- Extracts job requirements from email content
- Generates customized resume based on:
  - Your resume template
  - LinkedIn profile PDF
  - Projects and skills summary
- Creates professional response email
- Sends you separate email with response and resume for review

### ✅ Task Email Handling
- Identifies non-recruiter emails requiring action
- Generates 3-sentence summaries
- Includes in daily summary email

### ✅ Other Email Handling
- Captures sender name and subject
- Includes in daily summary email

### ✅ Automation
- Runs daily at 7pm (configurable)
- Tracks processed emails in SQLite database
- Sends summaries and responses via email

## File Structure

```
recruiter_email_automation/
├── main.py                    # Main entry point
├── setup.py                   # Setup helper script
├── test_setup.py              # Setup verification script
├── requirements.txt           # Python dependencies
├── README.md                  # Full documentation
├── QUICKSTART.md              # Quick setup guide
├── .env                       # Environment variables (create this)
├── credentials.json           # Gmail API credentials (from Google Cloud)
├── token.json                 # Gmail API token (auto-generated)
├── data/
│   ├── resume_template.txt    # Your resume template
│   ├── linkedin.pdf           # LinkedIn profile PDF
│   ├── skills_summary.txt      # Projects and skills
│   └── processed_emails.db    # Processed emails database
├── output/
│   └── resumes/               # Generated customized resumes
├── logs/                      # Log files
└── src/
    ├── email_processor.py     # Gmail API integration
    ├── email_classifier.py    # AI email classification
    ├── resume_generator.py    # Resume generation
    ├── response_generator.py  # Response generation
    ├── email_sender.py        # Email sending
    ├── database.py            # Email tracking
    └── logger.py              # Logging
```

## Workflow

### Daily Process (7pm)

1. **Fetch Emails** → Get all emails from last 24 hours
2. **Filter Processed** → Skip emails already in database
3. **Classify** → AI categorizes each email:
   - Recruiter
   - Task (action required)
   - Other
4. **Process Recruiters**:
   - Generate customized resume
   - Create professional response
   - Send you email with response + resume
5. **Process Tasks**:
   - Generate 3-sentence summaries
6. **Process Others**:
   - Extract sender + subject
7. **Send Summary**:
   - One email with task summaries + other emails list
8. **Send Recruiter Responses**:
   - Separate email for each recruiter

## Setup Requirements

1. **Python 3.8+**
2. **OpenAI API Key** (for AI features)
3. **Gmail API Credentials** (from Google Cloud Console)
4. **Gmail App Password** (for sending emails)
5. **Data Files**:
   - Resume template
   - LinkedIn PDF
   - Skills summary

## Usage

### Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run setup
python setup.py

# Test setup
python test_setup.py

# Configure .env file with your credentials
```

### Daily Use
```bash
# Start automation (runs daily at 7pm)
python main.py

# Test run (process emails immediately)
python main.py --once

# Test mode (process and exit)
python main.py --test
```

## Configuration

Edit `.env` file:
- `OPENAI_API_KEY` - Your OpenAI API key
- `SENDER_EMAIL` - Your Gmail address
- `SENDER_PASSWORD` - Gmail App Password
- `RECIPIENT_EMAIL` - Where to send summaries
- `SUMMARY_TIME` - Daily run time (default: 19:00)

## Output

### Daily Summary Email
- Statistics (task emails, other emails)
- Task email summaries (3 sentences each)
- List of other emails (sender + subject)

### Recruiter Response Emails
- Original recruiter email
- Generated professional response
- Attached customized resume
- Instructions for sending

### Generated Files
- Resumes: `output/resumes/resume_[sender]_[timestamp].pdf`
- Logs: `logs/automation_[date].log`
- Database: `data/processed_emails.db`

## Technology Stack

- **Python 3.8+**
- **OpenAI API** - Email classification, summarization, resume generation
- **Gmail API** - Email fetching
- **SQLite** - Processed emails tracking
- **SMTP** - Email sending
- **Schedule** - Daily automation

## Security

- Gmail API uses read-only scope
- Credentials stored locally (not in code)
- Processed emails tracked in local database
- No email content stored permanently (only metadata)

## Customization

- **Classification Logic**: Edit `src/email_classifier.py`
- **Resume Generation**: Edit `src/resume_generator.py`
- **Response Style**: Edit `src/response_generator.py`
- **Schedule Time**: Edit `SUMMARY_TIME` in `.env`

## Troubleshooting

See `README.md` for detailed troubleshooting guide.

Common issues:
- Gmail authentication → Delete `token.json` and re-run
- Missing files → Run `python setup.py`
- API errors → Check API keys in `.env`
- PDF generation → Install `wkhtmltopdf` (optional)

## Next Steps

1. Complete setup using `QUICKSTART.md`
2. Test with `python main.py --once`
3. Review generated responses
4. Customize resume template
5. Start daily automation

## Support

- Check logs in `logs/` directory
- Run `python test_setup.py` to verify setup
- Review `README.md` for detailed documentation



