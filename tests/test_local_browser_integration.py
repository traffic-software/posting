"""Opt-in Linux-container checks using synthetic pages and no model/account calls."""
import os
import time
from urllib.parse import quote

import pytest
from selenium.webdriver.common.by import By

from app.browser_runtime import local_browser
from app.config import Settings
from app.task_context import TaskContext
from app.totp_forms import DISCOVER_CONTROLS


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LOCAL_BROWSER_INTEGRATION") != "1",
    reason="Requires explicit opt-in inside the local-browser Linux image",
)


def test_real_display_click_type_scroll_and_repeated_sessions():
    settings = Settings(_env_file=None)
    html = '<html><body><input id="entry"><button id="action" onclick="this.textContent=\'clicked\'">Click</button><div style="height:2000px"></div></body></html>'
    from pathlib import Path
    from selenium.webdriver.chrome.webdriver import WebDriver

    previous_profiles = set()
    for _ in range(2):
        context = TaskContext()
        with local_browser(settings, context, time.monotonic() + 60) as session:
            assert isinstance(session.driver, WebDriver)
            assert session.driver.execute_script("return navigator.webdriver") is True
            profile = Path(session.driver.capabilities["chrome"]["userDataDir"])
            driver_path = Path(session.driver.service.path)
            assert profile not in previous_profiles
            previous_profiles.add(profile)
            assert driver_path == settings.chromedriver_binary
            assert driver_path.exists()
            session.driver.get("data:text/html," + quote(html))
            entry = session.driver.find_element(By.ID, "entry")
            session.desktop.type_text(entry, "synthetic text")
            assert entry.get_attribute("value") == "synthetic text"
            button = session.driver.find_element(By.ID, "action")
            session.desktop.click(button)
            assert button.text == "clicked"
            session.desktop.scroll(button, -3)
            time.sleep(0.2)
            assert session.driver.execute_script("return window.scrollY") > 0
        assert not profile.exists()
        assert driver_path.exists()


def test_actual_discovery_javascript_handles_deep_dom():
    settings = Settings(_env_file=None)
    html = "<html><body>" + "<div>" * 30 + '<input type="email"><button>Next</button>' + "</div>" * 30 + "</body></html>"
    with local_browser(settings, TaskContext(), time.monotonic() + 60) as session:
        session.driver.get("data:text/html," + quote(html))
        rows = session.driver.execute_script(DISCOVER_CONTROLS)
        assert rows
        for row in rows:
            assert row["selector"] and len(row["selector"]) <= 300
            assert session.driver.find_elements(By.CSS_SELECTOR, row["selector"]) == [row["element"]]


def test_real_agent_tools_on_synthetic_page(monkeypatch):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage, ToolMessage
    from app import agent, selenium_tools

    class Page(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'<html><body><input id="entry"><button id="action" onclick="document.getElementById(\'result\').textContent=document.getElementById(\'entry\').value">Apply</button><p id="result"></p></body></html>')

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Page)
    url = f"http://127.0.0.1:{server.server_port}/"
    original_check = selenium_tools.check_url

    def synthetic_destination(value):
        # Test-only exact fixture exception; production destination policy stays unchanged.
        if value != url:
            original_check(value)

    monkeypatch.setattr(selenium_tools, "check_url", synthetic_destination)
    operations = [
        ("navigate_to_page", {"url": url}),
        ("inspect_page", {}),
        ("fill_element", {"selector": "input:nth-child(1)", "value": "synthetic agent"}),
        ("click_element", {"selector": "button:nth-child(2)"}),
        ("extract_text", {"selector": "#result"}),
    ]
    replies = [AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"action-{index}"}])
               for index, (name, args) in enumerate(operations)]
    replies.append(AIMessage(content="Observed synthetic agent output."))

    class Model(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    monkeypatch.setattr(agent, "ChatOpenAI", lambda **_: Model(responses=replies))
    factory, states = agent.create_deep_agent, []

    def capture(**kwargs):
        graph = factory(**kwargs)

        class Graph:
            def invoke(self, *args, **kwargs):
                try:
                    state = graph.invoke(*args, **kwargs)
                except Exception:
                    import traceback
                    traceback.print_exc()
                    raise
                states.append(state)
                return state

        return Graph()

    monkeypatch.setattr(agent, "create_deep_agent", capture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        settings = Settings(_env_file=None, openai_api_key="synthetic", openai_base_url="https://unused.example/v1",
                            model_name="synthetic", enable_write_actions=True, max_agent_steps=40)
        result = agent.run_task("Interact with the approved synthetic fixture and verify its output", settings,
                                TaskContext(allow_write_actions=True))
        assert result["output"] == "Observed synthetic agent output."
        observations = [message for message in states[0]["messages"] if isinstance(message, ToolMessage)]
        assert all(message.status != "error" for message in observations)
        assert observations[-1].content == "synthetic agent"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
