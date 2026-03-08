"""Scrape Indeed job pages for title, company, description, and skills using Playwright."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from .browser_context import launch_browser, new_stealth_context

# Page content markers that indicate Cloudflare/bot block (do not treat as real job)
BLOCKED_PAGE_MARKERS = (
    "additional verification required",
    "cloudflare",
    "checking your browser",
    "please wait while we verify",
    "challenge-running",
    "cf-browser-verification",
)


@dataclass
class JobDetails:
    """Structured job posting data for resume tailoring."""
    url: str
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""
    job_type: str = ""
    description: str = ""
    skills: list[str] = field(default_factory=list)
    raw_html_snippet: str = ""

SELECTORS = {
    "title": [
        "h1.jobsearch-JobInfoHeader-title",
        "[data-testid='jobsearch-JobInfoHeader-title']",
        "h1",
    ],
    "company": [
        "[data-testid='inlineHeader-companyName']",
        ".jobsearch-InlineCompanyRating-companyHeader a",
        "a[data-tn-element='companyName']",
        ".companyName",
    ],
    "location": [
        "[data-testid='job-location']",
        ".jobsearch-JobInfoHeader-subtitle div",
        ".companyLocation",
        "[data-testid='jobsearch-JobInfoHeader-subtitle']",
    ],
    "salary": [
        "[data-testid='jobsearch-JobInfoHeader-salary']",
        "#jobDetailsSection .salary-snippet-container",
        ".jobsearch-JobInfoHeader-subtitle .salary",
    ],
    "description": [
        "#jobDescriptionText",
        "[data-testid='job-description-container']",
        ".jobsearch-jobDescriptionText",
        "#job-description-container",
    ],
    "skills": [
        "[data-testid='job-details-skills'] li",
        "#jobDetailsSection .jobsearch-JobMetadataHeader-item",
        ".jobsearch-JobMetadataHeader-item",
    ],
    "job_type": [
        "[data-testid='job-metadata-container']",
        ".jobsearch-JobMetadataHeader-item",
        "#jobDetailsSection .jobsearch-JobMetadataHeader-item",
    ],
}


def _query_one(page, selectors: list[str], default: str = "") -> str:
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                text = (el.inner_text() or "").strip()
                if text:
                    return text
        except Exception:
            continue
    return default


def _query_all(page, selectors: list[str]) -> list[str]:
    for sel in selectors:
        try:
            els = page.query_selector_all(sel)
            if els:
                return [((e.inner_text() or "").strip()) for e in els if (e.inner_text() or "").strip()]
        except Exception:
            continue
    return []


def _is_blocked_page(page) -> bool:
    """True if the current page looks like a Cloudflare/verification block."""
    try:
        content = (page.content() or "").lower()
        title = (page.title() or "").lower()
        text = content + " " + title
        return any(m in text for m in BLOCKED_PAGE_MARKERS)
    except Exception:
        return True


def scrape_job_page(url: str, page, wait_sec: float = 2.5) -> JobDetails:
    job = JobDetails(url=url)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(wait_sec)
        if _is_blocked_page(page):
            job.title = "[Blocked: Cloudflare]"
            job.company = ""
            return job
        job.title = _query_one(page, SELECTORS["title"])
        job.company = _query_one(page, SELECTORS["company"])
        job.location = _query_one(page, SELECTORS["location"])
        job.salary = _query_one(page, SELECTORS["salary"])
        job.job_type = _query_one(page, SELECTORS.get("job_type", []))
        job.description = _query_one(page, SELECTORS["description"])
        skills = _query_all(page, SELECTORS["skills"])
        job.skills = [s for s in skills if s and len(s) < 80 and not s.startswith("Profile")]
    except PlaywrightTimeout:
        job.title = "[Blocked: timeout]"
    except Exception:
        pass
    return job


def is_blocked_job(job: JobDetails) -> bool:
    """True if this job was blocked (Cloudflare/timeout) and has no real content."""
    t = (job.title or "").strip()
    return t.startswith("[Blocked:") or "additional verification" in t.lower() or "cloudflare" in t.lower()


def scrape_jobs_with_browser(
    urls: list[str],
    headless: bool = True,
    delay_between: float = 3.0,
    delay_jitter: float = 2.0,
    use_chrome: bool = True,
) -> list[JobDetails]:
    """
    Scrape each job URL. Uses stealthier browser (Chrome if available, anti-detection context).
    delay_between + random jitter reduces rate-limit/Cloudflare blocks.
    """
    results: list[JobDetails] = []
    with sync_playwright() as p:
        browser = launch_browser(p, headless=headless, use_chrome=use_chrome)
        try:
            context = new_stealth_context(browser)
            page = context.new_page()
            for i, url in enumerate(urls):
                job = scrape_job_page(url, page, wait_sec=2.5)
                results.append(job)
                if i < len(urls) - 1 and delay_between > 0:
                    wait = delay_between + random.uniform(0, delay_jitter)
                    time.sleep(max(0.5, wait))
        finally:
            browser.close()
    return results
