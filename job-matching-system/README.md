# Job Matching and Resume Generation System

An intelligent Python-based AI system that automatically searches job sites, evaluates job fit, and generates custom resumes for selected positions.

## Features

### Agent 1: Job Matching Agent
- **Multi-Site Scraping**: Searches LinkedIn Jobs, Indeed, and JobLeads
- **Smart Filtering**: Jobs posted within the last 7 days
- **AI-Powered Evaluation**: Uses OpenAI GPT-4 or Claude API for intelligent job scoring (1-100 scale)
- **Google Sheets Integration**: Automatically populates high-scoring jobs (85+)
- **Daily Automation**: Runs at 6 PM daily with email notifications

### Agent 2: Resume Generator
- **Sheet Monitoring**: Watches Google Sheets for jobs marked for application
- **Custom Resume Generation**: AI-tailored resumes for specific job requirements
- **Multiple Formats**: Generates PDF, DOCX, and plain text formats
- **ATS Optimization**: Ensures resumes pass Applicant Tracking Systems
- **Automated Workflow**: Hourly checks with status tracking

## Installation

1. **Clone the repository** (or use the generated files):
```bash
cd job-matching-system
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Install ChromeDriver** (for LinkedIn scraping):
   - Download from [ChromeDriver](https://chromedriver.chromium.org/)
   - Add to your PATH or place in project directory

## Configuration

### 1. Environment Setup
Copy `config/.env.example` to `config/.env` and fill in your configuration:

```bash
# AI API Configuration
OPENAI_API_KEY=your_openai_key
CLAUDE_API_KEY=your_claude_key

# Google APIs
GOOGLE_DRIVE_CREDENTIALS=config/credentials/drive_credentials.json
GOOGLE_SHEETS_ID=your_sheet_id
GMAIL_CREDENTIALS=config/credentials/gmail_credentials.json

# Job Search Configuration
LINKEDIN_EMAIL=your_linkedin_email
LINKEDIN_PASSWORD=your_linkedin_password
SEARCH_LOCATIONS=Toronto,ON;Remote;Ontario,Canada
MIN_MATCH_SCORE=85

# Profile Files (Google Drive file IDs)
LINKEDIN_PDF_ID=google_drive_file_id
SUMMARY_TXT_ID=google_drive_file_id

# Email Notifications
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
RECIPIENT_EMAIL=your_email@gmail.com
```

### 2. Google API Setup

#### Google Drive API:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Drive API and Google Sheets API
4. Create credentials (Service Account or OAuth2)
5. Download credentials as `config/credentials/drive_credentials.json`

#### Google Sheets Setup:
1. Create a new Google Sheet
2. Copy the Sheet ID from the URL
3. Share the sheet with your service account email (if using service account)

### 3. Profile Files Setup
Upload your profile files to Google Drive:
- `LinkedIn.pdf`: Export your LinkedIn profile as PDF
- `Summary.txt`: Your professional summary text file
- Note the file IDs from Google Drive URLs

## Usage

### Check System Status
```bash
python main.py status
```

### Run Individual Components

#### Job Matching Agent (once)
```bash
python main.py job-matching
```

#### Resume Generation Agent (once)
```bash
python main.py resume-generation
```

#### Resume Monitoring (continuous)
```bash
python main.py resume-monitoring
```

#### Full Automated Scheduler
```bash
python main.py scheduler
```

## System Architecture

### Agent 1 Workflow:
1. **Daily Execution**: Runs at 6 PM each day
2. **Profile Loading**: Fetches LinkedIn PDF and summary from Google Drive
3. **Job Scraping**: Searches LinkedIn, Indeed, and JobLeads
4. **Duplicate Filtering**: Ignores previously analyzed postings
5. **AI Evaluation**: Scores each job against profile (1-100)
6. **Sheet Population**: Adds high-scoring jobs (85+) to Google Sheets
7. **Email Notification**: Sends daily summary

### Agent 2 Workflow:
1. **Monitor Apply Column**: Checks for newly checked boxes hourly
2. **Job Analysis**: Re-fetches full job description and company info
3. **Custom Resume Generation**: Uses AI to create tailored resume
4. **Format Conversion**: Generates PDF, DOCX, and TXT formats
5. **Quality Assurance**: Maintains factual accuracy while optimizing
6. **File Management**: Stores in organized directory structure
7. **Status Updates**: Marks completion in Google Sheets

### Google Sheets Structure:
| Score | Job Title | Company | Location | Application Link | Match Reasoning | Apply | Resume Status | Generated Date | Resume Link |
|-------|-----------|---------|----------|------------------|-----------------|-------|---------------|----------------|-------------|

## Key Components

### Web Scrapers
- **LinkedIn Scraper**: Selenium-based with login automation
- **Indeed Scraper**: BeautifulSoup with request handling
- **JobLeads Scraper**: Placeholder for custom implementation

### AI Integration
- **Job Evaluator**: OpenAI GPT-4 or Claude for job scoring
- **Resume Builder**: AI-powered resume customization
- **Keyword Optimizer**: ATS optimization with job-specific keywords

### Profile Management
- **Google Drive Client**: Handles file downloads and authentication
- **Profile Manager**: Parses LinkedIn PDF and manages profile data

### Resume Generation
- **Resume Builder**: AI-powered content generation
- **Format Converter**: Multi-format output (PDF, DOCX, TXT)
- **Template Manager**: Support for custom resume templates

## Logging and Monitoring

All components generate detailed logs in the `logs/` directory:
- `main.log`: Main application events
- `job_matching_agent.log`: Job scraping and evaluation
- `resume_generation_agent.log`: Resume generation activities
- `scheduler.log`: Scheduled task execution

## Error Handling

- **Network Issues**: Retry mechanisms with exponential backoff
- **API Failures**: Fallback between OpenAI and Claude APIs
- **Rate Limiting**: Respectful delays between requests
- **Data Validation**: Comprehensive input validation and sanitization
- **Email Notifications**: Automatic error reporting via email

## Security Notes

- Store API keys securely in environment variables
- Use Gmail App Passwords instead of regular passwords
- Never commit credentials to version control
- Google APIs use read-only scopes where possible
- Regular credential rotation recommended

## Customization

### Search Terms
Modify search terms in `job_matching_agent.py`:
```python
search_terms = [
    "Business Analyst",
    "Project Manager", 
    "Process Analyst",
    # Add your terms here
]
```

### Scoring Criteria
Adjust AI evaluation prompts in `src/ai/prompt_templates.py`

### Resume Templates
Add custom DOCX templates to `templates/` directory

### Scheduling
Modify schedules in `src/scheduler/job_scheduler.py`

## Troubleshooting

### Common Issues

1. **LinkedIn Login Fails**
   - Check credentials and enable less secure apps
   - Handle 2FA if enabled

2. **Google API Errors**
   - Verify credentials file path and permissions
   - Ensure APIs are enabled in Google Cloud Console

3. **No Jobs Found**
   - Check search terms and locations
   - Verify minimum match score threshold

4. **Resume Generation Fails**
   - Verify AI API keys and quotas
   - Check profile files are accessible

### Debug Mode
Enable debug logging by modifying log level in main components:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Development

### Project Structure
```
job-matching-system/
├── src/
│   ├── scrapers/          # Web scrapers for job sites
│   ├── profile/           # Profile management
│   ├── ai/               # AI evaluation and generation
│   ├── resume_generator/  # Resume building and formatting
│   ├── reporting/        # Sheets and email integration
│   ├── monitoring/       # Apply column monitoring
│   └── scheduler/        # Task scheduling
├── config/               # Configuration files
├── templates/            # Resume templates
├── logs/                # Application logs
├── data/                # Generated resumes and data
├── requirements.txt     # Python dependencies
└── main.py             # Main entry point
```

### Adding New Job Sites
1. Create new scraper in `src/scrapers/`
2. Implement required methods following existing patterns
3. Add to `job_matching_agent.py` scrapers dictionary

### Contributing
1. Follow existing code patterns and documentation
2. Add comprehensive logging for debugging
3. Include error handling for all external API calls
4. Test with various job types and scenarios

## License

This project is provided as-is for educational and personal use. Ensure compliance with job site terms of service when scraping.

## Support

For issues and questions:
1. Check the logs in `logs/` directory
2. Verify configuration in `.env` file
3. Test individual components before running full system
4. Review error notifications sent via email