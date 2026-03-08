# File Paths Configuration

## Path Resolution

All file paths in the system are resolved relative to the project root directory:
```
C:\Users\user\projects\personal\recruiter_email_automation\
```

## Key File Locations

### Configuration Files
- `.env` → `C:\Users\user\projects\personal\recruiter_email_automation\.env`
- `credentials.json` → `C:\Users\user\projects\personal\recruiter_email_automation\credentials.json`
- `token.json` → `C:\Users\user\projects\personal\recruiter_email_automation\token.json`

### Data Files
- Resume Template → `C:\Users\user\projects\personal\recruiter_email_automation\data\resume_template.txt`
- LinkedIn PDF → `C:\Users\user\projects\personal\recruiter_email_automation\data\linkedin.pdf`
- Skills Summary → `C:\Users\user\projects\personal\recruiter_email_automation\data\skills_summary.txt`
- Database → `C:\Users\user\projects\personal\recruiter_email_automation\data\processed_emails.db`

### Output Files
- Generated Resumes → `C:\Users\user\projects\personal\recruiter_email_automation\output\resumes\`
- Log Files → `C:\Users\user\projects\personal\recruiter_email_automation\logs\`

## Path Handling

The system uses `os.path.join()` to ensure proper Windows path handling:
- All relative paths are resolved relative to the project root
- Absolute paths in `.env` are respected
- Paths work correctly on Windows with backslashes

## Customizing Paths

You can override default paths in your `.env` file:
```env
RESUME_TEMPLATE_PATH=C:\Users\user\Documents\my_resume.txt
LINKEDIN_PDF_PATH=C:\Users\user\Documents\linkedin.pdf
SKILLS_SUMMARY_PATH=C:\Users\user\Documents\skills.txt
```

Or use relative paths (relative to project root):
```env
RESUME_TEMPLATE_PATH=data/resume_template.txt
LINKEDIN_PDF_PATH=data/linkedin.pdf
SKILLS_SUMMARY_PATH=data/skills_summary.txt
```



