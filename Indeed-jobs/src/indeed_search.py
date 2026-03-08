"""
Fetch Indeed job URLs by running Indeed search with configured criteria
(salary, job type, date posted, location, title keywords).
Uses Playwright to load search result pages and extract job links.
"""
from __future__ import annotations

import time
from urllib.parse import urlencode, urljoin, urlparse, parse_qs

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from .config import load_indeed_search_config
from .link_extractor import job_key_from_url
from .browser_context import launch_browser, new_stealth_context

INDEED_BASE = "https://ca.indeed.com"


def _job_key_from_href(href: str) -> str | None:
    """Extract jk from an Indeed link (viewjob or rc/clk)."""
    if not href or "indeed.com" not in href.lower():
        return None
    if href.startswith("/"):
        href = urljoin(INDEED_BASE, href)
    parsed = urlparse(href)
    q = parse_qs(parsed.query)
    jk_list = q.get("jk", [])
    if jk_list:
        return jk_list[0].strip()
    return None


def _canonical_viewjob_url(jk: str, base: str = INDEED_BASE) -> str:
    return f"{base.rstrip('/')}/viewjob?jk={jk}"


def build_search_urls(config: dict | None = None) -> list[str]:
    """
    Build Indeed search URLs from config (indeed_search.json).
    Criteria: keywords (analyst, manager), locations (Toronto ON, Remote),
    salary_min, fromage=1 (last 24h). Job type filtering done after scrape.
    """
    cfg = config or load_indeed_search_config()
    base = (cfg.get("base_url") or INDEED_BASE).rstrip("/")
    keywords = cfg.get("keywords") or ["analyst", "manager"]
    locations = cfg.get("locations") or ["Toronto, ON", "Remote"]
    salary_min = cfg.get("salary_min")
    days_posted = cfg.get("days_posted", 1)

    urls = []
    for q in keywords:
        for loc in locations:
            params = {
                "q": q,
                "l": loc,
                "fromage": days_posted,
            }
            if salary_min is not None:
                params["salary"] = salary_min
            url = f"{base}/jobs?{urlencode(params)}"
            urls.append(url)
    return urls


def extract_job_urls_from_search_page(page) -> set[str]:
    """
    From a loaded Indeed search results page, extract all viewjob URLs (by jk).
    Returns set of canonical viewjob URLs.
    """
    seen_jk: set[str] = set()
    result_urls: set[str] = set()

    # Indeed: job cards have a link with data-jk or href containing jk=
    # Selectors that commonly work: a[data-jk], a[href*="viewjob"], a[href*="jk="]
    try:
        # Links that point to a job (href contains jk= or viewjob)
        links = page.query_selector_all('a[href*="jk="], a[href*="viewjob"], a[data-jk]')
        for link in links:
            href = link.get_attribute("href")
            data_jk = link.get_attribute("data-jk")
            jk = data_jk if data_jk else (_job_key_from_href(href) if href else None)
            if jk and jk not in seen_jk:
                seen_jk.add(jk)
                result_urls.add(_canonical_viewjob_url(jk, INDEED_BASE))
    except Exception:
        pass

    # Fallback: any link with viewjob in href
    try:
        all_links = page.query_selector_all("a[href]")
        for link in all_links:
            href = link.get_attribute("href")
            if not href:
                continue
            jk = _job_key_from_href(href) or job_key_from_url(href)
            if jk and jk not in seen_jk:
                seen_jk.add(jk)
                result_urls.add(_canonical_viewjob_url(jk, INDEED_BASE))
    except Exception:
        pass

    return result_urls


def get_search_result_job_urls(
    search_urls: list[str] | None = None,
    config: dict | None = None,
    max_jobs_total: int | None = None,
    max_per_search: int | None = None,
    headless: bool = True,
    delay_between_pages: float = 1.5,
) -> list[str]:
    """
    Open Indeed search URL(s), paginate through results, collect unique job viewjob URLs.
    If search_urls is None, builds from config (indeed_search.json).
    """
    if search_urls is None:
        search_urls = build_search_urls(config)
    cfg = config or load_indeed_search_config()
    max_total = max_jobs_total if max_jobs_total is not None else cfg.get("max_jobs_total", 200)
    max_per = max_per_search if max_per_search is not None else cfg.get("max_results_per_search", 100)
    base = (cfg.get("base_url") or INDEED_BASE).rstrip("/")

    all_jk: set[str] = set()
    ordered_urls: list[str] = []

    with sync_playwright() as p:
        browser = launch_browser(p, headless=headless, use_chrome=True)
        try:
            context = new_stealth_context(browser)
            page = context.new_page()

            first_page_retry_done = False
            for search_url in search_urls:
                if len(ordered_urls) >= max_total:
                    break
                start = 0
                collected_this_search = 0
                verification_failed = False
                while collected_this_search < max_per:
                    # Indeed pagination: start=0, 10, 20, ...
                    if start > 0:
                        sep = "&" if "?" in search_url else "?"
                        page_url = f"{search_url}{sep}start={start}"
                    else:
                        page_url = search_url
                    try:
                        page.goto(page_url, wait_until="domcontentloaded", timeout=20000)
                        time.sleep(2.5)
                    except PlaywrightTimeout:
                        break
                    except Exception:
                        break

                    urls_on_page = extract_job_urls_from_search_page(page)
                    # Only on the very first page load of the run: wait once for user to pass verification, then retry once
                    if not urls_on_page and start == 0 and not first_page_retry_done:
                        print("First search page returned no job links (verification page?). Waiting 15s for you to complete any check in the browser, then retrying once...")
                        first_page_retry_done = True
                        time.sleep(15)
                        try:
                            page.goto(page_url, wait_until="domcontentloaded", timeout=20000)
                            time.sleep(3)
                            urls_on_page = extract_job_urls_from_search_page(page)
                        except Exception:
                            pass
                    if not urls_on_page:
                        if start == 0 and first_page_retry_done:
                            verification_failed = True
                        break

                    added = 0
                    for url in urls_on_page:
                        jk = job_key_from_url(url)
                        if jk and jk not in all_jk and len(ordered_urls) < max_total:
                            all_jk.add(jk)
                            ordered_urls.append(url)
                            added += 1
                            collected_this_search += 1
                    if added == 0:
                        break
                    start += 10
                    if delay_between_pages > 0:
                        time.sleep(delay_between_pages + (0.5 if delay_between_pages < 3 else 0))
                if verification_failed:
                    break
        finally:
            browser.close()

    return ordered_urls


def filter_jobs_by_criteria(job_details_list, config: dict | None = None) -> list:
    """
    Filter list of JobDetails by config job_types (and optionally language).
    job_types e.g. ["Full-time", "Contract", "Permanent"].
    """
    from .indeed_scraper import JobDetails

    cfg = config or load_indeed_search_config()
    allowed_types = cfg.get("job_types") or ["Full-time", "Contract", "Permanent"]
    allowed_lower = {t.lower().strip() for t in allowed_types}

    out = []
    for job in job_details_list:
        if not isinstance(job, JobDetails):
            out.append(job)
            continue
        jt = (job.job_type or "").strip().lower()
        if not jt or any(allow in jt or jt in allow for allow in allowed_lower):
            out.append(job)
        elif job.job_type and job.job_type.strip():
            # e.g. "Full-time" in job_type
            if any(t in (job.job_type or "") for t in allowed_types):
                out.append(job)
            else:
                continue
        else:
            # No job type extracted - include by default so we don't drop everything
            out.append(job)
    return out
