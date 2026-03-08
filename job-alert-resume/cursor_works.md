# Cursor Works – Job Alert Resume Pipeline

**Purpose:** Give future Cursor sessions context on this project: what was built, why, and what was fixed during development.

---

## Project overview

**Goal:** Automate the process of reading Indeed job alerts from Gmail, opening each job link, extracting job details, **scoring jobs against a candidate profile with Gemini AI**, generating actionable reports (e.g. top 10 matches), and producing **customized resumes** for user-approved jobs using a master resume template.

**Two entrypoints:**
- **`main.py`** – Gmail → extract links → scrape → write markdown (no scoring).
- **`run_workflow.py`** – Full workflow: fetch → **score with Gemini** (using `config/scoring-criteria.json`) → **report** (top N + full list) → user approves via **`config/approved_jobs.txt`** → **tailored resumes** (.md + .pdf using **`config/resume-pdf-template.html`**) and **`job_links.md`** (apply links) in `output/resumes/`. Can be **scheduled twice daily (7 AM and 7 PM EST)** via `run_workflow_scheduled.bat` and Windows Task Scheduler (see `schedule_setup.md`).

---

## Session context (what we did)

1. **Initial build** – User described receiving Indeed job alerts in Gmail (Primary and Updates), opening each alert to view job descriptions for resume customization. We designed and implemented a full pipeline.
2. **First run** – Gmail auth worked, but "No Indeed job URLs found" when using Gmail; `--skip-gmail --urls-file urls.txt` failed with `FileNotFoundError` because `urls.txt` did not exist.
3. **Fixes for URLs and debugging:**
   - **urls_file:** Resolve path from project root; clear error if file missing; support `#` comments in urls file; added sample `urls.txt` with two Indeed viewjob URLs so the URL-only path works without Gmail.
   - **--debug:** Added `--debug` to print per-email body length and number of Indeed URLs extracted, to diagnose why Gmail returned 0 URLs.
4. **Gmail still 0 URLs** – Debug showed 10 emails with large bodies but 0 Indeed URLs. Cause: Indeed emails use **tracking/redirect links** (e.g. `indeed.com/rc/clk?jk=...`) and sometimes **Gmail link wrapping** (`google.com/url?q=...`), not direct `viewjob?jk=...` links.
5. **Link extractor fixes (final):**
   - Support **any Indeed URL that contains `jk=`** (job key): detect e.g. `/rc/clk?jk=...`, extract `jk`, and emit canonical `https://ca.indeed.com/viewjob?jk=...`.
   - **Unwrap Gmail redirects:** When an `<a href>` points to `google.com/url?q=ENCODED_URL`, parse `q` and run extraction on the decoded inner URL so wrapped Indeed links are found.
6. **Outcome:** With these changes, at least one of the user’s job alert emails (e.g. email 10 in "in:updates") yielded 21 Indeed URLs and the pipeline completed (scrape + output).

7. **Full automated workflow (second session):** User asked for: (1) fetch job alerts from Gmail, (2) analyze with Gemini AI, (3) score against a candidate profile in `config/` (scoring-criteria.json), (4) generate actionable reports (e.g. top 10) using that criteria, (5) user reviews and approves selection, (6) workflow creates customized resumes for approved list using master resume in config, (7) schedule twice daily (7 AM and 7 PM EST). Implemented: **config/** (scoring-criteria.json, profile.md, master-resume.md, approved_jobs.txt), **Gemini** (gemini_client.py, gemini_scorer.py), **job cache** (job_cache.py) so scrape output is reused for scoring and resumes, **report_generator.py** (top N + full ranked list), **resume_tailor.py** (load approved IDs, generate tailored resume per job via Gemini), **run_workflow.py** (phases: fetch, score, report, resumes, all), **run_workflow_scheduled.bat** and **schedule_setup.md** for 7 AM/7 PM EST with Task Scheduler.

8. **Gemini import error:** Report showed all scores 0 and reasoning: `[Gemini error: cannot import name 'genai' from 'google' (unknown location)]`. Cause: code expected **google-genai** (`from google import genai`); user’s environment had **google-generativeai** (legacy SDK) or a conflicting `google` namespace. **Fix:** In `src/gemini_client.py`, try new SDK first, then **fallback to legacy** `google.generativeai` (`genai.configure`, `GenerativeModel(...).generate_content`). Added `google-generativeai` to requirements so either package works.

9. **API key source:** User clarified they reuse the same Google API key from their **Trade-Alerts** program (Render.com env vars) and saved it in job-alert-resume’s `.env`. Code already supports **`GOOGLE_API_KEY`** (and `GEMINI_API_KEY`); no change needed.

10. **Task Scheduler password error:** When saving the scheduled task, user got “User account restriction error. … blank passwords not allowed, or policy restriction”. Cause: they had selected **“Run whether user is logged on or not”**, which requires a stored Windows password; blank passwords are not allowed. **Fix:** In **schedule_setup.md** we now recommend **“Run only when user is logged on”** so no password is required. Task still runs at 7 AM and 7 PM when the user is logged in.

11. **Task and sleep:** User asked if the task runs when the system is asleep. **Answer:** No. Scheduled tasks run only when Windows is **awake**. If the PC is asleep at 7 AM/7 PM, that run is skipped. Optional: in Task Scheduler → task → **Conditions** → “Wake the computer to run this task” (trade-offs: battery, hardware-dependent).

12. **Next steps:** Documented for user: (1) ensure GEMINI_API_KEY (or GOOGLE_API_KEY) and optionally GEMINI_MODEL in .env; (2) run `python run_workflow.py --phase all` once to verify; (3) review `reports/<run_id>/report.md`, add approved Job IDs to `config/approved_jobs.txt`; (4) run `python run_workflow.py --phase resumes` to generate tailored resumes.

13. **Gemini 404 / OpenAI option:** Report showed `[Gemini error: 404 This model models/gemini-2.0-flash is no longer available to new users ...]`. User’s Trade-Alerts uses `GEMINI_MODEL=gemini-1.5-flash` on Render. **Fixes:** (a) **Default model** changed from `gemini-2.0-flash` to **`gemini-1.5-flash`** in `src/config.py`. (b) Config now reads **`GEMINI_MODEL`** (and `JAR_GEMINI_MODEL`) from env so the same .env from Trade-Alerts works. (c) **OpenAI (ChatGPT) support added:** New **`src/ai_client.py`** as single entrypoint for AI text generation; if **`JAR_AI_PROVIDER=openai`** and **`OPENAI_API_KEY`** are set, scoring and resume generation use OpenAI instead of Gemini (default model `gpt-4o-mini`, overridable with `OPENAI_MODEL`). **gemini_scorer** and **resume_tailor** now import **generate** and **parse_score_and_reasoning** from **ai_client** (which delegates to gemini_client when provider is gemini). **requirements.txt** includes **openai**; README updated with AI provider and model notes.

14. **Job application links file:** User asked for a file with links to the jobs so they can use them to apply. **Implementation:** In **`src/resume_tailor.py`**, after writing tailored .md resumes we call **`_write_job_links_file()`**, which writes **`output/resumes/job_links.md`** with (1) a markdown table: #, job title, company, Apply link; (2) a “Plain URLs” section for copy-paste. **run_workflow.py** prints “Job application links: output/resumes/job_links.md” after a successful resume run.

15. **Resume .md → submission-ready .pdf:** User asked to convert the .md resume files into submission-ready .pdf using exactly the same format as the template they provided (image: centered name, contact on one line, underlined section titles, letter layout). **Implementation:** (a) **`config/resume-pdf-template.html`** – HTML + CSS template: centered h1 (name, uppercase), optional contact-block (one line with ` | `), underlined h2 (section titles), letter size, 0.6 in margins, Calibri/Segoe UI. (b) **`src/md_to_pdf.py`** – strip ` ```markdown ... ``` ` fence from .md; convert markdown to HTML (`markdown` package); if first h2 is “Contact Information” followed by ul, replace with single-line block; wrap body in template’s `{{CONTENT}}`; use **Playwright** to render and print to PDF (Letter, 0.6 in margins). (c) **Integration:** **`write_tailored_resumes()`** in resume_tailor calls **`convert_resume_mds_to_pdfs(resumes_dir=out_dir)** after writing .md and job_links.md, so each run of **`--phase resumes`** produces both .md and .pdf in `output/resumes/` (same base name). (d) **`--phase pdf`** added to **run_workflow.py** to regenerate PDFs only from existing .md files (e.g. after editing the template). **requirements.txt**: **markdown>=3.5.0**. README updated: PDF output, template path, `--phase pdf`.

---

## Implementation summary

| Component | Location | Notes |
|-----------|----------|--------|
| **Config** | `src/config.py` | Gmail query, max messages, paths (`credentials.json`, `token.json`, `output/`), scopes. |
| **Gmail** | `src/gmail_fetcher.py` | OAuth2 via `credentials.json` + `token.json`; list messages by query, fetch body (HTML/plain); decode base64. |
| **Link extraction** | `src/link_extractor.py` | Parse email HTML/text; find direct `viewjob` URLs and **any Indeed URL with `jk=`**; **unwrap `google.com/url?q=...`**; dedupe by `jk`; output canonical viewjob URLs. |
| **Indeed scraper** | `src/indeed_scraper.py` | Playwright (Chromium); one page per URL; selectors for title, company, location, salary, description, skills. Indeed changes DOM often—selectors may need updates. |
| **Output** | `src/resume_output.py` | One `.md` per job (title, company, location, salary, URL, skills, full description) + `jobs_combined.md`. |
| **CLI** | `main.py` | Orchestrates: collect URLs (Gmail or `--urls-file`) → scrape → write output. Args: `--gmail-query`, `--max-emails`, `--max-jobs`, `--urls-file`, `--skip-gmail`, `--debug`, `--no-headless`, `--output-dir`. |
| **Config** | `config/` | `scoring-criteria.json` (candidate + weights), `profile.md` (master resume), `master-resume.md` (optional), `approved_jobs.txt` (Job IDs for resume generation). |
| **Job cache** | `src/job_cache.py` | Save/load scraped jobs as JSON (`output/jobs_cache.json`) for scoring and resume steps. |
| **AI (unified)** | `src/ai_client.py` | Single entrypoint: **generate()** and **parse_score_and_reasoning()**. Uses **Gemini** (default) or **OpenAI** when `JAR_AI_PROVIDER=openai` and `OPENAI_API_KEY` set. |
| **Gemini** | `src/gemini_client.py` | Gemini API (new + legacy SDK fallback); called by ai_client when provider is gemini. Supports `GEMINI_API_KEY` or `GOOGLE_API_KEY`; default model `gemini-1.5-flash` (env: `GEMINI_MODEL` / `JAR_GEMINI_MODEL`). |
| **Scoring** | `src/gemini_scorer.py` | Score job vs candidate (0–100 + reasoning) via **ai_client.generate()**. |
| **Report** | `src/report_generator.py` | Top N + full ranked list in `reports/<run_id>/report.md` and `top_job_ids.txt`. |
| **Resume tailor** | `src/resume_tailor.py` | Read `approved_jobs.txt`, generate tailored .md per job via **ai_client.generate()** → `output/resumes/`; write **job_links.md** (table + plain URLs); call **md_to_pdf.convert_resume_mds_to_pdfs()** to produce .pdf for each .md. |
| **MD → PDF** | `src/md_to_pdf.py` | Strip markdown fence, MD→HTML, optional contact-oneline, wrap in **config/resume-pdf-template.html**, Playwright PDF. **convert_resume_mds_to_pdfs()** for all .md in resumes dir (skips job_links.md). |
| **PDF template** | `config/resume-pdf-template.html` | HTML + CSS: centered name (h1), contact-block, underlined h2, letter, 0.6 in margins. User can edit for exact format. |
| **Workflow** | `run_workflow.py` | Phases: `fetch`, `score`/`report`, `resumes` (tailored .md + job_links.md + .pdf), **`pdf`** (reconvert existing .md to .pdf only), `all`. Schedule via `run_workflow_scheduled.bat` at 7 AM/7 PM EST (see `schedule_setup.md`). |

---

## Fixes and where they live

- **urls_file path and missing file:** `main.py` – resolve `urls_file` with `PROJECT_ROOT` if relative; print helpful message if file not found; strip `#` comments when reading URLs.
- **Sample urls.txt:** Project root `urls.txt` – two example Indeed viewjob URLs so `--skip-gmail --urls-file urls.txt` works out of the box.
- **--debug:** `main.py` – when using Gmail, print per-email `body_len` and `indeed_urls`, and total unique URLs; hint to use `--debug` when 0 URLs found.
- **Indeed tracking/redirect links:** `src/link_extractor.py` – `INDEED_ANY_JK_PATTERN`; `_job_key_from_any_url()`; `_canonical_viewjob_url()`; in `add_url()` handle non-viewjob Indeed URLs by extracting `jk` and adding canonical URL.
- **Gmail link unwrapping:** `src/link_extractor.py` – `_unwrap_redirect_href()` using `parse_qs`/`unquote` on `q`/`url`; in HTML extraction, run `add_url()` on each unwrapped link so wrapped Indeed URLs are found.
- **Gemini import (genai from google):** `src/gemini_client.py` – try new SDK `from google import genai` first; on `ImportError`/`AttributeError`, fallback to legacy `import google.generativeai as genai` with `GenerativeModel(model_name).generate_content(prompt)`. Requirements include both `google-genai` and `google-generativeai`.
- **Task Scheduler without password:** `schedule_setup.md` – recommend **“Run only when user is logged on”** so no Windows password is required; document that “Run whether user is logged on or not” causes “User account restriction” with blank password.
- **Gemini 404 (model no longer available):** `src/config.py` – default model changed from `gemini-2.0-flash` to **`gemini-1.5-flash`**; read **`GEMINI_MODEL`** (and `JAR_GEMINI_MODEL`) from env for Trade-Alerts .env compatibility.
- **OpenAI (ChatGPT) support:** `src/ai_client.py` – new module; **generate()** and **parse_score_and_reasoning()**; when `JAR_AI_PROVIDER=openai` and `OPENAI_API_KEY` set, call OpenAI API (`openai` package); else delegate to `gemini_client.generate()`. **gemini_scorer** and **resume_tailor** import from **ai_client**. Config: `JAR_AI_PROVIDER`, `OPENAI_MODEL` (default `gpt-4o-mini`). Requirements: `openai>=1.0.0`.
- **Job application links:** `src/resume_tailor.py` – **`_write_job_links_file()`** writes **`output/resumes/job_links.md`** (table: #, title, company, Apply link; plus plain URLs list) after writing tailored .md files.
- **Resume .md → .pdf:** **`config/resume-pdf-template.html`** – user-editable HTML/CSS for PDF layout (centered name, underlined sections, letter). **`src/md_to_pdf.py`** – **`md_file_to_pdf()`**, **`convert_resume_mds_to_pdfs()`**; strip markdown fence, MD→HTML (markdown package), contact-oneline for first “Contact Information” list, inject into template, Playwright `page.pdf()`. **resume_tailor** calls **convert_resume_mds_to_pdfs()** after writing .md so **`--phase resumes`** outputs .md and .pdf. **`--phase pdf`** in run_workflow regenerates PDFs only. Requirements: **markdown>=3.5.0**.

---

## Common commands

```bash
# Original pipeline (Gmail → scrape → output only)
python main.py

# Full automated workflow (fetch → score → report)
python run_workflow.py --phase all

# After approving jobs in config/approved_jobs.txt (generates .md + .pdf + job_links.md)
python run_workflow.py --phase resumes

# Regenerate only PDFs from existing .md (e.g. after editing config/resume-pdf-template.html)
python run_workflow.py --phase pdf

# Limit scope for testing
python main.py --gmail-query "in:updates" --max-emails 10 --max-jobs 10

# See how many emails and URLs per email (diagnose 0 URLs)
python main.py --gmail-query "in:updates" --max-emails 10 --debug

# Scrape from file only (no Gmail)
python main.py --skip-gmail --urls-file urls.txt

# Show browser during scrape
python main.py --no-headless
```

---

## Troubleshooting (for future sessions)

- **"No Indeed job URLs found"** – Run with `--debug`. If emails have bodies but `indeed_urls=0`, link format may have changed (new redirect domain, new param names). Inspect raw `href` from one Indeed alert or add temporary dump of first link per email.
- **Empty title/description/skills in output** – Indeed’s HTML structure changes; update selectors in `src/indeed_scraper.py` (e.g. via DevTools on a live job page).
- **urls.txt not found** – Path is resolved from project root; run from `job-alert-resume` or pass absolute path to `--urls-file`.
- **Gmail auth** – First run opens browser for consent; `token.json` is created. If token is revoked, delete `token.json` and run again to re-auth.
- **"cannot import name 'genai' from 'google'"** – Use legacy Gemini SDK: `pip install google-generativeai`. Code in `gemini_client.py` falls back to it automatically.
- **"models/gemini-2.0-flash is no longer available" (404)** – Default is now `gemini-1.5-flash`. Set `GEMINI_MODEL=gemini-1.5-flash` (or another current model) in `.env` if needed.
- **Task Scheduler "User account restriction" / blank password** – In task properties, select **“Run only when user is logged on”** instead of “Run whether user is logged on or not”.
- **Use ChatGPT instead of Gemini** – In `.env` set `JAR_AI_PROVIDER=openai` and `OPENAI_API_KEY=sk-...`; optionally `OPENAI_MODEL=gpt-4o-mini` or `gpt-4o`. Install: `pip install openai`.
- **PDF not generated / wrong layout** – Edit **`config/resume-pdf-template.html`** (CSS and structure), then run **`python run_workflow.py --phase pdf`** to regenerate. Ensure **`markdown`** is installed: `pip install markdown`.

---

## File layout (reference)

```
job-alert-resume/
├── main.py                  # Gmail → scrape → output (no scoring)
├── run_workflow.py          # Full workflow: fetch → score → report → resumes
├── run_workflow_scheduled.bat
├── schedule_setup.md        # 7 AM / 7 PM EST Task Scheduler setup
├── credentials.json
├── token.json
├── urls.txt
├── cursor_works.md
├── README.md
├── config/
│   ├── scoring-criteria.json
│   ├── profile.md
│   ├── master-resume.md
│   ├── resume-pdf-template.html   # PDF layout (edit for format)
│   └── approved_jobs.txt
├── output/
│   ├── jobs_cache.json
│   ├── *.md
│   └── resumes/                   # .md + .pdf per job, job_links.md
├── reports/
└── src/
    ├── config.py          # + JAR_AI_PROVIDER, GEMINI_MODEL, OPENAI_MODEL
    ├── ai_client.py       # Unified AI: generate(), parse_score_and_reasoning(); Gemini or OpenAI
    ├── gemini_client.py    # Gemini (new + legacy SDK fallback)
    ├── gmail_fetcher.py
    ├── link_extractor.py
    ├── indeed_scraper.py
    ├── resume_output.py
    ├── job_cache.py
    ├── profile_loader.py
    ├── gemini_scorer.py   # Uses ai_client
    ├── report_generator.py
    ├── resume_tailor.py   # Uses ai_client; writes job_links.md; triggers PDF conversion
    └── md_to_pdf.py       # MD → HTML (template) → PDF via Playwright
```

---

### 16. No report when scheduled task ran at 7 AM

- **Observation:** No report folder for 7 AM (e.g. no `reports/2026-03-02_0700/`), while manual or other runs (e.g. 12:20 AM) produced reports.
- **Possible causes:** (1) Task did not run (PC asleep; scheduled tasks run only when Windows is awake). (2) Task ran but working directory or env was wrong so `.env` was not loaded and scoring failed. (3) Task ran but Python crashed (e.g. Playwright/import) with no visible error because the window closes.
- **Fixes:** (1) **Load `.env` from project root** in `src/config.py` via `load_dotenv(PROJECT_ROOT / ".env")` so the scheduled task always finds the API key even if "Start in" or cwd is wrong. (2) **Run log:** `run_workflow_scheduled.bat` now appends each run to **`output/workflow_run.log`** (timestamp, full Python stdout/stderr, exit code). Check this file after a run to see if the task ran and what failed. (3) **Docs:** `schedule_setup.md` updated with "When no report appears" and reminder to check `workflow_run.log` and "Start in".

### 17. Related project: Indeed-jobs (Indeed search as job source)

- **User ask:** Create a similar program called **Indeed-jobs** that extracts jobs from **Indeed search** (not Gmail) with criteria: salary > 80,000; job type = Full-time/Contract/Permanent; date posted = Last 24 hours; location = Toronto, ON / Remote; job language = English; title = *analyst/*manager. **Rest of pipeline** (scoring, report, approved jobs, tailored resumes, .pdf, job_links.md) should mirror job-alert-resume.
- **Plan:** New project **`Indeed-jobs`** (sibling to `job-alert-resume`, under `personal/`) with (1) different **job source**: build Indeed.ca search URLs from config and scrape search result pages to collect job links, then reuse same scrape → cache → score → report → resumes flow; (2) no Gmail; (3) same config shape (scoring-criteria, profile, master-resume, approved_jobs, resume-pdf-template).
- **Implementation:**
  - **Location:** `personal/Indeed-jobs/` (same level as `job-alert-resume`).
  - **Config:** `config/indeed_search.json` — keywords (`["analyst", "manager"]`), locations (`["Toronto, ON", "Remote"]`), `salary_min` (80000), `days_posted` (1), `job_types`, `max_results_per_search`, `max_jobs_total`. Job type/language applied in URL where supported; job_types filter also applied after scrape.
  - **New module:** `src/indeed_search.py` — `build_search_urls()` from config; `get_search_result_job_urls()` uses Playwright to open search URL(s), paginate (`start=0,10,20...`), extract job links (data-jk / href with jk=), dedupe, return list of viewjob URLs. `filter_jobs_by_criteria()` filters JobDetails by job_types after scrape.
  - **Rest mirrored:** `src/` has config (no Gmail), indeed_scraper, job_cache, link_extractor (minimal: job_key_from_url), resume_output, ai_client, gemini_client, gemini_scorer, report_generator, profile_loader, resume_tailor, md_to_pdf. Same `run_workflow.py` phases: fetch (Indeed search → scrape → cache + markdown), score, report, resumes, pdf, all. `main.py` = Indeed search → scrape → output only.
  - Config files (scoring-criteria, profile, master-resume, resume-pdf-template, approved_jobs) copied/adapted from job-alert-resume so user can reuse same profile.
- **Cloudflare blocking:** User reported most extraction attempts blocked (“Additional Verification Required”); output folder showed many `XX_Additional_Verification_Required_company.md` (1 KB) and only a few real job files.
- **Fixes for Cloudflare / successful runs:**
  1. **Stealth browser context** — New **`src/browser_context.py`**: use **Chrome** when available (`channel="chrome"`) instead of Chromium; **context options**: viewport 1920×1080, locale en-CA, timezone America/Toronto, realistic Accept-Language and Sec-Ch-Ua headers; **init script** to hide `navigator.webdriver` and add minimal `window.chrome`; launch args `--disable-blink-features=AutomationControlled`. Both Indeed search and job-detail scraping use this context.
  2. **Block detection** — In `indeed_scraper.py`: after each job page load, check content for strings like "additional verification required", "cloudflare", "checking your browser"; if found, set job title to `[Blocked: Cloudflare]` and do not use scraped content. **`is_blocked_job(job)`** helper to identify these. Blocked jobs are **not** saved to cache or written to output (filtered in `main.py` and `run_workflow.py` before `save_jobs_cache` / `write_job_files`). **`resume_output.py`**: `_is_blocked()` skips writing files for blocked jobs; `write_combined_markdown` excludes them. User sees “Skipped N job(s) (Cloudflare/timeout).” instead of many placeholder files.
  3. **Slower pacing** — Delay between job pages: **3–5 s** (3 s base + up to 2 s jitter) instead of 1.2 s; search result pages: 2.5 s wait after load. Reduces rate and helps avoid blocks.
  4. **Default visible browser** — Successful run used **visible browser** (`--no-headless`). We made **visible the default**: removed `--no-headless`, added **`--headless`** as opt-in (run in background). Default `headless=False` in `main.py` and `run_workflow.py` so `python run_workflow.py --phase fetch` opens Chrome visibly by default; use `--headless` only when user wants background (may increase blocks).
  5. **Default batch size 25** — User asked for “larger batch, 25”. Set **`--max-jobs` default to 25** in both `main.py` and `run_workflow.py` so a normal run fetches/scrapes up to 25 jobs without passing the flag.
- **Outcome:** Run with `python run_workflow.py --phase fetch --max-jobs 10 --no-headless` (later: visible default, so just `--phase fetch --max-jobs 10`) produced 10/10 jobs scraped, no “Skipped” message; output had 10 real job .md files plus jobs_cache.json and jobs_combined.md. User confirmed success; we then set defaults so future runs use visible browser and batch 25 by default.
- **Where it lives:** All of the above is in **`personal/Indeed-jobs/`**, not in job-alert-resume. job-alert-resume is unchanged; Indeed-jobs is a separate codebase that reuses the same pipeline design and config file shapes.

### 18. Related project: Linkedin-jobs (LinkedIn as job source)

- **User ask:** Build a program **Linkedin-jobs** to mirror **Indeed-jobs**, with the only difference that jobs are extracted from **LinkedIn** instead of Indeed.
- **Plan:** New project **`personal/Linkedin-jobs/`** (sibling to job-alert-resume and Indeed-jobs): (1) **Job source:** LinkedIn job search (config-driven keywords, locations, date posted); build search URLs, scrape search result pages for job links, then scrape each job view page for details. (2) **Same pipeline** as Indeed-jobs: fetch → score (AI) → report → user approves via `approved_jobs.txt` → tailored resumes (.md + .pdf) + `job_links.md`. (3) Same config shape: scoring-criteria, profile, master-resume, approved_jobs, resume-pdf-template; add **`config/linkedin_search.json`** for search criteria.
- **Implementation:**
  - **Location:** `personal/Linkedin-jobs/`.
  - **Config:** `config/linkedin_search.json` — keywords, locations, `days_posted` (1=24h, 7=week, 30=month), `job_types`, `max_results_per_search`, `max_jobs_total`. Job IDs are **numeric** (from `/jobs/view/1234567890`).
  - **New/specific modules:** **`src/linkedin_search.py`** — `build_search_urls()` (LinkedIn URL format with `keywords`, `location`, `f_TPR`); `get_search_result_job_urls()` uses Playwright, pagination `start=0,25,50...`, scrolls to lazy-load job cards, extracts job view URLs; `filter_jobs_by_criteria()` by job_types. **`src/linkedin_scraper.py`** — same `JobDetails` dataclass as Indeed; selectors for title, company, location, salary, job type, description, skills; blocked-page detection; **`src/link_extractor.py`** — `job_key_from_url()` for LinkedIn (extract numeric ID from `/jobs/view/ID` and from query `currentJobId=`).
  - **Rest mirrored:** `src/` has config, browser_context, job_cache, resume_output, profile_loader, ai_client, gemini_client, gemini_scorer, report_generator, resume_tailor, md_to_pdf. Same `run_workflow.py` phases: fetch, score, report, resumes, pdf, all. `main.py` = LinkedIn search → scrape → output only. Config files copied from Indeed-jobs so user can reuse same profile.
- **Fixes applied during development:**
  1. **Only 1 job URL found from search:** (a) LinkedIn lazy-loads job cards — added **`_scroll_jobs_list()`** after page load to scroll and trigger loading of more cards. (b) Job IDs not only in `<a href="/jobs/view/ID">` but in page URL (`currentJobId=`), in HTML as `currentJobId=123`, `"jobPostingId":123`, `urn:li:jobPosting:123`, etc. — **`link_extractor.job_key_from_url()`** extended to read `currentJobId` from query string; **`extract_job_urls_from_search_page()`** now also regex-scans full HTML for these patterns and adds **`page.url()`**’s currentJobId so the single ID in the address bar is included. (c) Longer wait after scroll and **`wait_for_load_state("networkidle")`** so list finishes loading. **Result:** With **`--debug`**, search page reported 60 job URLs; 10 used when `--max-jobs 10`.
  2. **All job pages “Skipped (auth/timeout)”:** Blocked-page check used **`"join linkedin"`** in `BLOCKED_PAGE_MARKERS`. That phrase appears in the **footer/sidebar on every LinkedIn page** when not logged in, so every real job page was wrongly treated as blocked. **Fix:** Removed **`"join linkedin"`** from `BLOCKED_PAGE_MARKERS` in **`src/linkedin_scraper.py`**. Block only on strong signals: `authwall`, `auth-wall`, `additional verification`, `checking your browser`, etc. Title-based block still uses “sign in” / “log in” in **page title** only (not in body), so nav “Sign in” does not trigger block.
  3. **Empty job descriptions (JDs) in output:** (a) **Bug:** **`_query_one()`** in linkedin_scraper returned text only when `len(text) < 500`. Job descriptions are long, so description was always rejected. **Fix:** Added **`max_len`** parameter (default 500); for description use **`max_len=0`** (no limit). (b) **Selectors:** Added more description fallbacks (e.g. `.jobs-description-content__content`, `.jobs-description-details`, `.jobs-box__body`, `[class*='jobs-description']`). (c) **Show more:** LinkedIn often truncates with “Show more”; added **`_click_show_more()`** (aria-label, `.inline-show-more-text__button`, `get_by_role("button", name="Show more")`) and **`_scroll_to_description()`** so full text is in DOM before extraction. (d) Skills fallback includes `.jobs-box__body li`. **Result:** Output .md files now contain full job description text; salary/skills may still be empty if LinkedIn’s DOM for those differs.
  4. **Debugging:** Added **`--debug`** to **`run_workflow.py`** and passed through to **`get_search_result_job_urls()`** and **`scrape_jobs_with_browser()`**. When set: search page prints how many job URLs found and a sample; if 0, prints HTML length; each job page that is blocked prints **page title** and **reason** (e.g. `body matched: 'join linkedin'`). Helps diagnose “only 1 URL” or “all skipped”.
- **Scripts:** **`Scripts for manual runs.txt`** in Linkedin-jobs updated with current commands: full run, fetch + score, resumes, and optional **`--debug`**, **`--phase pdf`**, **`--headless`**, **`--top-n`**.
- **Where it lives:** All of the above is in **`personal/Linkedin-jobs/`**. job-alert-resume and Indeed-jobs are unchanged.

---

## Related project: Indeed-jobs (reference)

| What | Where (Indeed-jobs project) |
|------|-----------------------------|
| Job source | Indeed search via `config/indeed_search.json`; `src/indeed_search.py` builds URLs and scrapes result pages for job links. |
| Stealth / anti-detection | `src/browser_context.py` (Chrome, viewport, locale, init script); used by indeed_search and indeed_scraper. |
| Cloudflare handling | `src/indeed_scraper.py`: `BLOCKED_PAGE_MARKERS`, `_is_blocked_page()`, `is_blocked_job()`; main/run_workflow filter blocked before save/write; resume_output skips blocked in write_job_files and write_combined_markdown. |
| Defaults | Visible browser (headless=False); `--headless` opt-in; `--max-jobs` default 25. |
| Commands | `python run_workflow.py --phase fetch` (up to 25 jobs, visible); `python run_workflow.py --phase all`; `python main.py`. |

---

## Related project: Linkedin-jobs (reference)

| What | Where (Linkedin-jobs project) |
|------|-------------------------------|
| Job source | LinkedIn job search via `config/linkedin_search.json`; `src/linkedin_search.py` builds URLs (keywords, location, f_TPR), paginates, scrolls to lazy-load, extracts `/jobs/view/ID` and job IDs from HTML/URL. |
| Job ID | Numeric (e.g. `4359155249`). `src/link_extractor.py`: from `/jobs/view/ID` and from query `currentJobId=`. |
| Search URL extraction | Scroll after load; regex for `currentJobId=`, `jobPostingId`, `urn:li:jobPosting:ID` in HTML; add `page.url()` currentJobId. |
| Block detection | `src/linkedin_scraper.py`: do **not** use "join linkedin" (footer on every page); use authwall, auth-wall, title "sign in"/"log in". |
| Description extraction | `_query_one(..., max_len=0)` for description (no 500-char cap); scroll to description, click Show more, then extract; multiple description selectors. |
| Debug | `--debug` in run_workflow: search page URL count + sample; job page blocked reason (title + which marker). |
| Commands | `python run_workflow.py --phase fetch --max-jobs 10`; `python run_workflow.py --phase all`; `python run_workflow.py --phase resumes`. See `Scripts for manual runs.txt` in Linkedin-jobs. |

---

*Last updated: sessions 14–18 — Job application links, resume .md→PDF; no report at 7 AM; **Indeed-jobs** (Indeed search, Cloudflare fixes); **Linkedin-jobs** (LinkedIn search, scroll/regex for URLs, block fix, empty JD fix, --debug).*
