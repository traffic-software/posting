import logging
import threading
from collections.abc import Callable

from app.agent import run_task
from app.config import Settings
from app.schemas import TaskStatus
from app.storage import TaskStore
from app.task_context import TaskContext, decode_context
from app.task_report import TaskExecutionFailure, failure_result, output_result

logger = logging.getLogger(__name__)


class TaskWorker:
    def __init__(self, store: TaskStore, settings: Settings, runner: Callable = run_task):
        self.store = store
        self.settings = settings
        self.runner = runner
        self.wakeup = threading.Event()
        self.stopping = threading.Event()
        self.active_lock = threading.Lock()
        self.active_task_id = None
        self.active_context = None
        self.thread = threading.Thread(target=self._loop, name="task-worker", daemon=True)

    def start(self) -> None:
        self.store.recover_interrupted()
        self.thread.start()
        self.notify()

    def notify(self) -> None:
        self.wakeup.set()

    def stop(self) -> None:
        self.stopping.set()
        self.notify()
        with self.active_lock:
            task_id, context = self.active_task_id, self.active_context
        if task_id is not None:
            try:
                self.store.cancel_processing(task_id)
            except Exception as exc:
                logger.error("Task shutdown cleanup failed (%s)", type(exc).__name__)
        if context is not None:
            try:
                context.cancel()
            except Exception as exc:
                logger.error("Browser shutdown failed (%s)", type(exc).__name__)
        self.thread.join(timeout=5)

    @property
    def alive(self) -> bool:
        return self.thread.is_alive() and not self.stopping.is_set()

    def _loop(self) -> None:
        while not self.stopping.is_set():
            try:
                with self.active_lock:
                    if self.stopping.is_set():
                        break
                    task = self.store.claim_execution()
                    self.active_task_id = task["task_id"] if task else None
                if task is None:
                    self.wakeup.wait(timeout=2)
                    self.wakeup.clear()
                    continue
                task_id, prompt = task["task_id"], task["prompt"]
                context = None
                try:
                    context = decode_context(task["context_json"], task["credential_blob"], self.settings)
                    if context is None and self.runner is run_task:
                        context = TaskContext()
                    with self.active_lock:
                        self.active_context = context
                        stopped = self.stopping.is_set()
                    if stopped:
                        if context is not None:
                            context.cancel()
                        raise RuntimeError("Task cancelled")
                    if context is not None:
                        result = context.redacted_result(self.runner(prompt, self.settings, context))
                    else:
                        result = self.runner(prompt, self.settings)
                    if self.stopping.is_set():
                        self.store.cancel_processing(task_id)
                    else:
                        self.store.finish(task_id, TaskStatus.COMPLETED, result=result)
                except Exception as exc:
                    if self.stopping.is_set():
                        self.store.cancel_processing(task_id)
                    else:
                        logger.error("Task %s failed (%s)", task_id, type(exc).__name__)
                        report = exc.result if isinstance(exc, TaskExecutionFailure) else failure_result()
                        if context is not None:
                            report = context.redacted_result(report)
                        report = output_result(report["output"])
                        self.store.finish(task_id, TaskStatus.FAILED, result=report, error="Task execution failed")
                finally:
                    if context is not None:
                        context.clear_sensitive_state()
                    with self.active_lock:
                        self.active_context = None
                        self.active_task_id = None
                    task = None
            except Exception as exc:
                logger.error("Task worker could not access task storage (%s)", type(exc).__name__)
                self.wakeup.wait(timeout=2)
                self.wakeup.clear()
