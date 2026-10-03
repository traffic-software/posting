import time

import pytest

from browser_helpers import FakeIdleTracker
from app.network_idle import NetworkIdleError
from app.selenium_tools import BrowserPolicyStop, browser_tools
from test_desktop_browser_tools import setup as desktop_setup, PageElement
from test_totp_tools import setup as totp_setup


def fail_idle():
    raise NetworkIdleError("sanitized")


def bind(setup, idle):
    driver, desktop, context, settings = setup
    return {item.name: item for item in browser_tools(driver, settings, time.monotonic() + 30,
            context, desktop, network_idle=idle)}


@pytest.mark.parametrize("idle", [None, FakeIdleTracker(fail_idle)])
@pytest.mark.parametrize("name,args", [
    ("fill_element", {"selector": "*:nth-child(1)", "value": "synthetic"}),
    ("press_key", {"selector": "*:nth-child(1)", "key": "enter"}),
    ("fill_credential", {"selector": "*:nth-child(1)", "credential_id": "account", "field": "username"}),
])
def test_idle_failure_before_target_resolution_or_input(desktop_setup, monkeypatch, idle, name, args):
    driver, desktop, _, _ = desktop_setup
    clears = []
    monkeypatch.setattr(driver.element, "clear", lambda: clears.append(True))
    original = driver.find_element
    def find(by, selector):
        if selector != "body":
            pytest.fail("Target resolved before readiness")
        return original(by, selector)
    monkeypatch.setattr(driver, "find_element", find)
    with pytest.raises(BrowserPolicyStop, match="this invocation entered no data"):
        bind(desktop_setup, idle)[name].invoke(args)
    assert not clears and not desktop.calls and not driver.element.values


def test_inspected_text_replacement_during_idle_requires_reinspection(desktop_setup):
    driver, desktop, _, _ = desktop_setup
    def replace():
        driver.elements[0] = PageElement()
    tools = bind(desktop_setup, FakeIdleTracker(replace))
    tools["inspect_page"].invoke({})
    with pytest.raises(BrowserPolicyStop, match="inspect_page again"):
        tools["fill_element"].invoke({"selector": "*:nth-child(1)", "value": "synthetic"})
    assert not desktop.calls


@pytest.mark.parametrize("change", ["origin", "expiry", "cancel"])
def test_policy_changes_during_idle_block_credential(desktop_setup, change):
    driver, desktop, context, _ = desktop_setup
    def action():
        if change == "origin":
            driver.current_url = "https://other.example/signin"
        elif change == "expiry":
            context.credential_expires_at = 0
        else:
            context.cancelled.set()
    tools = bind(desktop_setup, FakeIdleTracker(action))
    with pytest.raises(BrowserPolicyStop):
        tools["fill_credential"].invoke({"selector": "*:nth-child(1)", "credential_id": "account", "field": "username"})
    assert not driver.element.values and not desktop.calls


def test_totp_failure_precedes_generation_reservation_and_target_resolution(totp_setup, monkeypatch):
    import pyotp
    driver, settings, context = totp_setup
    def forbidden(*args, **kwargs):
        pytest.fail("OTP side effect or target resolution before readiness")
    monkeypatch.setattr(pyotp, "TOTP", forbidden)
    monkeypatch.setattr(context, "reserve_totp", forbidden)
    monkeypatch.setattr(driver, "find_elements", forbidden)
    tools = {item.name: item for item in browser_tools(driver, settings, time.monotonic() + 30,
            context, network_idle=FakeIdleTracker(fail_idle))}
    with pytest.raises(BrowserPolicyStop, match="this invocation entered no data"):
        tools["fill_totp"].invoke({"selector": "#otp", "submit_selector": "#submit", "credential_id": "account"})
    assert not driver.element.values and not driver.submit.clicked
