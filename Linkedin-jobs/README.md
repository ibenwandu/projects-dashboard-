# Linkedin-jobs

Automated pipeline: **LinkedIn job search** → scrape job details → score with AI (Gemini or OpenAI) → report (top N matches) → tailored resumes (.md + .pdf) and job application links for approved jobs.

Mirrors the [Indeed-jobs](https://github.com/...) design: job source is **LinkedIn** instead of Indeed; the rest (scoring, report, approved jobs, tailored resumes, PDF, job_links.md) is the same.

## Quick start

1. **Config**
   - Copy or edit `config/linkedin_search.json` (keywords, locations, `days_posted`, `job_types`, `max_jobs_total`).
   - Reuse `config/scoring-criteria.json`, `config/profile.md`, `config/master-resume.md` from job-alert-resume or Indeed-jobs if desired.
   - Add `config/approved_jobs.txt` with LinkedIn Job IDs (one per line) after you run a report.

2. **Environment**
   - `.env` in project root: `GEMINI_API_KEY` or `GOOGLE_API_KEY` (or `JAR_AI_PROVIDER=openai` and `OPENAI_API_KEY` for ChatGPT).
   - Optional: `GEMINI_MODEL`, `OPENAI_MODEL`, `JAR_TOP_N_JOBS`.

3. **Install**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
   For better anti-detection, use Chrome: install Chrome and the workflow will prefer it when available.

4. **Run**
   ```bash
   # Full pipeline: LinkedIn search -> scrape -> score -> report
   python run_workflow.py --phase all

   # Or step by step
   python run_workflow.py --phase fetch --max-jobs 25
   python run_workflow.py --phase score
   python run_workflow.py --phase report
   # Edit config/approved_jobs.txt with Job IDs from reports/<run_id>/report.md
   python run_workflow.py --phase resumes
   ```

## Commands

| Command | Description |
|--------|-------------|
| `python run_workflow.py --phase all` | Fetch from LinkedIn, score, and generate report (default --max-jobs 25) |
| `python run_workflow.py --phase fetch` | LinkedIn search + scrape only; writes `output/jobs_cache.json` and markdown |
| `python run_workflow.py --phase score` | Score jobs in cache with AI |
| `python run_workflow.py --phase report` | Write top-N and full ranked list to `reports/<run_id>/` |
| `python run_workflow.py --phase resumes` | Generate tailored .md + .pdf + `output/resumes/job_links.md` for IDs in `config/approved_jobs.txt` |
| `python run_workflow.py --phase pdf` | Regenerate PDFs from existing .md in `output/resumes/` |
| `python main.py` | LinkedIn search -> scrape -> output markdown only (no scoring) |

**Options**

- `--max-jobs N` — Limit jobs to fetch/scrape (default 25).
- `--headless` — Run browser in background (may increase auth/login prompts from LinkedIn).
- `--no-filter-job-type` — Do not filter by `job_types` in `config/linkedin_search.json`.
- `--top-n N` — Number of top jobs in the report (default from env or 10).
- `--run-id ID` — Report folder name (default: timestamp).
- `--include-reported` — Include jobs that were already in a previous report (default: exclude them).

**Already-reported filter:** Job IDs in `output/reported_job_ids.txt` are excluded from future score/report runs so the same jobs do not keep appearing. Delete or edit that file to clear the list.

## Config files

| File | Purpose |
|------|--------|
| `config/linkedin_search.json` | Keywords, locations, `days_posted` (1=24h, 7=week, 30=month), `job_types`, `max_jobs_total` |
| `config/scoring-criteria.json` | Candidate profile and weights for AI scoring |
| `config/profile.md` | Candidate profile text (fallback for master resume) |
| `config/master-resume.md` | Master resume for tailoring |
| `config/approved_jobs.txt` | LinkedIn Job IDs (numeric) for resume generation, one per line |
| `config/resume-pdf-template.html` | HTML/CSS template for PDF output |

## Output

- **output/** — `jobs_cache.json`, per-job markdown, `jobs_combined.md`, `reported_job_ids.txt` (IDs already reported; excluded from future reports).
- **output/resumes/** — Tailored .md and .pdf per approved job, plus `job_links.md` (table + plain URLs).
- **reports/<run_id>/** — `report.md` (top N + full list), `top_job_ids.txt`.

## Job IDs

LinkedIn job URLs look like `https://www.linkedin.com/jobs/view/3847291847`. The **Job ID** is the numeric part (e.g. `3847291847`). The report lists these as "Job ID (for approval)"; add them to `config/approved_jobs.txt` for resume generation.

## Notes

- **LinkedIn and login:** LinkedIn may show sign-in or verification for unauthenticated scraping. The scraper detects auth/login blocks and marks those jobs as blocked; they are skipped from cache and output. Running with a visible browser (default) and reasonable pacing (delays between pages) helps. For full access you may need to sign in manually in the browser (future enhancement).
- **Selectors:** LinkedIn’s HTML changes often. If title, company, or description are missing, update selectors in `src/linkedin_scraper.py`.
- **AI:** Same as Indeed-jobs — Gemini by default, or OpenAI when `JAR_AI_PROVIDER=openai` and `OPENAI_API_KEY` are set.

## Project layout

```
Linkedin-jobs/
├── main.py
├── run_workflow.py
├── config/
│   ├── linkedin_search.json
│   ├── scoring-criteria.json
│   ├── profile.md
│   ├── master-resume.md
│   ├── approved_jobs.txt
│   └── resume-pdf-template.html
├── output/
│   ├── jobs_cache.json
│   ├── *.md
│   └── resumes/          # .md + .pdf per job, job_links.md
├── reports/
└── src/
    ├── config.py
    ├── linkedin_search.py   # Build search URLs, get job links from search pages
    ├── linkedin_scraper.py  # Scrape job view pages -> JobDetails
    ├── link_extractor.py    # Job ID from LinkedIn view URL
    ├── browser_context.py
    ├── job_cache.py
    ├── resume_output.py
    ├── profile_loader.py
    ├── ai_client.py
    ├── gemini_client.py
    ├── gemini_scorer.py
    ├── report_generator.py
    ├── resume_tailor.py
    └── md_to_pdf.py
```
