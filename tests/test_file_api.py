import json
import socket
import time
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas import TaskRequest
from app.storage import TaskStore
from app.task_context import decode_context, encode_context, encode_file_sources


TOKEN = "synthetic-file-api-token"
SOURCE = "https://source.example/video.mp4?signature=private-source-signature"


def settings(tmp_path, **overrides):
    values = dict(_env_file=None, openai_api_key="fixture", openai_base_url="https://unused.example/v1",
                  model_name="fixture", task_api_token=TOKEN, database_path=tmp_path / "tasks.db",
                  browser_profiles_root=tmp_path / "profiles", enable_file_transfers=True, enable_write_actions=True,
                  artifact_root=tmp_path / "artifacts", artifact_public_base_url="https://files.example",
                  artifact_link_signing_key="k" * 32, credential_fernet_key=Fernet.generate_key().decode())
    values.update(overrides)
    return Settings(**values)


def await_task(client, task_id):
    end = time.monotonic() + 5
    while time.monotonic() < end:
        response = client.get(f"/task-status/{task_id}", headers={"Authorization": f"Bearer {TOKEN}"})
        task = response.json()
        if task["status"] in {"COMPLETED", "FAILED"}:
            return response, task
        time.sleep(.01)
    pytest.fail("Fixture task did not finish")


def test_ready_artifacts_are_separate_from_report_and_download_without_auth(tmp_path):
    payload = b"abcdef\x00"

    def runner(prompt, config, ctx):
        writer = ctx._artifact_session.reserve(name="video.mp4")
        writer.write(payload)
        writer.finish()
        return {"output": "x" * 7900}

    app = create_app(settings(tmp_path), runner=runner)
    with TestClient(app) as client:
        assert client.post("/run-task", json={"prompt": "Get the file", "allow_file_downloads": True}).status_code == 401
        posted = client.post("/run-task", json={"prompt": "Get the file", "allow_file_downloads": True}, headers={"Authorization": f"Bearer {TOKEN}"})
        assert posted.status_code == 202
        response, task = await_task(client, posted.json()["task_id"])
        assert response.headers["cache-control"] == "no-store"
        assert task["result"] == {"output": "x" * 7900}
        assert len(task["artifacts"]) == 1
        artifact = task["artifacts"][0]
        assert artifact["download_url"].startswith("https://files.example/task-artifacts/")
        assert "download_url" not in str(app.state.store.get(task["task_id"])["result"])
        downloaded = client.get(artifact["download_url"])
        assert downloaded.status_code == 200 and downloaded.content == payload
        assert downloaded.headers["content-type"] == "application/octet-stream"
        assert downloaded.headers["content-disposition"].startswith("attachment;")
        assert downloaded.headers["x-content-type-options"] == "nosniff"
        assert downloaded.headers["cache-control"] == "no-store"
        assert not app.state.artifacts._leases
        ranged = client.get(artifact["download_url"], headers={"Range": "bytes=1-3"})
        assert ranged.status_code == 206 and ranged.content == b"bcd"
        assert ranged.headers["content-range"] == "bytes 1-3/7"
        assert client.head(artifact["download_url"]).headers["content-length"] == "7"
        assert client.head(artifact["download_url"]).content == b""
        assert not app.state.artifacts._leases
        parsed = urlsplit(artifact["download_url"])
        query = parse_qs(parsed.query)
        query["signature"] = ["0" * 64]
        bad = parsed._replace(query=urlencode({key: value[0] for key, value in query.items()})).geturl()
        assert client.get(bad).status_code == 404
        assert client.get(parsed.path).status_code == 422
        assert client.get(f"/task-status/{task['task_id']}").status_code == 401


def test_failure_keeps_only_completed_outputs_not_input_or_partial_files(tmp_path):
    def runner(prompt, config, ctx):
        writer = ctx._artifact_session.reserve(name="completed.bin")
        writer.write(b"finished")
        writer.finish()
        source = ctx._artifact_session.reserve(purpose="input", name="reference.bin")
        source.write(b"private input")
        source.finish()
        partial = ctx._artifact_session.reserve(name="partial.bin")
        partial.write(b"unfinished")
        raise RuntimeError("Fixture failure")

    with TestClient(create_app(settings(tmp_path), runner=runner)) as client:
        posted = client.post("/run-task", json={"prompt": "Fetch fixture", "allow_file_downloads": True}, headers={"Authorization": f"Bearer {TOKEN}"})
        _, task = await_task(client, posted.json()["task_id"])
        assert task["status"] == "FAILED"
        assert [artifact["name"] for artifact in task["artifacts"]] == ["completed.bin"]
        assert client.get(task["artifacts"][0]["download_url"]).content == b"finished"


def test_source_blob_is_encrypted_legacy_context_decodes_and_claim_erases_it(tmp_path):
    config = settings(tmp_path)
    request = TaskRequest(prompt="Upload the reference", allow_write_actions=True, upload_origins=["https://upload.example"],
                          upload_sources=[{"id": "reference", "url": SOURCE, "filename": "video.mp4"}])
    options, credentials = encode_context(request, config)
    blob = encode_file_sources(request, config)
    assert SOURCE not in options and SOURCE not in blob and "private-source-signature" not in blob
    ctx = decode_context(options, credentials, config, file_sources_blob=blob)
    assert ctx.upload_sources[0].url.get_secret_value() == SOURCE
    assert SOURCE not in ctx.redact(SOURCE) and "private-source-signature" not in ctx.redact("private-source-signature")
    assert decode_context(None, None, config) is None
    old = decode_context(json.dumps({"allow_write_actions": True}), None, config)
    assert old.upload_sources == []
    store = TaskStore(config.database_path)
    store.initialize()
    task_id = store.create("Upload reference", 2, context_json=options, file_sources_blob=blob)
    claimed = store.claim_execution()
    assert claimed["file_sources_blob"] == blob
    with store.connection() as conn:
        assert conn.execute("SELECT file_sources_blob FROM tasks WHERE task_id=?", (task_id,)).fetchone()[0] is None


def test_url_grants_are_not_fetched_at_admission_and_missing_keys_are_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("8.8.8.8", 443))])
    seen = []

    def runner(prompt, config, ctx):
        seen.append((prompt, ctx.upload_sources[0].url.get_secret_value()))
        return {"output": "Source grant inspected; no upload attempted"}

    body = {"prompt": "Upload from " + SOURCE, "allow_write_actions": True, "upload_origins": ["https://upload.example"],
            "upload_sources": [{"id": "reference", "url": SOURCE}]}
    with TestClient(create_app(settings(tmp_path), runner=runner)) as client:
        posted = client.post("/run-task", json=body, headers={"Authorization": f"Bearer {TOKEN}"})
        assert posted.status_code == 202
        _, task = await_task(client, posted.json()["task_id"])
        assert task["artifacts"] == []
        assert SOURCE not in seen[0][0] and seen[0][1] == SOURCE
    with TestClient(create_app(settings(tmp_path / "no-key", credential_fernet_key=""), runner=runner)) as client:
        assert client.post("/run-task", json=body, headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 503


def test_file_fields_require_feature_flag_auth_and_upload_consent(tmp_path):
    app = create_app(settings(tmp_path, enable_file_transfers=False), runner=lambda *_: {"output": "unused"})
    with TestClient(app) as client:
        response = client.post("/run-task", json={"prompt": "Fetch a file", "allow_file_downloads": True}, headers={"Authorization": f"Bearer {TOKEN}"})
        assert response.status_code == 403
        response = client.post("/run-task", json={"prompt": "Upload", "upload_sources": [{"id": "ref", "url": SOURCE}],
                                               "upload_origins": ["https://upload.example"]}, headers={"Authorization": f"Bearer {TOKEN}"})
        assert response.status_code == 422 and SOURCE not in response.text


def test_expired_source_queue_grants_are_not_claimed(tmp_path):
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    task = store.create("Expired source", 1, file_sources_blob="ciphertext", file_sources_expires_at="2000-01-01T00:00:00+00:00")
    assert store.claim_execution() is None
    record = store.get(task)
    assert record["status"] == "FAILED" and "file-source grants expired" in record["result"]["output"]
