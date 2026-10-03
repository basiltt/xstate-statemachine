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
import logging
import math
import threading
import weakref
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

logger = logging.getLogger(__name__)

__all__ = [
    "DeadLetter",
    "DeadLetterPlugin",
    "DeadLetterStore",
    "MemoryDeadLetterStore",
    "DEAD_LETTER_TAG",
]

#: The state tag that marks a dead-letter terminal state in the chart.
DEAD_LETTER_TAG = "dead-letter"

#: Context key holding the error chain between attempts (#265 battle): it
#: must live in the snapshot so a chain built across several `persisted()`
#: blocks / scanner wakes reaches the record.
ERRORS_CONTEXT_KEY = "_xsm_errors"
DEFAULT_MAX_ERRORS = 20
#: Error messages are truncated: a chain rides in every snapshot.
MAX_ERROR_MESSAGE = 1000


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
        # 📝 #265 battle: a dict keyed by record id (insertion-ordered).
        #    The list version rebuilt itself on every `put` (O(n) per
        #    insert, O(n^2) to fill), which made 100 000 records a
        #    multi-minute operation. A duplicate id still REPLACES and
        #    moves to the end, exactly as before.
        self._records: Dict[str, DeadLetter] = {}
        self._lock = threading.Lock()

    def __call__(self, record: DeadLetter) -> None:
        self.put(record)

    def put(self, record: DeadLetter) -> None:
        with self._lock:
            self._records.pop(record.id, None)
            self._records[record.id] = record

    def get(self, record_id: str) -> Optional[DeadLetter]:
        with self._lock:
            return self._records.get(record_id)

    def list(
        self, *, include_resolved: bool = False, limit: int = 1000
    ) -> List[DeadLetter]:
        # 📝 #265 battle: `limit=-1` used to slice `rows[:-1]` (silently
        #    drop the newest record). Negative is a caller error.
        if limit < 0:
            raise ValueError("limit must be >= 0")
        with self._lock:
            rows = [
                r
                for r in self._records.values()
                if include_resolved or r.resolved_at is None
            ]
        rows.sort(key=lambda r: (r.taken_at, r.id))
        return rows[:limit]

    def mark_resolved(self, record_id: str, when: float) -> bool:
        with self._lock:
            r = self._records.get(record_id)
            if r is None:
                return False
            self._records[record_id] = replace(r, resolved_at=when)
            return True

    def delete(self, record_id: str) -> bool:
        with self._lock:
            return self._records.pop(record_id, None) is not None

    def all(self) -> List[DeadLetter]:
        with self._lock:
            return list(self._records.values())

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)

    def purge_older_than(self, cutoff_wall: float) -> int:
        """Drop records with ``taken_at < cutoff_wall``; return how many
        (X0.5 retention: dead letters hold snapshots and must not
        accumulate forever).

        Raises:
            ValueError: *cutoff_wall* is NaN (the #262 lesson).
        """
        # 📝 #265 battle: `taken_at >= nan` is False for every record, so
        #    a NaN cutoff (a bad `now - retention` computation) used to
        #    delete the WHOLE store. Fail loudly instead.
        cutoff = float(cutoff_wall)
        if math.isnan(cutoff):
            raise ValueError("cutoff_wall must not be NaN")
        with self._lock:
            old = [k for k, r in self._records.items() if r.taken_at < cutoff]
            for k in old:
                del self._records[k]
        return len(old)

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
        max_errors: Keep only the newest *max_errors* entries of the
            error chain (default 20).

    The error chain is stored in the machine's context under
    ``"_xsm_errors"`` (`ERRORS_CONTEXT_KEY`) so it survives a persist /
    restore between attempts; it is cleared on a clean ``on_service_done``,
    by `RetryPolicy`'s reset action and once a record is captured.

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
        max_errors: int = DEFAULT_MAX_ERRORS,
    ) -> None:
        if max_errors < 1:
            raise ValueError("max_errors must be >= 1")
        self.max_errors = int(max_errors)
        # 📝 #265 battle: an unusable sink used to fail only at the first
        #    dead letter (inside a contained hook -- i.e. the record was
        #    lost). Reject it at construction instead.
        put = sink if callable(sink) else getattr(sink, "put", None)
        if not callable(put):
            raise TypeError(
                "sink must be callable(DeadLetter) or have a put() method"
            )
        self.sink = put
        self.state_ids: Set[str] = set(state_ids)
        self.attempt_key = attempt_key
        self.redact_keys = redact_keys
        self.include_snapshot = include_snapshot
        #: Error chain per interpreter id, cleared on a clean transition
        #: out of the failure path (a `done.invoke.*` handled cleanly).
        #: 🏛️ #265 battle: keyed by the INTERPRETER OBJECT, not
        #:    `interpreter.id`. Every `fastapi_orders` order has machine id
        #:    ``order``; one shared plugin across concurrent `persisted()`
        #:    blocks merged their error chains (block A's errors landed in
        #:    block B's record) and B's record popped A's pending entry.
        #:    Weak keys also mean an interpreter that is never stopped
        #:    cannot leak its chain.
        self._errors: "weakref.WeakKeyDictionary[Any, List[Dict[str, str]]]"
        self._errors = weakref.WeakKeyDictionary()
        #: Dead-letter state ids entered during the step in progress.
        self._pending: "weakref.WeakKeyDictionary[Any, Set[str]]"
        self._pending = weakref.WeakKeyDictionary()
        self._lock = threading.Lock()

    # -- collection ---------------------------------------------------------
    def on_service_error(
        self, interpreter: Any, invocation: Any, error: Exception
    ) -> None:
        self._push(
            interpreter,
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
        self._push(interpreter, "action", getattr(action, "type", "?"), error)

    def on_service_done(
        self, interpreter: Any, invocation: Any, result: Any
    ) -> None:
        # A success ends the chain: the next failure starts a fresh one.
        self._clear_chain(interpreter)

    # -- the error chain ------------------------------------------------------
    # 🏛️ #265 battle (coordinator HIGH): the chain lives IN THE CONTEXT under
    #    `ERRORS_CONTEXT_KEY`, so it rides in the snapshot. In the
    #    production shape (create → act → persist → discard; one
    #    `persisted()` block per request + a `DueTimerScanner` wake per
    #    retry) every attempt runs in a FRESH interpreter, and the old
    #    per-plugin dict was popped in `on_interpreter_stop` at the end of
    #    every block -- the record arrived with ``attempts=3, errors=[]``.
    #    Context is per instance, which also removes the shared-plugin
    #    collision (#261) by construction. A non-dict context (rare) falls
    #    back to a per-interpreter in-memory chain (weakly keyed).
    def _chain(self, interpreter: Any) -> List[Dict[str, str]]:
        ctx = interpreter.context
        if isinstance(ctx, dict):
            raw = ctx.get(ERRORS_CONTEXT_KEY)
            return [dict(e) for e in raw] if isinstance(raw, list) else []
        with self._lock:
            return list(self._errors.get(interpreter, []))

    def _clear_chain(self, interpreter: Any) -> None:
        ctx = interpreter.context
        if isinstance(ctx, dict):
            ctx.pop(ERRORS_CONTEXT_KEY, None)
        with self._lock:
            self._errors.pop(interpreter, None)

    def _push(
        self, interpreter: Any, source: str, name: str, err: Any
    ) -> None:
        message = _scrub(str(err), interpreter.context, self.redact_keys)
        if len(message) > MAX_ERROR_MESSAGE:
            message = message[:MAX_ERROR_MESSAGE] + "…"
        rec = {
            "source": source,
            "name": str(name),
            "type": type(err).__name__,
            "message": message,
        }
        # 📝 New list each time (never mutate the stored one in place) and
        #    bounded to the newest `max_errors`: a poison loop with a huge
        #    `max_attempts` must not grow every snapshot without limit.
        chain = (self._chain(interpreter) + [rec])[-self.max_errors :]
        ctx = interpreter.context
        if isinstance(ctx, dict):
            ctx[ERRORS_CONTEXT_KEY] = chain
            return
        with self._lock:
            self._errors[interpreter] = chain

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
                self._pending.setdefault(interpreter, set()).update(
                    n.id for n in entered
                )

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Any
    ) -> None:
        with self._lock:
            entered = self._pending.pop(interpreter, None)
        if not entered:
            return
        for state_id in sorted(entered):
            record = self._capture(interpreter, event, state_id)
            try:
                self.sink(record)
            except Exception:
                # 📝 #265 battle: the plugin system contains this, but its
                #    log line names only the hook. Name the RECORD so an
                #    operator can tell which dead letter never reached the
                #    sink (and its machine / state), then re-raise so
                #    `on_plugin_error` still fires.
                logger.error(
                    "💀 DeadLetter sink failed; record %s (%s @ %s) was "
                    "NOT stored",
                    record.id,
                    record.machine_id,
                    record.state_id,
                )
                raise

    def on_interpreter_stop(self, interpreter: Any) -> None:
        # 📝 The context-held chain is deliberately NOT cleared here: a
        #    `persisted()` block stops its interpreter after every request,
        #    and the chain must outlive that (it is saved with the record).
        with self._lock:
            self._errors.pop(interpreter, None)
            self._pending.pop(interpreter, None)

    # -- record -----------------------------------------------------------------
    def _capture(self, interpreter: Any, ev: Any, state_id: str) -> DeadLetter:
        errors = self._chain(interpreter)
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
            # 📝 The chain is already `errors`; don't ship it twice.
            snap_ctx = snapshot.get("context")
            if isinstance(snap_ctx, dict):
                snap_ctx.pop(ERRORS_CONTEXT_KEY, None)
        # ✅ Captured: the next failure path starts a fresh chain.
        self._clear_chain(interpreter)
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


def _scrub(message: str, ctx: Any, keys: Tuple[str, ...]) -> str:
    """Mask secret context VALUES that leak into an error message.

    📝 #265 battle (X0.5): the chain now rides in the snapshot, so an
    exception text like ``"declined card tok_live_123"`` would persist the
    secret. `redact()` masks by KEY; here every string value whose key
    `redact()` would mask is replaced in the free-text message.
    """
    if not isinstance(ctx, dict):
        return message
    masked = redact(ctx, keys)
    for k, v in ctx.items():
        if (
            isinstance(v, str)
            and len(v) >= 4
            and masked.get(k) != v
            and v in message
        ):
            message = message.replace(v, "***")
    return message


def _machine_hash(machine: Any) -> Optional[str]:
    from ..persistence.snapshot import structure_hash

    try:
        return structure_hash(machine)
    except Exception:  # noqa: BLE001 - a record beats no record
        return None
