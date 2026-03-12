# Glassdoor-jobs

Automated pipeline for **Glassdoor** job search: fetch jobs by criteria → score with AI (Gemini/OpenAI) → report → tailored resumes (.md + .pdf) and job application links.

Same design as [Linkedin-jobs](https://github.com/...) and [Indeed-jobs](https://github.com/...): job source is **Glassdoor search**; the rest (scoring, report, approved jobs, resumes, PDFs) is identical.

## Setup

1. **Python 3.10+** and create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   python -m playwright install chromium
   ```

3. **Config:**
   - Copy `.env.example` to `.env` (or create `.env`) and set:
     - `GEMINI_API_KEY` or `GOOGLE_API_KEY` for AI scoring/resumes (Gemini)
     - Or `JAR_AI_PROVIDER=openai` and `OPENAI_API_KEY` for OpenAI
   - Edit `config/glassdoor_search.json` (keywords, locations, max_jobs_total, job_types).
   - Edit `config/scoring-criteria.json` and `config/profile.md` / `config/master-resume.md` for your profile.

## Commands

```bash
# One-shot: Glassdoor search → scrape → markdown in output/
python main.py

# Full workflow: fetch → score → report
python run_workflow.py --phase all

# After adding Job IDs to config/approved_jobs.txt (from report)
python run_workflow.py --phase resumes

# Regenerate PDFs only from existing .md in output/resumes/
python run_workflow.py --phase pdf

# Limit jobs / run in background
python main.py --max-jobs 10
python run_workflow.py --phase fetch --max-jobs 10 --headless

# Debug (why 0 URLs or blocked pages)
python run_workflow.py --phase fetch --max-jobs 5 --debug
```

## Config files

| File | Purpose |
|------|--------|
| `config/glassdoor_search.json` | Keywords, locations, job_types, max_jobs_total |
| `config/scoring-criteria.json` | Candidate profile and weights for AI scoring |
| `config/profile.md` | Candidate profile text |
| `config/master-resume.md` | Master resume for tailoring |
| `config/approved_jobs.txt` | Job IDs (one per line) to generate resumes for |
| `config/resume-pdf-template.html` | HTML/CSS for PDF layout |

## Output

- **output/** – Scraped job .md files, `jobs_combined.md`, `jobs_cache.json`, `reported_job_ids.txt`
- **output/resumes/** – Tailored .md + .pdf per approved job, `job_links.md`
- **reports/<run_id>/** – `report.md`, `top_job_ids.txt`

## Notes

- **Glassdoor** may show sign-in or verification pages. The scraper uses a stealth browser (Chrome) and skips blocked jobs. Run with visible browser (default) for better success.
- **"Help Us Protect Glassdoor" / Cloudflare:** If you see verification pages, those are detected and skipped (no file is written). Run with the browser visible (don’t use `--headless`), use a smaller batch (e.g. `--max-jobs 5`), and avoid running too often to reduce blocks.
- Job IDs are extracted from listing URLs (e.g. `JV_IC...`). Use the exact ID from the report in `config/approved_jobs.txt`.
- If search returns 0 URLs, run with `--debug` and check that `config/glassdoor_search.json` keywords/locations match what Glassdoor expects; their URL format may change over time.
