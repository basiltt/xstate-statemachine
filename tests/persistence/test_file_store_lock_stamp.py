"""FileStore lock-file holder stamp: rewritten only when it has to be.

The stamp (``"<pid> <wall time>"`` from byte 1 of a key's ``.lock`` file)
is read by waiters for the ``holder=`` of `LockTimeoutError` and for the
stale-lock retry. Rewriting it on every acquisition made each lock cycle
pay an on-access antivirus rescan of the modified file (about 10 ms under
Windows Defender against 0.14 ms for the same open/lock/unlock/close
without the write), and every `save` and every `OptimisticLock` retry
takes this lock. `_os_lock` now reads the stamp first and leaves it alone
when it already names this process and is younger than
``stale_lock_after / 2``; anything else is rewritten exactly as before.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Tuple

import pytest

from src.xstate_statemachine.persistence import FileStore
from src.xstate_statemachine.persistence.file_store import _pid_alive

SNAP = json.dumps(
    {"version": 4, "status": "running", "context": {}, "state_ids": ["m.a"]}
)


def _stamp(pid: int, ts: float) -> bytes:
    """A lock file as `_os_lock` leaves it: locked byte 0, stamp from 1."""
    return b"\x00" + f"{pid} {ts:.3f}\n".ljust(63).encode()


def _stamp_bytes(lock_path: Path) -> bytes:
    """The stamp region (byte 1 on), readable while byte 0 is locked."""
    with open(lock_path, "rb") as fh:
        fh.seek(1)
        return fh.read()


def _dead_pid() -> int:
    # Odd pids never exist on Windows (pids are multiples of 4); on POSIX
    # walk until one is really dead, by the library's own oracle.
    pid = 999_999
    while _pid_alive(pid):
        pid += 2
    return pid


def _parse(store: FileStore, key: str) -> Tuple[int, float]:
    pid_s, ts_s = store._holder_info(store._lock_path(key)).split()
    return int(pid_s), float(ts_s)


class TestHolderStamp:
    def test_same_process_reacquire_leaves_stamp_bytes_untouched(
        self, tmp_path: Any
    ) -> None:
        store = FileStore(tmp_path / "s", stale_lock_after=60)
        lock_path = store._lock_path("k")
        planted = _stamp(os.getpid(), time.time() - 1.0)  # ours, 1 s old
        lock_path.write_bytes(planted)

        with store.lock("k"):
            # Held: what a waiter reads while the lock is taken. Byte 0 is
            # the locked byte (Windows refuses to read it), so read from
            # byte 1 exactly as `_holder_info` does.
            assert _stamp_bytes(lock_path) == planted[1:]
        for _ in range(3):
            with store.lock("k"):
                pass
        store.save("k", SNAP)  # `save` takes the same lock
        store.save("k", SNAP)

        assert lock_path.read_bytes() == planted
        pid, _ts = _parse(store, "k")
        assert pid == os.getpid()  # still names the holder

    def test_first_acquisition_writes_the_stamp(self, tmp_path: Any) -> None:
        store = FileStore(tmp_path / "s")
        before = time.time()
        with store.lock("k"):
            pid, ts = _parse(store, "k")
        assert pid == os.getpid()
        assert before - 0.001 <= ts <= time.time() + 0.001

    @pytest.mark.parametrize(
        "label, planted",
        [
            (
                "same pid, older than stale_lock_after / 2",
                lambda: _stamp(os.getpid(), time.time() - 45.0),
            ),
            (
                "same pid, dated in the future (clock step)",
                lambda: _stamp(os.getpid(), time.time() + 3600.0),
            ),
            ("dead pid, fresh", lambda: _stamp(_dead_pid(), time.time())),
            ("unparseable", lambda: b"\x00" + b"garbage".ljust(63)),
            ("empty file", lambda: b""),
        ],
    )
    def test_stamp_that_cannot_vouch_for_this_holder_is_rewritten(
        self, tmp_path: Any, label: str, planted: Callable[[], bytes]
    ) -> None:
        store = FileStore(tmp_path / "s", stale_lock_after=60)
        lock_path = store._lock_path("k")
        lock_path.write_bytes(planted())
        before = time.time()
        with store.lock("k"):
            pass
        pid, ts = _parse(store, "k")
        assert pid == os.getpid(), label
        assert before - 0.001 <= ts <= time.time() + 0.001, label

    def test_fresh_bound_is_half_of_stale_lock_after(
        self, tmp_path: Any
    ) -> None:
        # Half of a 2 s `stale_lock_after` is 1 s: a 1.5 s-old stamp of
        # ours is rewritten, a 0.5 s-old one is kept.
        store = FileStore(tmp_path / "s", stale_lock_after=2.0)
        lock_path = store._lock_path("k")
        old = _stamp(os.getpid(), time.time() - 1.5)
        lock_path.write_bytes(old)
        with store.lock("k"):
            pass
        assert lock_path.read_bytes() != old
        fresh = _stamp(os.getpid(), time.time() - 0.5)
        lock_path.write_bytes(fresh)
        with store.lock("k"):
            pass
        assert lock_path.read_bytes() == fresh

    def test_zero_stale_lock_after_rewrites_every_time(
        self, tmp_path: Any
    ) -> None:
        # The pre-existing behaviour, kept for `stale_lock_after=0`.
        store = FileStore(tmp_path / "s", stale_lock_after=0.0)
        lock_path = store._lock_path("k")
        planted = _stamp(os.getpid(), time.time() - 1.0)
        lock_path.write_bytes(planted)
        with store.lock("k"):
            pass
        assert lock_path.read_bytes() != planted
        pid, ts = _parse(store, "k")
        assert pid == os.getpid() and time.time() - ts < 1.0
