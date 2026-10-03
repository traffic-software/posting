"""Task-scoped local Chromium runtime backed by an Xvfb display."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import Settings
from app.network_idle import NetworkIdleTracker, NetworkIdleError
from app.desktop_tools import DesktopTools, close_pyautogui_xlib, rebind_pyautogui
from app.task_context import TaskContext

_RUNTIME_LOCK = threading.Lock()


class BrowserRuntimeError(RuntimeError):
    pass


@dataclass
class LocalBrowserSession:
    driver: Any
    desktop: DesktopTools
    network_idle: NetworkIdleTracker


def _executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def browser_ready(settings: Settings) -> bool:
    """Check Linux local-browser prerequisites without spawning anything."""
    return (
        sys.platform.startswith("linux")
        and _executable(settings.chromium_binary)
        and _executable(settings.chromedriver_binary)
        and shutil.which("Xvfb") is not None
        and shutil.which("openbox") is not None
    )


def _wait_for_runtime(context: TaskContext, deadline: float) -> None:
    """Acquire the single display/browser slot while honoring task cancellation."""
    while True:
        if context.cancelled.is_set():
            raise BrowserRuntimeError("Task cancelled before browser was available")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BrowserRuntimeError("Task time limit reached while waiting for local browser")
        if _RUNTIME_LOCK.acquire(timeout=min(0.1, remaining)):
            return


def _guard(context: TaskContext, deadline: float) -> Callable[[], None]:
    def check() -> None:
        if context.cancelled.is_set():
            raise BrowserRuntimeError("Task cancelled")
        if time.monotonic() >= deadline:
            raise BrowserRuntimeError("Task time limit reached")
    return check


def _start_window_manager(check):
    from Xlib import X, display as xdisplay

    process = subprocess.Popen(["openbox", "--sm-disable"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    connection = None
    try:
        connection = xdisplay.Display(os.environ["DISPLAY"])
        atom = connection.intern_atom("_NET_SUPPORTING_WM_CHECK")
        limit = time.monotonic() + 5
        while True:
            check()
            if process.poll() is not None:
                raise BrowserRuntimeError("Window manager exited before the desktop was ready")
            if connection.screen().root.get_full_property(atom, X.AnyPropertyType) is not None:
                return process
            if time.monotonic() >= limit:
                raise BrowserRuntimeError("Window manager did not become ready")
            time.sleep(0.05)
    except BaseException:
        _stop_window_manager(process)
        raise
    finally:
        if connection is not None:
            connection.close()


def _stop_window_manager(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


@contextmanager
def local_browser(settings: Settings, context: TaskContext, deadline: float) -> Iterator[LocalBrowserSession]:
    """Start one task-local standard Chromium instance under an exclusive Xvfb.

    The browser is only supported in the Linux container.  It has a temporary
    profile and never attempts to access a host display or remote WebDriver.
    """
    if not sys.platform.startswith("linux"):
        raise BrowserRuntimeError("Local browser runtime is supported only on Linux")
    if not browser_ready(settings):
        raise BrowserRuntimeError("Local Chromium runtime prerequisites are unavailable")
    _wait_for_runtime(context, deadline)
    display = profile = driver = pyautogui = window_manager = None
    viewer = settings._display_viewer if settings.display_viewer_enabled else None
    viewer_generation = None
    prior_display = os.environ.get("DISPLAY")
    closed = False
    close_lock = threading.Lock()

    def stop_viewer() -> None:
        if viewer is not None and viewer_generation is not None:
            try:
                viewer.stop_display(viewer_generation)
            except Exception:
                context.record_observation("cleanup", "failed", "Live viewer cleanup could not be confirmed")

    def close_driver() -> None:
        nonlocal closed
        with close_lock:
            if closed:
                return
            closed = True
        stop_viewer()
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

    try:
        from pyvirtualdisplay import Display  # pylint: disable=import-outside-toplevel
        from selenium import webdriver  # pylint: disable=import-outside-toplevel
        from selenium.webdriver.chrome.options import Options  # pylint: disable=import-outside-toplevel
        from selenium.webdriver.chrome.service import Service  # pylint: disable=import-outside-toplevel

        check = _guard(context, deadline)
        check()
        display = Display(visible=False, size=(settings.browser_window_width, settings.browser_window_height))
        display.start()
        # Import/rebind only after DISPLAY has been established for this task.
        pyautogui = rebind_pyautogui()
        window_manager = _start_window_manager(check)
        check()
        profile = tempfile.TemporaryDirectory(prefix="posting-chromium-")
        options = Options()
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        options.binary_location = str(settings.chromium_binary)
        options.add_argument(f"--user-data-dir={profile.name}")
        options.add_argument(f"--window-size={settings.browser_window_width},{settings.browser_window_height}")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--force-device-scale-factor=1")
        driver = webdriver.Chrome(
            service=Service(executable_path=str(settings.chromedriver_binary)),
            options=options,
        )
        context.bind_browser(close_driver)
        check()
        try:
            network_idle = NetworkIdleTracker(driver, settings.network_idle_quiet_ms / 1000, settings.network_idle_max_wait_seconds)
        except NetworkIdleError:
            raise BrowserRuntimeError("Network readiness instrumentation unavailable") from None
        # Start on a neutral page, not Chromium's internal new-tab UI.
        driver.set_page_load_timeout(settings.browser_timeout_seconds)
        driver.get("about:blank")
        # The mapping adapter relies on this explicit fixed window geometry.
        driver.set_window_position(0, 0)
        driver.set_window_size(settings.browser_window_width, settings.browser_window_height)
        check()
        if viewer is not None:
            try:
                viewer_generation = viewer.start_display(os.environ["DISPLAY"])
            except Exception:
                context.record_observation("viewer", "unavailable", "Live viewer could not start; browser task continues")
        check()
        yield LocalBrowserSession(driver=driver, desktop=DesktopTools(driver, pyautogui, check), network_idle=network_idle)
    finally:
        stop_viewer()
        # Every layer has its own finally so a failed profile/context cleanup
        # cannot leave Xvfb or the exclusive lock behind.
        try:
            try:
                try:
                    context.close_browser()
                except Exception:
                    context.record_observation("cleanup", "failed", "Local browser cleanup could not be confirmed")
            finally:
                close_driver()
        finally:
            try:
                if pyautogui is not None:
                    close_pyautogui_xlib(pyautogui)
            finally:
                try:
                    if profile is not None:
                        try:
                            profile.cleanup()
                        except Exception:
                            context.record_observation("cleanup", "failed", "Temporary browser profile cleanup failed")
                finally:
                    try:
                        try:
                            _stop_window_manager(window_manager)
                        except Exception:
                            context.record_observation("cleanup", "failed", "Window manager cleanup failed")
                        if display is not None:
                            try:
                                display.stop()
                            except Exception:
                                context.record_observation("cleanup", "failed", "Virtual display cleanup failed")
                    finally:
                        if prior_display is None:
                            os.environ.pop("DISPLAY", None)
                        else:
                            os.environ["DISPLAY"] = prior_display
                        _RUNTIME_LOCK.release()
