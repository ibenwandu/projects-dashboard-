"""Scrape LinkedIn job pages for title, company, description, and skills using Playwright."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from .browser_context import launch_browser, new_stealth_context

# Page content markers that indicate a full login wall or bot block.
# Do NOT include "join linkedin" - it appears in footer/sidebar on every page when not logged in.
BLOCKED_PAGE_MARKERS = (
    "authwall",
    "auth-wall",
    "additional verification",
    "checking your browser",
    "please wait while we verify",
)
# Title/text that indicates the whole page is an auth gate (nav "Sign in" is not enough)
BLOCKED_TITLE_MARKERS = (
    "sign in",
    "log in",
    "login",
)


@dataclass
class JobDetails:
    """Structured job posting data for resume tailoring (same shape as Indeed-jobs)."""
    url: str
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""
    job_type: str = ""
    description: str = ""
    skills: list[str] = field(default_factory=list)
    raw_html_snippet: str = ""


# LinkedIn job view page selectors (class names change frequently; multiple fallbacks)
SELECTORS = {
    "title": [
        "h1.t-24",
        ".jobs-unified-top-card__job-title",
        "h1",
        "[data-tracking-control-name='public_jobs_topcard-title']",
    ],
    "company": [
        ".jobs-unified-top-card__company-name",
        ".jobs-unified-top-card__subtitle-primary-grouping a",
        "a[data-tracking-control-name='public_jobs_topcard-org']",
        ".topcard__org-name-link",
    ],
    "location": [
        ".jobs-unified-top-card__bullet",
        ".jobs-unified-top-card__primary-description-without-tagline",
        ".topcard__flavor--bullet",
    ],
    "salary": [
        "[data-tracking-control-name='public_jobs_topcard-compensation']",
        ".jobs-unified-top-card__job-insight-view-model-secondary",
    ],
    "description": [
        ".jobs-description__content",
        ".jobs-box__html-content",
        ".jobs-description-content__content",
        "#job-details",
        "[data-tracking-control-name='public_jobs_legacy-job-details']",
        ".jobs-description",
        ".description__text",
        ".jobs-description-details",
        ".jobs-box__body",
        "[class*='jobs-description']",
        "section.jobs-description-details",
    ],
    "job_type": [
        ".jobs-unified-top-card__job-insight-view-model-secondary",
        ".job-details-how-you-match",
    ],
}


def _query_one(page, selectors: list[str], default: str = "", max_len: int = 500) -> str:
    """Get first matching element's text. max_len=0 means no length limit (for long content like description)."""
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


def _query_all(page, selectors: list[str]) -> list[str]:
    for sel in selectors:
        try:
            els = page.query_selector_all(sel)
            if els:
                return [((e.inner_text() or "").strip()) for e in els if (e.inner_text() or "").strip()]
        except Exception:
            continue
    return []


def _click_show_more(page) -> None:
    """Click 'Show more' / 'See more' in the description area so full text is in the DOM."""
    try:
        for sel in (
            "button[aria-label*='Show more']",
            "button[aria-label*='See more']",
            ".inline-show-more-text__button",
            ".jobs-description__content button",
        ):
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    time.sleep(0.5)
            except Exception:
                continue
        # Playwright locator for text (query_selector doesn't support :has-text)
        try:
            for text in ("Show more", "See more"):
                loc = page.get_by_role("button", name=text)
                if loc.count() > 0:
                    loc.first.click()
                    time.sleep(0.5)
        except Exception:
            pass
    except Exception:
        pass


def _scroll_to_description(page) -> None:
    """Scroll so the description section is in view and may finish loading."""
    try:
        for sel in (".jobs-description__content", ".jobs-description", "[class*='jobs-description']"):
            el = page.query_selector(sel)
            if el:
                el.scroll_into_view_if_needed()
                time.sleep(0.8)
                break
    except Exception:
        pass


def _is_blocked_page(page, return_reason: bool = False):
    """True if the page looks like a full login wall or verification block. If return_reason, returns (bool, str)."""
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


def scrape_job_page(url: str, page, wait_sec: float = 2.5, debug: bool = False) -> JobDetails:
    job = JobDetails(url=url)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(wait_sec)
        blocked, reason = _is_blocked_page(page, return_reason=True)
        if blocked:
            if debug:
                print(f"  [debug] Job page blocked: title={page.title()!r} reason={reason}")
            job.title = "[Blocked: LinkedIn auth]"
            job.company = ""
            return job
        job.title = _query_one(page, SELECTORS["title"])
        job.company = _query_one(page, SELECTORS["company"])
        job.location = _query_one(page, SELECTORS["location"])
        job.salary = _query_one(page, SELECTORS["salary"])
        job.job_type = _query_one(page, SELECTORS.get("job_type", []))
        # Scroll to description and expand "Show more" so full text is available (max_len=0 = no limit)
        _scroll_to_description(page)
        _click_show_more(page)
        time.sleep(0.5)
        job.description = _query_one(page, SELECTORS["description"], max_len=0)
        if not job.description or len(job.description) < 100:
            for sel in [".jobs-box__html-content", ".jobs-description-details", "[class*='description']"]:
                job.description = _query_one(page, [sel], max_len=0)
                if job.description and len(job.description) > 100:
                    break
        skills = _query_all(page, [".jobs-description__content li", ".job-details-how-you-match li", ".jobs-box__body li"])
        job.skills = [s for s in skills if s and len(s) < 80 and not s.startswith("Profile")]
    except PlaywrightTimeout:
        job.title = "[Blocked: timeout]"
    except Exception:
        pass
    return job


def is_blocked_job(job: JobDetails) -> bool:
    """True if this job was blocked (auth/timeout) and has no real content."""
    t = (job.title or "").strip()
    return t.startswith("[Blocked:") or "sign in" in t.lower() or "auth" in t.lower()


def scrape_jobs_with_browser(
    urls: list[str],
    headless: bool = False,
    delay_between: float = 3.0,
    delay_jitter: float = 2.0,
    use_chrome: bool = True,
    debug: bool = False,
) -> list[JobDetails]:
    """
    Scrape each job URL. Uses stealth browser (Chrome if available).
    delay_between + jitter reduces rate limits.
    """
    results: list[JobDetails] = []
    with sync_playwright() as p:
        browser = launch_browser(p, headless=headless, use_chrome=use_chrome)
        try:
            context = new_stealth_context(browser)
            page = context.new_page()
            for i, url in enumerate(urls):
                job = scrape_job_page(url, page, wait_sec=2.5, debug=debug)
                results.append(job)
                if i < len(urls) - 1 and delay_between > 0:
                    wait = delay_between + random.uniform(0, delay_jitter)
                    time.sleep(max(0.5, wait))
        finally:
            browser.close()
    return results
