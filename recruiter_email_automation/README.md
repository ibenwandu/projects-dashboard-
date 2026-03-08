# Recruiter Email Automation System

An intelligent email automation workflow that processes your Gmail inbox daily, categorizes emails, generates professional responses to recruiters, and provides daily summaries.

## Features

✅ **Daily Email Processing**: Automatically reviews all emails from the past 24 hours  
✅ **Smart Classification**: Uses AI to categorize emails as recruiter, task, or other  
✅ **Automated Recruiter Responses**: Generates professional responses with customized resumes  
✅ **Resume Customization**: Creates tailored resumes from your template, LinkedIn PDF, and skills summary  
✅ **Task Email Summaries**: Provides 3-sentence summaries for actionable emails  
✅ **Daily Summary Reports**: Sends consolidated email summaries by 7pm daily  
✅ **Duplicate Prevention**: Tracks processed emails to avoid reprocessing  
✅ **Scheduled Automation**: Runs automatically at 7pm daily (configurable)

## Project Structure

```
recruiter_email_automation/
├── main.py                 # Main entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .env                    # Environment variables (create this)
├── credentials.json       # Gmail API credentials (from Google Cloud Console)
├── token.json             # Gmail API token (auto-generated)
├── data/
│   ├── resume_template.txt    # Your resume template
│   ├── linkedin.pdf           # Your LinkedIn profile PDF
│   ├── skills_summary.txt     # Your projects and skills summary
│   └── processed_emails.db    # Database of processed emails (auto-generated)
├── output/
│   └── resumes/               # Generated customized resumes
├── logs/                      # Log files
└── src/
    ├── email_processor.py     # Gmail API integration
    ├── email_classifier.py    # AI email classification
    ├── resume_generator.py    # Resume generation
    ├── response_generator.py  # Response generation
    ├── email_sender.py        # Email sending
    ├── database.py            # Processed emails tracking
    └── logger.py              # Logging configuration
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd personal/recruiter_email_automation
pip install -r requirements.txt
```

**Note**: For PDF generation, you may also need `wkhtmltopdf`:
- Windows: Download from [wkhtmltopdf.org](https://wkhtmltopdf.org/downloads.html)
- Mac: `brew install wkhtmltopdf`
- Linux: `sudo apt-get install wkhtmltopdf`

### 2. Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Gmail API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Choose **Desktop app** as the application type
6. Download the credentials file and save it as `credentials.json` in the project root
7. The first time you run the script, it will open a browser for authentication and create `token.json`

### 3. Environment Configuration

Create a `.env` file in the project root with the following variables:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini  # Optional, defaults to gpt-4o-mini

# Email Configuration (for sending summaries)
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_gmail_app_password
RECIPIENT_EMAIL=your_email@gmail.com  # Where to send summaries

# SMTP Configuration (Gmail defaults)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Summary Time (24-hour format)
SUMMARY_TIME=19:00  # 7pm default

# File Paths (optional, defaults shown)
RESUME_TEMPLATE_PATH=data/resume_template.txt
LINKEDIN_PDF_PATH=data/linkedin.pdf
SKILLS_SUMMARY_PATH=data/skills_summary.txt
```

### 4. Gmail App Password

To send emails, you need a Gmail App Password:

1. Enable 2-factor authentication on your Gmail account
2. Go to [Google Account Settings](https://myaccount.google.com/)
3. Security → 2-Step Verification → App passwords
4. Generate an app password for "Mail"
5. Use this password in the `SENDER_PASSWORD` environment variable

### 5. Prepare Your Data Files

Create the following files in the `data/` directory:

#### `data/resume_template.txt`
Your base resume template. This will be customized for each recruiter email.

#### `data/linkedin.pdf`
Export your LinkedIn profile as a PDF and save it here.

#### `data/skills_summary.txt`
A text file containing:
- Summary of your projects
- Key skills and technologies
- Notable achievements
- Any other relevant professional information

You can use the existing file at `personal/render-deploy/me/summary.txt` as a reference or copy it.

### 6. Create Data Directory

```bash
mkdir -p data output/resumes logs
```

## Usage

### Test Run (Process Emails Immediately)

```bash
python main.py
```

Then uncomment the test line in `main.py`:
```python
# automation.process_daily_emails()  # Uncomment to test immediately
```

### Start Daily Automation

```bash
python main.py
```

The system will:
- Run immediately if it's after 7pm
- Schedule daily runs at 7pm
- Continue running until you stop it (Ctrl+C)

### Run as a Background Service

#### Windows (Task Scheduler)
1. Create a batch file `run_automation.bat`:
```batch
@echo off
cd C:\Users\user\projects\personal\recruiter_email_automation
python main.py
```

2. Schedule it in Task Scheduler to run daily at 7pm

#### Linux/Mac (Cron)
```bash
# Edit crontab
crontab -e

# Add this line (adjust path):
0 19 * * * cd /path/to/recruiter_email_automation && python main.py
```

## How It Works

### Daily Workflow (7pm)

1. **Fetch Emails**: Retrieves all emails from the past 24 hours
2. **Filter Processed**: Skips emails that have already been processed
3. **Classify Emails**: Uses AI to categorize each email:
   - **Recruiter**: Emails from recruiters, headhunters, HR
   - **Task**: Emails requiring action (non-recruiter)
   - **Other**: All other emails
4. **Process Recruiter Emails**:
   - Generates customized resume based on job requirements
   - Creates professional response email
   - Sends you a separate email with the response and resume
5. **Process Task Emails**: Generates 3-sentence summaries
6. **Process Other Emails**: Extracts sender name and subject
7. **Send Daily Summary**: Sends one consolidated email with:
   - Task email summaries
   - List of other emails (sender + subject)

### Email Tracking

All processed emails are stored in `data/processed_emails.db` to prevent reprocessing. The database tracks:
- Email ID
- Category (recruiter/task/other)
- Processing timestamp
- Response/summary generated

## Output Files

- **Generated Resumes**: `output/resumes/resume_[sender]_[timestamp].pdf`
- **Logs**: `logs/automation_[date].log`
- **Database**: `data/processed_emails.db`

## Email Format

### Daily Summary Email
Contains:
- Statistics (number of task emails, other emails)
- Task email summaries (3 sentences each)
- List of other emails (sender name + subject)

### Recruiter Response Email
Contains:
- Original recruiter email
- Generated professional response
- Attached customized resume
- Instructions for sending

## Troubleshooting

### Gmail Authentication Issues
- Ensure `credentials.json` is in the project root
- Delete `token.json` and re-authenticate if needed
- Check that Gmail API is enabled in Google Cloud Console

### OpenAI API Errors
- Verify `OPENAI_API_KEY` is set correctly in `.env`
- Check your OpenAI account has sufficient credits
- Ensure the API key has proper permissions

### Email Sending Issues
- Verify Gmail App Password is correct
- Ensure 2FA is enabled on your Gmail account
- Check SMTP settings in `.env`

### Resume Generation Issues
- Ensure all data files exist (`resume_template.txt`, `linkedin.pdf`, `skills_summary.txt`)
- PDF generation requires `wkhtmltopdf` (optional - falls back to text files)
- Check file paths in `.env` if using custom locations

## Customization

### Change Summary Time
Edit `SUMMARY_TIME` in `.env` (24-hour format, e.g., `19:00` for 7pm)

### Adjust AI Model
Change `OPENAI_MODEL` in `.env` (e.g., `gpt-4`, `gpt-4-turbo`)

### Modify Classification Logic
Edit `src/email_classifier.py` to adjust how emails are categorized

### Customize Resume Generation
Edit `src/resume_generator.py` to change how resumes are generated

## Security Notes

- Never commit `.env`, `credentials.json`, or `token.json` to version control
- Keep your Gmail App Password secure
- Regularly review processed emails in the database
- The system only reads emails (Gmail API scope: `gmail.readonly`)

## License

This project is for personal use. Modify as needed for your requirements.

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Review error messages in the console
3. Ensure all setup steps are completed correctly



