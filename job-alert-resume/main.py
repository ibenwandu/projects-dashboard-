"""
Pipeline: Gmail job alerts → extract Indeed links → scrape job pages → write resume-tailoring docs.

First run:
  1. Put Gmail API credentials at project root: credentials.json
  2. pip install -r requirements.txt
  3. playwright install chromium
  4. python main.py   (will open browser for Gmail login once, then run)

Output: ./output/<NN>_<JobTitle>_<Company>.md per job, plus combined output/jobs_combined.md
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.config import GMAIL_MAX_MESSAGES, GMAIL_QUERY, OUTPUT_DIR, PROJECT_ROOT
from src.gmail_fetcher import fetch_job_alert_bodies
from src.indeed_scraper import scrape_jobs_with_browser
from src.link_extractor import extract_indeed_urls_from_html, extract_indeed_urls_from_plain_text
from src.resume_output import write_combined_markdown, write_job_files


def main(
    gmail_query: str | None = None,
    max_emails: int | None = None,
    max_jobs: int | None = None,
    headless: bool = True,
    output_dir: Path | None = None,
    skip_gmail: bool = False,
    urls_file: str | None = None,
    debug: bool = False,
) -> None:
    # 1) Collect Indeed job URLs
    all_urls: list[str] = []
    seen: set[str] = set()

    if urls_file:
        path = Path(urls_file)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.exists():
            print(f"URLs file not found: {path}")
            print("Create a text file with one Indeed job URL per line, e.g.:")
            print("  https://ca.indeed.com/viewjob?jk=cc46af67917defed")
            print("Then run: python main.py --skip-gmail --urls-file urls.txt")
            return
        with open(path, encoding="utf-8") as f:
            for line in f:
                url = line.strip().split("#")[0].strip()
                if url and "viewjob" in url and url not in seen:
                    seen.add(url)
                    all_urls.append(url)
    elif not skip_gmail:
        total_emails = 0
        for _mid, body in fetch_job_alert_bodies(
            query=gmail_query or GMAIL_QUERY,
            max_messages=max_emails or GMAIL_MAX_MESSAGES,
        ):
            total_emails += 1
            if body.strip().lower().startswith("<"):
                urls = extract_indeed_urls_from_html(body)
            else:
                urls = extract_indeed_urls_from_plain_text(body)
            if debug:
                print(f"  Email {total_emails}: body_len={len(body)}, indeed_urls={len(urls)}")
            for u in urls:
                if u not in seen:
                    seen.add(u)
                    all_urls.append(u)
        if debug and total_emails:
            print(f"  Total emails: {total_emails}, unique Indeed URLs: {len(all_urls)}")

    if not all_urls:
        print("No Indeed job URLs found. Check Gmail query or provide --urls-file.")
        print("Tip: run with --debug to see how many emails were read and URLs per email.")
        return

    if max_jobs:
        all_urls = all_urls[: max_jobs]
    print(f"Found {len(all_urls)} unique Indeed job URL(s). Scraping...")

    # 2) Scrape each job page
    jobs = scrape_jobs_with_browser(all_urls, headless=headless, delay_between=1.2)
    print(f"Scraped {len(jobs)} job(s).")

    # 3) Write output
    out = Path(output_dir or OUTPUT_DIR)
    written = write_job_files(jobs, out)
    combined = write_combined_markdown(jobs, out / "jobs_combined.md")
    print(f"Wrote {len(written)} file(s) to {out}")
    print(f"Combined: {combined}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gmail job alerts → Indeed scrape → resume docs")
    parser.add_argument("--gmail-query", default=None, help=f"Gmail search query (default: {GMAIL_QUERY})")
    parser.add_argument("--max-emails", type=int, default=None, help="Max job-alert emails to read")
    parser.add_argument("--max-jobs", type=int, default=None, help="Max job URLs to scrape (for testing)")
    parser.add_argument("--no-headless", action="store_true", help="Show browser window")
    parser.add_argument("--output-dir", type=Path, default=None, help=f"Output directory (default: {OUTPUT_DIR})")
    parser.add_argument("--skip-gmail", action="store_true", help="Skip Gmail; use only --urls-file")
    parser.add_argument("--urls-file", type=str, default=None, help="Text file with one Indeed viewjob URL per line")
    parser.add_argument("--debug", action="store_true", help="Print email count and URLs per email (Gmail mode)")
    args = parser.parse_args()

    main(
        gmail_query=args.gmail_query,
        max_emails=args.max_emails,
        max_jobs=args.max_jobs,
        headless=not args.no_headless,
        output_dir=args.output_dir,
        skip_gmail=args.skip_gmail,
        urls_file=args.urls_file,
        debug=args.debug,
    )
