# src/xstate_statemachine/persistence/log.py
# -----------------------------------------------------------------------------
# 📜 TransitionLogPlugin / AuditPlugin / replay() -- who did what, and why
# -----------------------------------------------------------------------------
# 🏛️ "Who approved this and why?" is answered by grepping Slack in most
#    codebases. An append-only transition log answers it from the same
#    plugin hook that OBSERVED the transition -- unlike django-fsm-log,
#    which writes from a separate signal and can disagree with the state.
#    The log is also event-sourcing-lite: `replay()` re-runs the recorded
#    events from context₀ and asserts every step lands where it was
#    recorded, which is the time-travel / audit-verification primitive and
#    the input to the coverage report (B3) and live inspector (B7).
#
# 📝 Hooks (review amendment): `on_transition` carries no event, and
#    denied / unhandled / deferred events fire no transition at all. So the
#    record is built from `on_event_processed(interp, event, receipt)` --
#    once per event, after the step settled, with the outcome -- paired
#    with the from/to sets collected from `on_transition` during that
#    step. Eventless `always` chains and engine-minted events therefore
#    log correctly, and a non-transition has `to_states == from_states`
#    plus a `disposition`.
#
# 🔁 `replay()` does NOT re-send engine-minted events through `send()`
#    (the #195/#203 provenance gates would rightly refuse them). `after`
#    steps replay by advancing a `SimulatedClock`; service completions
#    replay through STUB services that return the recorded `done` data or
#    raise the recorded error. Unless `logic=` is given, replay forces
#    stub logic -- real actions would repeat their side effects.
#
# 🔐 X0: payload redaction through the shared `redact()` before a record
#    is built; `purge_older_than` (X0.5); `append(..., connection=None)`
#    seam so a Django / SQLAlchemy log store can join the store's
#    transaction; `seq` is gap-free per key.
# -----------------------------------------------------------------------------
"""`TransitionRecord`, log stores, `TransitionLogPlugin`, `AuditPlugin`,
`replay()`."""

from __future__ import annotations

import contextvars
import copy
import json
import math
import os
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
)

try:  # pragma: no cover
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol, runtime_checkable  # type: ignore

from ..events import AfterEvent, DoneEvent, ErrorEvent, event_kind
from ..exceptions import StoreError, XStateMachineError
from ..plugins import DEFAULT_REDACT_KEYS, PluginBase, redact

__all__ = [
    "AuditPlugin",
    "JSONLinesLog",
    "LogCorruptError",
    "MemoryLog",
    "ReplayDivergenceError",
    "SQLiteLog",
    "TransitionLogPlugin",
    "TransitionLogStore",
    "TransitionRecord",
    "correlation_id_var",
    "replay",
]

#: Set this contextvar (a request middleware does) and `AuditPlugin` picks
#: the correlation id up without the event having to carry it.
correlation_id_var: contextvars.ContextVar[Optional[str]] = (
    contextvars.ContextVar("xsm_correlation_id", default=None)
)


class LogCorruptError(StoreError):
    """A transition-log record (a JSONL line, a SQLite row) is unreadable
    or not a record. Raised by ``read()`` / ``next_seq()`` / ``purge`` --
    never skipped, because a replay over a log with a hole would "succeed"
    to a wrong state. Inspect the named location and repair or truncate."""


def _check_cutoff(cutoff_ts: Any) -> float:
    """🛡️ #262 battle: a NaN cutoff made every ``ts >= cutoff`` False, so
    ``purge_older_than(nan)`` silently erased the whole log."""
    if isinstance(cutoff_ts, bool) or not isinstance(cutoff_ts, (int, float)):
        raise ValueError(f"cutoff_ts must be a number, got {cutoff_ts!r}")
    if math.isnan(cutoff_ts) or cutoff_ts == -math.inf:
        raise ValueError(f"cutoff_ts must not be NaN / -inf: {cutoff_ts!r}")
    return float(cutoff_ts)


def _check_read(after_seq: Any, limit: Any) -> None:
    # 🛡️ #262 battle: `limit=-1` sliced `rows[:-1]` (MemoryLog) / meant
    #    "no limit" (SQLite) -- three backends, three answers.
    for name, v in (("after_seq", after_seq), ("limit", limit)):
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise ValueError(f"{name} must be an int >= 0, got {v!r}")


def _check_append(rec: Any) -> None:
    if not isinstance(rec, TransitionRecord):
        raise TypeError(
            f"append() takes a TransitionRecord, got {type(rec).__name__}"
        )
    if (
        isinstance(rec.seq, bool)
        or not isinstance(rec.seq, int)
        or rec.seq < 1
    ):
        raise ValueError(f"seq must be an int >= 1, got {rec.seq!r}")
    if (
        isinstance(rec.ts, bool)
        or not isinstance(rec.ts, (int, float))
        or not math.isfinite(rec.ts)
    ):
        raise ValueError(f"ts must be a finite number, got {rec.ts!r}")


@dataclass(frozen=True)
class TransitionRecord:
    """One processed event and what it did.

    Attributes:
        machine_id: The log key -- `interpreter.store_key` when set (the
            persisted instance), else `interpreter.id`.
        seq: Gap-free per-key sequence, from 1.
        ts: Epoch seconds (`interpreter.wall_now()`).
        event_type / event_payload: The event (payload redacted). For
            engine-minted events the payload holds ``kind`` plus ``data``
            (done) or ``error`` (``{type, message}``) so `replay()` can
            drive the stub service.
        from_states / to_states: Leaf ids before and after (sorted).
        actions: Action names run, in order.
        disposition: ``"transition"`` | ``"denied"`` | ``"unhandled"`` |
            ``"deferred"`` | ``"error"`` | ``"duplicate"``.
        actor / reason / correlation_id: Audit fields (`AuditPlugin`).
        machine_version: `MachineNode.version` or ``""``.
        engine: ``True`` for an engine-minted event (after / done / error).
    """

    machine_id: str
    seq: int
    ts: float
    event_type: str
    event_payload: Dict[str, Any]
    from_states: Tuple[str, ...]
    to_states: Tuple[str, ...]
    actions: Tuple[str, ...]
    disposition: str = "transition"
    actor: Optional[str] = None
    reason: Optional[str] = None
    correlation_id: Optional[str] = None
    machine_version: str = ""
    engine: bool = False
    error: Optional[Dict[str, str]] = None
    #: ``"external"`` -- a caller's `send()`; ``"internal"`` -- produced
    #: INSIDE a step (a `raise`, an action's own `send()` to itself, a
    #: deferred event re-released). `replay()` re-sends only external
    #: records; internal ones are reproduced by the engine (battle #262).
    #: Records written before this field existed read as external.
    origin: str = "external"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["from_states"] = list(self.from_states)
        d["to_states"] = list(self.to_states)
        d["actions"] = list(self.actions)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TransitionRecord":
        """Strict inverse of `to_dict`; anything else is `LogCorruptError`."""
        try:
            if not isinstance(d, dict):
                raise TypeError(f"record is {type(d).__name__}, not object")
            seq, ts = d["seq"], d["ts"]
            if isinstance(seq, bool) or not isinstance(seq, int) or seq < 1:
                raise ValueError(f"seq {seq!r}")
            if (
                isinstance(ts, bool)
                or not isinstance(ts, (int, float))
                or not math.isfinite(ts)
            ):
                raise ValueError(f"ts {ts!r}")
            for name in ("from_states", "to_states", "actions"):
                v = d.get(name)
                if v is not None and not isinstance(v, (list, tuple)):
                    raise TypeError(f"{name} is not a list")
            payload = d.get("event_payload")
            if payload is not None and not isinstance(payload, dict):
                raise TypeError("event_payload is not an object")
            if not isinstance(d["machine_id"], str) or not isinstance(
                d["event_type"], str
            ):
                raise TypeError("machine_id / event_type not strings")
            return cls(
                machine_id=d["machine_id"],
                seq=seq,
                ts=float(ts),
                event_type=d["event_type"],
                event_payload=dict(payload or {}),
                from_states=tuple(d.get("from_states") or ()),
                to_states=tuple(d.get("to_states") or ()),
                actions=tuple(d.get("actions") or ()),
                disposition=str(d.get("disposition", "transition")),
                actor=d.get("actor"),
                reason=d.get("reason"),
                correlation_id=d.get("correlation_id"),
                machine_version=str(d.get("machine_version") or ""),
                engine=bool(d.get("engine", False)),
                error=d.get("error"),
                origin=str(d.get("origin") or "external"),
            )
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise LogCorruptError(
                f"not a TransitionRecord ({type(exc).__name__}: {exc})"
            ) from exc


@runtime_checkable
class TransitionLogStore(Protocol):
    """Append-only, ordered per key."""

    def append(self, rec: TransitionRecord, *, connection: Any = None) -> None:
        """Persist *rec*. ``connection`` is the seam a store adapter uses
        to join the snapshot save's transaction (Django / SQLAlchemy);
        stdlib stores ignore it."""
        ...  # pragma: no cover

    def next_seq(self, machine_id: str) -> int:
        """The seq the next record for *machine_id* should carry."""
        ...  # pragma: no cover

    def read(
        self, machine_id: str, *, after_seq: int = 0, limit: int = 1000
    ) -> List[TransitionRecord]:
        """Records with ``seq > after_seq``, ascending, at most *limit*."""
        ...  # pragma: no cover

    def purge_older_than(self, cutoff_ts: float) -> int:
        """Delete records with ``ts < cutoff_ts``; return how many (X0.5)."""
        ...  # pragma: no cover

    def forget(self, machine_id: str) -> int:
        """Delete every record for *machine_id*; return how many (X0.5)."""
        ...  # pragma: no cover


# -----------------------------------------------------------------------------
# 🧠 MemoryLog
# -----------------------------------------------------------------------------
class MemoryLog:
    def __init__(self) -> None:
        self._rows: Dict[str, List[TransitionRecord]] = {}
        self._lock = threading.Lock()

    def append(self, rec: TransitionRecord, *, connection: Any = None) -> None:
        _check_append(rec)
        with self._lock:
            self._rows.setdefault(rec.machine_id, []).append(rec)

    def append_next(
        self, rec: TransitionRecord, *, connection: Any = None
    ) -> TransitionRecord:
        """Assign the next seq and append, atomically (battle #262)."""
        with self._lock:
            rows = self._rows.setdefault(rec.machine_id, [])
            out = replace(rec, seq=(rows[-1].seq + 1) if rows else 1)
            rows.append(out)
        return out

    def next_seq(self, machine_id: str) -> int:
        with self._lock:
            rows = self._rows.get(machine_id)
            return (rows[-1].seq + 1) if rows else 1

    def read(
        self, machine_id: str, *, after_seq: int = 0, limit: int = 1000
    ) -> List[TransitionRecord]:
        _check_read(after_seq, limit)
        with self._lock:
            rows = [
                r for r in self._rows.get(machine_id, []) if r.seq > after_seq
            ]
        return rows[:limit]

    def purge_older_than(self, cutoff_ts: float) -> int:
        cutoff_ts = _check_cutoff(cutoff_ts)
        n = 0
        with self._lock:
            for k, rows in list(self._rows.items()):
                keep = [r for r in rows if r.ts >= cutoff_ts]
                n += len(rows) - len(keep)
                self._rows[k] = keep
        return n

    def forget(self, machine_id: str) -> int:
        with self._lock:
            return len(self._rows.pop(machine_id, []))

    def __len__(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._rows.values())


# -----------------------------------------------------------------------------
# 📄 JSONLinesLog -- one JSON object per line, append-only
# -----------------------------------------------------------------------------
class JSONLinesLog:
    """A single ``.jsonl`` file; appends are one ``write`` of one line
    under a process lock (line-atomic on local filesystems). Reads scan
    the file -- fine for audit trails, not for millions of rows."""

    def __init__(self, path: Any) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        #: ⚡ last seq per machine id, valid while the file is `_cache_size`
        #: bytes (see `next_seq`); -1 = never scanned.
        self._last_seq: Dict[str, int] = {}
        self._cache_size: int = -1

    def _iter(self) -> Iterable[TransitionRecord]:
        # 📝 #262 battle: `utf-8-sig` tolerates a BOM (a Windows editor
        #    saved the file); text mode folds CRLF. Anything else that is
        #    not a record -- a torn last line (writer killed mid-write),
        #    garbage, non-UTF-8 bytes -- is a typed `LogCorruptError`
        #    naming the line; it is never skipped (a replay over a hole
        #    would "succeed" to the wrong state).
        try:
            fh = open(self.path, "r", encoding="utf-8-sig")
        except FileNotFoundError:
            return
        except OSError as exc:
            raise StoreError(f"JSONLinesLog({self.path}): {exc}") from exc
        with fh:
            n = 0
            try:
                for n, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except ValueError as exc:
                        raise LogCorruptError(
                            f"{self.path}:{n}: not JSON ({exc}); a writer "
                            f"killed mid-append leaves a torn last line -- "
                            f"truncate it to repair"
                        ) from exc
                    try:
                        rec = TransitionRecord.from_dict(obj)
                    except LogCorruptError as exc:
                        raise LogCorruptError(
                            f"{self.path}:{n}: {exc}"
                        ) from exc
                    yield rec
            except UnicodeDecodeError as exc:
                raise LogCorruptError(
                    f"{self.path}:{n + 1}: not UTF-8 ({exc})"
                ) from exc
            except OSError as exc:
                raise StoreError(f"JSONLinesLog({self.path}): {exc}") from exc

    def append(self, rec: TransitionRecord, *, connection: Any = None) -> None:
        _check_append(rec)
        line = json.dumps(rec.to_dict(), sort_keys=True, default=str) + "\n"
        with self._lock:
            try:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(line)
                    fh.flush()
                # ⚡ Keep the seq cache coherent with what WE wrote, and
                #    remember the file size that write produced, so the
                #    next `next_seq` is O(1) instead of a full scan.
                size = self.path.stat().st_size
            except OSError as exc:
                raise StoreError(f"JSONLinesLog({self.path}): {exc}") from exc
            cached = self._last_seq.get(rec.machine_id, 0)
            self._last_seq[rec.machine_id] = max(cached, rec.seq)
            self._cache_size = size

    def append_next(
        self, rec: TransitionRecord, *, connection: Any = None
    ) -> TransitionRecord:
        """Assign the next seq and append under the process lock.

        ⚠️ Atomic within ONE process only: two processes appending the
        same key to one file can still mint the same seq. Use `SQLiteLog`
        for multi-process writers."""
        with self._lock:
            out = replace(rec, seq=self._last(rec.machine_id) + 1)
            line = json.dumps(out.to_dict(), sort_keys=True, default=str)
            try:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                    fh.flush()
                size = self.path.stat().st_size
            except OSError as exc:
                raise StoreError(f"JSONLinesLog({self.path}): {exc}") from exc
            self._last_seq[out.machine_id] = out.seq
            self._cache_size = size
        return out

    def _last(self, machine_id: str) -> int:
        """Last seq for *machine_id*; the caller holds ``self._lock``.

        ⚡ #262 battle (B): this scanned the WHOLE file on every send, so a
        run with a JSONL log was O(n^2) -- 79 ms per send at 10 000
        records. Cache the last seq per machine and trust it while the
        file is exactly the size our last write left it; any change
        (another process appended, a purge rewrote it, an editor) is a
        cache miss and a full, correct scan.
        """
        try:
            size = self.path.stat().st_size
        except FileNotFoundError:
            size = 0
        except OSError as exc:
            raise StoreError(f"JSONLinesLog({self.path}): {exc}") from exc
        if size != self._cache_size:
            self._last_seq = {}
            for r in self._iter():
                if r.seq > self._last_seq.get(r.machine_id, 0):
                    self._last_seq[r.machine_id] = r.seq
            self._cache_size = size
        return self._last_seq.get(machine_id, 0)

    def next_seq(self, machine_id: str) -> int:
        with self._lock:
            return self._last(machine_id) + 1

    def read(
        self, machine_id: str, *, after_seq: int = 0, limit: int = 1000
    ) -> List[TransitionRecord]:
        _check_read(after_seq, limit)
        with self._lock:
            rows = [
                r
                for r in self._iter()
                if r.machine_id == machine_id and r.seq > after_seq
            ]
        rows.sort(key=lambda r: r.seq)
        return rows[:limit]

    def _rewrite(self, keep: Callable[[TransitionRecord], bool]) -> int:
        with self._lock:
            rows = list(self._iter())
            kept = [r for r in rows if keep(r)]
            tmp = self.path.with_suffix(".jsonl.tmp")
            try:
                with open(tmp, "w", encoding="utf-8") as fh:
                    for r in kept:
                        fh.write(
                            json.dumps(
                                r.to_dict(), sort_keys=True, default=str
                            )
                            + "\n"
                        )
                    fh.flush()
                    os.fsync(fh.fileno())
                tmp.replace(self.path)
            except BaseException:
                # 🛡️ #262: a failed rewrite leaves the OLD file intact
                #    (replace is the only step that touches it); do not
                #    strand the temp copy.
                try:
                    tmp.unlink()
                except OSError:
                    pass
                raise
            # the file changed under our own hands: force a rescan
            self._cache_size = -1
        return len(rows) - len(kept)

    def purge_older_than(self, cutoff_ts: float) -> int:
        cutoff_ts = _check_cutoff(cutoff_ts)
        return self._rewrite(lambda r: r.ts >= cutoff_ts)

    def forget(self, machine_id: str) -> int:
        return self._rewrite(lambda r: r.machine_id != machine_id)


# -----------------------------------------------------------------------------
# 🗄️ SQLiteLog -- shares the SQLiteStore file when given one
# -----------------------------------------------------------------------------
_CREATE_LOG = """
CREATE TABLE IF NOT EXISTS transitions (
    machine_id     TEXT NOT NULL,
    seq            INTEGER NOT NULL,
    ts             REAL NOT NULL,
    record         TEXT NOT NULL,
    PRIMARY KEY (machine_id, seq)
)
"""
_CREATE_LOG_IDX = (
    "CREATE INDEX IF NOT EXISTS transitions_ts ON transitions(ts)"
)


class SQLiteLog:
    """Log rows in a SQLite table. Pass a `SQLiteStore` to share its file
    and per-thread connection -- then an append inside ``store.lock()``
    joins the snapshot's transaction."""

    def __init__(self, store_or_path: Any) -> None:
        from .sqlite_store import SQLiteStore

        if isinstance(store_or_path, SQLiteStore):
            self._store = store_or_path
            self._own: Optional[SQLiteStore] = None
        else:
            self._own = SQLiteStore(store_or_path)
            self._store = self._own
        try:
            conn = self._conn()
            with self._store._tx(conn, immediate=True):
                conn.execute(_CREATE_LOG)
                cols = {
                    str(r[1])
                    for r in conn.execute("PRAGMA table_info(transitions)")
                }
                if not {"machine_id", "seq", "ts", "record"} <= cols:
                    # 🛡️ #262 battle: a foreign `transitions` table made
                    #    CREATE IF NOT EXISTS a no-op and the first append
                    #    died with a bare `no such column`.
                    raise StoreError(
                        f"SQLiteLog: table 'transitions' exists with "
                        f"columns {sorted(cols)}, not the "
                        f"xstate-statemachine schema. Use another file."
                    )
                conn.execute(_CREATE_LOG_IDX)
        except sqlite3.Error as exc:
            raise StoreError(
                f"SQLiteLog: {type(exc).__name__}: {exc}"
            ) from exc

    def _conn(self) -> sqlite3.Connection:
        return self._store._conn()

    def append(self, rec: TransitionRecord, *, connection: Any = None) -> None:
        _check_append(rec)
        conn = (
            connection
            if isinstance(connection, sqlite3.Connection)
            else self._conn()
        )
        with self._store._tx(conn, immediate=True):
            conn.execute(
                "INSERT INTO transitions(machine_id, seq, ts, record) VALUES (?, ?, ?, ?)",
                (
                    rec.machine_id,
                    rec.seq,
                    rec.ts,
                    json.dumps(rec.to_dict(), sort_keys=True, default=str),
                ),
            )

    def append_next(
        self, rec: TransitionRecord, *, connection: Any = None
    ) -> TransitionRecord:
        """Assign ``MAX(seq) + 1`` and insert in ONE ``BEGIN IMMEDIATE``
        transaction (or the caller's, when inside a `PessimisticLock`).

        🐛 Battle #262: `next_seq()` then `append()` were two statements in
        two transactions, so concurrent writers on one key (``NoLock``,
        optimistic retries, two processes) minted the same seq; the
        primary key refused the second insert and the plugin's error
        containment swallowed it -- a silently missing audit row. SQLite
        takes the write lock at ``BEGIN IMMEDIATE``, so read-max-and-insert
        inside it is atomic across threads AND processes."""
        conn = (
            connection
            if isinstance(connection, sqlite3.Connection)
            else self._conn()
        )
        with self._store._tx(conn, immediate=True):
            row = conn.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM transitions WHERE machine_id = ?",
                (rec.machine_id,),
            ).fetchone()
            out = replace(rec, seq=int(row[0]) + 1)
            conn.execute(
                "INSERT INTO transitions(machine_id, seq, ts, record) VALUES (?, ?, ?, ?)",
                (
                    out.machine_id,
                    out.seq,
                    out.ts,
                    json.dumps(out.to_dict(), sort_keys=True, default=str),
                ),
            )
        return out

    def next_seq(self, machine_id: str) -> int:
        row = (
            self._conn()
            .execute(
                "SELECT COALESCE(MAX(seq), 0) FROM transitions WHERE machine_id = ?",
                (machine_id,),
            )
            .fetchone()
        )
        return int(row[0]) + 1

    def read(
        self, machine_id: str, *, after_seq: int = 0, limit: int = 1000
    ) -> List[TransitionRecord]:
        _check_read(after_seq, limit)
        try:
            rows = (
                self._conn()
                .execute(
                    "SELECT seq, record FROM transitions "
                    "WHERE machine_id = ? AND seq > ? ORDER BY seq LIMIT ?",
                    (machine_id, after_seq, limit),
                )
                .fetchall()
            )
        except sqlite3.Error as exc:
            raise StoreError(
                f"SQLiteLog: {type(exc).__name__}: {exc}"
            ) from exc
        if (
            after_seq == 0
            and self._conn()
            .execute(
                "SELECT 1 FROM transitions WHERE machine_id = ? AND seq < 1 "
                "LIMIT 1",
                (machine_id,),
            )
            .fetchone()
        ):
            # 🛡️ #262 battle: `seq > 0` never surfaces a row with a
            #    non-positive seq, so it was a silent hole in the replay.
            raise LogCorruptError(
                f"transitions({machine_id!r}): row with seq < 1"
            )
        out: List[TransitionRecord] = []
        for seq, raw in rows:
            where = f"transitions({machine_id!r}, seq={seq!r})"
            try:
                rec = TransitionRecord.from_dict(json.loads(raw))
            except (ValueError, TypeError) as exc:  # LogCorruptError is one
                raise LogCorruptError(f"{where}: {exc}") from exc
            if rec.seq != seq or rec.machine_id != machine_id:
                raise LogCorruptError(
                    f"{where}: row key disagrees with its record "
                    f"({rec.machine_id!r}, {rec.seq})"
                )
            out.append(rec)
        return out

    def purge_older_than(self, cutoff_ts: float) -> int:
        cutoff_ts = _check_cutoff(cutoff_ts)
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            return conn.execute(
                "DELETE FROM transitions WHERE ts < ?", (cutoff_ts,)
            ).rowcount

    def forget(self, machine_id: str) -> int:
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            return conn.execute(
                "DELETE FROM transitions WHERE machine_id = ?", (machine_id,)
            ).rowcount

    def close(self) -> None:
        if self._own is not None:
            self._own.close()


# -----------------------------------------------------------------------------
# 🔌 TransitionLogPlugin
# -----------------------------------------------------------------------------
def _leaf_ids(nodes: Iterable[Any]) -> Tuple[str, ...]:
    return tuple(sorted(n.id for n in nodes if not getattr(n, "states", None)))


def _inside_step(interpreter: Any) -> bool:
    """Is this `send()` coming from INSIDE the interpreter's own step?

    Sync engine: a step is in flight (`send()` is single-threaded;
    `send_threadsafe` producers are drained between steps). Async engine:
    the caller IS the run-loop task -- `_processing` alone would also be
    true for an unrelated task sending while a step runs."""
    task = getattr(interpreter, "_event_loop_task", None)
    if task is not None:
        import asyncio

        try:
            return asyncio.current_task() is task
        except RuntimeError:  # no running loop: a foreign thread
            return False
    return bool(interpreter._step_in_flight())


def _event_payload(event: Any) -> Dict[str, Any]:
    """A JSON-safe payload for any event kind (engine ones included)."""
    kind = event_kind(event)
    if kind in ("event", "system"):
        return dict(getattr(event, "payload", None) or {})
    if kind == "done":
        return {"kind": "done", "src": event.src, "data": event.data}
    if kind == "error":
        err = event.error
        return {
            "kind": "error",
            "src": event.src,
            "error": {"type": type(err).__name__, "message": str(err)},
        }
    return {"kind": kind}


class TransitionLogPlugin(PluginBase[Any]):
    """Append one `TransitionRecord` per processed event.

    Args:
        log: A `TransitionLogStore`.
        include_non_transitions: Also record denied / unhandled / deferred /
            errored events (``to_states == from_states``) with their
            `disposition`. Default ``True`` -- an audit that omits refused
            attempts is not an audit.
        redact_keys: Payload keys (substring, case-insensitive) masked
            before the record is built.
        machine_id: ``(interpreter) -> str`` log key; default
            ``interpreter.store_key or interpreter.id``.

    Both engines. Records are appended from `on_event_processed` (after
    the step settled); when `persisted()` holds a store transaction the
    append lands inside it.
    """

    def __init__(
        self,
        log: TransitionLogStore,
        *,
        include_non_transitions: bool = True,
        redact_keys: Tuple[str, ...] = DEFAULT_REDACT_KEYS,
        machine_id: Optional[Callable[[Any], str]] = None,
    ) -> None:
        self.log = log
        self.include_non_transitions = include_non_transitions
        self.redact_keys = redact_keys
        self.machine_id_fn = machine_id or (
            lambda i: str(getattr(i, "store_key", None) or i.id)
        )
        #: Per interpreter: leaves before the current step, actions run.
        self._before: Dict[int, Tuple[str, ...]] = {}
        self._actions: Dict[int, List[str]] = {}
        self._failed: Dict[int, List[str]] = {}
        #: Per interpreter: events a CALLER sent (id -> event, held so the
        #: id cannot be recycled before the event is processed).
        self._external: Dict[int, Dict[int, Any]] = {}
        #: persisted() sessions buffering records, and their records.
        self._buffering: Set[Any] = set()
        self._buffered: Dict[Any, List[TransitionRecord]] = {}
        self._sealed: Dict[Any, int] = {}
        self._lock = threading.Lock()

    # -- persisted() commit seam (battle #262) -------------------------------------
    #: After the idempotency inbox (0), before the outbox (10).
    flush_priority = 5

    @property
    def buffer_marks(self) -> bool:
        """``True`` while records of the CURRENT `persisted()` block are
        held until its snapshot save succeeds.

        🐛 Battle #262 (CRITICAL): records were appended the moment each
        event settled, i.e. BEFORE the save. An optimistic attempt that
        lost (`ConflictError`), a block that raised, or a crash before the
        save left audit rows for a step that never committed -- the log
        disagreed with the state, the one thing the audit promises it
        cannot do. Now they are written by `flush_marks` right after the
        save (inside its transaction under `PessimisticLock` on a shared
        `SQLiteStore`) and dropped by `discard_marks` if it fails."""
        from .locking import current_session

        return current_session.get() in self._buffering

    @buffer_marks.setter
    def buffer_marks(self, value: bool) -> None:
        from .locking import current_session

        token = current_session.get()
        with self._lock:
            if value:
                self._buffering.add(token)
            else:
                self._buffering.discard(token)
                self._buffered.pop(token, None)
                self._sealed.pop(token, None)

    def flush_marks(self) -> int:
        """Write this session's buffered records (seq assigned now) --
        only those sealed when the snapshot was taken, if it was sealed."""
        from .locking import current_session

        token = current_session.get()
        with self._lock:
            batch = self._buffered.pop(token, [])
            sealed = self._sealed.pop(token, None)
        if sealed is not None:
            batch = batch[:sealed]
        if not batch:
            return 0
        if self._joins_open_transaction():
            for rec in batch:
                self._write(rec)
            return len(batch)
        # 🐛 Battle #262: a log that cannot join the store's transaction
        #    (JSONL, memory, a SQLiteLog on another file) was written here,
        #    BEFORE `PessimisticLock` committed the save -- a kill in
        #    between left the log one step AHEAD of the state. Write it
        #    once the block has committed: the log may then trail the
        #    snapshot after a crash, never lead it.
        from .locking import after_commit

        def _late() -> None:
            for rec in batch:
                self._write(rec)

        after_commit(_late)
        return len(batch)

    def _joins_open_transaction(self) -> bool:
        """Would an append now land inside the snapshot's open SQLite
        transaction (`SQLiteLog` sharing the store, under its lock)?"""
        store = getattr(self.log, "_store", None)
        conn_fn = getattr(store, "_conn", None)
        if not callable(conn_fn):
            return False
        try:
            return bool(conn_fn().in_transaction)
        except Exception:  # noqa: BLE001 - a closed store: write late
            return False

    def seal_marks(self) -> None:
        """The snapshot about to be saved was just taken: records produced
        AFTER this point describe steps that snapshot does not contain.

        🐛 Battle #262: under `apersisted` a fire-and-forget event still
        queued at block exit was processed while ``await save`` yielded
        the loop. Its record was flushed although the committed snapshot
        held the event only as PENDING -- the restore re-processed it and
        the log carried the step twice."""
        from .locking import current_session

        token = current_session.get()
        with self._lock:
            self._sealed[token] = len(self._buffered.get(token, []))

    def discard_marks(self) -> int:
        """Drop this session's buffered records (the save failed)."""
        from .locking import current_session

        token = current_session.get()
        with self._lock:
            self._sealed.pop(token, None)
            return len(self._buffered.pop(token, []))

    def _write(self, rec: TransitionRecord) -> None:
        """Append with a store-assigned seq when the store can do it
        atomically (`append_next`), else ``next_seq`` + ``append``."""
        atomic = getattr(self.log, "append_next", None)
        if callable(atomic):
            atomic(rec)
            return
        self.log.append(replace(rec, seq=self.log.next_seq(rec.machine_id)))

    # -- audit fields (overridden by AuditPlugin) ----------------------------------
    def _audit(
        self, event: Any
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        return None, None, None

    # -- collection ----------------------------------------------------------------
    def on_before_send(self, interpreter: Any, event: Any) -> None:
        # 🐛 Battle #262: a `raise` chain and an action's own `send()` were
        #    logged indistinguishably from caller traffic, so `replay()`
        #    re-sent them AND the replayed actions produced them again --
        #    every such step ran twice (divergence at seq 1, or a context
        #    with doubled counters). Only an event sent while NO step is in
        #    flight is a caller's; it is remembered by identity until it is
        #    processed (a deferred event re-released later is the same
        #    object but is then the engine's, not the caller's).
        if _inside_step(interpreter):
            return None
        with self._lock:
            self._external.setdefault(id(interpreter), {})[id(event)] = event
        return None

    def on_event_refused(
        self, interpreter: Any, event: Any, receipt: Any
    ) -> None:
        with self._lock:
            self._external.get(id(interpreter), {}).pop(id(event), None)

    def on_event_received(self, interpreter: Any, event: Any) -> None:
        with self._lock:
            self._before[id(interpreter)] = tuple(
                sorted(interpreter.current_state_ids)
            )
            self._actions[id(interpreter)] = []
            self._failed[id(interpreter)] = []

    def on_action_execute(self, interpreter: Any, action: Any) -> None:
        with self._lock:
            acts = self._actions.get(id(interpreter))
            if acts is not None:
                acts.append(str(getattr(action, "type", action)))

    def on_action_error(
        self, interpreter: Any, action: Any, error: BaseException
    ) -> None:
        with self._lock:
            failed = self._failed.get(id(interpreter))
            if failed is not None:
                failed.append(str(getattr(action, "type", action)))

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Any
    ) -> None:
        with self._lock:
            before = self._before.pop(id(interpreter), None)
            actions = tuple(self._actions.pop(id(interpreter), []))
            failed = self._failed.pop(id(interpreter), [])
            ext = self._external.get(id(interpreter), {})
            external = ext.get(id(event)) is event
            if external:
                del ext[id(event)]
        if before is None:
            before = tuple(sorted(interpreter.current_state_ids))
        after = tuple(sorted(receipt.state_ids))
        if receipt.duplicate:
            disposition = "duplicate"
        elif receipt.error is not None or failed:
            # 📝 Under `actionErrorPolicy: "continue"` a raising action is
            #    contained and the receipt carries no error; the audit must
            #    still say the step errored (battle #262).
            disposition = "error"
        elif receipt.deferred:
            disposition = "deferred"
        elif receipt.denied:
            disposition = "denied"
        elif receipt.changed:
            disposition = "transition"
        else:
            disposition = "unhandled"
        if disposition != "transition" and not self.include_non_transitions:
            return
        actor, reason, corr = self._audit(event)
        key = self.machine_id_fn(interpreter)
        engine = isinstance(event, (AfterEvent, DoneEvent, ErrorEvent))
        if receipt.error is not None:
            error: Optional[Dict[str, str]] = {
                "type": type(receipt.error).__name__,
                "message": str(receipt.error),
            }
        elif failed:
            error = {
                "type": "ActionError",
                "message": ", ".join(failed),
                "actions": ", ".join(failed),
            }
        else:
            error = None
        if error is not None and failed and "actions" not in error:
            error["actions"] = ", ".join(failed)
        rec = TransitionRecord(
            machine_id=key,
            seq=0,  # assigned by the store at write time (gap-free)
            ts=float(interpreter.wall_now()),
            event_type=str(getattr(event, "type", event)),
            event_payload=redact(_event_payload(event), self.redact_keys),
            from_states=before,
            to_states=after,
            actions=actions,
            disposition=disposition,
            actor=actor,
            reason=reason,
            correlation_id=corr,
            machine_version=getattr(interpreter.machine, "version", None)
            or "",
            engine=engine,
            error=error,
            origin="external" if external and not engine else "internal",
        )
        from .locking import current_session

        token = current_session.get()
        with self._lock:
            if token is not None and token in self._buffering:
                self._buffered.setdefault(token, []).append(rec)
                return
        self._write(rec)

    def on_interpreter_stop(self, interpreter: Any) -> None:
        with self._lock:
            self._before.pop(id(interpreter), None)
            self._actions.pop(id(interpreter), None)
            self._failed.pop(id(interpreter), None)
            self._external.pop(id(interpreter), None)


class AuditPlugin(TransitionLogPlugin):
    """`TransitionLogPlugin` that also records **who** and **why**.

    ``actor`` / ``reason`` are read from the event payload (keys
    configurable); ``correlation_id`` from the payload or, failing that,
    from `correlation_id_var` (set by request middleware).
    """

    def __init__(
        self,
        log: TransitionLogStore,
        *,
        actor_key: str = "actor",
        reason_key: str = "reason",
        correlation_key: str = "correlation_id",
        **kw: Any,
    ) -> None:
        super().__init__(log, **kw)
        self.actor_key = actor_key
        self.reason_key = reason_key
        self.correlation_key = correlation_key

    def _audit(
        self, event: Any
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        payload = getattr(event, "payload", None) or {}
        actor = payload.get(self.actor_key)
        reason = payload.get(self.reason_key)
        corr = payload.get(self.correlation_key) or correlation_id_var.get()
        return (
            None if actor is None else str(actor),
            None if reason is None else str(reason),
            None if corr is None else str(corr),
        )


# -----------------------------------------------------------------------------
# 🔁 replay()
# -----------------------------------------------------------------------------
class ReplayDivergenceError(XStateMachineError):
    """`replay()` landed somewhere other than the record says (a tampered
    or out-of-order log, or a machine that changed since)."""

    def __init__(
        self,
        seq: int,
        expected: Any,
        actual: Any,
        *,
        field: str = "to_states",
    ) -> None:
        self.seq = seq
        self.expected = expected
        self.actual = actual
        #: What differed: ``"to_states"`` | ``"event_type"`` |
        #: ``"disposition"`` | ``"actions"`` | ``"missing"`` (the record's event never
        #: happened) | ``"unrecorded"`` (the engine produced an event the
        #: log does not have) | ``"seq"`` (a gap / purged head) |
        #: ``"machine_version"``.
        self.field = field
        shown = (
            (list(expected), list(actual))
            if isinstance(expected, tuple) and isinstance(actual, tuple)
            else (expected, actual)
        )
        super().__init__(
            f"Replay diverged at seq {seq} ({field}): recorded "
            f"{shown[0]!r}, got {shown[1]!r}."
        )


class _RecordedError(Exception):
    """Stand-in raised by a replay stub for a recorded failure."""

    def __init__(self, type_name: str, message: str) -> None:
        super().__init__(message)
        self.type_name = type_name


class _Tracer(PluginBase[Any]):
    """What the replay interpreter actually did, one entry per event."""

    def __init__(self) -> None:
        self.seen: List[Tuple[str, Tuple[str, ...], str]] = []
        self.actions: List[Tuple[str, ...]] = []
        self._acts: List[str] = []

    def on_event_received(self, interpreter: Any, event: Any) -> None:
        self._acts = []

    def on_action_execute(self, interpreter: Any, action: Any) -> None:
        self._acts.append(str(getattr(action, "type", action)))

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Any
    ) -> None:
        self.actions.append(tuple(self._acts))
        self._acts = []
        if receipt.error is not None:
            disp = "error"
        elif receipt.deferred:
            disp = "deferred"
        elif receipt.denied:
            disp = "denied"
        elif receipt.changed:
            disp = "transition"
        else:
            disp = "unhandled"
        self.seen.append(
            (
                str(getattr(event, "type", event)),
                tuple(sorted(receipt.state_ids)),
                disp,
            )
        )


def _check_sequence(recs: List[TransitionRecord], from_snapshot: bool) -> None:
    """Gap-free from 1 (or from wherever a snapshot resumes) -- else loud.

    🐛 Battle #262: a log with a deleted middle row or a purged head was
    replayed as if complete; the divergence surfaced (if at all) far from
    the cause, or the rebuilt state was silently wrong."""
    if not recs:
        return
    if recs[0].seq != 1 and not from_snapshot:
        raise ReplayDivergenceError(recs[0].seq, 1, recs[0].seq, field="seq")
    for prev, cur in zip(recs, recs[1:]):
        if cur.seq != prev.seq + 1:
            raise ReplayDivergenceError(
                prev.seq + 1, prev.seq + 1, cur.seq, field="seq"
            )


def _rebuild(machine: Any, logic: Any) -> Any:
    """The machine again, bound to *logic*; the caller's is untouched.

    🐛 Battle #262: this was ``copy.copy(machine)`` with ``.logic``
    swapped. The engine recognises machine completion by IDENTITY
    (``final_state.parent is self.machine``) and the copied root is not
    the parent of its own (shared) children -- so a replayed run that
    reached a top-level ``final`` state stayed ``"running"`` and kept
    re-releasing deferred events the original never saw again. Rebuild
    from the source config instead (same structural hash, so a snapshot
    restores onto it); a hand-built node without one falls back to the
    copy."""
    from ..factory import create_machine

    src = getattr(machine, "source_config", None)
    if not src:  # pragma: no cover - hand-built MachineNode
        m = copy.copy(machine)
        m.logic = logic
        return m
    m = create_machine(src, logic=logic)
    for attr in ("event_schemas", "context_validator"):
        if getattr(machine, attr, None):
            setattr(m, attr, getattr(machine, attr))
    return m


def replay(
    machine: Any,
    records: Iterable[TransitionRecord],
    *,
    upto: Optional[int] = None,
    logic: Any = None,
    verify: bool = True,
    key: Optional[str] = None,
    snapshot: Optional[str] = None,
) -> Any:
    """Rebuild a `SyncInterpreter` by re-running the recorded events.

    * Only events a CALLER sent (``origin == "external"``) are re-sent,
      with their recorded (redacted) payload. Events produced inside a
      step -- ``raise`` chains, an action's own ``send()``, re-released
      deferred events -- are reproduced by the engine, never re-sent.
    * Engine-minted events are NOT re-sent: an ``after`` step moves a
      `SimulatedClock` to the next due timer until it fires; a
      ``done.invoke`` / ``error.platform`` step is produced by a STUB
      service returning the recorded data or raising the recorded error
      -- always, even with *logic* (a service call is an external effect).
    * Unless *logic* is given, actions are stubs while the machine's REAL
      guards are kept (guards are pure): replay reproduces STATE; an
      action recorded as failed is made to fail again. Pass your real
      logic to rebuild ``context`` too -- its actions' side effects repeat.

    *key* selects one instance from a log holding several (required when
    *records* mixes keys). The records must be gap-free from seq 1 or,
    when *snapshot* is passed (a `get_snapshot()` taken right after the
    record preceding the first one given), gap-free from there.

    With *verify*, every record is checked in order -- event type, reached
    leaves, disposition -- and its ``machine_version`` against the
    machine's; the first mismatch raises `ReplayDivergenceError(seq,
    field=...)`. *upto* caps the seq.
    """
    from ..clock import SimulatedClock
    from ..sync_interpreter import SyncInterpreter
    from ..testing_utils import stub_logic

    recs = _select(machine, records, key, upto, snapshot is not None, verify)
    steps = [r for r in recs if r.disposition != "duplicate"]
    tracer = _Tracer()

    # Service outcomes indexed by invoke id, consumed in order.
    outcomes: Dict[str, List[Dict[str, Any]]] = {}
    for r in steps:
        p = r.event_payload
        if r.engine and p.get("kind") in ("done", "error"):
            outcomes.setdefault(str(p.get("src")), []).append(p)

    def stub_service(src_name: str) -> Callable[..., Any]:
        def _svc(i: Any, c: Any, e: Any) -> Any:
            for inv_id, queue in outcomes.items():
                if not queue:
                    continue
                for node in list(i._active_state_nodes):
                    for inv in getattr(node, "invoke", ()):
                        if inv.id == inv_id and inv.src == src_name:
                            rec = queue.pop(0)
                            if rec["kind"] == "error":
                                err = rec.get("error") or {}
                                raise _RecordedError(
                                    str(err.get("type", "Error")),
                                    str(err.get("message", "")),
                                )
                            return rec.get("data")
            return None

        _svc.__name__ = f"replay_service_{src_name}"
        return _svc

    def failing(name: str, inner: Callable[..., Any]) -> Callable[..., Any]:
        """A stub action that fails where the record says it failed."""

        def _act(i: Any, c: Any, e: Any, a: Any) -> Any:
            n = len(tracer.seen)
            if n < len(steps):
                err = steps[n].error or {}
                if name in str(err.get("actions") or "").split(", "):
                    raise _RecordedError("ActionError", name)
            return inner(i, c, e, a)

        _act.__name__ = f"replay_action_{name}"
        return _act

    # 🏛️ The caller's machine is never mutated: `_rebuild` builds a fresh
    #    one bound to the replay logic.
    lg = stub_logic(machine)
    if logic is None:
        for name in list(lg.actions):
            lg.actions[name] = failing(name, lg.actions[name])
        real_guards = getattr(machine.logic, "guards", None) or {}
        for name in list(lg.guards):
            if name in real_guards:
                lg.guards[name] = real_guards[name]
        final_logic: Any = lg
    else:
        final_logic = copy.copy(logic)
        final_logic.services = dict(getattr(logic, "services", None) or {})
    for name in list(lg.services):
        final_logic.services[name] = stub_service(name)
    m = _rebuild(machine, final_logic)

    clock = SimulatedClock()
    interp: Any
    if snapshot is not None:
        interp = SyncInterpreter.from_snapshot(
            snapshot, m, clock=clock, plugins=[tracer]
        )
    else:
        interp = SyncInterpreter(m, clock=clock).use(tracer)
    interp.start()
    tracer.seen.clear()  # entry-time events are not records
    tracer.actions.clear()

    def advance_until(n: int) -> None:
        """Move virtual time timer by timer until event *n* fires."""
        for _ in range(10_000):
            if len(tracer.seen) > n:
                return
            nxt = clock._heap.next_due()
            if nxt is None:
                return
            # 🐛 Battle #262: `clock.set()` returns an awaitable when an
            #    event loop is running in this thread, so `replay()` called
            #    from async code (a request handler, an async test) never
            #    fired a timer and diverged at the first `after` record.
            #    The replay interpreter is a SyncInterpreter: drain sync.
            clock._drain_sync(max(nxt, clock.now()))

    stubbed = logic is None
    for n, r in enumerate(steps):
        external = r.origin == "external" and not r.engine
        if len(tracer.seen) == n:
            if r.engine and r.event_payload.get("kind") == "after":
                advance_until(n)
            elif external or (stubbed and not r.engine):
                # 📝 Under stubs a user action that `send()`s to its own
                #    machine is a no-op, so the event it produced is
                #    re-sent from the record instead; a `raise` (a
                #    built-in, never stubbed) reproduces itself and is
                #    already in `seen` by now.
                interp.send(r.event_type, **r.event_payload)
        elif verify and external:
            # The engine produced an event here the log does not have.
            raise ReplayDivergenceError(
                r.seq, r.event_type, tracer.seen[n][0], field="unrecorded"
            )
        if len(tracer.seen) <= n:
            if verify:
                raise ReplayDivergenceError(
                    r.seq, r.event_type, None, field="missing"
                )
            continue
        if verify:
            _verify_step(r, tracer.seen[n], tracer.actions[n], stubbed)
    if verify and upto is None and len(tracer.seen) > len(steps):
        raise ReplayDivergenceError(
            (steps[-1].seq + 1) if steps else 1,
            None,
            tracer.seen[len(steps)][0],
            field="unrecorded",
        )
    return interp


def _select(
    machine: Any,
    records: Iterable[TransitionRecord],
    key: Optional[str],
    upto: Optional[int],
    from_snapshot: bool,
    verify: bool,
) -> List[TransitionRecord]:
    """The records `replay()` runs: one key, gap-free, capped, versioned."""
    rows = list(records)
    keys = {r.machine_id for r in rows}
    if key is not None:
        rows = [r for r in rows if r.machine_id == key]
    elif len(keys) > 1:
        raise ValueError(
            f"records hold {len(keys)} instances ({sorted(keys)}); pass "
            f"key= to choose one"
        )
    recs = sorted(rows, key=lambda r: r.seq)
    _check_sequence(recs, from_snapshot)
    if upto is not None:
        recs = [r for r in recs if r.seq <= upto]
    if verify:
        mv = getattr(machine, "version", None) or ""
        for r in recs:
            if r.machine_version != mv:
                raise ReplayDivergenceError(
                    r.seq, r.machine_version, mv, field="machine_version"
                )
    return recs


def _verify_step(
    r: TransitionRecord,
    seen: Tuple[str, Tuple[str, ...], str],
    actions: Tuple[str, ...],
    stubbed: bool,
) -> None:
    """One record against what the replay engine did for it."""
    etype, leaves, disp = seen
    if etype != r.event_type:
        raise ReplayDivergenceError(
            r.seq, r.event_type, etype, field="event_type"
        )
    if leaves != tuple(sorted(r.to_states)):
        raise ReplayDivergenceError(r.seq, tuple(sorted(r.to_states)), leaves)
    if actions != tuple(r.actions):
        raise ReplayDivergenceError(
            r.seq, tuple(r.actions), actions, field="actions"
        )
    if disp != r.disposition and not (
        # 📝 Stub actions do not change `context`, so a targetless step
        #    that only assigned reads "unhandled" on replay.
        stubbed
        and {disp, r.disposition} == {"transition", "unhandled"}
        and tuple(sorted(r.from_states)) == tuple(sorted(r.to_states))
    ):
        raise ReplayDivergenceError(
            r.seq, r.disposition, disp, field="disposition"
        )
