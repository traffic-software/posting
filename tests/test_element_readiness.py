import pytest
from langchain_core.tools import ToolException
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from app.element_readiness import ElementReadinessTimeout, READINESS, SCROLL_TARGET, wait_for_ready


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now

    def sleep(self, delay):
        self.now += delay


class Element:
    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def get_attribute(self, name):
        assert name == 'readonly'
        return None


class Driver:
    def __init__(self, states):
        self.states = iter(states)
        self.last = 'ready'
        self.scrolls = 0
        self.probes = 0

    def execute_script(self, script, *args):
        if script == SCROLL_TARGET:
            self.scrolls += 1
            return None
        assert script == READINESS
        self.probes += 1
        self.last = next(self.states, self.last)
        return self.last


def wait(driver, element, clock, **kwargs):
    return wait_for_ready(driver, lambda: [element], ['fill'], 10, 1,
                          lambda: None, clock=clock, sleep=clock.sleep, **kwargs)


def test_ready_returns_immediately():
    clock, element, driver = Clock(), Element(), Driver(['ready'])
    assert wait(driver, element, clock) == [element]
    assert clock.now == 0 and driver.probes == 1


@pytest.mark.parametrize('state', ['hidden', 'disabled', 'readonly', 'covered'])
def test_condition_waits_only_until_ready(state):
    clock, driver = Clock(), Driver([state, state, 'ready'])
    wait(driver, Element(), clock)
    assert clock.now == pytest.approx(.2)
    assert driver.probes == 3


@pytest.mark.parametrize('state', ['missing', 'hidden', 'disabled', 'readonly', 'covered'])
def test_timeout_contains_fixed_blocker_without_target_details(state):
    clock, driver = Clock(), Driver([state])
    with pytest.raises(ElementReadinessTimeout, match=state) as error:
        wait(driver, Element(), clock)
    assert 'performed no input or click' in str(error.value)
    assert clock.now == pytest.approx(1)


def test_offscreen_scrolls_once_then_returns():
    clock, driver = Clock(), Driver(['offscreen', 'offscreen', 'ready'])
    wait(driver, Element(), clock)
    assert driver.scrolls == 1


@pytest.mark.parametrize('exception', [NoSuchElementException, StaleElementReferenceException])
def test_transient_resolution_is_repeated_not_action(exception):
    clock, driver, element = Clock(), Driver(['ready']), Element()
    calls = []
    def resolve():
        calls.append(True)
        if len(calls) == 1:
            raise exception('private internal detail')
        return [element]
    result = wait_for_ready(driver, resolve, ['click'], 10, 1, lambda: None,
                            clock=clock, sleep=clock.sleep)
    assert result == [element] and len(calls) == 2


def test_task_deadline_caps_wait():
    clock = Clock()
    with pytest.raises(ElementReadinessTimeout):
        wait_for_ready(Driver(['covered']), lambda: [Element()], ['click'], .25, 20,
                       lambda: None, clock=clock, sleep=clock.sleep)
    assert clock.now == pytest.approx(.25)


def test_policy_guard_not_swallowed():
    clock = Clock()
    calls = []
    def guard():
        calls.append(True)
        if clock.now >= .1:
            raise RuntimeError('policy stop')
    with pytest.raises(RuntimeError, match='policy stop'):
        wait_for_ready(Driver(['covered']), lambda: [Element()], ['click'], 10, 1,
                       guard, clock=clock, sleep=clock.sleep)
    assert clock.now == pytest.approx(.1)


def test_unknown_probe_fails_closed_without_waiting():
    clock = Clock()
    with pytest.raises(ToolException, match='Could not verify'):
        wait(Driver(['unexpected']), Element(), clock)
    assert clock.now == 0


def test_all_controls_must_be_ready_together():
    clock, driver = Clock(), Driver(['ready', 'disabled', 'ready', 'ready'])
    controls = [Element(), Element()]
    assert wait_for_ready(driver, lambda: controls, ['fill', 'click'], 10, 1,
                          lambda: None, clock=clock, sleep=clock.sleep) == controls
    assert clock.now == pytest.approx(.1)


def test_cancellation_interrupts_sleep_before_another_probe():
    clock, driver = Clock(), Driver(['covered'])
    class Cancelled:
        flag = False
        def wait(self, delay):
            self.flag = True
            return True
    cancelled = Cancelled()
    def guard():
        if cancelled.flag:
            raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError, match='cancelled'):
        wait_for_ready(driver, lambda: [Element()], ['click'], 10, 1, guard,
                       cancelled, clock=clock, sleep=clock.sleep)
    assert driver.probes == 1


def test_driver_failure_is_not_a_readiness_timeout():
    clock = Clock()
    class BrokenDriver:
        def execute_script(self, *args):
            raise RuntimeError('driver disconnected')
    with pytest.raises(RuntimeError, match='driver disconnected'):
        wait(BrokenDriver(), Element(), clock)
    assert clock.now == 0
