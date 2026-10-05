"""Opt-in real noVNC manual login, retained synthetic state and task handoff.

Only local test fixtures and synthetic tokens are used. Never read a profile's
contents, website password/OTP, or cookie values to assert persistence.
"""
import os
import socket
import struct
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
import uvicorn
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from app.browser_runtime import browser_session, local_browser, _local_driver_version
from app.config import Settings
from app.main import create_app
from app.task_context import ExecutionBudget

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LOCAL_BROWSER_INTEGRATION") != "1",
                               reason="Explicit Linux desktop integration opt-in required")


def wait_for(predicate, seconds=20):
    end = time.monotonic() + seconds
    while not predicate():
        assert time.monotonic() < end, "Synthetic session did not reach expected state"
        time.sleep(0.05)


class SyntheticPage(BaseHTTPRequestHandler):
    def do_GET(self):
        signed_in = "posting_synthetic=1" in self.headers.get("Cookie", "")
        body = ('<html><head><title>Synthetic profile test</title></head><body>'
                '<h1 id="state">' + ("Synthetic signed in" if signed_in else "Synthetic anonymous") + '</h1>'
                '<button id="login" onclick="document.cookie=\'posting_synthetic=1; path=/; max-age=3600\';location.reload()">Synthetic login</button>'
                '<button id="probe" onclick="this.textContent=\'changed\'">Unchanged</button>'
                '<input id="entry"><button id="logout" onclick="document.cookie=\'posting_synthetic=; path=/; max-age=0\';location.reload()">Synthetic logout</button></body></html>')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *_):
        pass


def rfb_handshake(ws):
    buffer = bytearray()
    def take(n):
        while len(buffer) < n:
            buffer.extend(ws.recv(timeout=5))
        result = bytes(buffer[:n])
        del buffer[:n]
        return result
    assert take(12) == b"RFB 003.008\n"
    ws.send(b"RFB 003.008\n")
    count = take(1)[0]
    assert 1 in take(count)
    ws.send(b"\x01")
    assert take(4) == b"\x00\x00\x00\x00"
    ws.send(b"\x01")
    init = take(24)
    take(struct.unpack("!I", init[20:24])[0])


def test_panel_manual_profile_reuse_isolation_queue_and_task_handoff(tmp_path):
    from seleniumbase import Driver
    from websockets.sync.client import connect
    from websockets.exceptions import InvalidStatus, ConnectionClosed

    site = ThreadingHTTPServer(("127.0.0.1", 0), SyntheticPage)
    site_thread = threading.Thread(target=site.serve_forever, daemon=True)
    site_thread.start()
    site_url = f"http://127.0.0.1:{site.server_port}/"
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listener.bind(("127.0.0.1", 8001))
    except OSError:
        listener.bind(("127.0.0.1", 0))
    listener.listen()
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    settings = Settings(_env_file=None, database_path=tmp_path / "tasks.db",
        browser_profiles_root=tmp_path / "profiles", display_viewer_enabled=True,
        display_viewer_origin=origin, display_viewer_token="synthetic-viewer",
        task_api_token="synthetic-api", openai_api_key="unused-synthetic",
        openai_base_url="https://unused.example/v1", model_name="unused-synthetic",
        task_timeout_seconds=90, max_agent_steps=20)
    sessions = []
    runner_started = threading.Event()
    finish_runner = threading.Event()
    task_session = {}

    def runner(prompt, settings, context):
        # Synthetic runner deliberately opens only the exact local fixture;
        # no model call or production URL-policy change is made.
        budget = ExecutionBudget(settings.task_timeout_seconds)
        context.control.budget = budget
        with local_browser(settings, context, budget) as session:
            session.driver.execute_cdp_cmd("Network.enable", {})
            session.driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": ["https://*"]})
            session.driver.get(site_url)
            assert session.driver.find_element(By.ID, "state").text == "Synthetic signed in"
            task_session["session"] = session
            runner_started.set()
            while not finish_runner.wait(0.05):
                context.check_alive()
            with context.control.action(context):
                return {"output": "Synthetic persisted login observed"}

    app = create_app(settings, runner=runner)
    manager = app.state.browser_sessions
    @contextmanager
    def capture_runtime(*args, **kwargs):
        with browser_session(*args, **kwargs) as session:
            session.driver.execute_cdp_cmd("Network.enable", {})
            session.driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": ["https://*"]})
            sessions.append(session)
            yield session
    manager.runtime = capture_runtime
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="on"))
    server_thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    server_thread.start()
    wait_for(lambda: server.started)
    observer = None
    try:
        observer = Driver(browser="chrome", headless2=True, undetectable=False,
            binary_location=str(settings.chromium_binary), driver_version=_local_driver_version(settings),
            user_data_dir=str(tmp_path / "panel-observer"), window_size="1200,1400",
            chromium_arg="disable-dev-shm-usage", enable_ws=True)
        observer.get(origin + "/desktop")
        wait = WebDriverWait(observer, 20)
        wait.until(lambda d: d.find_element(By.ID, "viewer-token").is_displayed())
        observer.find_element(By.ID, "viewer-token").send_keys("synthetic-viewer")
        observer.find_element(By.ID, "login-button").click()
        wait.until(lambda d: d.find_element(By.ID, "profile-panel").is_displayed())
        observer.find_element(By.ID, "profile-label").send_keys("Synthetic A")
        observer.find_element(By.ID, "create-profile").click()
        wait.until(lambda d: d.find_element(By.ID, "profiles").get_attribute("value"))
        a = observer.find_element(By.ID, "profiles").get_attribute("value")
        observer.find_element(By.ID, "open-browser").click()
        wait.until(lambda d: "Your manual desktop" in d.find_element(By.ID, "status").text)
        assert len(sessions) == 1 and not runner_started.is_set()
        manual = sessions[-1]
        synthetic_owner = manager.owner
        assert manual.driver.current_url == "about:blank"
        # Place the exact local fixture using the harness. Authentication itself
        # and synthetic typing use real noVNC pointer/keyboard events. Avoid
        # flaky remote omnibox shortcuts accidentally triggering web searches.
        manual.driver.get(site_url)
        wait_for(lambda: manual.driver.find_element(By.ID, "state").text == "Synthetic anonymous")
        def click_remote(element):
            point = manual.desktop._point(element)
            canvas = observer.find_element(By.CSS_SELECTOR, "#screen canvas")
            observer.execute_script("arguments[0].scrollIntoView({block:'start'});", canvas)
            rect = observer.execute_script("const r=arguments[0].getBoundingClientRect();return {w:r.width,h:r.height};", canvas)
            dx = round(point.x * rect["w"] / settings.browser_window_width - rect["w"] / 2)
            dy = round(point.y * rect["h"] / settings.browser_window_height - rect["h"] / 2)
            ActionChains(observer).move_to_element(canvas).move_by_offset(dx, dy).click().perform()
        click_remote(manual.driver.find_element(By.ID, "entry"))
        ActionChains(observer).pause(.2).send_keys("synthetic").perform()
        wait_for(lambda: manual.driver.find_element(By.ID, "entry").get_attribute("value") == "synthetic")
        click_remote(manual.driver.find_element(By.ID, "login"))
        wait_for(lambda: manual.driver.find_element(By.ID, "state").text == "Synthetic signed in")
        assert manual.driver.execute_script("return history.length") >= 2
        screenshot = os.environ.get("PROFILE_PANEL_SCREENSHOT")
        if screenshot:
            observer.execute_script("window.scrollTo(0, 0)")
            observer.save_screenshot(screenshot)  # Synthetic-only fixture, opt-in artifact.
        with httpx.Client(base_url=origin, headers={"Authorization": "Bearer synthetic-api"}, timeout=10) as api:
            accepted = api.post("/run-task", json={"prompt": "Synthetic profile reuse", "browser_profile_id": a})
            assert accepted.status_code == 202
            task_id = accepted.json()["task_id"]
            time.sleep(0.2)
            assert api.get(f"/task-status/{task_id}").json()["status"] == "PENDING"
            assert not runner_started.is_set()
            observer.find_element(By.ID, "close-browser").click()
            assert runner_started.wait(20)
            active = task_session["session"]
            wait.until(lambda d: d.find_element(By.ID, "pause-task").is_enabled())
            headers = {"Cookie": "desktop_session=" + synthetic_owner}
            # This is a synthetic viewer cookie, not any website/session cookie.
            def stream_url():
                info = api.get("/desktop/status", headers=headers).json()
                return origin.replace("http://", "ws://") + "/desktop/ws?generation=" + info["generation"]
            readonly_url = stream_url()
            with connect(readonly_url, origin=origin, additional_headers=headers) as raw:
                rfb_handshake(raw)
                point = active.desktop._point(active.driver.find_element(By.ID, "probe"))
                raw.send(struct.pack("!BBHH", 5, 1, point.x, point.y))
                raw.send(struct.pack("!BBHH", 5, 0, point.x, point.y))
                raw.send(struct.pack("!BBHI", 4, 1, 0, ord("q")))
                raw.send(struct.pack("!BBHI", 4, 0, 0, ord("q")))
                time.sleep(.2)
                assert active.driver.find_element(By.ID, "probe").text == "Unchanged"
                observer.find_element(By.ID, "pause-task").click()
                wait.until(lambda d: d.find_element(By.ID, "resume-task").is_enabled())
                wait.until(lambda d: "Your manual desktop" in d.find_element(By.ID, "status").text)
                with pytest.raises(ConnectionClosed):
                    while True:
                        raw.recv(timeout=3)
            manual_url = stream_url()
            assert manual_url != readonly_url
            with pytest.raises(InvalidStatus):
                with connect(readonly_url, origin=origin, additional_headers=headers):
                    pass
            with httpx.Client(base_url=origin, timeout=5) as other:
                other.post("/desktop/login", headers={"Origin": origin}, json={"token": "synthetic-viewer"})
                wrong_owner = {"Cookie": "desktop_session=" + other.cookies.get("desktop_session")}
                with pytest.raises((InvalidStatus, ConnectionClosed)):
                    with connect(manual_url, origin=origin, additional_headers=wrong_owner) as outsider:
                        outsider.recv(timeout=3)
            with connect(manual_url, origin=origin, additional_headers=headers) as raw:
                rfb_handshake(raw)
                for target, expected in [("logout", "Synthetic anonymous"), ("login", "Synthetic signed in")]:
                    point = active.desktop._point(active.driver.find_element(By.ID, target))
                    raw.send(struct.pack("!BBHH", 5, 1, point.x, point.y))
                    raw.send(struct.pack("!BBHH", 5, 0, point.x, point.y))
                    wait_for(lambda: active.driver.find_element(By.ID, "state").text == expected)
                point = active.desktop._point(active.driver.find_element(By.ID, "probe"))
                raw.send(struct.pack("!BBHH", 5, 1, point.x, point.y))
                raw.send(struct.pack("!BBHH", 5, 0, point.x, point.y))
                wait_for(lambda: active.driver.find_element(By.ID, "probe").text == "changed")
                observer.find_element(By.ID, "resume-task").click()
                wait.until(lambda d: "Live display — read only" in d.find_element(By.ID, "status").text)
                with pytest.raises(ConnectionClosed):
                    while True:
                        raw.recv(timeout=3)
            assert app.state.worker.active_context.control.epoch == 1
            assert any(e["tool"] == "resume" for e in app.state.worker.active_context.observations())
            finish_runner.set()
            wait_for(lambda: api.get(f"/task-status/{task_id}").json()["status"] == "COMPLETED")
        wait.until(lambda d: d.find_element(By.ID, "create-profile").is_enabled() and "Session: idle" in d.find_element(By.ID, "session-state").text)
        observer.find_element(By.ID, "profile-label").send_keys("Synthetic B")
        observer.find_element(By.ID, "create-profile").click()
        wait.until(lambda d: d.find_element(By.ID, "profiles").get_attribute("value") not in ("", a))
        b = observer.find_element(By.ID, "profiles").get_attribute("value")
        assert a != b
        observer.find_element(By.ID, "open-browser").click()
        wait.until(lambda d: "Your manual desktop" in d.find_element(By.ID, "status").text)
        wait_for(lambda: len(sessions) == 2)
        sessions[-1].driver.get(site_url)
        assert sessions[-1].driver.find_element(By.ID, "state").text == "Synthetic anonymous"
        observer.find_element(By.ID, "close-browser").click()
        wait_for(lambda: manager.state == "idle")
        # Reopening the persistent store/browser simulates application restart;
        # verify only synthetic UI state/history, never cookie/profile contents.
        from app.browser_profiles import BrowserProfileStore
        from app.task_context import TaskContext
        assert BrowserProfileStore(settings.browser_profiles_root).get(a)["label"] == "Synthetic A"
        with local_browser(settings, TaskContext(browser_profile_id=a), time.monotonic() + 45) as restored:
            # Observe the synthetic history entry BEFORE visiting the fixture
            # again, through Chrome's UI only, never its on-disk database.
            restored.driver.get("chrome://history/")
            wait_for(lambda: restored.driver.execute_script("""
                function hasSyntheticHistory(root) {
                    for (const el of root.querySelectorAll('*')) {
                        if (el.localName === 'history-item' &&
                            (el.shadowRoot?.textContent || el.textContent).includes('Synthetic profile test')) return true;
                        if (el.shadowRoot && hasSyntheticHistory(el.shadowRoot)) return true;
                    }
                    return false;
                }
                return hasSyntheticHistory(document);
            """))
            restored.driver.get(site_url)
            assert restored.driver.find_element(By.ID, "state").text == "Synthetic signed in"
        observer.find_element(By.ID, "logout").click()
        wait.until(lambda d: d.find_element(By.ID, "viewer-token").is_displayed())
        print("Synthetic profile panel verified at " + origin + "/desktop")
    except Exception:
        print("Synthetic manager state:", manager.state, manager.error)
        if observer:
            print("Synthetic panel status:", observer.find_element(By.ID, "status").text)
            print("Synthetic panel error:", observer.find_element(By.ID, "panel-error").text)
            screenshot = os.environ.get("PROFILE_PANEL_SCREENSHOT")
            if screenshot:
                observer.save_screenshot(screenshot)
        raise
    finally:
        finish_runner.set()
        if observer:
            observer.quit()
        server.should_exit = True
        server_thread.join(25)
        listener.close()
        site.shutdown()
        site.server_close()
        site_thread.join(3)
