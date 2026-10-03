import json

import pytest

from app.network_idle import NetworkIdleError, NetworkIdleTracker


class Clock:
    value = 0.0

    def __call__(self):
        return self.value

    def sleep(self, delay):
        self.value += delay


def event(method, rid="1", **params):
    return {"message": json.dumps({"message": {"method": "Network." + method,
            "params": {"requestId": rid, **params}}})}


def request(rid="1", resource="Fetch"):
    return event("requestWillBeSent", rid, type=resource,
                 request={"url": "https://example.org/private?secret=not-retained"})


class Driver:
    log_types = ["performance"]
    def __init__(self, clock, events=()):
        self.clock = clock
        self.events = list(events)
        self.commands = []
        self.broken = False

    def execute_cdp_cmd(self, command, params):
        self.commands.append((command, params))
        return {}

    def get_log(self, name):
        assert name == "performance"
        if self.broken:
            raise RuntimeError("private diagnostic")
        ready = [item for when, item in self.events if when <= self.clock()]
        self.events = [(when, item) for when, item in self.events if when > self.clock()]
        return ready


def tracker(events=(), **kwargs):
    clock = Clock()
    driver = Driver(clock, events)
    value = NetworkIdleTracker(driver, clock=clock, sleep=clock.sleep, **kwargs)
    return value, clock, driver


@pytest.mark.parametrize("finish", ["loadingFinished", "loadingFailed"])
def test_historical_pending_and_delayed_completion(finish):
    value, clock, driver = tracker([(0, request()), (0.3, event(finish))])
    assert value.pending == {"1"}
    value.wait(10, lambda: None)
    assert clock() >= 0.8
    assert value.pending == set()
    assert driver.commands == [("Network.enable", {})]
    assert "private" not in repr(value.pending)


def test_redirect_reuses_id_without_resetting_pending_history():
    value, clock, _ = tracker([(0, request()), (0.2, request()), (0.8, event("loadingFinished"))])
    value.wait(10, lambda: None)
    assert clock() >= 1.3


def test_activity_resets_quiet_window_and_each_wait_starts_fresh():
    value, clock, _ = tracker([(0.3, request()), (0.3, event("loadingFinished"))])
    value.wait(10, lambda: None)
    first = clock()
    assert first >= 0.8
    value.wait(10, lambda: None)
    assert clock() >= first + 0.5


@pytest.mark.parametrize("resource", ["EventSource", "WebSocket"])
def test_explicit_streams_do_not_block(resource):
    value, clock, _ = tracker([(0, request(resource=resource))])
    value.wait(2, lambda: None)
    assert clock() < 1


def test_sse_response_classifies_fetch_as_persistent():
    value, clock, _ = tracker([(0, request()), (0.2, event("responseReceived", type="Fetch", response={"mimeType": "text/event-stream; charset=utf-8"}))])
    value.wait(2, lambda: None)
    assert clock() >= 0.7


@pytest.mark.parametrize("deadline,maximum", [(0.4, 20), (10, 0.4)])
def test_hung_request_timeout_is_bounded_and_sanitized(deadline, maximum):
    value, clock, _ = tracker([(0, request())], max_wait_seconds=maximum)
    with pytest.raises(NetworkIdleError, match="this invocation entered no data") as error:
        value.wait(deadline, lambda: None)
    assert clock() <= 0.401
    assert "secret" not in str(error.value)
    assert value.pending == {"1"}


@pytest.mark.parametrize("bad", [
    {"message": "not json"},
    event("requestWillBeSent", request={}),
    event("requestWillBeSent", rid=42, request={"url": "https://example.org"}),
    event("responseReceived", response={}),
])
def test_malformed_events_poison_tracker(bad):
    with pytest.raises(NetworkIdleError):
        tracker([(0, bad)])


def test_instrumentation_loss_is_sticky():
    value, _, driver = tracker()
    driver.broken = True
    with pytest.raises(NetworkIdleError):
        value.wait(10, lambda: None)
    driver.broken = False
    with pytest.raises(NetworkIdleError):
        value.wait(10, lambda: None)


@pytest.mark.parametrize("bound", ["MAX_PENDING", "MAX_EVENTS"])
def test_state_and_event_bounds_fail_closed(bound):
    value, _, driver = tracker()
    setattr(value, bound, 1)
    driver.events = [(0, request("1")), (0, request("2"))]
    with pytest.raises(NetworkIdleError):
        value.wait(10, lambda: None)


def test_cancellation_guard_runs_before_draining_or_success():
    value, clock, _ = tracker()
    calls = []
    def guard():
        calls.append(clock())
        if clock() >= 0.2:
            raise RuntimeError("cancelled")
    with pytest.raises(RuntimeError, match="cancelled"):
        value.wait(10, guard)
    assert clock() <= 0.21
    assert len(calls) > 2


def test_non_http_requests_are_not_blockers():
    value, _, _ = tracker([(0, event("requestWillBeSent", request={"url": "data:text/plain,example"}))])
    value.wait(2, lambda: None)


def test_document_navigation_preserves_subframe_pending():
    value, clock, _ = tracker([(0, request("subframe")), (0.1, request("document", "Document")),
                              (0.2, event("loadingFinished", "document")),
                              (0.6, event("loadingFailed", "subframe"))])
    value.wait(3, lambda: None)
    assert clock() >= 1.1


def test_cancellation_event_interrupts_sleep():
    value, clock, _ = tracker()
    class Cancellation:
        def wait(self, delay):
            clock.sleep(delay)
            return True
    with pytest.raises(NetworkIdleError):
        value.wait(3, lambda: None, Cancellation())
    assert clock() <= 0.05


@pytest.mark.parametrize("setting,bad", [
    ("network_idle_quiet_ms", 99), ("network_idle_quiet_ms", 5001),
    ("network_idle_max_wait_seconds", 0), ("network_idle_max_wait_seconds", 61),
])
def test_settings_bounds(setting, bad):
    from app.config import Settings
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{setting: bad})


def test_network_enable_failure_is_sanitized():
    class Unavailable:
        def execute_cdp_cmd(self, *args):
            raise RuntimeError("private transport diagnostic")
    with pytest.raises(NetworkIdleError) as error:
        NetworkIdleTracker(Unavailable())
    assert "private" not in str(error.value)


def test_explicit_detachment_fails_closed():
    with pytest.raises(NetworkIdleError):
        tracker([(0, {"message": json.dumps({"message": {"method": "Inspector.detached", "params": {}}})})])
