"""BrowserController - Playwright lifecycle manager for browser automation.

Manages Chromium browser lifecycle, page creation, navigation, and screenshots.
Supports async context manager pattern for clean resource management.

IMPORTANT: Uses playwright.async_api only. Never uses sync_api in FastAPI context.
"""

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from typing import Optional
import logging

logger = logging.getLogger("BrowserController")

# Chrome arguments for Render environment
RENDER_CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",  # Required on Render/Linux
    "--disable-dev-shm-usage",  # Required on Render (limited /dev/shm)
    "--disable-gpu",
    "--single-process",
    "--disable-extensions",
]


class BrowserController:
    """Async Playwright browser lifecycle manager.

    Handles:
    - Browser launch/teardown (with stealth mode)
    - Context creation (user agent, viewport)
    - Page creation with anti-automation detection
    - Navigation with network idle waiting
    - Screenshot capture
    - Resource cleanup

    Usage:
        async with BrowserController() as controller:
            page = await controller.new_page()
            success = await controller.navigate(page, "https://example.com")
            screenshot = await controller.screenshot(page)
            # Resources auto-cleaned up on context exit

    Attributes:
        headless: Run browser in headless mode (default True)
    """

    def __init__(self, headless: bool = True):
        """Initialize BrowserController.

        Args:
            headless: Whether to run Chromium in headless mode (default True)
        """
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self.logger = logging.getLogger("BrowserController")
        self.logger.debug(f"BrowserController created (headless={headless})")

    async def start(self) -> None:
        """Start Playwright and launch Chromium browser.

        Raises:
            Exception: If browser launch fails
        """
        try:
            self.logger.debug("Starting Playwright...")
            self._playwright = await async_playwright().start()

            self.logger.debug("Launching Chromium browser...")
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=RENDER_CHROME_ARGS,
            )
            self.logger.info("Browser started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop Playwright and close Chromium browser.

        Safe to call multiple times (checks if already stopped).
        """
        try:
            if self._browser:
                self.logger.debug("Closing browser...")
                await self._browser.close()
                self._browser = None

            if self._playwright:
                self.logger.debug("Stopping Playwright...")
                await self._playwright.stop()
                self._playwright = None

            self.logger.info("Browser stopped successfully")

        except Exception as e:
            self.logger.error(f"Error stopping browser: {e}", exc_info=True)

    async def new_page(self) -> Page:
        """Create a new browser page with stealth settings.

        Returns:
            Playwright Page object configured for browser automation

        Raises:
            RuntimeError: If browser not started
        """
        if not self._browser:
            raise RuntimeError("Browser not started. Call start() first.")

        try:
            self.logger.debug("Creating new page...")

            # Create context with stealth settings
            context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            page = await context.new_page()

            # Inject script to hide webdriver property
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )

            self.logger.debug("Page created successfully")
            return page

        except Exception as e:
            self.logger.error(f"Failed to create page: {e}", exc_info=True)
            raise

    async def navigate(self, page: Page, url: str, timeout: int = 30000) -> bool:
        """Navigate to URL and wait for network idle.

        Args:
            page: Playwright Page object
            url: URL to navigate to
            timeout: Navigation timeout in milliseconds (default 30s)

        Returns:
            True if navigation successful, False if timeout or error
        """
        try:
            self.logger.debug(f"Navigating to {url}...")
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            self.logger.info(f"Successfully navigated to {url}")
            return True

        except Exception as e:
            self.logger.error(f"Navigation failed for {url}: {e}")
            return False

    async def screenshot(self, page: Page) -> bytes:
        """Take a screenshot of current page.

        Args:
            page: Playwright Page object

        Returns:
            Screenshot as bytes (PNG format)

        Raises:
            Exception: If screenshot fails
        """
        try:
            self.logger.debug("Taking screenshot...")
            screenshot_bytes = await page.screenshot(full_page=False)
            self.logger.debug(f"Screenshot captured ({len(screenshot_bytes)} bytes)")
            return screenshot_bytes

        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}", exc_info=True)
            raise

    async def __aenter__(self):
        """Async context manager entry: start browser.

        Returns:
            Self (BrowserController instance)
        """
        await self.start()
        return self

    async def __aexit__(self, *args):
        """Async context manager exit: stop browser.

        Ensures browser is cleaned up even if exception occurs.
        """
        await self.stop()
