# src/xstate_statemachine/patterns/dead_letter.py
# -----------------------------------------------------------------------------
# 💀 DeadLetterPlugin -- capture a poison message WITH its error context (#265)
# -----------------------------------------------------------------------------
# 🏛️ Why a plugin: "dead-lettered" is a STATE the chart reaches (after the
#    retry loop gives up), not something the engine decides. The chart says
#    where the terminal state is (a `dead-letter` tag or an explicit id
#    list); this plugin watches for entry into it and writes ONE record that
#    holds everything an operator needs to replay or triage: the machine,
#    the event that was being handled, the attempt count, the chain of
#    errors that led here (collected from `on_service_error` /
#    `on_action_error` since the last clean step) and a snapshot.
#
# ⚠️ X0 (#303): a dead letter contains a snapshot, which contains `context`.
#    The record is passed through `redact()` BEFORE it reaches the sink, so
#    a secret in context never lands in a queue or a log. `errors` carry
#    class name + message only -- never the exception object.
# -----------------------------------------------------------------------------
"""`DeadLetterPlugin`, `DeadLetter` record and the in-memory store."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, fields, replace
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
)

from ..plugins import DEFAULT_REDACT_KEYS, PluginBase, redact

__all__ = [
    "DeadLetter",
    "DeadLetterPlugin",
    "DeadLetterStore",
    "MemoryDeadLetterStore",
    "DEAD_LETTER_TAG",
]

#: The state tag that marks a dead-letter terminal state in the chart.
DEAD_LETTER_TAG = "dead-letter"


@dataclass(frozen=True)
class DeadLetter:
    """One captured poison message.

    Attributes:
        machine_id: `interpreter.id` (actor id for a child).
        state_id: The dead-letter state that was entered.
        event: The last event the machine processed, as ``{type, payload}``
            (payload redacted).
        attempts: ``context[attempt_key]`` at capture, or ``None``.
        errors: The error chain since the last clean step, oldest first,
            each ``{"source": "service"|"action", "name", "type",
            "message"}``.
        snapshot: The redacted `get_persisted_snapshot()` dict.
        taken_at: Epoch seconds (`interpreter.wall_now()`).
        id: Record id (#293). For a dead-lettered ENVELOPE it is the
            envelope id, so a replay re-uses it and an inbox dedups a
            double replay.
        reason: ``"dead_letter_state"`` (chart-driven), ``"max_attempts"``
            (poison, X0.8), ``"unknown_event"``, ``"corrupt"``, ...
        envelope: The redacted envelope as a dict (EDA dead letters).
        topic: The topic the envelope came from.
        machine_hash: `structure_hash` of the machine that failed; replay
            refuses a different machine without ``--force``.
        machine_version: The chart's ``version`` at capture.
        resolved_at: Epoch seconds a replay resolved it, else ``None``.
    """

    machine_id: str
    state_id: str
    event: Dict[str, Any]
    attempts: Optional[int]
    errors: List[Dict[str, str]]
    snapshot: Dict[str, Any]
    taken_at: float
    id: str = ""
    reason: str = "dead_letter_state"
    envelope: Optional[Dict[str, Any]] = None
    topic: Optional[str] = None
    machine_hash: Optional[str] = None
    machine_version: Optional[str] = None
    resolved_at: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", uuid.uuid4().hex)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, sort_keys=True)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "DeadLetter":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in names})


class DeadLetterStore:
    """Thread-safe in-memory sink; also the reference store shape.

    A sink is anything callable as ``sink(dead_letter)``. Stores add the
    operator surface the ``xsm dlq`` CLI uses (#293): ``get``, ``list``,
    ``mark_resolved``, ``delete``, ``purge_older_than``. `MemoryDeadLetterStore`
    is this class; `SQLiteDeadLetterStore` (``xstate_statemachine.eda``)
    persists the same records.
    """

    def __init__(self) -> None:
        self._records: List[DeadLetter] = []
        self._lock = threading.Lock()

    def __call__(self, record: DeadLetter) -> None:
        self.put(record)

    def put(self, record: DeadLetter) -> None:
        with self._lock:
            self._records = [r for r in self._records if r.id != record.id]
            self._records.append(record)

    def get(self, record_id: str) -> Optional[DeadLetter]:
        with self._lock:
            for r in self._records:
                if r.id == record_id:
                    return r
        return None

    def list(
        self, *, include_resolved: bool = False, limit: int = 1000
    ) -> List[DeadLetter]:
        with self._lock:
            rows = [
                r
                for r in self._records
                if include_resolved or r.resolved_at is None
            ]
        rows.sort(key=lambda r: (r.taken_at, r.id))
        return rows[:limit]

    def mark_resolved(self, record_id: str, when: float) -> bool:
        with self._lock:
            for n, r in enumerate(self._records):
                if r.id == record_id:
                    self._records[n] = replace(r, resolved_at=when)
                    return True
        return False

    def delete(self, record_id: str) -> bool:
        with self._lock:
            before = len(self._records)
            self._records = [r for r in self._records if r.id != record_id]
            return len(self._records) != before

    def all(self) -> List[DeadLetter]:
        with self._lock:
            return list(self._records)

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)

    def purge_older_than(self, cutoff_wall: float) -> int:
        """Drop records with ``taken_at < cutoff_wall``; return how many
        (X0.5 retention: dead letters hold snapshots and must not
        accumulate forever)."""
        with self._lock:
            keep = [r for r in self._records if r.taken_at >= cutoff_wall]
            dropped = len(self._records) - len(keep)
            self._records = keep
        return dropped

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


#: #293 name for the in-memory store (the `DeadLetterStore` protocol's
#: reference implementation).
MemoryDeadLetterStore = DeadLetterStore


class DeadLetterPlugin(PluginBase[Any]):
    """Emit a `DeadLetter` when the machine enters a dead-letter state.

    Args:
        sink: ``callable(DeadLetter)`` -- a `DeadLetterStore`, a function
            that publishes to a queue, `eda.SQLiteDeadLetterStore`,
            `eda.BrokerDeadLetterSink` (publishes to ``<topic>.dlq``,
            #293) ... An object with ``put()`` is accepted too.
            Exceptions from the sink are contained by the plugin system
            (`on_plugin_error`).
        state_ids: Explicit dead-letter state ids. When empty, any state
            tagged ``"dead-letter"`` counts.
        attempt_key: Context key holding the attempt counter.
        redact_keys: Substrings of context / payload keys to mask.
        include_snapshot: Set ``False`` to omit the snapshot (smaller
            records; you lose replay-from-state).

    Works on both engines: the hooks it uses are engine-agnostic.
    """

    def __init__(
        self,
        sink: Any,
        *,
        state_ids: Iterable[str] = (),
        attempt_key: str = "attempt",
        redact_keys: Tuple[str, ...] = DEFAULT_REDACT_KEYS,
        include_snapshot: bool = True,
    ) -> None:
        self.sink = sink if callable(sink) else getattr(sink, "put")
        self.state_ids: Set[str] = set(state_ids)
        self.attempt_key = attempt_key
        self.redact_keys = redact_keys
        self.include_snapshot = include_snapshot
        #: Error chain per interpreter id, cleared on a clean transition
        #: out of the failure path (a `done.invoke.*` handled cleanly).
        self._errors: Dict[str, List[Dict[str, str]]] = {}
        #: Dead-letter state ids entered during the step in progress.
        self._pending: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()

    # -- collection ---------------------------------------------------------
    def on_service_error(
        self, interpreter: Any, invocation: Any, error: Exception
    ) -> None:
        self._push(
            interpreter.id,
            "service",
            str(
                getattr(invocation, "src", None)
                or getattr(invocation, "id", None)
                or "?"
            ),
            error,
        )

    def on_action_error(
        self, interpreter: Any, action: Any, error: BaseException
    ) -> None:
        self._push(
            interpreter.id, "action", getattr(action, "type", "?"), error
        )

    def on_service_done(
        self, interpreter: Any, invocation: Any, result: Any
    ) -> None:
        # A success ends the chain: the next failure starts a fresh one.
        with self._lock:
            self._errors.pop(interpreter.id, None)

    def _push(self, iid: str, source: str, name: str, err: Any) -> None:
        rec = {
            "source": source,
            "name": str(name),
            "type": type(err).__name__,
            "message": str(err),
        }
        with self._lock:
            self._errors.setdefault(iid, []).append(rec)

    # -- detection ------------------------------------------------------------
    def _is_dead_letter(self, node: Any) -> bool:
        if self.state_ids:
            return node.id in self.state_ids
        return DEAD_LETTER_TAG in (getattr(node, "tags", None) or ())

    def on_transition(
        self,
        interpreter: Any,
        from_states: Set[Any],
        to_states: Set[Any],
        transition: Any,
    ) -> None:
        # 📝 `on_transition` fires MID-macrostep (the configuration may not
        #    have settled; a snapshot here raises `SnapshotMidStepError`).
        #    Only NOTE the entry; the record is written from
        #    `on_event_processed`, which fires once per event after its
        #    step has settled and carries the event itself.
        entered = [
            n
            for n in to_states
            if n not in from_states and self._is_dead_letter(n)
        ]
        if entered:
            with self._lock:
                self._pending.setdefault(interpreter.id, set()).update(
                    n.id for n in entered
                )

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Any
    ) -> None:
        with self._lock:
            entered = self._pending.pop(interpreter.id, None)
        if not entered:
            return
        for state_id in sorted(entered):
            self.sink(self._capture(interpreter, event, state_id))

    def on_interpreter_stop(self, interpreter: Any) -> None:
        with self._lock:
            self._errors.pop(interpreter.id, None)
            self._pending.pop(interpreter.id, None)

    # -- record -----------------------------------------------------------------
    def _capture(self, interpreter: Any, ev: Any, state_id: str) -> DeadLetter:
        with self._lock:
            errors = list(self._errors.pop(interpreter.id, []))
        event = {
            "type": getattr(ev, "type", None),
            "payload": redact(
                dict(getattr(ev, "payload", None) or {}), self.redact_keys
            ),
        }
        ctx = interpreter.context
        attempts: Optional[int] = None
        if isinstance(ctx, dict) and self.attempt_key in ctx:
            try:
                attempts = int(ctx[self.attempt_key])
            except (TypeError, ValueError):
                attempts = None
        snapshot: Dict[str, Any] = {}
        if self.include_snapshot:
            snapshot = redact(
                interpreter.get_persisted_snapshot(), self.redact_keys
            )
        return DeadLetter(
            machine_id=interpreter.id,
            state_id=state_id,
            event=event,
            attempts=attempts,
            errors=errors,
            snapshot=snapshot,
            taken_at=float(interpreter.wall_now()),
            machine_hash=_machine_hash(interpreter.machine),
            machine_version=getattr(interpreter.machine, "version", None),
        )


def _machine_hash(machine: Any) -> Optional[str]:
    from ..persistence.snapshot import structure_hash

    try:
        return structure_hash(machine)
    except Exception:  # noqa: BLE001 - a record beats no record
        return None
