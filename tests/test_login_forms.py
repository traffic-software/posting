from browser_helpers import mock_local_browser
import json
import socket
import time
from pathlib import Path

import pytest
from langchain_core.tools import ToolException
from selenium.common.exceptions import NoSuchElementException

from app import agent, selenium_tools
from app.selenium_tools import BrowserPolicyStop, browser_tools
from app.task_context import TaskContext
from test_account_tasks import FakeDriver, FakeElement, PASSWORD, USERNAME, configured, credential


class Element(FakeElement):
    def __init__(self, kind="email", tag="input"):
        super().__init__(kind)
        self.tag_name = tag
        self.attributes = {}
        self.visible = True
        self.enabled = True
        self.reads = []
        self.clicked = False

    def get_attribute(self, name):
        self.reads.append(name)
        assert name not in ("value", "id", "name", "placeholder", "aria-label")
        return super().get_attribute(name) if name == "type" else self.attributes.get(name)

    def is_displayed(self):
        return self.visible

    def is_enabled(self):
        return self.enabled

    def click(self):
        self.clicked = True


class Driver(FakeDriver):
    def __init__(self):
        super().__init__()
        self.element = Element()
        self.button = Element("button", "button")
        self.elements = [self.element, self.button]
        self.scans = 0
        self.delay = False

    def execute_script(self, script, *args):
        if script == selenium_tools.DISCOVER_CONTROLS:
            self.scans += 1
            if self.delay and self.scans == 1:
                return []
            return [
                {"selector": f"*:nth-child({index + 1})", "element": element, "form": -1,
                 "value": PASSWORD, "name": USERNAME, "label": "secret-label"}
                for index, element in enumerate(self.elements)
            ]
        return super().execute_script(script)

    def find_element(self, by, value):
        if value.startswith("*:nth-child("):
            return self.elements[int(value.split("(")[1].split(")")[0]) - 1]
        return super().find_element(by, value)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.215.14", 443)),
    ])
    return Driver(), configured(tmp_path), TaskContext(allow_write_actions=True, credentials=[credential()])


def tools(setup, deadline=None):
    driver, settings, context = setup
    return {item.name: item for item in browser_tools(driver, settings, deadline or time.monotonic() + 30, context)}


def inspect(tool):
    return json.loads(tool.invoke({"credential_id": "account"}))


def test_discovery_and_fill_use_actual_value_free_controls(setup):
    driver, _, context = setup
    bound = tools(setup)
    result = inspect(bound["inspect_login_form"])
    assert result["controls"]["username"] == [{"selector": "*:nth-child(1)", "form": -1}]
    assert result["controls"]["password"] == []
    assert result["controls"]["buttons"] == [{"selector": "*:nth-child(2)", "form": -1}]
    assert not result["ambiguous"]["username"]
    assert not driver.element.values and not driver.button.clicked
    assert PASSWORD not in str(result) + str(context.observations())
    assert USERNAME not in str(result) + str(context.observations())
    assert "secret-label" not in str(result)
    bound["fill_credential"].invoke({"selector": result["controls"]["username"][0]["selector"],
                                    "credential_id": "account", "field": "username"})
    assert driver.element.values == [USERNAME]


def test_sequential_page_requires_fresh_discovery(setup):
    driver, _, _ = setup
    bound = tools(setup)
    assert inspect(bound["inspect_login_form"])["controls"]["username"]
    driver.element = Element("password")
    driver.elements = [driver.button, driver.element]
    result = inspect(bound["inspect_login_form"])
    assert not result["controls"]["username"]
    assert result["controls"]["password"][0]["selector"] == "*:nth-child(2)"
    bound["fill_credential"].invoke({"selector": "*:nth-child(2)", "credential_id": "account", "field": "password"})
    assert driver.element.values == [PASSWORD]


def test_discovery_waits_for_initial_hydration(setup):
    setup[0].delay = True
    assert inspect(tools(setup)["inspect_login_form"])["controls"]["username"]
    assert setup[0].scans == 2


def test_discovery_preserves_ambiguity_and_bounds_candidates(setup):
    driver, _, _ = setup
    driver.elements = [Element() for _ in range(20)] + [driver.button]
    result = inspect(tools(setup)["inspect_login_form"])
    assert len(result["controls"]["username"]) == 8
    assert result["ambiguous"]["username"] and result["truncated"]
    assert not any(element.values for element in driver.elements)


@pytest.mark.parametrize("restriction", ["hidden", "disabled", "readonly", "otp", "unsupported"])
def test_discovery_excludes_unusable_inputs(setup, restriction):
    driver, _, _ = setup
    rejected = Element()
    if restriction == "hidden":
        rejected.visible = False
    elif restriction == "disabled":
        rejected.enabled = False
    elif restriction == "readonly":
        rejected.attributes["readonly"] = "true"
    elif restriction == "otp":
        rejected.attributes["autocomplete"] = "one-time-code"
    else:
        rejected.input_type = "search"
    driver.elements.insert(0, rejected)
    result = inspect(tools(setup)["inspect_login_form"])
    assert result["controls"]["username"] == [{"selector": "*:nth-child(2)", "form": -1}]


@pytest.mark.parametrize("restriction", ["origin", "frame", "expired", "cancelled", "captcha", "mfa", "unknown"])
def test_discovery_keeps_credential_policy_stops(setup, restriction):
    driver, _, context = setup
    bound = tools(setup)
    if restriction == "origin":
        driver.current_url = "https://other.example/"
    elif restriction == "frame":
        driver.top = False
    elif restriction == "expired":
        context.credential_expires_at = time.time() - 1
    elif restriction == "cancelled":
        context.cancel()
    elif restriction == "captcha":
        driver.body.text = "CAPTCHA"
    elif restriction == "mfa":
        driver.body.text = "Use your authenticator app"
    with pytest.raises(BrowserPolicyStop):
        bound["inspect_login_form"].invoke({"credential_id": "unknown" if restriction == "unknown" else "account"})
    assert not driver.element.values and not driver.button.clicked
    assert driver.scans == 0


def test_discovery_respects_deadline_and_empty_page_timeout(setup):
    bound = tools(setup, deadline=time.monotonic() - 1)
    with pytest.raises(ToolException, match="time limit"):
        inspect(bound["inspect_login_form"])
    setup[0].elements = []
    setup[1].browser_timeout_seconds = 0.01
    with pytest.raises(ToolException, match="No usable login controls"):
        inspect(tools(setup)["inspect_login_form"])


@pytest.mark.parametrize("change", ["readonly", "disabled", "hidden", "type", "replacement"])
def test_field_revalidated_after_clear_before_secret_entry(setup, change):
    driver, _, _ = setup
    bound = tools(setup)
    inspect(bound["inspect_login_form"])

    def changed():
        if change == "readonly":
            driver.element.attributes["readonly"] = "true"
        elif change == "disabled":
            driver.element.enabled = False
        elif change == "hidden":
            driver.element.visible = False
        elif change == "type":
            driver.element.input_type = "password"
        else:
            driver.elements[0] = Element()

    driver.element.clear = changed
    with pytest.raises(BrowserPolicyStop, match="changed"):
        bound["fill_credential"].invoke({"selector": "*:nth-child(1)", "credential_id": "account", "field": "username"})
    assert not driver.element.values
    assert not driver.button.clicked


def test_unavailable_credential_selector_requests_fresh_inspection(setup, monkeypatch):
    driver, settings, _ = setup
    settings.browser_timeout_seconds = 0
    original = driver.find_element

    def missing(by, value):
        if value == "#guessed":
            raise NoSuchElementException("internal secret")
        return original(by, value)

    monkeypatch.setattr(driver, "find_element", missing)
    with pytest.raises(ToolException, match="inspect_login_form") as error:
        tools(setup)["fill_credential"].invoke({"selector": "#guessed", "credential_id": "account", "field": "username"})
    assert "internal secret" not in str(error.value)
    assert not driver.element.values and not driver.button.clicked


def test_agent_requires_discovery_and_virtual_display_browser(setup, monkeypatch):
    from types import SimpleNamespace
    driver, settings, context = setup
    seen = {}

    def remote(**kwargs):
        seen.update(kwargs)
        return driver

    class Graph:
        def invoke(self, *_args, **_kwargs):
            return {"messages": [SimpleNamespace(content="Observed test page")]}

    mock_local_browser(monkeypatch, lambda: remote(options=__import__("selenium").webdriver.ChromeOptions()))
    monkeypatch.setattr(agent, "ChatOpenAI", lambda **_: object())
    monkeypatch.setattr(agent, "create_deep_agent", lambda **_: Graph())
    agent.run_task("Inspect authorized test", settings, context)
    assert "inspect_login_form" in agent.SYSTEM_PROMPT
    assert "Do not guess among ambiguous" in agent.SYSTEM_PROMPT




def test_replaced_discovered_input_is_not_used_for_entry(setup):
    driver, _, _ = setup
    bound = tools(setup)
    inspect(bound["inspect_login_form"])
    replacement = Element()
    driver.elements[0] = replacement
    with pytest.raises(BrowserPolicyStop, match="changed since inspection"):
        bound["fill_credential"].invoke({"selector": "*:nth-child(1)", "credential_id": "account", "field": "username"})
    assert not replacement.values and not driver.element.values


def test_malformed_discovery_does_not_leak_or_act(setup, monkeypatch):
    driver, _, _ = setup
    original = driver.execute_script

    def malformed(script, *args):
        if script == selenium_tools.DISCOVER_CONTROLS:
            return {"value": PASSWORD}
        return original(script, *args)

    monkeypatch.setattr(driver, "execute_script", malformed)
    with pytest.raises(ToolException, match="Could not inspect") as error:
        inspect(tools(setup)["inspect_login_form"])
    assert PASSWORD not in str(error.value)
    assert not driver.element.values and not driver.button.clicked
