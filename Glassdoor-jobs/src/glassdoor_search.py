"""
Fetch Glassdoor job URLs by running Glassdoor job search with configured criteria
(keywords, location). Uses Playwright: open index page, fill search form, submit, then extract job links.
"""
from __future__ import annotations

import re
import time
from urllib.parse import urljoin, urlencode

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from .config import load_glassdoor_search_config
from .link_extractor import job_key_from_url
from .browser_context import launch_browser, new_stealth_context

GLASSDOOR_BASE = "https://www.glassdoor.com"
# Use .ca for Canada; redirects often send there when location is Canadian
GLASSDOOR_CA = "https://www.glassdoor.ca"
GLASSDOOR_INDEX = f"{GLASSDOOR_BASE}/Job/index.htm"


def build_search_urls(config: dict | None = None) -> list[str]:
    """Build list of "keyword|location" pairs for search."""
    cfg = config or load_glassdoor_search_config()
    keywords = cfg.get("keywords") or ["analyst", "manager"]
    locations = cfg.get("locations") or ["Toronto, ON", "Remote"]
    return [f"{q}|{loc}" for q in keywords for loc in locations]


def _build_direct_search_url(keyword: str, location: str, base: str) -> str:
    """Build a direct Glassdoor job search results URL (query params)."""
    # Use .ca when base is glassdoor.com so we hit the same domain as redirects
    host = base.rstrip("/")
    if "glassdoor.com" in host and "glassdoor.ca" not in host:
        host = GLASSDOOR_CA
    params = {
        "typedKeyword": keyword,
        "locKeyword": location,
        "clickSource": "searchBtn",
        "suggestCount": "0",
        "suggestChosen": "false",
    }
    return f"{host}/Job/jobs.htm?{urlencode(params)}"


def _slug(s: str) -> str:
    """Turn 'Toronto, ON' into 'toronto-on', 'Customer Success' into 'customer-success'."""
    return "-".join(re.sub(r"[^\w\s-]", "", s).lower().split())[:50]


def _run_single_search_via_form(page, keyword: str, location: str, base: str, debug: bool) -> list[str]:
    """
    Navigate directly to search results URL. Try (1) jobs.htm?typedKeyword=... then
    (2) path-style /Job/{loc}-{kw}-jobs-SRCH... if we're still on index.
    Then scroll and extract individual job listing links from the results page.
    """
    host = base.rstrip("/")
    if "glassdoor.com" in host and "glassdoor.ca" not in host:
        host = GLASSDOOR_CA
    direct_url = _build_direct_search_url(keyword, location, base)
    try:
        page.goto(direct_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2.5)
    except Exception as e:
        if debug:
            print(f"  [debug] Failed to load search URL: {e}")
        return []

    # If we were redirected back to index, try path-style search URL (Canada/Ontario codes)
    if "/Job/index" in page.url or page.url.rstrip("/").endswith("/Job"):
        path_url = f"{host}/Job/{_slug(location)}-{_slug(keyword)}-jobs-SRCH_IL.0,7_IC2281069_KO8,21.htm"
        if debug:
            print(f"  [debug] Redirected to index, trying path URL: {path_url[:80]}...")
        try:
            page.goto(path_url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(2.5)
        except Exception:
            pass

    _scroll_results(page, scroll_pause=0.5, max_scrolls=8)
    time.sleep(2.0)
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    time.sleep(1.0)

    page_base = page.url.split("/Job/")[0] if "/Job/" in page.url else host
    if debug:
        print(f"  [debug] After search: page URL = {page.url}")

    return list(extract_job_urls_from_search_page(page, page_base, debug=debug))


def _scroll_results(page, scroll_pause: float = 0.5, max_scrolls: int = 6) -> None:
    """Scroll to trigger lazy loading of job cards."""
    try:
        for _ in range(max_scrolls):
            page.evaluate("window.scrollBy(0, 500)")
            time.sleep(scroll_pause)
    except Exception:
        pass


def extract_job_urls_from_search_page(page, base: str = GLASSDOOR_BASE, debug: bool = False) -> set[str]:
    """
    From a loaded Glassdoor search results page, extract all job listing URLs.
    Returns set of full job listing URLs (job-listing/... or /Job/...).
    Uses a stable key for dedupe: job_key_from_url or full URL.
    """
    seen_keys: set[str] = set()
    result_urls: set[str] = set()

    def add_url(href: str) -> None:
        if not href or "glassdoor" not in href.lower():
            return
        full = urljoin(base, href) if href.startswith("/") else href
        # Only accept URLs that are clearly individual job listings (not category/search pages)
        if "job-listing" not in full and "JV_" not in full:
            return
        if "jobs-SRCH" in full or full.rstrip("/").endswith("jobs.htm") or "/Job/index" in full:
            return
        jk = job_key_from_url(full)
        if not jk:
            jk = full
        if jk not in seen_keys:
            seen_keys.add(jk)
            result_urls.add(full)

    # Links to job-listing pages (individual job detail pages only)
    try:
        for sel in (
            'a[href*="job-listing"]',
            'a[href*="/job-listing/"]',
            'a[href*="JV_"]',
            'a[data-test="job-link"]',
            '[data-test="job-card"] a[href*="job-listing"]',
            '[data-test="job-card"] a[href*="JV_"]',
            '[class*="JobsList"] a[href*="job-listing"]',
        ):
            links = page.query_selector_all(sel)
            for link in links:
                href = link.get_attribute("href")
                if href and ("job-listing" in href or "JV_" in href):
                    add_url(href)
    except Exception:
        pass

    # Any link that is clearly a job detail (job-listing or JV_)
    try:
        all_links = page.query_selector_all('a[href*="glassdoor"]')
        for link in all_links:
            href = link.get_attribute("href")
            if not href:
                continue
            if "job-listing" in href or "JV_" in href:
                add_url(href)
    except Exception:
        pass

    # Scan HTML for job listing URLs (embedded in data or scripts)
    try:
        html = page.content() or ""
        for pattern in [
            r'"(https?://[^"]*glassdoor[^"]*job-listing[^"]*)"',
            r'href="(/job-listing/[^"]+)"',
            r'url["\s:]+["\']([^"\']*JV_[A-Z0-9_,]+[^"\']*)["\']',
            r'"(https?://[^"]*glassdoor[^"]*JV_[A-Z0-9_,]+[^"]*)"',
        ]:
            for m in re.finditer(pattern, html, re.IGNORECASE):
                u = m.group(1).strip()
                if "jobs-SRCH" in u or "index" in u:
                    continue
                if "job-listing" not in u and "JV_" not in u:
                    continue
                if u.startswith("/"):
                    u = urljoin(base, u)
                add_url(u)
    except Exception:
        pass

    if debug and not result_urls:
        # Sample some hrefs that contain "job" to help diagnose
        try:
            sample = []
            for a in page.query_selector_all('a[href*="job"]')[:15]:
                h = a.get_attribute("href")
                if h:
                    sample.append(h[:90])
            if sample:
                print(f"  [debug] Sample job-related hrefs: {sample[:5]}")
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
    Run Glassdoor search via index form (keyword + location per pair), collect unique job listing URLs.
    search_urls from build_search_urls() are "keyword|location" strings.
    """
    if search_urls is None:
        search_urls = build_search_urls(config)
    cfg = config or load_glassdoor_search_config()
    base = (cfg.get("base_url") or GLASSDOOR_BASE).rstrip("/")
    max_total = max_jobs_total if max_jobs_total is not None else cfg.get("max_jobs_total", 200)

    all_keys: set[str] = set()
    ordered_urls: list[str] = []

    with sync_playwright() as p:
        browser = launch_browser(p, headless=headless, use_chrome=True)
        try:
            context = new_stealth_context(browser)
            page = context.new_page()

            for pair in search_urls:
                if len(ordered_urls) >= max_total:
                    break
                if "|" in pair:
                    keyword, location = pair.split("|", 1)
                else:
                    keyword, location = "analyst", "Toronto, ON"
                if debug:
                    print(f"  [debug] Searching: keyword={keyword!r}, location={location!r}")
                urls_from_search = _run_single_search_via_form(page, keyword, location, base, debug=debug)
                if debug and urls_from_search:
                    print(f"  [debug] Found {len(urls_from_search)} job URL(s); sample: {list(urls_from_search)[:2]}")
                for url in urls_from_search:
                    jk = job_key_from_url(url) or url
                    if jk not in all_keys and len(ordered_urls) < max_total:
                        all_keys.add(jk)
                        ordered_urls.append(url)
                if delay_between_pages > 0:
                    time.sleep(delay_between_pages)
        finally:
            browser.close()

    return ordered_urls


def filter_jobs_by_criteria(job_details_list, config: dict | None = None) -> list:
    """Filter list of JobDetails by config job_types (e.g. Full-time, Contract)."""
    from .glassdoor_scraper import JobDetails

    cfg = config or load_glassdoor_search_config()
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
