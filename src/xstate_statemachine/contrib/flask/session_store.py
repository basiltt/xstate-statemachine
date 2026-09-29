# src/xstate_statemachine/contrib/flask/session_store.py
# -----------------------------------------------------------------------------
# 🍪 SessionStore -- tiny snapshots inside Flask's signed session cookie
# -----------------------------------------------------------------------------
# 🏛️ For multi-step forms / wizards whose state belongs to ONE browser and
#    whose context is small: no database, the snapshot rides in the signed
#    (not encrypted!) session cookie. A hard size cap -- 3 KiB by default,
#    under the ~4 KiB every browser accepts for a whole cookie -- is enforced
#    on save AND load with `SessionStoreTooLargeError`, which names the fix.
#
# 🔐 The cookie is SIGNED with ``SECRET_KEY`` (tamper-evident) but readable
#    by the client: never put secrets in such a context. Versions still
#    fence writes (two tabs of one browser → `ConflictError`), but a client
#    can always REPLAY an older cookie -- use a server-side store when that
#    matters (payments, approvals).
# -----------------------------------------------------------------------------
"""`SessionStore` and `SessionStoreTooLargeError`."""

from __future__ import annotations

import contextlib
import time
from typing import (
    Any,
    ContextManager,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
)

from flask import session

from ...exceptions import ConflictError, SnapshotTooLargeError
from ...persistence.deadline import Deadline
from ...persistence.store import BaseStore

__all__ = [
    "DEFAULT_SESSION_LIMIT",
    "SessionStore",
    "SessionStoreTooLargeError",
]

#: 3 KiB: leaves room for Flask's own session keys and the signature under
#: the ~4096-byte cookie limit browsers enforce.
DEFAULT_SESSION_LIMIT = 3 * 1024
_SESSION_KEY = "_xsm"


class SessionStoreTooLargeError(SnapshotTooLargeError):
    """A snapshot does not fit in the session cookie."""

    def __init__(self, key: str, size: int, limit: int) -> None:
        super().__init__(key, size, limit)
        self.args = (
            f"Snapshot for '{key}' is {size} bytes; SessionStore keeps "
            f"snapshots in the session cookie and allows {limit} bytes. "
            f"Shrink the context or use a server-side store (SQLiteStore, "
            f"SQLAlchemyStore).",
        )

    def __str__(self) -> str:
        return str(self.args[0])


class SessionStore(BaseStore):
    """`StateStore` over ``flask.session`` (needs a request context).

    Args:
        max_snapshot_bytes: Hard cap per snapshot (default 3 KiB).
        codec: Optional ``str -> str`` codec (compression fits here).
    """

    backend = "flask-session"

    def __init__(
        self, *, max_snapshot_bytes: int = DEFAULT_SESSION_LIMIT, **kw: Any
    ) -> None:
        super().__init__(max_snapshot_bytes=max_snapshot_bytes, **kw)

    def _check_size(self, key: str, data: str) -> None:
        size = len(data.encode("utf-8"))
        if size > self.max_snapshot_bytes:
            raise SessionStoreTooLargeError(key, size, self.max_snapshot_bytes)

    @staticmethod
    def _bucket(create: bool = False) -> Dict[str, Any]:
        bucket = session.get(_SESSION_KEY)
        if bucket is None:
            bucket = {}
            if create:
                session[_SESSION_KEY] = bucket
        return bucket  # type: ignore[no-any-return]

    def _load_raw(
        self, key: str
    ) -> Optional[Tuple[str, int, str, float, Sequence[Deadline]]]:
        rec = self._bucket().get(key)
        if not isinstance(rec, dict):
            return None
        deadlines = [Deadline.from_dict(d) for d in rec.get("d") or ()]
        return (
            str(rec["s"]),
            int(rec["v"]),
            str(rec.get("mv") or ""),
            float(rec.get("t") or 0.0),
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
        bucket = dict(self._bucket())
        rec = bucket.get(key)
        current = int(rec["v"]) if isinstance(rec, dict) else 0
        if expected_version is not None and expected_version != current:
            raise ConflictError(
                key, expected_version, current if rec else None
            )
        bucket[key] = {
            "s": data,
            "v": current + 1,
            "mv": machine_version,
            "t": time.time(),
            "d": [d.to_dict() for d in deadlines],
        }
        # 📝 Reassign (not mutate) so Flask marks the session modified.
        session[_SESSION_KEY] = bucket
        return current + 1

    def _delete_raw(self, key: str) -> bool:
        bucket = dict(self._bucket())
        existed = bucket.pop(key, None) is not None
        session[_SESSION_KEY] = bucket
        return existed

    def _forget_raw(self, key: str) -> Dict[str, int]:
        rec = self._bucket().get(key)
        n_d = len(rec.get("d") or ()) if isinstance(rec, dict) else 0
        return {"snapshots": int(self._delete_raw(key)), "deadlines": n_d}

    def _list_keys_raw(self, prefix: str, limit: int) -> List[str]:
        return sorted(k for k in self._bucket() if k.startswith(prefix))[
            :limit
        ]

    def _lock_raw(self, key: str, timeout: float) -> ContextManager[None]:
        # One browser's cookie: there is nothing to lock across processes.
        return contextlib.nullcontext()
