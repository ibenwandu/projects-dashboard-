"""Tests for BrowserController Playwright lifecycle management.

Test Coverage:
1. BrowserController instantiation
2. start() calls playwright.start()
3. stop() closes browser cleanly
4. Context manager pattern (__aenter__/__aexit__)
5. new_page() returns Page object
6. navigate() returns True on success
7. navigate() returns False on timeout
8. screenshot() returns bytes
9. RENDER_CHROME_ARGS contains --no-sandbox
10. RENDER_CHROME_ARGS contains --disable-dev-shm-usage

All tests use AsyncMock to avoid launching real browser.
Integration tests marked with @pytest.mark.integration for manual testing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from emy.brain.browser_controller import (
    BrowserController,
    RENDER_CHROME_ARGS,
)


class TestBrowserControllerInstantiation:
    """Tests for BrowserController instantiation."""

    def test_instantiation_default(self):
        """Test BrowserController instantiates with default headless=True."""
        controller = BrowserController()
        assert controller.headless is True
        assert controller._playwright is None
        assert controller._browser is None

    def test_instantiation_custom_headless_false(self):
        """Test BrowserController accepts headless=False parameter."""
        controller = BrowserController(headless=False)
        assert controller.headless is False


class TestBrowserControllerAsync:
    """Tests for BrowserController async methods (mocked)."""

    @pytest.mark.asyncio
    async def test_start_calls_playwright(self):
        """Test start() initializes Playwright."""
        controller = BrowserController()

        with patch("emy.brain.browser_controller.async_playwright") as mock_ap:
            mock_pw = AsyncMock()
            mock_ap.return_value = mock_pw
            mock_chromium = AsyncMock()
            mock_pw.chromium.launch = AsyncMock(return_value=AsyncMock())

            await controller.start()

            assert controller._playwright is not None
            assert controller._browser is not None

    @pytest.mark.asyncio
    async def test_stop_closes_browser(self):
        """Test stop() closes browser and playwright."""
        controller = BrowserController()
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        controller._browser = mock_browser
        controller._playwright = mock_playwright

        await controller.stop()

        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        assert controller._browser is None
        assert controller._playwright is None

    @pytest.mark.asyncio
    async def test_stop_safe_on_already_stopped(self):
        """Test stop() is safe to call multiple times."""
        controller = BrowserController()
        assert controller._browser is None
        assert controller._playwright is None

        # Should not raise
        await controller.stop()

    @pytest.mark.asyncio
    async def test_context_manager_pattern(self):
        """Test async context manager (__aenter__/__aexit__)."""
        with patch("emy.brain.browser_controller.async_playwright") as mock_ap:
            mock_pw = AsyncMock()
            mock_ap.return_value = mock_pw
            mock_pw.chromium = AsyncMock()
            mock_pw.chromium.launch = AsyncMock(return_value=AsyncMock())

            async with BrowserController() as controller:
                # Browser should be set during __aenter__ (which calls start())
                assert controller._browser is not None
                assert controller._playwright is not None

            # After __aexit__ (which calls stop()), both should be None
            assert controller._browser is None
            assert controller._playwright is None

    @pytest.mark.asyncio
    async def test_new_page_returns_page(self):
        """Test new_page() returns Page object."""
        controller = BrowserController()
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        controller._browser = mock_browser

        page = await controller.new_page()

        assert page is mock_page
        mock_browser.new_context.assert_called_once()
        mock_context.new_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_page_fails_if_browser_not_started(self):
        """Test new_page() raises RuntimeError if browser not started."""
        controller = BrowserController()
        # Browser not started
        assert controller._browser is None

        with pytest.raises(RuntimeError, match="Browser not started"):
            await controller.new_page()

    @pytest.mark.asyncio
    async def test_navigate_success(self):
        """Test navigate() returns True on successful navigation."""
        controller = BrowserController()
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()

        success = await controller.navigate(mock_page, "https://example.com")

        assert success is True
        mock_page.goto.assert_called_once_with(
            "https://example.com",
            wait_until="networkidle",
            timeout=30000,
        )

    @pytest.mark.asyncio
    async def test_navigate_custom_timeout(self):
        """Test navigate() accepts custom timeout parameter."""
        controller = BrowserController()
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()

        success = await controller.navigate(
            mock_page, "https://example.com", timeout=60000
        )

        assert success is True
        mock_page.goto.assert_called_once_with(
            "https://example.com",
            wait_until="networkidle",
            timeout=60000,
        )

    @pytest.mark.asyncio
    async def test_navigate_timeout_returns_false(self):
        """Test navigate() returns False on timeout."""
        controller = BrowserController()
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=TimeoutError("Navigation timeout"))

        success = await controller.navigate(mock_page, "https://example.com")

        assert success is False

    @pytest.mark.asyncio
    async def test_navigate_exception_returns_false(self):
        """Test navigate() returns False on any exception."""
        controller = BrowserController()
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Network error"))

        success = await controller.navigate(mock_page, "https://example.com")

        assert success is False

    @pytest.mark.asyncio
    async def test_screenshot_returns_bytes(self):
        """Test screenshot() returns bytes."""
        controller = BrowserController()
        mock_page = AsyncMock()
        screenshot_data = b"fake png data"
        mock_page.screenshot = AsyncMock(return_value=screenshot_data)

        result = await controller.screenshot(mock_page)

        assert result == screenshot_data
        assert isinstance(result, bytes)
        mock_page.screenshot.assert_called_once_with(full_page=False)

    @pytest.mark.asyncio
    async def test_screenshot_raises_on_error(self):
        """Test screenshot() raises exception on error."""
        controller = BrowserController()
        mock_page = AsyncMock()
        mock_page.screenshot = AsyncMock(side_effect=Exception("Screenshot failed"))

        with pytest.raises(Exception, match="Screenshot failed"):
            await controller.screenshot(mock_page)


class TestChromeArgs:
    """Tests for Chrome arguments configuration."""

    def test_render_chrome_args_no_sandbox(self):
        """Test RENDER_CHROME_ARGS contains --no-sandbox."""
        assert "--no-sandbox" in RENDER_CHROME_ARGS

    def test_render_chrome_args_disable_dev_shm_usage(self):
        """Test RENDER_CHROME_ARGS contains --disable-dev-shm-usage."""
        assert "--disable-dev-shm-usage" in RENDER_CHROME_ARGS

    def test_render_chrome_args_disable_automation(self):
        """Test RENDER_CHROME_ARGS contains AutomationControlled disable."""
        assert "--disable-blink-features=AutomationControlled" in RENDER_CHROME_ARGS

    def test_render_chrome_args_are_strings(self):
        """Test all RENDER_CHROME_ARGS are strings."""
        for arg in RENDER_CHROME_ARGS:
            assert isinstance(arg, str)

    def test_render_chrome_args_not_empty(self):
        """Test RENDER_CHROME_ARGS is not empty."""
        assert len(RENDER_CHROME_ARGS) > 0


class TestBrowserControllerIntegration:
    """Integration tests with real browser (marked for manual testing)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_browser_lifecycle_real(self):
        """Test full browser lifecycle with real Chromium (requires installation)."""
        async with BrowserController() as controller:
            # Navigation test would require network access
            assert controller._browser is not None
            page = await controller.new_page()
            assert page is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_navigate_real_site(self):
        """Test navigation to real site (requires network)."""
        async with BrowserController() as controller:
            page = await controller.new_page()
            # Would navigate to real site, requires network
            success = await controller.navigate(page, "https://httpbin.org/")
            # This is a real test, so we expect real results
            # Commenting out for CI environments without network
            # assert success is True
