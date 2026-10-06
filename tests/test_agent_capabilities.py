import pytest

from app.browser_dom import IS_EDITING_HOST
from app.desktop_tools import DesktopInputError, DesktopTools, _DRAG_TARGETS, _TEXT_INPUT_FOCUS_TARGET
from app.selenium_tools import BrowserPolicyStop
from test_desktop_browser_tools import bind, setup  # noqa: F401
from test_desktop_runtime import FakeDriver, FakeElement, FakePyAutoGUI


class PointerDriver(FakeDriver):
    def execute_script(self, script, *elements):
        if script == _DRAG_TARGETS:
            return {"points": [dict(self.geometry) for _ in elements], "url": "https://example.com/", "scrollX": 0, "scrollY": 0}
        return super().execute_script(script, elements[0])


def test_named_mouse_and_editing_actions():
    gui = FakePyAutoGUI()
    desktop = DesktopTools(PointerDriver(), gui)
    desktop.double_click(FakeElement())
    desktop.drag(FakeElement(), FakeElement())
    desktop.select_all(FakeElement())
    assert ("double",) in gui.calls
    assert gui.calls.index(("down",)) < gui.calls.index(("up",))
    assert gui.calls[-3:] == [("key-down", "ctrl"), ("press", "a"), ("key-up", "ctrl")]
    assert gui.FAILSAFE is True


@pytest.mark.parametrize("action,held,released", [
    (lambda d: d.drag(FakeElement(), FakeElement()), ("down",), ("up",)),
    (lambda d: d.select_all(FakeElement()), ("key-down", "ctrl"), ("key-up", "ctrl")),
])
def test_input_releases_on_guard_failure(action, held, released):
    gui = FakePyAutoGUI()

    def guard():
        if held in gui.calls:
            raise RuntimeError("cancelled during input")

    with pytest.raises(RuntimeError, match="cancelled"):
        action(DesktopTools(PointerDriver(), gui, guard))
    assert gui.calls[-1] == released


def test_changed_drag_targets_perform_no_button_input():
    class Changed(PointerDriver):
        scans = 0

        def execute_script(self, script, *elements):
            result = super().execute_script(script, *elements)
            if script == _DRAG_TARGETS:
                self.scans += 1
                result["scrollY"] = self.scans
            return result

    gui = FakePyAutoGUI()
    with pytest.raises(DesktopInputError, match="changed"):
        DesktopTools(Changed(), gui).drag(FakeElement(), FakeElement())
    assert ("down",) not in gui.calls


@pytest.mark.parametrize("duration", [True, 0, 3, float("nan"), float("inf")])
def test_drag_duration_bounds(duration):
    gui = FakePyAutoGUI()
    with pytest.raises(DesktopInputError):
        DesktopTools(PointerDriver(), gui).drag(FakeElement(), FakeElement(), duration)
    assert not gui.calls


def test_non_text_focus_refusal_blocks_typing_and_selection():
    class Rejected(PointerDriver):
        def execute_script(self, script, *elements):
            if script == _TEXT_INPUT_FOCUS_TARGET:
                return False
            return super().execute_script(script, *elements)

    gui = FakePyAutoGUI()
    desktop = DesktopTools(Rejected(), gui)
    for action in (lambda: desktop.type_text(FakeElement(), "ordinary"), lambda: desktop.select_all(FakeElement())):
        with pytest.raises(DesktopInputError):
            action()
    assert not gui.calls


def test_contenteditable_fill_uses_guarded_desktop(setup, monkeypatch):
    driver, desktop, _, _ = setup
    driver.element.tag_name = "div"
    driver.element.input_type = "text"
    original = driver.execute_script

    def script(code, *args):
        if code == IS_EDITING_HOST:
            return True
        return original(code, *args)

    monkeypatch.setattr(driver, "execute_script", script)
    assert bind(setup)["fill_element"].invoke({"selector": "*:nth-child(1)", "value": "new prompt"}) == "Field updated"
    assert desktop.calls[-1][0] == "type"


def test_unsupported_text_target_is_recoverable_without_clear(setup, monkeypatch):
    driver, desktop, _, _ = setup
    driver.element.tag_name = "div"
    original = driver.execute_script
    monkeypatch.setattr(driver, "execute_script", lambda code, *args: False if code == IS_EDITING_HOST else original(code, *args))
    result = bind(setup)["fill_element"].invoke({"selector": "*:nth-child(1)", "value": "new prompt"})
    assert "Unsupported text target" in result
    assert not desktop.calls and not driver.element.values


@pytest.mark.parametrize("autocomplete", ["current-password", "new-password", "one-time-code"])
def test_sensitive_autocomplete_remains_policy_stop(setup, autocomplete):
    setup[0].element.attributes["autocomplete"] = autocomplete
    with pytest.raises(BrowserPolicyStop):
        bind(setup)["fill_element"].invoke({"selector": "*:nth-child(1)", "value": "ordinary"})
    assert not setup[1].calls


def test_new_mouse_tools_require_fresh_inspection(setup):
    from langchain_core.tools import ToolException
    with pytest.raises(ToolException, match="Inspect"):
        bind(setup)["double_click_element"].invoke({"selector": "*:nth-child(2)"})
    assert not setup[1].calls
