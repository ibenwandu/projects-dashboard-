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
   python run.py full --platforms linkedin glassdoor indeed --profile cs
   ```

## Usage

**Command Structure:**
```bash
python run.py <PHASE> [--platforms PLATFORM ...] [--profile PROFILE] [--max-jobs N] [--top-n N]
```

**Available Phases:** `validate`, `fetch`, `score`, `report`, `tailor`, `full`

**Examples:**

```bash
# Fetch jobs from multiple platforms (note: SPACES between platforms, not commas)
python run.py fetch --platforms linkedin glassdoor indeed --profile cs --max-jobs 25

# Score jobs with AI (uses cached jobs from fetch)
python run.py score --profile cs

# Generate report of top matches
python run.py report --profile cs --top-n 10

# Generate tailored resumes for top jobs
python run.py tailor --profile cs --top-n 10

# Run everything in one command
python run.py full --platforms indeed --profile cs

# Use analyst profile instead of cs
python run.py fetch --platforms linkedin glassdoor --profile analyst --max-jobs 50

# Validate configuration without running pipeline
python run.py validate --profile cs
```

## Architecture

- `core/` — Shared logic (scoring, caching, reporting, deduplication)
- `platforms/` — Platform adapters (LinkedIn, Glassdoor, Indeed)
- `profiles/` — Configuration bundles (CS, Analyst, etc.)
- `output/` — Generated jobs, reports, resumes

See `docs/plans/2025-03-08-job-search-monorepo-design.md` for full design.
