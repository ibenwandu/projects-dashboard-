# Quick Start Guide - Job Alerts Application

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run Your First Job Search
```bash
# Search for software engineering jobs
python main.py crawl --job-titles "Software Engineer" "Developer" --locations "Toronto" "Remote"
```

### Step 3: Find Jobs Matching Your Skills
```bash
# Find jobs where you match 70%+ of required skills
python main.py search --matching --min-score 0.7
```

## 📋 Essential Commands

| Command | Description | Example |
|---------|-------------|---------|
| `crawl` | Search for new jobs | `python main.py crawl` |
| `search --matching` | Find jobs matching your skills | `python main.py search --matching --min-score 0.8` |
| `stats` | View database statistics | `python main.py stats` |
| `export` | Export jobs to CSV | `python main.py export --filename my_jobs.csv` |
| `cleanup` | Remove old jobs | `python main.py cleanup --days 30` |

## 🎯 Customize Your Search

### Add Your Skills
Edit `config.py` and add your skills to the `SKILLS_DATABASE`:

```python
# Add your specific skills
USER_SKILLS = ["Python", "JavaScript", "React", "Node.js", "AWS", "Docker"]
```

### Custom Job Titles
```bash
python main.py crawl --job-titles "Data Scientist" "ML Engineer" "Python Developer"
```

### Custom Locations
```bash
python main.py crawl --locations "Vancouver" "Montreal" "Calgary"
```

## 📊 Understanding Results

### Match Score
- **0.0-0.3**: Low match (few skills overlap)
- **0.4-0.6**: Moderate match (some skills overlap)
- **0.7-0.9**: High match (most skills overlap)
- **1.0**: Perfect match (all skills match)

### Job Information
Each job includes:
- **Title & Company**: Job role and employer
- **Location**: Where the job is located
- **Date Posted**: When the job was posted
- **Skills Required**: What skills the job needs
- **Match Score**: How well you match the requirements
- **Source**: Indeed or LinkedIn
- **URL**: Direct link to apply

## 🔄 Daily Workflow

1. **Morning**: Run daily crawl
   ```bash
   python main.py crawl --date-posted 1d
   ```

2. **Review**: Check matching jobs
   ```bash
   python main.py search --matching --min-score 0.7 --limit 20
   ```

3. **Export**: Save interesting jobs
   ```bash
   python main.py export --filename today_jobs.csv
   ```

## 🛠️ Troubleshooting

### No Jobs Found?
- Check your internet connection
- Verify job titles and locations are correct
- Try different search terms

### Rate Limited?
- The app includes delays to avoid being blocked
- Wait a few minutes and try again
- Consider reducing the number of pages crawled

### Database Errors?
- Ensure you have write permissions in the directory
- Check that SQLite is working properly

## 📈 Advanced Usage

### Scheduled Crawling
Set up automatic daily searches:

**Windows (Task Scheduler):**
```cmd
schtasks /create /tn "Job Crawler" /tr "python main.py crawl" /sc daily /st 09:00
```

**Linux/Mac (Cron):**
```bash
# Add to crontab: 0 9 * * * cd /path/to/job_alerts && python main.py crawl
```

### Integration with Other Tools
```bash
# Export and open in Excel
python main.py export --filename jobs.xlsx && start jobs.xlsx

# Filter by company
python main.py search --company "Google" --limit 50
```

## 🎯 Pro Tips

1. **Start Small**: Begin with 1-2 job titles and locations
2. **Use Skills**: Add your specific skills for better matching
3. **Regular Cleanup**: Remove old jobs weekly to keep database fast
4. **Export Regularly**: Save interesting jobs before they expire
5. **Monitor Logs**: Check `job_crawler.log` for any issues

## 📞 Need Help?

1. Check the full `README.md` for detailed documentation
2. Run `python main.py --help` for command options
3. Review log files for error messages
4. Test with `python test_database.py` to verify setup

---

**Happy Job Hunting! 🎉**
