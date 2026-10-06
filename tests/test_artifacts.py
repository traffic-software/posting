import hashlib
import logging
import os
import threading
from urllib.parse import parse_qs, urlsplit

import pytest

from app.artifacts import ArtifactAccessLogFilter, ArtifactError, ArtifactManager
from app.config import Settings
from app.schemas import TaskStatus
from app.storage import TaskStore


@pytest.fixture
def files(tmp_path):
    settings = Settings(_env_file=None, enable_file_transfers=True, artifact_root=tmp_path / "files",
                        artifact_public_base_url="https://files.example", artifact_link_signing_key="s" * 32,
                        task_api_token="synthetic-task-token", artifact_max_file_bytes=1024,
                        artifact_max_task_bytes=4096, artifact_max_storage_bytes=8192)
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    manager = ArtifactManager(settings, store)
    manager.initialize()
    yield manager, store, settings
    manager.close()


def session(manager, store):
    task_id = store.create("Transfer authorized fixture files", 20)
    assert store.claim_execution()["task_id"] == task_id
    return manager.task_session(task_id, lambda: None)


def ready(scope, payload=b"binary\x00content", purpose="output", name="video.mp4"):
    writer = scope.reserve(purpose=purpose, name=name)
    writer.write(payload)
    return writer.finish()


def capability(manager, task_id):
    item = manager.links(task_id)[0]
    query = parse_qs(urlsplit(item["download_url"]).query)
    return item, int(query["expires"][0]), query["signature"][0]


def test_verified_opaque_bytes_original_filename_and_signed_link(files):
    manager, store, _ = files
    scope = session(manager, store)
    payload = b"arbitrary software\x00\xff"
    metadata = ready(scope, payload, name="installer.exe")
    assert metadata["size_bytes"] == len(payload)
    assert metadata["sha256"] == hashlib.sha256(payload).hexdigest()
    path, _ = scope.resolve(metadata["id"])
    assert path.name == "installer.exe" and path.read_bytes() == payload
    item, expires, signature = capability(manager, scope.task_id)
    assert item["download_url"].startswith("https://files.example/task-artifacts/")
    leased, row, release = manager.download_lease(metadata["id"], expires, signature)
    assert leased == path and row["purpose"] == "output"
    assert str(path) not in str(item)
    release()
    release()
    assert not manager._leases


def test_inputs_are_not_published_and_other_tasks_cannot_resolve(files):
    manager, store, _ = files
    first = session(manager, store)
    input_file = ready(first, purpose="input", name="reference.wav")
    assert manager.links(first.task_id) == []
    second = session(manager, store)
    with pytest.raises(ArtifactError, match="this task"):
        second.resolve(input_file["id"])
    first.close()
    with pytest.raises(ArtifactError, match="Unknown"):
        manager.row(input_file["id"])


def test_failed_and_partial_transfers_cannot_get_links_and_release_quota(files):
    manager, store, _ = files
    scope = session(manager, store)
    writer = scope.reserve()
    writer.write(b"partial")
    assert manager.links(scope.task_id) == []
    with pytest.raises(ArtifactError, match="reserved"):
        writer.write(b"x" * 2048)
    writer.abort()
    assert manager.links(scope.task_id) == []
    with manager.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM file_artifacts").fetchone()[0] == 0


def test_completed_outputs_survive_failed_task_and_restart(files):
    manager, store, settings = files
    scope = session(manager, store)
    metadata = ready(scope)
    _, expires, signature = capability(manager, scope.task_id)
    store.finish(scope.task_id, TaskStatus.FAILED, result={"output": "Other steps were incomplete"})
    scope.close()
    manager.close()
    restarted = ArtifactManager(settings, TaskStore(store.path))
    restarted.initialize()
    try:
        path, _, release = restarted.download_lease(metadata["id"], expires, signature)
        assert path.read_bytes() == b"binary\x00content"
        release()
    finally:
        restarted.close()


def test_tampering_input_capability_and_wrong_expiry_are_rejected(files):
    manager, store, _ = files
    scope = session(manager, store)
    output = ready(scope)
    input_file = ready(scope, purpose="input")
    _, expires, signature = capability(manager, scope.task_id)
    for identifier, exp, sig in ((output["id"], expires, "0" * 64), (output["id"], expires + 1, signature),
                                 (input_file["id"], expires, signature), ("../outside", expires, signature)):
        with pytest.raises(ArtifactError):
            manager.download_lease(identifier, exp, sig)


def test_expiry_cleanup_waits_for_an_active_response_lease(files, monkeypatch):
    manager, store, _ = files
    scope = session(manager, store)
    metadata = ready(scope)
    _, expires, signature = capability(manager, scope.task_id)
    path, _, release = manager.download_lease(metadata["id"], expires, signature)
    scope.close()
    monkeypatch.setattr("app.artifacts.time.time", lambda: expires + 1)
    with pytest.raises(ArtifactError):
        manager.download_lease(metadata["id"], expires, signature)
    manager.cleanup()
    assert path.exists()
    release()
    manager.cleanup()
    assert not path.exists()


def test_atomic_quota_reservations_and_file_count(files):
    manager, store, settings = files
    settings.artifact_max_task_bytes = 1024
    settings.artifact_max_files_per_task = 1
    scope = session(manager, store)
    barrier = threading.Barrier(2)
    outcomes = []

    def reserve():
        barrier.wait()
        try:
            outcomes.append(scope.reserve())
        except ArtifactError:
            outcomes.append(None)

    threads = [threading.Thread(target=reserve) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)
    assert sum(item is not None for item in outcomes) == 1
    next(item for item in outcomes if item is not None).abort()
    assert scope.reserve().max_bytes == 1024


def test_native_import_uses_completed_file_and_preserves_bytes(files):
    manager, store, _ = files
    scope = session(manager, store)
    writer = scope.reserve()
    path = scope.browser_directory / "native-guid"
    path.write_bytes(b"completed bytes")
    metadata = scope.import_browser_file(path, "result.zip", writer)
    assert not path.exists()
    assert scope.resolve(metadata["id"])[0].read_bytes() == b"completed bytes"
    partial = scope.browser_directory / "unfinished.crdownload"
    partial.write_bytes(b"incomplete")
    with pytest.raises(ArtifactError):
        scope.import_browser_file(partial, "partial.zip", scope.reserve())
    assert len(manager.links(scope.task_id)) == 1


def test_paths_and_hard_link_escapes_are_rejected(files, tmp_path):
    manager, store, _ = files
    scope = session(manager, store)
    metadata = ready(scope)
    path, _ = scope.resolve(metadata["id"])
    try:
        os.link(path, tmp_path / "outside-link")
    except OSError:
        pytest.skip("Hard links are unavailable on this filesystem")
    with pytest.raises(ArtifactError, match="regular private"):
        scope.resolve(metadata["id"])
    with pytest.raises(ArtifactError):
        scope.resolve("../../outside")
    (tmp_path / "outside-link").unlink()


def test_reserved_files_are_recovered_without_publishing(files):
    manager, store, settings = files
    scope = session(manager, store)
    writer = scope.reserve()
    writer.write(b"unfinished")
    writer._handle.flush()
    writer._handle.close()
    writer._handle = None
    manager._sessions.clear()  # Simulate an interrupted process rather than orderly close.
    manager.close()
    restarted = ArtifactManager(settings, store)
    restarted.initialize()
    try:
        assert restarted.links(scope.task_id) == []
        with store.connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM file_artifacts").fetchone()[0] == 0
    finally:
        restarted.close()


def test_access_log_filter_redacts_encoded_and_plain_signatures():
    for query in ("signature=" + "a" * 64, "sign%61ture=" + "a" * 64):
        record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                                   ("client", "GET", "/task-artifacts/id/download?expires=123&" + query, "1.1", 200), None)
        ArtifactAccessLogFilter().filter(record)
        assert "a" * 64 not in record.getMessage()
        assert "REDACTED" in record.getMessage()
