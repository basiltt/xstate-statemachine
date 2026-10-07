# src/xstate_statemachine/contrib/django/_locking.py
# -----------------------------------------------------------------------------
# 🔒 Is this driver error "someone else holds the lock"? (#280 battle A)
# -----------------------------------------------------------------------------
# The SQLSTATE is trusted when the driver gives one (psycopg 2/3); else an
# ANCHORED phrase list -- a bare "locked" substring made a table named
# ``locked_orders`` in "no such table" look retryable.
# -----------------------------------------------------------------------------
"""Lock-error classification for `StatechartModelMixin.send`."""

from __future__ import annotations

import re
from typing import FrozenSet, Optional

#: SQLSTATEs that mean "another transaction holds the lock": lock_not_
#: available (NOWAIT / lock_timeout), deadlock_detected, serialization_
#: failure. Retryable by `send_with_retry`.
_LOCK_SQLSTATES: FrozenSet[str] = frozenset({"55P03", "40P01", "40001"})

#: Driver phrases, anchored (never a bare "locked" -- a table called
#: ``locked_orders`` in "no such table" is not a lock error).
_LOCK_PHRASE = re.compile(
    r"\bdatabase (?:table )?is (?:locked|busy)\b"
    r"|\block wait timeout exceeded\b"
    r"|\bdue to lock timeout\b"
    r"|\bdeadlock (?:detected|found)\b"
)


def _sqlstate(exc: BaseException) -> Optional[str]:
    """The SQLSTATE of *exc* or its driver cause (psycopg 2/3)."""
    seen = 0
    cur: Optional[BaseException] = exc
    while cur is not None and seen < 5:
        code = getattr(cur, "sqlstate", None) or getattr(cur, "pgcode", None)
        if isinstance(code, str) and code:
            return code
        cur = cur.__cause__ or cur.__context__
        seen += 1
    return None


def _is_lock_error(exc: BaseException) -> bool:
    """SQLite ``database is locked`` / ``busy``; Postgres 55P03 / 40P01 /
    40001 (the SQLSTATE is trusted when present); MySQL 1205 / 1213."""
    state = _sqlstate(exc)
    if state is not None:
        return state in _LOCK_SQLSTATES
    return bool(_LOCK_PHRASE.search(str(exc).lower()))


def _lock_timeout_s(using: str) -> float:
    """Best-effort: SQLite's configured ``timeout`` (Django default 5 s)."""
    from django.db import connections

    conn = connections[using]
    opts = conn.settings_dict.get("OPTIONS") or {}
    if conn.vendor == "postgresql":
        # 📝 Postgres has no busy_timeout: report the session's
        #    ``lock_timeout`` (0 = wait forever; a deadlock still aborts).
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT current_setting('lock_timeout')")
                raw = str(cur.fetchone()[0]).strip().lower()
        except Exception:  # pragma: no cover - aborted txn / no conn
            return 0.0
        num = raw.rstrip("mins")
        scale = {"ms": 0.001, "s": 1.0, "min": 60.0}.get(
            raw[len(num) :], 0.001
        )
        try:
            return float(num) * scale
        except ValueError:  # pragma: no cover - odd unit
            return 0.0
    try:
        return float(opts.get("timeout", 5.0))
    except (TypeError, ValueError):  # pragma: no cover - odd settings
        return 5.0
