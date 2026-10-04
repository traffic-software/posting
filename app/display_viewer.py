"""Read-only, authenticated bridge from the browser to a task-local X11 display.

The viewer deliberately has no control endpoint: it starts x11vnc on loopback,
then relays its RFB byte stream only after cookie authentication.  The VNC port
is never exposed by this module or returned in an API response.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import JSONResponse, Response
from pydantic import SecretStr
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect


_COOKIE_NAME = "desktop_session"
_DISPLAY_RE = re.compile(r"^:[0-9]{1,4}(?:\.[0-9]{1,4})?$")
_MAX_LOGIN_ATTEMPTS = 8
_LOGIN_WINDOW_SECONDS = 60.0
_MAX_LOGIN_CLIENTS = 256
_MAX_LOGIN_BODY = 2 * 1024
_MAX_SESSIONS = 64
_MAX_BINARY_FRAME = 64 * 1024
_STARTUP_SECONDS = 5.0
_IO_TIMEOUT_SECONDS = 1.0

_SECURITY_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'none'; base-uri 'none'; form-action 'self'; "
        "frame-ancestors 'none'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; frame-src 'self'"
    ),
}


class DisplayViewerError(RuntimeError):
    """The local, read-only display cannot be viewed safely."""


@dataclass
class _Display:
    generation: str
    display_name: str
    port: int
    process: Any


@dataclass
class _Session:
    expires_at: float


def _secret_value(value: Any) -> str:
    """Accept either a plain setting or Pydantic's SecretStr without logging it."""
    getter = getattr(value, "get_secret_value", None)
    value = getter() if callable(getter) else value
    return value if isinstance(value, str) else ""


def _is_loopback_http(origin: str) -> bool:
    parsed = urlsplit(origin)
    return parsed.scheme == "http" and (parsed.hostname or "") in {"localhost", "127.0.0.1", "::1"}


def _valid_origin(origin: str) -> bool:
    """Accept one canonical browser origin, never a pattern or near-match."""
    if not isinstance(origin, str) or not origin or any(char.isspace() for char in origin):
        return False
    if any(char in origin for char in ("%", "\\", "*")):
        return False
    try:
        parsed = urlsplit(origin)
        host = parsed.hostname
        port = parsed.port  # Forces validation, including out-of-range ports.
        if parsed.scheme not in {"https", "http"} or not host or parsed.username or parsed.password:
            return False
        # Reject default ports instead of silently normalizing an origin value.
        if (parsed.scheme == "https" and port == 443) or (parsed.scheme == "http" and port == 80):
            return False
        authority = f"[{host}]" if ":" in host else host
        if port is not None:
            authority = f"{authority}:{port}"
        canonical = f"{parsed.scheme}://{authority}"
        if origin != canonical:
            return False
        return parsed.scheme == "https" or _is_loopback_http(origin)
    except (TypeError, ValueError):
        return False


def _reserve_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _stop_process(process: Any) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=3)
    except (subprocess.TimeoutExpired, TimeoutError):
        try:
            process.kill()
            process.wait(timeout=3)
        except Exception:  # Best-effort cleanup of an owned child only.
            pass
    except Exception:
        pass


class DisplayViewer:
    """Owns at most one x11vnc child and the viewer's bounded session state."""

    def __init__(self, settings: Any):
        self._settings = settings
        self.enabled = bool(getattr(settings, "display_viewer_enabled", False))
        self._token = _secret_value(getattr(settings, "display_viewer_token", ""))
        try:
            self._token_digest = hashlib.sha256(self._token.encode("utf-8")).digest()
        except UnicodeError as exc:
            raise ValueError("display viewer token is invalid") from exc
        self._origin = str(getattr(settings, "display_viewer_origin", ""))
        try:
            self._origin_digest = hashlib.sha256(self._origin.encode("utf-8")).digest()
        except UnicodeError as exc:
            raise ValueError("display viewer origin is invalid") from exc
        self._session_seconds = int(getattr(settings, "display_viewer_session_seconds", 900))
        self._max_viewers = int(getattr(settings, "display_viewer_max_connections", 2))
        self._assets = Path(getattr(settings, "display_viewer_assets", Path("/usr/share/novnc")))
        self._lock = threading.RLock()
        self._start_lock = threading.Lock()
        self._closed = False
        self._display: _Display | None = None
        self._unavailable = False
        self._sessions: dict[str, _Session] = {}
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._connections: dict[str, int] = defaultdict(int)

        if not self.enabled:
            return
        if not self._token.strip() or len(self._token) > 512:
            raise ValueError("display viewer token is required when enabled")
        if not _valid_origin(self._origin):
            raise ValueError("display viewer origin must be an exact HTTPS or loopback HTTP origin")
        if not 1 <= self._session_seconds <= 3600:
            raise ValueError("display viewer session duration must be between 1 and 3600 seconds")
        if not 1 <= self._max_viewers <= 2:
            raise ValueError("display viewer maximum viewers must be between 1 and 2")

    @property
    def origin(self) -> str:
        return self._origin

    @property
    def assets(self) -> Path:
        return self._assets

    @property
    def secure_cookie(self) -> bool:
        return not _is_loopback_http(self._origin)

    def _retire_locked(self, generation: str | None = None) -> _Display | None:
        display = self._display
        if display is None or (generation is not None and display.generation != generation):
            return None
        # Retire before touching the child so existing WS connections cannot
        # ever attach to a subsequent task's display.
        self._display = None
        return display

    def _wait_for_listener(self, process: Any, port: int, deadline: float) -> None:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise DisplayViewerError("read-only display server exited during startup")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                    return
            except OSError:
                time.sleep(0.05)
        raise DisplayViewerError("read-only display server did not become ready")

    def start_display(self, display_name: str) -> str | None:
        """Synchronously start x11vnc, returning an opaque generation or ``None``.

        Viewer failure is intentionally non-fatal to the task runtime.  The
        status endpoint reports ``unavailable`` and no process survives a
        failed bounded startup attempt.
        """
        if not self.enabled:
            return None
        # Only one worker may replace the owned server at a time. close() does
        # not take this lock so application shutdown can retire its generation
        # immediately; the publish check below then kills a late child.
        with self._start_lock:
            return self._start_display_locked(display_name)

    def _start_display_locked(self, display_name: str) -> str | None:
        if not isinstance(display_name, str) or not _DISPLAY_RE.fullmatch(display_name):
            with self._lock:
                self._unavailable = True
            return None
        if not sys.platform.startswith("linux") or shutil.which("x11vnc") is None:
            with self._lock:
                self._unavailable = True
            return None

        with self._lock:
            if self._closed:
                return None
            previous = self._retire_locked()
        _stop_process(previous.process if previous else None)

        process = None
        try:
            port = _reserve_loopback_port()
            # -localhost prevents non-loopback connections. -viewonly and all
            # clipboard flags keep the RFB server observational, not interactive.
            process = subprocess.Popen(
                [
                    "x11vnc", "-display", display_name, "-localhost", "-rfbport", str(port),
                    "-viewonly", "-noprimary", "-noclipboard", "-nosetclipboard", "-nosetprimary",
                    "-forever", "-shared", "-nopw", "-quiet",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            self._wait_for_listener(process, port, time.monotonic() + _STARTUP_SECONDS)
            display = _Display(secrets.token_urlsafe(24), display_name, port, process)
            with self._lock:
                rejected = self._closed
                if rejected:
                    self._unavailable = True
                else:
                    self._display = display
                    self._unavailable = False
            if rejected:
                _stop_process(process)
                return None
            return display.generation
        except Exception:
            _stop_process(process)
            with self._lock:
                self._unavailable = True
            return None

    def stop_display(self, generation: str) -> None:
        """Retire exactly this generation, then stop its owned process."""
        with self._lock:
            display = self._retire_locked(generation)
        if display is not None:
            _stop_process(display.process)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            display = self._retire_locked()
            self._sessions.clear()
            self._connections.clear()
        if display is not None:
            _stop_process(display.process)

    def status(self) -> tuple[str, str | None]:
        if not self.enabled:
            return "unavailable", None
        stale = None
        with self._lock:
            display = self._display
            if display is not None and display.process.poll() is not None:
                stale = self._retire_locked(display.generation)
                self._unavailable = True
                result = ("unavailable", None)
            elif display is not None:
                result = ("live", display.generation)
            else:
                result = ("unavailable" if self._unavailable else "idle", None)
        _stop_process(stale.process if stale else None)
        return result

    def _prune_sessions_locked(self, now: float) -> None:
        for key, session in list(self._sessions.items()):
            if session.expires_at <= now:
                self._sessions.pop(key, None)

    def authenticate(self, session_id: str | None) -> bool:
        if not self.enabled or not isinstance(session_id, str) or len(session_id) > 256:
            return False
        now = time.monotonic()
        with self._lock:
            self._prune_sessions_locked(now)
            session = self._sessions.get(session_id)
            return session is not None and session.expires_at > now

    def issue_session(self, client: str, token: str) -> str | None:
        """Rate-limit login attempts and issue an opaque, short-lived cookie value."""
        if not self.enabled or not isinstance(token, str) or len(token) > 512:
            return None
        now = time.monotonic()
        try:
            candidate = token.encode("utf-8")
        except UnicodeError:
            return None
        with self._lock:
            # Bound this attacker-controlled map and remove stale entries.
            for address, history in list(self._attempts.items()):
                while history and history[0] <= now - _LOGIN_WINDOW_SECONDS:
                    history.popleft()
                if not history:
                    self._attempts.pop(address, None)
            if client not in self._attempts and len(self._attempts) >= _MAX_LOGIN_CLIENTS:
                return None
            attempts = self._attempts[client]
            if len(attempts) >= _MAX_LOGIN_ATTEMPTS:
                return None
            attempts.append(now)
            # compare_digest is deliberately reached for every non-oversized
            # candidate; no configuration state or token is reflected outward.
            if not hmac.compare_digest(hashlib.sha256(candidate).digest(), self._token_digest):
                return None
            self._prune_sessions_locked(now)
            if len(self._sessions) >= _MAX_SESSIONS:
                return None
            session_id = secrets.token_urlsafe(32)
            self._sessions[session_id] = _Session(now + self._session_seconds)
            return session_id

    def revoke(self, session_id: str | None) -> None:
        if isinstance(session_id, str):
            with self._lock:
                self._sessions.pop(session_id, None)

    def claim_connection(self) -> tuple[str, int] | None:
        """Snapshot one live generation and reserve a bounded viewer slot."""
        with self._lock:
            display = self._display
            if display is None or display.process.poll() is not None:
                return None
            if self._connections[display.generation] >= self._max_viewers:
                return None
            self._connections[display.generation] += 1
            return display.generation, display.port

    def release_connection(self, generation: str) -> None:
        with self._lock:
            if self._connections[generation] > 1:
                self._connections[generation] -= 1
            else:
                self._connections.pop(generation, None)

    def generation_is_live(self, generation: str) -> bool:
        with self._lock:
            display = self._display
            return bool(display and display.generation == generation and display.process.poll() is None)


def _headers(response: Response) -> Response:
    response.headers.update(_SECURITY_HEADERS)
    return response


def _json(status_code: int, content: dict[str, Any]) -> JSONResponse:
    return _headers(JSONResponse(status_code=status_code, content=content))  # type: ignore[return-value]


def create_router(viewer: DisplayViewer) -> APIRouter:
    """Build the isolated /desktop API, assets and authenticated WS endpoint."""
    router = APIRouter()

    def enabled_or_404() -> Response | None:
        return None if viewer.enabled else _json(404, {"detail": "Not found"})

    def origin_ok(request: Request | WebSocket) -> bool:
        try:
            supplied = request.headers.get("origin", "").encode("utf-8")
        except UnicodeError:
            return False
        return hmac.compare_digest(hashlib.sha256(supplied).digest(), viewer._origin_digest)

    def session_from(request: Request | WebSocket) -> str | None:
        return request.cookies.get(_COOKIE_NAME)

    def authenticated(request: Request | WebSocket) -> bool:
        return viewer.authenticate(session_from(request))

    @router.get("/desktop", include_in_schema=False)
    async def desktop() -> Response:
        disabled = enabled_or_404()
        if disabled:
            return disabled
        index = Path(__file__).with_name("viewer_static") / "index.html"
        if not index.is_file():
            return _json(404, {"detail": "Not found"})
        try:
            return _headers(Response(index.read_bytes(), media_type="text/html; charset=utf-8"))
        except OSError:
            return _json(404, {"detail": "Not found"})

    @router.post("/desktop/login", include_in_schema=False)
    async def login(request: Request) -> Response:
        disabled = enabled_or_404()
        if disabled:
            return disabled
        if not origin_ok(request):
            return _json(404, {"detail": "Not found"})
        try:
            chunks: list[bytes] = []
            received = 0
            async for chunk in request.stream():
                received += len(chunk)
                if received > _MAX_LOGIN_BODY:
                    raise ValueError("request body too large")
                chunks.append(chunk)
            payload = json.loads(b"".join(chunks))
        except (ValueError, UnicodeError, json.JSONDecodeError):
            payload = None
        raw_token = payload.get("token") if isinstance(payload, dict) and set(payload) == {"token"} else None
        # Keep the supplied credential redacted if this request is ever
        # represented by a framework error or debug tool.
        token = SecretStr(raw_token).get_secret_value() if isinstance(raw_token, str) and len(raw_token) <= 512 else None
        client = request.client.host if request.client else "unknown"
        session = viewer.issue_session(client, token) if token is not None else None
        if session is None:
            return _json(401, {"detail": "Unauthorized"})
        response = _json(200, {"status": "ok"})
        response.set_cookie(
            _COOKIE_NAME, session, max_age=viewer._session_seconds, httponly=True,
            samesite="strict", secure=viewer.secure_cookie, path="/desktop",
        )
        return response

    @router.get("/desktop/status", include_in_schema=False)
    async def status(request: Request) -> Response:
        disabled = enabled_or_404()
        if disabled:
            return disabled
        if not authenticated(request):
            return _json(401, {"detail": "Unauthorized"})
        state, generation = viewer.status()
        return _json(200, {"state": state, "generation": generation})

    @router.post("/desktop/logout", include_in_schema=False)
    async def logout(request: Request) -> Response:
        disabled = enabled_or_404()
        if disabled:
            return disabled
        if not origin_ok(request):
            return _json(404, {"detail": "Not found"})
        session = session_from(request)
        if not authenticated(request):
            return _json(401, {"detail": "Unauthorized"})
        viewer.revoke(session)
        response = _json(200, {"status": "ok"})
        response.delete_cookie(_COOKIE_NAME, path="/desktop", httponly=True, samesite="strict", secure=viewer.secure_cookie)
        return response

    @router.websocket("/desktop/ws")
    async def websocket_bridge(websocket: WebSocket) -> None:
        if not viewer.enabled or not origin_ok(websocket) or not authenticated(websocket):
            await websocket.close(code=1008)
            return
        session_id = session_from(websocket)
        claim = viewer.claim_connection()
        if claim is None:
            await websocket.close(code=1013)
            return
        generation, port = claim
        reader = writer = None
        tasks: list[asyncio.Task[Any]] = []

        def still_authorized() -> bool:
            # Both expiry/revocation and generation retirement are observed on
            # every bounded I/O cycle, so a socket never outlives either.
            return viewer.authenticate(session_id) and viewer.generation_is_live(generation)
        try:
            try:
                reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", port), _IO_TIMEOUT_SECONDS)
            except (OSError, asyncio.TimeoutError):
                await websocket.close(code=1011)
                return
            if not still_authorized():
                await websocket.close(code=1001)
                return
            protocols = websocket.scope.get("subprotocols", [])
            await websocket.accept(
                subprotocol="binary" if "binary" in protocols else None,
                headers=[(key.encode("latin-1"), value.encode("latin-1")) for key, value in _SECURITY_HEADERS.items()],
            )

            async def browser_to_vnc() -> None:
                while still_authorized():
                    try:
                        message = await asyncio.wait_for(websocket.receive(), _IO_TIMEOUT_SECONDS)
                    except asyncio.TimeoutError:
                        continue
                    if message.get("type") == "websocket.disconnect":
                        return
                    data = message.get("bytes")
                    if not isinstance(data, bytes) or len(data) > _MAX_BINARY_FRAME:
                        return
                    if not still_authorized():
                        return
                    writer.write(data)
                    await asyncio.wait_for(writer.drain(), _IO_TIMEOUT_SECONDS)

            async def vnc_to_browser() -> None:
                while still_authorized():
                    try:
                        data = await asyncio.wait_for(reader.read(_MAX_BINARY_FRAME), _IO_TIMEOUT_SECONDS)
                    except asyncio.TimeoutError:
                        continue
                    if not data:
                        return
                    if not still_authorized():
                        return
                    await asyncio.wait_for(websocket.send_bytes(data), _IO_TIMEOUT_SECONDS)

            tasks = [asyncio.create_task(browser_to_vnc()), asyncio.create_task(vnc_to_browser())]
            _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            if writer is not None:
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), _IO_TIMEOUT_SECONDS)
                except Exception:
                    pass
            viewer.release_connection(generation)
            try:
                await websocket.close()
            except (RuntimeError, WebSocketDisconnect):
                pass

    # APIRouter mounts are not reliably copied by FastAPI.include_router(), so
    # serve both static trees through ordinary routes instead. The assets are
    # public only after the feature gate; they have no task/session data.
    ui_files = StaticFiles(directory=Path(__file__).with_name("viewer_static"), check_dir=False)
    novnc_files = StaticFiles(directory=viewer.assets, check_dir=False)

    async def static_response(files: StaticFiles, path: str, request: Request) -> Response:
        disabled = enabled_or_404()
        if disabled:
            return disabled
        try:
            return _headers(await files.get_response(path, request.scope))
        except Exception:
            # Do not reveal deployment paths or StaticFiles configuration.
            return _json(404, {"detail": "Not found"})

    @router.get("/desktop/static/{path:path}", include_in_schema=False)
    async def ui_asset(path: str, request: Request) -> Response:
        return await static_response(ui_files, path, request)

    @router.get("/desktop/novnc/{path:path}", include_in_schema=False)
    async def novnc_asset(path: str, request: Request) -> Response:
        return await static_response(novnc_files, path, request)

    return router
