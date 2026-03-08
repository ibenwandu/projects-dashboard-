"""
Fully automated workflow: fetch job alerts → score with Gemini → report → (user approves) → tailored resumes.

Phases:
  fetch   - Gmail → extract links → scrape Indeed → save jobs_cache.json + markdown in output/
  score   - Load jobs from cache, score each against config scoring-criteria.json via Gemini
  report  - Generate top-N report and full ranked list in reports/
  resumes - Read config/approved_jobs.txt, generate tailored resumes for those jobs into output/resumes/

Run full pipeline (fetch → score → report):
  python run_workflow.py

Run only resumes (after you've approved jobs):
  python run_workflow.py --phase resumes

Schedule (7 AM and 7 PM EST): use run_workflow_scheduled.bat with Windows Task Scheduler.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from src.config import (
    GMAIL_MAX_MESSAGES,
    GMAIL_QUERY,
    JOBS_CACHE_PATH,
    OUTPUT_DIR,
    PROJECT_ROOT,
    REPORTS_DIR,
    TOP_N_JOBS,
)
from src.gmail_fetcher import fetch_job_alert_bodies
from src.indeed_scraper import scrape_jobs_with_browser
from src.job_cache import load_jobs_cache, save_jobs_cache
from src.link_extractor import extract_indeed_urls_from_html, extract_indeed_urls_from_plain_text
from src.report_generator import generate_report
from src.resume_output import write_combined_markdown, write_job_files
from src.resume_tailor import write_tailored_resumes
from src.gemini_scorer import score_jobs


def run_fetch(
    gmail_query: str | None = None,
    max_emails: int | None = None,
    max_jobs: int | None = None,
    headless: bool = True,
) -> list:
    """Fetch from Gmail, scrape, save cache and markdown. Returns list of JobDetails."""
    all_urls = []
    seen = set()
    for _mid, body in fetch_job_alert_bodies(
        query=gmail_query or GMAIL_QUERY,
        max_messages=max_emails or GMAIL_MAX_MESSAGES,
    ):
        if body.strip().lower().startswith("<"):
            urls = extract_indeed_urls_from_html(body)
        else:
            urls = extract_indeed_urls_from_plain_text(body)
        for u in urls:
            if u not in seen:
                seen.add(u)
                all_urls.append(u)

    if not all_urls:
        print("No Indeed job URLs found.")
        return []
    if max_jobs:
        all_urls = all_urls[:max_jobs]

    print(f"Found {len(all_urls)} job URL(s). Scraping...")
    jobs = scrape_jobs_with_browser(all_urls, headless=headless, delay_between=1.2)
    print(f"Scraped {len(jobs)} job(s).")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_jobs_cache(jobs, JOBS_CACHE_PATH)
    write_job_files(jobs, OUTPUT_DIR)
    write_combined_markdown(jobs, OUTPUT_DIR / "jobs_combined.md")
    print(f"Saved cache to {JOBS_CACHE_PATH}")
    return jobs


def run_score_and_report(
    jobs_cache_path: Path | None = None,
    top_n: int | None = None,
    run_id: str | None = None,
) -> None:
    """Load jobs from cache, score with Gemini, generate report."""
    path = jobs_cache_path or JOBS_CACHE_PATH
    jobs = load_jobs_cache(path)
    if not jobs:
        print("No jobs in cache. Run fetch first: python run_workflow.py --phase fetch")
        return

    print(f"Scoring {len(jobs)} job(s) with Gemini...")
    scored = score_jobs(jobs)
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    report_path = generate_report(scored, top_n=top_n or TOP_N_JOBS, report_dir=REPORTS_DIR, run_id=run_id)
    print(f"Report written: {report_path}")
    print("Review the report, then add approved Job IDs to config/approved_jobs.txt and run: python run_workflow.py --phase resumes")


def run_pdfs() -> list[Path]:
    """Convert existing .md resumes in output/resumes/ to PDF using config template. Returns list of PDF paths."""
    from src.md_to_pdf import convert_resume_mds_to_pdfs
    from src.config import RESUMES_DIR
    created = convert_resume_mds_to_pdfs(resumes_dir=RESUMES_DIR)
    if created:
        print(f"Created {len(created)} PDF(s) in output/resumes/")
    else:
        print("No .md resume files found in output/resumes/ to convert.")
    return created


def run_resumes() -> list[Path]:
    """Generate tailored resumes for approved jobs. Returns list of written paths."""
    written = write_tailored_resumes()
    if written:
        n_md = sum(1 for p in written if str(p).endswith(".md") and p.name != "job_links.md")
        n_pdf = sum(1 for p in written if str(p).endswith(".pdf"))
        print(f"Wrote {n_md} tailored resume(s) (.md + .pdf) to output/resumes/")
        print("Job application links: output/resumes/job_links.md")
    else:
        print("No resumes generated. Add Job IDs to config/approved_jobs.txt (one per line).")
    return written


def _append_run_log(message: str) -> None:
    """Append a line to output/workflow_run.log (for scheduled runs when stdout may not be captured)."""
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        log_path = OUTPUT_DIR / "workflow_run.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] {message}\n")
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Job alert workflow: fetch → score → report → resumes")
    parser.add_argument("--phase", choices=["fetch", "score", "report", "resumes", "pdf", "all"], default="all",
                        help="fetch=Gmail+scrape; score+report=score and write report; resumes=tailored resumes + PDFs; pdf=convert existing .md to PDF only; all=fetch+score+report")
    parser.add_argument("--gmail-query", default=None, help=f"Gmail query (default: {GMAIL_QUERY})")
    parser.add_argument("--max-emails", type=int, default=None)
    parser.add_argument("--max-jobs", type=int, default=None)
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("--top-n", type=int, default=None, help=f"Top N jobs in report (default: {TOP_N_JOBS})")
    parser.add_argument("--run-id", type=str, default=None, help="Subfolder name for this run's report (default: timestamp)")
    args = parser.parse_args()

    _append_run_log(f"Python workflow started (phase={args.phase})")

    phase = args.phase
    if phase == "all":
        run_fetch(gmail_query=args.gmail_query, max_emails=args.max_emails, max_jobs=args.max_jobs, headless=not args.no_headless)
        run_score_and_report(top_n=args.top_n, run_id=args.run_id)
        return

    if phase == "fetch":
        run_fetch(gmail_query=args.gmail_query, max_emails=args.max_emails, max_jobs=args.max_jobs, headless=not args.no_headless)
        return

    if phase in ("score", "report"):
        run_score_and_report(top_n=args.top_n, run_id=args.run_id)
        return

    if phase == "resumes":
        run_resumes()
        return

    if phase == "pdf":
        run_pdfs()
        return


if __name__ == "__main__":
    try:
        main()
        _append_run_log("Python workflow finished OK")
    except Exception as e:
        _append_run_log(f"Python workflow failed: {e!r}")
        raise
