"""
Fetch LinkedIn job URLs by running LinkedIn job search with configured criteria
(keywords, location, date posted). Uses Playwright to load search result pages and extract job links.
"""
from __future__ import annotations

import re
import time
from urllib.parse import urlencode, urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from .config import load_linkedin_search_config
from .link_extractor import job_key_from_url
from .browser_context import launch_browser, new_stealth_context

LINKEDIN_BASE = "https://www.linkedin.com"

# f_TPR: time posted (seconds) - r86400 = last 24h, r604800 = last week, r2592000 = last month
DAYS_TO_F_TPR = {1: "r86400", 7: "r604800", 30: "r2592000"}


def _canonical_view_url(job_id: str, base: str = LINKEDIN_BASE) -> str:
    return f"{base.rstrip('/')}/jobs/view/{job_id}"


def build_search_urls(config: dict | None = None) -> list[str]:
    """
    Build LinkedIn job search URLs from config (linkedin_search.json).
    Criteria: keywords, locations, f_TPR (date posted).
    """
    cfg = config or load_linkedin_search_config()
    base = (cfg.get("base_url") or LINKEDIN_BASE).rstrip("/")
    keywords = cfg.get("keywords") or ["analyst", "manager"]
    locations = cfg.get("locations") or ["Toronto, ON", "Remote"]
    days_posted = cfg.get("days_posted", 1)
    f_tpr = DAYS_TO_F_TPR.get(days_posted, "r86400")

    urls = []
    for q in keywords:
        for loc in locations:
            params = {
                "keywords": q,
                "location": loc,
                "f_TPR": f_tpr,
            }
            url = f"{base}/jobs/search/?{urlencode(params)}"
            urls.append(url)
    return urls


def _scroll_jobs_list(page, scroll_pause: float = 0.5, max_scrolls: int = 8) -> None:
    """
    Scroll the jobs list / main content to trigger lazy loading.
    LinkedIn often loads only ~7 jobs initially; scrolling loads more (up to 25 per page).
    """
    try:
        # Scroll the window or the jobs list container
        for _ in range(max_scrolls):
            page.evaluate("window.scrollBy(0, 600)")
            time.sleep(scroll_pause)
            page.evaluate("window.scrollBy(0, 400)")
            time.sleep(scroll_pause)
    except Exception:
        pass


def extract_job_urls_from_search_page(page) -> set[str]:
    """
    From a loaded LinkedIn search results page, extract all job view URLs.
    Returns set of canonical .../jobs/view/<id> URLs.
    """
    seen_ids: set[str] = set()
    result_urls: set[str] = set()

    def add_url(full_url: str) -> None:
        jid = job_key_from_url(full_url)
        if jid and jid not in seen_ids:
            seen_ids.add(jid)
            result_urls.add(_canonical_view_url(jid, LINKEDIN_BASE))

    # 1) Links with /jobs/view/ in href (primary)
    try:
        links = page.query_selector_all('a[href*="/jobs/view/"]')
        for link in links:
            href = link.get_attribute("href")
            if not href:
                continue
            full_url = urljoin(LINKEDIN_BASE, href) if href.startswith("/") else href
            add_url(full_url)
    except Exception:
        pass

    # 2) Job card title links (class can vary: job-card-list__title, base-card__full-link, etc.)
    for sel in (
        'a.job-card-list__title[href]',
        'a.base-card__full-link[href*="view"]',
        'a[href*="/jobs/view/"]',
    ):
        try:
            links = page.query_selector_all(sel)
            for link in links:
                href = link.get_attribute("href")
                if not href:
                    continue
                full_url = urljoin(LINKEDIN_BASE, href) if href.startswith("/") else href
                add_url(full_url)
        except Exception:
            continue

    # 3) Any link containing /jobs/view/<digits>
    try:
        all_links = page.query_selector_all("a[href]")
        for link in all_links:
            href = link.get_attribute("href")
            if not href:
                continue
            full_url = urljoin(LINKEDIN_BASE, href) if href.startswith("/") else href
            add_url(full_url)
    except Exception:
        pass

    # 4) Scrape page HTML for job ID patterns (LinkedIn embeds IDs in URLs, JSON, urns)
    try:
        html = page.content() or ""
        patterns = [
            r"/jobs/view/(\d+)",
            r"currentJobId[=:](\d+)",
            r"currentJobId%3D(\d+)",  # URL-encoded
            r'"jobPostingId"\s*:\s*"?(\d+)"?',
            r"urn:li:jobPosting:(\d+)",
            r"data-job-id=\"(\d+)\"",
            r"/jobs/search/\?.*?currentJobId=(\d+)",
        ]
        for pat in patterns:
            for m in re.finditer(pat, html, re.IGNORECASE):
                jid = m.group(1)
                if jid.isdigit() and jid not in seen_ids:
                    seen_ids.add(jid)
                    result_urls.add(_canonical_view_url(jid, LINKEDIN_BASE))
    except Exception:
        pass

    return result_urls


def get_search_result_job_urls(
    search_urls: list[str] | None = None,
    config: dict | None = None,
    max_jobs_total: int | None = None,
    max_per_search: int | None = None,
    headless: bool = False,
    delay_between_pages: float = 2.5,
    debug: bool = False,
) -> list[str]:
    """
    Open LinkedIn search URL(s), paginate through results, collect unique job view URLs.
    If search_urls is None, builds from config (linkedin_search.json).
    LinkedIn pagination: start=0, 25, 50, ...
    """
    if search_urls is None:
        search_urls = build_search_urls(config)
    cfg = config or load_linkedin_search_config()
    max_total = max_jobs_total if max_jobs_total is not None else cfg.get("max_jobs_total", 200)
    max_per = max_per_search if max_per_search is not None else cfg.get("max_results_per_search", 50)
    page_size = 25

    all_ids: set[str] = set()
    ordered_urls: list[str] = []

    with sync_playwright() as p:
        browser = launch_browser(p, headless=headless, use_chrome=True)
        try:
            context = new_stealth_context(browser)
            page = context.new_page()

            for search_url in search_urls:
                if len(ordered_urls) >= max_total:
                    break
                start = 0
                collected_this_search = 0
                while collected_this_search < max_per:
                    if start > 0:
                        sep = "&" if "?" in search_url else "?"
                        page_url = f"{search_url}{sep}start={start}"
                    else:
                        page_url = search_url
                    try:
                        page.goto(page_url, wait_until="domcontentloaded", timeout=25000)
                        time.sleep(delay_between_pages)
                        _scroll_jobs_list(page, scroll_pause=0.5, max_scrolls=10)
                        time.sleep(2.0)
                        # Allow time for any lazy-loaded job cards to render
                        try:
                            page.wait_for_load_state("networkidle", timeout=5000)
                        except Exception:
                            pass
                        time.sleep(1.0)
                    except PlaywrightTimeout:
                        break
                    except Exception:
                        break

                    urls_on_page = extract_job_urls_from_search_page(page)
                    # LinkedIn sometimes puts currentJobId only in the address bar when a job is selected; add it if present
                    try:
                        current_url = page.url()
                        jid = job_key_from_url(current_url)
                        if jid and jid not in all_ids:
                            urls_on_page.add(_canonical_view_url(jid, LINKEDIN_BASE))
                    except Exception:
                        pass
                    if debug and urls_on_page:
                        print(f"  [debug] Search page: found {len(urls_on_page)} job URL(s); sample: {list(urls_on_page)[:2]}")
                    if not urls_on_page:
                        if debug:
                            html_len = len(page.content() or "")
                            print(f"  [debug] Search page: 0 job URLs (HTML length {html_len})")
                        break

                    added = 0
                    for url in sorted(urls_on_page):
                        jid = job_key_from_url(url)
                        if jid and jid not in all_ids and len(ordered_urls) < max_total:
                            all_ids.add(jid)
                            ordered_urls.append(url)
                            added += 1
                            collected_this_search += 1
                    if added == 0:
                        break
                    start += page_size
                    if delay_between_pages > 0:
                        time.sleep(delay_between_pages * 0.5)
        finally:
            browser.close()

    return ordered_urls


def filter_jobs_by_criteria(job_details_list, config: dict | None = None) -> list:
    """Filter list of JobDetails by config job_types (e.g. Full-time, Contract)."""
    from .linkedin_scraper import JobDetails

    cfg = config or load_linkedin_search_config()
    allowed_types = cfg.get("job_types") or ["Full-time", "Contract"]
    allowed_lower = {t.lower().strip() for t in allowed_types}

    out = []
    for job in job_details_list:
        if not isinstance(job, JobDetails):
            out.append(job)
            continue
        jt = (job.job_type or "").strip().lower()
        if not jt or any(allow in jt or jt in allow for allow in allowed_lower):
            out.append(job)
        elif job.job_type and any(t in (job.job_type or "") for t in allowed_types):
            out.append(job)
        else:
            out.append(job)
    return out
