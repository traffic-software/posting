"""Synthetic, opt-in container verification of the authenticated read-only viewer."""
import os
import socket
import struct
import threading
import time
from urllib.parse import quote

import httpx
import pytest
import uvicorn
from selenium.webdriver.common.by import By

from app.browser_runtime import local_browser
from app.config import Settings
from app.main import create_app
from app.task_context import TaskContext

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LOCAL_BROWSER_INTEGRATION") != "1",
    reason="Requires explicit opt-in in the Linux viewer image",
)


def test_real_viewer_auth_stream_read_only_and_task_teardown(tmp_path):
    from websockets.sync.client import connect
    from websockets.exceptions import ConnectionClosed, InvalidStatus

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    settings = Settings(_env_file=None, database_path=tmp_path / "tasks.db", display_viewer_enabled=True,
                        display_viewer_token="synthetic-viewer-token", display_viewer_origin=origin)
    app = create_app(settings, runner=lambda *_: {})
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="on"))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    stop_at = time.monotonic() + 10
    while not server.started:
        assert thread.is_alive() and time.monotonic() < stop_at
        time.sleep(0.05)
    ws = None
    try:
        with httpx.Client(base_url=origin, timeout=5) as client:
            assert client.get("/desktop").status_code == 200
            assert client.get("/desktop/static/viewer.js").status_code == 200
            assert client.get("/desktop/novnc/core/rfb.js").status_code == 200
            assert client.get("/desktop/novnc/vendor/pako/lib/zlib/inflate.js").status_code == 200
            assert client.get("/desktop/status").status_code == 401
            assert client.post("/desktop/login", json={"token": "wrong"}, headers={"Origin": origin}).status_code == 401
            login = client.post("/desktop/login", json={"token": "synthetic-viewer-token"}, headers={"Origin": origin})
            assert login.status_code == 200
            assert "HttpOnly" in login.headers["set-cookie"]
            assert client.get("/desktop/status").json()["state"] == "idle"
            cookie = "desktop_session=" + client.cookies.get("desktop_session")
            ws_url = f"ws://127.0.0.1:{port}/desktop/ws"
            with local_browser(settings, TaskContext(), time.monotonic() + 90) as session:
                assert client.get("/desktop/status").json()["state"] == "live"
                for headers, client_origin in [({}, origin), ({"Cookie": cookie}, "http://untrusted.example")]:
                    with pytest.raises(InvalidStatus):
                        with connect(ws_url, origin=client_origin, additional_headers=headers):
                            pass
                html = '<input id="entry"><button id="action" onclick="this.textContent=\'clicked\'">Apply</button>'
                session.driver.get("data:text/html," + quote(html))
                entry = session.driver.find_element(By.ID, "entry")
                button = session.driver.find_element(By.ID, "action")
                session.desktop.type_text(entry, "safe")
                ws = connect(ws_url, origin=origin, additional_headers={"Cookie": cookie}, max_size=65536)
                buffered = bytearray()

                def take(size):
                    while len(buffered) < size:
                        chunk = ws.recv(timeout=5)
                        assert isinstance(chunk, bytes)
                        buffered.extend(chunk)
                    data = bytes(buffered[:size])
                    del buffered[:size]
                    return data

                assert take(12) == b"RFB 003.008\n"
                ws.send(b"RFB 003.008\n")
                count = take(1)[0]
                types = take(count)
                assert 1 in types  # Private loopback RFB; public bridge already authenticated.
                ws.send(b"\x01")
                assert take(4) == b"\x00\x00\x00\x00"
                ws.send(b"\x01")
                init = take(24)
                width, height = struct.unpack("!HH", init[:4])
                assert width > 0 and height > 0
                take(struct.unpack("!I", init[20:24])[0])
                point = session.desktop._point(button)
                ws.send(struct.pack("!BBHH", 5, 1, point.x, point.y))
                ws.send(struct.pack("!BBHH", 5, 0, point.x, point.y))
                ws.send(struct.pack("!BBHI", 4, 1, 0, ord("q")))
                ws.send(struct.pack("!BBHI", 4, 0, 0, ord("q")))
                ws.send(struct.pack("!BBBBI", 6, 0, 0, 0, 5) + b"dummy")
                time.sleep(0.2)
                assert button.text == "Apply"
                assert entry.get_attribute("value") == "safe"
                ws.send(struct.pack("!BBHHHH", 3, 0, 0, 0, 8, 8))
                assert take(1) == b"\x00"  # A real framebuffer update, not just a status response.
                assert client.post("/desktop/logout", headers={"Origin": origin}).status_code == 200
                assert client.get("/desktop/status").status_code == 401
                with pytest.raises(ConnectionClosed):
                    while True:
                        ws.recv(timeout=3)
                assert client.post("/desktop/login", json={"token": "synthetic-viewer-token"}, headers={"Origin": origin}).status_code == 200
                cookie = "desktop_session=" + client.cookies.get("desktop_session")
                ws = connect(ws_url, origin=origin, additional_headers={"Cookie": cookie})
                assert ws.recv(timeout=5).startswith(b"RFB ")
            assert client.get("/desktop/status").json()["state"] == "idle"
            end = time.monotonic() + 5
            with pytest.raises(ConnectionClosed):
                while time.monotonic() < end:
                    ws.recv(timeout=2)
            assert client.post("/desktop/logout", headers={"Origin": origin}).status_code == 200
            assert client.get("/desktop/status").status_code == 401

            # A separate headless observer exercises the real noVNC browser UI;
            # it does not appear on the task's Xvfb desktop or use real secrets.
            import tempfile
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.support.ui import WebDriverWait

            with tempfile.TemporaryDirectory() as profile:
                options = webdriver.ChromeOptions()
                options.binary_location = str(settings.chromium_binary)
                options.add_argument("--headless=new")
                options.add_argument("--window-size=1100,900")
                options.add_argument("--user-data-dir=" + profile)
                options.add_argument("--disable-dev-shm-usage")
                observer = webdriver.Chrome(service=Service(str(settings.chromedriver_binary)), options=options)
                try:
                    observer.get(origin + "/desktop")
                    wait = WebDriverWait(observer, 12)
                    wait.until(lambda browser: browser.find_element(By.ID, "viewer-token").is_displayed())
                    observer.find_element(By.ID, "viewer-token").send_keys("synthetic-viewer-token")
                    observer.find_element(By.ID, "login-button").click()
                    wait.until(lambda browser: "No active task" in browser.find_element(By.ID, "status").text)
                    for _ in range(2):
                        with local_browser(settings, TaskContext(), time.monotonic() + 60) as task:
                            task.driver.get("data:text/html," + quote('<body style="background:rgb(17,71,91);color:white"><h1>Synthetic live desktop</h1></body>'))
                            wait.until(lambda browser: "Live display" in browser.find_element(By.ID, "status").text)
                            wait.until(lambda browser: browser.execute_script("""
                                const canvas = document.querySelector('#screen canvas');
                                if (!canvas || !canvas.width || !canvas.height) return false;
                                const pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
                                let matches = 0;
                                for (let i = 0; i < pixels.length; i += 64) {
                                    if (Math.abs(pixels[i] - 17) < 5 && Math.abs(pixels[i+1] - 71) < 5 && Math.abs(pixels[i+2] - 91) < 5) matches++;
                                }
                                return matches > 100;
                            """))
                            assert observer.execute_script("return document.getElementById('viewer-token').value;") == ""
                        wait.until(lambda browser: "No active task" in browser.find_element(By.ID, "status").text)
                    observer.find_element(By.ID, "logout").click()
                    wait.until(lambda browser: browser.find_element(By.ID, "viewer-token").is_displayed())
                finally:
                    observer.quit()
    finally:
        if ws is not None:
            ws.close()
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
