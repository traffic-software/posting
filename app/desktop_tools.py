"""Restricted desktop input for the local Chromium task window."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

from app.browser_dom import EDITING_HOST_JS


class DesktopInputError(RuntimeError):
    pass


_ALLOWED_KEYS = frozenset({"backspace", "delete", "down", "end", "enter", "esc", "escape", "home", "left", "pagedown", "pageup", "right", "space", "tab", "up"})
_POINTER_TARGET = """
const el = arguments[0];
if (!el || !el.isConnected || !document.hasFocus()) return null;
const r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
if (!Number.isFinite(x) || !Number.isFinite(y) || r.width <= 0 || r.height <= 0 || x < 0 || y < 0 || x >= innerWidth || y >= innerHeight) return null;
const hit = document.elementFromPoint(x, y);
if (!(hit === el || el.contains(hit))) return null;
return {x, y, screenX, screenY, outerWidth, outerHeight, innerWidth, innerHeight,
        screenWidth: screen.width, screenHeight: screen.height, dpr: devicePixelRatio};
"""
_FOCUS_TARGET = """
const el = arguments[0];
if (!el || !el.isConnected || !document.hasFocus()) return false;
try { el.focus({preventScroll: true}); } catch (_) { return false; }
return document.activeElement === el || el.contains(document.activeElement);
"""
_SAFE_INPUT_FOCUS_TARGET = """
const el = arguments[0];
if (!el || !el.isConnected || !document.hasFocus()) return false;
const type = (el.getAttribute('type') || '').toLowerCase();
const autocomplete = (el.getAttribute('autocomplete') || '').toLowerCase();
if (type === 'password' || type === 'file' || el.disabled || el.readOnly ||
    autocomplete === 'current-password' || autocomplete === 'new-password' ||
    autocomplete === 'one-time-code') return false;
try { el.focus({preventScroll: true}); } catch (_) { return false; }
return document.activeElement === el || el.contains(document.activeElement);
"""

_TEXT_INPUT_FOCUS_TARGET = EDITING_HOST_JS + """
const el = arguments[0];
if (!el || !el.isConnected || !document.hasFocus()) return false;
const native = el.matches('textarea,input[type="text"],input:not([type]),input[type="search"],input[type="email"],input[type="url"],input[type="tel"],input[type="number"]');
if ((!native && !editingHost(el)) || el.disabled || el.readOnly || el.getAttribute('aria-readonly') === 'true') return false;
const privateTarget = '[data-private],[data-sensitive],[autocomplete="current-password"],[autocomplete="new-password"],[autocomplete="one-time-code"],input[type="password"],input[type="file"],input[type="hidden"]';
if (el.closest(privateTarget) || el.querySelector(privateTarget)) return false;
if (arguments[1] !== false) {
 try { el.focus({preventScroll: true}); } catch (_) { return false; }
}
return document.activeElement === el;
"""
_DRAG_TARGETS = """
const targets = Array.from(arguments);
if (!document.hasFocus()) return null;
const unsafe = 'input,textarea,select,[contenteditable],iframe,frame,[data-private],[data-sensitive],[autocomplete="one-time-code"]';
const points = [];
for (const el of targets) {
 if (!el || !el.isConnected || el.closest(unsafe) || el.querySelector(unsafe) || el.matches(':disabled') || el.getAttribute('aria-disabled') === 'true') return null;
 const r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
 const style = getComputedStyle(el), hit = document.elementFromPoint(x, y);
 if (r.width <= 0 || r.height <= 0 || style.visibility !== 'visible' || style.display === 'none' || !(hit === el || el.contains(hit))) return null;
 points.push({x,y,screenX,screenY,outerWidth,outerHeight,innerWidth,innerHeight,screenWidth:screen.width,screenHeight:screen.height,dpr:devicePixelRatio});
}
return {points, url: location.href, scrollX, scrollY};
"""


@dataclass(frozen=True)
class _ScreenPoint:
    x: int
    y: int


def close_pyautogui_xlib(pyautogui: Any) -> None:
    """Close this task's cached Xlib Display before its Xvfb disappears."""
    backend = getattr(pyautogui, "_pyautogui_x11", None)
    display = getattr(backend, "_display", None)
    if display is not None:
        try:
            display.close()
        except Exception:
            pass
        try:
            backend._display = None
        except AttributeError:
            pass


def rebind_pyautogui() -> Any:
    """Lazy-load PyAutoGUI after DISPLAY exists and rebind cached Xlib state."""
    if not os.environ.get("DISPLAY"):
        raise DesktopInputError("Virtual display is not available")
    import pyautogui  # pylint: disable=import-outside-toplevel
    pyautogui.FAILSAFE = True
    backend = getattr(pyautogui, "_pyautogui_x11", None)
    if backend is not None:
        close_pyautogui_xlib(pyautogui)
        try:
            from Xlib.display import Display  # pylint: disable=import-outside-toplevel
            backend._display = Display(os.environ["DISPLAY"])
        except (ImportError, AttributeError) as exc:
            raise DesktopInputError("Could not connect desktop input to virtual display") from exc
    return pyautogui


class DesktopTools:
    """Element-targeted actions with guard checks; never exposes raw coordinates."""
    def __init__(self, driver: Any, pyautogui: Any | None = None, guard: Callable[[], None] | None = None):
        self._driver = driver
        self._pyautogui = pyautogui if pyautogui is not None else rebind_pyautogui()
        self._pyautogui.FAILSAFE = True
        self._guard = guard or (lambda: None)

    def _activate_page(self) -> None:
        self._guard()
        try:
            self._driver.execute_cdp_cmd("Page.bringToFront", {})
        except Exception as exc:
            raise DesktopInputError("Could not activate the task browser page") from exc
        self._guard()

    def _point(self, element: Any) -> _ScreenPoint:
        self._activate_page()
        try:
            raw = self._driver.execute_script(_POINTER_TARGET, element)
            if not isinstance(raw, dict):
                raise ValueError("no unambiguous target")
            point = self._map_point(raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise DesktopInputError("Desktop target is ambiguous or invalid") from exc
        self._guard()
        return point

    @staticmethod
    def _map_point(raw):
        x, y, sx, sy, ow, oh, iw, ih, sw, sh, dpr = (float(raw[key]) for key in ("x", "y", "screenX", "screenY", "outerWidth", "outerHeight", "innerWidth", "innerHeight", "screenWidth", "screenHeight", "dpr"))
        values = (x, y, sx, sy, ow, oh, iw, ih, sw, sh, dpr)
        if not all(value == value and abs(value) != float("inf") for value in values) or dpr != 1 or ow < iw or oh < ih or sw <= 0 or sh <= 0:
            raise ValueError("invalid geometry")
        point = _ScreenPoint(round(sx + (ow - iw) / 2 + x), round(sy + oh - ih + y))
        if not (0 <= point.x < round(sw) and 0 <= point.y < round(sh)):
            raise ValueError("target lies outside Xvfb screen")
        if not (0 <= x < iw and 0 <= y < ih):
            raise ValueError("point outside content viewport")
        return point

    def click_viewport(self, x, y, expected, fresh, guard):
        self._activate_page()
        guard()
        raw = self._driver.execute_script("return {screenX,screenY,outerWidth,outerHeight,innerWidth,innerHeight,screenWidth:screen.width,screenHeight:screen.height,dpr:devicePixelRatio};")
        if any(raw[key] != expected[key] for key in ("screenX", "screenY", "outerWidth", "outerHeight", "dpr")):
            raise DesktopInputError("Browser moved after screenshot")
        raw.update(x=x, y=y)
        try:
            point = self._map_point(raw)
        except (ValueError, TypeError, KeyError):
            raise DesktopInputError("Screenshot geometry is unsupported") from None
        guard()
        self._pyautogui.moveTo(point.x, point.y)
        guard()
        if not fresh():
            raise DesktopInputError("Screenshot changed before click")
        self._pyautogui.click()
        guard()

    def _move(self, element: Any) -> None:
        point = self._point(element)
        self._guard()
        try:
            self._pyautogui.moveTo(point.x, point.y)
        except Exception as exc:
            raise DesktopInputError("Could not move to desktop target") from exc
        self._guard()

    def _focus(self, element: Any, *, safe_input: bool = False, text_only: bool = False) -> None:
        self._activate_page()
        try:
            script = _TEXT_INPUT_FOCUS_TARGET if text_only else _SAFE_INPUT_FOCUS_TARGET if safe_input else _FOCUS_TARGET
            focused = self._driver.execute_script(script, element)
        except Exception as exc:
            raise DesktopInputError("Could not focus desktop target") from exc
        if focused is not True:
            raise DesktopInputError("Desktop target could not be focused")
        self._guard()

    def click(self, element: Any) -> None:
        self._move(element)
        self._guard()
        self._pyautogui.click()
        self._guard()

    def _safe_pointer_targets(self, *elements):
        self._activate_page()
        raw = self._driver.execute_script(_DRAG_TARGETS, *elements)
        if not isinstance(raw, dict) or len(raw.get("points", [])) != len(elements):
            raise DesktopInputError("Mouse targets are not safe visible controls")
        try:
            points = [self._map_point(point) for point in raw["points"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise DesktopInputError("Mouse target geometry is unsupported") from exc
        self._guard()
        return raw, points

    def double_click(self, element: Any) -> None:
        snapshot, points = self._safe_pointer_targets(element)
        self._pyautogui.moveTo(points[0].x, points[0].y)
        self._guard()
        fresh, _ = self._safe_pointer_targets(element)
        if fresh != snapshot:
            raise DesktopInputError("Mouse target changed before double click")
        self._pyautogui.doubleClick(interval=0.1)
        self._guard()

    def drag(self, source: Any, destination: Any, duration: float = 0.5) -> None:
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not 0.1 <= duration <= 2:
            raise DesktopInputError("Drag duration must be between 0.1 and 2 seconds")
        snapshot, points = self._safe_pointer_targets(source, destination)
        self._pyautogui.moveTo(points[0].x, points[0].y)
        fresh, _ = self._safe_pointer_targets(source, destination)
        if fresh != snapshot:
            raise DesktopInputError("Drag targets changed before input")
        self._guard()
        try:
            self._pyautogui.mouseDown(button="left")
            self._guard()
            self._pyautogui.moveTo(points[1].x, points[1].y, duration=duration)
            self._guard()
        finally:
            self._pyautogui.mouseUp(button="left")
        self._guard()

    def _verify_text_focus(self, element: Any) -> None:
        if self._driver.execute_script(_TEXT_INPUT_FOCUS_TARGET, element, False) is not True:
            raise DesktopInputError("Editable target or focus changed before input")

    def select_all(self, element: Any) -> None:
        self._focus(element, text_only=True)
        self._guard()
        self._verify_text_focus(element)
        try:
            self._pyautogui.keyDown("ctrl")
            self._guard()
            self._verify_text_focus(element)
            self._pyautogui.press("a")
        finally:
            self._pyautogui.keyUp("ctrl")
        self._guard()

    def hover(self, element: Any) -> None:
        self._move(element)

    def scroll(self, element: Any, amount: int) -> None:
        if isinstance(amount, bool) or not isinstance(amount, int) or not -10 <= amount <= 10 or amount == 0:
            raise DesktopInputError("Scroll amount must be a non-zero integer from -10 to 10")
        self._move(element)
        self._guard()
        self._pyautogui.scroll(amount)
        self._guard()

    def press_key(self, element: Any, key: str) -> None:
        if key not in _ALLOWED_KEYS:
            raise DesktopInputError("Desktop key is not allowed")
        self._focus(element, safe_input=True)
        self._guard()
        self._pyautogui.press(key)
        self._guard()

    def type_text(self, element: Any, text: str) -> None:
        if not isinstance(text, str) or not text or any(ord(char) < 32 or ord(char) == 127 for char in text):
            raise DesktopInputError("Text must be non-empty and contain no control characters")
        self._focus(element, text_only=True)
        self._guard()
        self._verify_text_focus(element)
        if text.isascii():
            self._pyautogui.write(text)
        else:
            element.send_keys(text)
        self._guard()
