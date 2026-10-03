from browser_helpers import mock_local_browser
import json
import socket
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet, InvalidToken
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import agent
from app.config import Settings
from app.main import create_app
from app.schemas import FixedProxy, LoginCredential, TaskRequest, TaskStatus
from app.selenium_tools import BrowserPolicyStop, browser_tools
from app.storage import TaskStore
from app.task_context import TaskContext, credential_cipher, decode_context, encode_context


USERNAME = "fake-account@example.com"
PASSWORD = "fake-test-password-123"


def credential():
    return LoginCredential(id="account", origins=["https://login.example"], username=USERNAME, password=PASSWORD)


def request_body():
    return {
        "prompt": "Sign in to my authorized account using credential ID account",
        "allow_write_actions": True,
        "credentials": [{
            "id": "account", "origins": ["https://login.example"],
            "username": USERNAME, "password": PASSWORD,
        }],
    }


def configured(tmp_path):
    return Settings(
        _env_file=None, database_path=tmp_path / "tasks.db", openai_api_key="test",
        openai_base_url="https://model.example/v1", model_name="test",
        task_api_token="test-token", enable_write_actions=True,
        credential_fernet_key=Fernet.generate_key().decode(),
    )


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.215.14", 443)),
    ])


@pytest.mark.parametrize("persistent", [False, True])
def test_encrypt_decrypt_and_redact(tmp_path, persistent):
    settings = configured(tmp_path)
    if not persistent:
        settings.credential_fernet_key = ""
    options, blob = encode_context(TaskRequest.model_validate(request_body()), settings)
    assert USERNAME not in options + blob
    assert PASSWORD not in options + blob
    context = decode_context(options, blob, settings)
    assert context.credentials[0].password.get_secret_value() == PASSWORD
    assert context.redacted_result({"output": PASSWORD, "nested": [USERNAME]}) == {
        "output": "[REDACTED]", "nested": ["[REDACTED]"],
    }
    assert decode_context(None, None, settings) is None
    with pytest.raises(InvalidToken):
        decode_context(options, "corrupt", settings)
    old = credential_cipher(settings).encrypt_at_time(b"[]", int(time.time()) - 1000).decode()
    with pytest.raises(InvalidToken):
        decode_context(options, old, settings)


def test_ephemeral_cipher_is_private_and_instance_scoped(tmp_path):
    settings = configured(tmp_path)
    settings.credential_fernet_key = ""
    cipher = credential_cipher(settings)
    assert credential_cipher(settings) is cipher
    assert "_ephemeral_credential_cipher" not in settings.model_dump()
    assert "_ephemeral_credential_cipher" not in repr(settings)
    request = TaskRequest.model_validate(request_body())
    options, blob = encode_context(request, settings)
    fresh = configured(tmp_path)
    fresh.credential_fernet_key = ""
    assert credential_cipher(fresh) is not cipher
    with pytest.raises(InvalidToken):
        decode_context(options, blob, fresh)


def test_pending_ephemeral_credentials_fail_safely_after_restart(tmp_path):
    from app.worker import TaskWorker

    settings = configured(tmp_path)
    settings.credential_fernet_key = ""
    options, blob = encode_context(TaskRequest.model_validate(request_body()), settings)
    store = TaskStore(settings.database_path)
    store.initialize()
    task_id = store.create("Authorized synthetic account test", 1, context_json=options, credential_blob=blob)
    fresh = configured(tmp_path)
    fresh.credential_fernet_key = ""
    calls = []
    worker = TaskWorker(store, fresh, runner=lambda *_: calls.append(True))
    worker.start()
    try:
        for _ in range(100):
            if store.get(task_id)["status"] == "FAILED":
                break
            time.sleep(0.01)
        result = store.get(task_id)
        assert result["status"] == "FAILED"
        assert result["error"] == "Task execution failed"
        assert not calls
        with store.connection() as connection:
            assert connection.execute("SELECT credential_blob FROM tasks WHERE task_id = ?", (task_id,)).fetchone()[0] is None
    finally:
        worker.stop()


@pytest.mark.parametrize("changes", [
    {"allow_write_actions": False},
    {"allow_write_actions": "true"},
    {"credentials": [{"id": "account", "origins": ["http://login.example"], "username": USERNAME, "password": PASSWORD}]},
    {"proxy": {"host": "proxy.example", "port": 8080, "password": PASSWORD}},
    {"proxy": {"host": "user:secret@proxy.example", "port": 8080}},
    {"proxy": {"host": "proxy.example", "port": 0}},
    {"proxy": {"scheme": "http", "host": "proxy.example", "port": 8080}},
    {"proxy": {"scheme": "socks5", "host": "proxy.example", "port": 8080}},
])
def test_validation_never_reflects_credentials(tmp_path, changes):
    body = request_body() | changes
    with TestClient(create_app(configured(tmp_path), runner=lambda *_: {})) as client:
        response = client.post("/run-task", json=body, headers={"Authorization": "Bearer test-token"})
        assert response.status_code == 422
        assert response.json() == {"detail": "Invalid task request"}
        assert PASSWORD not in response.text
        assert USERNAME not in response.text


@pytest.mark.parametrize("setting,value,expected", [
    ("enable_write_actions", False, 403),
    ("task_api_token", "", 403),
    ("credential_fernet_key", "invalid", 503),
])
def test_credential_admission_fails_closed(tmp_path, setting, value, expected):
    settings = configured(tmp_path)
    setattr(settings, setting, value)
    with TestClient(create_app(settings, runner=lambda *_: {})) as client:
        response = client.post("/run-task", json=request_body(), headers={"Authorization": "Bearer test-token"})
        assert response.status_code == expected
        assert PASSWORD not in response.text
        assert client.app.state.store.claim_execution() is None


@pytest.mark.parametrize("persistent", [False, True])
def test_authenticated_execution_redacts_and_clears(tmp_path, persistent):
    settings = configured(tmp_path)
    if not persistent:
        settings.credential_fernet_key = ""
    seen = []

    def runner(prompt, _, context):
        assert PASSWORD not in prompt
        seen.append(context.credentials[0].password.get_secret_value())
        return {"output": f"{USERNAME} {PASSWORD}"}

    with TestClient(create_app(settings, runner=runner)) as client:
        headers = {"Authorization": "Bearer test-token"}
        response = client.post("/run-task", json=request_body(), headers=headers)
        assert response.status_code == 202
        task_id = response.json()["task_id"]
        for _ in range(100):
            result = client.get(f"/task-status/{task_id}", headers=headers)
            if result.json()["status"] in ("COMPLETED", "FAILED"):
                break
            time.sleep(0.01)
        assert result.json()["status"] == "COMPLETED"
        assert seen == [PASSWORD]
        assert PASSWORD not in result.text and USERNAME not in result.text
        with client.app.state.store.connection() as conn:
            row = conn.execute("SELECT credential_blob FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            assert row[0] is None


@pytest.mark.parametrize("status", [TaskStatus.COMPLETED, TaskStatus.FAILED, "restart"])
def test_storage_migrates_and_clears_secrets(tmp_path, status):
    path = tmp_path / "tasks.db"
    with sqlite3.connect(path) as conn:
        conn.execute("""CREATE TABLE tasks (
            task_id TEXT PRIMARY KEY, prompt TEXT NOT NULL, status TEXT NOT NULL,
            result_json TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
    store = TaskStore(path)
    store.initialize()
    store.initialize()
    task_id = store.create("Test", 2, context_json="{}", credential_blob="ciphertext")
    assert store.claim_execution()["credential_blob"] == "ciphertext"
    if status == "restart":
        store.recover_interrupted()
    else:
        store.finish(task_id, status)
    with store.connection() as conn:
        assert conn.execute("SELECT credential_blob FROM tasks").fetchone()[0] is None
    assert "credential_blob" not in store.get(task_id)


def test_pending_expiry_cleanup_and_recovery(tmp_path):
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    old = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    expired = store.create("Old", 2, credential_blob="encrypted", credential_expires_at=old)
    pending = store.create("New", 2, context_json="{}", credential_blob="still-encrypted")
    assert store.recover_interrupted() == 0
    assert store.claim_execution()["task_id"] == pending
    assert store.get(expired)["status"] == "FAILED"
    with store.connection() as conn:
        assert conn.execute("SELECT credential_blob FROM tasks WHERE task_id = ?", (expired,)).fetchone()[0] is None


class FakeElement:
    tag_name = "input"
    text = "Sign in"

    def __init__(self, input_type="password"):
        self.input_type = input_type
        self.values = []

    def get_attribute(self, name):
        return self.input_type if name == "type" else None

    def clear(self):
        pass

    def send_keys(self, value):
        self.values.append(value)

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True


class FakeDriver:
    current_url = "https://login.example/signin"
    title = "Sign in"

    def __init__(self):
        self.closed = False
        self.top = True
        self.element = FakeElement()
        self.body = SimpleNamespace(text="Sign in")
        self.capabilities = {}

    def find_element(self, by, value):
        return self.body if value == "body" else self.element

    def execute_script(self, _):
        return {"origin": "https://login.example", "top": self.top}

    def set_page_load_timeout(self, _):
        pass

    def set_script_timeout(self, _):
        pass

    def quit(self):
        self.closed = True


def tool_by_name(driver, settings, context, name):
    tools = browser_tools(driver, settings, time.monotonic() + 60, context)
    return next(item for item in tools if item.name == name)


def test_origin_bound_credential_fill(tmp_path):
    driver = FakeDriver()
    context = TaskContext(allow_write_actions=True, credentials=[credential()])
    fill = tool_by_name(driver, configured(tmp_path), context, "fill_credential")
    result = fill.invoke({"selector": "#password", "credential_id": "account", "field": "password"})
    assert result == "Credential entered"
    assert driver.element.values == [PASSWORD]
    assert PASSWORD not in result


@pytest.mark.parametrize("restriction", ["origin", "frame", "input", "challenge", "expired", "id"])
def test_credential_policy_stops_before_entry(tmp_path, restriction):
    driver = FakeDriver()
    context = TaskContext(allow_write_actions=True, credentials=[credential()])
    if restriction == "origin":
        driver.current_url = "https://other.example/"
    elif restriction == "frame":
        driver.top = False
    elif restriction == "input":
        driver.element.input_type = "text"
    elif restriction == "challenge":
        driver.body.text = "Enter your verification code"
    elif restriction == "expired":
        context.credential_expires_at = time.time() - 1
    fill = tool_by_name(driver, configured(tmp_path), context, "fill_credential")
    with pytest.raises(BrowserPolicyStop):
        fill.invoke({"selector": "#password", "credential_id": "unknown" if restriction == "id" else "account", "field": "password"})
    assert driver.element.values == []


@pytest.mark.parametrize("global_gate,task_gate", [(False, True), (True, False), (True, None)])
def test_account_write_gates(tmp_path, global_gate, task_gate):
    settings = configured(tmp_path)
    settings.enable_write_actions = global_gate
    context = TaskContext(allow_write_actions=task_gate, credentials=[credential()])
    tools = browser_tools(FakeDriver(), settings, time.monotonic() + 60, context)
    assert {item.name for item in tools} == {"navigate_to_page", "extract_text", "inspect_page"}


def test_direct_browser_and_secret_free_model_context(tmp_path, monkeypatch):
    driver = FakeDriver()
    captured = {}

    def remote(**kwargs):
        captured["options"] = kwargs["options"].to_capabilities()
        driver.capabilities = captured["options"]
        return driver

    class FakeAgent:
        def invoke(self, state, config):
            captured["state"] = state
            return {"messages": [SimpleNamespace(content=f"Done {PASSWORD}")]}

    def factory(**kwargs):
        captured.update(kwargs)
        return FakeAgent()

    mock_local_browser(monkeypatch, lambda: remote(options=__import__("selenium").webdriver.ChromeOptions()))
    monkeypatch.setattr(agent, "create_deep_agent", factory)
    context = TaskContext(allow_write_actions=True, credentials=[credential()])
    result = agent.run_task("Authorized login using account", configured(tmp_path), context)
    assert driver.closed
    assert result == {"output": "Done [REDACTED]"}
    assert not captured["options"].get("proxy")
    assert PASSWORD not in json.dumps(captured["state"]) + captured["system_prompt"]
    assert USERNAME not in captured["system_prompt"]
    assert "account" in captured["system_prompt"]
    from deepagents.backends import StateBackend

    assert isinstance(captured["backend"], StateBackend)
    assert captured["subagents"][0]["tools"] == []
    assert PASSWORD not in captured["subagents"][0]["system_prompt"]
    assert USERNAME not in captured["subagents"][0]["system_prompt"]
    assert all(item.name not in ("read_file", "execute", "task") for item in captured["tools"])


@pytest.mark.parametrize("host,scheme", [("proxy.example", "http"), ("proxy.example", "socks5"), ("127.0.0.1", "http")])
def test_legacy_proxy_context_rejected_before_browser(tmp_path, monkeypatch, host, scheme):
    calls = []
    mock_local_browser(monkeypatch, lambda: calls.append(True))
    context = TaskContext(proxy=FixedProxy(host=host, scheme=scheme, port=8080))
    with pytest.raises(RuntimeError, match="Task proxies are disabled"):
        agent.run_task("Read title", configured(tmp_path), context)
    assert calls == []


def test_real_deep_agent_graph_uses_virtual_files_and_browser_tools(tmp_path, monkeypatch):
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage

    seen = []

    class TestModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            seen.extend(item.name for item in tools)
            return self

    driver = FakeDriver()
    settings = configured(tmp_path)
    tools = browser_tools(driver, settings, time.monotonic() + 60)
    mock_local_browser(monkeypatch, lambda: driver)
    monkeypatch.setattr(agent, "ChatOpenAI", lambda **_: TestModel(responses=[AIMessage(content="Read-only test")]))
    result = agent.run_task("Report no action", settings)
    assert result == {"output": "Read-only test"}
    assert driver.closed
    assert {item.name for item in tools}.issubset(seen)
    assert {"read_file", "write_file", "write_todos", "task"}.issubset(seen)
    assert "execute" not in seen


def test_worker_decryption_failure_is_sanitized_and_cleared(tmp_path, caplog):
    from app.worker import TaskWorker

    settings = configured(tmp_path)
    store = TaskStore(settings.database_path)
    store.initialize()
    task_id = store.create("Test", 1, context_json="{}", credential_blob=PASSWORD)
    calls = []
    worker = TaskWorker(store, settings, runner=lambda *_: calls.append(True))
    worker.start()
    try:
        for _ in range(100):
            if store.get(task_id)["status"] == "FAILED":
                break
            time.sleep(0.01)
        assert store.get(task_id)["error"] == "Task execution failed"
        assert calls == []
        assert PASSWORD not in caplog.text
        with store.connection() as conn:
            assert conn.execute("SELECT credential_blob FROM tasks").fetchone()[0] is None
    finally:
        worker.stop()


def test_credential_context_survives_pending_restart(tmp_path):
    settings = configured(tmp_path)
    options, blob = encode_context(TaskRequest.model_validate(request_body()), settings)
    store = TaskStore(settings.database_path)
    store.initialize()
    task_id = store.create("Test", 1, context_json=options, credential_blob=blob)
    reopened = TaskStore(settings.database_path)
    reopened.initialize()
    assert reopened.recover_interrupted() == 0
    record = reopened.claim_execution()
    assert record["task_id"] == task_id
    assert decode_context(record["context_json"], record["credential_blob"], settings).credentials[0].id == "account"
    with reopened.connection() as conn:
        assert PASSWORD not in str(tuple(conn.execute("SELECT * FROM tasks").fetchone()))


def test_explicit_read_only_task_ceiling(tmp_path):
    context = TaskContext(allow_write_actions=False)
    tools = browser_tools(FakeDriver(), configured(tmp_path), time.monotonic() + 60, context)
    assert {item.name for item in tools} == {"navigate_to_page", "extract_text", "inspect_page"}


def test_shutdown_cancels_active_credentials_and_browser(tmp_path):
    from threading import Event
    from app.worker import TaskWorker

    settings = configured(tmp_path)
    options, blob = encode_context(TaskRequest.model_validate(request_body()), settings)
    store = TaskStore(settings.database_path)
    store.initialize()
    task_id = store.create("Test", 1, context_json=options, credential_blob=blob)
    started = Event()
    closed = Event()

    def runner(_prompt, _settings, context):
        context.bind_browser(closed.set)
        started.set()
        assert context.cancelled.wait(3)
        return {"output": "Cancelled"}

    worker = TaskWorker(store, settings, runner=runner)
    worker.start()
    try:
        assert started.wait(3)
    finally:
        worker.stop()
    assert closed.is_set()
    assert not worker.thread.is_alive()
    assert store.get(task_id)["status"] == "FAILED"
    assert "shutdown" in store.get(task_id)["error"]
    with store.connection() as conn:
        assert conn.execute("SELECT credential_blob FROM tasks").fetchone()[0] is None


def test_cancelled_context_closes_late_session_and_blocks_tools(tmp_path):
    context = TaskContext(allow_write_actions=True, credentials=[credential()])
    context.cancel()
    driver = FakeDriver()
    with pytest.raises(RuntimeError, match="cancelled"):
        context.bind_browser(driver.quit)
    assert driver.closed
    tools = browser_tools(driver, configured(tmp_path), time.monotonic() + 60, context)
    with pytest.raises(BrowserPolicyStop, match="cancelled"):
        tools[0].invoke({"url": "https://example.com"})
