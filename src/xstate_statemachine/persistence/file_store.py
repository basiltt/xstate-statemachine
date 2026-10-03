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
import errno
import hashlib
import json
import os
import re
import sys
import tempfile
import threading
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
    SnapshotTooLargeError,
    StoreError,
)
from .deadline import Deadline, check_deadline_record
from .store import BaseStore, check_record_fields

__all__ = ["FORMAT_VERSION", "FileStore", "encode_key", "decode_key"]

_SUFFIX = ".xsm.json"
#: #263 battle: bytes `list_versions` reads per record. Covers the header
#: (`format`, a 200-char key and a 255-char label, each up to 12 bytes
#: per char once `ensure_ascii` escapes it) with room to spare.
_HEADER_BYTES = 8192
_LOCK_SUFFIX = ".lock"
#: 🔐 X0.10: the record FORMAT version (distinct from the per-key record
#: `version`, the optimistic-locking counter). Bump with an upgrade step
#: in `_upcast_record`; a newer format is refused, never guessed at.
FORMAT_VERSION = 1
#: Characters that pass through unchanged. Everything else (including
#: uppercase -- see below) is percent-escaped, so the encoding is
#: reversible and case-insensitive filesystems cannot collide two keys.
_SAFE = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-_")
_WINDOWS_RESERVED = re.compile(
    r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.IGNORECASE
)
_WRITE_RETRIES = 20
_WRITE_RETRY_SLEEP = 0.025
#: Envelope + deadlines allowance on top of the escaped snapshot (X0.4).
_RECORD_HEADROOM = 1024 * 1024
#: Longest encoded stem used verbatim; + ``.xsm.json`` stays far below the
#: 255-unit component limit of NTFS / ext4 / APFS.
_MAX_STEM = 200
_HASHED_PREFIX = "~"


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


def _file_stem(key: str) -> str:
    """The on-disk stem for *key*: `encode_key` when that fits, else a
    ``~`` + SHA-256 name.

    🛡️ #259 battle: percent-encoding triples every non-``[a-z0-9_-]`` byte,
    so a legal 200-char key (``"A" * 200``, or CJK text) became a 600+-char
    file name and `save` died with ``OSError: [Errno 22]`` (Windows) /
    ``ENAMETOOLONG`` (POSIX) -- every filesystem caps a component at 255.
    ``~`` is never produced by `encode_key`, so the two namespaces cannot
    collide; the hash is of the exact UTF-8 key, so ``Order`` / ``order``
    stay distinct. `list_keys` recovers the key from the record body.
    """
    enc = encode_key(key)
    if len(enc) <= _MAX_STEM:
        return enc
    return _HASHED_PREFIX + hashlib.sha256(key.encode("utf-8")).hexdigest()


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
    import ctypes
    import msvcrt
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _CreateFileW = _k32.CreateFileW
    _CreateFileW.restype = wintypes.HANDLE
    _CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    _INVALID_HANDLE = wintypes.HANDLE(-1).value

    def _open_for_read(path: Path) -> Any:
        """Open *path* for reading WITH ``FILE_SHARE_DELETE``.

        🛡️ #259 battle: Python's `open()` omits ``FILE_SHARE_DELETE``, so
        on Windows every open reader made the writer's `os.replace` fail
        with a sharing violation. A reader polling in a loop starved the
        writer's whole retry budget and `save` raised `PermissionError`.
        With share-delete the rename succeeds while the reader finishes
        reading the OLD record from its handle -- POSIX semantics.
        """
        handle = _CreateFileW(
            str(path),
            0x80000000,  # GENERIC_READ
            0x7,  # FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
            None,
            3,  # OPEN_EXISTING
            0x80,  # FILE_ATTRIBUTE_NORMAL
            None,
        )
        if handle is None or handle == _INVALID_HANDLE:
            err = ctypes.get_last_error()
            if err in (2, 3):  # FILE_NOT_FOUND / PATH_NOT_FOUND
                raise FileNotFoundError(errno.ENOENT, "not found", str(path))
            if err in (5, 32):  # ACCESS_DENIED / SHARING_VIOLATION
                raise PermissionError(errno.EACCES, "access denied", str(path))
            raise ctypes.WinError(err)
        try:
            fd = msvcrt.open_osfhandle(handle, os.O_RDONLY)
        except BaseException:
            _k32.CloseHandle(handle)
            raise
        return os.fdopen(fd, "rb")

    class _RenameInfo(ctypes.Structure):
        _fields_ = (
            ("Flags", wintypes.DWORD),
            ("RootDirectory", wintypes.HANDLE),
            ("FileNameLength", wintypes.DWORD),
            ("FileName", wintypes.WCHAR * 1),
        )

    _SetFileInformationByHandle = _k32.SetFileInformationByHandle
    _SetFileInformationByHandle.restype = wintypes.BOOL
    _SetFileInformationByHandle.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )

    def _replace(src: str, dst: Path) -> None:
        """`os.replace`, falling back to a POSIX-semantics rename.

        `MoveFileEx` (what `os.replace` calls) refuses to replace a file
        any process has open. ``FileRenameInfoEx`` with
        ``FILE_RENAME_FLAG_POSIX_SEMANTICS`` (Windows 10 1709+, NTFS)
        replaces it anyway as long as the opener shared delete -- which
        `_open_for_read` does -- and the reader keeps reading the old
        bytes. If that is unsupported too, the original error stands and
        the caller's retry loop takes over.
        """
        try:
            os.replace(src, dst)
        except PermissionError:
            if not _posix_rename(src, dst):
                raise

    def _posix_rename(src: str, dst: Path) -> bool:
        target = os.path.abspath(str(dst))
        handle = _CreateFileW(
            src,
            0x00010000 | 0x80000000,  # DELETE | GENERIC_READ
            0x7,
            None,
            3,  # OPEN_EXISTING
            0x80,
            None,
        )
        if handle is None or handle == _INVALID_HANDLE:
            return False
        try:
            name = ctypes.create_unicode_buffer(target)
            size = ctypes.sizeof(_RenameInfo) + 2 * len(target)
            buf = ctypes.create_string_buffer(size)
            info = _RenameInfo.from_buffer(buf)
            info.Flags = 0x1 | 0x2  # REPLACE_IF_EXISTS | POSIX_SEMANTICS
            info.RootDirectory = None
            info.FileNameLength = 2 * len(target)
            ctypes.memmove(
                ctypes.addressof(buf) + _RenameInfo.FileName.offset,
                name,
                2 * len(target),
            )
            return bool(_SetFileInformationByHandle(handle, 22, buf, size))
        finally:
            _k32.CloseHandle(handle)

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

    def _open_for_read(path: Path) -> Any:
        return open(path, "rb")

    def _replace(src: str, dst: Path) -> None:
        os.replace(src, dst)

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


class _StoreWriteError(StoreError, OSError):
    """A failed record write (ENOSPC, EIO, ...): a StoreError for the
    documented `except XStateMachineError`, still an OSError (with
    `errno`) for callers that caught the bare error (#263 battle)."""


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
        #: 🔁 Keys this THREAD currently holds via `lock()`, so `save()`
        #: inside a `with store.lock(key):` block does not deadlock on its
        #: own lock (the OS primitive is not reentrant).
        self._held = threading.local()
        #: Test seam: called with the temp path right before `os.replace`.
        #: A test raises from it to simulate a crash mid-write and asserts
        #: the previous record is intact (the review's "fault hook, not a
        #: real process kill").
        self._before_replace_hook: Optional[Any] = None
        self._sweep_orphan_temps()

    def _sweep_orphan_temps(self) -> None:
        """Remove ``.tmp-*`` files a killed writer left behind.

        🛡️ #259 battle: the exception path unlinks its temp file, but a
        process killed (SIGKILL, power loss, TerminateProcess) between
        ``mkstemp`` and ``os.replace`` cannot -- the guarantee's "no temp
        litter" only held for in-process failures. Only temps older than
        ``stale_lock_after`` go, so a live writer in another process (whose
        temp lives for milliseconds) is never raced.
        """
        cutoff = time.time() - self.stale_lock_after
        with contextlib.suppress(OSError):
            for p in self.directory.iterdir():
                if not p.name.startswith(".tmp-"):
                    continue
                with contextlib.suppress(OSError):
                    if p.stat().st_mtime < cutoff:
                        p.unlink()

    # -- paths --------------------------------------------------------------------
    def _path(self, key: str) -> Path:
        _validate_file_key(key)
        return self.directory / (_file_stem(key) + _SUFFIX)

    def _lock_path(self, key: str) -> Path:
        return self.directory / (_file_stem(key) + _LOCK_SUFFIX)

    def _record_limit(self) -> int:
        """Largest legitimate record file: the snapshot JSON-escaped
        (``\\uXXXX`` is at most 6 bytes per input byte) plus headroom for
        the envelope and deadlines."""
        return 6 * self.max_snapshot_bytes + _RECORD_HEADROOM

    # -- record I/O -----------------------------------------------------------------
    @staticmethod
    def _read(
        path: Path, limit: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        # 🪟 Windows: while another process's `os.replace` is in flight the
        #    target is briefly inaccessible and `open` raises
        #    PermissionError (not FileNotFoundError). Retry briefly, as the
        #    writer does on the other side of the same race.
        raw: Optional[bytes] = None
        for attempt in range(_WRITE_RETRIES):
            try:
                with _open_for_read(path) as fh:
                    # 🛡️ X0.4 (#303 battle): bound the read BEFORE parsing;
                    #    `_check_size` only ran after the whole record had
                    #    been read and `json.loads`-ed.
                    raw = fh.read() if limit is None else fh.read(limit + 1)
                break
            except FileNotFoundError:
                return None
            except PermissionError as exc:
                # A DIRECTORY where the record should be reads as
                # PermissionError on Windows; retrying cannot help.
                if path.is_dir():
                    raise SnapshotCorruptError(
                        f"FileStore record {path.name} is a directory."
                    ) from exc
                if attempt == _WRITE_RETRIES - 1:
                    raise StoreError(
                        f"FileStore record {path.name} is unreadable: {exc}"
                    ) from exc
                time.sleep(_WRITE_RETRY_SLEEP)
            except OSError as exc:
                # IsADirectoryError, ELOOP (symlink loop), EIO, ... are a
                # damaged store, not a bare OSError.
                raise SnapshotCorruptError(
                    f"FileStore record {path.name} cannot be read: {exc}"
                ) from exc
        assert raw is not None
        if limit is not None and len(raw) > limit:
            raise SnapshotTooLargeError(path.name, len(raw), limit)
        # 🛡️ #303 battle: non-UTF-8 bytes (UnicodeDecodeError) and a deeply
        #    nested `[[[[...` (RecursionError) are corruption like any other
        #    -- they must surface as `SnapshotCorruptError`, not escape the
        #    documented `except XStateMachineError`.
        try:
            rec = json.loads(raw.decode("utf-8"))
        except (ValueError, RecursionError) as exc:
            raise SnapshotCorruptError(
                f"FileStore record {path.name} is not valid JSON: {exc}"
            ) from exc
        ver = rec.get("version") if isinstance(rec, dict) else None
        if (
            not isinstance(rec, dict)
            or isinstance(ver, bool)
            or not isinstance(ver, int)
            or ver < 1
        ):
            raise SnapshotCorruptError(
                f"FileStore record {path.name} is malformed."
            )
        return FileStore._upcast_record(rec, path.name)

    @staticmethod
    def _upcast_record(rec: Dict[str, Any], name: str) -> Dict[str, Any]:
        """X0.10: bring an older-format record up to `FORMAT_VERSION`;
        refuse a newer one."""
        fmt = rec.get("format", 1)  # records before the field are format 1
        if isinstance(fmt, bool) or not isinstance(fmt, int) or fmt < 1:
            raise SnapshotCorruptError(
                f"FileStore record {name} has an invalid 'format' {fmt!r}."
            )
        if fmt > FORMAT_VERSION:
            raise SnapshotCorruptError(
                f"FileStore record {name} is format {fmt}, newer than this "
                f"library supports ({FORMAT_VERSION}). Upgrade "
                f"xstate-statemachine."
            )
        # (no upgrade steps yet: format 1 is the only one)
        rec["format"] = FORMAT_VERSION
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
                    _replace(tmp, path)
                    break
                except PermissionError:
                    if attempt == _WRITE_RETRIES - 1:
                        raise
                    time.sleep(_WRITE_RETRY_SLEEP)
        except BaseException as exc:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            if isinstance(exc, OSError):
                # 🛡️ #263 battle: ENOSPC / EIO / a stuck rename escaped as
                #    a bare OSError, outside `except XStateMachineError`.
                #    The target was never replaced: the old record stands.
                raise _StoreWriteError(
                    exc.errno or 0,
                    f"FileStore could not write {path.name}: {exc}",
                ) from exc
            raise

    # -- primitives ----------------------------------------------------------------------
    def _load_raw(
        self, key: str
    ) -> Optional[Tuple[str, int, str, float, Sequence[Deadline]]]:
        rec = self._read(self._path(key), self._record_limit())
        if rec is None:
            return None
        where = f"FileStore record {self._path(key).name}"
        snap = rec.get("snapshot", "")
        mv = rec.get("machine_version", "")
        upd = rec.get("updated_at", 0.0)
        check_record_fields(where, snap, rec["version"], mv, upd)
        raw_dl = rec.get("deadlines") or []
        if not isinstance(raw_dl, list):
            raise SnapshotCorruptError(f"{where}: 'deadlines' is not a list.")
        deadlines = []
        for d in raw_dl:
            problem = check_deadline_record(d)
            if problem is not None:
                raise SnapshotCorruptError(
                    f"{where}: bad deadline entry: {problem}."
                )
            deadlines.append(Deadline.from_dict(d))
        return (snap, int(rec["version"]), mv, float(upd), deadlines)

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
        #    processes, or two writers both pass the version check. If this
        #    thread already holds the key (a `PessimisticLock` block), reuse
        #    it -- the OS lock is not reentrant.
        with self._maybe_lock(key, timeout=10.0):
            rec = self._read(path, self._record_limit())
            current = int(rec["version"]) if rec else 0
            if expected_version is not None and expected_version != current:
                raise ConflictError(
                    key, expected_version, current if rec else None
                )
            new_version = current + 1
            self._write_atomic(
                path,
                {
                    "format": FORMAT_VERSION,
                    "key": key,
                    # 📝 #263 battle: the label precedes the blob so
                    #    `list_versions` reads a few hundred bytes per file.
                    "machine_version": machine_version,
                    "snapshot": data,
                    "version": new_version,
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
            stem = name[: -len(_SUFFIX)]
            if stem.startswith(_HASHED_PREFIX):
                hashed = self._hashed_key(p, stem)
                if hashed is None:
                    continue
                key = hashed
            else:
                try:
                    key = decode_key(stem)
                except (ValueError, UnicodeDecodeError):
                    continue  # not ours
            if key.startswith(prefix):
                keys.append(key)
        keys.sort()
        return keys[:limit]

    def _list_versions_raw(
        self, prefix: str, limit: int
    ) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        for key in self.list_keys(prefix=prefix, limit=limit):
            mv = self._header_label(self._path(key))
            if mv is None:
                # Older record (label after the blob) or odd layout: the
                # full, validating read decides.
                raw = self._load_raw(key)
                if raw is None:
                    continue
                mv = raw[2]
            out.append((key, mv))
        return out

    @staticmethod
    def _header_label(path: Path) -> Optional[str]:
        """The ``machine_version`` from the first `_HEADER_BYTES` of a
        record written label-first; ``None`` when it is not there."""
        try:
            with _open_for_read(path) as fh:
                head = fh.read(_HEADER_BYTES).decode("utf-8", "ignore")
        except OSError:
            return None
        # 🏛️ Walk the top-level members with the real JSON decoder (never
        #    a substring search: a key may contain `"machine_version":`).
        dec = json.JSONDecoder()
        pos = 1 if head.startswith("{") else -1
        while 0 < pos < len(head):
            try:
                name, pos = dec.raw_decode(head, pos)
                if head[pos : pos + 1] != ":":
                    return None
                value, pos = dec.raw_decode(head, pos + 1)
            except (ValueError, RecursionError):
                return None
            if name == "snapshot" or not isinstance(name, str):
                return None
            if name == "machine_version":
                return value if isinstance(value, str) else None
            if head[pos : pos + 1] != ",":
                return None
            pos += 1
        return None

    def _hashed_key(self, path: Path, stem: str) -> Optional[str]:
        """The key stored inside a hashed-name record, if it really hashes
        to *stem* (anything else is not ours, or is corrupt)."""
        try:
            rec = self._read(path, self._record_limit())
        except (OSError, SnapshotCorruptError, SnapshotTooLargeError):
            return None
        key = rec.get("key") if rec else None
        if not isinstance(key, str) or _file_stem(key) != stem:
            return None
        return key

    def _lock_raw(self, key: str, timeout: float) -> ContextManager[None]:
        return self._file_lock(self._lock_path(key), key, timeout)

    def _holds(self, key: str) -> bool:
        return key in getattr(self._held, "keys", ())

    @contextlib.contextmanager
    def _maybe_lock(self, key: str, timeout: float) -> Iterator[None]:
        if self._holds(key):
            yield
            return
        with self._lock_raw(key, timeout):
            yield

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
                # 🛡️ #259 battle: a "stale" verdict (holder info older than
                #    `stale_lock_after`, or a recycled pid) used to
                #    `continue` straight past the deadline check -- a LIVE
                #    holder slower than `stale_lock_after` made every waiter
                #    spin forever at 100 % CPU, ignoring `timeout`. The OS
                #    lock is the truth (it dies with its owner's fd); stale
                #    info only earns one immediate retry, never an unbounded
                #    one.
                if time.monotonic() >= deadline:
                    raise LockTimeoutError(
                        key, timeout, holder=self._holder_info(lock_path)
                    )
                time.sleep(0.001 if self._reclaim_stale(lock_path) else 0.01)
            held = getattr(self._held, "keys", None)
            if held is None:
                held = self._held.keys = set()
            held.add(key)
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
                held.discard(key)
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
