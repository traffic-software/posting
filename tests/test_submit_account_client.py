import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("status,detail", [
    (202, None),
    (503, "Task service is not configured"),
    (422, "unknown-sensitive-error"),
])
def test_prompt_only_submission_without_live_calls(monkeypatch, capsys, status, detail):
    path = Path(__file__).resolve().parents[1] / "scripts" / "submit_account_task.py"
    spec = importlib.util.spec_from_file_location("submit_client", path)
    client_script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client_script)
    monkeypatch.setattr(client_script, "load_dotenv", lambda *_: None)
    monkeypatch.setenv("TASK_API_TOKEN", "fake-token")
    monkeypatch.setenv("TASK_API_URL", "https://api.example")
    monkeypatch.setattr(client_script.sys, "argv", ["submit_account_task.py"])
    monkeypatch.setattr(client_script.getpass, "getpass", lambda *_: "Authorized demo task")
    submitted = []

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, path, json):
            submitted.append(json)
            return SimpleNamespace(
                status_code=status,
                json=lambda: {"task_id": "fake-task"} if status == 202 else {"detail": detail},
            )

        def get(self, path):
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {"status": "COMPLETED", "result": {"output": "Demo done"}},
            )

    monkeypatch.setattr(client_script.httpx, "Client", FakeClient)
    assert client_script.main() == (0 if status == 202 else 1)
    assert submitted == [{"prompt": "Authorized demo task"}]
    captured = capsys.readouterr()
    assert "fake-token" not in captured.out + captured.err
    assert "unknown-sensitive-error" not in captured.err
    if status == 503:
        assert "model configuration is incomplete" in captured.err


@pytest.mark.parametrize("consent,seed,origins,expected", [
    ("yes", "gezd gnbv gy3t qojq gezd gnbv gy3t qojq", "https://login.example", 0),
    ("no", "", "https://login.example", 1),
    ("yes", "invalid-private-seed", "https://login.example", 1),
    ("yes", "", "http://login.example", 1),
    ("yes", "", "https://login.example", 0),
])
def test_account_mode_keeps_secrets_out_of_prompt(monkeypatch, capsys, consent, seed, origins, expected):
    path = Path(__file__).resolve().parents[1] / "scripts" / "submit_account_task.py"
    spec = importlib.util.spec_from_file_location("account_client", path)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    monkeypatch.setattr(script, "load_dotenv", lambda *_: None)
    monkeypatch.setenv("TASK_API_TOKEN", "private-token")
    monkeypatch.setenv("TASK_API_URL", "https://api.example")
    monkeypatch.setattr(script.sys, "argv", ["submit_account_task.py", "--account"])
    hidden = iter(["Sign in using account", "private-user", 'private-"password', seed])
    visible = iter(["account", origins, consent])
    monkeypatch.setattr(script.getpass, "getpass", lambda *_: next(hidden))
    monkeypatch.setattr("builtins.input", lambda *_: next(visible))
    submitted = []

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, path, json):
            submitted.append(json)
            return SimpleNamespace(status_code=202, json=lambda: {"task_id": "fake-task"})

        def get(self, path):
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {
                "status": "COMPLETED", "result": {"output": 'private-user private-"password ' + seed + " GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"},
            })

    monkeypatch.setattr(script.httpx, "Client", FakeClient)
    assert script.main() == expected
    output = capsys.readouterr()
    assert "private-token" not in output.out + output.err
    assert "private-user" not in output.out + output.err and 'private-\\"password' not in output.out + output.err
    if seed:
        assert seed not in output.out + output.err
    if expected:
        assert not submitted
    else:
        assert submitted[0]["prompt"] == "Sign in using account"
        assert submitted[0]["allow_write_actions"] is True
        credential = submitted[0]["credentials"][0]
        assert credential["password"] == 'private-"password'
        assert credential["totp_secret"] == ("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ" if seed else None)
        if seed:
            assert credential["totp_secret"] not in output.out


def test_account_mode_and_polling_are_mutually_exclusive(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts" / "submit_account_task.py"
    spec = importlib.util.spec_from_file_location("account_conflict", path)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    monkeypatch.setattr(script.sys, "argv", ["client", "--account", "--task-id", "00000000-0000-0000-0000-000000000001"])
    with pytest.raises(SystemExit) as error:
        script.main()
    assert error.value.code == 2


def test_account_payload_imports_schema_outside_repository(tmp_path):
    import subprocess
    import sys

    path = Path(__file__).resolve().parents[1] / "scripts" / "submit_account_task.py"
    code = """
import runpy, builtins, getpass, sys
module = runpy.run_path(sys.argv[1])
visible = iter(['account', 'https://login.example', 'yes'])
hidden = iter(['private-user', 'private-password', ''])
builtins.input = lambda *_: next(visible)
getpass.getpass = lambda *_: next(hidden)
payload = module['account_payload']('Authorized account task', set())
assert payload['credentials'][0]['password'] == 'private-password'
print('ok')
"""
    result = subprocess.run([sys.executable, "-I", "-c", code, str(path)], cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
