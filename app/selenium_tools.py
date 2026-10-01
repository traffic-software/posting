import ipaddress
import socket
import time
from typing import Literal
from urllib.parse import urlsplit

from langchain_core.tools import ToolException, tool
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as conditions
from selenium.webdriver.support.ui import WebDriverWait

from app.config import Settings
from app.schemas import https_origin
from app.task_context import TaskContext


class BrowserPolicyStop(RuntimeError):
    pass


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


def browser_tools(driver, settings: Settings, deadline: float, context: TaskContext | None = None):
    def redact(text: str) -> str:
        return context.redact(text) if context else text

    def check_write_page() -> None:
        check_session()
        if context and context.credentials:
            try:
                visible = driver.find_element(By.TAG_NAME, "body").text[:20000].lower()
                markers = (
                    "captcha", "verify you are human", "verify it's you", "two-step verification",
                    "two-factor", "verification code", "access denied", "suspicious login",
                    "this browser or app may not be secure", "unusual traffic",
                )
                if any(marker in visible for marker in markers):
                    raise BrowserPolicyStop("Authentication challenge or access restriction encountered")
            except WebDriverException:
                raise BrowserPolicyStop("Could not verify login page policy") from None

    def credential_origin(credential) -> None:
        check_write_page()
        if context.credential_expires_at is not None and time.time() >= context.credential_expires_at:
            raise BrowserPolicyStop("Task credentials expired")
        try:
            origin = https_origin(driver.current_url)
            frame = driver.execute_script("return {origin: window.location.origin, top: window === window.top};")
            if (
                origin not in credential.origins or not isinstance(frame, dict)
                or not frame.get("top") or frame.get("origin") != origin
            ):
                raise BrowserPolicyStop("Credential entry is not authorized at this origin or frame")
        except (ValueError, WebDriverException):
            raise BrowserPolicyStop("Could not verify credential origin") from None

    def check_session() -> None:
        if context and context.cancelled.is_set():
            raise BrowserPolicyStop("Task cancelled")
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
            return redact(f"Opened {urlsplit(driver.current_url).hostname}; title: {driver.title[:200]}")
        except WebDriverException as exc:
            raise ToolException("Browser navigation failed") from exc

    @tool
    def extract_text(selector: str) -> str:
        """Read visible text from the first element matching a CSS selector (up to 2000 characters)."""
        element = find_element(selector)
        check_session()
        try:
            return redact(element.text[:2000])
        except WebDriverException as exc:
            raise ToolException("Could not read element") from exc

    tools = [navigate_to_page, extract_text]

    writes_allowed = settings.enable_write_actions and (
        context is None or context.allow_write_actions is not False
    )
    if context and context.credentials:
        writes_allowed = settings.enable_write_actions and context.allow_write_actions is True
    if writes_allowed:
        @tool
        def click_element(selector: str) -> str:
            """Click the first clickable element matching a CSS selector on the public website."""
            check_write_page()
            element = find_element(selector, clickable=True)
            try:
                check_write_page()
                element.click()
                check_write_page()
                return "Element clicked"
            except WebDriverException as exc:
                raise ToolException("Could not click element") from exc

        @tool
        def fill_element(selector: str, value: str) -> str:
            """Replace an input field's text with a provided value on the public website."""
            if len(value) > 2000:
                raise ToolException("Input is too long")
            check_write_page()
            element = find_element(selector)
            try:
                check_write_page()
                element.clear()
                element.send_keys(value)
                check_session()
                return "Field updated"
            except WebDriverException as exc:
                raise ToolException("Could not fill field") from exc

        tools.extend([click_element, fill_element])
        if context and context.credentials:
            @tool
            def fill_credential(selector: str, credential_id: str, field: Literal["username", "password"]) -> str:
                """Fill a username or password using a supplied credential ID at its authorized login origin."""
                credential = next((item for item in context.credentials if item.id == credential_id), None)
                if credential is None:
                    raise BrowserPolicyStop("Unknown credential ID")
                credential_origin(credential)
                element = find_element(selector)
                try:
                    credential_origin(credential)
                    if element.tag_name.lower() != "input":
                        raise BrowserPolicyStop("Credentials may only be entered into input fields")
                    input_type = (element.get_attribute("type") or "text").lower()
                    if (field == "password" and input_type != "password") or (
                        field == "username" and input_type not in ("text", "email", "tel")
                    ):
                        raise BrowserPolicyStop("Credential field type is not authorized")
                    element.clear()
                    credential_origin(credential)
                    element.send_keys(getattr(credential, field).get_secret_value())
                    check_session()
                    return "Credential entered"
                except WebDriverException:
                    raise BrowserPolicyStop("Credential entry failed") from None

            tools.append(fill_credential)
    return tools
