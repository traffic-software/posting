import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import browser_runtime
from app.config import Settings
from app.task_context import TaskContext


@pytest.mark.parametrize("failure", ["startup", "cancel", "configure"])
def test_browser_failure_cleans_files_display_service_and_releases_lock(monkeypatch, tmp_path, failure):
    import pyvirtualdisplay
    from selenium import webdriver
    from selenium.webdriver.chrome import service as chrome_service

    directories, displays, options_seen, closed, services = [], [], [], [], []
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
        options = kwargs["options"]
        assert all(options is not previous for previous in options_seen)
        options_seen.append(options)
        assert kwargs["service"].path == str(source)
        if failure == "startup":
            raise RuntimeError("synthetic session startup failure")
        driver = SimpleNamespace(
            service=kwargs["service"],
            quit=lambda: closed.append(True),
            set_page_load_timeout=lambda _: (_ for _ in ()).throw(RuntimeError("configuration failure")),
        )
        if failure == "cancel":
            context.cancel()
        return driver

    source = tmp_path / "chromedriver"
    source.write_bytes(b"synthetic executable")
    monkeypatch.setenv("DISPLAY", ":original")
    monkeypatch.setattr(browser_runtime.sys, "platform", "linux")
    monkeypatch.setattr(browser_runtime, "browser_ready", lambda _: True)
    monkeypatch.setattr(browser_runtime, "rebind_pyautogui", lambda: None)
    monkeypatch.setattr(browser_runtime, "_start_window_manager", lambda _: None)
    monkeypatch.setattr(browser_runtime.tempfile, "TemporaryDirectory", temporary)
    monkeypatch.setattr(pyvirtualdisplay, "Display", Display)
    monkeypatch.setattr(chrome_service, "Service", Service)
    monkeypatch.setattr(webdriver, "Chrome", create)
    settings = Settings(_env_file=None, chromedriver_binary=source)
    for _ in range(2):
        context = TaskContext()
        with pytest.raises(RuntimeError):
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
