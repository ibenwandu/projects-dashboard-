# Indeed-jobs

Automated pipeline: **Indeed search** (by your criteria) → scrape job pages → **score with AI** (Gemini or OpenAI) → report (top N) → **tailored resumes** (.md + .pdf) and job application links.

Same workflow as [job-alert-resume](../job-alert-resume), but **job source is Indeed search** instead of Gmail alerts.

## Search criteria (config)

Edit **`config/indeed_search.json`** to set:

- **keywords** – Title keywords, e.g. `["analyst", "manager"]`
- **locations** – e.g. `["Toronto, ON", "Remote"]`
- **salary_min** – Minimum salary (e.g. `80000`)
- **days_posted** – `1` = last 24h, `3` = last 3 days, `7` = last 7 days (Indeed `fromage`). Use 3 or 7 if you see the same jobs every run; 1 often repeats for 2–3 days.
- **job_types** – e.g. `["Full-time", "Contract", "Permanent"]` (filtered after scrape)
- **max_results_per_search** / **max_jobs_total** – Limits

Language (English) is assumed for Toronto/Canada; Indeed may not expose it as a URL filter.

## Setup

1. **Python 3.10+**, create a venv and install:
   ```bash
   cd Indeed-jobs
   pip install -r requirements.txt
   playwright install chromium
   ```
2. **AI (scoring + resumes):**  
   - **Gemini (default):** In project root create `.env` with `GEMINI_API_KEY` or `GOOGLE_API_KEY`.  
   - **OpenAI:** Set `JAR_AI_PROVIDER=openai` and `OPENAI_API_KEY` in `.env`.
3. **Config:** Reuse or edit `config/scoring-criteria.json`, `config/profile.md`, `config/master-resume.md` (same as job-alert-resume). Copy from job-alert-resume if you already use that project.

## Commands

By default the browser runs **visible** (not headless) to reduce Cloudflare blocks. Use `--headless` for background runs. If you see "Additional Verification Required", complete the check in the browser; the script waits 15s and retries the first page once.

```bash
# Full workflow: Indeed search → scrape → score → report (browser visible)
python run_workflow.py --phase all

# Fetch only (Indeed search + scrape, write output + cache)
python run_workflow.py --phase fetch

# Limit to 10 jobs for a quick test
python run_workflow.py --phase fetch --max-jobs 10

# After reviewing reports/<run_id>/report.md, add Job IDs to config/approved_jobs.txt, then:
python run_workflow.py --phase resumes

# Regenerate PDFs from existing .md resumes
python run_workflow.py --phase pdf

# Scrape-only (no scoring): Indeed search → scrape → markdown in output/
python main.py

# Run browser in background (faster but more likely to hit Cloudflare)
python run_workflow.py --phase fetch --headless
```

**Same jobs every day?** Reports are built from `output/jobs_cache.json`. To get fresh results you must run **`--phase fetch`** or **`--phase all`** (fetch updates the cache). **Already-reported filter:** Job IDs that have been included in any previous report are stored in **`output/reported_job_ids.txt`** and are **excluded** from future score/report runs, so you only see jobs that haven’t been reported before. If all jobs in cache are already reported, the run will tell you to fetch again or clear the file. Use **`--include-reported`** to score and report all jobs in cache (ignore the exclusion list). To start over, delete or edit `output/reported_job_ids.txt`.

## Output

- **output/** – Scraped job markdown files, `jobs_combined.md`, `jobs_cache.json`
- **output/resumes/** – Tailored .md + .pdf per approved job, `job_links.md`
- **reports/<run_id>/** – `report.md` (top N + full ranked list), `top_job_ids.txt`

## File layout

```
Indeed-jobs/
├── main.py              # Indeed search → scrape → output (no scoring)
├── run_workflow.py      # fetch → score → report → resumes
├── config/
│   ├── indeed_search.json   # Search criteria (keywords, locations, salary_min, etc.)
│   ├── scoring-criteria.json
│   ├── profile.md
│   ├── master-resume.md
│   ├── resume-pdf-template.html
│   └── approved_jobs.txt
├── output/
│   ├── jobs_cache.json
│   └── resumes/             # .md + .pdf, job_links.md
├── reports/
└── src/
    ├── config.py
    ├── indeed_search.py    # Build search URLs, scrape result pages for job links
    ├── indeed_scraper.py
    ├── job_cache.py
    ├── link_extractor.py
    ├── ai_client.py
    ├── gemini_client.py
    ├── gemini_scorer.py
    ├── report_generator.py
    ├── resume_tailor.py
    ├── resume_output.py
    ├── profile_loader.py
    └── md_to_pdf.py
```

## Troubleshooting

- **No job URLs found** – Run with `--no-headless` to see the browser. Check `config/indeed_search.json` (keywords, locations). Indeed may change selectors; if so, `src/indeed_search.py` (e.g. `extract_job_urls_from_search_page`) may need updates.
- **Empty title/description** – Indeed job page HTML changes; update selectors in `src/indeed_scraper.py`.
- **AI errors** – Ensure `.env` has `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) for Gemini, or `JAR_AI_PROVIDER=openai` and `OPENAI_API_KEY` for OpenAI.
- **Cloudflare / "Additional Verification Required"** – The script defaults to a **visible browser** (Chrome if installed, anti-detection context, slower pacing) to reduce blocks. Install [Chrome](https://www.google.com/chrome/) for best results. If you use `--headless` and see blocks, run without it. For large runs, try `--max-jobs 25` or run in smaller batches.
