import time
from threading import Event
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas import TaskStatus


def settings_for(tmp_path):
    return Settings(
        _env_file=None,
        database_path=tmp_path / "tasks.db",
        openai_api_key="test-key",
        openai_base_url="https://model.example/v1",
        model_name="test-model",
        allowed_hosts="example.com",
        task_api_token="test-token",
    )


def headers():
    return {"Authorization": "Bearer test-token"}


def await_final(client, task_id):
    for _ in range(100):
        response = client.get(f"/task-status/{task_id}", headers=headers())
        if response.json()["status"] in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            return response
        time.sleep(0.01)
    raise AssertionError("Task did not finish")


def test_submit_poll_and_reopen_database(tmp_path):
    settings = settings_for(tmp_path)
    with TestClient(create_app(settings, runner=lambda prompt, _: {"output": prompt.upper()})) as client:
        assert client.get("/health").json() == {"status": "ok"}
        accepted = client.post("/run-task", json={"prompt": "hello"}, headers=headers())
        assert accepted.status_code == 202
        task_id = accepted.json()["task_id"]
        assert accepted.json()["status"] == TaskStatus.PENDING
        done = await_final(client, task_id)
        assert done.json()["result"] == {"output": "HELLO"}
        assert done.json()["status"] == TaskStatus.COMPLETED
    with TestClient(create_app(settings, runner=lambda *_: None)) as client:
        assert client.get(f"/task-status/{task_id}", headers=headers()).json()["result"] == {"output": "HELLO"}


def test_validation_auth_and_missing_task(tmp_path):
    with TestClient(create_app(settings_for(tmp_path), runner=lambda *_: {})) as client:
        assert client.post("/run-task", json={"prompt": "secret"}).status_code == 401
        assert client.post("/run-task", json={"prompt": "   "}, headers=headers()).status_code == 422
        assert client.get(f"/task-status/{uuid4()}", headers=headers()).status_code == 404
        assert client.get("/task-status/not-a-uuid", headers=headers()).status_code == 422


def test_runner_failure_is_sanitized(tmp_path):
    def fail(*_):
        raise RuntimeError("secret internal value")

    with TestClient(create_app(settings_for(tmp_path), runner=fail)) as client:
        task_id = client.post("/run-task", json={"prompt": "fail"}, headers=headers()).json()["task_id"]
        result = await_final(client, task_id).json()
        assert result["status"] == TaskStatus.FAILED
        assert result["error"] == "Task execution failed"
        assert "secret" not in str(result)


def test_unconfigured_service_rejects_submission(tmp_path):
    settings = Settings(_env_file=None, database_path=tmp_path / "tasks.db", allowed_hosts="")
    with TestClient(create_app(settings, runner=lambda *_: {})) as client:
        assert client.post("/run-task", json={"prompt": "test"}).status_code == 503


def test_processing_task_limits_admission(tmp_path):
    started = Event()
    release = Event()

    def wait_for_release(*_):
        started.set()
        assert release.wait(5)
        return {"output": "done"}

    settings = settings_for(tmp_path)
    settings.max_active_tasks = 1
    try:
        with TestClient(create_app(settings, runner=wait_for_release)) as client:
            task_id = client.post("/run-task", json={"prompt": "first"}, headers=headers()).json()["task_id"]
            assert started.wait(5)
            current = client.get(f"/task-status/{task_id}", headers=headers()).json()
            assert current["status"] == TaskStatus.PROCESSING
            assert client.post("/run-task", json={"prompt": "second"}, headers=headers()).status_code == 429
            release.set()
            assert await_final(client, task_id).json()["status"] == TaskStatus.COMPLETED
    finally:
        release.set()
