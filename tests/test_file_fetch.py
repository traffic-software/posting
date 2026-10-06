from email.message import Message
import threading
import time

import pytest

from app.file_fetch import FileFetchError, _PinnedHTTPSConnection, fetch_file


class Response:
    def __init__(self, status=200, chunks=(), headers=None):
        self.status = status
        self.chunks = list(chunks)
        self.headers = headers or {}
        self.msg = Message()
        for name, value in self.headers.items():
            self.msg[name] = str(value)

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def read1(self, size):
        assert size == 64 * 1024
        return self.chunks.pop(0) if self.chunks else b""

    def close(self):
        pass


class Connection:
    def __init__(self, response):
        self.response = response
        self.requests = []
        self.sock = self

    def settimeout(self, value):
        self.timeout = value

    def request(self, method, target, headers):
        self.requests.append((method, target, headers))

    def getresponse(self):
        return self.response

    def close(self):
        pass


def public(host, port=None):
    return ["8.8.8.8"]


def run(url, responses, *, resolver=public, **kwargs):
    made = []

    def factory(*args, **values):
        connection = Connection(responses[len(made)])
        made.append((args, values, connection))
        return connection

    output = []
    result = fetch_file(url, output.append, lambda: None, time.monotonic() + 20,
                        max_bytes=1000, resolver=resolver, connection_factory=factory, **kwargs)
    return result, b"".join(output), made


def test_fetches_opaque_bytes_with_pinned_public_address_and_safe_metadata():
    result, output, made = run(
        "https://files.example.test/path/ignored",
        [Response(chunks=[b"abc", b"def"], headers={
            "Content-Length": "6", "Content-Type": "application/x-custom; x=y",
            "Content-Disposition": "attachment; filename*=UTF-8''report%20%F0%9F%93%84.bin",
        })],
    )
    assert output == b"abcdef"
    assert result == {"name": "report 📄.bin", "media_type": "application/x-custom", "size_bytes": 6}
    assert made[0][1]["ip"] == "8.8.8.8"
    assert made[0][2].requests == [("GET", "/path/ignored", {
        "Host": "files.example.test", "Accept-Encoding": "identity", "Connection": "close",
    })]


@pytest.mark.parametrize("url", [
    "file:///tmp/x", "https://user:password@example.test/x", "https://localhost/x",
    "https://example.test/\nsecret", "https://127.0.0.1/x",
])
def test_rejects_non_public_or_credential_urls_before_connect(url):
    calls = 0

    def factory(*args, **kwargs):
        nonlocal calls
        calls += 1

    with pytest.raises(FileFetchError) as error:
        fetch_file(url, lambda _: None, lambda: None, time.monotonic() + 5, max_bytes=1,
                   resolver=public, connection_factory=factory)
    assert calls == 0
    assert "password" not in str(error.value) and "secret" not in str(error.value)


def test_rejects_private_dns_answers_and_revalidates_redirect_before_request():
    calls = 0

    def private(host, port=None):
        return ["8.8.8.8", "127.0.0.1"]

    def factory(*args, **kwargs):
        nonlocal calls
        calls += 1
        return Connection(Response(302, headers={"Location": "https://private.test/x"}))

    with pytest.raises(FileFetchError, match="not public"):
        fetch_file("https://example.test/x", lambda _: None, lambda: None, time.monotonic() + 5,
                   max_bytes=1, resolver=private, connection_factory=factory)
    assert calls == 0

    def redirect_resolver(host, port=None):
        return ["8.8.8.8"] if host == "example.test" else ["10.0.0.1"]

    with pytest.raises(FileFetchError, match="not public"):
        fetch_file("https://example.test/x", lambda _: None, lambda: None, time.monotonic() + 5,
                   max_bytes=1, resolver=redirect_resolver, connection_factory=factory)
    assert calls == 1


def test_rejects_downgrade_and_redirect_cap():
    with pytest.raises(FileFetchError, match="Insecure"):
        run("https://example.test/x", [Response(302, headers={"Location": "http://example.test/x"})])
    with pytest.raises(FileFetchError, match="Too many"):
        run("https://example.test/x", [Response(302, headers={"Location": "/x"})], max_redirects=0)


def test_size_truncation_and_encoding_failures_never_finish_the_partial_writer():
    cases = [
        Response(chunks=[b"ab"], headers={"Content-Length": "3"}),
        Response(chunks=[b"abcd"], headers={"Content-Length": "4"}),
        Response(chunks=[b"abc"], headers={"Content-Encoding": "gzip"}),
    ]
    for response in cases:
        output = []
        with pytest.raises(FileFetchError):
            fetch_file("https://example.test/x", output.append, lambda: None, time.monotonic() + 5,
                       max_bytes=3, resolver=public, connection_factory=lambda *a, r=response, **k: Connection(r))
        assert sum(len(chunk) for chunk in output) <= 3  # Partial bytes are caller-owned and must be aborted.


def test_cancellation_during_a_read_does_not_publish_staged_bytes():
    checks = 0
    output = []

    def guard():
        nonlocal checks
        checks += 1
        if checks == 6:  # The next read-loop checkpoint follows the first chunk.
            raise RuntimeError("cancelled")

    with pytest.raises(FileFetchError, match="cancelled"):
        fetch_file("https://example.test/x", output.append, guard, time.monotonic() + 5,
                   max_bytes=3, resolver=public,
                   connection_factory=lambda *a, **k: Connection(Response(chunks=[b"abc"])))
    assert output == []


def test_guard_and_expired_budget_prevent_connection_and_no_server_error_leaks():
    calls = 0

    def factory(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise OSError("server secret https://example.test")

    with pytest.raises(FileFetchError, match="cancelled"):
        fetch_file("https://example.test/x", lambda _: None, lambda: (_ for _ in ()).throw(RuntimeError()),
                   time.monotonic() + 5, max_bytes=1, resolver=public, connection_factory=factory)
    with pytest.raises(FileFetchError, match="timed out"):
        fetch_file("https://example.test/x", lambda _: None, lambda: None, time.monotonic() - 1,
                   max_bytes=1, resolver=public, connection_factory=factory)
    with pytest.raises(FileFetchError) as error:
        fetch_file("https://example.test/x", lambda _: None, lambda: None, time.monotonic() + 5,
                   max_bytes=1, resolver=public, connection_factory=factory)
    assert calls == 1 and "secret" not in str(error.value) and "example" not in str(error.value)


def test_pinned_https_connects_to_ip_but_uses_original_host_for_verified_sni(monkeypatch):
    events = []

    class Socket:
        def close(self):
            events.append("closed")

    class Context:
        def wrap_socket(self, sock, server_hostname):
            events.append((sock, server_hostname))
            return "tls-socket"

    monkeypatch.setattr("app.file_fetch.socket.create_connection", lambda address, timeout: events.append((address, timeout)) or Socket())
    monkeypatch.setattr("app.file_fetch.ssl.create_default_context", lambda: Context())
    connection = _PinnedHTTPSConnection("origin.example", 443, "8.8.8.8", 3)
    connection.connect()
    assert events[0][0] == ("8.8.8.8", 443)
    assert events[1][1] == "origin.example"
    assert connection.sock == "tls-socket"


@pytest.mark.parametrize("stop", ["deadline", "cancel", "network_timeout"])
def test_stalled_dns_is_bounded_and_does_not_connect(monkeypatch, stop):
    import app.file_fetch as module

    monkeypatch.setattr(module, "_DNS_SLOTS", threading.BoundedSemaphore(1))
    release, started, cancelled = threading.Event(), threading.Event(), threading.Event()
    connections = []

    def resolver(host, port):
        started.set()
        release.wait(2)
        return ["8.8.8.8"]

    def guard():
        if cancelled.is_set():
            raise RuntimeError("cancelled")

    timer = threading.Timer(0.05, cancelled.set) if stop == "cancel" else None
    if timer:
        timer.start()
    before = time.monotonic()
    try:
        with pytest.raises(FileFetchError):
            fetch_file("https://example.test/x", lambda _: None, guard,
                       before + (0.05 if stop == "deadline" else 2), max_bytes=1,
                       timeout=0.05 if stop == "network_timeout" else 2, resolver=resolver,
                       connection_factory=lambda *a, **k: connections.append(1))
        assert started.is_set()
        assert time.monotonic() - before < 0.5
        assert not connections
    finally:
        release.set()
        if timer:
            timer.cancel()


def test_stalled_dns_workers_keep_slots_until_resolution_finishes(monkeypatch):
    import app.file_fetch as module

    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(module, "_DNS_SLOTS", slots)
    release, finished = threading.Event(), threading.Event()
    calls = []

    def resolver(host, port):
        calls.append(host)
        try:
            release.wait(2)
            return ["8.8.8.8"]
        finally:
            finished.set()

    try:
        for _ in range(5):
            with pytest.raises(FileFetchError):
                fetch_file("https://example.test/x", lambda _: None, lambda: None,
                           time.monotonic() + 0.05, max_bytes=1, resolver=resolver)
        assert calls == ["example.test"]
        assert not slots.acquire(blocking=False)
    finally:
        release.set()
        assert finished.wait(1)
    assert slots.acquire(timeout=1)
    slots.release()
