from pathlib import Path
from types import SimpleNamespace

import pytest

from app.browser_downloads import BrowserDownloads


class Reservation:
    def __init__(self, maximum=20):
        self.id, self.max_bytes, self.aborted = "r1", maximum, False

    def abort(self):
        self.aborted = True


class Artifacts:
    def __init__(self, directory, maximum=20):
        self.browser_directory = Path(directory)
        self.maximum, self.reservations, self.imports = maximum, [], []

    def reserve(self, **kwargs):
        reservation = Reservation(self.maximum)
        self.reservations.append((kwargs, reservation))
        return reservation

    def import_browser_file(self, path, name, reservation):
        self.imports.append((Path(path), name, reservation))
        return {"id": "artifact-1", "name": name}


class Browser:
    class DownloadWillBegin:
        event_class = "Browser.downloadWillBegin"

    class DownloadProgress:
        event_class = "Browser.downloadProgress"

    @staticmethod
    def set_download_behavior(behavior, **kwargs):
        yield {"method": "Browser.setDownloadBehavior", "params": {"behavior": behavior, **kwargs}}

    @staticmethod
    def cancel_download(guid):
        yield {"method": "Browser.cancelDownload", "params": {"guid": guid}}


class Connection:
    def __init__(self):
        self.session_id = "page-session"
        self.callbacks, self.commands, self.removed = {}, [], []

    def add_callback(self, event, callback):
        self.callbacks[event.event_class] = callback
        return event.event_class

    def remove_callback(self, event, callback_id):
        self.removed.append((event.event_class, callback_id))
        self.callbacks.pop(event.event_class, None)

    def execute(self, command):
        data = next(command)
        self.commands.append((self.session_id, data))
        return None

    def emit(self, event, **kwargs):
        self.callbacks[event.event_class](SimpleNamespace(**kwargs))


class Driver:
    def __init__(self, connection=None, failure=None):
        self.connection, self.failure = connection or Connection(), failure

    def start_devtools(self):
        if self.failure:
            raise self.failure
        return SimpleNamespace(browser=Browser), self.connection


def collector(tmp_path, maximum=20, guard=lambda: None, validate=lambda url: None):
    artifacts, driver = Artifacts(tmp_path, maximum), Driver()
    return BrowserDownloads(driver, artifacts, guard, validate), artifacts, driver.connection


def begin(connection, guid="a-guid", url="https://files.example/report", name="report.pdf"):
    connection.emit(Browser.DownloadWillBegin, guid=guid, url=url, suggested_filename=name)


def progress(connection, guid="a-guid", received=1, total=1, state="inProgress"):
    connection.emit(Browser.DownloadProgress, guid=guid, received_bytes=received, total_bytes=total, state=state)


def test_one_armed_click_collects_cdp_completed_guid_file(tmp_path):
    checked = []
    downloads, artifacts, connection = collector(tmp_path, validate=checked.append)
    assert downloads.available
    assert connection.commands[0][1]["params"]["behavior"] == "deny"
    attempt = downloads.arm("https://origin.example")
    assert artifacts.reservations[0][0] == {"purpose": "output", "name": "download.bin", "media_type": "application/octet-stream"}
    assert connection.session_id == "page-session"
    assert all(session is None for session, _ in connection.commands)
    assert downloads.poll(attempt) == {"status": "pending"}
    begin(connection)
    (tmp_path / "a-guid").write_bytes(b"complete")
    progress(connection, received=8, total=8, state="completed")
    assert downloads.poll(attempt) == {"status": "ready", "artifact": {"id": "artifact-1", "name": "report.pdf"}}
    assert artifacts.imports[0][0] == tmp_path / "a-guid"
    assert checked == ["https://origin.example", "https://files.example/report"]


def test_parallel_arm_and_unexpected_second_download_are_denied(tmp_path):
    downloads, artifacts, connection = collector(tmp_path)
    attempt = downloads.arm("https://origin.example")
    with pytest.raises(RuntimeError, match="already armed"):
        downloads.arm("https://other.example")
    begin(connection, "first")
    assert connection.commands[-1][1]["params"]["behavior"] == "allowAndName"
    begin(connection, "second")
    assert downloads.poll(attempt) == {"status": "pending"}
    assert any(command[1]["method"] == "Browser.cancelDownload" and command[1]["params"]["guid"] == "second"
               for command in connection.commands)
    (tmp_path / "first").write_bytes(b"complete")
    progress(connection, guid="first", received=8, total=8, state="completed")
    assert downloads.poll(attempt)["status"] == "ready"
    assert [item[0] for item in artifacts.imports] == [tmp_path / "first"]


def test_partial_file_never_imports_without_completed_event(tmp_path):
    downloads, artifacts, connection = collector(tmp_path)
    attempt = downloads.arm("https://origin.example")
    begin(connection)
    (tmp_path / "a-guid").write_bytes(b"partial")
    progress(connection, received=7, total=10)
    assert downloads.poll(attempt) == {"status": "pending", "received_bytes": 7}
    assert not artifacts.imports
    downloads.cancel(attempt)
    assert artifacts.reservations[0][1].aborted


def test_quota_and_invalid_sources_cancel_without_import(tmp_path):
    downloads, artifacts, connection = collector(tmp_path, maximum=3)
    attempt = downloads.arm("https://origin.example")
    begin(connection, url="file:///secret")
    assert any(item[1]["params"].get("guid") == "a-guid" for item in connection.commands)
    assert downloads.poll(attempt)["status"] == "failed"
    attempt = downloads.arm("https://origin.example")
    begin(connection, guid="valid")
    progress(connection, guid="valid", received=4, total=4)
    assert downloads.poll(attempt)["status"] == "failed"
    assert artifacts.reservations[0][1].aborted
    assert not artifacts.imports


def test_blob_requires_armed_https_origin(tmp_path):
    downloads, _, connection = collector(tmp_path)
    attempt = downloads.arm("https://origin.example")
    begin(connection, url="blob:https://other.example/abc")
    assert downloads.poll(attempt)["status"] == "failed"
    attempt = downloads.arm("https://origin.example")
    begin(connection, guid="good", url="blob:https://origin.example/abc")
    (tmp_path / "good").write_bytes(b"ok")
    progress(connection, guid="good", received=2, total=2, state="completed")
    assert downloads.poll(attempt)["status"] == "ready"


def test_missing_event_transport_is_explicitly_unavailable(tmp_path):
    downloads = BrowserDownloads(Driver(failure=RuntimeError("private detail")), Artifacts(tmp_path), lambda: None, lambda _: None)
    assert not downloads.available
    assert downloads.disabled_reason == "Browser download transport is unavailable"
    with pytest.raises(RuntimeError, match="unavailable"):
        downloads.arm("https://origin.example")


def test_finalize_imports_completed_before_close_and_preserves_ready(tmp_path):
    downloads, artifacts, connection = collector(tmp_path)
    attempt = downloads.arm("https://origin.example")
    begin(connection)
    (tmp_path / "a-guid").write_bytes(b"done")
    progress(connection, received=4, total=4, state="completed")
    assert downloads.finalize()[attempt]["status"] == "ready"
    downloads.close()
    assert downloads.poll(attempt)["status"] == "ready"
    assert len(connection.removed) == 2
