"""
Pipeline: Glassdoor job search (by criteria) -> scrape job pages -> write resume-tailoring docs.

Job source: config/glassdoor_search.json (keywords, locations, etc.)
Output: output/<NN>_<JobTitle>_<Company>.md per job, plus output/jobs_combined.md
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.config import OUTPUT_DIR, load_glassdoor_search_config
from src.glassdoor_search import get_search_result_job_urls, filter_jobs_by_criteria
from src.glassdoor_scraper import scrape_jobs_with_browser, is_blocked_job
from src.resume_output import write_combined_markdown, write_job_files


def main(
    max_jobs: int | None = None,
    headless: bool = False,
    output_dir: Path | None = None,
    no_filter_job_type: bool = False,
) -> None:
    config = load_glassdoor_search_config()
    print("Fetching job URLs from Glassdoor search (config/glassdoor_search.json)...")
    urls = get_search_result_job_urls(
        config=config,
        max_jobs_total=max_jobs,
        headless=headless,
    )
    if not urls:
        print("No job URLs found. Check config/glassdoor_search.json.")
        return
    print("Found", len(urls), "job URL(s). Scraping details (Chrome + anti-detection)...")
    all_jobs = scrape_jobs_with_browser(urls, headless=headless, delay_between=5.0, delay_jitter=3.0)
    blocked = [j for j in all_jobs if is_blocked_job(j)]
    jobs = [j for j in all_jobs if not is_blocked_job(j)]
    if blocked:
        print("Skipped", len(blocked), "job(s) (auth/timeout).")
    if not jobs:
        print("No jobs could be scraped. Try --max-jobs 5 or run with visible browser.")
        return
    if not no_filter_job_type and config.get("job_types"):
        jobs = filter_jobs_by_criteria(jobs, config=config)
        print("After filtering by job type:", len(jobs), "job(s).")
    out = Path(output_dir or OUTPUT_DIR)
    written = write_job_files(jobs, out)
    combined = write_combined_markdown(jobs, out / "jobs_combined.md")
    print("Wrote", len(written), "file(s) to", out)
    print("Combined:", combined)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Glassdoor search -> scrape -> resume docs")
    parser.add_argument("--max-jobs", type=int, default=25, help="Max jobs to scrape (default: 25)")
    parser.add_argument("--headless", action="store_true", help="Run browser in background")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--no-filter-job-type", action="store_true", help="Do not filter by job_types in config")
    args = parser.parse_args()
    main(
        max_jobs=args.max_jobs,
        headless=args.headless,
        output_dir=args.output_dir,
        no_filter_job_type=args.no_filter_job_type,
    )
