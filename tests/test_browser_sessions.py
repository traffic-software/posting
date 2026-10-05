import os
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.browser_profiles import BrowserProfileStore
from app.browser_sessions import BrowserSessionManager, SessionConflict
from app.config import Settings
from app.display_viewer import DisplayViewer, _Display, create_router
from app.storage import TaskStore
from app.task_context import ExecutionBudget, TaskContext, encode_context
from app.schemas import TaskRequest
from app.worker import TaskWorker

ORIGIN = "http://127.0.0.1:8001"
pytestmark = pytest.mark.skipif(os.name != "posix", reason="Session filesystem-lease tests require Linux")


def until(predicate, seconds=3):
    end = time.monotonic() + seconds
    while not predicate():
        assert time.monotonic() < end
        time.sleep(0.01)


@pytest.fixture
def environment(tmp_path):
    settings = Settings(_env_file=None, database_path=tmp_path / "tasks.db",
        browser_profiles_root=tmp_path / "profiles", display_viewer_enabled=True,
        display_viewer_token="synthetic-token", display_viewer_origin=ORIGIN)
    viewer = DisplayViewer(settings)
    profiles = BrowserProfileStore(settings.browser_profiles_root)
    events = []

    @contextmanager
    def runtime(settings, context, deadline, **kwargs):
        with profiles.lease(context.browser_profile_id):
            events.append(("open", kwargs))
            yield SimpleNamespace()
            events.append(("close", {}))

    manager = BrowserSessionManager(settings, viewer, profiles, runtime=runtime)
    settings._browser_sessions = manager
    owner = viewer.issue_session("owner", "synthetic-token")
    other = viewer.issue_session("other", "synthetic-token")
    profile = profiles.create("A")
    manager.start()
    yield settings, viewer, profiles, manager, owner, other, profile, events
    manager.close()
    viewer.close()


def test_open_close_double_click_ownership_and_lease_release(environment):
    _, _, profiles, manager, owner, other, profile, events = environment
    result = manager.open(owner, profile["id"])
    generation = result["generation"]
    until(lambda: manager.state == "manual")
    assert events[0][1]["interactive"] is True
    with pytest.raises(SessionConflict, match="busy"):
        manager.open(owner, profile["id"])
    with pytest.raises(SessionConflict):
        manager.close_manual(other, generation)
    with pytest.raises(SessionConflict):
        manager.close_manual(owner, "stale")
    manager.close_manual(owner, generation)
    until(lambda: manager.state == "idle")
    with profiles.lease(profile["id"]):
        pass
    assert [event[0] for event in events] == ["open", "close"]


def test_start_failure_is_visible_and_runtime_reservation_released(environment):
    _, _, _, manager, owner, _, profile, _ = environment
    @contextmanager
    def failure(*args, **kwargs):
        raise RuntimeError("private runtime details")
        yield
    manager.runtime = failure
    manager.open(owner, profile["id"])
    until(lambda: manager.state == "error")
    assert "private" not in manager.status(owner)["error"]
    assert manager.reserve_task()
    manager.release_task()


@pytest.mark.parametrize("cause", ["logout", "expiry", "disconnect", "timeout", "shutdown"])
def test_manual_owner_lifecycle_closes_browser(environment, cause):
    _, viewer, _, manager, owner, _, profile, events = environment
    manager.open(owner, profile["id"])
    until(lambda: manager.state == "manual")
    if cause == "logout":
        viewer.revoke(owner)
        manager.owner_gone(owner)
    elif cause == "expiry":
        viewer._sessions[owner].expires_at = 0
    elif cause == "disconnect":
        manager.last_seen = 0
    elif cause == "timeout":
        manager.expires_at = time.monotonic() - 1
    else:
        manager.close()
    until(lambda: manager.state == "idle")
    assert events[-1][0] == "close"


def test_queued_task_stays_pending_without_execution_budget_and_close_wakes_worker(environment):
    settings, _, _, manager, owner, _, profile, _ = environment
    store = TaskStore(settings.database_path)
    store.initialize()
    called = threading.Event()
    def runner(prompt, settings, context):
        assert context.browser_profile_id == profile["id"]
        called.set()
        return {"output": "synthetic"}
    worker = TaskWorker(store, settings, runner=runner)
    manager.worker = worker
    manager.open(owner, profile["id"])
    until(lambda: manager.state == "manual")
    options, blob = encode_context(TaskRequest(prompt="test", browser_profile_id=profile["id"]), settings)
    task_id = store.create("test", 5, context_json=options, credential_blob=blob)
    worker.start()
    try:
        time.sleep(0.15)
        assert not called.is_set()
        assert store.get(task_id)["status"] == "PENDING"
        assert worker.active_context is None
        manager.close_manual(owner, manager.generation)
        assert called.wait(2)
        until(lambda: store.get(task_id)["status"] == "COMPLETED")
    finally:
        worker.stop()


def task_environment(environment):
    settings, _, _, manager, owner, other, profile, _ = environment
    context = TaskContext(browser_profile_id=profile["id"])
    context.control.budget = ExecutionBudget(30)
    transitions = []
    context.control.transition = lambda who: transitions.append(("mode", who))
    context.control.observe = lambda: transitions.append(("observation", None))
    manager.worker = SimpleNamespace(active_lock=threading.Lock(), active_task_id="task", active_context=context,
                                   notify=lambda: None)
    assert manager.reserve_task()
    manager.bind_task("task", context)
    return settings, manager, owner, other, context, transitions


def test_pause_waits_complete_action_freezes_budget_and_resume_observes_before_release(environment):
    _, manager, owner, other, context, transitions = task_environment(environment)
    entered, release, completed = threading.Event(), threading.Event(), threading.Event()
    def tool():
        with context.control.action(context):
            entered.set()
            release.wait(3)
        completed.set()
    thread = threading.Thread(target=tool)
    thread.start()
    assert entered.wait(1)
    original = context.control.budget.deadline
    manager.control_task(owner, "task", manager.generation)
    assert context.control.state == "pause_requested"
    time.sleep(0.05)
    assert not transitions
    release.set()
    assert completed.wait(1)
    until(lambda: context.control.state == "manual")
    time.sleep(0.08)
    assert context.control.budget.deadline > original + 0.07
    blocked = threading.Event()
    def pending_tool():
        with context.control.action(context):
            assert transitions[-1][0] == "observation"
            blocked.set()
    pending = threading.Thread(target=pending_tool)
    pending.start()
    time.sleep(0.05)
    assert not blocked.is_set()
    with pytest.raises(SessionConflict):
        manager.control_task(other, "task", manager.generation, resume=True)
    with pytest.raises(SessionConflict):
        manager.control_task(owner, "task", "stale", resume=True)
    manager.control_task(owner, "task", manager.generation, resume=True)
    assert blocked.wait(2)
    thread.join(1)
    pending.join(1)
    assert transitions == [("mode", owner), ("mode", None), ("observation", None)]
    assert context.control.epoch == 1
    assert context.control.state == "agent"
    manager.release_task()


@pytest.mark.parametrize("cause", ["manual_timeout", "credential_expiry", "owner_expiry", "transition_failure"])
def test_task_handoff_failure_and_expiry_cancel_never_resume(environment, cause):
    _, manager, owner, _, context, transitions = task_environment(environment)
    if cause == "transition_failure":
        def failure(owner):
            raise RuntimeError()
        context.control.transition = failure
    manager.control_task(owner, "task", manager.generation)
    if cause == "transition_failure":
        until(context.cancelled.is_set)
    else:
        until(lambda: context.control.state == "manual")
        if cause == "manual_timeout":
            context.control.expires_at = time.monotonic() - 1
        elif cause == "credential_expiry":
            context.credential_expires_at = time.time() - 1
        else:
            manager.viewer._sessions[owner].expires_at = 0
        until(context.cancelled.is_set)
    assert context.control.state != "agent"
    assert not any(event[0] == "observation" for event in transitions)
    manager.release_task()


def test_profile_and_control_api_auth_origin_body_limits_and_ui_escape(environment):
    _, viewer, profiles, manager, _, _, _, _ = environment
    app = FastAPI()
    app.include_router(create_router(viewer, manager, profiles))
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.post("/desktop/profiles", headers={"Origin": ORIGIN}, json={"label": "A"}).status_code == 401
        assert client.post("/desktop/login", headers={"Origin": ORIGIN}, json={"token": "synthetic-token"}).status_code == 200
        assert client.post("/desktop/profiles", json={"label": "A"}).status_code == 404
        assert client.post("/desktop/profiles", headers={"Origin": ORIGIN + ".bad"}, json={"label": "A"}).status_code == 404
        headers = {"Origin": ORIGIN}
        made = client.post("/desktop/profiles", headers=headers, json={"label": "<script>synthetic</script>"})
        assert made.status_code == 200
        pid = made.json()["profile"]["id"]
        listed = client.post("/desktop/profiles/list", headers=headers, json={}).json()["profiles"]
        assert len(listed) == 2
        assert all(set(p) == {"id", "label", "created_at", "updated_at"} for p in listed)
        assert client.post("/desktop/profiles", headers=headers, json={"label": "A", "path": "/tmp/arbitrary"}).status_code == 422
        assert client.post("/desktop/profiles", headers=headers, content=b"x" * 4097).status_code == 422
        opened = client.post("/desktop/browser/open", headers=headers, json={"browser_profile_id": pid})
        assert opened.status_code == 200
        until(lambda: manager.state == "manual")
        assert client.post("/desktop/browser/open", headers=headers, json={"browser_profile_id": pid}).status_code == 409
        assert client.post("/desktop/browser/close", headers=headers, json={"generation": "old"}).status_code == 409
        assert client.post("/desktop/browser/close", headers=headers, json={"generation": opened.json()["generation"]}).status_code == 200
        until(lambda: manager.state == "idle")
        js = client.get("/desktop/static/viewer.js").text
        assert "new Option(profile.label, profile.id)" in js and "innerHTML" not in js


def test_interactive_generation_is_owner_only_and_readonly_is_observable(environment):
    _, viewer, _, _, owner, other, _, _ = environment
    process = SimpleNamespace(poll=lambda: None)
    viewer._display = _Display("manual", ":99", 5900, process, True, owner)
    assert viewer.connection_authorized(owner, "manual")
    assert not viewer.connection_authorized(other, "manual")
    assert not viewer.connection_authorized(owner, "stale")
    assert viewer.mode(owner)["input_allowed"]
    viewer._display = _Display("agent", ":99", 5900, process)
    assert viewer.connection_authorized(other, "agent")
    assert not viewer.mode(owner)["input_allowed"]
    viewer._display = None


def test_idle_worker_does_not_self_wake_or_publish_fake_busy_state(environment):
    settings, _, _, manager, owner, _, profile, _ = environment
    store = TaskStore(settings.database_path)
    store.initialize()
    calls = []
    original = store.claim_execution
    def claim():
        calls.append(True)
        return original()
    store.claim_execution = claim
    worker = TaskWorker(store, settings, runner=lambda *args: {})
    manager.worker = worker
    worker.start()
    try:
        time.sleep(.15)
        assert manager.state == "idle" and len(calls) <= 2
        manager.open(owner, profile["id"])
        until(lambda: manager.state == "manual")
    finally:
        worker.stop()


def test_budget_freezes_only_acknowledged_time_and_keeps_finite_expiry(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("app.task_context.time.monotonic", lambda: clock[0])
    budget = ExecutionBudget(20)
    assert budget.deadline == 120
    clock[0] = 105
    assert budget - clock[0] == 15
    budget.freeze()
    clock[0] = 300
    assert budget - clock[0] == 15
    budget.resume()
    assert budget.deadline == 315
    clock[0] = 316
    context = TaskContext()
    context.control.budget = budget
    with pytest.raises(TimeoutError):
        context.check_alive()


def test_closing_during_opening_cancels_late_startup_and_releases_ownership(environment):
    _, _, _, manager, owner, _, profile, _ = environment
    entered = threading.Event()
    @contextmanager
    def slow(settings, context, deadline, **kwargs):
        entered.set()
        until(context.cancelled.is_set)
        raise RuntimeError("Opening cancelled")
        yield
    manager.runtime = slow
    result = manager.open(owner, profile["id"])
    assert entered.wait(1)
    manager.close_manual(owner, result["generation"])
    until(lambda: manager.state == "idle")
    assert manager.error is None


def test_session_countdown_uses_earliest_viewer_expiry(environment):
    _, viewer, _, manager, owner, _, profile, _ = environment
    viewer._sessions[owner].expires_at = time.monotonic() + 70
    manager.open(owner, profile["id"])
    until(lambda: manager.state == "manual")
    assert 0 < manager.status(owner)["remaining_seconds"] <= 70


def test_failed_resume_revokes_input_and_cancels_task(environment):
    _, manager, owner, _, context, transitions = task_environment(environment)
    manager.control_task(owner, "task", manager.generation)
    until(lambda: context.control.state == "manual")
    def failure(owner):
        raise RuntimeError("Synthetic backend failure")
    context.control.transition = failure
    manager.control_task(owner, "task", manager.generation, resume=True)
    until(context.cancelled.is_set)
    assert context.control.state == "error"
    assert context.control.epoch == 0
    assert not any(e[0] == "observation" for e in transitions)
    manager.release_task()


def test_model_and_builtin_tool_dispatch_wait_for_resume_and_receive_fresh_observation(environment):
    from app.agent import ControlMiddleware
    _, manager, owner, _, context, _ = task_environment(environment)
    middleware = ControlMiddleware(context)
    messages = []
    request = SimpleNamespace(messages=[], override=lambda **kwargs: SimpleNamespace(**kwargs))
    context.control.observe = lambda: context.record_observation("resume", "returned", "Fresh synthetic selectors")
    manager.control_task(owner, "task", manager.generation)
    until(lambda: context.control.state == "manual")
    model_called, tool_called = threading.Event(), threading.Event()
    def model_handler(request):
        messages.extend(request.messages)
        model_called.set()
        return "synthetic"
    model = threading.Thread(target=lambda: middleware.wrap_model_call(request, model_handler))
    tool = threading.Thread(target=lambda: middleware.wrap_tool_call(request, lambda _: tool_called.set()))
    model.start()
    tool.start()
    time.sleep(.1)
    assert not model_called.is_set() and not tool_called.is_set()
    manager.control_task(owner, "task", manager.generation, resume=True)
    assert model_called.wait(2) and tool_called.wait(2)
    model.join(1)
    tool.join(1)
    assert "Fresh synthetic selectors" in messages[-1].content
    assert "Previous page targets are stale" in messages[-1].content
    manager.release_task()


def test_polling_alone_does_not_extend_manual_disconnected_grace(environment):
    _, _, _, manager, owner, _, profile, _ = environment
    manager.open(owner, profile["id"])
    until(lambda: manager.state == "manual")
    before = manager.last_seen
    time.sleep(.02)
    manager.heartbeat(owner)
    assert manager.last_seen == before
    manager.heartbeat(owner, connection=True)
    assert manager.last_seen > before


def test_stale_control_generations_and_repeated_requests(environment):
    _, manager, owner, _, context, _ = task_environment(environment)
    initial = manager.generation
    manager.control_task(owner, "task", initial)
    until(lambda: context.control.state == "manual")
    manual = manager.generation
    assert initial != manual
    with pytest.raises(SessionConflict, match="generation"):
        manager.control_task(owner, "task", initial)
    assert manager.control_task(owner, "task", manual)["control"] == "manual"
    manager.control_task(owner, "task", manual, resume=True)
    until(lambda: context.control.state == "agent")
    assert manager.generation not in {initial, manual}
    with pytest.raises(SessionConflict, match="generation"):
        manager.control_task(owner, "task", initial)
    with pytest.raises(SessionConflict, match="generation"):
        manager.control_task(owner, "task", manual, resume=True)
    manager.release_task()


def test_default_viewer_credential_covers_nominal_standalone_lifetime():
    settings = Settings(_env_file=None)
    assert settings.manual_browser_seconds == 1800
    assert settings.display_viewer_session_seconds >= settings.manual_browser_seconds
    assert settings.task_manual_seconds == 600
