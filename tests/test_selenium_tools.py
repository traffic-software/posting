import socket
import time

import pytest
from langchain_core.tools import ToolException

from app.config import Settings
from app.selenium_tools import browser_tools, check_url


def dns_answer(address):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, 443))


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [dns_answer("93.184.215.14")])


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "data:text/html,hello",
    "javascript:alert(1)",
    "https:///missing-host",
    "http://localhost/",
    "http://sub.localhost/",
    "http://printer.local/",
    "http://local/",
    "http://127.0.0.1/",
    "http://10.0.0.1/",
    "http://172.16.0.1/",
    "http://192.168.1.1/",
    "http://169.254.169.254/",
    "http://100.64.0.1/",
    "http://0.0.0.0/",
    "http://224.0.0.1/",
    "http://[::1]/",
    "http://[fc00::1]/",
    "http://[fe80::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://[ff02::1]/",
    "http://user:pass@example.com/",
    "http://@example.com/",
    "http://example.com:invalid/",
    "http://example.com:65536/",
    "http://example.com:0/",
    "http://[invalid-ipv6/",
    "http://example.com\\@127.0.0.1/",
    "http://%31%32%37.0.0.1/",
])
def test_url_policy_rejects_unsafe_destinations(url):
    with pytest.raises(ToolException):
        check_url(url)


@pytest.mark.parametrize("url", [
    "https://example.com/page",
    "https://another.example/page",
    "https://example.org/",
    "http://93.184.215.14/",
    "https://[2606:4700:4700::1111]/",
])
def test_url_policy_allows_public_destinations(url):
    check_url(url)


@pytest.mark.parametrize("address", [
    "127.0.0.1", "10.0.0.1", "169.254.169.254", "fc00::1", "224.0.0.1",
])
def test_dns_with_non_public_address_is_rejected(monkeypatch, address):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        dns_answer("93.184.215.14"), dns_answer(address),
    ])
    with pytest.raises(ToolException):
        check_url("https://any.example/")


def test_dns_with_public_ipv4_and_ipv6_is_allowed(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        dns_answer("93.184.215.14"), dns_answer("2606:4700:4700::1111"),
    ])
    check_url("https://any.example/")


def test_dns_failure_is_rejected(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise socket.gaierror("Lookup failed")

    monkeypatch.setattr(socket, "getaddrinfo", unavailable)
    with pytest.raises(ToolException):
        check_url("https://any.example/")


def test_empty_dns_answer_is_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [])
    with pytest.raises(ToolException):
        check_url("https://any.example/")


@pytest.mark.parametrize("host", ["2130706433", "127.1", "0x7f000001"])
def test_numeric_loopback_forms_are_checked_via_dns(monkeypatch, host):
    seen = []

    def loopback(name, *_args, **_kwargs):
        seen.append(name)
        return [dns_answer("127.0.0.1")]

    monkeypatch.setattr(socket, "getaddrinfo", loopback)
    with pytest.raises(ToolException):
        check_url(f"http://{host}/")
    assert seen == [host]


class FakeBrowser:
    def __init__(self):
        self.current_url = "about:blank"
        self.title = "Example"
        self.closed = False

    def get(self, url):
        self.current_url = url

    def quit(self):
        self.closed = True


def test_read_only_tools_and_navigation():
    browser = FakeBrowser()
    settings = Settings(_env_file=None)
    tools = browser_tools(browser, settings, time.monotonic() + 60)
    assert {item.name for item in tools} == {"navigate_to_page", "extract_text", "inspect_page"}
    assert "Example" in tools[0].invoke({"url": "https://another.example"})


def test_private_redirect_blocks_further_actions():
    browser = FakeBrowser()
    browser.current_url = "http://127.0.0.1/"
    settings = Settings(_env_file=None)
    tools = browser_tools(browser, settings, time.monotonic() + 60)
    with pytest.raises(ToolException):
        tools[1].invoke({"selector": "body"})


@pytest.mark.parametrize("destination,blocked", [
    ("https://another.example/", False),
    ("http://169.254.169.254/", True),
])
def test_navigation_checks_redirect_destination(destination, blocked):
    class RedirectBrowser(FakeBrowser):
        def get(self, url):
            self.current_url = destination

    tools = browser_tools(RedirectBrowser(), Settings(_env_file=None), time.monotonic() + 60)
    if blocked:
        with pytest.raises(ToolException):
            tools[0].invoke({"url": "https://example.com"})
    else:
        assert "another.example" in tools[0].invoke({"url": "https://example.com"})


def test_write_tools_require_explicit_opt_in():
    settings = Settings(_env_file=None, enable_write_actions=True)
    tools = browser_tools(FakeBrowser(), settings, time.monotonic() + 60)
    assert {item.name for item in tools} == {
        "navigate_to_page", "extract_text", "inspect_page", "click_element", "fill_element"
    }


def test_tool_stop_observation_is_bounded_and_preserves_policy():
    from types import SimpleNamespace
    from app.task_context import TaskContext
    context = TaskContext()
    tools = browser_tools(SimpleNamespace(current_url="about:blank"), Settings(_env_file=None), time.monotonic() + 30, context)
    navigate = next(item for item in tools if item.name == "navigate_to_page")
    with pytest.raises(ToolException):
        navigate.invoke({"url": "http://localhost/"})
    assert context.observations()[-1]["outcome"] == "stopped"
    assert "Local destinations" in context.observations()[-1]["detail"]
    for _ in range(20):
        context.record_observation("extract_text", "returned", "x" * 2000)
    assert len(context.observations()) == 12
    assert all(len(item["detail"]) <= 500 for item in context.observations())
    context.clear_sensitive_state()
    assert context.observations() == []
