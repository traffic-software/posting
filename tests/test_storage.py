from app.schemas import TaskStatus
from app.storage import QueueFullError, TaskStore


def test_lifecycle_and_persistence(tmp_path):
    path = tmp_path / "tasks.db"
    store = TaskStore(path)
    store.initialize()
    task_id = store.create("Get the page title", 1)
    assert store.get(task_id)["status"] == TaskStatus.PENDING
    assert store.claim_next() == (task_id, "Get the page title")
    assert store.claim_next() is None
    assert store.get(task_id)["status"] == TaskStatus.PROCESSING
    store.finish(task_id, TaskStatus.COMPLETED, result={"output": "Example"})
    assert TaskStore(path).get(task_id)["result"] == {"output": "Example"}
    assert store.get(task_id)["error"] is None


def test_capacity_is_atomic_and_recovered_tasks_are_not_retried(tmp_path):
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    first = store.create("First", 2)
    second = store.create("Second", 2)
    try:
        store.create("Third", 2)
        assert False, "Capacity should be enforced"
    except QueueFullError:
        pass
    assert store.claim_next() == (first, "First")
    assert store.recover_interrupted() == 1
    assert store.get(first)["status"] == TaskStatus.FAILED
    assert store.get(first)["error"] == "Task interrupted by application restart"
    assert store.claim_next() == (second, "Second")
    assert store.claim_next() is None


def test_failed_result_does_not_disappear(tmp_path):
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    task_id = store.create("Fail", 1)
    store.claim_next()
    store.finish(task_id, TaskStatus.FAILED, error="Task execution failed")
    assert TaskStore(store.path).get(task_id)["error"] == "Task execution failed"


def test_lifecycle_failures_include_persisted_explanations(tmp_path):
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    cancelled = store.create("cancel", 3)
    store.claim_next()
    store.cancel_processing(cancelled)
    interrupted = store.create("restart", 3)
    store.claim_next()
    store.recover_interrupted()
    expired = store.create("expire", 3, credential_blob="unused", credential_expires_at="2000-01-01T00:00:00Z")
    assert store.claim_next() is None
    reopened = TaskStore(store.path)
    for task_id, reason in [(cancelled, "shut down"), (interrupted, "restart"), (expired, "expired")]:
        record = reopened.get(task_id)
        assert record["status"] == TaskStatus.FAILED
        assert reason in record["result"]["output"]
        assert "not confirmed" in record["result"]["output"]
