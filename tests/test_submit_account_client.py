import importlib.util
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest


@pytest.fixture
def client_script(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts" / "submit_account_task.py"
    spec = importlib.util.spec_from_file_location("submit_client", path)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    monkeypatch.setattr(script, "load_dotenv", lambda *_: None)
    monkeypatch.setenv("TASK_API_TOKEN", "fake-token")
    monkeypatch.setenv("TASK_API_URL", "https://api.example")
    monkeypatch.setattr(script.sys, "argv", ["submit_account_task.py"])
    monkeypatch.setattr(script.getpass, "getpass", lambda *_: pytest.fail("Unexpected credential prompt"))
    return script


def fake_client(monkeypatch, script, submitted, status=202, detail=None, result=None):
    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, path, json):
            submitted.append(json)
            return SimpleNamespace(status_code=status, json=lambda: {"task_id": "fake-task"} if status == 202 else {"detail": detail})

        def get(self, path):
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: result or {"status": "COMPLETED", "result": {"output": "Demo done"}})

    monkeypatch.setattr(script.httpx, "Client", FakeClient)


@pytest.mark.parametrize("status,detail", [
    (202, None), (503, "Task service is not configured"),
    (503, "Credential encryption is unavailable"), (422, "unknown-sensitive-error"),
])
def test_fixed_account_submission_without_live_calls(client_script, monkeypatch, capsys, status, detail):
    submitted = []
    fake_client(monkeypatch, client_script, submitted, status, detail)
    assert client_script.main() == (0 if status == 202 else 1)
    assert len(submitted) == 1
    payload = submitted[0]
    assert payload["allow_write_actions"] is True
    assert "inspect_totp_form" in payload["prompt"] and "fill_totp" in payload["prompt"]
    expected = client_script.account_payload(payload["prompt"], set())["credentials"][0]
    assert all(payload["credentials"][0][key] == value for key, value in expected.items())
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "fake-token" not in output and "unknown-sensitive-error" not in output
    assert all(expected[key] not in output for key in ("username", "password", "totp_secret"))
    if detail == "Credential encryption is unavailable":
        assert detail in captured.err


def test_known_credential_output_is_redacted(client_script, monkeypatch, capsys):
    secrets = {"fake-token"}
    credential = client_script.account_payload("test", secrets)["credentials"][0]
    fake_client(monkeypatch, client_script, [], result={
        "status": "COMPLETED", "result": {"output": " ".join(secrets)},
    })
    assert client_script.main() == 0
    output = capsys.readouterr().out
    assert "[REDACTED]" in output
    assert all(secret not in output for secret in secrets)
    assert all(credential[key] not in output for key in ("username", "password", "totp_secret"))


def test_resume_does_not_resubmit(client_script, monkeypatch):
    submitted = []
    monkeypatch.setattr(client_script.sys, "argv", ["client", "--task-id", "existing-task"])
    fake_client(monkeypatch, client_script, submitted)
    assert client_script.main() == 0
    assert not submitted


def test_old_account_flag_still_runs_fixed_test(client_script, monkeypatch):
    submitted = []
    monkeypatch.setattr(client_script.sys, "argv", ["client", "--account"])
    fake_client(monkeypatch, client_script, submitted)
    assert client_script.main() == 0
    assert len(submitted) == 1 and "credentials" in submitted[0]


def test_https_is_required_before_submission(client_script, monkeypatch):
    monkeypatch.setenv("TASK_API_URL", "http://api.example")
    submitted = []
    fake_client(monkeypatch, client_script, submitted)
    assert client_script.main() == 1
    assert not submitted


def test_network_failure_never_retries(client_script, monkeypatch, capsys):
    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, *args, **kwargs):
            calls.append(True)
            raise httpx.ConnectError("private-error-details")

    monkeypatch.setattr(client_script.httpx, "Client", FakeClient)
    assert client_script.main() == 1
    assert len(calls) == 1
    output = capsys.readouterr()
    assert "private-error-details" not in output.err
    assert "outcome may be unknown" in output.err
