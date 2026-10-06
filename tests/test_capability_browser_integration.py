"""Opt-in local browser capability checks, with synthetic pages and no external calls."""
import os
import time
from urllib.parse import quote

import pytest
from selenium.webdriver.common.by import By

from app.browser_dom import DISCOVER_PAGE, IS_EDITING_HOST
from app.browser_runtime import local_browser
from app.config import Settings
from app.desktop_tools import DesktopInputError
from app.selenium_tools import BrowserPolicyStop, browser_tools
from app.task_context import TaskContext


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LOCAL_BROWSER_INTEGRATION") != "1",
    reason="Requires explicit local Linux browser integration opt-in",
)


HTML = """<html><body>
<div id="editor" contenteditable="true" style="border:1px solid;width:500px;height:60px" oninput="document.getElementById('result').textContent=this.textContent"><span>old prompt</span></div>
<div id="plain" contenteditable="plaintext-only">plain text</div>
<div id="disabled" contenteditable="false">not editable</div>
<p id="result"></p>
<button id="double" ondblclick="this.textContent='double clicked'">Double click</button>
<div style="display:flex;gap:80px;margin-top:30px">
<div id="source" draggable="true" style="background:lightblue;width:100px;height:100px">Drag source</div>
<div id="target" ondragover="event.preventDefault()" ondrop="event.preventDefault();this.textContent='Dropped'" style="background:lightgreen;width:100px;height:100px">Drop target</div>
</div>
<div data-private><textarea id="private">private text</textarea></div>
</body></html>"""


def test_editor_discovery_fill_selection_and_safe_mouse_actions(monkeypatch):
    from app import selenium_tools
    url = "data:text/html," + quote(HTML)
    # Only this exact synthetic fixture is exempt; production URL checks are unchanged.
    original = selenium_tools.check_url
    monkeypatch.setattr(selenium_tools, "check_url", lambda value: None if value == url else original(value))
    settings = Settings(_env_file=None, enable_write_actions=True)
    ctx = TaskContext(allow_write_actions=True)
    with local_browser(settings, ctx, time.monotonic() + 60) as session:
        driver = session.driver
        driver.get(url)
        tools = {tool.name: tool for tool in browser_tools(driver, settings, time.monotonic() + 40, ctx, session.desktop)}
        rows = driver.execute_script(DISCOVER_PAGE)
        editor = driver.find_element(By.ID, "editor")
        plain = driver.find_element(By.ID, "plain")
        disabled = driver.find_element(By.ID, "disabled")
        assert any(row["element"] == editor and row["editable_host"] for row in rows)
        assert any(row["element"] == plain and row["editable_host"] for row in rows)
        assert all(row["element"] != disabled for row in rows)
        assert driver.execute_script(IS_EDITING_HOST, editor) is True
        tools["inspect_page"].invoke({})
        selector = next(row["selector"] for row in rows if row["element"] == editor)
        assert tools["fill_element"].invoke({"selector": selector, "value": "new café prompt"}) == "Field updated"
        assert editor.text == "new café prompt"
        assert driver.find_element(By.ID, "result").text == "new café prompt"
        tools["select_all_text"].invoke({"selector": selector})
        session.desktop.press_key(editor, "backspace")
        assert editor.text == ""
        session.desktop.type_text(editor, "replacement prompt")
        assert editor.text == "replacement prompt"
        session.desktop.double_click(driver.find_element(By.ID, "double"))
        assert driver.find_element(By.ID, "double").text == "double clicked"
        session.desktop.drag(driver.find_element(By.ID, "source"), driver.find_element(By.ID, "target"))
        assert driver.find_element(By.ID, "target").text == "Dropped"
        with pytest.raises(DesktopInputError):
            session.desktop.drag(editor, driver.find_element(By.ID, "target"))
        private = driver.find_element(By.ID, "private")
        with pytest.raises(BrowserPolicyStop):
            tools["fill_element"].invoke({"selector": "#private", "value": "must not clear"})
        assert private.get_attribute("value") == "private text"
        assert "Unsupported text target" in tools["fill_element"].invoke({"selector": "#disabled", "value": "not entered"})
        assert disabled.text == "not editable"
