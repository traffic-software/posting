"""CDP-backed, task-scoped browser download collection.

The collector intentionally does not fetch download URLs itself: Chrome keeps the
session cookies and CDP is the sole authority for transfer completion.
"""
from __future__ import annotations

import math
import re
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from app.schemas import https_origin

_GUID = re.compile(r"^[A-Za-z0-9_-]{1,160}$")
_NAME = re.compile(r"^[^/\\\x00-\x1f]{1,180}$")


class BrowserDownloads:
    """Collect one explicitly armed Chrome download at a time."""

    def __init__(self, driver, artifact_session, guard, validate_url, *, clock=time.monotonic):
        self.driver = driver
        self.artifact_session = artifact_session
        self.guard = guard
        self.validate_url = validate_url
        self.clock = clock
        self.available = False
        self.disabled_reason = None
        self.sanitized_disabled_reason = None
        self._lock = threading.RLock()
        self._command_lock = threading.Lock()
        self._attempts = {}
        self._active = None
        self._closed = False
        self._callbacks = []
        self._devtools = self._connection = None
        self._directory = Path(artifact_session.browser_directory)
        try:
            # The browser directory is session-owned; never make a caller-selected path.
            self._directory.mkdir(parents=True, exist_ok=True)
            devtools, connection = driver.start_devtools()
            browser = getattr(devtools, "browser", None)
            if browser is None or not all(hasattr(browser, name) for name in (
                "set_download_behavior", "cancel_download", "DownloadWillBegin", "DownloadProgress",
            )):
                raise RuntimeError("CDP download events are unavailable")
            self._devtools, self._connection = devtools, connection
            self._callbacks = [
                (browser.DownloadWillBegin, connection.add_callback(browser.DownloadWillBegin, self._will_begin)),
                (browser.DownloadProgress, connection.add_callback(browser.DownloadProgress, self._progress)),
            ]
            self._set_behavior("deny", events=False)
            self.available = True
        except Exception:
            self._disable("Browser download transport is unavailable")

    def _disable(self, reason):
        self.available = False
        self.disabled_reason = reason
        self.sanitized_disabled_reason = reason
        connection = self._connection
        for event, callback_id in self._callbacks:
            try:
                connection.remove_callback(event, callback_id)
            except Exception:
                pass
        self._callbacks = []

    def _command(self, generator):
        """Run Browser-domain command at the root CDP session, serially."""
        with self._command_lock:
            old = getattr(self._connection, "session_id", None)
            try:
                # Selenium attaches its socket to a page. Browser.* must be root-scoped.
                self._connection.session_id = None
                return self._connection.execute(generator)
            finally:
                self._connection.session_id = old

    def _set_behavior(self, behavior, *, events):
        return self._command(self._devtools.browser.set_download_behavior(
            behavior, download_path=str(self._directory), events_enabled=events,
        ))

    @staticmethod
    def _origin(value):
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("not a public HTTPS origin")
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("not an origin")
        return https_origin(value)

    def _source_is_allowed(self, value, origin):
        """This runs on Selenium's callback thread: no DOM/WebDriver calls."""
        try:
            parsed = urlsplit(value)
            if parsed.scheme == "blob":
                # urlsplit('blob:https://host/id') leaves the inner URL in path.
                inner = urlsplit(parsed.path)
                if inner.scheme != "https" or not inner.hostname or inner.username or inner.password:
                    return False
                blob_origin = https_origin(parsed.path)
                return blob_origin == origin
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                return False
            self.validate_url(value)
            return True
        except Exception:
            return False

    @staticmethod
    def _filename(value):
        return isinstance(value, str) and bool(_NAME.fullmatch(value)) and value not in {".", ".."}

    def arm(self, origin: str):
        """Reserve quota and allow exactly the next valid browser download."""
        if not self.available:
            raise RuntimeError(self.disabled_reason or "Browser downloads are unavailable")
        try:
            self.guard()
            origin = self._origin(origin)
            self.validate_url(origin)
        except Exception as exc:
            raise ValueError("Download origin is not an allowed public HTTPS origin") from exc
        with self._lock:
            if self._closed:
                raise RuntimeError("Browser downloads are closed")
            if self._active is not None:
                raise RuntimeError("A browser download is already armed")
        reservation = self.artifact_session.reserve(
            purpose="output", name="download.bin", media_type="application/octet-stream",
        )
        attempt_id = uuid4().hex
        attempt = {"id": attempt_id, "origin": origin, "reservation": reservation,
                   "guid": None, "name": None, "received": 0, "state": "pending",
                   "error": None, "completed": False, "artifact": None}
        with self._lock:
            unavailable = self._closed or self._active is not None
            if not unavailable:
                self._attempts[attempt_id] = attempt
                self._active = attempt_id
        if unavailable:
            reservation.abort()
            raise RuntimeError("Browser download is no longer available")
        try:
            self.guard()
            self._set_behavior("allowAndName", events=True)
        except Exception as exc:
            self._fail(attempt, "Browser download transport could not be armed")
            raise RuntimeError("Browser download transport could not be armed") from exc
        return attempt_id

    def _cancel_guid(self, guid):
        if not guid:
            return
        try:
            self._command(self._devtools.browser.cancel_download(guid))
        except Exception:
            pass

    def _fail(self, attempt, message, *, cancel=True):
        guid = None
        with self._lock:
            if attempt["state"] in {"ready", "failed"}:
                return
            attempt["state"], attempt["error"] = "failed", message
            guid = attempt["guid"]
        if cancel:
            self._cancel_guid(guid)
        try:
            attempt["reservation"].abort()
        except Exception:
            pass
        try:
            self._set_behavior("deny", events=False)
        except Exception:
            pass
        with self._lock:
            if self._active == attempt["id"]:
                self._active = None

    def _will_begin(self, event):
        guid = getattr(event, "guid", None)
        try:
            self.guard()
            guid, url, name = event.guid, event.url, event.suggested_filename
            with self._lock:
                attempt = self._attempts.get(self._active)
                existing_guid = attempt["guid"] if attempt else None
            if existing_guid is not None:
                if guid != existing_guid:
                    self._cancel_guid(guid if isinstance(guid, str) else None)
                return
            if not attempt:
                self._cancel_guid(guid if isinstance(guid, str) else None)
                return
            if not isinstance(guid, str) or not _GUID.fullmatch(guid) or not self._filename(name) or not self._source_is_allowed(url, attempt["origin"]):
                self._cancel_guid(guid if isinstance(guid, str) else None)
                self._fail(attempt, "Browser download source or metadata is not permitted", cancel=False)
                return
            with self._lock:
                # A second event is never an implicit second output.
                if self._active != attempt["id"] or attempt["guid"] is not None:
                    reject = guid
                else:
                    attempt["guid"], attempt["name"] = guid, name
                    reject = None
            if reject:
                self._cancel_guid(reject)
        except Exception:
            # CDP callbacks must stay cheap and must not leak URLs/errors.
            self._cancel_guid(guid if isinstance(guid, str) else None)
            return

    def _progress(self, event):
        try:
            self.guard()
            with self._lock:
                attempt = self._attempts.get(self._active)
                if not attempt or event.guid != attempt["guid"] or attempt["state"] != "pending":
                    return
                received = max(0, int(event.received_bytes))
                declared = max(0, int(event.total_bytes))
                maximum = int(attempt["reservation"].max_bytes)
                over = received > maximum or (declared and declared > maximum)
                failed = not over and event.state not in {"inProgress", "completed"}
                if not over and not failed:
                    attempt["received"] = received
                    if event.state == "completed":
                        attempt["completed"] = True
            if over:
                self._fail(attempt, "Browser download exceeded its reserved size")
            elif failed:
                self._fail(attempt, "Browser download failed")
        except Exception:
            with self._lock:
                attempt = self._attempts.get(self._active)
            if attempt is not None:
                self._fail(attempt, "Browser download guard failed")

    def _import_completed(self, attempt):
        with self._lock:
            if attempt["state"] != "pending" or not attempt["completed"] or not attempt["guid"]:
                return
            guid, name = attempt["guid"], attempt["name"]
        path = self._directory / guid
        try:
            # allowAndName writes exactly this GUID path. Ignore CDP's optional path.
            if path.is_symlink() or not path.is_file() or path.name != guid or path.suffix == ".crdownload":
                self._fail(attempt, "Browser download completion file is unavailable", cancel=False)
                return
            if path.stat().st_size > int(attempt["reservation"].max_bytes):
                self._fail(attempt, "Browser download exceeded its reserved size", cancel=False)
                return
            artifact = self.artifact_session.import_browser_file(path, name, attempt["reservation"])
            with self._lock:
                if attempt["state"] == "pending":
                    attempt["artifact"], attempt["state"] = artifact, "ready"
            self._set_behavior("deny", events=False)
            with self._lock:
                if self._active == attempt["id"]:
                    self._active = None
        except Exception:
            self._fail(attempt, "Browser download could not be imported", cancel=False)

    @staticmethod
    def _result(attempt):
        result = {"status": attempt["state"]}
        if attempt["state"] == "pending" and attempt["received"]:
            result["received_bytes"] = attempt["received"]
        if attempt["state"] == "ready":
            result["artifact"] = attempt["artifact"]
        elif attempt["state"] == "failed":
            result["error"] = attempt["error"]
        return result

    def poll(self, attempt_id):
        with self._lock:
            attempt = self._attempts.get(attempt_id)
            if attempt is None:
                return {"status": "failed", "error": "Unknown browser download"}
        if attempt["state"] == "pending":
            try:
                self.guard()
            except Exception:
                self._fail(attempt, "Browser download deadline or guard expired")
        self._import_completed(attempt)
        with self._lock:
            return self._result(attempt)

    def wait(self, attempt_id, timeout: float):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout < 0:
            raise ValueError("timeout must be non-negative")
        end = self.clock() + timeout
        while True:
            result = self.poll(attempt_id)
            if result["status"] != "pending":
                return result
            try:
                self.guard()
            except Exception:
                self.cancel(attempt_id)
                return self.poll(attempt_id)
            remaining = end - self.clock()
            if remaining <= 0:
                return result  # A bounded observation window is not the transfer deadline.
            time.sleep(min(0.05, remaining))

    def cancel(self, attempt_id):
        with self._lock:
            attempt = self._attempts.get(attempt_id)
        if attempt is not None:
            self._fail(attempt, "Browser download was cancelled")
        return self.poll(attempt_id)

    def finalize(self):
        """Import completed transfers only; this deliberately never waits."""
        with self._lock:
            attempts = tuple(self._attempts.values())
        for attempt in attempts:
            self._import_completed(attempt)
        return {attempt["id"]: self._result(attempt) for attempt in attempts}

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            pending = [item for item in self._attempts.values() if item["state"] == "pending"]
        for attempt in pending:
            self._fail(attempt, "Browser downloads closed")
        if self._connection is not None:
            for event, callback_id in self._callbacks:
                try:
                    self._connection.remove_callback(event, callback_id)
                except Exception:
                    pass
        self._callbacks = []
        if self._devtools is not None:
            try:
                self._set_behavior("deny", events=False)
            except Exception:
                pass
