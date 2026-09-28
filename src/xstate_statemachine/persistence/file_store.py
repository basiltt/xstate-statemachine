# src/xstate_statemachine/persistence/file_store.py
# -----------------------------------------------------------------------------
# 📁 FileStore -- one JSON file per key, atomic writes, advisory locks (#259)
# -----------------------------------------------------------------------------
# 🏛️ Good for: a single host with a few processes (a dev server with
#    reload, a cron job + a web worker), no database wanted. NOT for
#    network shares: SMB/NFS advisory locking is unreliable and
#    `os.replace` is not atomic across them -- documented, not detected.
#
# 🔐 X0 items (#303): the key NEVER appears raw in a path -- it is encoded
#    to a reversible, filesystem-safe form (X0.9), so `../etc/passwd`,
#    `CON`, a NUL or a 300-char key cannot escape, collide or crash the
#    directory. Directory 0700, files 0600 (POSIX). Locks record pid+time
#    so a crashed holder's lock is reclaimed instead of wedging the key.
#
# 📝 Windows: `os.replace` over a file another process has open raises
#    `PermissionError`; the writer retries briefly. Readers open-read-close
#    and never hold the file. `msvcrt.locking` is the lock primitive there,
#    `fcntl.flock` elsewhere.
# -----------------------------------------------------------------------------
"""`FileStore`: JSON-file-per-key store with atomic writes and locks."""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import (
    Any,
    ContextManager,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

from ..exceptions import (
    ConflictError,
    InvalidKeyError,
    LockTimeoutError,
    SnapshotCorruptError,
)
from .deadline import Deadline, check_deadline_record
from .store import BaseStore

__all__ = ["FileStore", "encode_key", "decode_key"]

_SUFFIX = ".xsm.json"
_LOCK_SUFFIX = ".lock"
#: Characters that pass through unchanged. Everything else (including
#: uppercase -- see below) is percent-escaped, so the encoding is
#: reversible and case-insensitive filesystems cannot collide two keys.
_SAFE = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-_")
_WINDOWS_RESERVED = re.compile(
    r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.IGNORECASE
)
_WRITE_RETRIES = 20
_WRITE_RETRY_SLEEP = 0.025


def encode_key(key: str) -> str:
    """Filesystem-safe, reversible, case-preserving encoding of *key*.

    Lower-case letters, digits, ``-`` and ``_`` pass through; every other
    code point (uppercase included, so ``Order`` and ``order`` never
    collide on a case-insensitive filesystem) becomes ``%XX`` per UTF-8
    byte. Windows reserved device names are prefixed so ``con`` cannot
    become a device.
    """
    out: List[str] = []
    for ch in key:
        if ch in _SAFE:
            out.append(ch)
        else:
            out.extend(f"%{b:02x}" for b in ch.encode("utf-8"))
    enc = "".join(out)
    if _WINDOWS_RESERVED.match(enc):
        enc = "%5f" + enc  # a leading escaped '_' -- still reversible
    return enc


def decode_key(name: str) -> str:
    """Inverse of `encode_key`."""
    if name.startswith("%5f") and _WINDOWS_RESERVED.match(name[3:]):
        name = name[3:]
    buf = bytearray()
    i = 0
    while i < len(name):
        if name[i] == "%":
            buf.append(int(name[i + 1 : i + 3], 16))
            i += 3
        else:
            buf.extend(name[i].encode("utf-8"))
            i += 1
    return buf.decode("utf-8")


def _validate_file_key(key: str) -> None:
    """FileStore's extra rules on top of `validate_key` (X0.9)."""
    if key in (".", "..") or "/" in key or "\\" in key:
        raise InvalidKeyError(
            f"FileStore key {key!r} must not contain path separators or "
            f"be '.' / '..'."
        )
    if os.path.isabs(key):
        raise InvalidKeyError(f"FileStore key {key!r} must not be a path.")


# -- locking primitives -------------------------------------------------------
if sys.platform == "win32":  # pragma: no cover - exercised on Windows CI
    import msvcrt

    def _try_lock(fd: int) -> bool:
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    def _unlock(fd: int) -> None:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass

else:  # pragma: no cover - exercised on POSIX CI
    import fcntl

    def _try_lock(fd: int) -> bool:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

    def _unlock(fd: int) -> None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":  # pragma: no cover
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class FileStore(BaseStore):
    """One ``<encoded-key>.xsm.json`` file per key under *directory*.

    Args:
        directory: Created if missing (mode ``0700`` on POSIX).
        stale_lock_after: Seconds after which a lock file whose owning pid
            is dead (or which is simply this old) is reclaimed.
        fsync: ``True`` (default) calls ``os.fsync`` before the atomic
            rename so a power loss cannot leave a zero-length file.

    Each write goes to a temp file in the same directory, is flushed and
    fsynced, then ``os.replace``d over the target -- readers see either the
    old record or the new one, never a torn one. ``save`` takes the key's
    advisory lock around read-compare-write so two processes cannot both
    pass an ``expected_version`` check.

    ⚠️ Not safe on network shares (SMB/NFS).
    """

    backend = "file"

    def __init__(
        self,
        directory: Any,
        *,
        stale_lock_after: float = 60.0,
        fsync: bool = True,
        **kw: Any,
    ) -> None:
        super().__init__(**kw)
        self.directory = Path(directory)
        self.stale_lock_after = float(stale_lock_after)
        self.fsync = bool(fsync)
        self.directory.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            with contextlib.suppress(OSError):
                os.chmod(self.directory, 0o700)
        #: Test seam: called with the temp path right before `os.replace`.
        #: A test raises from it to simulate a crash mid-write and asserts
        #: the previous record is intact (the review's "fault hook, not a
        #: real process kill").
        self._before_replace_hook: Optional[Any] = None

    # -- paths --------------------------------------------------------------------
    def _path(self, key: str) -> Path:
        _validate_file_key(key)
        return self.directory / (encode_key(key) + _SUFFIX)

    def _lock_path(self, key: str) -> Path:
        return self.directory / (encode_key(key) + _LOCK_SUFFIX)

    # -- record I/O -----------------------------------------------------------------
    @staticmethod
    def _read(path: Path) -> Optional[Dict[str, Any]]:
        # 🪟 Windows: while another process's `os.replace` is in flight the
        #    target is briefly inaccessible and `open` raises
        #    PermissionError (not FileNotFoundError). Retry briefly, as the
        #    writer does on the other side of the same race.
        text: Optional[str] = None
        for attempt in range(_WRITE_RETRIES):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read()
                break
            except FileNotFoundError:
                return None
            except PermissionError:
                if attempt == _WRITE_RETRIES - 1:
                    raise
                time.sleep(_WRITE_RETRY_SLEEP)
        assert text is not None
        try:
            rec = json.loads(text)
        except ValueError as exc:
            raise SnapshotCorruptError(
                f"FileStore record {path.name} is not valid JSON: {exc}"
            ) from exc
        if not isinstance(rec, dict) or not isinstance(
            rec.get("version"), int
        ):
            raise SnapshotCorruptError(
                f"FileStore record {path.name} is malformed."
            )
        return rec

    def _write_atomic(self, path: Path, rec: Dict[str, Any]) -> None:
        fd, tmp = tempfile.mkstemp(
            prefix=".tmp-", suffix=_SUFFIX, dir=str(self.directory)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(rec, fh, separators=(",", ":"))
                fh.flush()
                if self.fsync:
                    os.fsync(fh.fileno())
            if os.name == "posix":
                os.chmod(tmp, 0o600)
            if self._before_replace_hook is not None:
                self._before_replace_hook(tmp)
            # 🪟 Windows: a reader that still has the target open makes
            #    `os.replace` raise PermissionError; retry briefly.
            for attempt in range(_WRITE_RETRIES):
                try:
                    os.replace(tmp, path)
                    break
                except PermissionError:
                    if attempt == _WRITE_RETRIES - 1:
                        raise
                    time.sleep(_WRITE_RETRY_SLEEP)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise

    # -- primitives ----------------------------------------------------------------------
    def _load_raw(
        self, key: str
    ) -> Optional[Tuple[str, int, str, float, Sequence[Deadline]]]:
        rec = self._read(self._path(key))
        if rec is None:
            return None
        deadlines = []
        for d in rec.get("deadlines") or []:
            if check_deadline_record(d) is None:
                deadlines.append(Deadline.from_dict(d))
        return (
            str(rec.get("snapshot", "")),
            int(rec["version"]),
            str(rec.get("machine_version", "")),
            float(rec.get("updated_at", 0.0)),
            deadlines,
        )

    def _save_raw(
        self,
        key: str,
        data: str,
        expected_version: Optional[int],
        machine_version: str,
        deadlines: Tuple[Deadline, ...],
    ) -> int:
        path = self._path(key)
        # 🔒 The read-compare-write must be one critical section across
        #    processes, or two writers both pass the version check.
        with self._lock_raw(key, timeout=10.0):
            rec = self._read(path)
            current = int(rec["version"]) if rec else 0
            if expected_version is not None and expected_version != current:
                raise ConflictError(
                    key, expected_version, current if rec else None
                )
            new_version = current + 1
            self._write_atomic(
                path,
                {
                    "key": key,
                    "snapshot": data,
                    "version": new_version,
                    "machine_version": machine_version,
                    "updated_at": time.time(),
                    "deadlines": [d.to_dict() for d in deadlines],
                },
            )
            return new_version

    def _delete_raw(self, key: str) -> bool:
        try:
            os.unlink(self._path(key))
            return True
        except FileNotFoundError:
            return False

    def _forget_raw(self, key: str) -> Dict[str, int]:
        existed = self._delete_raw(key)
        locks = 0
        with contextlib.suppress(FileNotFoundError, PermissionError):
            os.unlink(self._lock_path(key))
            locks = 1
        return {"snapshots": int(existed), "locks": locks}

    def _list_keys_raw(self, prefix: str, limit: int) -> List[str]:
        keys: List[str] = []
        for p in self.directory.iterdir():
            name = p.name
            if not name.endswith(_SUFFIX) or name.startswith(".tmp-"):
                continue
            try:
                key = decode_key(name[: -len(_SUFFIX)])
            except (ValueError, UnicodeDecodeError):
                continue  # not ours
            if key.startswith(prefix):
                keys.append(key)
        keys.sort()
        return keys[:limit]

    def _lock_raw(self, key: str, timeout: float) -> ContextManager[None]:
        return self._file_lock(self._lock_path(key), key, timeout)

    @contextlib.contextmanager
    def _file_lock(
        self, lock_path: Path, key: str, timeout: float
    ) -> Iterator[None]:
        deadline = time.monotonic() + timeout
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            while True:
                if _try_lock(fd):
                    break
                if self._reclaim_stale(lock_path):
                    continue
                if time.monotonic() >= deadline:
                    raise LockTimeoutError(
                        key, timeout, holder=self._holder_info(lock_path)
                    )
                time.sleep(0.01)
            # Record ownership for stale-lock diagnosis. The OS lock covers
            # byte 0 only; the info lives from byte 1 so a WAITER can still
            # read it (msvcrt.locking blocks reads of the locked byte).
            with contextlib.suppress(OSError):
                os.lseek(fd, 1, os.SEEK_SET)
                os.write(
                    fd, f"{os.getpid()} {time.time():.3f}\n".ljust(63).encode()
                )
                os.lseek(fd, 0, os.SEEK_SET)
            try:
                yield
            finally:
                _unlock(fd)
        finally:
            os.close(fd)

    def _holder_info(self, lock_path: Path) -> str:
        try:
            with open(lock_path, "rb") as fh:
                fh.seek(1)  # byte 0 is the locked byte; see _file_lock
                return fh.read(63).decode("utf-8", "replace").strip()
        except OSError:
            return ""

    def _reclaim_stale(self, lock_path: Path) -> bool:
        """If the lock's recorded holder is dead or too old, the OS-level
        lock is already released (locks die with their fd); we only need
        to report that a retry is worthwhile. Returns False if the holder
        looks alive."""
        info = self._holder_info(lock_path)
        try:
            pid_s, ts_s = info.split()
            pid, ts = int(pid_s), float(ts_s)
        except ValueError:
            return False
        if time.time() - ts > self.stale_lock_after:
            return True
        return not _pid_alive(pid) and pid != os.getpid()

    def health(self) -> Dict[str, Any]:
        ok = self.directory.is_dir() and os.access(self.directory, os.W_OK)
        return {
            "ok": ok,
            "backend": self.backend,
            "directory": str(self.directory),
        }
