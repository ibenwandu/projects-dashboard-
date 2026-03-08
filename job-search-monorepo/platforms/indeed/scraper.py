"""Indeed job scraper using Playwright."""
import time
import urllib.parse
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

    def search(self, keywords: list[str], locations: list[str], max_results: int = 50, **kwargs) -> list[str]:
        """Search Indeed for job URLs matching keywords and locations.

        Builds search result page URLs and extracts job posting URLs from them.
        """
        if not keywords or not locations:
            return []

        job_urls = []
        jobs_per_page = 15

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            try:
                for keyword in keywords:
                    for location in locations:
                        # Calculate pages needed
                        pages_needed = (max_results + jobs_per_page - 1) // jobs_per_page

                        for page_num in range(pages_needed):
                            offset = page_num * jobs_per_page

                            # Build and navigate to search page
                            params = {
                                "q": keyword,
                                "l": location,
                                "start": offset
                            }
                            search_url = "https://www.indeed.com/jobs?" + urllib.parse.urlencode(params)

                            try:
                                page.goto(search_url, timeout=10000, wait_until="load")
                                time.sleep(1)

                                # Extract job URLs from search results
                                job_links = page.query_selector_all("a[data-jk]")

                                for link in job_links:
                                    jk = link.get_attribute("data-jk")
                                    if jk:
                                        job_url = f"https://www.indeed.com/viewjob?jk={jk}"
                                        job_urls.append(job_url)

                                        if len(job_urls) >= max_results:
                                            return job_urls

                            except Exception as e:
                                print(f"Error searching page {page_num}: {e}")
                                continue

            finally:
                browser.close()

        return job_urls

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
