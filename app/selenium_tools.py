import ipaddress
import time
from urllib.parse import urlsplit

from langchain_core.tools import ToolException, tool
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as conditions
from selenium.webdriver.support.ui import WebDriverWait

from app.config import Settings


def check_url(url: str, allowed_hosts: frozenset[str]) -> None:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
    except ValueError as exc:
        raise ToolException("Invalid URL") from exc
    if parsed.scheme not in ("http", "https") or not host or parsed.username or parsed.password:
        raise ToolException("Only approved HTTP(S) URLs without embedded credentials are allowed")
    if host not in allowed_hosts or host == "localhost" or host.endswith(".local"):
        raise ToolException("This website is not on the approved host list")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if not address.is_global:
        raise ToolException("Private and non-public IP addresses are not allowed")


def browser_tools(driver, settings: Settings, deadline: float):
    allowed_hosts = settings.host_allowlist

    def check_session() -> None:
        if time.monotonic() >= deadline:
            raise ToolException("Task time limit reached")
        current = driver.current_url
        if current and current != "data:," and not current.startswith("about:blank"):
            check_url(current, allowed_hosts)

    def find_element(selector: str, clickable: bool = False):
        if len(selector) > 300 or not selector.strip():
            raise ToolException("Invalid CSS selector")
        check_session()
        condition = (conditions.element_to_be_clickable if clickable else conditions.visibility_of_element_located)
        try:
            return WebDriverWait(driver, settings.browser_timeout_seconds).until(
                condition((By.CSS_SELECTOR, selector))
            )
        except WebDriverException as exc:
            raise ToolException("Element not available") from exc

    @tool
    def navigate_to_page(url: str) -> str:
        """Navigate to a URL on the approved website list and report the resulting page title."""
        check_url(url, allowed_hosts)
        check_session()
        try:
            driver.get(url)
            check_session()
            return f"Opened {urlsplit(driver.current_url).hostname}; title: {driver.title[:200]}"
        except WebDriverException as exc:
            raise ToolException("Browser navigation failed") from exc

    @tool
    def extract_text(selector: str) -> str:
        """Read visible text from the first element matching a CSS selector (up to 2000 characters)."""
        element = find_element(selector)
        check_session()
        try:
            return element.text[:2000]
        except WebDriverException as exc:
            raise ToolException("Could not read element") from exc

    tools = [navigate_to_page, extract_text]

    if settings.enable_write_actions:
        @tool
        def click_element(selector: str) -> str:
            """Click the first clickable element matching a CSS selector on the approved site."""
            element = find_element(selector, clickable=True)
            try:
                element.click()
                check_session()
                return "Element clicked"
            except WebDriverException as exc:
                raise ToolException("Could not click element") from exc

        @tool
        def fill_element(selector: str, value: str) -> str:
            """Replace an input field's text with a provided value on the approved site."""
            if len(value) > 2000:
                raise ToolException("Input is too long")
            element = find_element(selector)
            try:
                element.clear()
                element.send_keys(value)
                check_session()
                return "Field updated"
            except WebDriverException as exc:
                raise ToolException("Could not fill field") from exc

        tools.extend([click_element, fill_element])
    return tools
