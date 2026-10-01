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
