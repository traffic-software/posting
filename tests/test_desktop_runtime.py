import os
import time
from types import SimpleNamespace

import pytest

from app.browser_runtime import BrowserRuntimeError, browser_ready, local_browser
from app.config import Settings
from app.desktop_tools import DesktopInputError, DesktopTools
from app.task_context import TaskContext


class FakePyAutoGUI:
    FAILSAFE = False

    def __init__(self):
        self.calls = []

    def moveTo(self, x, y):
        self.calls.append(("move", x, y))

    def click(self):
        self.calls.append(("click",))

    def scroll(self, amount):
        self.calls.append(("scroll", amount))

    def press(self, key):
        self.calls.append(("press", key))

    def write(self, value):
        self.calls.append(("write", value))


class FakeDriver:
    geometry = {
        "x": 40, "y": 50, "screenX": 0, "screenY": 0,
        "outerWidth": 1024, "outerHeight": 768, "innerWidth": 1000,
        "innerHeight": 700, "screenWidth": 1024, "screenHeight": 768, "dpr": 1,
    }

    def __init__(self):
        self.scripts = []

    def execute_cdp_cmd(self, command, arguments):
        assert command == "Page.bringToFront" and arguments == {}
        return {}

    def execute_script(self, script, _element):
        self.scripts.append(script)
        if "return document.activeElement" in script:
            return True
        return self.geometry


class FakeElement:
    def __init__(self):
        self.sent = []

    def send_keys(self, value):
        self.sent.append(value)


def test_desktop_actions_use_verified_element_mapping_and_guard():
    gui, driver, element = FakePyAutoGUI(), FakeDriver(), FakeElement()
    checks = []
    desktop = DesktopTools(driver, gui, lambda: checks.append("checked"))
    desktop.click(element)
    desktop.hover(element)
    desktop.scroll(element, -2)
    desktop.press_key(element, "enter")
    desktop.type_text(element, "plain text")
    desktop.type_text(element, "café")
    assert gui.FAILSAFE is True
    assert ("click",) in gui.calls
    assert ("scroll", -2) in gui.calls
    assert ("press", "enter") in gui.calls
    assert ("write", "plain text") in gui.calls
    assert element.sent == ["café"]
    assert len(checks) >= 10


@pytest.mark.parametrize("action", [
    lambda adapter, target: adapter.press_key(target, "ctrl"),
    lambda adapter, target: adapter.scroll(target, 0),
    lambda adapter, target: adapter.type_text(target, "bad\ntext"),
])
def test_desktop_rejects_unapproved_input(action):
    with pytest.raises(DesktopInputError):
        action(DesktopTools(FakeDriver(), FakePyAutoGUI()), FakeElement())


def test_desktop_fails_closed_for_obscured_target():
    driver = FakeDriver()
    driver.geometry = None
    with pytest.raises(DesktopInputError):
        DesktopTools(driver, FakePyAutoGUI()).click(FakeElement())


def test_generic_type_rejects_secret_field():
    class PasswordDriver(FakeDriver):
        def execute_script(self, script, element):
            if "current-password" in script:
                return False
            return super().execute_script(script, element)

    with pytest.raises(DesktopInputError):
        DesktopTools(PasswordDriver(), FakePyAutoGUI()).type_text(FakeElement(), "safe")


def test_browser_ready_does_not_spawn(monkeypatch, tmp_path):
    browser, driver = (tmp_path / name for name in ("chromium", "chromedriver"))
    browser.write_text("")
    driver.write_text("")
    browser.chmod(0o700)
    driver.chmod(0o700)
    settings = Settings(_env_file=None, chromium_binary=browser, chromedriver_binary=driver)
    monkeypatch.setattr("app.browser_runtime.sys.platform", "linux")
    monkeypatch.setattr("app.browser_runtime.shutil.which", lambda name: "/usr/bin/Xvfb")
    assert browser_ready(settings) is True


def test_local_browser_never_falls_back_to_host_platform(monkeypatch):
    settings = Settings(_env_file=None)
    monkeypatch.setattr("app.browser_runtime.sys.platform", "win32")
    with pytest.raises(BrowserRuntimeError, match="Linux"):
        with local_browser(settings, TaskContext(), time.monotonic() + 1):
            pass


def test_local_browser_wait_is_cancellable(monkeypatch):
    context = TaskContext()
    context.cancel()
    monkeypatch.setattr("app.browser_runtime.sys.platform", "linux")
    monkeypatch.setattr("app.browser_runtime.browser_ready", lambda _settings: True)
    with pytest.raises(BrowserRuntimeError, match="cancelled"):
        with local_browser(Settings(_env_file=None), context, time.monotonic() + 1):
            pass


@pytest.mark.parametrize("viewer_fails", [False, True])
def test_local_browser_uses_mocked_xvfb_and_cleans_task_driver(monkeypatch, viewer_fails):
    import pyvirtualdisplay
    import selenium.webdriver

    displays = []
    viewer_events = []

    class FakeDisplay:
        def __init__(self, **_kwargs):
            self.stopped = False
            displays.append(self)

        def start(self):
            os.environ["DISPLAY"] = ":99"

        def stop(self):
            self.stopped = True

    class Browser(FakeDriver):
        def __init__(self):
            super().__init__()
            self.quit_calls = 0

        def set_page_load_timeout(self, timeout):
            assert timeout > 0

        def get(self, url):
            assert url == "about:blank"

        def set_window_position(self, *_args):
            pass

        def set_window_size(self, *_args):
            pass

        def quit(self):
            viewer_events.append("browser-closed")
            self.quit_calls += 1

    class Viewer:
        def start_display(self, display_name):
            assert display_name == ":99"
            viewer_events.append("viewer-started")
            if viewer_fails:
                raise RuntimeError("synthetic viewer startup failure")
            return "synthetic-generation"

        def stop_display(self, generation):
            assert generation == "synthetic-generation"
            viewer_events.append("viewer-stopped")

    browser = Browser()
    monkeypatch.setattr("app.browser_runtime.sys.platform", "linux")
    monkeypatch.setattr("app.browser_runtime.browser_ready", lambda _settings: True)
    monkeypatch.setattr("app.browser_runtime.rebind_pyautogui", lambda: FakePyAutoGUI())
    monkeypatch.setattr("app.browser_runtime._start_window_manager", lambda check: None)
    monkeypatch.setattr(pyvirtualdisplay, "Display", FakeDisplay)
    monkeypatch.setattr(selenium.webdriver, "Chrome", lambda **_kwargs: browser)
    context = TaskContext()
    settings = Settings(_env_file=None, display_viewer_enabled=True)
    settings._display_viewer = Viewer()
    with local_browser(settings, context, time.monotonic() + 5) as session:
        assert session.driver is browser
        assert session.desktop._pyautogui.FAILSAFE is True
    assert browser.quit_calls == 1
    assert displays[0].stopped is True
    assert "DISPLAY" not in os.environ
    assert "viewer-started" in viewer_events
    if not viewer_fails:
        assert viewer_events.index("viewer-stopped") < viewer_events.index("browser-closed")
    else:
        assert "viewer-stopped" not in viewer_events


@pytest.mark.parametrize("needs_kill", [False, True])
def test_window_manager_cleanup_waits_for_owned_process(needs_kill):
    import subprocess
    from app.browser_runtime import _stop_window_manager

    class Process:
        def __init__(self):
            self.calls = []

        def poll(self):
            return None

        def terminate(self):
            self.calls.append("terminate")

        def wait(self, timeout):
            self.calls.append("wait")
            if needs_kill and "kill" not in self.calls:
                raise subprocess.TimeoutExpired("openbox", timeout)

        def kill(self):
            self.calls.append("kill")

    process = Process()
    _stop_window_manager(process)
    assert process.calls == (["terminate", "wait", "kill", "wait"] if needs_kill else ["terminate", "wait"])
