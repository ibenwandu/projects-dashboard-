import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_PATH = "job_database.db"

# Search criteria
DEFAULT_SEARCH_CRITERIA = {
    "job_titles": [
        "Software Engineer",
        "Full Stack Developer", 
        "Backend Developer",
        "Frontend Developer",
        "DevOps Engineer",
        "Data Engineer",
        "Python Developer",
        "React Developer",
        "Node.js Developer"
    ],
    "locations": [
        "Remote",
        "Toronto, ON",
        "Vancouver, BC", 
        "Montreal, QC",
        "Calgary, AB",
        "Ottawa, ON"
    ],
    "date_posted": "7d",  # Last 7 days
    "experience_level": ["Entry Level", "Mid Level", "Senior"]
}

# Indeed configuration
INDEED_BASE_URL = "https://ca.indeed.com"
INDEED_SEARCH_URL = "https://ca.indeed.com/jobs"

# LinkedIn configuration  
LINKEDIN_BASE_URL = "https://www.linkedin.com"
LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs"

# Crawling settings
REQUEST_DELAY = 2  # seconds between requests
MAX_PAGES_PER_SEARCH = 10
MAX_JOBS_PER_PAGE = 25

# User agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
]

# Skills database (your skills for matching)
SKILLS_DATABASE = {
    "programming_languages": [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "PHP", "Ruby"
    ],
    "frameworks": [
        "React", "Angular", "Vue.js", "Node.js", "Django", "Flask", "Express.js", "Spring Boot", "Laravel"
    ],
    "databases": [
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Oracle", "SQL Server"
    ],
    "cloud_platforms": [
        "AWS", "Azure", "Google Cloud", "Heroku", "DigitalOcean", "Vercel"
    ],
    "tools": [
        "Git", "Docker", "Kubernetes", "Jenkins", "GitHub Actions", "Jira", "Confluence"
    ],
    "methodologies": [
        "Agile", "Scrum", "DevOps", "CI/CD", "TDD", "BDD", "Microservices"
    ]
}

# Experience levels mapping
EXPERIENCE_LEVELS = {
    "entry": ["entry level", "junior", "0-2 years", "1-2 years", "new grad", "recent graduate"],
    "mid": ["mid level", "intermediate", "2-5 years", "3-5 years", "mid-level"],
    "senior": ["senior", "lead", "5+ years", "7+ years", "principal", "staff"]
}
























