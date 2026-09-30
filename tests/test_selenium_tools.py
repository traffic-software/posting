import time

import pytest
from langchain_core.tools import ToolException

from app.config import Settings
from app.selenium_tools import browser_tools, check_url


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "http://localhost/",
    "http://127.0.0.1/",
    "http://user:pass@example.com/",
    "https://another.example/",
    "https://example.com.evil.net/",
    "http://[invalid-ipv6/",
])
def test_url_policy_rejects_unapproved_destinations(url):
    with pytest.raises(ToolException):
        check_url(url, frozenset({"example.com"}))


def test_url_policy_allows_exact_host():
    check_url("https://example.com/page", frozenset({"example.com"}))


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
    settings = Settings(_env_file=None, allowed_hosts="example.com")
    tools = browser_tools(browser, settings, time.monotonic() + 60)
    assert {item.name for item in tools} == {"navigate_to_page", "extract_text"}
    assert "Example" in tools[0].invoke({"url": "https://example.com"})


def test_unapproved_redirect_blocks_further_actions():
    browser = FakeBrowser()
    browser.current_url = "http://127.0.0.1/"
    settings = Settings(_env_file=None, allowed_hosts="example.com")
    tools = browser_tools(browser, settings, time.monotonic() + 60)
    with pytest.raises(ToolException):
        tools[1].invoke({"selector": "body"})


def test_write_tools_require_explicit_opt_in():
    settings = Settings(_env_file=None, allowed_hosts="example.com", enable_write_actions=True)
    tools = browser_tools(FakeBrowser(), settings, time.monotonic() + 60)
    assert {item.name for item in tools} == {
        "navigate_to_page", "extract_text", "click_element", "fill_element"
    }
