"""
Fully automated workflow: Indeed search (CX/CS focus) → scrape → score with AI → report → (user approves) → tailored resumes.

Phases:
  fetch   - Indeed search (config/indeed_search.json) → scrape → save jobs_cache.json + markdown in output/
  score   - Load jobs from cache, score each against config scoring-criteria.json via Gemini/OpenAI
  report  - Generate top-N report and full ranked list in reports/
  resumes - Read config/approved_jobs.txt, generate tailored resumes for those jobs into output/resumes/

Run full pipeline:
  python run_workflow.py --phase all
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from src.config import (
    JOBS_CACHE_PATH,
    OUTPUT_DIR,
    REPORTS_DIR,
    TOP_N_JOBS,
    load_indeed_search_config,
)
from src.indeed_search import get_search_result_job_urls, filter_jobs_by_criteria
from src.indeed_scraper import scrape_jobs_with_browser, is_blocked_job
from src.job_cache import load_jobs_cache, save_jobs_cache, load_reported_job_ids, append_reported_job_ids
from src.link_extractor import job_key_from_url
from src.report_generator import generate_report
from src.resume_output import write_combined_markdown, write_job_files
from src.resume_tailor import write_tailored_resumes
from src.gemini_scorer import score_jobs


def run_fetch(
    max_jobs: int | None = None,
    headless: bool = False,
    no_filter_job_type: bool = False,
) -> list:
    """Fetch from Indeed search, scrape, save cache and markdown. Returns list of JobDetails."""
    config = load_indeed_search_config()
    print("Fetching job URLs from Indeed search...")
    urls = get_search_result_job_urls(
        config=config,
        max_jobs_total=max_jobs,
        headless=headless,
    )
    if not urls:
        print("No Indeed job URLs found.")
        print("Indeed may be showing 'Additional Verification Required' (Cloudflare). Try:")
        print("  • Run without --headless so the browser window is visible.")
        print("  • If you see a verification page, wait for it to finish or complete any check, then run again.")
        print("  • Try again in a few minutes, or use --max-jobs 5 to reduce request volume.")
        print("  • Check config/indeed_search.json (keywords, locations, salary_min, days_posted).")
        return []
    if max_jobs:
        urls = urls[:max_jobs]
    print("Found", len(urls), "job URL(s). Scraping (Chrome + anti-detection, slower to reduce blocks)...")
    all_jobs = scrape_jobs_with_browser(urls, headless=headless, delay_between=3.0, delay_jitter=2.0)
    blocked = [j for j in all_jobs if is_blocked_job(j)]
    jobs = [j for j in all_jobs if not is_blocked_job(j)]
    if blocked:
        print(f"Skipped {len(blocked)} job(s) (Cloudflare/timeout).")
    if not jobs:
        print("No jobs could be scraped. Try --max-jobs 5 or run without --headless.")
        return []
    if not no_filter_job_type and config.get("job_types"):
        jobs = filter_jobs_by_criteria(jobs, config=config)
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
    skip_reported_filter: bool = False,
) -> None:
    path = jobs_cache_path or JOBS_CACHE_PATH
    jobs = load_jobs_cache(path)
    if not jobs:
        print("No jobs in cache. Run fetch first: python run_workflow.py --phase fetch")
        return

    if not skip_reported_filter:
        reported = load_reported_job_ids()
        jobs_new = [j for j in jobs if (job_key_from_url(j.url) or "") not in reported]
        excluded = len(jobs) - len(jobs_new)
        if excluded:
            print(f"Excluding {excluded} job(s) already reported in a previous run.")
        if not jobs_new:
            print("All jobs in cache were already reported. Run fetch to get new jobs, or use --include-reported to score all.")
            print("To clear the list: delete or edit output/reported_job_ids.txt")
            return
        jobs = jobs_new

    print(f"Scoring {len(jobs)} job(s) with AI...")
    scored = score_jobs(jobs)
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    report_path = generate_report(scored, top_n=top_n or TOP_N_JOBS, report_dir=REPORTS_DIR, run_id=run_id)

    if not skip_reported_filter and scored:
        jks = [s.jk for s in scored if s.jk]
        append_reported_job_ids(jks)
        print(f"Recorded {len(jks)} job ID(s) in output/reported_job_ids.txt (excluded from future reports).")

    print(f"Report written: {report_path}")
    print("Review the report, then add approved Job IDs to config/approved_jobs.txt and run: python run_workflow.py --phase resumes")


def run_pdfs() -> list:
    from src.md_to_pdf import convert_resume_mds_to_pdfs
    from src.config import RESUMES_DIR
    created = convert_resume_mds_to_pdfs(resumes_dir=RESUMES_DIR)
    if created:
        print(f"Created {len(created)} PDF(s) in output/resumes/")
    else:
        print("No .md resume files found in output/resumes/ to convert.")
    return created


def run_resumes() -> list:
    written = write_tailored_resumes()
    if written:
        n_md = sum(1 for p in written if str(p).endswith(".md") and p.name != "job_links.md")
        n_pdf = sum(1 for p in written if str(p).endswith(".pdf"))
        print(f"Wrote {n_md} tailored resume(s) (.md + .pdf) to output/resumes/")
        print("Job application links: output/resumes/job_links.md")
    else:
        print("No resumes generated. Add Job IDs to config/approved_jobs.txt (one per line).")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Indeed-jobs-cs workflow: fetch → score → report → resumes")
    parser.add_argument("--phase", choices=["fetch", "score", "report", "resumes", "pdf", "all"], default="all",
                        help="fetch=Indeed search+scrape; score+report=score and write report; resumes=tailored resumes + PDFs; pdf=convert .md to PDF only; all=fetch+score+report")
    parser.add_argument("--max-jobs", type=int, default=25, help="Max jobs to fetch and scrape (default: 25)")
    parser.add_argument("--headless", action="store_true", help="Run browser in background (may increase Cloudflare blocks)")
    parser.add_argument("--no-filter-job-type", action="store_true")
    parser.add_argument("--top-n", type=int, default=None)
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--include-reported", action="store_true",
                        help="Include jobs already in a previous report (default: exclude them)")
    args = parser.parse_args()

    phase = args.phase
    if phase == "all":
        run_fetch(max_jobs=args.max_jobs, headless=args.headless, no_filter_job_type=args.no_filter_job_type)
        run_score_and_report(top_n=args.top_n, run_id=args.run_id, skip_reported_filter=args.include_reported)
        return
    if phase == "fetch":
        run_fetch(max_jobs=args.max_jobs, headless=args.headless, no_filter_job_type=args.no_filter_job_type)
        return
    if phase in ("score", "report"):
        run_score_and_report(top_n=args.top_n, run_id=args.run_id, skip_reported_filter=args.include_reported)
        return
    if phase == "resumes":
        run_resumes()
        return
    if phase == "pdf":
        run_pdfs()
        return


if __name__ == "__main__":
    main()
