"""Scrape Glassdoor job pages for title, company, description, and skills using Playwright."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from .browser_context import launch_browser, new_stealth_context

# Page content markers that indicate login wall, Cloudflare, or bot block.
BLOCKED_PAGE_MARKERS = (
    "sign in to glassdoor",
    "join glassdoor",
    "additional verification",
    "checking your browser",
    "please wait while we verify",
    "unlock with glassdoor",
    "help us protect glassdoor",
    "verify that you're a real person",
    "help us protect",
    "cloudflare",
    "ray id",
    "_cf_chl_rt_tk",
)
BLOCKED_TITLE_MARKERS = (
    "sign in",
    "log in",
    "login",
    "just a moment",
)


@dataclass
class JobDetails:
    """Structured job posting data (same shape as LinkedIn/Indeed pipeline)."""
    url: str
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""
    job_type: str = ""
    description: str = ""
    skills: list = field(default_factory=list)
    raw_html_snippet: str = ""


# Glassdoor job page selectors (DOM changes frequently; multiple fallbacks)
SELECTORS = {
    "title": [
        "[data-test='job-title']",
        "h1[data-test='job-title']",
        ".JobDetails_jobTitle__",
        "[class*='JobDetails_jobTitle']",
        "h1",
    ],
    "company": [
        "[data-test='employer-name']",
        ".JobDetails_employerName__",
        "[class*='EmployerProfile_employerName']",
        "[class*='job-details_employer']",
        "a[data-test='employer-name']",
    ],
    "location": [
        "[data-test='location']",
        ".JobDetails_location__",
        "[class*='JobDetails_location']",
        "[class*='job-details_location']",
    ],
    "salary": [
        "[data-test='detailSalary']",
        ".JobDetails_salary__",
        "[class*='SalaryEstimate']",
        "[class*='job-details_salary']",
    ],
    "job_type": [
        "[data-test='job-type']",
        "[class*='JobDetails_jobType']",
        "[class*='EmploymentType']",
    ],
    "description": [
        "[data-test='job-description']",
        ".JobDetails_jobDescription__",
        "[class*='JobDetails_jobDescription']",
        ".jobDescriptionContent",
        "[class*='job-description']",
        "#JobDescriptionContainer",
        ".desc",
    ],
}


def _query_one(page, selectors: list[str], default: str = "", max_len: int = 500) -> str:
    """Get first matching element's text. max_len=0 means no limit."""
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                text = (el.inner_text() or "").strip()
                if text and (max_len == 0 or len(text) <= max_len):
                    return text
        except Exception:
            continue
    return default


def _query_all(page, selectors: list[str]) -> list:
    for sel in selectors:
        try:
            els = page.query_selector_all(sel)
            if els:
                return [((e.inner_text() or "").strip()) for e in els if (e.inner_text() or "").strip()]
        except Exception:
            continue
    return []


def _click_show_more(page) -> None:
    """Click 'Show more' in description if present."""
    try:
        for sel in (
            "button[aria-label*='Show more']",
            "button[aria-label*='See more']",
            "[data-test='show-more']",
            ".show-more",
        ):
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    time.sleep(0.5)
            except Exception:
                continue
        for text in ("Show more", "See more", "Show less"):
            try:
                loc = page.get_by_role("button", name=text)
                if loc.count() > 0:
                    loc.first.click()
                    time.sleep(0.5)
            except Exception:
                pass
    except Exception:
        pass


def _is_blocked_page(page, return_reason: bool = False):
    """True if the page looks like login or verification block."""
    try:
        content = (page.content() or "").lower()
        title = (page.title() or "").lower()
        if any(m in title for m in BLOCKED_TITLE_MARKERS):
            if return_reason:
                return True, f"title matched: {title[:80]!r}"
            return True
        for m in BLOCKED_PAGE_MARKERS:
            if m in content:
                if return_reason:
                    return True, f"body matched: {m!r}"
                return True
        if return_reason:
            return False, ""
        return False
    except Exception as e:
        if return_reason:
            return True, str(e)
        return True


def scrape_job_page(url: str, page, wait_sec: float = 6.0, debug: bool = False) -> JobDetails:
    job = JobDetails(url=url)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        # Give Cloudflare / verification time to auto-resolve (or user to complete in visible browser)
        time.sleep(wait_sec)
        blocked, reason = _is_blocked_page(page, return_reason=True)
        if blocked:
            # If Cloudflare, wait longer and re-check once (challenge may complete)
            content_lower = (page.content() or "").lower()
            is_cf = "help us protect" in content_lower or "cloudflare" in content_lower or "real person" in content_lower
            if is_cf:
                if debug:
                    print("  [debug] Cloudflare/verification detected, waiting 12s for resolve...")
                time.sleep(12)
                blocked, reason = _is_blocked_page(page, return_reason=True)
            if blocked:
                if debug:
                    print(f"  [debug] Job page blocked: title={page.title()!r} reason={reason}")
                content_lower = (page.content() or "").lower()
                if "help us protect" in content_lower or "cloudflare" in content_lower or "real person" in content_lower:
                    job.title = "[Blocked: Cloudflare]"
                else:
                    job.title = "[Blocked: Glassdoor auth]"
                job.company = ""
                return job
        job.title = _query_one(page, SELECTORS["title"])
        job.company = _query_one(page, SELECTORS["company"])
        # Catch Cloudflare/verification page by title (in case block check missed it)
        if job.title and ("help us protect" in job.title.lower() or "just a moment" in job.title.lower()):
            job.title = "[Blocked: Cloudflare]"
            job.company = ""
            return job
        job.location = _query_one(page, SELECTORS["location"])
        job.salary = _query_one(page, SELECTORS["salary"])
        job.job_type = _query_one(page, SELECTORS.get("job_type", []))
        _click_show_more(page)
        time.sleep(0.5)
        job.description = _query_one(page, SELECTORS["description"], max_len=0)
        if not job.description or len(job.description) < 80:
            for sel in [".jobDescriptionContent", "[class*='job-description']", ".desc", "#JobDescriptionContainer"]:
                job.description = _query_one(page, [sel], max_len=0)
                if job.description and len(job.description) > 80:
                    break
        # If this looks like a category/search list page (not a single job), mark as non-job
        page_title = (page.title() or "").lower()
        if not job.title and not job.company and (
            "jobs in" in page_title or "search results" in page_title or "job search" in page_title
        ):
            job.title = "[Blocked: not a job page]"
            job.company = ""
            return job
        if job.title and ("jobs in" in job.title.lower() or "search results" in job.title.lower()):
            job.title = "[Blocked: not a job page]"
            job.company = ""
            return job
        skills = _query_all(page, [
            "[data-test='job-description'] li",
            ".JobDetails_jobDescription__ li",
            ".jobDescriptionContent li",
        ])
        job.skills = [s for s in skills if s and len(s) < 80 and not s.startswith("Profile")]
    except PlaywrightTimeout:
        job.title = "[Blocked: timeout]"
    except Exception:
        pass
    return job


def is_blocked_job(job: JobDetails) -> bool:
    """True if this job was blocked (auth/Cloudflare/timeout) and has no real content."""
    t = (job.title or "").strip().lower()
    return (
        t.startswith("[blocked:")
        or "sign in" in t
        or "auth" in t
        or "help us protect" in t
        or "cloudflare" in t
        or "verify" in t and "real person" in t
    )


def scrape_jobs_with_browser(
    urls: list[str],
    headless: bool = False,
    delay_between: float = 3.0,
    delay_jitter: float = 2.0,
    use_chrome: bool = True,
    debug: bool = False,
) -> list[JobDetails]:
    """Scrape each job URL. Uses stealth browser (Chrome if available)."""
    results: list[JobDetails] = []
    with sync_playwright() as p:
        browser = launch_browser(p, headless=headless, use_chrome=use_chrome)
        try:
            context = new_stealth_context(browser)
            page = context.new_page()
            for i, url in enumerate(urls):
                job = scrape_job_page(url, page, wait_sec=6.0, debug=debug)
                results.append(job)
                if i < len(urls) - 1 and delay_between > 0:
                    wait = delay_between + random.uniform(0, delay_jitter)
                    time.sleep(max(0.5, wait))
        finally:
            browser.close()
    return results
