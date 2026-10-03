"""Task-local fail-closed finite HTTP readiness; never retain payloads or URLs."""
import json
import time
from urllib.parse import urlsplit


class NetworkIdleError(RuntimeError):
    pass


class NetworkIdleTracker:
    MAX_PENDING = 4096
    MAX_EVENTS = 20000
    FAILURE = "Network readiness could not be confirmed; this invocation entered no data"

    def __init__(self, driver, quiet_seconds=0.5, max_wait_seconds=20, *, clock=time.monotonic, sleep=time.sleep):
        if not 0.1 <= quiet_seconds <= 5 or not 0.1 <= max_wait_seconds <= 60:
            raise ValueError("Invalid readiness settings")
        self.driver, self.clock, self.sleep = driver, clock, sleep
        self.quiet_seconds, self.max_wait_seconds = quiet_seconds, max_wait_seconds
        self.pending = set()
        self.failed = False
        try:
            if "performance" not in driver.log_types:
                self._fail()
            if not isinstance(driver.execute_cdp_cmd("Network.enable", {}), dict):
                self._fail()
            self.drain()
        except Exception:
            self._fail()

    def _fail(self):
        self.failed = True
        raise NetworkIdleError(self.FAILURE) from None

    def drain(self):
        if self.failed:
            self._fail()
        activity = False
        try:
            entries = self.driver.get_log("performance")
            if not isinstance(entries, list) or len(entries) > self.MAX_EVENTS:
                self._fail()
            for entry in entries:
                raw = entry["message"]
                if not isinstance(raw, str) or len(raw) > 1048576:
                    self._fail()
                message = json.loads(raw)["message"]
                method = message["method"]
                if not isinstance(method, str):
                    self._fail()
                if method in ("Inspector.detached", "Target.detachedFromTarget", "Tracing.bufferUsage"):
                    self._fail()
                if method not in ("Network.requestWillBeSent", "Network.responseReceived", "Network.loadingFinished", "Network.loadingFailed"):
                    continue
                params = message["params"]
                rid = params["requestId"]
                if not isinstance(rid, str) or not rid or len(rid) > 512:
                    self._fail()
                if method == "Network.requestWillBeSent":
                    url = params["request"]["url"]
                    resource = params.get("type", "")
                    if not isinstance(url, str) or not isinstance(resource, str):
                        self._fail()
                    if urlsplit(url).scheme.lower() in ("http", "https") and resource not in ("WebSocket", "EventSource"):
                        self.pending.add(rid)
                        activity = True
                    else:
                        activity = activity or rid in self.pending
                        self.pending.discard(rid)
                elif method == "Network.responseReceived":
                    mime = params["response"]["mimeType"]
                    resource = params.get("type", "")
                    if not isinstance(mime, str) or not isinstance(resource, str):
                        self._fail()
                    if resource in ("WebSocket", "EventSource") or mime.split(";", 1)[0].strip().lower() == "text/event-stream":
                        activity = activity or rid in self.pending
                        self.pending.discard(rid)
                else:
                    activity = activity or rid in self.pending
                    self.pending.discard(rid)
                if len(self.pending) > self.MAX_PENDING:
                    self._fail()
            return activity
        except Exception:
            self._fail()

    def wait(self, deadline, guard, cancelled=None):
        end = min(deadline, self.clock() + self.max_wait_seconds)
        quiet_since = None
        while True:
            guard()
            if self.clock() >= end:
                self._fail()
            activity = self.drain()
            guard()
            now = self.clock()
            if now >= end:
                self._fail()
            if self.pending or activity:
                quiet_since = None
            elif quiet_since is None:
                quiet_since = now
            elif now - quiet_since >= self.quiet_seconds:
                return
            delay = min(0.05, end - now)
            if cancelled is None:
                self.sleep(delay)
            elif cancelled.wait(delay):
                guard()
                self._fail()
