import asyncio
from unittest.mock import AsyncMock

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.display_viewer import DisplayViewer, _Display, create_router


ORIGIN = "https://viewer.example"


def settings(**overrides):
    values = {
        "display_viewer_enabled": True,
        "display_viewer_token": "test-token",
        "display_viewer_origin": ORIGIN,
        "display_viewer_session_seconds": 900,
        "display_viewer_assets": Path("/not-present/novnc"),
        "display_viewer_max_connections": 2,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def client_for(viewer):
    app = FastAPI()
    app.include_router(create_router(viewer))
    return TestClient(app, base_url=ORIGIN)


def login(client, token="test-token"):
    return client.post("/desktop/login", headers={"Origin": ORIGIN}, json={"token": token})


@pytest.mark.parametrize("close_error", [RuntimeError("already closed"), WebSocketDisconnect(1006)])
def test_websocket_cleanup_tolerates_disconnected_client(monkeypatch, close_error):
    viewer = DisplayViewer(settings())
    monkeypatch.setattr(viewer, "authenticate", lambda *_: True)
    monkeypatch.setattr(viewer, "claim_connection", lambda: ("generation", 5900))
    released = []
    monkeypatch.setattr(viewer, "release_connection", released.append)
    monkeypatch.setattr(asyncio, "open_connection", AsyncMock(side_effect=OSError))
    websocket = SimpleNamespace(
        headers={"origin": ORIGIN}, cookies={"desktop_session": "session"},
        close=AsyncMock(side_effect=[None, close_error]),
    )
    route = next(route for route in create_router(viewer).routes if route.path == "/desktop/ws")
    asyncio.run(route.endpoint(websocket))
    assert released == ["generation"]


def test_disabled_routes_are_hidden_and_spawn_nothing():
    viewer = DisplayViewer(settings(display_viewer_enabled=False))
    client = client_for(viewer)
    response = client.get("/desktop/status")
    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert viewer.start_display(":99") is None
    assert viewer.status() == ("unavailable", None)


@pytest.mark.parametrize("origin", [
    "https://viewer.example/", "http://viewer.example", "https://user@viewer.example",
    "https://VIEWER.example", "https://viewer.example:443", "https://viewer.example%2f.bad",
    "https://viewer.example\\bad", "https://*.example",
])
def test_enabled_rejects_non_exact_or_insecure_origin(origin):
    with pytest.raises(ValueError, match="origin"):
        DisplayViewer(settings(display_viewer_origin=origin))


def test_login_requires_exact_origin_and_uses_strict_secure_cookie():
    viewer = DisplayViewer(settings())
    client = client_for(viewer)
    assert client.post("/desktop/login", json={"token": "test-token"}).status_code == 404
    assert login(client, "wrong").status_code == 401
    response = login(client)
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "secure" in cookie
    assert "path=/desktop" in cookie
    status = client.get("/desktop/status")
    assert status.status_code == 200
    assert status.json() == {"state": "idle", "generation": None}
    assert status.headers["content-security-policy"].startswith("default-src 'none'")
    asset = client.get("/desktop/static/viewer.js")
    assert asset.status_code == 200
    assert asset.headers["x-frame-options"] == "DENY"


def test_loopback_http_cookie_is_not_secure():
    viewer = DisplayViewer(settings(display_viewer_origin="http://127.0.0.1:8080"))
    client = client_for(viewer)
    response = client.post("/desktop/login", headers={"Origin": "http://127.0.0.1:8080"}, json={"token": "test-token"})
    assert response.status_code == 200
    assert "secure" not in response.headers["set-cookie"].lower()


def test_expired_session_and_logout_revoke_cookie():
    viewer = DisplayViewer(settings())
    client = client_for(viewer)
    assert login(client).status_code == 200
    session = client.cookies.get("desktop_session")
    viewer._sessions[session].expires_at = 0
    assert client.get("/desktop/status").status_code == 401

    assert login(client).status_code == 200
    assert client.post("/desktop/logout", json={}, headers={"Origin": "https://elsewhere.example"}).status_code == 404
    assert client.post("/desktop/logout", json={}, headers={"Origin": ORIGIN}).status_code == 200
    assert client.get("/desktop/status").status_code == 401


def test_login_is_rate_limited_and_sessions_are_bounded():
    viewer = DisplayViewer(settings())
    client = client_for(viewer)
    for _ in range(8):
        assert login(client, "no").status_code == 401
    assert login(client, "test-token").status_code == 401

    other = DisplayViewer(settings())
    for index in range(64):
        assert other.issue_session(str(index), "test-token")
    assert other.issue_session("one-more", "test-token") is None


class FakeProcess:
    def __init__(self):
        self.stopped = False
        self.calls = []

    def poll(self):
        return None if not self.stopped else 0

    def terminate(self):
        self.calls.append("terminate")
        self.stopped = True

    def wait(self, timeout):
        self.calls.append(("wait", timeout))


def test_start_uses_loopback_viewonly_server_and_retires_before_cleanup(monkeypatch):
    viewer = DisplayViewer(settings())
    old = FakeProcess()
    viewer._display = _Display("old", ":90", 5999, old)
    spawned = []

    def popen(args, **kwargs):
        spawned.append((args, kwargs))
        return FakeProcess()

    monkeypatch.setattr("app.display_viewer.sys.platform", "linux")
    monkeypatch.setattr("app.display_viewer.shutil.which", lambda name: "/usr/bin/x11vnc")
    monkeypatch.setattr("app.display_viewer.subprocess.Popen", popen)
    monkeypatch.setattr(viewer, "_wait_for_listener", lambda *_args: None)
    monkeypatch.setattr("app.display_viewer._reserve_loopback_port", lambda: 5998)
    generation = viewer.start_display(":91")

    assert generation != "old"
    assert old.calls[0] == "terminate"
    args, kwargs = spawned[0]
    assert args[:6] == ["x11vnc", "-display", ":91", "-localhost", "-rfbport", "5998"]
    assert "-viewonly" in args and "-noclipboard" in args and "-forever" in args and "-shared" in args
    assert all(flag in args for flag in ("-noprimary", "-nosetprimary", "-nosetclipboard"))
    assert "shell" not in kwargs  # Popen is invoked directly, never through a shell.
    assert viewer.status() == ("live", generation)
    viewer.stop_display(generation)
    assert viewer.status() == ("idle", None)


def test_startup_failure_is_nonfatal_and_marks_viewer_unavailable(monkeypatch):
    viewer = DisplayViewer(settings())
    monkeypatch.setattr("app.display_viewer.sys.platform", "linux")
    monkeypatch.setattr("app.display_viewer.shutil.which", lambda name: "/usr/bin/x11vnc")
    monkeypatch.setattr("app.display_viewer._reserve_loopback_port", lambda: 5998)

    class ExitingProcess(FakeProcess):
        def poll(self):
            return 1

    monkeypatch.setattr("app.display_viewer.subprocess.Popen", lambda *_args, **_kwargs: ExitingProcess())
    assert viewer.start_display(":91") is None
    assert viewer.status() == ("unavailable", None)


def test_connection_claims_are_bounded_and_never_retarget():
    viewer = DisplayViewer(settings())
    process = FakeProcess()
    viewer._display = _Display("first", ":99", 5901, process)
    assert viewer.claim_connection() == ("first", 5901)
    assert viewer.claim_connection() == ("first", 5901)
    assert viewer.claim_connection() is None
    viewer.stop_display("first")
    assert not viewer.generation_is_live("first")
    viewer.release_connection("first")
    viewer.release_connection("first")


def test_interactive_start_requires_owner_filters_wayland_and_retires_generations(monkeypatch):
    viewer = DisplayViewer(settings())
    owner = viewer.issue_session("owner", "test-token")
    observer = viewer.issue_session("observer", "test-token")
    spawned = []
    monkeypatch.setattr("app.display_viewer.sys.platform", "linux")
    monkeypatch.setattr("app.display_viewer.shutil.which", lambda _: "/usr/bin/x11vnc")
    monkeypatch.setattr(viewer, "_wait_for_listener", lambda *args: None)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-synthetic")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    def popen(args, **kwargs):
        process = FakeProcess()
        spawned.append((args, kwargs, process))
        return process
    monkeypatch.setattr("app.display_viewer.subprocess.Popen", popen)
    with pytest.raises(RuntimeError, match="owner"):
        viewer.start_display(":99", interactive=True, owner="invalid")
    readonly = viewer.start_display(":99")
    manual = viewer.start_display(":99", interactive=True, owner=owner)
    assert readonly != manual and not viewer.generation_is_live(readonly)
    assert spawned[0][2].stopped
    assert "-viewonly" in spawned[0][0]
    assert "-viewonly" not in spawned[1][0]
    assert "-localhost" in spawned[1][0] and "-noclipboard" in spawned[1][0]
    assert all("WAYLAND_DISPLAY" not in kwargs["env"] and "XDG_SESSION_TYPE" not in kwargs["env"]
               for _, kwargs, _ in spawned)
    assert viewer.connection_authorized(owner, manual)
    assert not viewer.connection_authorized(observer, manual)
    agent = viewer.start_display(":99")
    assert not viewer.connection_authorized(owner, manual)
    assert viewer.connection_authorized(observer, agent)
    viewer.close()
