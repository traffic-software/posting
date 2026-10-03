"""Bounded, action-specific readiness checks without retrying browser writes."""
import time

from langchain_core.tools import ToolException
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException


class ElementReadinessTimeout(ToolException):
    pass


READINESS = """
const el = arguments[0], mode = arguments[1];
if (!el || !el.isConnected) return 'missing';
const r = el.getBoundingClientRect(), style = getComputedStyle(el);
if (!el.getClientRects().length || r.width <= 0 || r.height <= 0 ||
    style.visibility === 'hidden' || style.visibility === 'collapse' || style.display === 'none') return 'hidden';
if (mode === 'read') return 'ready';
if (el.matches(':disabled') || el.getAttribute('aria-disabled') === 'true') return 'disabled';
if (mode === 'fill' && el.readOnly) return 'readonly';
const x = r.left + r.width / 2, y = r.top + r.height / 2;
if (x < 0 || y < 0 || x >= innerWidth || y >= innerHeight) return 'offscreen';
const hit = document.elementFromPoint(x, y);
return hit && (hit === el || el.contains(hit)) ? 'ready' : 'covered';
"""
SCROLL_TARGET = "arguments[0].scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'});"
_STATES = frozenset({'ready', 'missing', 'hidden', 'disabled', 'readonly', 'offscreen', 'covered'})


def readiness(driver, element, mode):
    if not element.is_displayed():
        return 'hidden'
    if mode != 'read' and not element.is_enabled():
        return 'disabled'
    if mode == 'fill' and element.get_attribute('readonly') is not None:
        return 'readonly'
    state = driver.execute_script(READINESS, element, mode)
    if state not in _STATES:
        raise ToolException('Could not verify element readiness')
    return state


def wait_for_ready(driver, resolve, modes, deadline, timeout, guard, cancelled=None,
                   *, clock=time.monotonic, sleep=time.sleep):
    """Resolve fresh controls on every poll; never click, clear or type here."""
    end = min(deadline, clock() + timeout)
    state = 'missing'
    scrolled = []
    while True:
        guard()
        if clock() >= end:
            raise ElementReadinessTimeout(
                f'Element readiness timed out ({state}); this invocation performed no input or click. '
                'Inspect the current page/form again before choosing a current target.'
            )
        try:
            elements = resolve()
            current_modes = modes(elements) if callable(modes) else modes
            if elements and len(elements) == len(current_modes):
                for element, mode in zip(elements, current_modes):
                    guard()
                    state = readiness(driver, element, mode)
                    if state == 'offscreen' and element not in scrolled:
                        guard()
                        driver.execute_script(SCROLL_TARGET, element)
                        scrolled.append(element)
                        if len(scrolled) > 16:
                            raise ToolException('Target changed repeatedly; inspect the page again')
                    if state != 'ready':
                        break
                else:
                    guard()
                    if clock() < end:
                        return elements
            else:
                state = 'missing'
        except (NoSuchElementException, StaleElementReferenceException):
            state = 'missing'
        delay = max(0, min(0.1, end - clock()))
        if cancelled is None:
            sleep(delay)
        elif cancelled.wait(delay):
            guard()
