# Job Search Monorepo

Unified job scraping, AI scoring, and resume tailoring for LinkedIn, Glassdoor, and Indeed.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure:**
   - Copy `.env.example` to `.env` and add your API keys
   - Review `profiles/cs/` configuration

3. **Run full pipeline:**
   ```bash
   python run.py --platforms linkedin,glassdoor --profile cs --phase all
   ```

## Usage

```bash
# Fetch jobs from platforms
python run.py --platforms linkedin,glassdoor,indeed --profile cs --phase fetch --max-jobs 25

# Score jobs with AI
python run.py --profile cs --phase score

# Generate report
python run.py --profile cs --phase report --top-n 10

# Generate tailored resumes
python run.py --profile cs --phase resumes
```

## Architecture

- `core/` — Shared logic (scoring, caching, reporting, deduplication)
- `platforms/` — Platform adapters (LinkedIn, Glassdoor, Indeed)
- `profiles/` — Configuration bundles (CS, Analyst, etc.)
- `output/` — Generated jobs, reports, resumes

See `docs/plans/2025-03-08-job-search-monorepo-design.md` for full design.
