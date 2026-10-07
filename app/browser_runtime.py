"""Task-scoped local Chromium runtime backed by an Xvfb display."""
from __future__ import annotations

import os
import re
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
from app.desktop_tools import DesktopTools, close_pyautogui_xlib, rebind_pyautogui
from app.task_context import TaskContext
from app.browser_profiles import BrowserProfileStore

_RUNTIME_LOCK = threading.Lock()


class BrowserRuntimeError(RuntimeError):
    pass


@dataclass
class LocalBrowserSession:
    driver: Any
    desktop: DesktopTools


def _executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _driver_slot() -> Path:
    from seleniumbase import drivers

    return Path(drivers.__file__).parent / "chromedriver"


def _provisioned_driver(settings: Settings) -> bool:
    try:
        slot = _driver_slot()
        return _executable(slot) and slot.samefile(settings.chromedriver_binary)
    except (ImportError, OSError):
        return False


def _local_driver_version(settings: Settings) -> str:
    """Fail before launching if build-time browser/driver provisioning drifted."""
    if not _provisioned_driver(settings):
        raise BrowserRuntimeError("SeleniumBase driver slot must resolve to CHROMEDRIVER_BINARY")
    versions = []
    for binary in (settings.chromium_binary, settings.chromedriver_binary):
        try:
            output = subprocess.check_output([str(binary), "--version"], text=True, timeout=10)
        except (OSError, subprocess.SubprocessError) as exc:
            raise BrowserRuntimeError("Could not verify local browser/driver version") from exc
        match = re.search(r"\b\d+\.\d+\.\d+\.\d+\b", output)
        if match is None:
            raise BrowserRuntimeError("Local browser/driver version is not an exact release")
        versions.append(match.group())
    if versions[0] != versions[1]:
        raise BrowserRuntimeError("Local browser and driver versions must match exactly")
    return versions[1]


def browser_ready(settings: Settings) -> bool:
    """Check Linux local-browser prerequisites without spawning anything."""
    return (
        sys.platform.startswith("linux")
        and _executable(settings.chromium_binary)
        and _executable(settings.chromedriver_binary)
        and _provisioned_driver(settings)
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


def _close_driver(driver) -> None:
    """Allow graceful profile flush first, then bound owned-process escalation."""
    failures = []

    def bounded(function, seconds):
        def run():
            try:
                function()
            except Exception as exc:
                failures.append(exc)
        thread = threading.Thread(target=run, name="browser-cleanup", daemon=True)
        thread.start()
        thread.join(seconds)
        return not thread.is_alive()

    service = getattr(driver, "service", None)
    graceful = bounded(driver.quit, 8)
    try:
        if not graceful or failures:
            # Only this WebDriver's Chrome PID and service are eligible for escalation.
            pid = getattr(driver, "capabilities", {}).get("goog:processID")
            if isinstance(pid, int) and pid > 1 and sys.platform.startswith("linux"):
                import signal
                try:
                    os.kill(pid, signal.SIGTERM)
                    end = time.monotonic() + 2
                    while time.monotonic() < end:
                        try:
                            os.kill(pid, 0)
                        except ProcessLookupError:
                            break
                        time.sleep(0.05)
                    else:
                        os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            _stop_window_manager(getattr(service, "process", None))
    finally:
        if service is not None and not bounded(service.stop, 5):
            _stop_window_manager(getattr(service, "process", None))
    if not graceful:
        raise BrowserRuntimeError("Graceful browser shutdown exceeded its time limit")
    if failures:
        raise failures[0]


@contextmanager
def browser_session(settings: Settings, context: TaskContext, deadline, *, owner=None, interactive=False) -> Iterator[LocalBrowserSession]:
    """Shared headed Chrome/Xvfb lifecycle for tasks and standalone manual use.

    Persistent profiles are leased and retained. No live WebDriver transfers
    between manual and task sessions; the task adapter remains separate.
    """
    if not sys.platform.startswith("linux"):
        raise BrowserRuntimeError("Local browser runtime is supported only on Linux")
    if not browser_ready(settings):
        raise BrowserRuntimeError("Local Chromium runtime prerequisites are unavailable")
    _wait_for_runtime(context, deadline)
    display = profile = driver = pyautogui = window_manager = None
    viewer = settings._display_viewer if settings.display_viewer_enabled else None
    viewer_generation = None
    profile_lease = None
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
                    _close_driver(driver)
                except Exception:
                    context.record_observation("cleanup", "failed", "Browser process cleanup could not be confirmed")

    try:
        from pyvirtualdisplay import Display  # pylint: disable=import-outside-toplevel
        from seleniumbase import Driver  # pylint: disable=import-outside-toplevel

        check = _guard(context, deadline)
        check()
        driver_version = _local_driver_version(settings)
        check()
        display = Display(visible=False, size=(settings.browser_window_width, settings.browser_window_height))
        display.start()
        # Import/rebind only after DISPLAY has been established for this task.
        pyautogui = rebind_pyautogui()
        window_manager = _start_window_manager(check)
        check()
        if context.browser_profile_id:
            profile_lease = BrowserProfileStore(settings.browser_profiles_root).lease(context.browser_profile_id)
            profile_path = str(profile_lease.__enter__())
        else:
            profile = tempfile.TemporaryDirectory(prefix="posting-chromium-")
            profile_path = profile.name
        check()
        driver = Driver(
            browser="chrome",
            headed=True,
            headless=False,
            headless1=False,
            headless2=False,
            undetectable=True,
            uc=True,
            uc_cdp_events=False,
            uc_subprocess=True,
            log_cdp_events=False,
            enable_ws=True,
            disable_ws=False,
            disable_csp=False,
            binary_location=str(settings.chromium_binary),
            driver_version=driver_version,
            user_data_dir=profile_path,
            chromium_arg="disable-dev-shm-usage,force-device-scale-factor=1",
            window_position="0,0",
            window_size=f"{settings.browser_window_width},{settings.browser_window_height}",
        )
        if not Path(driver.service.path).samefile(settings.chromedriver_binary):
            raise BrowserRuntimeError("SeleniumBase did not use the configured local driver")
        context.bind_browser(close_driver)
        check()
        # Start on a neutral page, not Chromium's internal new-tab UI.
        driver.set_page_load_timeout(settings.browser_timeout_seconds)
        driver.set_script_timeout(settings.browser_timeout_seconds)
        driver.get("about:blank")
        # Fill the configured desktop; the mapping adapter reads live window geometry.
        driver.set_window_position(0, 0)
        driver.set_window_size(settings.browser_window_width, settings.browser_window_height)
        driver.maximize_window()
        check()
        if context._artifact_session is not None:
            # Browser defaults must not write unrequested files into a shared directory.
            driver.execute_cdp_cmd("Browser.setDownloadBehavior", {"behavior": "deny"})
            if context.allow_file_downloads and settings.enable_write_actions and context.allow_write_actions is True:
                from app.browser_downloads import BrowserDownloads
                from app.selenium_tools import check_url
                artifact_session = context._artifact_session

                def transfer_guard():
                    check()
                    artifact_session.check()

                context._browser_downloads = BrowserDownloads(driver, artifact_session, transfer_guard, check_url)
                if not context._browser_downloads.available:
                    context.record_observation("download", "unavailable", "Native download events are unavailable; public HTTPS file downloads remain supported")
        display_name = os.environ["DISPLAY"]

        def change_mode(manual_owner):
            nonlocal viewer_generation
            if viewer is None:
                raise BrowserRuntimeError("Desktop viewer is unavailable")
            stop_viewer()  # Retire old sockets before enabling/revoking input.
            _release_desktop_input(display_name)
            viewer_generation = viewer.start_display(display_name, owner=manual_owner, interactive=manual_owner is not None)
            if viewer_generation is None:
                raise BrowserRuntimeError("Desktop input transition failed")
            return viewer_generation

        def fresh_observation():
            from app.browser_dom import DISCOVER_PAGE
            page = driver.execute_script(DISCOVER_PAGE)
            selectors = [item.get("selector", "") for item in page if isinstance(item, dict)]
            context.record_observation("resume", "returned", "Fresh live control selectors: " + str(selectors))

        if viewer is not None:
            try:
                if interactive:
                    viewer_generation = viewer.start_display(display_name, owner=owner, interactive=True)
                    if viewer_generation is None:
                        raise BrowserRuntimeError("Manual desktop viewer could not start")
                else:
                    viewer_generation = viewer.start_display(display_name)
            except Exception:
                if interactive:
                    raise
                context.record_observation("viewer", "unavailable", "Live viewer could not start; browser task continues")
        elif interactive:
            raise BrowserRuntimeError("Manual desktop viewer is disabled")
        check()
        context.control.transition = change_mode
        context.control.observe = fresh_observation
        yield LocalBrowserSession(driver=driver, desktop=DesktopTools(driver, pyautogui, check))
    finally:
        with context.control.condition:
            context.control.transition = None
            context.control.observe = None
            if not interactive and context.control.state != "agent":
                context.control.state = "error"
                context.cancelled.set()
            context.control.condition.notify_all()
        stop_viewer()
        downloads, context._browser_downloads = context._browser_downloads, None
        if downloads is not None:
            try:
                downloads.finalize()  # Import only confirmed completions while Chrome is alive.
            except Exception:
                context.record_observation("download", "unverified", "Final download collection could not be confirmed")
            finally:
                try:
                    downloads.close()
                except Exception:
                    context.record_observation("download", "unverified", "Download cleanup could not be confirmed")
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
                    for temporary in (profile,):
                        if temporary is not None:
                            try:
                                temporary.cleanup()
                            except Exception:
                                context.record_observation("cleanup", "failed", "Temporary browser files cleanup failed")
                finally:
                    try:
                        if profile_lease is not None:
                            profile_lease.__exit__(None, None, None)
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


def _release_desktop_input(display_name):
    """Release held X11 keys/buttons after retiring an interactive generation."""
    from Xlib import X, display as xdisplay
    from Xlib.ext import xtest

    connection = xdisplay.Display(display_name)
    try:
        keymap = connection.query_keymap()
        for keycode in range(8, 256):
            if keymap[keycode // 8] & (1 << (keycode % 8)):
                xtest.fake_input(connection, X.KeyRelease, keycode)
        for button in range(1, 6):
            xtest.fake_input(connection, X.ButtonRelease, button)
        connection.sync()
    finally:
        connection.close()


@contextmanager
def local_browser(settings: Settings, context: TaskContext, deadline):
    """Task adapter; standalone browsing calls the shared lifecycle directly."""
    with browser_session(settings, context, deadline) as session:
        yield session
