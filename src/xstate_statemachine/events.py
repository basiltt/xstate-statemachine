# /src/xstate_statemachine/events.py
# -----------------------------------------------------------------------------
# ✉️ Event System Data Contracts
# -----------------------------------------------------------------------------
# This module defines the core event structures used throughout the state
# machine interpreter. These immutable, typed data structures ensure consistent
# and predictable communication for all event types:
#
#   1. `Event`: For external events triggered by users or systems.
#   2. `DoneEvent`: For internal events signaling the completion of services.
#   3. `AfterEvent`: For internal events triggered by timed delays.
#
# By standardizing these structures we create a clear, lightweight, and
# maintainable contract for how different parts of the system interact with the
# state machine. This adheres to SOLID principles by defining distinct,
# single-responsibility data structures.
# -----------------------------------------------------------------------------
"""
Defines the core, immutable event types for the state machine.

This module provides the data classes used for communication with the
state machine interpreters (`Interpreter` and `SyncInterpreter`). Historically
these events were implemented with ``NamedTuple`` but the ``Event`` type now
uses a ``dataclass`` so that a fresh payload dictionary is created for every
instance. This prevents subtle bugs where mutating the payload of one event
would affect all subsequently created events.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
from dataclasses import dataclass, field
import copy
import warnings
from typing import Any, Dict, FrozenSet, NamedTuple, Optional, Tuple

# -----------------------------------------------------------------------------
# 🏛️ Reserved event namespaces
# -----------------------------------------------------------------------------
#: Prefixes of events the ENGINE synthesises: ``done.invoke.*`` /
#: ``done.state.*``, ``error.platform.*``, ``after.*``, ``xstate.*`` (from
#: `escalate`) and the ``___xstate`` init/exit sentinels. Events in these
#: namespaces are exempt from ``"*"`` / partial-descriptor matching, from the
#: ``onUnhandled`` policy and from strict-mode name checks, so the engine's
#: own traffic is never mistaken for a user event the machine forgot to
#: handle. Consequently a USER event named ``done.review`` is only ever
#: matched by an exact ``on`` key (#79). `create_machine()` warns about
#: ``on`` keys declared in these namespaces.
SYSTEM_EVENT_PREFIXES: Tuple[str, ...] = (
    "done.",
    "error.",
    "after.",
    "xstate.",
    "___xstate",
)

#: The exact name SHAPES the engine synthesises. Since 0.8.1 (#79) system
#: status is decided by provenance (`is_system_event`), not by name; this
#: list exists for the one place a name is all we have -- build-time
#: `strict` validation of `raise`/`on` keys -- and for documentation.
ENGINE_EVENT_SHAPES: Tuple[str, ...] = (
    "done.invoke.",
    "done.state.",
    "error.platform.",
    "after.",
    "xstate.",
    "___xstate",
)

# -----------------------------------------------------------------------------
# 📨 Event Definitions
# -----------------------------------------------------------------------------
# These classes represent the different types of events that can be processed
# by the state machine interpreter. They serve as Data Transfer Objects (DTOs)
# that carry information into and within the machine.
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Event:
    """Represents a standard event sent to the state machine.

    This is the most common type of event, typically triggered by external
    inputs, user actions, or other system components. It serves as the primary
    mechanism for driving state transitions.

    Attributes:
        type: The name of the event, which is used to match against
            transitions defined in the machine's `on` property.
        payload: An optional dictionary containing extra data associated with
            the event. This data is accessible to actions and guards,
            allowing them to make dynamic decisions.

    Example:
        >>> # An event representing a user login attempt with a payload.
        >>> login_event = Event(type="USER_LOGIN", payload={"username": "alice"})
        >>> print(login_event)
        Event(type='USER_LOGIN', payload={'username': 'alice'})

        >>> # A simple event with no payload.
        >>> timer_tick_event = Event(type="TICK")
        >>> print(timer_tick_event)
        Event(type='TICK', payload={})
    """

    # 🏷️ The unique identifier for the event type (e.g., "SUBMIT", "CANCEL").
    type: str

    # 📦 A dictionary for any additional, dynamic data. ``default_factory`` is
    # used instead of a plain ``{}`` to ensure that each ``Event`` receives its
    # own payload dictionary rather than sharing one across instances.
    payload: Dict[str, Any] = field(default_factory=dict)

    # 🏷️ #79/#85: provenance. Set ONLY by `system_event()` via the private
    #    `_provenance` slot, which holds an engine-owned sentinel object that
    #    user code cannot obtain by name. A caller passing `system=True`
    #    used to forge engine status and bypass `strict`, `onUnhandled`
    #    and the `"*"` matcher (#85); the public constructor no longer has
    #    such a parameter. Excluded from equality/repr so
    #    `Event("X") == Event("X")` is unaffected. `init=False` so it cannot
    #    be supplied positionally or by keyword.
    _provenance: Any = field(
        default=None, init=False, compare=False, repr=False
    )

    @property
    def system(self) -> bool:
        """``True`` if the ENGINE minted this event (read-only, #85)."""
        return self._provenance is _ENGINE_MARK

    @property
    def data(self) -> Dict[str, Any]:
        """Alias for `payload` to maintain compatibility with older versions."""
        # This property allows access to the payload using the `data` attribute,
        # which is a common convention in state machine libraries.
        # It ensures that existing code using `data` will continue to work.
        if not isinstance(self.payload, dict):
            raise TypeError(
                f"Expected payload to be a dict, got {type(self.payload).__name__}"
            )

        return self.payload


class DoneEvent(NamedTuple):
    """Represents the completion of a background service or a final state.

    This is an internal event generated by the interpreter when:
    1. An `invoke`d service finishes its work successfully.
    2. A compound or parallel state reaches its `final` state configuration.

    The `type` attribute follows a specific naming convention to avoid
    collisions with user-defined events, making it easy to target `onDone`
    transitions declaratively in the machine configuration.

    Attributes:
        type: The event name, following a strict convention:
            - `done.invoke.<service_id>` for invoked services.
            - `done.state.<state_id>` for states reaching a final state.
        data: The data returned by the completed service or from a final
            state's `data` property. This is the primary way services
            pass results back to the machine.
        src: The unique identifier of the service or state that generated
             this event, allowing for targeted transitions.

    Example:
        >>> # Event from a completed 'fetchData' service.
        >>> done_invoke_event = DoneEvent(
        ...     type="done.invoke.fetchData",
        ...     data={"user_id": 123, "name": "Alice"},
        ...     src="fetchData"
        ... )
        >>> print(done_invoke_event)
        DoneEvent(type='done.invoke.fetchData', data={'user_id': 123, 'name': 'Alice'}, src='fetchData')
    """

    # 🏷️ The structured name of the completion event.
    type: str

    # 📊 The data payload returned from the source (e.g., the return
    #    value of a service function).
    data: Any

    # 📍 The ID of the invoked service or state that completed.
    src: str


class ErrorEvent(NamedTuple):
    """A failure delivered by the engine: an invoked service or child actor
    raised, or a child machine ended in the ``error`` status (#80).

    🏛️ Architecture decision: before 0.8.1 failures rode in a `DoneEvent`
    whose `data` happened to hold an exception, so an `onError` handler and
    an `onDone` handler received the same shape and consumers had to
    string-prefix the type to tell them apart. XState v5 delivers
    ``xstate.error.actor.*`` as a distinct event carrying ``error``. This
    type does the same: branch on ``isinstance(event, ErrorEvent)`` or read
    ``event.error``. ``event.data`` still returns the exception for one
    minor version so existing ``onError`` actions keep working, but it is
    deprecated and reads as such.

    Attributes:
        type: ``error.platform.<invoke_id>`` (XState v4 naming, which this
            library keeps for compatibility with existing configs).
        error: The exception the service or child raised.
        src: The ``id`` of the invoke that failed, for `onError` routing.
    """

    type: str
    error: BaseException
    src: str

    @property
    def data(self) -> BaseException:
        """Deprecated alias for :attr:`error` (removed in 0.9).

        Kept so an ``onError`` action written against 0.8.0 --
        ``context["err"] = str(event.data)`` -- keeps working unchanged.
        """
        warnings.warn(
            "ErrorEvent.data is deprecated and will be removed in 0.9; "
            "read ErrorEvent.error instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.error


#: Event classes the engine itself mints. Membership -- not the name -- is
#: what marks an event as "system traffic" for the wildcard matcher, the
#: `onUnhandled` policy and strict mode (#79). A user-sent `Event` whose
#: `type` merely starts with ``done.`` is user traffic and is treated as
#: such. `Event` instances the engine creates for its own sentinels are
#: flagged with `Event.system=True` (see `system_event`).
ENGINE_EVENT_TYPES: Tuple[type, ...] = ()  # populated below, after defs


#: Engine-private provenance sentinel. Compared by IDENTITY; it is not
#: exported, not a bool, and cannot be reconstructed from a name.
class _EngineMark:
    """The engine-private provenance sentinel (#85, #138).

    A class with a module-level singleton, not a bare ``object()``, so that
    ``copy.deepcopy`` and ``pickle`` reconstruct the SAME object:
    ``__reduce__`` names the module attribute, and ``__deepcopy__`` returns
    ``self``. Identity comparison in `is_system_event` therefore survives a
    deep copy or a pickle round-trip -- which a persisted inbox, a
    multiprocessing hand-off or a defensive `deepcopy` in user code all
    perform. Still unforgeable from a NAME: user code cannot obtain the
    instance except by holding an engine event that already carries it, and
    copying that event is the legitimate case.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover -- debugging aid
        return "<engine-provenance>"

    def __deepcopy__(self, memo: Dict[int, Any]) -> "_EngineMark":
        return self

    def __copy__(self) -> "_EngineMark":
        return self

    def __reduce__(self) -> str:
        return "_ENGINE_MARK"  # pickle resolves this module attribute


_ENGINE_MARK: Any = _EngineMark()


def is_system_event(event: Any) -> bool:
    """``True`` for events the ENGINE synthesised (#79).

    Provenance, not spelling -- and not public type either (#195). A
    `DoneEvent` / `ErrorEvent` / `AfterEvent` the engine minted is an
    instance of a private subclass (`engine_done` / `engine_error` /
    `engine_after`); one built by hand from the public class is USER
    traffic, subject to `strict` and `onUnhandled` like any other event.
    A plain `Event` is engine-made only when created via
    :func:`system_event` (init/exit sentinels, `escalate`, restore).
    """
    if isinstance(event, _ENGINE_MINTED_TYPES):
        return True
    return isinstance(event, Event) and event._provenance is _ENGINE_MARK


def system_event(event_type: str, **payload: Any) -> "Event":
    """Mint an engine-owned `Event` (init/exit sentinels, restore, …).

    The ONLY way to produce an `Event` for which `is_system_event` is
    true. `Event` is frozen, so the marker is written through
    `object.__setattr__` exactly once, here.
    """
    ev = Event(type=event_type, payload=dict(payload))
    object.__setattr__(ev, "_provenance", _ENGINE_MARK)
    return ev


def event_kind(event: Any) -> str:
    """Discriminator persisted with an event (#86/#87).

    ``"system"`` for an engine-minted plain `Event`, ``"done"`` /
    ``"error"`` / ``"after"`` for the NamedTuple engine events, ``"event"``
    for user traffic. `restore_event` inverts it.
    """
    if isinstance(event, DoneEvent):
        return "done"
    if isinstance(event, ErrorEvent):
        return "error"
    if isinstance(event, AfterEvent):
        return "after"
    return "system" if is_system_event(event) else "event"


def persist_event(event: Any) -> Dict[str, Any]:
    """JSON-safe record for a pending/deferred event (#86/#87).

    Round-trips every engine event kind instead of silently dropping the
    NamedTuple ones. `ErrorEvent.error` is an exception and cannot be
    serialised faithfully; its ``repr`` is kept and restored as a
    `RestoredError`-style stand-in by `restore_event`.
    """
    kind = event_kind(event)
    rec: Dict[str, Any] = {"kind": kind, "type": event.type}
    # 🏷️ #195: an engine-minted completion persists its provenance so the
    #    round-trip restores it as engine-minted (and a record without the
    #    flag -- hand-written, or from a pre-#195 writer -- restores as the
    #    PUBLIC class, i.e. user traffic). `Event` provenance is already
    #    carried by `kind == "system"`.
    if kind in ("done", "error", "after") and is_system_event(event):
        rec["engine"] = True
    if kind in ("event", "system"):
        rec["payload"] = copy.deepcopy(event.payload)
    elif kind == "done":
        rec["data"] = copy.deepcopy(event.data)
        rec["src"] = event.src
    elif kind == "error":
        rec["error"] = repr(event.error)
        rec["src"] = event.src
    elif kind == "after":
        # 📏 #118: the lateness telemetry is real data. Dropping it made a
        #    restored timer event claim it fired exactly on schedule (0.0).
        rec["scheduled_for"] = event.scheduled_for
        rec["fired_at"] = event.fired_at
    # 🛡️ #131: `get_snapshot()` used `json.dumps(default=str)`, which turned a
    #    `Decimal` / `datetime` in a pending `DoneEvent.data` into a STRING
    #    silently -- the restored handler got a `str` where the live one got
    #    a `Decimal`. Fail loudly at persist time instead: a value that
    #    cannot round-trip must not be persisted as something else.
    _assert_json_safe(rec, event)
    return rec


def _assert_json_safe(record: Dict[str, Any], event: Any) -> None:
    """Raise `SnapshotSerializationError` if *record* is not JSON-native."""
    import json

    try:
        json.dumps(record)
    except (TypeError, ValueError) as exc:
        from .exceptions import SnapshotSerializationError

        raise SnapshotSerializationError(event.type, exc) from exc


def restore_event(record: Dict[str, Any]) -> Any:
    """Inverse of `persist_event`; tolerant of v1 records (#86).

    A v1 record has no ``kind``. For those, provenance is re-derived from
    the NAME for the exact engine shapes only -- the one place a name is
    all we have, and only at this boundary -- so an escalate event or init
    sentinel persisted by 0.8.1 is not turned into user traffic that fails
    an `onUnhandled: "error"` machine on restore.
    """
    from .exceptions import SnapshotCorruptError

    if not isinstance(record, dict):
        raise SnapshotCorruptError(
            f"Snapshot is malformed: event record is "
            f"{type(record).__name__}, expected an object."
        )
    kind = record.get("kind")
    etype = record.get("type")
    # 🛡️ #158: the same guard `send()` applies (#113) -- a non-`str` type
    #    must not enter the hierarchy through the restore door either.
    if not isinstance(etype, str) or not etype:
        raise SnapshotCorruptError(
            f"Snapshot is malformed: event record 'type' must be a "
            f"non-empty string, got {etype!r}."
        )
    if kind is None:
        # 🏷️ #162: a v1 record (no `kind`) carries no provenance. It is
        #    USER traffic by default -- laundering it into a system event
        #    on the strength of its NAME is exactly the by-name
        #    classification #79 removed everywhere else, and it exempted a
        #    user's `after.hours` from `onUnhandled`/`strict`. The one
        #    shape the engine itself persisted under v1 that must stay
        #    system is the init sentinel; everything else re-persists as
        #    v2 on the next save. See the 0.8.1 changelog migration note.
        kind = "system" if etype.startswith("___xstate") else "event"
    # 🏷️ #195: provenance is restored exactly as persisted. A `done` /
    #    `error` / `after` record carrying ``"engine": true`` was written by
    #    `persist_event` from an engine-minted completion and restores as
    #    one, so a persisted `done.invoke` still drives its `onDone` after a
    #    round-trip. A record WITHOUT the flag -- hand-authored, or written
    #    by a pre-#195 library -- restores as the PUBLIC class: user
    #    traffic, subject to `strict` / `onUnhandled`, never a trusted
    #    completion. The flag is not a secret; what it closes is the
    #    accidental laundering of "I have a dict shaped like a completion"
    #    into "the engine said this happened". A caller who can write
    #    arbitrary snapshot records already controls `state_ids` and
    #    `context` outright (#185), so this is the correct trust boundary.
    trusted = record.get("engine") is True
    return _restore(record, etype, kind, trusted=trusted)


def _restore(
    record: Dict[str, Any], etype: str, kind: Any, *, trusted: bool
) -> Any:
    """Body of `restore_event` (#195).

    ``trusted`` selects engine-minted classes for engine kinds; otherwise
    the plain public NamedTuples are built, which `is_system_event`
    reports as user traffic.
    """
    if kind == "done":
        args = (etype, record.get("data"), record.get("src", ""))
        return engine_done(*args) if trusted else DoneEvent(*args)
    if kind == "error":
        from .exceptions import RestoredError

        eargs = (
            etype,
            RestoredError(record.get("error") or "unknown error"),
            record.get("src", ""),
        )
        return engine_error(*eargs) if trusted else ErrorEvent(*eargs)
    if kind == "after":
        # 📏 #118: absent telemetry restores as None, never 0.0.
        sched = record.get("scheduled_for")
        fired = record.get("fired_at")
        aargs = (
            etype,
            None if sched is None else float(sched),
            None if fired is None else float(fired),
        )
        return engine_after(*aargs) if trusted else AfterEvent(*aargs)
    payload = record.get("payload") or {}
    if kind == "system":
        # `kind == "system"` IS the persisted provenance for a plain
        # `Event` (#86/#162); it needs no separate flag.
        return system_event(etype, **payload)
    return Event(type=etype, payload=payload)


class Receipt(NamedTuple):
    """What ``send(..., wait=True)`` resolves to once the event's macrostep
    has run to completion (#39).

    Attributes:
        state_ids: The active leaf ids the instant processing finished.
        changed: ``True`` if a transition was taken (configuration or
            context changed) for THIS event.
        error: The exception raised while processing this event -- an
            action that raised, an unresolvable target, a runaway-chain
            budget trip -- or ``None``. The machine may still be
            ``running`` (see ``actionErrorPolicy``); the receipt tells the
            CALLER its request did not run cleanly.
        deferred: ``True`` when the event was HELD by ``onUnhandled:
            "defer"`` rather than processed (#84). ``changed`` is then
            ``False`` because nothing has run yet -- not because the event
            was a correct no-op. Check this before reading ``changed``.
        denied: ``True`` when the active state DID declare a handler for
            this event but every candidate's guard returned ``False``
            (#153). Distinguishes "a business rule refused it" from "this
            event does not apply in this state" (``denied=False``,
            ``changed=False``), which are otherwise identical receipts.
    """

    state_ids: FrozenSet[str]
    changed: bool
    error: Optional[BaseException] = None
    deferred: bool = False
    denied: bool = False


class AfterEvent(NamedTuple):
    """Represents a delayed event used for timed (`after`) transitions.

    This event is scheduled and sent internally by the `Interpreter`. A developer
    using the library typically does not create this event manually. It is
    generated when the interpreter enters a state that has an `after`
    transition defined in its configuration.

    Attributes:
        type: The event name, which is internally generated by the interpreter
              to be unique to the state and delay (e.g., `after.5000.myState`).
              This is used to match the specific `after` transition.

    Example:
        A developer defines an `after` transition in their JSON:
        ```json
        "states": {
          "pending": {
            "after": {
              "3000": { "target": "timed_out" }
            }
          },
          "timed_out": {}
        }
        ```

        After 3 seconds in the `pending` state, the interpreter would create
        and process an event like this one internally:

        >>> after_event = AfterEvent(type="after.3000.machineName.pending")
        >>> print(after_event)
        AfterEvent(type='after.3000.machineName.pending')
    """

    # 🏷️ The structured, internally-generated name of the delayed event.
    type: str
    #: 📏 #48: when the timer was DUE (clock seconds) and when it actually
    #: fired. `lateness_ms` is the difference -- data an application can
    #: alarm on instead of inferring timer starvation from symptoms.
    #: ``None`` (#118) means "not recorded": a record persisted before the
    #: telemetry existed, or one whose keys were stripped. It is never
    #: coerced to ``0.0``, which would be an affirmative "fired on time".
    scheduled_for: Optional[float] = None
    fired_at: Optional[float] = None

    @property
    def lateness_ms(self) -> Optional[float]:
        """Milliseconds the timer fired AFTER its deadline (>= 0).

        ``None`` when either timestamp is unknown (#118) -- telemetry that
        reads ``0.0`` when the truth is "we do not know" gets trusted
        downstream, so the absence is made explicit instead.
        """
        if self.scheduled_for is None or self.fired_at is None:
            return None
        return max(0.0, (self.fired_at - self.scheduled_for) * 1000.0)


# 🧩 Filled in here, once every class above is defined (#79).
ENGINE_EVENT_TYPES = (DoneEvent, ErrorEvent, AfterEvent)


# -----------------------------------------------------------------------------
# 🏷️ #195: engine-minted completions carry provenance by TYPE IDENTITY
# -----------------------------------------------------------------------------
# The public `DoneEvent` / `ErrorEvent` / `AfterEvent` are documented,
# exported NamedTuples; anyone can construct one. Before #195 the engine
# trusted them on a bare `isinstance`, so a hand-built
# `DoneEvent("done.invoke.fill", data=..., src="fill")` bypassed `strict` and
# `onUnhandled` and drove a real `onDone` while the genuine service was still
# running. The engine now mints PRIVATE subclasses. To user code they are
# indistinguishable from the public class -- `isinstance(ev, DoneEvent)`,
# field access, equality, `_replace`, pickle and deepcopy all behave the same
# and preserve the subclass -- but `is_system_event` requires the subclass,
# so only what the engine (or `restore_event` on a persisted engine record)
# produced is system traffic. The classes are not exported and have no
# public name; construct through the `engine_*` helpers only.


class _EngineDone(DoneEvent):
    """A `DoneEvent` the engine minted (#195). Not public."""

    __slots__ = ()


class _EngineError(ErrorEvent):
    """An `ErrorEvent` the engine minted (#195). Not public."""

    __slots__ = ()


class _EngineAfter(AfterEvent):
    """An `AfterEvent` the engine minted (#195). Not public."""

    __slots__ = ()


_ENGINE_MINTED_TYPES: Tuple[type, ...] = (
    _EngineDone,
    _EngineError,
    _EngineAfter,
)


def engine_done(type: str, data: Any, src: str) -> DoneEvent:  # noqa: A002
    """Mint an engine-owned `DoneEvent` (#195). The ONLY sanctioned way."""
    return _EngineDone(type, data, src)


def engine_error(
    type: str, error: BaseException, src: str  # noqa: A002
) -> ErrorEvent:
    """Mint an engine-owned `ErrorEvent` (#195). The ONLY sanctioned way."""
    return _EngineError(type, error, src)


def engine_after(
    type: str,  # noqa: A002
    scheduled_for: Optional[float] = None,
    fired_at: Optional[float] = None,
) -> AfterEvent:
    """Mint an engine-owned `AfterEvent` (#195). The ONLY sanctioned way."""
    return _EngineAfter(type, scheduled_for, fired_at)
