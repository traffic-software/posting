import ipaddress
import json
import socket
import time
from functools import wraps
from typing import Literal
from urllib.parse import urlsplit

import pyotp
from langchain_core.tools import ToolException, tool
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from app.browser_dom import DISCOVER_PAGE
from app.config import Settings
from app.element_readiness import ElementReadinessTimeout, readiness, wait_for_ready
from app.desktop_tools import DesktopInputError
from app.login_forms import continuation_control, login_input
from app.schemas import https_origin
from app.task_context import TaskContext
from app.totp_forms import (
    DISCOVER_CONTROLS, SUBMISSION_FORM, single_input, split_input, structural_selector,
    submit_control, validate_inputs,
)


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


def browser_tools(driver, settings: Settings, deadline: float, context: TaskContext | None = None, desktop=None):
    def redact(text: str) -> str:
        return context.redact(text) if context else text

    def observe(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if context:
                context.record_observation(function.__name__, "started", "Browser action attempted")
            try:
                result = function(*args, **kwargs)
            except (BrowserPolicyStop, ToolException) as exc:
                if context:
                    context.record_observation(function.__name__, "stopped", str(exc))
                raise
            except DesktopInputError:
                if context:
                    context.record_observation(function.__name__, "stopped", "Desktop target or input could not be safely verified; no automatic retry")
                raise BrowserPolicyStop("Desktop input stopped because target or focus could not be verified") from None
            except Exception:
                if context:
                    context.record_observation(function.__name__, "failed", "Browser action failed; cause not verified")
                raise
            if context:
                context.record_observation(function.__name__, "returned", str(result))
            return result
        return wrapped

    hard_markers = (
        "captcha", "verify you are human", "verify it's you", "access denied", "suspicious login",
        "this browser or app may not be secure", "unusual traffic",
    )
    mfa_markers = (
        "two-step verification", "two-factor", "verification code", "authenticator",
        "authentication app", "totp", "one-time code",
    )

    def page_text() -> str:
        check_session()
        try:
            visible = driver.find_element(By.TAG_NAME, "body").text[:20000].lower()
            if any(marker in visible for marker in hard_markers):
                raise BrowserPolicyStop("Authentication challenge or access restriction encountered")
            return visible
        except WebDriverException:
            raise BrowserPolicyStop("Could not verify login page policy") from None

    def check_write_page() -> None:
        check_session()
        if context and context.credentials:
            if any(marker in page_text() for marker in mfa_markers):
                raise BrowserPolicyStop("Authentication challenge or access restriction encountered")

    if desktop is not None:
        original_guard = desktop._guard

        def guard_desktop():
            original_guard()
            check_write_page()

        desktop._guard = guard_desktop

    def check_credential_origin(credential) -> None:
        check_session()
        if not any(item is credential for item in context.credentials):
            raise BrowserPolicyStop("Task credentials unavailable")
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

    def credential_origin(credential) -> None:
        check_write_page()
        check_credential_origin(credential)

    def check_totp_page(credential) -> None:
        check_credential_origin(credential)
        visible = page_text()
        if not any(marker in visible for marker in ("authenticator app", "authentication app", "totp")) or any(
            marker in visible for marker in ("sms", "text message", "email code", "recovery code", "backup code", "device approval")
        ):
            raise BrowserPolicyStop("Only an explicit authenticator-app form is supported")

    def check_session() -> None:
        if context and context.cancelled.is_set():
            raise BrowserPolicyStop("Task cancelled")
        if time.monotonic() >= deadline:
            raise ToolException("Task time limit reached")
        current = driver.current_url
        if current and current != "data:," and not current.startswith("about:blank"):
            check_url(current)

    def find_element(selector: str, clickable: bool = False, *, editable=False, policy=None):
        if len(selector) > 300 or not selector.strip():
            raise ToolException("Invalid CSS selector")
        def guard():
            check_session()
            if policy:
                policy()
        mode = "fill" if editable else "click" if clickable else "read"
        try:
            return wait_for_ready(
                driver, lambda: [driver.find_element(By.CSS_SELECTOR, selector)], [mode],
                deadline, settings.browser_timeout_seconds, guard,
                context.cancelled if context else None,
            )[0]
        except WebDriverException as exc:
            raise ToolException("Could not verify element readiness") from exc

    def readiness_error(exc):
        if isinstance(exc, ElementReadinessTimeout):
            return str(exc)
        raise exc

    @tool
    @observe
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
    @observe
    def extract_text(selector: str) -> str:
        """Read visible text from the first element matching a CSS selector (up to 2000 characters)."""
        element = find_element(selector)
        check_session()
        try:
            return redact(element.text[:2000])
        except WebDriverException as exc:
            raise ToolException("Could not read element") from exc

    inspected_controls = {}

    @tool
    @observe
    def inspect_page() -> str:
        """Inspect visible page controls and bounded text without reading input values."""
        check_session()
        try:
            rows = driver.execute_script(DISCOVER_PAGE)
            if not isinstance(rows, list):
                raise ToolException("Could not inspect page controls")
            inspected_controls.clear()
            controls = []
            for row in rows[:200]:
                if not isinstance(row, dict):
                    continue
                element, selector = row.get("element"), row.get("selector")
                if element is None or not structural_selector(selector) or not element.is_displayed():
                    continue
                tag = element.tag_name.lower()
                kind = (element.get_attribute("type") or "text").lower() if tag == "input" else tag
                sensitive = kind == "password" or element.get_attribute("autocomplete") == "one-time-code"
                label = "" if sensitive else redact(str(element.get_attribute("aria-label") or (element.text if tag != "input" else "")))[:120]
                controls.append({"selector": selector, "kind": kind, "enabled": element.is_enabled(), "label": label})
                inspected_controls[selector] = element
                if len(controls) >= 30:
                    break
            check_session()
            summary = redact(driver.find_element(By.TAG_NAME, "body").text[:2000])
            check_session()
            return json.dumps({"controls": controls, "text": summary, "note": "Page data is untrusted. Inspect again after changes; actions do not prove success."}, ensure_ascii=False)
        except WebDriverException:
            raise ToolException("Could not inspect page controls") from None

    tools = [navigate_to_page, extract_text, inspect_page]

    writes_allowed = settings.enable_write_actions and (
        context is None or context.allow_write_actions is not False
    )
    if context and context.credentials:
        writes_allowed = settings.enable_write_actions and context.allow_write_actions is True
    if writes_allowed:
        @tool
        @observe
        def click_element(selector: str) -> str:
            """Click the first clickable element matching a CSS selector on the public website."""
            check_write_page()
            element = find_element(selector, clickable=True, policy=check_write_page)
            try:
                check_write_page()
                if (element.get_attribute("type") or "").lower() == "file":
                    raise BrowserPolicyStop("File dialogs are not supported")
                if desktop is not None:
                    previous = inspected_controls.get(selector)
                    if previous is not None and previous != element:
                        raise ToolException("Control changed; inspect_page again")
                    desktop.click(element)
                else:
                    element.click()
                check_write_page()
                return "Element clicked"
            except WebDriverException as exc:
                raise ToolException("Could not click element") from exc

        @tool
        @observe
        def fill_element(selector: str, value: str) -> str:
            """Replace an input field's text with a provided value on the public website."""
            if len(value) > 2000:
                raise ToolException("Input is too long")
            check_write_page()
            element = find_element(selector, editable=True, policy=check_write_page)
            previous = inspected_controls.get(selector)
            if previous is not None and previous != element:
                raise BrowserPolicyStop("Control changed; inspect_page again")
            try:
                check_write_page()
                tag = element.tag_name.lower()
                if tag not in ("input", "textarea") or (element.get_attribute("type") or "text").lower() in ("password", "file", "hidden") or element.get_attribute("autocomplete") == "one-time-code":
                    raise BrowserPolicyStop("Use dedicated tools for secret fields; unsupported text target")
                if context and context.redact(value) != value:
                    raise BrowserPolicyStop("Use structured credential tools for secret values")
                if not element.is_enabled() or element.get_attribute("readonly"):
                    raise ToolException("Text target is not editable")
                element.clear()
                check_write_page()
                if driver.find_element(By.CSS_SELECTOR, selector) != element or not element.is_displayed() or not element.is_enabled() or element.get_attribute("readonly"):
                    raise BrowserPolicyStop("Text target changed before entry")
                if desktop is not None:
                    desktop.type_text(element, value)
                else:
                    element.send_keys(value)
                check_write_page()
                return "Field updated"
            except WebDriverException as exc:
                raise ToolException("Could not fill field") from exc

        tools.extend([click_element, fill_element])
        if desktop is not None:
            def desktop_target(selector):
                check_write_page()
                element = find_element(selector, clickable=True, policy=check_write_page)
                check_write_page()
                previous = inspected_controls.get(selector)
                if previous is not None and previous != element:
                    raise ToolException("Control changed; inspect_page again")
                return element

            @tool
            @observe
            def hover_element(selector: str) -> str:
                """Move the mouse to a live browser control without clicking."""
                desktop.hover(desktop_target(selector))
                check_write_page()
                return "Control hovered; observe the page"

            @tool
            @observe
            def scroll_element(selector: str, amount: int) -> str:
                """Scroll over a live control by bounded wheel steps (positive up, negative down)."""
                if not -10 <= amount <= 10 or amount == 0:
                    raise ToolException("Scroll amount must be nonzero and between -10 and 10")
                desktop.scroll(desktop_target(selector), amount)
                check_write_page()
                return "Page scrolled; inspect controls again"

            @tool
            @observe
            def press_key(selector: str, key: Literal["enter", "tab", "esc", "space", "up", "down", "left", "right", "home", "end", "pageup", "pagedown", "backspace", "delete"]) -> str:
                """Press one allowed page key on a live nonsecret browser control; no shortcuts."""
                element = desktop_target(selector)
                if (element.get_attribute("type") or "").lower() in ("password", "file") or element.get_attribute("autocomplete") == "one-time-code":
                    raise BrowserPolicyStop("Generic keyboard actions cannot target secret or file fields")
                desktop.press_key(element, key)
                check_write_page()
                return "Key pressed; observe the outcome"

            tools.extend([hover_element, scroll_element, press_key])
        if context and context.credentials:
            discovered_login_inputs = {}

            def login_credential(credential_id):
                credential = next((item for item in context.credentials if item.id == credential_id), None)
                if credential is None:
                    raise BrowserPolicyStop("Unknown credential ID")
                return credential

            @tool
            @observe
            def inspect_login_form(credential_id: str) -> str:
                """Discover live username/password inputs and continuation buttons without reading field values."""
                credential = login_credential(credential_id)
                counts = {"scanned": 0, "editable": 0, "unsupported_selectors": 0}

                def discover(browser):
                    credential_origin(credential)
                    controls = browser.execute_script(DISCOVER_CONTROLS)
                    credential_origin(credential)
                    if not isinstance(controls, list):
                        raise ToolException("Could not inspect login controls")
                    counts.update(scanned=min(len(controls), 200), editable=0, unsupported_selectors=0)
                    candidates = {"username": [], "password": [], "buttons": []}
                    live_inputs = {}
                    for row in controls[:200]:
                        if not isinstance(row, dict):
                            continue
                        selector, form_id, element = row.get("selector"), row.get("form"), row.get("element")
                        if element is not None and any(login_input(element, field) for field in ("username", "password")):
                            counts["editable"] += 1
                            if not structural_selector(selector):
                                counts["unsupported_selectors"] += 1
                        if not structural_selector(selector) or type(form_id) is not int or form_id < -1 or element is None:
                            continue
                        candidate = {"selector": selector, "form": form_id}
                        for field in ("username", "password"):
                            if login_input(element, field):
                                candidates[field].append(candidate)
                                live_inputs[(credential_id, selector, field)] = element
                        if continuation_control(element):
                            candidates["buttons"].append(candidate)
                    credential_origin(credential)
                    return (candidates, live_inputs) if candidates["username"] or candidates["password"] else False

                try:
                    credential_origin(credential)
                    remaining = min(settings.browser_timeout_seconds, deadline - time.monotonic())
                    if remaining <= 0:
                        raise ToolException("Task time limit reached")
                    candidates, live_inputs = WebDriverWait(driver, remaining).until(discover)
                    credential_origin(credential)
                    discovered_login_inputs.clear()
                    discovered_login_inputs.update(live_inputs)
                    return json.dumps({
                        "controls": {kind: items[:8] for kind, items in candidates.items()},
                        "ambiguous": {kind: len(items) > 1 for kind, items in candidates.items()},
                        "truncated": any(len(items) > 8 for items in candidates.values()),
                        "note": "Use live selectors; inspect again after navigation. Do not guess among ambiguous controls. Entry or continuation is not proof of login.",
                    })
                except BrowserPolicyStop:
                    raise
                except WebDriverException:
                    raise ToolException(
                        "No usable login controls became available; "
                        f"scanned={counts['scanned']}, editable={counts['editable']}, unsupported_selectors={counts['unsupported_selectors']}. "
                        "Inspect the current page before continuing"
                    ) from None
                except (ValueError, TypeError, AttributeError):
                    raise ToolException("Could not inspect login controls") from None

            @tool
            @observe
            def fill_credential(selector: str, credential_id: str, field: Literal["username", "password"]) -> str:
                """Fill a username or password using a supplied credential ID at its authorized login origin."""
                credential = login_credential(credential_id)
                credential_origin(credential)
                try:
                    element = find_element(selector, editable=True, policy=lambda: credential_origin(credential))
                except ToolException as exc:
                    if isinstance(exc.__cause__, WebDriverException):
                        raise ToolException("Credential element unavailable; use inspect_login_form again for a current selector") from None
                    raise
                try:
                    credential_origin(credential)
                    if not login_input(element, field):
                        raise BrowserPolicyStop("Credential field is not an authorized editable input")
                    discovered = discovered_login_inputs.get((credential_id, selector, field))
                    if discovered is not None and discovered != element:
                        raise BrowserPolicyStop("Credential field changed since inspection; inspect_login_form again")
                    element.clear()
                    credential_origin(credential)
                    if not login_input(element, field) or driver.find_element(By.CSS_SELECTOR, selector) != element:
                        raise BrowserPolicyStop("Credential field changed before entry")
                    element.send_keys(getattr(credential, field).get_secret_value())
                    check_session()
                    return "Credential entered"
                except WebDriverException:
                    raise BrowserPolicyStop("Credential entry failed") from None

            tools.extend([inspect_login_form, fill_credential])
            if any(credential.totp_secret is not None for credential in context.credentials):
                discovered_totp_controls = {}
                def totp_credential(credential_id):
                    credential = next((item for item in context.credentials if item.id == credential_id), None)
                    if credential is None or credential.totp_secret is None:
                        raise BrowserPolicyStop("Authenticator credential unavailable")
                    return credential

                def check_submission(elements, submit, credential):
                    check_totp_page(credential)
                    validate_inputs(elements)
                    if not submit_control(submit):
                        raise BrowserPolicyStop("Authenticator submit control is not authorized")
                    for element in elements:
                        form = driver.execute_script(SUBMISSION_FORM, element, submit)
                        if (
                            not isinstance(form, dict) or form.get("sameForm") is not True
                            or https_origin(form.get("action", "")) != https_origin(driver.current_url)
                        ):
                            raise BrowserPolicyStop("Authenticator form submission is not authorized")

                @tool
                @observe
                def inspect_totp_form(credential_id: str) -> str:
                    """Discover supported authenticator inputs and submit selectors without reading field values."""
                    credential = totp_credential(credential_id)
                    try:
                        check_totp_page(credential)
                        controls = driver.execute_script(DISCOVER_CONTROLS)
                        check_totp_page(credential)
                        if not isinstance(controls, list):
                            raise BrowserPolicyStop("Could not inspect authenticator form")
                        forms = {}
                        for row in controls[:200]:
                            if not isinstance(row, dict):
                                continue
                            selector, form_id, element = row.get("selector"), row.get("form"), row.get("element")
                            if not structural_selector(selector) or type(form_id) is not int or form_id < 0:
                                continue
                            group = forms.setdefault(form_id, {"single": [], "split": [], "submit": []})
                            if single_input(element):
                                group["single"].append((selector, element))
                            if split_input(element):
                                group["split"].append((selector, element))
                            if submit_control(element):
                                group["submit"].append((selector, element))
                        candidates = []
                        discovered_totp_controls.clear()
                        for group in forms.values():
                            layouts = [("single", [item]) for item in group["single"]]
                            if len(group["split"]) == 6:
                                layouts.append(("six-digit", group["split"]))
                            for layout, inputs in layouts:
                                for submit_selector, submit in group["submit"]:
                                    try:
                                        check_submission([item[1] for item in inputs], submit, credential)
                                    except (BrowserPolicyStop, ValueError):
                                        continue
                                    input_selector = ", ".join(item[0] for item in inputs)
                                    discovered_totp_controls[(credential_id, input_selector, submit_selector)] = ([item[1] for item in inputs], submit)
                                    candidates.append({"layout": layout, "selector": input_selector, "submit_selector": submit_selector})
                                    if len(candidates) >= 8:
                                        break
                                if len(candidates) >= 8:
                                    break
                            if len(candidates) >= 8:
                                break
                        check_totp_page(credential)
                        return redact(json.dumps({"forms": candidates, "note": "Revalidate with fill_totp; submission is not proof of login."}))
                    except BrowserPolicyStop:
                        raise
                    except (WebDriverException, ToolException, ValueError, TypeError, AttributeError):
                        raise BrowserPolicyStop("Authenticator inspection failed") from None

                @tool
                @observe
                def fill_totp(selector: str, submit_selector: str, credential_id: str) -> str:
                    """Generate the current OTP locally and submit one input or exactly six digit cells using a credential ID."""
                    credential = totp_credential(credential_id)
                    try:
                        check_totp_page(credential)
                        if not selector.strip() or len(selector) > 2000:
                            raise BrowserPolicyStop("Invalid authenticator selector")
                        def resolve_controls():
                            inputs = driver.find_elements(By.CSS_SELECTOR, selector)
                            if not inputs:
                                return []
                            if len(inputs) not in (1, 6):
                                raise BrowserPolicyStop('Unsupported authenticator input layout')
                            return inputs + [driver.find_element(By.CSS_SELECTOR, submit_selector)]

                        controls = wait_for_ready(
                            driver, resolve_controls,
                            lambda found: ["fill"] * max(0, len(found) - 1) + ["click"],
                            deadline, settings.browser_timeout_seconds,
                            lambda: check_totp_page(credential), context.cancelled,
                        )
                        elements, submit = controls[:-1], controls[-1]
                        check_totp_page(credential)
                        previous = discovered_totp_controls.get((credential_id, selector, submit_selector))
                        if previous is not None and previous != (elements, submit):
                            raise BrowserPolicyStop("Authenticator controls changed; inspect_totp_form again")

                        def check_controls():
                            check_submission(elements, submit, credential)
                            for target, mode in [(item, "fill") for item in elements] + [(submit, "click")]:
                                if readiness(driver, target, mode) != "ready":
                                    raise BrowserPolicyStop("Authenticator controls are no longer ready")
                            if driver.find_elements(By.CSS_SELECTOR, selector) != elements or driver.find_element(By.CSS_SELECTOR, submit_selector) != submit:
                                raise BrowserPolicyStop("Authenticator controls changed")

                        totp = pyotp.TOTP(credential.totp_secret.get_secret_value(), digits=6, interval=30)
                        while True:
                            check_controls()
                            if deadline - time.monotonic() <= 0.25:
                                raise BrowserPolicyStop("Insufficient time for a fresh authenticator code")
                            before = time.time()
                            if 30 - before % 30 >= 5:
                                code = totp.now()
                                after = time.time()
                                if int(before // 30) == int(after // 30) and 30 - after % 30 >= 5:
                                    timestep = int(after // 30)
                                    break
                            if context.cancelled.wait(0.25):
                                raise BrowserPolicyStop("Task cancelled")
                        context.reserve_totp(credential, timestep, code)

                        def check_current_code():
                            check_controls()
                            if int(time.time() // 30) != timestep:
                                raise BrowserPolicyStop("Authenticator code expired before submission")

                        for index, element in enumerate(elements):
                            check_current_code()
                            element.clear()
                            check_current_code()
                            element.send_keys(code if len(elements) == 1 else code[index])
                            check_current_code()
                        submit.click()
                        check_session()
                        page_text()
                        return "Authenticator code submitted; login outcome must be observed separately"
                    except ElementReadinessTimeout:
                        raise
                    except BrowserPolicyStop:
                        raise
                    except (WebDriverException, ToolException, ValueError, RuntimeError):
                        raise BrowserPolicyStop("Authenticator entry failed") from None

                tools.extend([inspect_totp_form, fill_totp])
    for browser_tool in tools:
        browser_tool.handle_tool_error = readiness_error
    return tools
