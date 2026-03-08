"""
Indeed-jobs-cs: Indeed search (CX/CS focus) -> scrape -> resume docs.
Job source: config/indeed_search.json. Output: output/*.md, jobs_combined.md
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.config import OUTPUT_DIR, load_indeed_search_config
from src.indeed_search import get_search_result_job_urls, filter_jobs_by_criteria
from src.indeed_scraper import scrape_jobs_with_browser, is_blocked_job
from src.resume_output import write_combined_markdown, write_job_files


def main(max_jobs=None, headless=False, output_dir=None, no_filter_job_type=False):
    config = load_indeed_search_config()
    print("Fetching job URLs from Indeed search (config/indeed_search.json)...")
    urls = get_search_result_job_urls(config=config, max_jobs_total=max_jobs, headless=headless)
    if not urls:
        print("No job URLs found. Check config/indeed_search.json.")
        return
    print("Found", len(urls), "job URL(s). Scraping details...")
    all_jobs = scrape_jobs_with_browser(urls, headless=headless, delay_between=3.0, delay_jitter=2.0)
    blocked = [j for j in all_jobs if is_blocked_job(j)]
    jobs = [j for j in all_jobs if not is_blocked_job(j)]
    if blocked:
        print("Skipped", len(blocked), "job(s) (Cloudflare/timeout).")
    if not jobs:
        print("No jobs could be scraped.")
        return
    if not no_filter_job_type and config.get("job_types"):
        jobs = filter_jobs_by_criteria(jobs, config=config)
        print("After filtering by job type:", len(jobs), "job(s).")
    out = Path(output_dir or OUTPUT_DIR)
    written = write_job_files(jobs, out)
    write_combined_markdown(jobs, out / "jobs_combined.md")
    print("Wrote", len(written), "file(s) to", out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indeed-jobs-cs: Indeed search (CX/CS) -> scrape -> docs")
    parser.add_argument("--max-jobs", type=int, default=25)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--no-filter-job-type", action="store_true")
    args = parser.parse_args()
    main(max_jobs=args.max_jobs, headless=args.headless, output_dir=args.output_dir, no_filter_job_type=args.no_filter_job_type)
