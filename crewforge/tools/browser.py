"""Browser automation tool using Playwright."""

import asyncio
from typing import Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

try:
    from playwright.sync_api import sync_playwright, Browser, Page
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class BrowserNavigateInput(BaseModel):
    """Input schema for browser navigation."""

    url: str = Field(..., description="URL to navigate to")
    wait_for: str = Field(
        default="load",
        description="Wait for: 'load', 'domcontentloaded', or 'networkidle'",
    )
    screenshot_path: Optional[str] = Field(
        default=None, description="Path to save screenshot (optional)"
    )


class BrowserNavigateTool(BaseTool):
    """Tool to navigate to a URL and optionally take a screenshot."""

    name: str = "browser_navigate"
    description: str = """Navigate to a URL and get page information.
    Can optionally take a screenshot for visual verification."""
    args_schema: Type[BaseModel] = BrowserNavigateInput

    def _run(
        self,
        url: str,
        wait_for: str = "load",
        screenshot_path: Optional[str] = None,
    ) -> str:
        """Navigate to URL."""
        if not PLAYWRIGHT_AVAILABLE:
            return "Error: Playwright is not installed. Run 'pip install playwright && playwright install'"

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Navigate
                page.goto(url, wait_until=wait_for)

                # Get page info
                title = page.title()
                current_url = page.url

                # Take screenshot if requested
                if screenshot_path:
                    page.screenshot(path=screenshot_path)

                browser.close()

                result = f"Navigated to: {current_url}\nTitle: {title}"
                if screenshot_path:
                    result += f"\nScreenshot saved to: {screenshot_path}"
                return result

        except Exception as e:
            return f"Error navigating: {str(e)}"


class BrowserClickInput(BaseModel):
    """Input schema for browser click action."""

    url: str = Field(..., description="URL to navigate to first")
    selector: str = Field(..., description="CSS selector of element to click")
    wait_after: int = Field(
        default=1000, description="Milliseconds to wait after clicking"
    )


class BrowserClickTool(BaseTool):
    """Tool to click an element on a page."""

    name: str = "browser_click"
    description: str = "Navigate to a URL and click an element using CSS selector."
    args_schema: Type[BaseModel] = BrowserClickInput

    def _run(self, url: str, selector: str, wait_after: int = 1000) -> str:
        """Click element."""
        if not PLAYWRIGHT_AVAILABLE:
            return "Error: Playwright is not installed."

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.goto(url, wait_until="networkidle")
                page.click(selector)
                page.wait_for_timeout(wait_after)

                new_url = page.url
                browser.close()

                return f"Clicked element '{selector}'. Current URL: {new_url}"

        except Exception as e:
            return f"Error clicking: {str(e)}"


class BrowserFillInput(BaseModel):
    """Input schema for browser form fill."""

    url: str = Field(..., description="URL to navigate to first")
    selector: str = Field(..., description="CSS selector of input element")
    value: str = Field(..., description="Value to fill in")


class BrowserFillTool(BaseTool):
    """Tool to fill a form field."""

    name: str = "browser_fill"
    description: str = "Navigate to a URL and fill a form field."
    args_schema: Type[BaseModel] = BrowserFillInput

    def _run(self, url: str, selector: str, value: str) -> str:
        """Fill form field."""
        if not PLAYWRIGHT_AVAILABLE:
            return "Error: Playwright is not installed."

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.goto(url, wait_until="networkidle")
                page.fill(selector, value)

                browser.close()

                return f"Filled '{selector}' with value."

        except Exception as e:
            return f"Error filling form: {str(e)}"


class BrowserGetContentInput(BaseModel):
    """Input schema for getting page content."""

    url: str = Field(..., description="URL to navigate to")
    selector: Optional[str] = Field(
        default=None, description="CSS selector to get specific content (optional)"
    )


class BrowserGetContentTool(BaseTool):
    """Tool to get page text content."""

    name: str = "browser_get_content"
    description: str = "Navigate to a URL and get the text content of the page or specific element."
    args_schema: Type[BaseModel] = BrowserGetContentInput

    def _run(self, url: str, selector: Optional[str] = None) -> str:
        """Get page content."""
        if not PLAYWRIGHT_AVAILABLE:
            return "Error: Playwright is not installed."

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.goto(url, wait_until="networkidle")

                if selector:
                    element = page.query_selector(selector)
                    if element:
                        content = element.inner_text()
                    else:
                        content = f"Element '{selector}' not found."
                else:
                    content = page.inner_text("body")

                browser.close()

                # Truncate if too long
                if len(content) > 5000:
                    content = content[:5000] + "\n... (truncated)"

                return content

        except Exception as e:
            return f"Error getting content: {str(e)}"


class BrowserTestInput(BaseModel):
    """Input schema for running browser tests."""

    url: str = Field(..., description="Base URL to test")
    test_steps: list[dict] = Field(
        ...,
        description="""List of test steps. Each step is a dict with:
        - action: 'navigate', 'click', 'fill', 'assert_text', 'assert_visible', 'screenshot'
        - selector: CSS selector (for click, fill, assert_*)
        - value: Value to fill or assert
        - path: Screenshot path (for screenshot action)""",
    )


class BrowserTestTool(BaseTool):
    """Tool to run a sequence of browser test steps."""

    name: str = "browser_test"
    description: str = """Run a sequence of browser test steps for E2E testing.
    Actions: navigate, click, fill, assert_text, assert_visible, screenshot"""
    args_schema: Type[BaseModel] = BrowserTestInput

    def _run(self, url: str, test_steps: list[dict]) -> str:
        """Run browser tests."""
        if not PLAYWRIGHT_AVAILABLE:
            return "Error: Playwright is not installed."

        results = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Initial navigation
                page.goto(url, wait_until="networkidle")
                results.append(f"✓ Navigated to {url}")

                for i, step in enumerate(test_steps, 1):
                    action = step.get("action")
                    selector = step.get("selector")
                    value = step.get("value")

                    try:
                        if action == "navigate":
                            page.goto(value, wait_until="networkidle")
                            results.append(f"✓ Step {i}: Navigated to {value}")

                        elif action == "click":
                            page.click(selector)
                            results.append(f"✓ Step {i}: Clicked {selector}")

                        elif action == "fill":
                            page.fill(selector, value)
                            results.append(f"✓ Step {i}: Filled {selector}")

                        elif action == "assert_text":
                            element = page.query_selector(selector)
                            if element:
                                text = element.inner_text()
                                if value in text:
                                    results.append(
                                        f"✓ Step {i}: Found text '{value}' in {selector}"
                                    )
                                else:
                                    results.append(
                                        f"✗ Step {i}: Text '{value}' not found in {selector}"
                                    )
                            else:
                                results.append(
                                    f"✗ Step {i}: Element {selector} not found"
                                )

                        elif action == "assert_visible":
                            if page.is_visible(selector):
                                results.append(
                                    f"✓ Step {i}: Element {selector} is visible"
                                )
                            else:
                                results.append(
                                    f"✗ Step {i}: Element {selector} not visible"
                                )

                        elif action == "screenshot":
                            path = step.get("path", f"screenshot_{i}.png")
                            page.screenshot(path=path)
                            results.append(f"✓ Step {i}: Screenshot saved to {path}")

                        else:
                            results.append(f"? Step {i}: Unknown action '{action}'")

                    except Exception as e:
                        results.append(f"✗ Step {i}: Error - {str(e)}")

                browser.close()

        except Exception as e:
            results.append(f"✗ Browser error: {str(e)}")

        return "\n".join(results)


class BrowserTool:
    """Collection of browser automation tools."""

    @staticmethod
    def get_tools() -> list[BaseTool]:
        """Get all browser tools."""
        return [
            BrowserNavigateTool(),
            BrowserClickTool(),
            BrowserFillTool(),
            BrowserGetContentTool(),
            BrowserTestTool(),
        ]

    @staticmethod
    def install_browsers() -> str:
        """Install Playwright browsers."""
        import subprocess

        try:
            result = subprocess.run(
                ["playwright", "install", "chromium"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return "Playwright browsers installed successfully."
            return f"Error installing browsers: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
