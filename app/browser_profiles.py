"""Private persistent Chrome directories; metadata never contains session material."""
from __future__ import annotations

import json
import os
import re
import secrets
import stat
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

PROFILE_ID_PATTERN = r"^[a-f0-9]{32}$"
_ID = re.compile(PROFILE_ID_PATTERN)


class ProfileError(ValueError):
    pass


class ProfileBusy(ProfileError):
    pass


def validate_profile_id(value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ProfileError("Invalid browser profile ID")
    return value


class BrowserProfileStore:
    def __init__(self, root: Path):
        self.root = Path(root).absolute()
        self._lock = threading.RLock()

    def _directory(self, path: Path, *, create=False) -> Path:
        # Reject symlinks in every ancestor, including the configured root.
        for part in reversed((path, *path.parents)):
            if part.is_symlink():
                raise ProfileError("Unsafe browser profile directory")
        if create:
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not path.is_dir() or path.resolve() != path:
            raise ProfileError("Browser profile not found")
        if os.name == "posix":
            if path.stat().st_uid != os.getuid():
                raise ProfileError("Browser profile directory has a different owner")
            path.chmod(0o700)
        return path

    def _root(self):
        return self._directory(self.root, create=True)

    def _path(self, profile_id):
        validate_profile_id(profile_id)
        self._root()
        return self._directory(self.root / profile_id)

    def _read(self, path):
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path / "metadata.json", flags)
            with os.fdopen(fd, "r", encoding="utf-8") as handle:
                if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                    raise ProfileError("Invalid browser profile metadata")
                data = json.loads(handle.read(4096))
            if set(data) != {"id", "label", "created_at", "updated_at"} or data["id"] != path.name:
                raise ValueError()
            validate_profile_id(data["id"])
            self.validate_label(data["label"])
            return data
        except (OSError, ValueError, TypeError) as exc:
            raise ProfileError("Invalid browser profile metadata") from exc

    @staticmethod
    def validate_label(label):
        if not isinstance(label, str) or not label.strip() or len(label) > 80 or any(ord(c) < 32 for c in label):
            raise ProfileError("Profile label must contain 1–80 printable characters")
        return label.strip()

    def create(self, label):
        label = self.validate_label(label)
        with self._lock:
            self._root()
            profile_id = secrets.token_hex(16)
            path = self.root / profile_id
            try:
                path.mkdir(mode=0o700)  # Exclusive; never reuse a collision.
            except FileExistsError as exc:
                raise ProfileError("Browser profile ID already exists") from exc
            now = datetime.now(timezone.utc).isoformat()
            data = {"id": profile_id, "label": label, "created_at": now, "updated_at": now}
            fd = os.open(path / "metadata.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            self._directory(path / "chrome", create=True)
            return data

    def get(self, profile_id):
        with self._lock:
            return self._read(self._path(profile_id))

    def list(self):
        with self._lock:
            root = self._root()
            return sorted((self._read(self._directory(path)) for path in root.iterdir()
                           if _ID.fullmatch(path.name)), key=lambda item: item["created_at"])

    @contextmanager
    def lease(self, profile_id):
        import fcntl  # Persistent browsers are Linux-only, like the runtime.

        path = self._path(profile_id)
        self._read(path)
        fd = os.open(path / "lease", os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ProfileError("Unsafe browser profile lease")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ProfileBusy("Browser profile is already in use") from exc
            yield self._directory(path / "chrome", create=True)
        finally:
            os.close(fd)  # Releases only our lease; never delete Chrome Singleton* locks.
