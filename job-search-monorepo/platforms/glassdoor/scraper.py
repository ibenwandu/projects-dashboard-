"""Glassdoor job scraper using Playwright."""
import time
from typing import Optional

from playwright.sync_api import sync_playwright

from core.job_model import JobDetails
from platforms.base_scraper import BaseScraper


SELECTORS = {
    "title": ["h1.jobTitle", ".job-title", "h1"],
    "company": ["a.employer-name", ".employer-name"],
    "location": [".job-location", "[data-test='job-location']"],
    "salary": [".salary", "[data-test='job-salary']"],
    "description": [".jobDescriptionContent", "[data-test='job-description']", ".description"],
}

BLOCKED_MARKERS = ("login", "sign in", "verify")


class GlassdoorScraper(BaseScraper):
    """Scrape jobs from Glassdoor."""

    platform_name = "glassdoor"

    def search(self, keywords, locations, max_results=50, **kwargs):
        """Build Glassdoor search URLs (MVP stub)."""
        return []

    def scrape_job(self, url: str) -> Optional[JobDetails]:
        """Scrape a Glassdoor job posting."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            try:
                page.goto(url, timeout=10000)
                time.sleep(2)

                page_text = page.content().lower()
                for marker in BLOCKED_MARKERS:
                    if marker in page_text:
                        return None

                title = self._query_one(page, SELECTORS["title"])
                company = self._query_one(page, SELECTORS["company"])
                location = self._query_one(page, SELECTORS["location"])
                salary = self._query_one(page, SELECTORS["salary"])
                description = self._query_one(page, SELECTORS["description"], max_len=0)

                job_id = url.split("jobListingId=")[-1].split("&")[0] if "jobListingId=" in url else ""

                return JobDetails(
                    url=url,
                    platform=self.platform_name,
                    job_id=job_id,
                    title=title,
                    company=company,
                    location=location,
                    salary=salary,
                    description=description,
                )
            finally:
                browser.close()

    @staticmethod
    def _query_one(page, selectors: list, default: str = "", max_len: int = 500) -> str:
        """Query for first matching element."""
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el:
                    text = (el.inner_text() or "").strip()
                    if text and (max_len == 0 or len(text) <= max_len):
                        return text
            except:
                continue
        return default
