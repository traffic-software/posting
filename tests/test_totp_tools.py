from browser_helpers import mock_local_browser
import socket
import time
from types import SimpleNamespace

import pyotp
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from selenium.common.exceptions import WebDriverException

from app import agent, selenium_tools
from app.main import create_app
from app.schemas import LoginCredential, TaskRequest
from app.selenium_tools import BrowserPolicyStop, browser_tools
from app.task_context import TaskContext, decode_context, encode_context
from test_account_tasks import FakeDriver, FakeElement, configured


SEED = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
NOW = 2000000000
CODE = "279037"


def credential(seed=SEED):
    return LoginCredential(id="account", origins=["https://login.example"], username="test-user", password="test-password", totp_secret=seed)


class Element(FakeElement):
    def __init__(self, tag="input", kind="text"):
        super().__init__(kind)
        self.tag_name = tag
        self.attributes = {"autocomplete": "one-time-code"}
        self.clicked = False
        self.fail_send = False

    def get_attribute(self, name):
        return self.input_type if name == "type" else self.attributes.get(name)

    def send_keys(self, value):
        super().send_keys(value)
        if self.fail_send:
            raise WebDriverException(value)

    def click(self):
        self.clicked = True


class Driver(FakeDriver):
    def __init__(self):
        super().__init__()
        self.element = Element()
        self.submit = Element("button", "submit")
        self.body = SimpleNamespace(text="Enter the verification code from your authenticator app", is_displayed=lambda: True)
        self.action = "https://login.example/verify"
        self.same_form = True
        self.cells = None

    def find_elements(self, by, value):
        return self.cells if self.cells is not None else [self.element]

    def find_element(self, by, value):
        if value == "#submit":
            return self.submit
        return super().find_element(by, value)

    def execute_script(self, script, *args):
        from app.element_readiness import READINESS, SCROLL_TARGET
        if script in (READINESS, SCROLL_TARGET):
            return super().execute_script(script, *args)
        if script == selenium_tools.DISCOVER_CONTROLS:
            inputs = self.cells if self.cells is not None else [self.element]
            return [{"element": element, "selector": f"*:nth-child({index + 1})", "form": 0} for index, element in enumerate(inputs)] + [
                {"element": self.submit, "selector": "*:nth-child(7)", "form": 0},
            ]
        if args:
            return {"sameForm": self.same_form and not getattr(args[0], "other_form", False), "action": self.action}
        return super().execute_script(script)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.215.14", 443)),
    ])
    monkeypatch.setattr(selenium_tools.time, "time", lambda: NOW)
    monkeypatch.setattr(pyotp.TOTP, "now", lambda self: self.at(selenium_tools.time.time()))
    settings = configured(tmp_path)
    context = TaskContext(allow_write_actions=True, credentials=[credential()])
    return Driver(), settings, context


def get_tool(setup, name="fill_totp", deadline=None):
    driver, settings, context = setup
    return next(tool for tool in browser_tools(driver, settings, deadline or time.monotonic() + 60, context) if tool.name == name)


def invoke(tool, credential_id="account"):
    return tool.invoke({"selector": "#otp", "submit_selector": "#submit", "credential_id": credential_id})


@pytest.mark.parametrize("timestamp,expected", [
    (59, "287082"), (1111111109, "081804"), (1111111111, "050471"),
    (1234567890, "005924"), (2000000000, CODE), (20000000000, "353130"),
])
def test_rfc6238_sha1_six_digit_vectors(timestamp, expected):
    assert pyotp.TOTP(SEED, digits=6, interval=30).at(timestamp) == expected


def test_fill_and_submit_never_returns_code(setup):
    driver, _, context = setup
    result = invoke(get_tool(setup))
    assert driver.element.values == [CODE]
    assert driver.submit.clicked
    assert CODE not in result and SEED not in result
    assert context.redacted_result({"output": f"{SEED} {CODE}"}) == {"output": "[REDACTED] [REDACTED]"}
    driver.element.text = f"{SEED} {CODE}"
    assert get_tool(setup, "extract_text").invoke({"selector": "#otp"}) == "[REDACTED] [REDACTED]"
    with pytest.raises(BrowserPolicyStop):
        invoke(get_tool(setup))
    assert len(driver.element.values) == 1


@pytest.mark.parametrize("restriction", [
    "origin", "frame", "expired", "cancelled", "captcha", "denied", "suspicious", "insecure",
    "ambiguous", "sms", "email", "recovery", "input", "autocomplete", "readonly", "button", "action", "form",
])
def test_totp_guards_prevent_entry(setup, restriction):
    driver, _, context = setup
    tool = get_tool(setup)
    if restriction == "origin":
        driver.current_url = "https://other.example/"
    elif restriction == "frame":
        driver.top = False
    elif restriction == "expired":
        context.credential_expires_at = NOW - 1
    elif restriction == "cancelled":
        context.cancel()
    elif restriction in ("captcha", "denied", "suspicious", "insecure", "sms", "email", "recovery"):
        driver.body.text += {"captcha": " CAPTCHA", "denied": " Access denied", "suspicious": " suspicious login",
                             "insecure": " this browser or app may not be secure", "sms": " SMS",
                             "email": " email code", "recovery": " recovery code"}[restriction]
    elif restriction == "ambiguous":
        driver.body.text = "Enter your verification code"
    elif restriction == "input":
        driver.element.input_type = "password"
    elif restriction == "autocomplete":
        driver.element.attributes.clear()
    elif restriction == "readonly":
        driver.element.attributes["readonly"] = "true"
    elif restriction == "button":
        driver.submit.input_type = "button"
    elif restriction == "action":
        driver.action = "https://other.example/collect"
    elif restriction == "form":
        driver.same_form = False
    if restriction == "readonly":
        setup[1].browser_timeout_seconds = 0
        assert "readiness timed out" in invoke(tool)
    else:
        with pytest.raises(BrowserPolicyStop):
            invoke(tool)
    assert not driver.element.values and not driver.submit.clicked
    assert not context._totp_codes


@pytest.mark.parametrize("name,args", [
    ("click_element", {"selector": "#submit"}),
    ("fill_element", {"selector": "#otp", "value": "123456"}),
    ("fill_credential", {"selector": "#otp", "credential_id": "account", "field": "username"}),
])
@pytest.mark.parametrize("text", ["Use your authenticator app", "Enter TOTP", "Use your authentication app"])
def test_generic_tools_still_stop_at_totp(setup, name, args, text):
    setup[0].body.text = text
    with pytest.raises(BrowserPolicyStop):
        get_tool(setup, name).invoke(args)


@pytest.mark.parametrize("server,consent,seed", [(False, True, SEED), (True, False, SEED), (True, None, SEED), (True, True, None)])
def test_tool_visibility_requires_secret_and_both_gates(setup, server, consent, seed):
    driver, settings, context = setup
    settings.enable_write_actions = server
    context.allow_write_actions = consent
    context.credentials = [credential(seed)]
    assert "fill_totp" not in {tool.name for tool in browser_tools(driver, settings, time.monotonic() + 60, context)}


def test_unknown_and_seedless_credentials_fail(setup):
    _, _, context = setup
    tool = get_tool(setup)
    context.credentials.append(credential(None).model_copy(update={"id": "other"}))
    for ident in ("unknown", "other"):
        with pytest.raises(BrowserPolicyStop, match="unavailable"):
            invoke(tool, ident)


def test_uncertain_entry_does_not_retry_or_leak(setup):
    driver, _, context = setup
    tool = get_tool(setup)
    driver.element.fail_send = True
    with pytest.raises(BrowserPolicyStop) as error:
        invoke(tool)
    assert CODE not in str(error.value) and SEED not in str(error.value)
    assert not driver.submit.clicked
    driver.element.fail_send = False
    with pytest.raises(BrowserPolicyStop):
        invoke(tool)
    assert driver.element.values == [CODE]
    assert context.redact(CODE) == "[REDACTED]"


def test_boundary_waits_for_fresh_period(setup, monkeypatch):
    driver, _, context = setup
    clock = [NOW + 9]  # One second remains in the current period.
    monkeypatch.setattr(selenium_tools.time, "time", lambda: clock[0])
    monkeypatch.setattr(context.cancelled, "wait", lambda _: clock.__setitem__(0, NOW + 10) or False)
    invoke(get_tool(setup))
    assert driver.element.values == [pyotp.TOTP(SEED).at(NOW + 10)]


def test_boundary_cannot_exceed_deadline(setup, monkeypatch):
    monkeypatch.setattr(selenium_tools.time, "time", lambda: NOW + 9)
    with pytest.raises(BrowserPolicyStop):
        invoke(get_tool(setup, deadline=time.monotonic() + 0.1))
    assert not setup[0].element.values


@pytest.mark.parametrize("change", ["origin", "expiry", "cancel"])
def test_guard_rechecked_after_element_waits(setup, monkeypatch, change):
    driver, _, context = setup
    original = driver.find_element

    def redirected(by, value):
        element = original(by, value)
        if value == "#submit":
            if change == "origin":
                driver.current_url = "https://other.example/"
            elif change == "expiry":
                context.credential_expires_at = NOW - 1
            else:
                context.cancelled.set()
        return element

    monkeypatch.setattr(driver, "find_element", redirected)
    with pytest.raises(BrowserPolicyStop):
        invoke(get_tool(setup))
    assert not driver.element.values and not driver.submit.clicked


def test_new_hard_restriction_after_submission_stops_task(setup, monkeypatch):
    driver, _, _ = setup

    def click():
        driver.submit.clicked = True
        driver.body.text = "Suspicious login"

    monkeypatch.setattr(driver.submit, "click", click)
    with pytest.raises(BrowserPolicyStop):
        invoke(get_tool(setup))
    assert driver.element.values == [CODE] and driver.submit.clicked


def test_attempts_bounded_and_runtime_cleanup(setup):
    _, _, context = setup
    item = context.credentials[0]
    context.reserve_totp(item, 1, "111111")
    context.reserve_totp(item, 2, "222222")
    with pytest.raises(RuntimeError):
        context.reserve_totp(item, 3, "333333")
    assert SEED not in repr(context) and "111111" not in repr(context)
    context.cancel()
    assert not context.credentials and not context._totp_codes and not context._totp_attempts


@pytest.mark.parametrize("persistent", [False, True])
def test_totp_encrypted_round_trip_and_legacy(tmp_path, persistent):
    settings = configured(tmp_path)
    if not persistent:
        settings.credential_fernet_key = ""
    request = TaskRequest(prompt="Authorized login", allow_write_actions=True, credentials=[credential()])
    options, blob = encode_context(request, settings)
    assert SEED not in options + blob
    context = decode_context(options, blob, settings)
    assert context.credentials[0].totp_secret.get_secret_value() == SEED
    request.credentials = [credential(None)]
    options, blob = encode_context(request, settings)
    assert decode_context(options, blob, settings).credentials[0].totp_secret is None


@pytest.mark.parametrize("seed", ["", "not-base32-secret", "A" * 17, "A" * 129, "otpauth://totp/test", " " + SEED])
def test_invalid_seeds_have_sanitized_errors(seed):
    with pytest.raises(ValidationError) as error:
        credential(seed)
    assert "Invalid Base32 TOTP secret" in str(error.value)
    if seed:
        assert seed not in str(error.value)


@pytest.mark.parametrize("fails", [False, True])
def test_worker_redacts_persisted_result_and_cleans_runtime(tmp_path, caplog, monkeypatch, fails):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.215.14", 443)),
    ])
    settings = configured(tmp_path)
    seen = []

    def runner(_prompt, _settings, context):
        seen.append(context)
        context.reserve_totp(context.credentials[0], 1, CODE)
        if fails:
            raise RuntimeError(f"{SEED} {CODE}")
        return {"output": f"{SEED} {CODE}"}

    body = {"prompt": "Authorized login", "allow_write_actions": True, "credentials": [{
        "id": "account", "origins": ["https://login.example"], "username": "test-user",
        "password": "test-password", "totp_secret": SEED,
    }]}
    with TestClient(create_app(settings, runner=runner)) as client:
        headers = {"Authorization": "Bearer test-token"}
        response = client.post("/run-task", json=body, headers=headers)
        assert response.status_code == 202
        task_id = response.json()["task_id"]
        for _ in range(100):
            result = client.get(f"/task-status/{task_id}", headers=headers).json()
            if result["status"] in ("COMPLETED", "FAILED"):
                break
            time.sleep(0.01)
        assert result["status"] == ("FAILED" if fails else "COMPLETED")
        if fails:
            assert result["error"] == "Task execution failed"
        else:
            assert result["result"] == {"output": "[REDACTED] [REDACTED]"}
        with client.app.state.store.connection() as connection:
            row = connection.execute("SELECT result_json, credential_blob FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            assert row[1] is None
            assert SEED not in (row[0] or "") and CODE not in (row[0] or "")
    assert seen and not seen[0].credentials and not seen[0]._totp_codes
    assert CODE not in caplog.text and SEED not in caplog.text


@pytest.mark.parametrize("split", [False, True])
def test_real_deep_agent_invokes_totp_without_secret_observations(setup, monkeypatch, split):
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage, ToolMessage

    driver, settings, context = setup
    transcripts = []

    class TestModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            transcripts.extend(messages)
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    if split:
        split_cells(driver)
    model = TestModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "inspect_totp_form", "id": "inspect", "args": {"credential_id": "account"}}]),
        AIMessage(content="", tool_calls=[{"name": "fill_totp", "id": "totp", "args": {
            "selector": "#otp", "submit_selector": "#submit", "credential_id": "account",
        }}]),
        AIMessage(content="", tool_calls=[{"name": "extract_text", "id": "observe", "args": {"selector": "body"}}]),
        AIMessage(content="Authenticator submitted; outcome not yet observed"),
    ])
    mock_local_browser(monkeypatch, lambda: driver)
    monkeypatch.setattr(agent, "ChatOpenAI", lambda **_: model)
    result = agent.run_task("Authorized authenticator login", settings, context)
    assert driver.submit.clicked and driver.closed
    if split:
        assert [element.values for element in driver.cells] == [[digit] for digit in CODE]
    else:
        assert driver.element.values == [CODE]
    assert CODE not in result["output"] and SEED not in result["output"]
    assert any(isinstance(message, ToolMessage) and message.name == "fill_totp" for message in transcripts)
    assert all(SEED not in str(message.content) and CODE not in str(message.content) for message in transcripts)


def split_cells(driver, count=6):
    driver.cells = [Element(kind="tel") for _ in range(count)]
    for element in driver.cells:
        element.attributes = {"maxlength": "1", "inputmode": "numeric"}
    return driver.cells


@pytest.mark.parametrize("attributes", [
    {"maxlength": "6", "inputmode": "numeric"},
    {"maxlength": "6", "pattern": "[0-9]{6}"},
])
def test_single_without_autocomplete_supported(setup, attributes):
    driver, _, _ = setup
    driver.element.attributes = attributes
    invoke(get_tool(setup))
    assert driver.element.values == [CODE] and driver.submit.clicked


def test_six_cell_entry_in_dom_order(setup):
    driver, _, _ = setup
    cells = split_cells(driver)
    invoke(get_tool(setup))
    assert [element.values for element in cells] == [[digit] for digit in CODE]
    assert driver.submit.clicked


@pytest.mark.parametrize("restriction", ["five", "seven", "hidden", "disabled", "readonly", "type", "length", "numeric", "form"])
def test_invalid_split_layout_rejected_before_entry(setup, monkeypatch, restriction):
    driver, _, context = setup
    cells = split_cells(driver, 5 if restriction == "five" else 7 if restriction == "seven" else 6)
    if restriction == "hidden":
        monkeypatch.setattr(cells[-1], "is_displayed", lambda: False)
    elif restriction == "disabled":
        monkeypatch.setattr(cells[-1], "is_enabled", lambda: False)
    elif restriction == "readonly":
        cells[-1].attributes["readonly"] = "true"
    elif restriction == "type":
        cells[-1].input_type = "password"
    elif restriction == "length":
        cells[-1].attributes["maxlength"] = "2"
    elif restriction == "numeric":
        cells[-1].input_type = "text"
        cells[-1].attributes.pop("inputmode")
    elif restriction == "form":
        cells[-1].other_form = True
    if restriction in ("hidden", "disabled", "readonly"):
        setup[1].browser_timeout_seconds = 0
        assert "readiness timed out" in invoke(get_tool(setup))
    else:
        with pytest.raises(BrowserPolicyStop):
            invoke(get_tool(setup))
    assert all(not element.values for element in cells) and not context._totp_codes
    assert not driver.submit.clicked


@pytest.mark.parametrize("change", ["origin", "expired", "cancelled", "replacement"])
def test_split_mid_entry_changes_prevent_completion(setup, monkeypatch, change):
    driver, _, context = setup
    cells = split_cells(driver)
    send = cells[0].send_keys

    def change_after_first_digit(value):
        send(value)
        if change == "origin":
            driver.current_url = "https://other.example/"
        elif change == "expired":
            context.credential_expires_at = NOW - 1
        elif change == "cancelled":
            context.cancelled.set()
        else:
            driver.cells = [Element(kind="tel") for _ in range(6)]

    monkeypatch.setattr(cells[0], "send_keys", change_after_first_digit)
    with pytest.raises(BrowserPolicyStop):
        invoke(get_tool(setup))
    assert cells[0].values == [CODE[0]] and all(not element.values for element in cells[1:])
    assert not driver.submit.clicked


@pytest.mark.parametrize("split", [False, True])
def test_discovery_is_value_free_and_bounded(setup, split):
    import json

    driver, _, _ = setup
    if split:
        split_cells(driver)
    driver.element.attributes["value"] = SEED
    driver.element.attributes["name"] = "private-token"
    driver.element.text = CODE
    metadata = get_tool(setup, "inspect_totp_form").invoke({"credential_id": "account"})
    assert SEED not in metadata and CODE not in metadata and "private-token" not in metadata
    data = json.loads(metadata)
    assert len(data["forms"]) == 1
    assert set(data["forms"][0]) == {"layout", "selector", "submit_selector"}
    assert data["forms"][0]["layout"] == ("six-digit" if split else "single")
    assert not driver.element.values and not driver.submit.clicked


def test_discovery_is_not_a_fill_authorization(setup):
    get_tool(setup, "inspect_totp_form").invoke({"credential_id": "account"})
    setup[0].action = "https://other.example/"
    with pytest.raises(BrowserPolicyStop):
        invoke(get_tool(setup))
    assert not setup[0].element.values


@pytest.mark.parametrize("crossing", ["boundary", "freshness"])
def test_now_reserves_only_a_stable_fresh_period(setup, monkeypatch, crossing):
    driver, _, context = setup
    clock = [NOW]
    calls = []
    monkeypatch.setattr(selenium_tools.time, "time", lambda: clock[0])

    def now(totp):
        calls.append(clock[0])
        code = totp.at(clock[0])
        if len(calls) == 1:
            clock[0] = NOW + (10 if crossing == "boundary" else 6)
        return code

    monkeypatch.setattr(pyotp.TOTP, "now", now)
    monkeypatch.setattr(context.cancelled, "wait", lambda _: clock.__setitem__(0, NOW + 10) or False)
    invoke(get_tool(setup))
    assert len(calls) == 2
    assert driver.element.values == [pyotp.TOTP(SEED).at(NOW + 10)]
    assert context._totp_attempts == {"account": {int((NOW + 10) // 30)}}


def test_seed_canonicalization():
    raw = " ".join(SEED.lower()[index:index + 4] for index in range(0, len(SEED), 4))
    assert credential("\t" + raw + "\n").totp_secret.get_secret_value() == SEED


def test_agent_prompt_contains_only_totp_capability(setup, monkeypatch):
    driver, settings, context = setup
    captured = {}
    mock_local_browser(monkeypatch, lambda: driver)

    def factory(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(invoke=lambda *_args, **_kwargs: {"messages": [SimpleNamespace(content="Stopped")]})

    monkeypatch.setattr(agent, "create_deep_agent", factory)
    agent.run_task("Authorized account", settings, context)
    assert "authenticator=True" in captured["system_prompt"]
    assert SEED not in captured["system_prompt"] and CODE not in captured["system_prompt"]
    assert captured["subagents"][0]["tools"] == []
    tool = next(item for item in captured["tools"] if item.name == "fill_totp")
    assert set(tool.args) == {"selector", "submit_selector", "credential_id"}
