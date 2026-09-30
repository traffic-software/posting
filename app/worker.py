import logging
import threading
from collections.abc import Callable

from app.agent import run_task
from app.config import Settings
from app.schemas import TaskStatus
from app.storage import TaskStore

logger = logging.getLogger(__name__)


class TaskWorker:
    def __init__(self, store: TaskStore, settings: Settings, runner: Callable = run_task):
        self.store = store
        self.settings = settings
        self.runner = runner
        self.wakeup = threading.Event()
        self.stopping = threading.Event()
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
        self.thread.join(timeout=5)

    @property
    def alive(self) -> bool:
        return self.thread.is_alive() and not self.stopping.is_set()

    def _loop(self) -> None:
        while not self.stopping.is_set():
            try:
                task = self.store.claim_next()
                if task is None:
                    self.wakeup.wait(timeout=2)
                    self.wakeup.clear()
                    continue
                task_id, prompt = task
                try:
                    result = self.runner(prompt, self.settings)
                    self.store.finish(task_id, TaskStatus.COMPLETED, result=result)
                except Exception as exc:
                    logger.error("Task %s failed (%s)", task_id, type(exc).__name__)
                    self.store.finish(task_id, TaskStatus.FAILED, error="Task execution failed")
            except Exception as exc:
                logger.error("Task worker could not access task storage (%s)", type(exc).__name__)
                self.wakeup.wait(timeout=2)
                self.wakeup.clear()
