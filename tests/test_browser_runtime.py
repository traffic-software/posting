import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import browser_runtime
from app.config import Settings
from app.task_context import TaskContext


@pytest.mark.parametrize("failure", ["startup", "cancel", "configure", "wrong-service"])
def test_browser_failure_cleans_files_display_service_and_releases_lock(monkeypatch, tmp_path, failure):
    import pyvirtualdisplay
    import seleniumbase

    directories, displays, profiles_seen, closed, services = [], [], [], [], []
    original_temporary = browser_runtime.tempfile.TemporaryDirectory

    def temporary(**kwargs):
        directory = original_temporary(**kwargs)
        directories.append(Path(directory.name))
        return directory

    class Display:
        def __init__(self, **kwargs):
            self.stopped = False
            displays.append(self)

        def start(self):
            os.environ["DISPLAY"] = ":99"

        def stop(self):
            self.stopped = True

    class Service:
        def __init__(self, executable_path):
            self.path = executable_path
            self.stopped = False
            services.append(self)

        def stop(self):
            self.stopped = True

    def create(**kwargs):
        assert kwargs["user_data_dir"] not in profiles_seen
        profiles_seen.append(kwargs["user_data_dir"])
        assert Path(kwargs["user_data_dir"]) == directories[-1]
        assert kwargs["binary_location"] == str(settings.chromium_binary)
        assert "service" not in kwargs
        if failure == "startup":
            raise RuntimeError("synthetic session startup failure")
        driver = SimpleNamespace(
            service=Service(str(source if failure != "wrong-service" else other_source)),
            quit=lambda: closed.append(True),
            set_page_load_timeout=lambda _: (_ for _ in ()).throw(RuntimeError("configuration failure")),
        )
        if failure == "cancel":
            context.cancel()
        return driver

    source = tmp_path / "chromedriver"
    source.write_bytes(b"synthetic executable")
    other_source = tmp_path / "unexpected-chromedriver"
    other_source.write_bytes(b"unexpected executable")
    monkeypatch.setenv("DISPLAY", ":original")
    monkeypatch.setattr(browser_runtime.sys, "platform", "linux")
    monkeypatch.setattr(browser_runtime, "browser_ready", lambda _: True)
    monkeypatch.setattr(browser_runtime, "rebind_pyautogui", lambda: None)
    monkeypatch.setattr(browser_runtime, "_start_window_manager", lambda _: None)
    monkeypatch.setattr(browser_runtime.tempfile, "TemporaryDirectory", temporary)
    monkeypatch.setattr(pyvirtualdisplay, "Display", Display)
    monkeypatch.setattr(browser_runtime, "_local_driver_version", lambda _: "123.0.1.2")
    monkeypatch.setattr(seleniumbase, "Driver", create)
    settings = Settings(_env_file=None, chromedriver_binary=source)
    for _ in range(2):
        context = TaskContext()
        message = "driver" if failure == "wrong-service" else None
        with pytest.raises(RuntimeError, match=message):
            with browser_runtime.local_browser(settings, context, time.monotonic() + 5):
                pytest.fail("Failed startup must not yield a session")
        assert not browser_runtime._RUNTIME_LOCK.locked()
        assert os.environ["DISPLAY"] == ":original"
        assert all(display.stopped for display in displays)
        assert all(service.stopped for service in services)
        assert all(not directory.exists() for directory in directories)
    assert len(closed) == (0 if failure == "startup" else 2)


@pytest.mark.parametrize("quit_fails", [False, True])
def test_browser_close_stops_owned_service_even_if_quit_fails(quit_fails):
    events = []

    def quit():
        events.append("quit")
        if quit_fails:
            raise RuntimeError("synthetic quit failure")

    driver = SimpleNamespace(
        service=SimpleNamespace(stop=lambda: events.append("service-stop")),
        quit=quit,
    )
    if quit_fails:
        with pytest.raises(RuntimeError):
            browser_runtime._close_driver(driver)
    else:
        browser_runtime._close_driver(driver)
    assert events == ["quit", "service-stop"]


@pytest.fixture
def provisioned_settings(monkeypatch, tmp_path):
    browser, driver = (tmp_path / name for name in ("chromium", "chromedriver"))
    for binary in (browser, driver):
        binary.write_bytes(b"synthetic executable")
        binary.chmod(0o700)
    monkeypatch.setattr(browser_runtime, "_driver_slot", lambda: driver)
    return Settings(_env_file=None, chromium_binary=browser, chromedriver_binary=driver)


def test_local_driver_version_requires_exact_release_match(monkeypatch, provisioned_settings):
    calls = []

    def version(command, **kwargs):
        calls.append((command, kwargs))
        return "Chromium 123.0.1.2\n" if len(calls) == 1 else "ChromeDriver 123.0.1.2 (build)\n"

    monkeypatch.setattr(browser_runtime.subprocess, "check_output", version)
    assert browser_runtime._local_driver_version(provisioned_settings) == "123.0.1.2"
    assert calls == [
        ([str(binary), "--version"], {"text": True, "timeout": 10})
        for binary in (provisioned_settings.chromium_binary, provisioned_settings.chromedriver_binary)
    ]


@pytest.mark.parametrize("outputs, message", [
    (["Chromium 123.0.1.2", "ChromeDriver 123.0.1.3"], "match exactly"),
    (["Chromium 123.0", "ChromeDriver 123.0.1.2"], "exact release"),
    (["Chromium 123.0.1.2", "unknown"], "exact release"),
])
def test_local_driver_version_rejects_invalid_or_mismatched_versions(monkeypatch, provisioned_settings, outputs, message):
    versions = iter(outputs)
    monkeypatch.setattr(browser_runtime.subprocess, "check_output", lambda *a, **kw: next(versions))
    with pytest.raises(browser_runtime.BrowserRuntimeError, match=message):
        browser_runtime._local_driver_version(provisioned_settings)


@pytest.mark.parametrize("error", [
    OSError("cannot execute"),
    browser_runtime.subprocess.CalledProcessError(1, "chromium"),
    browser_runtime.subprocess.TimeoutExpired("chromium", 10),
])
def test_local_driver_version_rejects_command_failure(monkeypatch, provisioned_settings, error):
    def failed_version(*args, **kwargs):
        raise error

    monkeypatch.setattr(browser_runtime.subprocess, "check_output", failed_version)
    with pytest.raises(browser_runtime.BrowserRuntimeError, match="Could not verify"):
        browser_runtime._local_driver_version(provisioned_settings)


@pytest.mark.parametrize("slot_kind", ["missing", "different"])
def test_local_driver_version_rejects_unprovisioned_slot(monkeypatch, provisioned_settings, tmp_path, slot_kind):
    slot = tmp_path / "seleniumbase-chromedriver"
    if slot_kind == "different":
        slot.write_bytes(b"another driver")
        slot.chmod(0o700)
    monkeypatch.setattr(browser_runtime, "_driver_slot", lambda: slot)
    monkeypatch.setattr(browser_runtime.subprocess, "check_output", lambda *a, **kw: pytest.fail("Invalid slot must not spawn"))
    assert not browser_runtime._provisioned_driver(provisioned_settings)
    with pytest.raises(browser_runtime.BrowserRuntimeError, match="driver slot"):
        browser_runtime._local_driver_version(provisioned_settings)


def test_version_preflight_failure_never_starts_display_and_releases_lock(monkeypatch, provisioned_settings):
    import pyvirtualdisplay

    monkeypatch.setattr(browser_runtime.sys, "platform", "linux")
    monkeypatch.setattr(browser_runtime, "browser_ready", lambda _: True)
    monkeypatch.setattr(browser_runtime.subprocess, "check_output", lambda *a, **kw: "invalid version")
    monkeypatch.setattr(pyvirtualdisplay, "Display", lambda **kw: pytest.fail("Version gate must precede Xvfb"))
    with pytest.raises(browser_runtime.BrowserRuntimeError, match="exact release"):
        with browser_runtime.local_browser(provisioned_settings, TaskContext(), time.monotonic() + 5):
            pytest.fail("Invalid version must not yield")
    assert not browser_runtime._RUNTIME_LOCK.locked()
