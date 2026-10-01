import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.schemas import TaskStatus
from app.task_report import failure_result


class QueueFullError(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=10000")
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
            for name in ("context_json", "credential_blob", "credential_expires_at"):
                if name not in columns:
                    conn.execute(f"ALTER TABLE tasks ADD COLUMN {name} TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at)")

    def create(
        self, prompt: str, max_active: int, *, context_json: str | None = None,
        credential_blob: str | None = None, credential_expires_at: str | None = None,
    ) -> str:
        task_id = str(uuid4())
        now = utc_now()
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            active = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status IN (?, ?)",
                (TaskStatus.PENDING, TaskStatus.PROCESSING),
            ).fetchone()[0]
            if active >= max_active:
                raise QueueFullError()
            conn.execute(
                """INSERT INTO tasks (task_id, prompt, status, created_at, updated_at,
                   context_json, credential_blob, credential_expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_id, prompt, TaskStatus.PENDING, now, now, context_json, credential_blob, credential_expires_at),
            )
        return task_id

    def get(self, task_id: str) -> dict | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT task_id, status, result_json, error, created_at, updated_at FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        raw_result = result.pop("result_json")
        result["result"] = json.loads(raw_result) if raw_result else None
        return result

    def claim_next(self) -> tuple[str, str] | None:
        record = self.claim_execution()
        return (record["task_id"], record["prompt"]) if record else None

    def claim_execution(self) -> dict | None:
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """UPDATE tasks SET status = ?, error = ?, result_json = ?, credential_blob = NULL,
                   credential_expires_at = NULL, updated_at = ?
                   WHERE status = ? AND credential_expires_at <= ?""",
                (TaskStatus.FAILED, "Task credentials expired", json.dumps(failure_result("Queued task credentials expired before execution.")), utc_now(), TaskStatus.PENDING, utc_now()),
            )
            row = conn.execute(
                """SELECT task_id, prompt, context_json, credential_blob FROM tasks
                   WHERE status = ? ORDER BY created_at, rowid LIMIT 1""",
                (TaskStatus.PENDING,),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ? AND status = ?",
                (TaskStatus.PROCESSING, utc_now(), row["task_id"], TaskStatus.PENDING),
            )
            return dict(row)

    def finish(self, task_id: str, status: TaskStatus, *, result: dict | None = None, error: str | None = None) -> None:
        if status not in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            raise ValueError("Invalid final status")
        data = json.dumps(result, ensure_ascii=False) if result is not None else None
        if data and len(data.encode("utf-8")) > 8192:
            raise ValueError("Task result exceeds storage limit")
        with self.connection() as conn:
            updated = conn.execute(
                """UPDATE tasks SET status = ?, result_json = ?, error = ?, updated_at = ?,
                   credential_blob = NULL, credential_expires_at = NULL
                   WHERE task_id = ? AND status = ?""",
                (status, data, error, utc_now(), task_id, TaskStatus.PROCESSING),
            )
            if updated.rowcount != 1:
                raise ValueError("Task is not processing")

    def cancel_processing(self, task_id: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """UPDATE tasks SET status = ?, error = ?, result_json = ?, updated_at = ?,
                   credential_blob = NULL, credential_expires_at = NULL
                   WHERE task_id = ? AND status = ?""",
                (TaskStatus.FAILED, "Task cancelled by application shutdown", json.dumps(failure_result("The application shut down and cancelled execution.")), utc_now(), task_id, TaskStatus.PROCESSING),
            )

    def recover_interrupted(self) -> int:
        with self.connection() as conn:
            updated = conn.execute(
                """UPDATE tasks SET status = ?, error = ?, result_json = ?, updated_at = ?,
                   credential_blob = NULL, credential_expires_at = NULL
                   WHERE status = ?""",
                (TaskStatus.FAILED, "Task interrupted by application restart", json.dumps(failure_result("An application restart interrupted execution.")), utc_now(), TaskStatus.PROCESSING),
            )
            return updated.rowcount

    def healthy(self) -> bool:
        with self.connection() as conn:
            return conn.execute("SELECT 1").fetchone()[0] == 1
