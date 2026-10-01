import ipaddress
import socket
import time
from urllib.parse import urlsplit

from langchain_core.tools import ToolException, tool
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as conditions
from selenium.webdriver.support.ui import WebDriverWait

from app.config import Settings


def check_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as exc:
        raise ToolException("Invalid URL") from exc
    if (
        parsed.scheme not in ("http", "https") or not host
        or parsed.username is not None or parsed.password is not None
        or port == 0 or "\\" in parsed.netloc or "%" in host
    ):
        raise ToolException("Only public HTTP(S) URLs without embedded credentials are allowed")
    if host == "localhost" or host.endswith((".localhost", ".local")) or host == "local":
        raise ToolException("Local destinations are not allowed")
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            answers = socket.getaddrinfo(
                host, port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
            addresses = [ipaddress.ip_address(answer[4][0]) for answer in answers]
        except (OSError, ValueError, UnicodeError) as exc:
            raise ToolException("Could not verify public destination addresses") from exc
    if not addresses or any(not address.is_global or address.is_multicast for address in addresses):
        raise ToolException("Private and non-public IP addresses are not allowed")


def browser_tools(driver, settings: Settings, deadline: float):
    def check_session() -> None:
        if time.monotonic() >= deadline:
            raise ToolException("Task time limit reached")
        current = driver.current_url
        if current and current != "data:," and not current.startswith("about:blank"):
            check_url(current)

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
        """Navigate to a public HTTP(S) URL and report the resulting page title."""
        check_url(url)
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
            """Click the first clickable element matching a CSS selector on the public website."""
            element = find_element(selector, clickable=True)
            try:
                element.click()
                check_session()
                return "Element clicked"
            except WebDriverException as exc:
                raise ToolException("Could not click element") from exc

        @tool
        def fill_element(selector: str, value: str) -> str:
            """Replace an input field's text with a provided value on the public website."""
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
