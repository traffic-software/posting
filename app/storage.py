import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.schemas import TaskStatus
from app.task_report import diagnostic, failure_result


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
            for name in ("context_json", "credential_blob", "credential_expires_at", "file_sources_blob", "file_sources_expires_at"):
                if name not in columns:
                    conn.execute(f"ALTER TABLE tasks ADD COLUMN {name} TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at)")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS workflows (
                    profile_id TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    intent_key TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    source_task_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (profile_id, origin, intent_key)
                )"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workflows_scope ON workflows(profile_id, origin, updated_at)")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS file_artifacts (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    purpose TEXT NOT NULL CHECK (purpose IN ('input', 'output')),
                    state TEXT NOT NULL CHECK (state IN ('RESERVED', 'READY', 'FAILED', 'DELETING')),
                    name TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    reserved_bytes INTEGER NOT NULL DEFAULT 0,
                    sha256 TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    expires_at INTEGER NOT NULL
                )"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_task ON file_artifacts(task_id, state, purpose)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_expiry ON file_artifacts(expires_at, state)")

    def create(
        self, prompt: str, max_active: int, *, context_json: str | None = None,
        credential_blob: str | None = None, credential_expires_at: str | None = None,
        file_sources_blob: str | None = None, file_sources_expires_at: str | None = None,
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
                   context_json, credential_blob, credential_expires_at, file_sources_blob, file_sources_expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_id, prompt, TaskStatus.PENDING, now, now, context_json, credential_blob, credential_expires_at, file_sources_blob, file_sources_expires_at),
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
                   credential_expires_at = NULL, file_sources_blob = NULL, file_sources_expires_at = NULL, updated_at = ?
                   WHERE status = ? AND credential_expires_at <= ?""",
                (TaskStatus.FAILED, "Task credentials expired", json.dumps(failure_result("Queued task credentials expired before execution.", diagnostic("credentials_expired", "preflight"))), utc_now(), TaskStatus.PENDING, utc_now()),
            )
            conn.execute(
                """UPDATE tasks SET status = ?, error = ?, result_json = ?, credential_blob = NULL,
                   credential_expires_at = NULL, file_sources_blob = NULL, file_sources_expires_at = NULL, updated_at = ?
                   WHERE status = ? AND file_sources_expires_at <= ?""",
                (TaskStatus.FAILED, "Task file-source grants expired", json.dumps(failure_result("Queued task file-source grants expired before execution.", diagnostic("file_sources_expired", "preflight"))), utc_now(), TaskStatus.PENDING, utc_now()),
            )
            row = conn.execute(
                """SELECT task_id, prompt, context_json, credential_blob, file_sources_blob FROM tasks
                   WHERE status = ? ORDER BY created_at, rowid LIMIT 1""",
                (TaskStatus.PENDING,),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ?, file_sources_blob = NULL, file_sources_expires_at = NULL WHERE task_id = ? AND status = ?",
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
                   credential_blob = NULL, credential_expires_at = NULL,
                   file_sources_blob = NULL, file_sources_expires_at = NULL
                   WHERE task_id = ? AND status = ?""",
                (status, data, error, utc_now(), task_id, TaskStatus.PROCESSING),
            )
            if updated.rowcount != 1:
                raise ValueError("Task is not processing")

    def cancel_processing(self, task_id: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """UPDATE tasks SET status = ?, error = ?, result_json = ?, updated_at = ?,
                   credential_blob = NULL, credential_expires_at = NULL,
                   file_sources_blob = NULL, file_sources_expires_at = NULL
                   WHERE task_id = ? AND status = ?""",
                (TaskStatus.FAILED, "Task cancelled by application shutdown", json.dumps(failure_result("The application shut down and cancelled execution.", diagnostic("application_shutdown", "worker"))), utc_now(), task_id, TaskStatus.PROCESSING),
            )

    def recover_interrupted(self) -> int:
        with self.connection() as conn:
            updated = conn.execute(
                """UPDATE tasks SET status = ?, error = ?, result_json = ?, updated_at = ?,
                   credential_blob = NULL, credential_expires_at = NULL,
                   file_sources_blob = NULL, file_sources_expires_at = NULL
                   WHERE status = ?""",
                (TaskStatus.FAILED, "Task interrupted by application restart", json.dumps(failure_result("An application restart interrupted execution.", diagnostic("application_restart", "worker"))), utc_now(), TaskStatus.PROCESSING),
            )
            return updated.rowcount

    def save_workflow(self, task_id: str, profile_id: str, data: dict, *, limit=100, days=90) -> None:
        from app.browser_profiles import validate_profile_id
        from app.workflow_memory import candidate_data, safe_text, workflow_key

        validate_profile_id(profile_id)
        candidate = candidate_data({key: data[key] for key in ("intent", "origin", "steps", "prerequisites")})
        evidence = data.get("evidence")
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 3:
            raise ValueError("Verified evidence is required")
        for item in evidence:
            if set(item) != {"criterion", "source", "origin", "expected_text", "verified_at"} or item["source"] != "visible_dom" or item["origin"] != candidate["origin"]:
                raise ValueError("Invalid workflow evidence")
            safe_text(item["expected_text"], maximum=160)
            datetime.fromisoformat(item["verified_at"])
        candidate["evidence"] = evidence
        encoded = json.dumps(candidate, ensure_ascii=False)
        if len(encoded.encode()) > 8192 or not 1 <= limit <= 500 or not 1 <= days <= 365:
            raise ValueError("Workflow storage bounds exceeded")
        now = utc_now()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            task = conn.execute("SELECT status, context_json FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if task is None or task["status"] != TaskStatus.COMPLETED:
                raise ValueError("Only completed tasks may supply workflows")
            options = json.loads(task["context_json"] or "{}")
            if options.get("browser_profile_id") != profile_id:
                raise ValueError("Workflow profile does not match task")
            criteria = options.get("workflow_success_criteria", [])
            if len(criteria) != len(evidence) or any(
                item["criterion"] != index or item["origin"] != criterion.get("origin")
                or item["expected_text"] != criterion.get("expected_text")
                for index, (item, criterion) in enumerate(zip(evidence, criteria))
            ):
                raise ValueError("Workflow evidence does not match caller criteria")
            conn.execute(
                """INSERT INTO workflows (profile_id, origin, intent_key, data_json, source_task_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(profile_id, origin, intent_key) DO UPDATE SET
                   data_json = excluded.data_json, source_task_id = excluded.source_task_id, updated_at = excluded.updated_at""",
                (profile_id, candidate["origin"], workflow_key(candidate["intent"]), encoded, task_id, now, now),
            )
            conn.execute("DELETE FROM workflows WHERE profile_id = ? AND updated_at < ?", (profile_id, cutoff))
            conn.execute(
                """DELETE FROM workflows WHERE profile_id = ? AND rowid NOT IN
                   (SELECT rowid FROM workflows WHERE profile_id = ? ORDER BY updated_at DESC, rowid DESC LIMIT ?)""",
                (profile_id, profile_id, limit),
            )

    def find_workflows(self, profile_id: str, origin: str, intent: str, *, limit=3, days=90) -> list[dict]:
        from app.browser_profiles import validate_profile_id
        from app.workflow_memory import candidate_data, public_origin, safe_text, terms

        validate_profile_id(profile_id)
        origin = public_origin(origin)
        intent = safe_text(intent, maximum=160)
        if not 1 <= limit <= 3 or not 1 <= days <= 365:
            raise ValueError("Invalid workflow retrieval bounds")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self.connection() as conn:
            rows = conn.execute(
                """SELECT data_json FROM workflows WHERE profile_id = ? AND origin = ? AND updated_at >= ?
                   ORDER BY updated_at DESC LIMIT 100""", (profile_id, origin, cutoff),
            ).fetchall()
        wanted = terms(intent)
        matches = []
        for row in rows:
            try:
                raw = json.loads(row["data_json"])
                if raw.get("version") != 1 or raw.get("origin") != origin:
                    continue
                data = candidate_data({key: raw[key] for key in ("intent", "origin", "steps", "prerequisites")})
                score = len(wanted & terms(data["intent"]))
                if score:
                    matches.append((score, data))
            except (ValueError, TypeError, KeyError):
                continue
        return [data for _, data in sorted(matches, key=lambda item: item[0], reverse=True)[:limit]]

    def healthy(self) -> bool:
        with self.connection() as conn:
            return conn.execute("SELECT 1").fetchone()[0] == 1
