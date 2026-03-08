# Job Evaluation System

An intelligent job evaluation and resume generation system that processes Gmail job alerts instead of web scraping.

## 🎯 Project Overview

This system implements two AI agents:
- **Agent 1 (Gmail Job Agent)**: Extracts job alerts from Gmail, evaluates them using AI, and populates Google Sheets
- **Agent 2 (Resume Generation Agent)**: Monitors Google Sheets for marked jobs and generates customized resumes

## 🏗️ Architecture

```
Job_evaluation/
├── src/
│   ├── agents/               # Main agents
│   │   ├── gmail_job_agent.py
│   │   └── resume_generation_agent.py
│   ├── gmail/               # Gmail integration
│   │   ├── gmail_client.py
│   │   ├── email_parser.py
│   │   └── job_extractor.py
│   ├── ai/                  # AI evaluation
│   │   ├── job_evaluator.py
│   │   └── prompt_templates.py
│   ├── storage/             # Google APIs
│   │   ├── google_drive_client.py
│   │   ├── sheets_manager.py
│   │   └── file_manager.py
│   ├── utils/               # Utilities
│   │   ├── name_formatter.py
│   │   ├── text_processor.py
│   │   └── docx_generator.py
│   ├── config/              # Configuration
│   │   └── settings.py
│   └── tests/               # Test suite
├── config/credentials/      # API credentials
├── logs/                   # Application logs
├── data/                   # Profile and temp data
├── main.py                 # Main entry point
├── requirements.txt        # Dependencies
├── .env                   # Environment variables
└── README.md              # This file
```

## 🚀 Key Features

### Gmail Integration
- ✅ Retrieves job alerts from last 7 days
- ✅ Identifies job alerts from multiple sources (LinkedIn, Indeed, Glassdoor, etc.)
- ✅ Extracts sender information with new "sender" column in Google Sheets
- ✅ Stores raw email alerts in Google Drive "Alerts" folder

### AI Job Evaluation
- ✅ Uses OpenAI GPT-4 or Claude API for intelligent job scoring (1-100 scale)
- ✅ Evaluates skills alignment, experience relevance, industry fit
- ✅ Generates detailed feedback for each job
- ✅ Filters high-scoring jobs (85+ threshold)

### Google Sheets Integration
- ✅ Populates sheet with job data including new "sender" column
- ✅ Only includes high-scoring jobs (85+)
- ✅ Monitors "Apply" column for resume generation triggers
- ✅ Updates resume status and links

### Resume Generation
- ✅ Generates customized resumes in DOCX format
- ✅ Creates evaluation feedback documents
- ✅ Uses standardized naming: CompanyName_JobTitle.docx
- ✅ Stores files in Google Drive "Result" folder

### Google Drive Storage
- ✅ **Alerts folder**: Raw email alerts and extracted job data
- ✅ **Result folder**: Generated resumes and feedback documents
- ✅ **Reports folder**: Job evaluation reports and summary documents
- ✅ Automatic folder creation and management

## 📋 Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy and update the `.env` file with your API keys:

```bash
# AI API Keys
OPENAI_API_KEY=your_openai_key
CLAUDE_API_KEY=your_claude_key

# Google API Configuration
GMAIL_CREDENTIALS=config/credentials/gmail_credentials.json
DRIVE_CREDENTIALS=config/credentials/drive_credentials.json
SHEETS_CREDENTIALS=config/credentials/gmail_credentials.json
GOOGLE_SHEETS_ID=your_google_sheets_id

# Gmail Configuration
GMAIL_SEARCH_DAYS=7
JOB_ALERT_KEYWORDS=job,position,opportunity,hiring,career

# Profile Configuration
LINKEDIN_PDF_ID=your_linkedin_pdf_file_id
SUMMARY_TXT_ID=your_summary_file_id

# Scoring Configuration
MIN_MATCH_SCORE=85

# Email Notifications
NOTIFICATION_EMAIL=your_email@gmail.com
```

### 3. Setup Google API Credentials
Place your Google API credential files in `config/credentials/`:
- `gmail_credentials.json`
- `drive_credentials.json`

### 4. Prepare Profile Files
Upload your profile files to Google Drive and update the IDs in `.env`:
- LinkedIn profile export (PDF)
- Professional summary (TXT)

## 🔧 Usage

### Test Connection
```bash
python main.py --test-connection
```

### Get Job Alert Summary
```bash
python main.py --summary
```

### Run Gmail Agent Only
```bash
python main.py --run-gmail
```

### Run Resume Agent Only
```bash
python main.py --run-resume
```

### Run Full Pipeline
```bash
python main.py --run-pipeline
```

### Run Tests
```bash
python main.py --run-tests
```

## 📊 Google Sheets Structure

The system populates Google Sheets with the following columns:

| Column | Description |
|--------|-------------|
| Score | AI match score (1-100) |
| Job Title | Extracted job title |
| Company | Company name |
| Location | Job location |
| Application Link | Direct application URL |
| **Sender** | **NEW: Email sender info** |
| Match Reasoning | AI evaluation feedback |
| Apply | Checkbox for resume generation |
| Resume Status | Generation status |
| Generated Date | When resume was created |
| Resume Link | Google Drive link to resume |
| Email Date | When job alert was received |
| Source Type | Job board source |

## 🤖 AI Evaluation Criteria

Jobs are evaluated on a 1-100 scale based on:

1. **Skills Alignment (40%)**: Match between candidate skills and job requirements
2. **Experience Relevance (30%)**: Relevant experience level and background
3. **Industry/Domain Match (15%)**: Industry alignment with candidate background
4. **Location/Remote Flexibility (10%)**: Location compatibility
5. **Career Growth Potential (5%)**: Advancement opportunities

### Scoring Guidelines
- **90-100**: Exceptional match, highly recommended
- **80-89**: Strong match, recommended
- **70-79**: Good match, worth considering
- **60-69**: Moderate match, some concerns
- **50-59**: Weak match, significant gaps
- **1-49**: Poor match, not recommended

## 📁 File Organization

### Google Drive Structure
```
Google Drive/
├── Alerts/                    # Raw email alerts
│   ├── email_20240729_120000_LinkedIn_abc123.json
│   └── extracted_jobs_20240729_120500.json
└── Job_evaluation/
    ├── Result/               # Generated documents
    │   ├── Resume_TechCorp_SeniorAnalyst.docx
    │   └── Feedback_TechCorp_SeniorAnalyst.docx
    └── Reports/              # Job evaluation reports
        └── job_evaluation_report_20240729_120500.docx
```

### Naming Convention
All files use standardized naming: `CompanyName_JobTitle.docx`

Examples:
- `Resume_Microsoft_SeniorBusinessAnalyst.docx`
- `Feedback_Google_ProductManager.docx`

## 🔄 Automation Workflow

1. **Gmail Agent Pipeline**:
   - Authenticate with Gmail API
   - Retrieve job alerts from last 7 days
   - Store raw emails in Google Drive
   - Parse and extract job data
   - AI evaluation and scoring
   - Update Google Sheets with high-scoring jobs

2. **Resume Agent Pipeline**:
   - Monitor Google Sheets for marked jobs
   - Generate customized resumes using AI
   - Create evaluation feedback documents
   - Upload files to Google Drive
   - Update job status in Google Sheets

## 🧪 Testing

The system includes comprehensive tests for:
- Gmail API connection
- Email parsing and job extraction
- AI evaluation functionality
- Google Sheets integration
- End-to-end workflow

Run tests with: `python main.py --run-tests`

## 📈 Success Criteria (MVP)

- ✅ Successfully retrieves job alerts from Gmail (last 7 days)
- ✅ Accurately extracts job data from 90% of emails
- ✅ AI evaluation produces meaningful scores (1-100)
- ✅ Google Sheets populated with job data including sender column
- ✅ Customized resumes generated in DOCX format
- ✅ All files stored in correct Google Drive locations
- ✅ Proper naming convention applied throughout system
- ✅ System runs without manual intervention

## 🚨 Error Handling

The system includes robust error handling for:
- Gmail API rate limits and authentication issues
- AI API failures with fallback mechanisms
- Google Drive storage errors with retry logic
- Data quality issues with validation systems
- Network and connectivity problems

## 📝 Logging

Comprehensive logging is available in:
- `logs/gmail_agent.log` - Gmail agent activities
- `logs/resume_agent.log` - Resume agent activities
- `logs/system.log` - General system events

## 🔐 Security

- API keys stored in environment variables
- OAuth2 authentication for Google APIs
- No sensitive information logged or committed
- Secure credential management

## 📞 Support

For issues or questions:
1. Check the logs in the `logs/` directory
2. Verify API credentials and permissions
3. Test individual components using the CLI options
4. Review the test suite for component validation

## 🎉 Implementation Status

**✅ COMPLETED MILESTONES:**

- **Milestone 1**: Gmail Integration Foundation
- **Milestone 2**: Job Data Extraction & Google Drive Storage  
- **Milestone 3**: AI Job Evaluation System
- **Milestone 4**: Google Sheets Integration with Sender Column
- **Milestone 5**: Resume Generation System
- **Milestone 6**: System Integration & Automation

**🚀 READY FOR PRODUCTION USE**

The system is fully functional and ready for daily automated execution!