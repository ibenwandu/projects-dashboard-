# Job Alert → Resume Pipeline

Automates the flow: **Gmail (Indeed job alerts) → extract job links → scrape each Indeed job page → write structured docs** so you can create custom resumes per role.

## What it does

1. **Gmail** – Uses the Gmail API to read your job alert emails (Indeed, and optionally LinkedIn) from the **Updates** category.
2. **Link extraction** – Parses each email and collects unique Indeed `viewjob` URLs.
3. **Indeed scraper** – Opens each job URL in a headless browser (Playwright), then extracts:
   - Job title, company, location, salary
   - Full job description
   - Skills / keywords (when present)
4. **Output** – Writes one Markdown file per job under `output/`, plus `output/jobs_combined.md`, with all fields ready for resume tailoring.

## Setup

### 1. Python and dependencies

- Python 3.10+
- Install deps and Playwright browser:

```bash
cd job-alert-resume
pip install -r requirements.txt
playwright install chromium
```

### 2. Gmail API credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or pick one) → **APIs & Services** → **Enable APIs** → enable **Gmail API**.
3. **Credentials** → **Create credentials** → **OAuth 2.0 Client ID**.
4. Application type: **Desktop app**.
5. Download the JSON and save it as **`credentials.json`** in the project root (same folder as `main.py`).

On first run, the script will open a browser for you to sign in to Gmail and authorize read-only access. It will save a `token.json` so you don’t have to log in again.

### 3. Optional environment

- `JAR_GMAIL_QUERY` – Gmail search query (default: `from:indeed OR from:linkedin in:updates`).
- `JAR_GMAIL_MAX_MESSAGES` – Max number of job-alert emails to process (default: 50).

Or pass `--gmail-query` and `--max-emails` from the command line.

## Usage

**Full pipeline (Gmail → scrape → output):**

```bash
python main.py
```

**Limit emails and jobs (e.g. for testing):**

```bash
python main.py --max-emails 5 --max-jobs 10
```

**Custom Gmail query (e.g. only Indeed, or a label):**

```bash
python main.py --gmail-query "from:indeed in:updates"
```

**Scrape from a list of URLs only (no Gmail):**

```bash
# Put one Indeed viewjob URL per line in urls.txt, then:
python main.py --skip-gmail --urls-file urls.txt
```

**Show the browser window while scraping:**

```bash
python main.py --no-headless
```

**Change output directory:**

```bash
python main.py --output-dir ./my_jobs
```

## Output

- **Per job:** `output/01_Business_Analyst_Desjardins.md`, etc., with:
  - Title, company, location, salary, URL
  - **Skills / keywords** to prioritize on your resume
  - **Full job description** for tailoring bullets

- **Combined:** `output/jobs_combined.md` – all jobs in one file.

Use these files as input for:
- Manual resume edits
- An LLM or script that suggests bullet points from the description and skills

---

## Automated workflow (fetch → score → report → resumes)

A **fully automated workflow** runs: fetch job alerts from Gmail → scrape jobs → **score each job with Gemini AI** against your candidate profile → generate an **actionable report** (e.g. top 10 matches) → you **approve** which jobs you want → **customized resumes** are generated for the approved list using your master resume.

### Config folder (`config/`)

- **`scoring-criteria.json`** – Candidate profile, required/preferred skills, location, salary, role types, seniority, industries, red flags. Used by Gemini to score each job (0–100) and explain fit.
- **`profile.md`** – Your full narrative profile / resume (used as master resume when `master-resume.md` is not used).
- **`master-resume.md`** – (Optional) Dedicated template for tailoring. If empty or missing, `profile.md` is used.
- **`approved_jobs.txt`** – After reviewing the report, add one **Job ID** per line (the `jk` value from the report). These jobs get tailored resumes when you run `--phase resumes`.

### AI: Gemini or OpenAI (ChatGPT)

**Default (Gemini):** Set **`GEMINI_API_KEY`** or **`GOOGLE_API_KEY`** in your environment or **`.env`**. The default model is **`gemini-1.5-flash`** (you can override with **`GEMINI_MODEL`** or **`JAR_GEMINI_MODEL`**, e.g. `gemini-1.5-pro`).

**Use ChatGPT instead:** Set **`JAR_AI_PROVIDER=openai`** and **`OPENAI_API_KEY`** in `.env`. The app will use **`gpt-4o-mini`** by default (override with **`OPENAI_MODEL`**, e.g. `gpt-4o`).

### Run the workflow

**Full run (fetch + score + report):**

```bash
python run_workflow.py --phase all
```

This will: fetch from Gmail, scrape jobs, save `output/jobs_cache.json`, score every job with Gemini, and write **`reports/<run_id>/report.md`** (top 10 + full ranked list with scores and reasoning).

**After you review the report:**  
Copy the Job IDs you want into **`config/approved_jobs.txt`** (one per line), then:

```bash
python run_workflow.py --phase resumes
```

Tailored resumes are written to **`output/resumes/`** as **.md** and **.pdf**. The PDFs use the layout defined in **`config/resume-pdf-template.html`** (centered name, underlined section titles, letter format). A **`job_links.md`** file in the same folder lists each job with its apply link. To regenerate only PDFs from existing .md files (e.g. after editing the template), run: `python run_workflow.py --phase pdf`.

**Phases:**

- `--phase fetch` – Gmail + scrape only; saves cache and markdown.
- `--phase score` or `--phase report` – Load cache, score with Gemini, write report (requires existing cache).
- `--phase resumes` – Generate resumes for jobs listed in `config/approved_jobs.txt`.
- `--phase all` – fetch + score + report (does not run resumes; you approve first).

### Schedule: 7 AM and 7 PM EST

To run the workflow **twice daily** (7 AM and 7 PM Eastern):

1. Use **Windows Task Scheduler** to run **`run_workflow_scheduled.bat`** at 7:00 AM and 7:00 PM (set task time zone to Eastern).
2. See **`schedule_setup.md`** for step-by-step instructions.

Each scheduled run runs `python run_workflow.py --phase all` (fetch, score, report). You then review the latest report and, when ready, add approved Job IDs to `config/approved_jobs.txt` and run `python run_workflow.py --phase resumes` manually (or add a separate task for that).

---

## Notes

- **Indeed** often changes their HTML. If title, description, or skills stop populating, the selectors in `src/indeed_scraper.py` may need updating (check the page in DevTools).
- **Rate limiting:** The script waits between page loads; you can increase the delay if needed.
- **LinkedIn:** The pipeline is set up to *find* LinkedIn alert emails; link extraction and scraping are currently implemented for **Indeed** only. Adding LinkedIn URL extraction would follow the same pattern.

## Project layout

```
job-alert-resume/
├── main.py                  # Gmail → scrape → output (no scoring)
├── run_workflow.py          # Full workflow: fetch → score → report → (approve) → resumes
├── run_workflow_scheduled.bat   # For Task Scheduler (7 AM / 7 PM EST)
├── schedule_setup.md        # How to set up the schedule
├── requirements.txt
├── credentials.json         # Gmail OAuth (you add)
├── token.json               # Created after first Gmail login
├── config/
│   ├── scoring-criteria.json  # Candidate profile + scoring weights
│   ├── profile.md             # Full profile / master resume content
│   ├── master-resume.md       # Optional dedicated template
│   └── approved_jobs.txt      # Job IDs you approve for resume generation
├── output/
│   ├── jobs_cache.json       # Scraped jobs (for scoring & resumes)
│   ├── *.md                  # Per-job markdown (from main.py or workflow)
│   └── resumes/              # Tailored resumes (from --phase resumes)
├── reports/                  # Reports per run (report.md, top_job_ids.txt)
└── src/
    ├── config.py
    ├── gmail_fetcher.py
    ├── link_extractor.py
    ├── indeed_scraper.py
    ├── resume_output.py
    ├── job_cache.py          # Save/load jobs cache
    ├── profile_loader.py     # Load scoring-criteria + profile
    ├── gemini_client.py      # Gemini API
    ├── gemini_scorer.py      # Score job vs profile with Gemini
    ├── report_generator.py   # Top N + full list report
    └── resume_tailor.py      # Tailored resume per approved job
```
