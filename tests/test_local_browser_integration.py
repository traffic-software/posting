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
    for _ in range(2):
        context = TaskContext()
        with local_browser(settings, context, time.monotonic() + 60) as session:
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


def test_real_network_idle_delayed_replacement_hung_and_failure():
    """Synthetic loopback only, directly at runtime/helper boundary."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from app.network_idle import NetworkIdleError

    release = threading.Event()

    class Page(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/delay"):
                time.sleep(0.4)
                payload = b"done"
            elif self.path.startswith("/hung"):
                release.wait(10)
                payload = b"released"
            elif self.path.startswith("/fail"):
                self.connection.shutdown(2)
                self.connection.close()
                return
            else:
                payload = b"<html><body><input id='entry'><script>window.done=false;window.begin=(path)=>fetch(path).then(()=>{document.querySelector('#entry').outerHTML=\"<input id='entry'>\";window.done=true}).catch(()=>window.done=true);</script></body></html>"
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Content-Type", "text/html" if self.path == "/" else "text/plain")
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Page)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        settings = Settings(_env_file=None, network_idle_max_wait_seconds=2)
        context = TaskContext()
        deadline = time.monotonic() + 60
        with local_browser(settings, context, deadline) as session:
            driver, idle = session.driver, session.network_idle
            driver.get(f"http://127.0.0.1:{server.server_port}/")
            previous = driver.find_element(By.ID, "entry")
            driver.execute_script("window.begin('/delay')")
            start = time.monotonic()
            idle.wait(deadline, lambda: None, context.cancelled)
            assert time.monotonic() - start >= 0.8
            assert driver.execute_script("return window.done")
            fresh = driver.find_element(By.ID, "entry")
            assert fresh != previous
            session.desktop.type_text(fresh, "synthetic readiness")
            assert fresh.get_attribute("value") == "synthetic readiness"
            driver.execute_script("window.begin('/fail')")
            idle.wait(deadline, lambda: None, context.cancelled)
            assert not idle.pending
            driver.execute_script("window.begin('/hung')")
            start = time.monotonic()
            with pytest.raises(NetworkIdleError, match="this invocation entered no data"):
                idle.wait(deadline, lambda: None, context.cancelled)
            assert 1.9 <= time.monotonic() - start < 4
            assert driver.find_element(By.ID, "entry").get_attribute("value") == "synthetic readiness"
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
