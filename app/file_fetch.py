"""Small, pinned-IP HTTP downloader for untrusted public files."""

from __future__ import annotations

import http.client
import ipaddress
import math
import re
import socket
import ssl
import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import unquote, unquote_to_bytes, urljoin, urlsplit


_CHUNK = 64 * 1024
_MAX_REDIRECTS = 5
# Timed-out system DNS calls cannot be killed. Keep their daemon workers bounded
# process-wide, and retain each slot until its resolver actually returns.
_DNS_SLOTS = threading.BoundedSemaphore(4)
_MEDIA_TYPE = re.compile(r"^[!#$&^_.+\-A-Za-z0-9]+/[!#$&^_.+\-A-Za-z0-9]+$")
_HOST = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$", re.I)
_FILENAME_STAR = re.compile(r"(?:^|;)\s*filename\*\s*=\s*([^;]+)", re.I)
_FILENAME = re.compile(r'(?:^|;)\s*filename\s*=\s*("(?:[^"\\]|\\.)*"|[^;]*)', re.I)


class FileFetchError(RuntimeError):
    """A deliberately non-diagnostic error safe to give to an untrusted caller."""


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, pinned_ip: str, timeout: float):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._pinned_ip = pinned_ip

    def connect(self) -> None:
        sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


def _remaining(deadline: Any) -> float:
    try:
        return float(deadline - time.monotonic())
    except (TypeError, ValueError, OverflowError):
        raise FileFetchError("File fetch timed out") from None


def _check(guard: Callable[[], None], deadline: Any) -> float:
    try:
        guard()
    except FileFetchError:
        raise
    except Exception:
        raise FileFetchError("File fetch cancelled") from None
    remaining = _remaining(deadline)
    if remaining <= 0:
        raise FileFetchError("File fetch timed out")
    return remaining


def _public(address: str) -> str:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        raise FileFetchError("File URL is not public") from None
    if not parsed.is_global or parsed.is_multicast:
        raise FileFetchError("File URL is not public")
    return str(parsed)


def _resolve(host: str, port: int, resolver: Callable | None) -> list[str]:
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        return [_public(str(literal))]
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM) if resolver is None else resolver(host, port)
    except TypeError:
        try:
            records = resolver(host)  # type: ignore[misc]
        except Exception:
            raise FileFetchError("Could not resolve file host") from None
    except FileFetchError:
        raise
    except Exception:
        raise FileFetchError("Could not resolve file host") from None
    addresses: list[str] = []
    try:
        for record in records:
            value = record[4][0] if isinstance(record, tuple) and len(record) >= 5 else record
            address = _public(str(value))
            if address not in addresses:
                addresses.append(address)
    except (TypeError, IndexError):
        raise FileFetchError("Could not resolve file host") from None
    if not addresses:
        raise FileFetchError("Could not resolve file host")
    return addresses


def _resolve_bounded(host, port, resolver, guard, deadline, timeout):
    _check(guard, deadline)
    slots = _DNS_SLOTS
    if not slots.acquire(blocking=False):
        raise FileFetchError("File host resolution is unavailable")
    done = threading.Event()
    result = []
    errors = []

    def resolve():
        try:
            result.extend(_resolve(host, port, resolver))
        except Exception as exc:
            errors.append(exc)
        finally:
            slots.release()
            done.set()

    thread = threading.Thread(target=resolve, name="file-fetch-dns", daemon=True)
    try:
        thread.start()
    except BaseException:
        slots.release()
        raise
    resolution_deadline = time.monotonic() + timeout
    while True:
        remaining = min(_check(guard, deadline), resolution_deadline - time.monotonic())
        if remaining <= 0:
            raise FileFetchError("File host resolution timed out")
        if done.wait(min(0.02, remaining)):
            _check(guard, deadline)
            if errors:
                if isinstance(errors[0], FileFetchError):
                    raise errors[0]
                raise FileFetchError("Could not resolve file host") from None
            return result


def _target(url: str, resolver: Callable | None) -> tuple[str, str, int, str, str]:
    if not isinstance(url, str) or not url or len(url) > 8192 or any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise FileFetchError("Invalid file URL")
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").rstrip(".").encode("idna").decode("ascii").lower()
        port = parts.port if parts.port is not None else (443 if parts.scheme.lower() == "https" else 80)
    except (ValueError, UnicodeError):
        raise FileFetchError("Invalid file URL") from None
    scheme = parts.scheme.lower()
    if (scheme != "https" or not host or host == "localhost"
            or host.endswith((".localhost", ".local")) or parts.username is not None
            or parts.password is not None or "\\" in parts.netloc or not 1 <= port <= 65535):
        raise FileFetchError("Invalid file URL")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if len(host) > 253 or not _HOST.fullmatch(host):
            raise FileFetchError("Invalid file URL")
    pinned_ip = _resolve(host, port, resolver)[0]  # Every answer was checked before pinning one.
    path = parts.path or "/"
    return scheme, host, port, pinned_ip, path + (("?" + parts.query) if parts.query else "")


def _host_header(host: str, port: int, scheme: str) -> str:
    try:
        address = ipaddress.ip_address(host)
        shown = f"[{address}]" if address.version == 6 else str(address)
    except ValueError:
        shown = host
    return shown if port == (443 if scheme == "https" else 80) else f"{shown}:{port}"


def _connection(scheme: str, host: str, port: int, ip: str, timeout: float, factory: Callable | None):
    if factory is None:
        return _PinnedHTTPSConnection(host, port, ip, timeout)
    try:
        return factory(scheme=scheme, host=host, port=port, ip=ip, timeout=timeout)
    except TypeError:
        return factory(scheme, host, port, ip, timeout)


def _watch_transfer(connection, guard, deadline):
    """Interrupt socket work on cancellation/deadline, including slow header reads."""
    stopped = threading.Event()

    def watch():
        while not stopped.wait(0.05):
            try:
                _check(guard, deadline)
            except FileFetchError:
                try:
                    sock = getattr(connection, "sock", None)
                    if sock is not None:
                        sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    connection.close()
                except Exception:
                    pass
                return
    thread = threading.Thread(target=watch, name="file-fetch-deadline", daemon=True)
    thread.start()
    return stopped, thread


def _content_length(response: http.client.HTTPResponse, maximum: int) -> int | None:
    values = response.msg.get_all("Content-Length", []) if response.msg else []
    if not values:
        return None
    if len(values) != 1 or not values[0].strip().isdigit():
        raise FileFetchError("Invalid file response")
    size = int(values[0].strip())
    if size > maximum:
        raise FileFetchError("File exceeds size limit")
    return size


def _media_type(response: http.client.HTTPResponse) -> str:
    raw = response.getheader("Content-Type", "")
    value = raw.split(";", 1)[0].strip().lower()
    return value if _MEDIA_TYPE.fullmatch(value) else "application/octet-stream"


def _safe_name(value: str) -> str:
    value = unquote(value).replace("\\", "/").rsplit("/", 1)[-1]
    value = "".join(char for char in value if ord(char) >= 32 and ord(char) != 127).strip(" .")
    if not value or value in {".", ".."}:
        return "download"
    return value[:200]


def _filename(response: http.client.HTTPResponse, url: str) -> str:
    header = response.getheader("Content-Disposition", "")[:2048]
    match = _FILENAME_STAR.search(header)
    if match:
        value = match.group(1).strip().strip('"')
        try:
            charset, quote, remainder = value.partition("'")
            _, quote2, encoded = remainder.partition("'")
            if charset and quote and quote2:
                return _safe_name(unquote_to_bytes(encoded).decode(charset, "strict"))
        except (LookupError, UnicodeError, ValueError):
            pass
    match = _FILENAME.search(header)
    if match:
        value = match.group(1).strip()
        if value.startswith('"') and value.endswith('"'):
            value = re.sub(r"\\(.)", r"\1", value[1:-1])
        return _safe_name(value)
    return _safe_name(urlsplit(url).path.rsplit("/", 1)[-1])


def fetch_file(url: str, write: Callable[[bytes], Any], guard: Callable[[], None], deadline: Any, *,
               max_bytes: int, timeout: float = 10, max_redirects: int = 5,
               resolver: Callable | None = None, connection_factory: Callable | None = None) -> dict:
    """Stream public HTTPS bytes into a reserved partial file, with no ambient proxy state."""
    if not callable(write) or not callable(guard) or isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 0:
        raise FileFetchError("Invalid file fetch limits")
    try:
        timeout = float(timeout)
    except (TypeError, ValueError, OverflowError):
        raise FileFetchError("Invalid file fetch limits") from None
    if (isinstance(max_redirects, bool) or not isinstance(max_redirects, int)
            or not math.isfinite(timeout) or timeout <= 0
            or not 0 <= max_redirects <= _MAX_REDIRECTS):
        raise FileFetchError("Invalid file fetch limits")
    redirects = max_redirects

    current = url
    previous_scheme = None
    for _ in range(redirects + 1):
        _check(guard, deadline)
        if previous_scheme == "https" and urlsplit(current).scheme.lower() != "https":
            raise FileFetchError("Insecure file redirect")
        scheme, host, port, pinned_ip, target = _target(
            current, lambda host, port: _resolve_bounded(host, port, resolver, guard, deadline, timeout),
        )
        conn = None
        response = None
        watch_stop = watch_thread = None
        try:
            # The target is resolved and every DNS answer vetted before this connect.
            conn = _connection(scheme, host, port, pinned_ip, min(timeout, _check(guard, deadline)), connection_factory)
            _check(guard, deadline)
            watch_stop, watch_thread = _watch_transfer(conn, guard, deadline)
            conn.request("GET", target, headers={"Host": _host_header(host, port, scheme), "Accept-Encoding": "identity", "Connection": "close"})
            response = conn.getresponse()
            encoding = response.getheader("Content-Encoding", "").strip().lower()
            if encoding not in {"", "identity"}:
                raise FileFetchError("Unsupported file encoding")
            if 300 <= response.status < 400:
                location = response.getheader("Location")
                if not location:
                    raise FileFetchError("Invalid file redirect")
                if _ == redirects:
                    raise FileFetchError("Too many file redirects")
                previous_scheme = scheme
                current = urljoin(current, location)
                continue
            if not 200 <= response.status < 300:
                raise FileFetchError("File request failed")
            expected = _content_length(response, max_bytes)
            size = 0
            # The caller writes only to a reserved partial file; publication is separate.
            while True:
                _check(guard, deadline)
                if getattr(conn, "sock", None) is not None:
                    conn.sock.settimeout(min(timeout, _check(guard, deadline)))
                chunk = response.read1(_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise FileFetchError("File exceeds size limit")
                _check(guard, deadline)
                write(chunk)
            if expected is not None and size != expected:
                raise FileFetchError("Incomplete file response")
            return {"name": _filename(response, current), "media_type": _media_type(response), "size_bytes": size}
        except FileFetchError:
            raise
        except Exception:
            _check(guard, deadline)
            raise FileFetchError("File request failed") from None
        finally:
            if watch_stop is not None:
                watch_stop.set()
            if watch_thread is not None:
                watch_thread.join(timeout=0.1)
            try:
                if response is not None:
                    response.close()
            except Exception:
                pass
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass
    raise FileFetchError("Too many file redirects")
