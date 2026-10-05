"""Application-owned desktop sessions and safe task/manual ownership handoff."""
from __future__ import annotations

import threading
import time
from uuid import uuid4

from app.browser_runtime import browser_session
from app.task_context import TaskContext


class SessionConflict(RuntimeError):
    pass


class BrowserSessionManager:
    def __init__(self, settings, viewer, profiles, *, runtime=browser_session):
        self.settings, self.viewer, self.profiles = settings, viewer, profiles
        self.runtime = runtime
        self.lock = threading.RLock()
        self.state = "idle"
        self.owner = self.profile_id = self.generation = self.task_id = None
        self.context = None
        self.expires_at = None
        self.last_seen = 0
        self.error = None
        self.worker = None
        self._closed = threading.Event()
        self._close_manual = threading.Event()
        self._manual_thread = None
        self._transition_thread = None
        self._monitor = threading.Thread(target=self._watch, name="browser-sessions", daemon=True)

    def start(self):
        self._monitor.start()

    def reserve_task(self):
        """Reserve before SQLite claim/budget start, atomically with manual opens."""
        with self.lock:
            if self._closed.is_set() or self.state not in {"idle", "error"}:
                return False
            self.state, self.error = "task", None
            return True

    def claim_task(self, store):
        """Make queue claim and ownership one atomic operation, without idle churn."""
        with self.lock:
            if self._closed.is_set() or self.state not in {"idle", "error"}:
                return None
            task = store.claim_execution()
            if task:
                self.state, self.error = "task", None
            return task

    def bind_task(self, task_id, context):
        with self.lock:
            self.task_id, self.context = task_id, context
            self.profile_id = context.browser_profile_id if context else None
            self.generation = uuid4().hex

    def release_task(self):
        with self.lock:
            self.state = "idle"
            self.owner = self.profile_id = self.generation = self.task_id = self.context = None
            self.expires_at = None
        self._notify()

    def _notify(self):
        if self.worker:
            self.worker.notify()

    def heartbeat(self, owner, *, connection=False):
        with self.lock:
            # A live authenticated VNC connection, not merely polling status,
            # extends disconnected grace after manual readiness.
            if owner == self.owner and (connection or self.state == "opening"):
                self.last_seen = time.monotonic()

    def status(self, owner):
        with self.lock:
            context = self.context
            state = {
                "state": self.state, "profile_id": self.profile_id,
                "generation": self.generation, "task_id": self.task_id,
                "is_owner": owner == self.owner and self.owner is not None,
                "remaining_seconds": max(0, int(self.expires_at - time.monotonic())) if self.expires_at else None,
                "manual_limit_seconds": self.settings.manual_browser_seconds,
                "task_manual_limit_seconds": self.settings.task_manual_seconds,
                "error": self.error,
            }
        if context and state["state"] == "task":
            with context.control.condition:
                control = context.control
                state["control"] = control.state
                state["is_owner"] = control.owner == owner and control.owner is not None
                state["remaining_seconds"] = max(0, int(control.expires_at - time.monotonic())) if control.expires_at else None
                state["can_pause"] = bool(control.transition and control.state == "agent")
        return state

    def open(self, owner, profile_id):
        if not self.viewer.authenticate(owner):
            raise SessionConflict("Viewer session expired")
        self.profiles.get(profile_id)
        with self.lock:
            if self._closed.is_set() or self.state not in {"idle", "error"}:
                raise SessionConflict("Browser runtime is busy; close manual browsing or use task manual control")
            self.state, self.error = "opening", None
            self.owner, self.profile_id, self.generation = owner, profile_id, uuid4().hex
            self.expires_at = min(time.monotonic() + self.settings.manual_browser_seconds,
                                  self.viewer.session_deadline(owner))
            self.last_seen = time.monotonic()
            self._close_manual = threading.Event()
            context = TaskContext(browser_profile_id=profile_id)
            self.context = context
            self._manual_thread = threading.Thread(target=self._manual, args=(context, owner), name="manual-browser", daemon=True)
            self._manual_thread.start()
        return self.status(owner)

    def _manual(self, context, owner):
        error = None
        try:
            with self.runtime(self.settings, context, self.expires_at, owner=owner, interactive=True):
                with self.lock:
                    if not self._close_manual.is_set() and not self._closed.is_set():
                        self.state = "manual"
                self._close_manual.wait(max(0, self.expires_at - time.monotonic()))
            if any(event["tool"] == "cleanup" and event["outcome"] == "failed" for event in context.observations()):
                error = "Manual browser cleanup could not be confirmed; profile state may not have fully flushed"
        except Exception as exc:
            if not self._close_manual.is_set():
                from app.browser_profiles import ProfileBusy
                error = ("Selected browser profile is already in use; close its other browser before retrying"
                         if isinstance(exc, ProfileBusy) else
                         "Manual browser could not start or close safely; check local runtime prerequisites")
        finally:
            with self.lock:
                self.state = "error" if error else "idle"
                self.error = error
                self.owner = self.profile_id = self.generation = self.context = None
                self.expires_at = None
            self._notify()

    def close_manual(self, owner, generation):
        with self.lock:
            if owner != self.owner or generation != self.generation or self.state not in {"opening", "manual", "closing"}:
                raise SessionConflict("Manual browser ownership or generation changed")
            opening_context = self.context if self.state == "opening" else None
            self.state = "closing"
            self._close_manual.set()
        self._retire_input()
        if opening_context:
            opening_context.cancel()
        return self.status(owner)

    def _retire_input(self):
        _, generation = self.viewer.status()
        if generation:
            self.viewer.stop_display(generation)

    def owner_gone(self, owner):
        with self.lock:
            if owner != self.owner:
                return
            context, state = self.context, self.state
            if state in {"opening", "manual", "closing"}:
                self.state = "closing"
                self._close_manual.set()
        self._retire_input()
        if state in {"task", "opening"} and context:
            context.cancel()

    def control_task(self, owner, task_id, generation, *, resume=False):
        if not self.viewer.authenticate(owner):
            raise SessionConflict("Viewer session expired")
        # The worker's active lock is the authoritative task identity.
        if self.worker is None:
            raise SessionConflict("Task worker is unavailable")
        with self.worker.active_lock:
            context = self.worker.active_context
            if self.worker.active_task_id != task_id or context is None:
                raise SessionConflict("Task is no longer active")
        with self.lock:
            if self.state != "task" or self.task_id != task_id or self.generation != generation or self.context is not context:
                raise SessionConflict("Task generation changed")
        control = context.control
        with control.condition:
            context.check_alive()
            with self.lock:
                if self.generation != generation or self.context is not context:
                    raise SessionConflict("Task generation changed")
            if resume:
                if control.owner != owner or control.state != "manual":
                    raise SessionConflict("Task is not in your manual control")
                control.state = "resuming"
            else:
                if control.state in {"pause_requested", "manual"} and control.owner == owner:
                    return self.status(owner)
                if control.state != "agent" or control.transition is None:
                    raise SessionConflict("Task cannot take manual control at this point")
                control.owner = owner
                control.state = "pause_requested"
            with self.lock:
                self.owner = owner
                self.last_seen = time.monotonic()
            self._transition_thread = threading.Thread(target=self._handoff, args=(context, owner, resume), name="task-handoff", daemon=True)
            self._transition_thread.start()
        return self.status(owner)

    def _handoff(self, context, owner, resume):
        control = context.control
        try:
            with control.condition:
                while control.active:
                    context.check_alive()
                    control.condition.wait(0.1)
                context.check_alive()
                if not self.viewer.authenticate(owner) or self._closed.is_set():
                    raise RuntimeError("Manual owner is unavailable")
                if resume:
                    # Input is revoked and held keys reset BEFORE automation wakes.
                    control.transition(None)
                    control.observe()
                    if control.budget:
                        control.budget.resume()
                    control.epoch += 1
                    control.owner = control.expires_at = None
                    with self.lock:
                        self.owner = None
                        self.generation = uuid4().hex
                    control.state = "agent"
                else:
                    control.transition(owner)
                    context.check_alive()
                    if control.budget:
                        control.budget.freeze()
                    control.expires_at = min(time.monotonic() + self.settings.task_manual_seconds,
                                             self.viewer.session_deadline(owner))
                    if context.credential_expires_at is not None:
                        control.expires_at = min(control.expires_at,
                            time.monotonic() + max(0, context.credential_expires_at - time.time()))
                    with self.lock:
                        self.generation = uuid4().hex
                    control.state = "manual"
                control.condition.notify_all()
        except Exception:
            with control.condition:
                control.state = "error"
                control.condition.notify_all()
            self._retire_input()
            context.cancel()  # Never silently resume after timeout/failed handoff.

    def _watch(self):
        while not self._closed.wait(0.25):
            with self.lock:
                owner, context, state = self.owner, self.context, self.state
                expired = bool(owner and (not self.viewer.authenticate(owner)
                    or time.monotonic() - self.last_seen > self.settings.manual_disconnected_grace_seconds
                    or (self.expires_at and time.monotonic() >= self.expires_at)))
            if context and state == "task":
                with context.control.condition:
                    if context.control.state in {"pause_requested", "manual", "resuming"}:
                        expired = expired or bool(context.control.expires_at and time.monotonic() >= context.control.expires_at)
                        expired = expired or bool(context.credential_expires_at and time.time() >= context.credential_expires_at)
            if expired:
                self.owner_gone(owner)

    def close(self):
        self._closed.set()
        with self.lock:
            self._close_manual.set()
            context = self.context if self.state in {"task", "opening"} else None
        self._retire_input()
        if context:
            context.cancel()
        for thread in (self._manual_thread, self._transition_thread, self._monitor):
            if thread and thread.is_alive() and thread is not threading.current_thread():
                thread.join(timeout=15)
