from types import SimpleNamespace

import pytest

from app import agent
from app.config import Settings


class FakeDriver:
    def __init__(self):
        self.current_url = "about:blank"
        self.closed = False

    def set_page_load_timeout(self, _):
        pass

    def set_script_timeout(self, _):
        pass

    def quit(self):
        self.closed = True


def test_agent_closes_its_browser_after_result(monkeypatch):
    browser = FakeDriver()
    monkeypatch.setattr(agent.webdriver, "Remote", lambda **_: browser)
    seen = {}

    class FakeAgent:
        def invoke(self, state, config):
            seen["state"] = state
            seen["config"] = config
            return {"messages": [SimpleNamespace(content="Page title: Example")]}

    monkeypatch.setattr(agent, "create_agent", lambda **_: FakeAgent())
    settings = Settings(
        _env_file=None, openai_api_key="test", openai_base_url="https://model.example/v1",
        model_name="test-model"
    )
    assert agent.run_task("Get title", settings) == {"output": "Page title: Example"}
    assert browser.closed
    assert seen["state"]["messages"][0]["content"] == "Get title"
    assert seen["config"] == {"recursion_limit": settings.max_agent_steps}


def test_agent_closes_its_browser_after_error(monkeypatch):
    browser = FakeDriver()
    monkeypatch.setattr(agent.webdriver, "Remote", lambda **_: browser)

    class FakeAgent:
        def invoke(self, *_args, **_kwargs):
            raise RuntimeError("provider failure")

    monkeypatch.setattr(agent, "create_agent", lambda **_: FakeAgent())
    settings = Settings(
        _env_file=None, openai_api_key="test", openai_base_url="https://model.example/v1",
        model_name="test-model"
    )
    with pytest.raises(RuntimeError):
        agent.run_task("Get title", settings)
    assert browser.closed
