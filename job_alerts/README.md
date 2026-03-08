# Job Alerts Application

A comprehensive job crawling and matching system that automatically scrapes job postings from Indeed and LinkedIn, analyzes them for skill requirements, and matches them against your skills and experience.

## Features

- 🔍 **Multi-Source Crawling**: Automatically scrapes jobs from Indeed and LinkedIn
- 🎯 **Smart Skill Matching**: Analyzes job descriptions and calculates match scores
- 📊 **Database Storage**: Stores all job data in SQLite for easy querying
- 📈 **Statistics & Analytics**: Provides insights about job market trends
- 🚀 **Command Line Interface**: Easy-to-use CLI for all operations
- 📤 **Export Functionality**: Export jobs to CSV for further analysis
- 🧹 **Automatic Cleanup**: Removes old job postings to keep database fresh

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd personal/job_alerts
   ```

2. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your environment (optional):**
   Create a `.env` file with your configuration:
   ```env
   # Optional: Add your specific skills here
   USER_SKILLS=Python,JavaScript,React,Node.js,AWS
   ```

## Quick Start

### 1. Crawl Jobs
Search for jobs using default criteria:
```bash
python main.py crawl
```

Search with custom criteria:
```bash
python main.py crawl --job-titles "Software Engineer" "Full Stack Developer" --locations "Toronto" "Remote" --user-skills Python JavaScript React
```

### 2. Search Jobs
Find jobs matching your skills:
```bash
python main.py search --matching --min-score 0.7
```

Search by specific criteria:
```bash
python main.py search --job-title "Python Developer" --location "Toronto" --limit 20
```

### 3. View Statistics
```bash
python main.py stats
```

### 4. Export Jobs
```bash
python main.py export --filename my_jobs.csv
```

### 5. Cleanup Old Jobs
```bash
python main.py cleanup --days 30
```

## Configuration

### Default Search Criteria
The application comes with pre-configured search criteria in `config.py`:

```python
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
```

### Skills Database
The application includes a comprehensive skills database covering:

- **Programming Languages**: Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust, PHP, Ruby
- **Frameworks**: React, Angular, Vue.js, Node.js, Django, Flask, Express.js, Spring Boot, Laravel
- **Databases**: PostgreSQL, MySQL, MongoDB, Redis, SQLite, Oracle, SQL Server
- **Cloud Platforms**: AWS, Azure, Google Cloud, Heroku, DigitalOcean, Vercel
- **Tools**: Git, Docker, Kubernetes, Jenkins, GitHub Actions, Jira, Confluence
- **Methodologies**: Agile, Scrum, DevOps, CI/CD, TDD, BDD, Microservices

## Usage Examples

### Example 1: Daily Job Search
```bash
# Search for recent software engineering jobs
python main.py crawl --job-titles "Software Engineer" "Developer" --locations "Remote" "Toronto" --date-posted 1d
```

### Example 2: Find High-Match Jobs
```bash
# Find jobs where you match 80% or more of required skills
python main.py search --matching --min-score 0.8 --limit 10
```

### Example 3: Export Specific Jobs
```bash
# Export all Python developer jobs from the last week
python main.py search --job-title "Python" --limit 1000 | python main.py export --filename python_jobs.csv
```

### Example 4: Weekly Cleanup
```bash
# Remove jobs older than 2 weeks
python main.py cleanup --days 14
```

## Database Schema

The application uses SQLite with the following tables:

### Jobs Table
- `id`: Primary key
- `job_id`: Unique job identifier
- `title`: Job title
- `company`: Company name
- `location`: Job location
- `date_posted`: When the job was posted
- `job_description`: Full job description
- `salary`: Salary information (if available)
- `experience_level`: Entry/Mid/Senior level
- `job_type`: Full-time/Part-time/Contract
- `source`: Indeed or LinkedIn
- `url`: Job posting URL
- `skills_required`: JSON array of required skills
- `skills_matched`: JSON array of skills you have
- `match_score`: Percentage match (0.0-1.0)
- `created_at`: When added to database
- `updated_at`: Last update timestamp

### Search Logs Table
- Tracks search operations and results

### Skills Matches Table
- Detailed skill matching information

## Advanced Usage

### Custom Skills Configuration
You can customize the skills database by modifying `config.py`:

```python
SKILLS_DATABASE = {
    "programming_languages": ["Your", "Custom", "Languages"],
    "frameworks": ["Your", "Frameworks"],
    # ... add more categories
}
```

### Scheduled Crawling
Set up a cron job for automatic daily crawling:

```bash
# Add to crontab (crawl daily at 9 AM)
0 9 * * * cd /path/to/job_alerts && python main.py crawl
```

### Integration with Other Tools
Export jobs and analyze with other tools:

```bash
# Export and open in Excel
python main.py export --filename jobs.xlsx && open jobs.xlsx

# Export for data analysis
python main.py export --filename jobs.csv && python analyze_jobs.py
```

## Troubleshooting

### Common Issues

1. **No jobs found**: Check your internet connection and verify the search criteria
2. **Rate limiting**: The application includes delays to avoid being blocked, but you may need to adjust timing
3. **Database errors**: Ensure you have write permissions in the directory

### Logs
Check the log files for detailed information:
- `job_crawler.log`: Main application logs
- `job_alerts.log`: CLI operation logs

## Legal and Ethical Considerations

- **Respect robots.txt**: The application respects website robots.txt files
- **Rate limiting**: Built-in delays prevent overwhelming target websites
- **Terms of Service**: Ensure compliance with Indeed and LinkedIn terms of service
- **Data usage**: Use scraped data responsibly and in accordance with applicable laws

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for educational and personal use. Please respect the terms of service of the websites you're crawling.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Open an issue with detailed information about your problem
