from browser_helpers import mock_local_browser
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
    mock_local_browser(monkeypatch, lambda: browser)
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
    mock_local_browser(monkeypatch, lambda: browser)
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
    mock_local_browser(monkeypatch, lambda: browser)

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


def test_failure_diagnosis_uses_redacted_evidence_without_tools(monkeypatch):
    import json
    from app.schemas import LoginCredential
    from app.task_context import TaskContext
    from app.task_report import TaskExecutionFailure

    browser = FakeDriver()
    context = TaskContext(allow_write_actions=True, credentials=[LoginCredential(
        id="account", origins=["https://example.com"], username="private-user",
        password="private-password",
    )])
    context.record_observation("extract_text", "returned", "private-user: account form visible")
    mock_local_browser(monkeypatch, lambda: browser)

    class BrokenAgent:
        def invoke(self, *_args, **_kwargs):
            raise RuntimeError("private-password provider internal data")

    monkeypatch.setattr(agent, "create_deep_agent", lambda **_: BrokenAgent())
    calls = []

    class Model:
        def invoke(self, messages):
            assert browser.closed
            calls.append(messages)
            return SimpleNamespace(content="Could not finish after viewing the form. private-password")

    configurations = []
    def model(**kwargs):
        configurations.append(kwargs)
        return Model()

    monkeypatch.setattr(agent, "ChatOpenAI", model)
    settings = Settings(_env_file=None, openai_api_key="test", openai_base_url="https://model.example/v1",
                        model_name="test", enable_write_actions=True)
    with pytest.raises(TaskExecutionFailure) as error:
        agent.run_task("Sign in private-user", settings, context)
    assert len(calls) == 1
    evidence = json.loads(calls[0][1]["content"])
    assert "account form visible" in str(evidence)
    assert "private-user" not in str(calls)
    assert "private-password" not in str(calls) + str(error.value.result)
    assert "provider internal" not in str(calls)
    assert configurations[-1]["max_retries"] == 0
    assert configurations[-1]["timeout"] <= 10


def test_failure_analysis_outage_has_safe_fallback(monkeypatch):
    from app.task_report import TaskExecutionFailure
    browser = FakeDriver()
    mock_local_browser(monkeypatch, lambda: browser)

    class Broken:
        def invoke(self, *_args, **_kwargs):
            raise RuntimeError("secret internal detail")

    monkeypatch.setattr(agent, "create_deep_agent", lambda **_: Broken())
    monkeypatch.setattr(agent, "ChatOpenAI", lambda **_: Broken())
    settings = Settings(_env_file=None, openai_api_key="test", openai_base_url="https://model.example/v1", model_name="test")
    with pytest.raises(TaskExecutionFailure) as error:
        agent.run_task("Read title", settings)
    assert browser.closed
    assert "No additional agent analysis" in error.value.result["output"]
    assert "secret" not in str(error.value.result)


def test_cancelled_task_does_not_call_diagnostic_model(monkeypatch):
    from app.task_context import TaskContext
    from app.task_report import TaskExecutionFailure
    context = TaskContext()
    context.cancel()
    monkeypatch.setattr(agent, "ChatOpenAI", lambda **_: pytest.fail("Unexpected model call"))
    settings = Settings(_env_file=None, openai_api_key="test", openai_base_url="https://model.example/v1", model_name="test")
    with pytest.raises(TaskExecutionFailure):
        agent.run_task("Read title", settings, context)


@pytest.mark.parametrize("text", ["বাংলা" * 6000, '"\\n' * 6000], ids=["unicode", "escaping"])
def test_report_respects_serialized_byte_limit(text):
    import json
    from app.task_report import output_result
    result = output_result(text)
    assert result["output"]
    assert len(json.dumps(result, ensure_ascii=False).encode("utf-8")) <= 8000


@pytest.mark.parametrize("failure", [TimeoutError, RuntimeError], ids=["timeout", "unknown"])
def test_startup_failure_is_reported_without_raw_exception(monkeypatch, failure):
    from app.task_report import TaskExecutionFailure

    def unavailable(**_):
        raise failure("raw startup secret")

    class Offline:
        def invoke(self, *_):
            raise RuntimeError("raw provider secret")

    mock_local_browser(monkeypatch, unavailable)
    monkeypatch.setattr(agent, "ChatOpenAI", lambda **_: Offline())
    settings = Settings(_env_file=None, openai_api_key="test", openai_base_url="https://model.example/v1", model_name="test")
    with pytest.raises(TaskExecutionFailure) as error:
        agent.run_task("Read title", settings)
    assert "raw" not in str(error.value.result)
    if failure is TimeoutError:
        assert "time limit" in error.value.result["output"]


def test_cleanup_error_does_not_discard_success(monkeypatch):
    class Driver(FakeDriver):
        def quit(self):
            raise RuntimeError("cleanup secret")

    class Graph:
        def invoke(self, *_args, **_kwargs):
            return {"messages": [SimpleNamespace(content="Observed page title")]}

    mock_local_browser(monkeypatch, lambda: Driver())
    monkeypatch.setattr(agent, "create_deep_agent", lambda **_: Graph())
    monkeypatch.setattr(agent, "ChatOpenAI", lambda **_: object())
    settings = Settings(_env_file=None, openai_api_key="test", openai_base_url="https://model.example/v1", model_name="test")
    assert agent.run_task("Read title", settings) == {"output": "Observed page title"}
