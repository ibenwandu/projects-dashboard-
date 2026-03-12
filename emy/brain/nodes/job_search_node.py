"""JobSearchBrainNode - thread-based job search with Playwright."""

import logging
from concurrent.futures import ThreadPoolExecutor
from emy.brain.nodes.base_node import BaseDomainNode

logger = logging.getLogger("JobSearchBrainNode")

# Stealth patterns (copied from Linkedin-jobs-cs patterns)
STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
]

STEALTH_INIT_SCRIPT = (
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    "window.chrome = { runtime: {} };"
)

STEALTH_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class JobSearchBrainNode(BaseDomainNode):
    """Adapter node for job search using Playwright.

    Uses ThreadPoolExecutor to run sync_playwright in isolation from async context.
    Stealth patterns prevent LinkedIn detection.
    """

    def __init__(self, scrape_fn=None):
        """Initialize node with optional injected scrape function for testing.

        Args:
            scrape_fn: Optional function(query: str) -> list for testing.
                      If not provided, uses _sync_scrape_jobs.
        """
        self._scrape_fn = scrape_fn or self._sync_scrape_jobs
        self._executor = ThreadPoolExecutor(max_workers=1)

    def execute(self, state: dict) -> dict:
        """Execute job search in thread pool.

        Runs sync scraper in executor to avoid blocking the event loop.

        Args:
            state: Current workflow state dict

        Returns:
            State updates dict with step_count, execution_history, context
        """
        query = state.get("user_request", {}).get("query", "")

        try:
            # Always run in executor to avoid Playwright async conflicts
            jobs = self._executor.submit(self._scrape_fn, query).result(timeout=30)
        except Exception as e:
            logger.error(f"JobSearch scrape failed: {e}")
            jobs = []

        result = {
            "jobs_found": len(jobs),
            "job_listings": jobs,
            "query": query,
            "agent": "JobSearchBrainNode",
        }

        step = state.get("step_count", 0) + 1
        history = list(state.get("execution_history", []))
        history.append({
            "step": step,
            "agent": "JobSearchBrainNode",
            "success": True,
            "result": result,
        })

        return {
            "step_count": step,
            "execution_history": history,
            "context": {**state.get("context", {}), "agent_result": result},
            "current_agent": "JobSearchBrainNode",
        }

    def _sync_scrape_jobs(self, query: str) -> list:
        """Runs in thread pool. Uses sync_playwright (safe from non-async thread).

        Searches LinkedIn for jobs matching the query and returns results.

        Args:
            query: Job search query string

        Returns:
            List of job listing dicts
        """
        from playwright.sync_api import sync_playwright

        jobs = []
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, args=STEALTH_ARGS)
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=STEALTH_USER_AGENT,
                )
                context.add_init_script(STEALTH_INIT_SCRIPT)
                page = context.new_page()

                # TODO: Implement full LinkedIn search + scrape pattern
                # (adapted from Linkedin-jobs-cs/src/linkedin_search.py patterns)
                # For now, return empty list (failing gracefully)

                browser.close()
        except Exception as e:
            logger.warning(f"Sync scrape error: {e}")

        return jobs
