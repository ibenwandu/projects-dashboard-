 want to create an intelligent job matching and resume generation system with two integrated AI agents:
Project Overview
Create a Python-based AI system that automatically searches job sites, evaluates job fit, generates reports, and creates custom resumes for selected positions.
Agent 1: Job Matching Agent
Core Functionality

Target Sites: LinkedIn Jobs, Indeed, and JobLeads
Search Terms: "Business Analyst", "Project Manager", "Process Analyst", "Data Analyst", "Scrum Master", "Product Manager"
Filters: Jobs posted within the last 7 days
Data to Extract: Job title, company, location, job description, application link, posting date

Profile Management

Profile Sources:

LinkedIn.pdf (from Google Drive) - my LinkedIn profile export
Summary.txt (from Google Drive) - my professional summary


Google Drive Integration: Automatically fetch and read these files for profile matching

AI-Powered Job Matching

Scoring System: 1-100 scale (1 = least fit, 100 = most fit)
Evaluation Criteria: Skills alignment, experience relevance, education match, industry experience, role responsibilities fit
AI Model: Use OpenAI GPT-4 or Claude API for intelligent analysis

Agent 2: Custom Resume Generator
Core Functionality

Monitor Apply Column: Check Google Sheets for newly checked boxes
Job Description Analysis: Re-fetch and analyze selected job descriptions
Resume Customization: Generate tailored resumes based on original profile and specific job requirements
ATS Optimization: Ensure resumes pass Applicant Tracking Systems

Resume Generation Features

Multiple Formats: Generate in PDF, DOCX, and plain text formats
Template Variations: Professional, Modern, Executive, Tech-focused templates
Keyword Optimization: Integrate job-specific keywords naturally
Skills Highlighting: Emphasize most relevant skills for each role

Google Sheets Integration
Columns Structure:

Score, Job Title, Company, Location, Application Link, Match Reasoning, Apply (checkbox), Resume Status, Generated Date, Resume Link

Features:

Apply Column: Checkbox type for manual job selection
Automatic Updates: First agent populates, second agent monitors checkboxes
Filter Threshold: Only include jobs with 85%+ match score
Status Tracking: Track resume generation progress

Technical Requirements
Technologies to Use:

Python 3.9+
Web Scraping: Selenium, BeautifulSoup, or Playwright
AI Integration: OpenAI API or Anthropic Claude API
Google APIs: Google Drive API, Google Sheets API, Gmail API
Scheduling: APScheduler for daily automation
Data Processing: Pandas for data manipulation
Environment: Use python-dotenv for configuration

Project Structure:

job-matching-system/
├── src/
│   ├── scrapers/
│   │   ├── linkedin_scraper.py
│   │   ├── indeed_scraper.py
│   │   └── jobleads_scraper.py
│   ├── profile/
│   │   ├── profile_manager.py
│   │   └── google_drive_client.py
│   ├── ai/
│   │   ├── job_evaluator.py
│   │   └── prompt_templates.py
│   ├── resume_generator/
│   │   ├── resume_builder.py
│   │   ├── template_manager.py
│   │   ├── keyword_optimizer.py
│   │   └── format_converter.py
│   ├── reporting/
│   │   ├── sheets_manager.py
│   │   └── email_notifier.py
│   ├── monitoring/
│   │   └── apply_column_monitor.py
│   └── scheduler/
│       └── job_scheduler.py
├── config/
│   ├── .env.example
│   └── credentials/
├── templates/
├── logs/
├── data/
├── requirements.txt
├── main.py
└── README.md

Configuration Requirements (.env file):

# AI API Configuration
OPENAI_API_KEY=your_openai_key
CLAUDE_API_KEY=your_claude_key

# Google APIs
GOOGLE_DRIVE_CREDENTIALS=path_to_credentials.json
GOOGLE_SHEETS_ID=your_sheet_id
GMAIL_CREDENTIALS=gmail_credentials.json

# Job Search Configuration
LINKEDIN_EMAIL=your_linkedin_email
LINKEDIN_PASSWORD=your_linkedin_password
SEARCH_LOCATIONS=Toronto,ON;Remote;Ontario,Canada
MIN_MATCH_SCORE=85

# Profile Files
LINKEDIN_PDF_ID=google_drive_file_id
SUMMARY_TXT_ID=google_drive_file_id

# Email Notifications
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
RECIPIENT_EMAIL=your_email@gmail.com

# Resume Generation
RESUME_TEMPLATES_FOLDER=path_to_templates
GENERATED_RESUMES_FOLDER=google_drive_folder_id
DEFAULT_RESUME_TEMPLATE=professional_template.docx

Implementation Requirements:
Agent 1 Workflow:

Daily Execution: Run at 6 pm each day.
Job Scraping: Search all target sites for recent postings
No duplicates. Ignore any posting that have been previously analyzed
Profile Analysis: Load and analyze personal profile files
AI Evaluation: Score each job against profile (1-100)
Sheet Population: Add high-scoring jobs (85+) to Google Sheets
Email Notification: Send daily summary

Agent 2 Workflow:

Monitor Apply Column: Check for newly checked boxes hourly
Fetch Job Details: Retrieve full job description and company info
Generate Custom Resume: Use AI to create tailored resume
Quality Check: Ensure factual accuracy while optimizing
Save & Organize: Store in Google Drive with proper naming
Update Status: Mark completion in Google Sheets

Key Features:

Robust Web Scraping: Handle anti-bot measures, retry mechanisms
Comprehensive Logging: Debug and monitoring capabilities
Error Handling: Network issues, API failures, parsing errors
Data Persistence: Avoid re-processing same jobs
Rate Limiting: Respect website terms of service
Resume Customization: Maintain accuracy while optimizing for ATS

Deliverables:

Complete Python application with both agents
Requirements.txt with all dependencies
Detailed README with setup instructions
Example configuration files and templates
Google Sheets template
Comprehensive error handling and logging