# Indeed-jobs-cs

Job pipeline focused on **Customer Success, Customer Experience (CX), and affiliated roles**. Mirrors [Indeed-jobs](../Indeed-jobs) but uses customer-success–oriented search criteria and scoring.

## What it does

1. **Fetch** — Indeed search (config: `config/indeed_search.json`) for CX, Customer Success, Business Development, etc. → scrape job pages.
2. **Score** — AI (Gemini or OpenAI) scores each job against `config/scoring-criteria.json` (location, salary, role types).
3. **Report** — Top-N match report in `reports/<run_id>/report.md`.
4. **Resumes** — Add approved Job IDs to `config/approved_jobs.txt`, then generate tailored .md + .pdf resumes and `output/resumes/job_links.md`.

## Setup

- Copy `.env.example` to `.env` and set `GEMINI_API_KEY` or `GOOGLE_API_KEY` (or `JAR_AI_PROVIDER=openai` and `OPENAI_API_KEY`).
- `pip install -r requirements.txt`
- `playwright install chromium` (or use Chrome via browser_context).

## Commands

```bash
# Full pipeline: fetch → score → report
python run_workflow.py --phase all

# Fetch only (Indeed search → scrape → output + cache)
python run_workflow.py --phase fetch

# After adding Job IDs to config/approved_jobs.txt: generate resumes + PDFs
python run_workflow.py --phase resumes

# Regenerate PDFs from existing .md in output/resumes/
python run_workflow.py --phase pdf

# Scrape-only (no scoring)
python main.py --max-jobs 25
```

**Verification (Cloudflare):** Indeed sometimes shows "Additional Verification Required". Run without `--headless` so the browser is visible; if you see that page, complete the check. The script will wait 15 seconds and retry the first page once to give you time. If it still fails, try again later or use `--max-jobs 5`.

## Config

- **config/indeed_search.json** — Keywords (e.g. Customer Experience, Customer Success, CX Manager), locations, salary_min, job_types.
- **config/scoring-criteria.json** — Candidate profile, location/salary/role_types weights; tuned for customer success roles.
- **config/approved_jobs.txt** — Job IDs (one per line) for which to generate tailored resumes.

## Output

- **output/** — Job .md files, `jobs_combined.md`, `jobs_cache.json`, **`reported_job_ids.txt`** (IDs already in a report; excluded from future reports).
- **output/resumes/** — Tailored resumes (.md + .pdf), `job_links.md`.
- **reports/<run_id>/** — `report.md`, `top_job_ids.txt`.

**Already-reported filter:** Job IDs in `output/reported_job_ids.txt` are excluded from future score/report runs. Use **`--include-reported`** to score and report all jobs in cache. Delete or edit the file to clear the list.
