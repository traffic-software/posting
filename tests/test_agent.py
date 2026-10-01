from types import SimpleNamespace

import pytest

from app import agent
from app.config import Settings


@pytest.mark.parametrize("operation", ["task", "write_file"])
def test_deep_agent_builtin_tools_are_task_scoped(monkeypatch, operation):
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage, ToolMessage

    browser = FakeDriver()
    bound_tools = []
    if operation == "task":
        arguments = {"subagent_type": "general-purpose", "description": "Plan only; do not act."}
        replies = [
            AIMessage(content="", tool_calls=[{"name": operation, "args": arguments, "id": "builtin"}]),
            AIMessage(content="Plan: read the page title."),
            AIMessage(content="Planning complete."),
        ]
    else:
        arguments = {"file_path": "/migration-test.txt", "content": "Task-local notes"}
        replies = [
            AIMessage(content="", tool_calls=[{"name": operation, "args": arguments, "id": "builtin"}]),
            AIMessage(content="Planning complete."),
        ]

    class TestModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            bound_tools.append({item.name for item in tools})
            return self

    model = TestModel(responses=replies)
    monkeypatch.setattr(agent.webdriver, "Remote", lambda **_: browser)
    monkeypatch.setattr(agent, "ChatOpenAI", lambda **_: model)
    states = []
    factory = agent.create_deep_agent

    def capture_graph(**kwargs):
        graph = factory(**kwargs)

        class Graph:
            def invoke(self, *args, **kwargs):
                state = graph.invoke(*args, **kwargs)
                states.append(state)
                return state

        return Graph()

    monkeypatch.setattr(agent, "create_deep_agent", capture_graph)
    settings = Settings(
        _env_file=None, openai_api_key="test", openai_base_url="https://model.example/v1",
        model_name="test-model",
    )
    assert agent.run_task("Plan without browser actions", settings) == {"output": "Planning complete."}
    assert browser.closed
    assert all("execute" not in names for names in bound_tools)
    results = [message for message in states[0]["messages"] if isinstance(message, ToolMessage)]
    assert results and all(message.status != "error" for message in results)
    if operation == "task":
        assert any("navigate_to_page" in names for names in bound_tools)
        assert any("navigate_to_page" not in names and "fill_credential" not in names for names in bound_tools)
        assert "Plan: read the page title." in str(results[0].content)
    else:
        assert "/migration-test.txt" in states[0]["files"]
        assert "Task-local notes" in str(states[0]["files"]["/migration-test.txt"])


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

    monkeypatch.setattr(agent, "create_deep_agent", lambda **_: FakeAgent())
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

    monkeypatch.setattr(agent, "create_deep_agent", lambda **_: FakeAgent())
    settings = Settings(
        _env_file=None, openai_api_key="test", openai_base_url="https://model.example/v1",
        model_name="test-model"
    )
    with pytest.raises(RuntimeError):
        agent.run_task("Get title", settings)
    assert browser.closed
