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
from dataclasses import asdict, dataclass, field
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
            except OSError as exc:
                raise StoreError(f"JSONLinesLog({self.path}): {exc}") from exc

    def next_seq(self, machine_id: str) -> int:
        with self._lock:
            last = 0
            for r in self._iter():
                if r.machine_id == machine_id and r.seq > last:
                    last = r.seq
        return last + 1

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
        self._lock = threading.Lock()

    # -- audit fields (overridden by AuditPlugin) ----------------------------------
    def _audit(
        self, event: Any
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        return None, None, None

    # -- collection ----------------------------------------------------------------
    def on_event_received(self, interpreter: Any, event: Any) -> None:
        with self._lock:
            self._before[id(interpreter)] = tuple(
                sorted(interpreter.current_state_ids)
            )
            self._actions[id(interpreter)] = []

    def on_action_execute(self, interpreter: Any, action: Any) -> None:
        with self._lock:
            acts = self._actions.get(id(interpreter))
            if acts is not None:
                acts.append(str(getattr(action, "type", action)))

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Any
    ) -> None:
        with self._lock:
            before = self._before.pop(id(interpreter), None)
            actions = tuple(self._actions.pop(id(interpreter), []))
        if before is None:
            before = tuple(sorted(interpreter.current_state_ids))
        after = tuple(sorted(receipt.state_ids))
        if receipt.duplicate:
            disposition = "duplicate"
        elif receipt.error is not None:
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
        rec = TransitionRecord(
            machine_id=key,
            seq=self.log.next_seq(key),
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
            engine=isinstance(event, (AfterEvent, DoneEvent, ErrorEvent)),
            error=(
                {
                    "type": type(receipt.error).__name__,
                    "message": str(receipt.error),
                }
                if receipt.error is not None
                else None
            ),
        )
        self.log.append(rec)

    def on_interpreter_stop(self, interpreter: Any) -> None:
        with self._lock:
            self._before.pop(id(interpreter), None)
            self._actions.pop(id(interpreter), None)


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
        self, seq: int, expected: Tuple[str, ...], actual: Tuple[str, ...]
    ) -> None:
        self.seq = seq
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Replay diverged at seq {seq}: recorded {list(expected)}, "
            f"got {list(actual)}."
        )


class _RecordedError(Exception):
    """Stand-in raised by a replay stub service for a recorded failure."""

    def __init__(self, type_name: str, message: str) -> None:
        super().__init__(message)
        self.type_name = type_name


def replay(
    machine: Any,
    records: Iterable[TransitionRecord],
    *,
    upto: Optional[int] = None,
    logic: Any = None,
    verify: bool = True,
) -> Any:
    """Rebuild a `SyncInterpreter` by re-running the recorded events.

    * User events are re-sent (payload as recorded, redaction included).
    * Engine-minted events are NOT re-sent: an ``after`` step advances a
      `SimulatedClock` until it fires; a ``done.invoke`` / ``error.platform``
      step is produced by a STUB service that returns the recorded data or
      raises the recorded error.
    * Unless *logic* is given, actions and services are stubs
      (`testing_utils.stub_logic`) while the machine's REAL guards are
      kept (guards are pure): replay reproduces STATE, never side
      effects. Pass your real logic only if its actions are idempotent
      and you also want ``context`` rebuilt.

    After each record (when *verify*) the reached leaves must equal
    ``to_states`` or `ReplayDivergenceError(seq)` is raised. Returns the
    started interpreter positioned after the last replayed record (*upto*
    caps the seq).
    """
    from ..clock import SimulatedClock
    from ..sync_interpreter import SyncInterpreter
    from ..testing_utils import stub_logic

    recs = sorted(
        (r for r in records if upto is None or r.seq <= upto),
        key=lambda r: r.seq,
    )
    # Service outcomes indexed by invoke id, consumed in order.
    outcomes: Dict[str, List[Dict[str, Any]]] = {}
    for r in recs:
        p = r.event_payload
        if r.engine and p.get("kind") in ("done", "error"):
            outcomes.setdefault(str(p.get("src")), []).append(p)

    def stub_service(src_name: str) -> Callable[..., Any]:
        def _svc(i: Any, c: Any, e: Any) -> Any:
            # Find the invoke id this service runs under (the record's src).
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

    # 🏛️ `MachineNode.logic` is a plain attribute read at run time (see
    #    factory.py), so a shallow copy of the node with the replay logic
    #    attached is observationally a machine built with it -- and the
    #    caller's machine is left untouched.
    if logic is None:
        lg = stub_logic(machine)
        for name in list(lg.services):
            lg.services[name] = stub_service(name)
        # 📝 Guards are pure predicates over (context, event) and carry no
        #    side effects, so the REAL ones are kept when the machine has
        #    them: a stub guard answering True where the original said
        #    False would make an honest log diverge at the first denied
        #    event. Actions and services stay stubbed -- those are where
        #    side effects live.
        real_guards = getattr(machine.logic, "guards", None) or {}
        for name in list(lg.guards):
            if name in real_guards:
                lg.guards[name] = real_guards[name]
        final_logic: Any = lg
    else:
        final_logic = logic
    m = copy.copy(machine)
    m.logic = final_logic

    clock = SimulatedClock()
    interp = SyncInterpreter(m, clock=clock).start()

    def leaves() -> Tuple[str, ...]:
        return tuple(sorted(interp.current_state_ids))

    # 📝 Verification granularity: on the sync engine ONE `send()` drains
    #    the user event AND every engine follow-up it triggers (a service
    #    completion, a chained timer) before returning, so the machine is
    #    only observable at the end of that chain. A record group = a user
    #    event plus the engine-minted records that immediately follow it;
    #    the group is verified against its LAST record's `to_states`.
    groups: List[List[TransitionRecord]] = []
    for r in recs:
        if groups and r.engine:
            groups[-1].append(r)
        else:
            groups.append([r])

    for group in groups:
        head, tail = group[0], group[1:]
        if head.engine and head.event_payload.get("kind") == "after":
            # A timer that fired on its own (no user event in this group):
            # advance the clock until the recorded leaves are reached.
            target = tuple(sorted(group[-1].to_states))
            for _ in range(10_000):
                if leaves() == target or not clock.pending:
                    break
                clock.increment(1)
        elif head.engine:
            interp.tick()
        elif head.disposition == "duplicate":
            continue  # never entered the machine
        else:
            interp.send(head.event_type, **head.event_payload)
        # Any `after` in the tail needs the virtual clock to move.
        if any(t.event_payload.get("kind") == "after" for t in tail):
            target = tuple(sorted(group[-1].to_states))
            for _ in range(10_000):
                if leaves() == target or not clock.pending:
                    break
                clock.increment(1)
        expected = tuple(sorted(group[-1].to_states))
        if verify and leaves() != expected:
            raise ReplayDivergenceError(group[-1].seq, expected, leaves())
    return interp
