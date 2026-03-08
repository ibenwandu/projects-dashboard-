"""
Create a Playwright browser context with anti-detection settings to reduce
bot blocks. Use for LinkedIn search and job detail pages.
"""
from __future__ import annotations

DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}
DEFAULT_LOCALE = "en-CA"
DEFAULT_TIMEZONE = "America/Toronto"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def get_context_options(headless: bool = True) -> dict:
    """Options for browser.new_context() to appear more like a real user."""
    return {
        "viewport": DEFAULT_VIEWPORT,
        "user_agent": DEFAULT_USER_AGENT,
        "locale": DEFAULT_LOCALE,
        "timezone_id": DEFAULT_TIMEZONE,
        "ignore_https_errors": False,
        "java_script_enabled": True,
        "bypass_csp": False,
        "extra_http_headers": {
            "Accept-Language": "en-CA,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        },
    }


def get_stealth_init_script() -> str:
    """Inject script to hide common automation signals."""
    return """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = { runtime: {} };
    """


def launch_browser(playwright, headless: bool = True, use_chrome: bool = True):
    """Launch browser. Prefer Chrome when use_chrome=True."""
    try:
        if use_chrome:
            return playwright.chromium.launch(
                headless=headless,
                channel="chrome",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                ],
            )
    except Exception:
        pass
    return playwright.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )


def new_stealth_context(browser, use_stealth_script: bool = True):
    """Create a new context with anti-detection options and optional init script."""
    context = browser.new_context(**get_context_options())
    if use_stealth_script:
        try:
            context.add_init_script(get_stealth_init_script())
        except Exception:
            pass
    return context
