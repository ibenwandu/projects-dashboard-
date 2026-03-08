"""Indeed job scraper using Playwright."""
import time
from typing import Optional

from playwright.sync_api import sync_playwright

from core.job_model import JobDetails
from platforms.base_scraper import BaseScraper


SELECTORS = {
    "title": ["h1.jobsearch-JobInfoHeader-title", ".jobsearch-JobInfoHeader-title", "h1"],
    "company": ["[data-testid='inlineTitle-companyName']", ".jobsearch-CompanyReview"],
    "location": ["[data-testid='jobsearch-JobInfoHeader-companyLocation']", ".jobsearch-JobInfoHeader-companyLocation"],
    "salary": ["[data-testid='salary-snippet-container']", ".salary-snippet-container"],
    "description": [".jobsearch-jobDescriptionText", "[id='jobDescriptionText']"],
}

BLOCKED_MARKERS = ("login", "sign in", "verify")


class IndeedScraper(BaseScraper):
    """Scrape jobs from Indeed."""

    platform_name = "indeed"

    def search(self, keywords, locations, max_results=50, **kwargs):
        """Build Indeed search URLs (MVP stub)."""
        return []

    def scrape_job(self, url: str) -> Optional[JobDetails]:
        """Scrape an Indeed job posting."""
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

                job_id = url.split("jk=")[-1].split("&")[0] if "jk=" in url else ""

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
