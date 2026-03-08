"""Abstract base class for platform scrapers."""
from abc import ABC, abstractmethod
from typing import Optional

from core.job_model import JobDetails


class BaseScraper(ABC):
    """Base interface for platform-specific scrapers."""

    platform_name: str = ""

    @abstractmethod
    def search(
        self,
        keywords: list[str],
        locations: list[str],
        max_results: int = 50,
        **kwargs
    ) -> list[str]:
        """Search for job URLs given keywords and locations."""
        pass

    @abstractmethod
    def scrape_job(self, url: str) -> Optional[JobDetails]:
        """Scrape a single job page and extract job details."""
        pass

    def scrape_jobs(self, urls: list[str], headless: bool = False) -> list[JobDetails]:
        """Scrape multiple job URLs."""
        jobs = []
        for url in urls:
            try:
                job = self.scrape_job(url)
                if job:
                    jobs.append(job)
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue
        return jobs
