# Schedule: Run workflow twice daily (7 AM and 7 PM EST)

## Option 1: Windows Task Scheduler (recommended)

1. Open **Task Scheduler** (search "Task Scheduler" in Windows).
2. **Create Basic Task**:
   - Name: `Job Alert Resume Workflow`
   - Trigger: **Daily**
   - Start: pick today, time **7:00:00 AM**
   - Action: **Start a program**
   - Program: `run_workflow_scheduled.bat`
   - Start in: `C:\Users\user\projects\personal\job-alert-resume` (or your project path)
3. After creating, open the task → **Triggers** → **Edit** → set time to **7:00 AM**.
4. **New** trigger: **Daily**, **7:00:00 PM**, repeat.
5. **Important:** Under **Security options**, select **"Run only when user is logged on"**. Do *not* choose "Run whether user is logged on or not"—that option requires a Windows account password (blank passwords are not allowed), and you’ll get a "User account restriction error" when saving.

**Time zone:** Set the task's time zone to **Eastern Standard Time (EST)** so 7 AM and 7 PM are in your local Eastern time.

## Option 2: Two separate tasks

- Task 1: 7:00 AM EST, run `run_workflow_scheduled.bat`.
- Task 2: 7:00 PM EST, run `run_workflow_scheduled.bat`.

Same "Start a program" action; Start in = project root.

## What runs

Each run executes:

```
python run_workflow.py --phase all
```

That will:

1. Fetch job alerts from Gmail (indeed/linkedin in:updates).
2. Scrape each job page and save to `output/jobs_cache.json` and markdown files.
3. Score every job with Gemini using `config/scoring-criteria.json`.
4. Write a report to `reports/<timestamp>/report.md` (top 10 + full ranked list).

You then:

1. Open `reports/<latest>/report.md` and review.
2. Copy the Job IDs you want into `config/approved_jobs.txt` (one per line).
3. Run once manually (or add a second scheduled run later): `python run_workflow.py --phase resumes` to generate tailored resumes in `output/resumes/`.

## Notes

- **GEMINI_API_KEY** must be set (env or .env) for scoring and resume generation.
- Gmail OAuth uses `credentials.json` and `token.json`; ensure the task runs as a user who has completed the browser login once.
- **No password on your account?** Use "Run only when user is logged on". The task will run at 7 AM and 7 PM whenever you’re logged in; no password is required.
- **Run log:** Each scheduled run appends to `output/workflow_run.log` (timestamp, Python output, exit code). If a run produces no report, open this file to see whether the task ran and what failed.

## When no report appears (e.g. 7 AM run)

1. **Check `output/workflow_run.log`** – If you see `[date time] Starting workflow` and then output (or an error), the task ran; the log explains why no report (e.g. "No Indeed job URLs found", Gemini error, or traceback). If there is no new "Starting workflow" line at 7 AM, the task did not run.
2. **Task didn't run** – The PC may have been **asleep** at 7 AM (scheduled tasks do not run when the system is asleep unless you enable "Wake the computer to run this task" in the task's Conditions). Or the task has only one trigger (e.g. 7 PM only); add a second trigger for 7:00 AM.
3. **"Start in"** – In the task action, set **Start in** to the project folder (e.g. `C:\Users\user\projects\personal\job-alert-resume`) so the batch and Python find the project. The script now also loads `.env` from the project root regardless of working directory.
