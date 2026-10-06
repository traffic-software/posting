import json
import socket
import time
from datetime import datetime, timezone

import pytest

from app.config import Settings
from app.schemas import TaskRequest, TaskStatus, WorkflowSuccessCriterion
from app.selenium_tools import browser_tools
from app.storage import TaskStore
from app.task_context import TaskContext, decode_context, encode_context
from app.workflow_memory import candidate_data, eligible_workflow
from test_account_tasks import credential, PASSWORD
from test_login_forms import Driver, Element


PROFILE = "a" * 32
ORIGIN = "https://example.com"
CRITERION = WorkflowSuccessCriterion(origin=ORIGIN, selector="*:nth-child(1)", expected_text="Generation complete")
CANDIDATE = {"intent": "generate video", "origin": ORIGIN, "steps": ["Open the video workspace", "Enter the requested prompt", "Submit once and observe the completed result"], "prerequisites": ["Verify current signed-in state"]}


def context():
    return TaskContext(browser_profile_id=PROFILE, workflow_success_criteria=[CRITERION.model_copy(deep=True)])


def evidence():
    return [{"criterion": 0, "source": "visible_dom", "origin": ORIGIN,
             "expected_text": CRITERION.expected_text, "matched": True,
             "verified_at": datetime.now(timezone.utc).isoformat()}]


def finished(store, profile=PROFILE):
    request = TaskRequest(prompt="Generate video", browser_profile_id=profile, workflow_success_criteria=[CRITERION])
    options, _ = encode_context(request, Settings(_env_file=None))
    task = store.create(request.prompt, 5, context_json=options)
    store.claim_next()
    store.finish(task, TaskStatus.COMPLETED, result={"output": "Observed result"})
    return task


def test_criteria_context_roundtrip_and_cancellation_clears_workflow():
    settings = Settings(_env_file=None)
    request = TaskRequest(prompt="Generate video", browser_profile_id=PROFILE, workflow_success_criteria=[CRITERION])
    options, blob = encode_context(request, settings)
    restored = decode_context(options, blob, settings)
    assert restored.workflow_success_criteria == [CRITERION]
    restored.stage_workflow(CANDIDATE)
    restored.record_workflow_evidence(evidence())
    restored._workflow_terminal_verified = True
    assert eligible_workflow(restored) is not None
    restored.cancel()
    assert restored.workflow_state() == (None, [])
    assert not restored.workflow_success_criteria


def test_model_claim_and_missing_caller_criteria_cannot_promote():
    ctx = context()
    ctx.stage_workflow(CANDIDATE)
    ctx.record_observation("click_element", "returned", "Generation complete")
    assert eligible_workflow(ctx) is None
    ctx.record_workflow_evidence(evidence())
    ctx._workflow_terminal_verified = True
    ctx.workflow_success_criteria = []
    assert eligible_workflow(ctx) is None


@pytest.mark.parametrize("private", [PASSWORD, "Cookie: session=private", "person@example.com", "pyautogui.click(1,2)", "div:nth-child(1)", "data:image/png;base64,abcdef", "https://example.com/?token=private"])
def test_private_or_executable_workflow_is_rejected(private):
    ctx = TaskContext(credentials=[credential()])
    with pytest.raises(ValueError):
        candidate_data({**CANDIDATE, "steps": [private]}, ctx)


def test_storage_migration_restart_scope_deduplication_and_retention(tmp_path):
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    store.initialize()
    ctx = context()
    ctx.stage_workflow(CANDIDATE)
    ctx.record_workflow_evidence(evidence())
    ctx._workflow_terminal_verified = True
    data = eligible_workflow(ctx)
    task = finished(store)
    store.save_workflow(task, PROFILE, data)
    store.save_workflow(task, PROFILE, data)
    reopened = TaskStore(store.path)
    assert len(reopened.find_workflows(PROFILE, ORIGIN, "generate video")) == 1
    assert reopened.find_workflows("b" * 32, ORIGIN, "generate video") == []
    assert reopened.find_workflows(PROFILE, "https://other.example", "generate video") == []
    assert reopened.find_workflows(PROFILE, ORIGIN, "unrelated invoice") == []
    with store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0] == 1
        conn.execute("UPDATE workflows SET updated_at = '2000-01-01T00:00:00+00:00'")
    assert reopened.find_workflows(PROFILE, ORIGIN, "generate video") == []


def test_failed_and_cross_profile_tasks_cannot_save(tmp_path):
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    ctx = context()
    ctx.stage_workflow(CANDIDATE)
    ctx.record_workflow_evidence(evidence())
    ctx._workflow_terminal_verified = True
    data = eligible_workflow(ctx)
    task = store.create("failed task", 5)
    store.claim_next()
    store.finish(task, TaskStatus.FAILED, error="failed")
    with pytest.raises(ValueError, match="completed"):
        store.save_workflow(task, PROFILE, data)
    with pytest.raises(ValueError, match="profile"):
        store.save_workflow(finished(store, "b" * 32), PROFILE, data)


def bound(tmp_path, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.215.14", 443))])
    settings = Settings(_env_file=None, enable_workflow_memory=True)
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    settings._workflow_store = store
    driver = Driver()
    driver.current_url = ORIGIN + "/workspace"
    driver.element = Element("text", "p")
    driver.element.text = "Generation complete"
    driver.elements = [driver.element]
    original = driver.execute_script

    def script(code, *args):
        if "window===window.top" in code:
            return True
        return original(code, *args)

    monkeypatch.setattr(driver, "execute_script", script)
    ctx = context()
    return {item.name: item for item in browser_tools(driver, settings, time.monotonic() + 30, ctx)}, ctx, driver


def test_live_evidence_and_staged_candidate_are_not_immediately_saved(tmp_path, monkeypatch):
    tools, ctx, driver = bound(tmp_path, monkeypatch)
    assert "staged" in tools["remember_successful_workflow"].invoke(CANDIDATE)
    assert eligible_workflow(ctx) is None
    assert json.loads(tools["verify_workflow_outcome"].invoke({}))["verified"] is True
    assert eligible_workflow(ctx) is None  # Tool evidence is not terminal verification.
    ctx._workflow_terminal_verified = ctx._workflow_verifier()["verified"]
    assert eligible_workflow(ctx) is not None
    driver.element.text = "Processing"
    assert json.loads(tools["verify_workflow_outcome"].invoke({}))["verified"] is False
    assert eligible_workflow(ctx) is None


def test_missing_criteria_is_recoverable_and_does_not_stage(tmp_path, monkeypatch):
    tools, ctx, _ = bound(tmp_path, monkeypatch)
    ctx.workflow_success_criteria.clear()
    result = tools["remember_successful_workflow"].invoke(CANDIDATE)
    assert "no caller-supplied" in result
    assert ctx.workflow_state() == (None, [])


def test_unsafe_outcome_target_does_not_record_evidence(tmp_path, monkeypatch):
    tools, ctx, driver = bound(tmp_path, monkeypatch)
    original = driver.execute_script
    monkeypatch.setattr(driver, "execute_script", lambda code, *args: False if "window===window.top" in code else original(code, *args))
    result = json.loads(tools["verify_workflow_outcome"].invoke({}))
    assert not result["verified"] and ctx.workflow_state()[1] == []


@pytest.mark.parametrize("storage_fails", [False, True])
def test_worker_promotes_after_completion_and_memory_failure_is_nonfatal(tmp_path, monkeypatch, storage_fails):
    import threading
    from app.worker import TaskWorker

    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    settings = Settings(_env_file=None, enable_workflow_memory=True)
    request = TaskRequest(prompt="Generate video", browser_profile_id=PROFILE, workflow_success_criteria=[CRITERION])
    options, _ = encode_context(request, settings)
    task_id = store.create(request.prompt, 5, context_json=options)
    saved = threading.Event()
    original = store.save_workflow

    def save(task, profile, data, **kwargs):
        assert store.get(task)["status"] == TaskStatus.COMPLETED
        try:
            if storage_fails:
                raise OSError("synthetic memory failure")
            return original(task, profile, data, **kwargs)
        finally:
            saved.set()

    def runner(prompt, config, ctx):
        ctx.stage_workflow(CANDIDATE)
        ctx.record_workflow_evidence(evidence())
        ctx._workflow_terminal_verified = True
        return {"output": "Observed result"}

    monkeypatch.setattr(store, "save_workflow", save)
    worker = TaskWorker(store, settings, runner)
    worker.start()
    try:
        assert saved.wait(5)
        assert store.get(task_id)["status"] == TaskStatus.COMPLETED
        assert bool(store.find_workflows(PROFILE, ORIGIN, "generate video")) is not storage_fails
    finally:
        worker.stop()


def test_initial_hints_only_reuse_same_profile_and_origin(tmp_path):
    from app.agent import workflow_hints
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    ctx = context()
    ctx.stage_workflow(CANDIDATE)
    ctx.record_workflow_evidence(evidence())
    ctx._workflow_terminal_verified = True
    store.save_workflow(finished(store), PROFILE, eligible_workflow(ctx))
    settings = Settings(_env_file=None, enable_workflow_memory=True)
    settings._workflow_store = store
    assert workflow_hints("Generate video at https://example.com/workspace", settings, ctx)
    assert not workflow_hints("Generate video at https://other.example/workspace", settings, TaskContext(browser_profile_id=PROFILE))
    assert not workflow_hints("Generate video at https://example.com/workspace", settings, TaskContext(browser_profile_id="b" * 32))
