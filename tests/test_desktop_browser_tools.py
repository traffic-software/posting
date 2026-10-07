import json
import socket
import time

import pytest

from app.browser_dom import DISCOVER_PAGE
from app.selenium_tools import BrowserPolicyStop, browser_tools
from test_login_forms import Driver, Element
from test_account_tasks import configured, credential, PASSWORD
from app.task_context import TaskContext


class PageElement(Element):
    def get_attribute(self, name):
        if name == "aria-label":
            return "Test control"
        return super().get_attribute(name)


class Desktop:
    def __init__(self):
        self.calls = []
        self._guard = lambda: None

    def _act(self, name, *args):
        self._guard()
        self.calls.append((name, args))
        self._guard()

    def click(self, element):
        self._act("click", element)

    def double_click(self, element):
        self._act("double", element)

    def drag(self, source, destination):
        self._act("drag", source, destination)

    def select_all(self, element):
        self._act("select-all", element)

    def hover(self, element):
        self._act("hover", element)

    def scroll(self, element, amount):
        self._act("scroll", element, amount)

    def press_key(self, element, key):
        self._act("key", element, key)

    def type_text(self, element, text):
        self._act("type", element, text)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.215.14", 443)),
    ])
    driver, desktop = Driver(), Desktop()
    driver.element = PageElement()
    driver.button = PageElement("button", "button")
    driver.elements = [driver.element, driver.button]
    context = TaskContext(allow_write_actions=True, credentials=[credential()])
    settings = configured(tmp_path)
    original = driver.execute_script

    def script(code, *args):
        if code == DISCOVER_PAGE:
            return [{"selector": f"*:nth-child({index + 1})", "element": element} for index, element in enumerate(driver.elements)]
        return original(code, *args)

    monkeypatch.setattr(driver, "execute_script", script)
    return driver, desktop, context, settings


def bind(setup):
    driver, desktop, context, settings = setup
    return {item.name: item for item in browser_tools(driver, settings, time.monotonic() + 30, context, desktop)}


def test_inspection_pagination_exposes_later_targets(setup):
    driver, _, _, _ = setup
    driver.elements = [PageElement("button", "button") for _ in range(40)]
    tools = bind(setup)
    first = json.loads(tools["inspect_page"].invoke({}))
    assert len(first["controls"]) == 30 and first["next_offset"] == 30
    second = json.loads(tools["inspect_page"].invoke({"focus": "menus", "offset": 30}))
    assert len(second["controls"]) == 10 and second["next_offset"] is None
    assert second["controls"][0]["selector"] == "*:nth-child(31)"
    assert second["focus"] == "menus"


def test_inspected_video_can_be_hovered_without_click(setup):
    driver, desktop, _, _ = setup
    driver.element = PageElement("video", "video")
    driver.elements = [driver.element]
    tools = bind(setup)
    page = json.loads(tools["inspect_page"].invoke({"focus": "media"}))
    assert page["controls"][0]["kind"] == "video"
    tools["hover_element"].invoke({"selector": page["controls"][0]["selector"]})
    assert desktop.calls[0][0] == "hover"
    assert not driver.element.clicked
    assert "src" not in driver.element.reads and "href" not in driver.element.reads


def test_mouse_and_keyboard_use_guarded_desktop(setup):
    driver, desktop, _, _ = setup
    tools = bind(setup)
    page = json.loads(tools["inspect_page"].invoke({}))
    assert page["controls"]
    tools["hover_element"].invoke({"selector": "*:nth-child(1)"})
    tools["scroll_element"].invoke({"selector": "*:nth-child(1)", "amount": -2})
    tools["press_key"].invoke({"selector": "*:nth-child(1)", "key": "tab"})
    tools["fill_element"].invoke({"selector": "*:nth-child(1)", "value": "ordinary text"})
    assert [name for name, _ in desktop.calls] == ["hover", "scroll", "key", "type"]
    assert not driver.element.values


@pytest.mark.parametrize("method,args", [
    ("hover_element", {"selector": "*:nth-child(1)"}),
    ("scroll_element", {"selector": "*:nth-child(1)", "amount": 1}),
    ("press_key", {"selector": "*:nth-child(1)", "key": "enter"}),
])
def test_desktop_actions_stop_at_mfa(setup, method, args):
    tools = bind(setup)
    setup[0].body.text = "Use your authenticator app"
    with pytest.raises(BrowserPolicyStop):
        tools[method].invoke(args)
    assert not setup[1].calls


def test_desktop_tools_absent_without_consent(setup):
    setup[2].allow_write_actions = False
    assert set(bind(setup)) == {"navigate_to_page", "extract_text", "inspect_page"}


def test_generic_secret_entry_blocked(setup):
    tools = bind(setup)
    for value in (PASSWORD, "ordinary text"):
        if value != PASSWORD:
            setup[0].element.input_type = "password"
        with pytest.raises(BrowserPolicyStop):
            tools["fill_element"].invoke({"selector": "*:nth-child(1)", "value": value})
    assert not setup[1].calls


def test_inspected_replaced_target_is_not_clicked(setup):
    tools = bind(setup)
    tools["inspect_page"].invoke({})
    setup[0].elements[0] = Element()
    from langchain_core.tools import ToolException
    with pytest.raises(ToolException, match="changed"):
        tools["click_element"].invoke({"selector": "*:nth-child(1)"})
    assert not setup[1].calls


def test_inspected_replaced_text_target_requires_reinspection(setup):
    tools = bind(setup)
    tools["inspect_page"].invoke({})
    setup[0].elements[0] = PageElement()
    with pytest.raises(BrowserPolicyStop, match="inspect_page again"):
        tools["fill_element"].invoke({"selector": "*:nth-child(1)", "value": "synthetic"})
    assert not setup[1].calls


@pytest.mark.parametrize('name,args', [
    ('click_element', {'selector': '*:nth-child(1)'}),
    ('fill_element', {'selector': '*:nth-child(1)', 'value': 'synthetic'}),
    ('press_key', {'selector': '*:nth-child(1)', 'key': 'enter'}),
])
def test_readiness_timeout_is_actionable_without_input(setup, monkeypatch, name, args):
    driver, desktop, context, settings = setup
    settings.browser_timeout_seconds = .01
    original = driver.execute_script
    from app.element_readiness import READINESS
    def script(code, *values):
        if code == READINESS:
            return 'covered'
        return original(code, *values)
    monkeypatch.setattr(driver, 'execute_script', script)
    result = bind(setup)[name].invoke(args)
    assert 'readiness timed out (covered)' in result
    assert 'Inspect the current page/form again' in result
    assert not desktop.calls and not driver.element.values
    assert any(item['outcome'] == 'stopped' for item in context.observations())


def test_overlay_disappears_before_one_click(setup, monkeypatch):
    driver, desktop, _, _ = setup
    original = driver.execute_script
    from app.element_readiness import READINESS
    states = iter(['covered', 'ready'])
    def script(code, *values):
        if code == READINESS:
            return next(states)
        return original(code, *values)
    monkeypatch.setattr(driver, 'execute_script', script)
    assert bind(setup)['click_element'].invoke({'selector': '*:nth-child(1)'}) == 'Element clicked'
    assert [name for name, _ in desktop.calls] == ['click']
