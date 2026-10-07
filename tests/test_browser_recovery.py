import json
import os
import socket
import time
from types import SimpleNamespace

import pytest
from langchain_core.tools import ToolException
from selenium.common.exceptions import NoSuchElementException

from app import browser_runtime, selenium_tools
from app.config import Settings
from app.selenium_tools import PublicAddressUnavailable, browser_tools, check_url
from app.task_context import TaskContext, TaskDeadlineExceeded
from app.task_report import failure_diagnostics


def public_dns(*_args, **_kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('93.184.215.14', 443))]


class Browser:
    current_url = 'https://example.com'
    title = 'Synthetic'

    def __init__(self):
        self.clicks = []
        self.navigations = []

    def find_element(self, *args):
        if args[1] == 'body':
            return SimpleNamespace(text='Synthetic page')
        raise NoSuchElementException('private missing selector')

    def get(self, url):
        self.navigations.append(url)

    def execute_script(self, *_):
        return []


def tools_for(browser, context=None, *, timeout=1, deadline=None):
    settings = Settings(_env_file=None, enable_write_actions=True, browser_timeout_seconds=timeout)
    return {item.name: item for item in browser_tools(browser, settings, deadline or time.monotonic() + 30, context)}


def test_missing_target_is_recoverable_and_fresh_inspection_works(monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', public_dns)
    browser = Browser()
    context = TaskContext()
    tools = tools_for(browser, context)
    report = json.loads(tools['click_element'].invoke({'selector': '#missing'}))
    assert report['status'] == 'recoverable_error'
    assert report['code'] == 'element_not_ready'
    assert not browser.clicks
    assert json.loads(tools['inspect_page'].invoke({}))['text'] == 'Synthetic page'
    details = failure_diagnostics(ValueError(), context)
    assert details['code'] == 'unknown_failure'
    assert details['last_tool_blocker']['code'] == 'element_not_ready'


def test_dns_failure_blocks_action_without_crashing_and_can_recover(monkeypatch):
    browser = Browser()
    context = TaskContext()
    tools = tools_for(browser, context)

    def unavailable(*_args, **_kwargs):
        raise socket.gaierror(socket.EAI_AGAIN, 'private DNS internal info')

    monkeypatch.setattr(socket, 'getaddrinfo', unavailable)
    with pytest.raises(PublicAddressUnavailable):
        check_url(browser.current_url)
    report = json.loads(tools['navigate_to_page'].invoke({'url': 'https://example.org'}))
    assert report['code'] == 'public_dns_unavailable'
    assert not browser.navigations
    assert 'private' not in json.dumps(report)
    assert failure_diagnostics(ValueError(), context)['last_tool_blocker']['code'] == 'public_dns_unavailable'
    monkeypatch.setattr(socket, 'getaddrinfo', public_dns)
    assert 'Synthetic page' in tools['inspect_page'].invoke({})


def test_dns_failure_after_click_does_not_replay_or_claim_no_click(monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', public_dns)
    browser = Browser()
    element = SimpleNamespace(get_attribute=lambda _: None)

    def click():
        browser.clicks.append(True)
        monkeypatch.setattr(socket, 'getaddrinfo', lambda *_args, **_kwargs: (_ for _ in ()).throw(socket.gaierror('private DNS')))

    element.click = click
    monkeypatch.setattr(selenium_tools, 'wait_for_ready', lambda *_args, **_kwargs: [element])
    report = json.loads(tools_for(browser)['click_element'].invoke({'selector': '#button'}))
    assert report['code'] == 'public_dns_unavailable'
    assert browser.clicks == [True]
    assert 'never replay' in report['next_action']
    assert 'action_performed' not in report


@pytest.mark.parametrize('address', ['127.0.0.1', '10.0.0.1', '169.254.169.254'])
def test_unsafe_destination_stays_fatal(address):
    browser = Browser()
    browser.current_url = 'http://' + address
    with pytest.raises(ToolException):
        tools_for(browser)['click_element'].invoke({'selector': '#button'})
    assert not browser.clicks


def test_deadline_and_cancellation_stay_fatal(monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', public_dns)
    with pytest.raises(TaskDeadlineExceeded):
        tools_for(Browser(), deadline=time.monotonic() - 1)['click_element'].invoke({'selector': '#button'})
    context = TaskContext()
    context.cancel()
    with pytest.raises(Exception):
        tools_for(Browser(), context)['click_element'].invoke({'selector': '#button'})


def test_larger_display_and_browser_maximization(monkeypatch, tmp_path):
    import pyvirtualdisplay
    import seleniumbase

    events = []
    source = tmp_path / 'chromedriver'
    source.write_bytes(b'synthetic')
    settings = Settings(_env_file=None, chromedriver_binary=source)
    assert (settings.browser_window_width, settings.browser_window_height) == (1920, 1080)

    class Display:
        def __init__(self, **kwargs):
            assert kwargs['size'] == (1920, 1080)
        def start(self):
            os.environ['DISPLAY'] = ':99'
        def stop(self):
            events.append('display_closed')

    browser = SimpleNamespace(
        service=SimpleNamespace(path=str(source), stop=lambda: None),
        set_page_load_timeout=lambda _: None, set_script_timeout=lambda _: None,
        get=lambda _: None, set_window_position=lambda x, y: events.append(('position', x, y)),
        set_window_size=lambda w, h: events.append(('size', w, h)),
        maximize_window=lambda: events.append('maximized'), quit=lambda: events.append('closed'),
    )
    monkeypatch.setattr(browser_runtime.sys, 'platform', 'linux')
    monkeypatch.setattr(browser_runtime, 'browser_ready', lambda _: True)
    monkeypatch.setattr(browser_runtime, 'rebind_pyautogui', lambda: SimpleNamespace(FAILSAFE=False))
    monkeypatch.setattr(browser_runtime, '_start_window_manager', lambda _: None)
    monkeypatch.setattr(browser_runtime, '_local_driver_version', lambda _: '123.0.0.1')
    monkeypatch.setattr(pyvirtualdisplay, 'Display', Display)
    monkeypatch.setattr(seleniumbase, 'Driver', lambda **_: browser)
    with browser_runtime.local_browser(settings, TaskContext(), time.monotonic() + 5):
        assert events[-1] == 'maximized'
        assert ('size', 1920, 1080) in events
    assert 'closed' in events and 'display_closed' in events
