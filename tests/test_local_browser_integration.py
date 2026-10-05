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
            assert driver_path.samefile(settings.chromedriver_binary)
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


def test_offline_worker_thread_cancellation_and_recovery(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path
    from threading import Event
    from selenium.webdriver.common.selenium_manager import SeleniumManager
    from seleniumbase.console_scripts import sb_install
    from app.browser_runtime import BrowserRuntimeError, _RUNTIME_LOCK

    downloads = []

    def unexpected_download(*args, **kwargs):
        downloads.append((args, kwargs))
        raise AssertionError("Runtime driver provisioning must not run")

    monkeypatch.setattr(sb_install, "main", unexpected_download)
    monkeypatch.setattr(SeleniumManager, "binary_paths", unexpected_download)
    settings = Settings(_env_file=None)
    ready, cancelled = Event(), Event()
    context = TaskContext()

    def worker():
        with pytest.raises(BrowserRuntimeError, match="cancelled"):
            with local_browser(settings, context, time.monotonic() + 60) as session:
                service = session.driver.service
                process = service.process
                profile = Path(session.driver.capabilities["chrome"]["userDataDir"])
                assert Path(service.path).samefile(settings.chromedriver_binary)
                geometry = session.driver.get_window_size()
                # Openbox can reserve one pixel at the Xvfb screen boundary.
                assert abs(geometry["width"] - settings.browser_window_width) <= 1
                assert abs(geometry["height"] - settings.browser_window_height) <= 1
                assert session.driver.execute_script("return devicePixelRatio") == 1
                ready.set()
                assert cancelled.wait(20)
                session.desktop._guard()
        assert process.poll() is not None
        assert not profile.exists()
        assert not _RUNTIME_LOCK.locked()
        with local_browser(settings, TaskContext(), time.monotonic() + 60) as session:
            assert session.driver.execute_script("return navigator.webdriver") is True

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker)
        try:
            if not ready.wait(30):
                future.result(timeout=35)
                pytest.fail("Worker did not signal browser readiness")
            context.cancel()
        finally:
            cancelled.set()
        future.result(timeout=60)
    assert downloads == []


def test_real_constructor_failure_releases_runtime(monkeypatch, tmp_path):
    import subprocess
    from pathlib import Path
    from selenium.common.exceptions import WebDriverException
    from seleniumbase.console_scripts import sb_install
    from app import browser_runtime

    settings = Settings(_env_file=None)
    version = subprocess.check_output([str(settings.chromium_binary), "--version"], text=True).strip()
    broken_browser = tmp_path / "chrome"
    broken_browser.write_text(f'#!/bin/sh\nif [ "$1" = "--version" ]; then\n echo "{version}"\nelse\n exit 1\nfi\n')
    broken_browser.chmod(0o755)
    profiles = []
    original_temporary = browser_runtime.tempfile.TemporaryDirectory

    def temporary(**kwargs):
        result = original_temporary(**kwargs)
        profiles.append(Path(result.name))
        return result

    def driver_processes():
        found = set()
        for executable in Path("/proc").glob("[0-9]*/exe"):
            try:
                if executable.samefile(settings.chromedriver_binary):
                    found.add(executable.parent.name)
            except OSError:
                pass
        return found

    def unexpected_download(*args, **kwargs):
        pytest.fail("Failed browser startup must not provision a driver")

    monkeypatch.setattr(sb_install, "main", unexpected_download)
    monkeypatch.setattr(browser_runtime.tempfile, "TemporaryDirectory", temporary)
    prior_display = os.environ.get("DISPLAY")
    prior_processes = driver_processes()
    broken_settings = settings.model_copy(update={"chromium_binary": broken_browser})
    with pytest.raises(WebDriverException):
        with local_browser(broken_settings, TaskContext(), time.monotonic() + 60):
            pytest.fail("Broken browser must not yield a session")
    assert not browser_runtime._RUNTIME_LOCK.locked()
    assert os.environ.get("DISPLAY") == prior_display
    assert profiles and all(not profile.exists() for profile in profiles)
    assert driver_processes() == prior_processes
    with local_browser(settings, TaskContext(), time.monotonic() + 60) as session:
        assert session.driver.current_url == "about:blank"


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
