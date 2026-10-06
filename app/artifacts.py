"""Private task files, durable metadata and expiring download capabilities."""
from __future__ import annotations

import hashlib
import hmac
import logging
import mimetypes
import os
import re
import secrets
import stat
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from starlette.responses import FileResponse
from uuid import UUID

from app.storage import utc_now

_ID = re.compile(r"^[a-f0-9]{32}$")
_BROWSER_FILE = re.compile(r"^[A-Za-z0-9_-]{1,160}(?:\.crdownload)?$")
_MEDIA = re.compile(r"^[a-zA-Z0-9!#$&^_.+-]+/[a-zA-Z0-9!#$&^_.+-]+$")
logger = logging.getLogger(__name__)


class ArtifactError(ValueError):
    pass


def display_name(value):
    value = str(value or "file.bin").replace("\\", "/").rsplit("/", 1)[-1]
    value = "".join(char for char in value if char.isprintable() and char not in '<>:"|?*').strip(" .")
    value = value[:180] or "file.bin"
    if value.split(".", 1)[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        value = "file-" + value
    return value


def media_type(value, name="file.bin"):
    value = str(value or "").split(";", 1)[0].strip()
    if not _MEDIA.fullmatch(value) or len(value) > 120:
        value = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return value


def private_directory(path, *, create=False):
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ArtifactError("Unsafe artifact directory")
    if create:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_dir() or path.resolve() != path:
        raise ArtifactError("Artifact directory is unavailable")
    if os.name == "posix":
        if path.stat().st_uid != os.getuid():
            raise ArtifactError("Artifact directory has a different owner")
        path.chmod(0o700)
    return path


def open_regular(path):
    if path.is_symlink():
        raise ArtifactError("Artifact file is not a regular private file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (os.name == "posix" and info.st_uid != os.getuid()):
            raise ArtifactError("Artifact file is not a regular private file")
        current = path.stat(follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise ArtifactError("Artifact file changed")
        return os.fdopen(fd, "rb"), info
    except BaseException:
        os.close(fd)
        raise


class ArtifactAccessLogFilter(logging.Filter):
    def filter(self, record):
        def clean(value):
            if not isinstance(value, str) or "?" not in value:
                return value
            try:
                parts = urlsplit(value)
                query = parse_qsl(parts.query, keep_blank_values=True)
                if any(key.lower() == "signature" for key, _ in query):
                    query = [(key, "[REDACTED]" if key.lower() == "signature" else item) for key, item in query]
                    return urlunsplit(parts._replace(query=urlencode(query)))
            except ValueError:
                return "[REDACTED REQUEST TARGET]"
            return value
        if isinstance(record.args, tuple):
            record.args = tuple(clean(value) for value in record.args)
        return True


class ArtifactFileResponse(FileResponse):
    def __init__(self, path, row, release):
        self._release_lease = release
        super().__init__(path, filename=row["name"], media_type="application/octet-stream", headers={
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'", "Referrer-Policy": "no-referrer",
        })

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._release_lease()


class ArtifactManager:
    def __init__(self, settings, store):
        self.settings, self.store = settings, store
        self.root = Path(settings.artifact_root).absolute()
        self._lock = threading.RLock()
        self._leases = {}
        self._sessions = {}
        self._stopped = threading.Event()
        self._thread = None
        self._lock_fd = None
        base = urlsplit(settings.artifact_public_base_url)
        if (base.scheme not in {"https", "http"} or not base.hostname or base.username is not None
            or base.password is not None or base.query or base.fragment or base.port == 0
            or "\\" in base.netloc or "%" in base.hostname
            or (base.scheme == "http" and base.hostname not in {"127.0.0.1", "localhost", "::1"})):
            raise ArtifactError("Configure a trusted HTTPS artifact base URL (HTTP is loopback-only)")
        key = settings.artifact_link_signing_key
        if len(key) < 32 or len(key) > 256 or not key.isascii():
            raise ArtifactError("Configure a persistent artifact link key with at least 32 ASCII characters")
        if not settings.task_api_token:
            raise ArtifactError("File transfers require task API authentication")
        self.base_url = settings.artifact_public_base_url.rstrip("/")
        self._signing_key = key.encode("ascii")

    def initialize(self):
        private_directory(self.root, create=True)
        for name in ("ready", "incoming", "tasks"):
            private_directory(self.root / name, create=True)
        lock = self.root / "manager.lock"
        if lock.is_symlink():
            raise ArtifactError("Unsafe artifact manager lock")
        self._lock_fd = os.open(lock, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            info = os.fstat(self._lock_fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ArtifactError("Unsafe artifact manager lock")
            if os.name == "posix":
                import fcntl
                fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.store.connection() as conn:
                conn.execute("UPDATE file_artifacts SET state='DELETING' WHERE state IN ('RESERVED','FAILED')")
            self.cleanup()
            self._cleanup_orphans()
        except BaseException:
            os.close(self._lock_fd)
            self._lock_fd = None
            raise

    def start(self):
        def reap():
            while not self._stopped.wait(30):
                try:
                    self.cleanup()
                except Exception as exc:
                    logger.warning("Artifact cleanup deferred (%s)", type(exc).__name__)
        self._thread = threading.Thread(target=reap, name="artifact-expiry", daemon=True)
        self._thread.start()

    def close(self):
        self._stopped.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        with self._lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            session.close()
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None

    def task_session(self, task_id, guard):
        if str(UUID(task_id)) != task_id:
            raise ArtifactError("Invalid task file scope")
        with self._lock:
            if task_id in self._sessions:
                raise ArtifactError("Task files are already active")
            session = ArtifactSession(self, task_id, guard)
            self._sessions[task_id] = session
            return session

    def _path(self, artifact_id, *, incoming=False, name=None, create=False):
        if not isinstance(artifact_id, str) or not _ID.fullmatch(artifact_id):
            raise ArtifactError("Unknown artifact")
        private_directory(self.root)
        if incoming:
            return private_directory(self.root / "incoming") / (artifact_id + ".part")
        filename = name if name is not None else self.row(artifact_id)["name"]
        if filename != display_name(filename):
            raise ArtifactError("Unsafe artifact filename")
        directory = private_directory(self.root / "ready" / artifact_id, create=create)
        return directory / filename

    def row(self, artifact_id):
        if not isinstance(artifact_id, str) or not _ID.fullmatch(artifact_id):
            raise ArtifactError("Unknown artifact")
        with self.store.connection() as conn:
            row = conn.execute("SELECT * FROM file_artifacts WHERE id=?", (artifact_id,)).fetchone()
        if row is None:
            raise ArtifactError("Unknown artifact")
        return dict(row)

    @staticmethod
    def summary(row):
        return {key: row[key] for key in ("id", "name", "size_bytes", "media_type", "sha256")}

    def _signature(self, row, expires):
        payload = f"artifact-download/v1\n{row['task_id']}\n{row['id']}\n{row['sha256']}\n{row['purpose']}\n{expires}".encode()
        return hmac.new(self._signing_key, payload, hashlib.sha256).hexdigest()

    def links(self, task_id):
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM file_artifacts WHERE task_id=? AND state='READY' AND purpose='output' AND expires_at>? ORDER BY created_at, id LIMIT ?",
                (task_id, int(time.time()), self.settings.artifact_max_files_per_task),
            ).fetchall()
        links = []
        for raw in rows:
            row = dict(raw)
            try:
                handle, info = open_regular(self._path(row["id"]))
                handle.close()
                if info.st_size != row["size_bytes"]:
                    continue
            except (OSError, ArtifactError):
                continue
            expires = row["expires_at"]
            links.append({**self.summary(row),
                "download_url": f"{self.base_url}/task-artifacts/{row['id']}/download?expires={expires}&signature={self._signature(row, expires)}",
                "expires_at": datetime.fromtimestamp(expires, timezone.utc).isoformat()})
        return links

    def download_lease(self, artifact_id, expires, signature):
        with self._lock:
            row = self.row(artifact_id)
            if (row["state"] != "READY" or row["purpose"] != "output" or expires != row["expires_at"]
                or expires <= int(time.time()) or not isinstance(signature, str)
                or not hmac.compare_digest(self._signature(row, expires), signature)):
                raise ArtifactError("Download link is invalid or expired")
            path = self._path(artifact_id)
            handle, info = open_regular(path)
            handle.close()
            if info.st_size != row["size_bytes"]:
                raise ArtifactError("Artifact file changed")
            self._leases[artifact_id] = self._leases.get(artifact_id, 0) + 1
        released = False

        def release():
            nonlocal released
            with self._lock:
                if not released:
                    count = self._leases.get(artifact_id, 1) - 1
                    if count:
                        self._leases[artifact_id] = count
                    else:
                        self._leases.pop(artifact_id, None)
                    released = True
        return path, row, release

    def delete(self, artifact_id):
        with self._lock:
            if self._leases.get(artifact_id):
                return False
            row = self.row(artifact_id)
            with self.store.connection() as conn:
                conn.execute("UPDATE file_artifacts SET state='DELETING' WHERE id=?", (artifact_id,))
            path = self._path(artifact_id, incoming=True)
            if path.exists() or path.is_symlink():
                handle, _ = open_regular(path)
                handle.close()
                path.unlink()
            directory = self.root / "ready" / artifact_id
            if directory.exists() or directory.is_symlink():
                directory = private_directory(directory)
                for path in directory.iterdir():
                    handle, _ = open_regular(path)
                    handle.close()
                    path.unlink()
                directory.rmdir()
            with self.store.connection() as conn:
                conn.execute("DELETE FROM file_artifacts WHERE id=?", (artifact_id,))
            return True

    def cleanup(self):
        with self._lock:
            with self.store.connection() as conn:
                rows = conn.execute("SELECT id,task_id,state FROM file_artifacts WHERE expires_at<=? OR state IN ('FAILED','DELETING')", (int(time.time()),)).fetchall()
            for row in rows:
                if row["task_id"] in self._sessions or self._leases.get(row["id"]):
                    continue
                self.delete(row["id"])

    def _cleanup_orphans(self):
        with self.store.connection() as conn:
            known = {row[0] for row in conn.execute("SELECT id FROM file_artifacts")}
        for path in private_directory(self.root / "incoming").iterdir():
            identifier = path.name.removesuffix(".part")
            if _ID.fullmatch(identifier) and identifier not in known:
                handle, _ = open_regular(path)
                handle.close()
                path.unlink()
        for directory in private_directory(self.root / "ready").iterdir():
            if _ID.fullmatch(directory.name) and directory.name not in known:
                for path in private_directory(directory).iterdir():
                    handle, _ = open_regular(path)
                    handle.close()
                    path.unlink()
                directory.rmdir()
        for directory in private_directory(self.root / "tasks").iterdir():
            try:
                if str(UUID(directory.name)) == directory.name:
                    self._clear_browser_directory(directory / "browser")
            except (ValueError, OSError, ArtifactError):
                continue

    @staticmethod
    def _clear_browser_directory(directory):
        if not directory.exists():
            return
        directory = private_directory(directory)
        for path in directory.iterdir():
            if _BROWSER_FILE.fullmatch(path.name):
                handle, _ = open_regular(path)
                handle.close()
                path.unlink()
        try:
            directory.rmdir()
            directory.parent.rmdir()
        except OSError:
            pass


class ArtifactSession:
    def __init__(self, manager, task_id, guard):
        self.manager, self.task_id, self.guard = manager, task_id, guard
        self._lock = threading.RLock()
        self._closed = False
        self._writers = {}
        self._sources = {}
        task_directory = private_directory(manager.root / "tasks" / task_id, create=True)
        self.browser_directory = private_directory(task_directory / "browser", create=True)

    def check(self):
        if self._closed:
            raise ArtifactError("Task files are closed")
        self.guard()

    def reserve(self, purpose="output", name="file.bin", media_type="application/octet-stream"):
        self.check()
        if purpose not in {"input", "output"}:
            raise ArtifactError("Invalid artifact purpose")
        settings, manager = self.manager.settings, self.manager
        identifier = secrets.token_hex(16)
        with manager._lock, manager.store.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            task = conn.execute("SELECT status FROM tasks WHERE task_id=?", (self.task_id,)).fetchone()
            if task is None or task["status"] != "PROCESSING":
                raise ArtifactError("Task is not processing")
            counts = conn.execute(
                "SELECT COUNT(*),COALESCE(SUM(CASE WHEN state='RESERVED' THEN reserved_bytes ELSE MAX(size_bytes,reserved_bytes) END),0) FROM file_artifacts WHERE state IN ('RESERVED','READY','DELETING')",
            ).fetchone()
            own = conn.execute(
                "SELECT COUNT(*),COALESCE(SUM(CASE WHEN state='RESERVED' THEN reserved_bytes ELSE MAX(size_bytes,reserved_bytes) END),0) FROM file_artifacts WHERE task_id=? AND state IN ('RESERVED','READY','DELETING')", (self.task_id,),
            ).fetchone()
            maximum = min(settings.artifact_max_file_bytes, settings.artifact_max_task_bytes - own[1], settings.artifact_max_storage_bytes - counts[1])
            if counts[0] >= settings.artifact_max_objects or own[0] >= settings.artifact_max_files_per_task or maximum <= 0:
                raise ArtifactError("Artifact file or storage quota is exhausted")
            conn.execute(
                "INSERT INTO file_artifacts (id,task_id,purpose,state,name,media_type,reserved_bytes,created_at,expires_at) VALUES (?,?,?,'RESERVED',?,?,?,?,?)",
                (identifier, self.task_id, purpose, display_name(name), media_type, maximum, utc_now(), int(time.time()) + max(3600, settings.task_timeout_seconds * 2)),
            )
        try:
            writer = ArtifactWriter(self, identifier, maximum)
            with self._lock:
                self.check()
                self._writers[identifier] = writer
            return writer
        except BaseException:
            manager.delete(identifier)
            raise

    def list_files(self):
        self.check()
        with self.manager.store.connection() as conn:
            rows = conn.execute("SELECT * FROM file_artifacts WHERE task_id=? AND state='READY' AND expires_at>? ORDER BY created_at,id", (self.task_id, int(time.time()))).fetchall()
        return [{**self.manager.summary(dict(row)), "purpose": row["purpose"]} for row in rows]

    def resolve(self, identifier):
        self.check()
        row = self.manager.row(identifier)
        if row["task_id"] != self.task_id or row["state"] != "READY" or row["expires_at"] <= int(time.time()):
            raise ArtifactError("File is not available to this task")
        path = self.manager._path(identifier)
        handle, info = open_regular(path)
        handle.close()
        if info.st_size != row["size_bytes"]:
            raise ArtifactError("Task file changed")
        return path, row

    def import_browser_file(self, path, name, reservation):
        self.check()
        if reservation.session is not self:
            raise ArtifactError("Download reservation does not belong to this task")
        path = Path(path)
        if path.parent != self.browser_directory or not _BROWSER_FILE.fullmatch(path.name) or path.name.endswith(".crdownload"):
            raise ArtifactError("Browser download is not a completed task file")
        handle, info = open_regular(path)
        if info.st_size > reservation.max_bytes:
            handle.close()
            raise ArtifactError("Browser download exceeds reserved bytes")
        try:
            digest = hashlib.sha256()
            with handle:
                while True:
                    self.check()
                    chunk = handle.read(65536)
                    if not chunk:
                        break
                    digest.update(chunk)
            self.check()
            current = path.stat(follow_symlinks=False)
            if (current.st_size, current.st_dev, current.st_ino) != (info.st_size, info.st_dev, info.st_ino):
                raise ArtifactError("Browser download changed during import")
            with reservation._lock:
                self.check()
                if reservation._state != "writing" or reservation._size:
                    raise ArtifactError("Download reservation is no longer empty")
                reservation._handle.close()
                reservation._handle = None
                os.replace(path, reservation.path)
                fd = os.open(reservation.path, os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0))
                reservation._handle = os.fdopen(fd, "ab")
                reservation._hash, reservation._size = digest, info.st_size
                return reservation.finish(name=name, mime=media_type(None, name))
        except BaseException:
            reservation.abort()
            raise

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            writers = list(self._writers.values())
        for writer in writers:
            writer.abort()
        with self.manager._lock:
            with self.manager.store.connection() as conn:
                inputs = conn.execute("SELECT id FROM file_artifacts WHERE task_id=? AND purpose='input'", (self.task_id,)).fetchall()
            for row in inputs:
                try:
                    self.manager.delete(row["id"])
                except (OSError, ArtifactError):
                    pass
            try:
                self.manager._clear_browser_directory(self.browser_directory)
            except (OSError, ArtifactError):
                pass
            self.manager._sessions.pop(self.task_id, None)


class ArtifactWriter:
    def __init__(self, session, identifier, maximum):
        self.session, self.id, self.max_bytes = session, identifier, maximum
        self.path = session.manager._path(identifier, incoming=True)
        self._lock = threading.RLock()
        self._state = "writing"
        self._size = 0
        self._hash = hashlib.sha256()
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        self._handle = os.fdopen(fd, "wb")

    def write(self, data):
        with self._lock:
            self.session.check()
            if self._state != "writing" or not isinstance(data, bytes):
                raise ArtifactError("Artifact is not writable")
            if self._size + len(data) > self.max_bytes:
                raise ArtifactError("Artifact exceeds its reserved bytes")
            self._handle.write(data)
            self._hash.update(data)
            self._size += len(data)

    def finish(self, *, name=None, mime=None):
        with self._lock:
            self.session.check()
            if self._state != "writing":
                raise ArtifactError("Artifact is not writable")
            manager = self.session.manager
            row = manager.row(self.id)
            if os.name == "posix":
                os.fchmod(self._handle.fileno(), 0o600)
            self._handle.flush()
            os.fsync(self._handle.fileno())
            self._handle.close()
            self._handle = None
            handle, info = open_regular(self.path)
            handle.close()
            if info.st_size != self._size:
                raise ArtifactError("Artifact bytes changed before publication")
            final_name = display_name(name or row["name"])
            final_mime = media_type(mime or row["media_type"], final_name)
            target = manager._path(self.id, name=final_name, create=True)
            if target.exists() or target.is_symlink():
                raise ArtifactError("Artifact storage collision")
            os.rename(self.path, target)
            if os.name == "posix":
                for parent in (target.parent, target.parent.parent):
                    directory = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                    try:
                        os.fsync(directory)
                    finally:
                        os.close(directory)
            with manager.store.connection() as conn:
                updated = conn.execute(
                    "UPDATE file_artifacts SET state='READY',name=?,media_type=?,size_bytes=?,reserved_bytes=0,sha256=?,expires_at=? WHERE id=? AND state='RESERVED'",
                    (final_name, final_mime, self._size, self._hash.hexdigest(), int(time.time()) + manager.settings.artifact_retention_seconds, self.id),
                )
                if updated.rowcount != 1:
                    raise ArtifactError("Artifact reservation is no longer valid")
            self._state = "ready"
            with self.session._lock:
                self.session._writers.pop(self.id, None)
            return manager.summary(manager.row(self.id))

    def abort(self):
        with self._lock:
            if self._state != "writing":
                return
            self._state = "aborted"
            if self._handle is not None:
                self._handle.close()
                self._handle = None
            try:
                self.session.manager.delete(self.id)
            except (OSError, ArtifactError):
                pass
            with self.session._lock:
                self.session._writers.pop(self.id, None)
