"""Scrape Indeed job pages for title, company, description, and skills using Playwright."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


@dataclass
class JobDetails:
    """Structured job posting data for resume tailoring."""
    url: str
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""
    job_type: str = ""  # Full-time, Part-time, etc.
    description: str = ""
    skills: list[str] = field(default_factory=list)
    raw_html_snippet: str = ""  # optional, for debugging


# Selectors that tend to exist on Indeed job pages (may need updates if Indeed changes layout)
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
}


def _query_one(page, selectors: list[str], default: str = "") -> str:
    """Try each selector and return first non-empty text."""
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
    """Try each selector and return list of non-empty texts from first match."""
    for sel in selectors:
        try:
            els = page.query_selector_all(sel)
            if els:
                return [((e.inner_text() or "").strip()) for e in els if (e.inner_text() or "").strip()]
        except Exception:
            continue
    return []


def scrape_job_page(url: str, page, wait_sec: float = 2.0) -> JobDetails:
    """
    Scrape a single Indeed viewjob URL using an already-open Playwright page.
    Returns JobDetails; description/skills may be empty if selectors don't match.
    """
    job = JobDetails(url=url)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(wait_sec)
        job.title = _query_one(page, SELECTORS["title"])
        job.company = _query_one(page, SELECTORS["company"])
        job.location = _query_one(page, SELECTORS["location"])
        job.salary = _query_one(page, SELECTORS["salary"])
        job.description = _query_one(page, SELECTORS["description"])
        skills = _query_all(page, SELECTORS["skills"])
        # Filter to likely skill-like strings (short, no long sentences)
        job.skills = [s for s in skills if s and len(s) < 80 and not s.startswith("Profile")]
    except PlaywrightTimeout:
        pass
    except Exception:
        pass
    return job


def scrape_jobs_with_browser(
    urls: list[str],
    headless: bool = True,
    delay_between: float = 1.0,
) -> list[JobDetails]:
    """
    Open a browser, visit each Indeed job URL, and return list of JobDetails.
    Uses a single page and navigates sequentially to avoid rate limits.
    """
    results: list[JobDetails] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()
            for i, url in enumerate(urls):
                job = scrape_job_page(url, page, wait_sec=2.0)
                results.append(job)
                if delay_between and i < len(urls) - 1:
                    time.sleep(delay_between)
        finally:
            browser.close()
    return results
