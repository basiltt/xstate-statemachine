# /src/xstate_statemachine/helpers.py
# -----------------------------------------------------------------------------
# 🧰 Interpreter Helpers & Pure Transition API
# -----------------------------------------------------------------------------
# Utilities that operate *on* interpreters and machines rather than being part
# of them:
#
#   - `wait_for` / `to_promise` — await a machine reaching a condition or
#     completing, mirroring XState's `waitFor()` and `toPromise()`.
#   - `transition` / `initial_transition` — pure, actor-free reducers that map
#     `(snapshot, event) -> (snapshot, actions)` without starting anything.
#   - `get_next_snapshot` / `get_initial_snapshot` — thin wrappers over the
#     pure API, matching the XState names.
#
# 🏛️ Architecture decision: the pure API is genuinely side-effect free. It
# runs a throwaway `SyncInterpreter` over a deep copy of the context and
# *records* the actions a real run would execute instead of performing them.
# That makes it safe for tests, previews and model-based exploration, which is
# exactly what XState added it for in v5.19.0.
# -----------------------------------------------------------------------------
"""
Helper utilities: awaiting completion and pure transition computation.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import asyncio
import copy
import logging
import threading
import time
import weakref
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .events import AfterEvent, DoneEvent, Event
from .exceptions import XStateMachineError
from .models import ActionDefinition, MachineNode

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .base_interpreter import BaseInterpreter

#: 📝 The interpreter flavour a helper was handed is the one it hands back,
#: so `await wait_for(interp, ...)` keeps the caller's concrete type.
TInterp = TypeVar("TInterp", bound="BaseInterpreter[Any]")

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

#: Statuses from which a machine can no longer make progress.
TERMINAL_STATUSES = frozenset({"done", "error", "stopped"})


# -----------------------------------------------------------------------------
# ⏳ Awaiting Helpers
# -----------------------------------------------------------------------------


class WaitTerminatedError(TimeoutError):
    """The machine reached a terminal status before the predicate held.

    A ``TimeoutError`` subclass so existing ``except TimeoutError`` code
    keeps working, although nothing timed out: waiting longer could never
    help. ⚠️ On Python 3.9/3.10 the builtin ``TimeoutError`` is NOT
    ``asyncio.TimeoutError``; catch the builtin.

    Attributes:
        status: The terminal status (``"done"``, ``"error"``, ``"stopped"``).
    """

    def __init__(self, message: str, status: str = "") -> None:
        super().__init__(message)
        self.status = status

    def __reduce__(self) -> Tuple[Any, ...]:
        """Keep the exception picklable across process boundaries."""
        return (self.__class__, (str(self), self.status))


async def wait_for(
    interpreter: TInterp,
    predicate: Callable[[TInterp], bool],
    *,
    timeout: Optional[float] = 10.0,
    poll_interval: float = 0.005,
) -> TInterp:
    """Waits until `predicate(interpreter)` is true.

    Mirrors XState's ``waitFor(actor, predicate, {timeout})``.

    Args:
        interpreter (Any): The running interpreter to observe.
        predicate (Callable[[Any], bool]): Called with the interpreter;
            return `True` to stop waiting.
        timeout (Optional[float]): Seconds to wait before raising. `None`
            waits indefinitely.
        poll_interval (float): Seconds between checks.

    Returns:
        Any: The interpreter, once the predicate holds.

    Raises:
        WaitTerminatedError: (a ``TimeoutError``) If the machine reached a
            terminal status (done/error/stopped) while the predicate was
            still false.
        TimeoutError: If the predicate does not hold within `timeout`.
    """
    # 🐍 Inside a coroutine the running loop is the only correct answer;
    #    `get_event_loop()` is deprecated here from 3.12 and errors on 3.14+
    #    when no loop is set, which is exactly the case under the policy-free
    #    3.14/3.15 asyncio.
    loop = asyncio.get_running_loop()
    deadline = None if timeout is None else loop.time() + timeout

    while True:
        if predicate(interpreter):
            return interpreter
        # 🛑 Stop early when the machine can no longer change. The predicate
        #    just returned falsy and nothing ran since, so it is NOT
        #    evaluated a second time (a costly/side-effecting one would
        #    otherwise run twice per iteration).
        _raise_if_terminal(interpreter)
        if deadline is not None and loop.time() > deadline:
            raise TimeoutError(
                f"Timed out after {timeout}s waiting on '{interpreter.id}'. "
                f"Current states: {interpreter.current_state_ids}"
            )
        await asyncio.sleep(poll_interval)


def _raise_if_terminal(interpreter: Any) -> None:
    """Raise `WaitTerminatedError` when *interpreter* can no longer progress.

    Args:
        interpreter: The interpreter being observed.

    Raises:
        WaitTerminatedError: If its status is in `TERMINAL_STATUSES`.
    """
    status = interpreter.status
    if status in TERMINAL_STATUSES:
        raise WaitTerminatedError(
            f"Machine '{interpreter.id}' reached terminal status "
            f"'{status}' before the predicate held.",
            status,
        )


def wait_for_sync(
    interpreter: TInterp,
    predicate: Callable[[TInterp], bool],
    *,
    timeout: Optional[float] = 10.0,
    poll_interval: float = 0.005,
) -> TInterp:
    """Blocking counterpart to :func:`wait_for` for `SyncInterpreter`.

    📝 A pure OBSERVER: it never pumps the interpreter. Timers and
    ``send_threadsafe`` mailbox events are delivered by whoever owns the
    interpreter (``send()`` / ``tick()`` / a `SimulatedClock`), so another
    thread must keep the machine moving while this one waits.

    Args:
        interpreter (Any): The running interpreter to observe.
        predicate (Callable[[Any], bool]): The stop condition.
        timeout (Optional[float]): Seconds to wait before raising.
        poll_interval (float): Seconds between checks.

    Returns:
        Any: The interpreter, once the predicate holds.

    Raises:
        WaitTerminatedError: (a ``TimeoutError``) If the machine reached a
            terminal status while the predicate was still false.
        TimeoutError: If the predicate does not hold within `timeout`.
    """
    deadline = None if timeout is None else time.monotonic() + timeout
    while True:
        if predicate(interpreter):
            return interpreter
        _raise_if_terminal(interpreter)  # 🛑 never spin on a finished machine
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError(
                f"Timed out after {timeout}s waiting on '{interpreter.id}'. "
                f"Current states: {interpreter.current_state_ids}"
            )
        time.sleep(poll_interval)


async def to_promise(
    interpreter: "BaseInterpreter[Any]", *, timeout: Optional[float] = None
) -> Any:
    """Waits for a machine to reach a top-level final state and returns output.

    Mirrors XState's ``toPromise(actor)``.

    Args:
        interpreter (Any): The running interpreter.
        timeout (Optional[float]): Seconds to wait, or `None` for no limit.

    Returns:
        Any: The machine's `output`.

    Raises:
        Exception: The machine's recorded error if it failed.
        XStateMachineError: If the machine is in ``"error"`` status but
            recorded no error object (nothing meaningful to re-raise).
        TimeoutError: If the machine does not complete within `timeout`.
    """
    await wait_for(
        interpreter,
        lambda i: i.status in ("done", "error"),
        timeout=timeout,
    )
    if interpreter.status == "error":
        if interpreter.error is None:
            raise XStateMachineError(
                f"Machine '{interpreter.id}' ended in status 'error' without "
                "recording an error."
            )
        raise interpreter.error
    return interpreter.output


# -----------------------------------------------------------------------------
# 🧪 Pure Transition API
# -----------------------------------------------------------------------------


class PureSnapshot:
    """A snapshot of a machine state produced by the pure API.

    📝 "Immutable" is a contract, not enforcement: the library never mutates
    a snapshot it handed out (every call deep-copies on the way in and out),
    but ``state_ids``/``configuration``/``context`` are ordinary mutable
    containers, so a caller who edits them edits their own copy's truth.

    Attributes:
        state_ids (Set[str]): Active atomic/final leaf ids.
        configuration (Set[str]): Every active state id, ancestors included.
        context (Dict[str, Any]): The context after the step.
        status (str): `"active"`, `"done"` or `"error"`.
        output (Any): Output when the machine completed.
    """

    __slots__ = (
        "state_ids",
        "configuration",
        "context",
        "status",
        "output",
        "_nodes",
        "_history",
        "_entry_order",
    )

    def __init__(
        self,
        state_ids: Set[str],
        configuration: Set[str],
        context: Dict[str, Any],
        status: str = "active",
        output: Any = None,
    ) -> None:
        """Initializes the snapshot.

        Args:
            state_ids: Active leaf ids.
            configuration: All active state ids.
            context: The context after the step.
            status: Lifecycle status.
            output: Completion output, if any.
        """
        self.state_ids = state_ids
        self.configuration = configuration
        self.context = context
        self.status = status
        self.output = output
        #: Resolved `StateNode`s for `configuration`, filled in by `_capture`
        #: (#54). Private: lets the chained-call pattern skip N id lookups
        #: per step. Absent (None) on hand-built snapshots.
        self._nodes: Optional[Set[Any]] = None
        #: History memory (`parent id -> remembered children`) as of this
        #: snapshot (#54, 0.8.0 audit). A history target is only
        #: meaningful relative to the path that produced the snapshot, so
        #: it must ride WITH the snapshot: chained calls resolve `p.hist`
        #: to where that chain left `p`; an unrelated or hand-built
        #: snapshot (None) resolves it to the default child. Before this
        #: the cached probe's own memory served both -- correct for one
        #: chain, silently wrong across independent calls.
        self._history: Optional[Dict[str, List[Any]]] = None
        #: When each active leaf was entered (`BaseInterpreter._leaf_entry`),
        #: so a chained call visits `always` transitions in the order XState's
        #: snapshot holds its states. None on hand-built snapshots (document
        #: order, as XState's `resolveState`).
        self._entry_order: Optional[Dict[Any, int]] = None

    def matches(self, state_id: str) -> bool:
        """Reports whether a state is active in this snapshot.

        Args:
            state_id (str): The state to test for.

        Returns:
            bool: `True` if active.
        """
        target = state_id[1:] if state_id.startswith("#") else state_id
        return any(
            sid == target or sid.endswith("." + target)
            for sid in self.configuration
        )

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return (
            f"PureSnapshot(states={sorted(self.state_ids)}, "
            f"status='{self.status}')"
        )


# -----------------------------------------------------------------------------
# 🔬 Pure-transition probe
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision (#54): `transition()` used to define a NEW
# `SyncInterpreter` subclass inside the function (closing over a fresh
# `recorded` list) and construct an instance of it on every call, then
# deep-copy the context on the way in AND on the way out. Measured: the
# "cheap" pure path cost 4x a real `send()`. The class is now module-level,
# ONE probe per `MachineNode` is cached (ON the machine, so it is freed with
# it -- see `_ProbeSlot`) and reset per call, and only the outbound copy remains -- that is the one
# that makes the returned snapshot immutable, which is the promise the guide
# makes.
#
# 🧵 The cache is PER THREAD (`threading.local`). A probe is a mutable
# interpreter reset in place; two threads sharing one -- e.g. a UI preview
# and a test runner calling `get_next_snapshot` on the same machine -- would
# interleave `_reset_probe` / `send` / `_capture` and return each other's
# results. The pre-#54 code was accidentally thread-safe because it built a
# fresh probe per call; caching must not give that up. Confirmed on Linux CI
# (502 wrong results from 8 threads on a shared cache) before this fix.
# -----------------------------------------------------------------------------
class _ProbeSlot:
    """Per-machine home of the per-thread probes (RU-03).

    🏛️ The old cache was a ``WeakKeyDictionary[machine -> probe]``. The probe
    is a `SyncInterpreter` that strongly references its machine, and a
    WeakKeyDictionary keeps its VALUES alive -- so the key was always
    reachable and no machine was ever freed. The probe now lives ON the
    machine (in a thread-local held by the machine), so key and value form
    one cycle the garbage collector can reclaim together.

    ``copy`` / ``deepcopy`` / ``pickle`` of a machine produce an EMPTY slot:
    a probe belongs to exactly one machine object (a thread-local cannot be
    copied at all), and the copy simply builds its own on first use.
    """

    __slots__ = ("local",)

    def __init__(self) -> None:
        self.local = threading.local()

    def __copy__(self) -> "_ProbeSlot":
        return _ProbeSlot()

    def __deepcopy__(self, memo: Dict[int, Any]) -> "_ProbeSlot":
        return _ProbeSlot()

    def __reduce__(self) -> Tuple[Any, ...]:
        return (_ProbeSlot, ())


class _ProbeCache:
    """This thread's machine -> probe view (dict-like, weakly keyed).

    Only the operations the pure API and its tests use are provided.
    Machines are tracked in a `WeakSet`, so the cache itself never pins one.
    """

    def __init__(self) -> None:
        self._machines: "weakref.WeakSet[MachineNode[Any]]" = weakref.WeakSet()

    @staticmethod
    def _slot(machine: MachineNode[Any]) -> _ProbeSlot:
        # `setdefault` is atomic: two threads racing on first use agree on
        # ONE slot, which is what keeps the per-thread probes apart.
        slot = machine.__dict__.setdefault("_pure_probe_slot", _ProbeSlot())
        return cast(_ProbeSlot, slot)

    def get(self, machine: MachineNode[Any]) -> Optional[Any]:
        """Return this thread's probe for *machine*, or ``None``."""
        probe = getattr(self._slot(machine).local, "probe", None)
        # 🛡️ A shallow copy of the machine shares ``__dict__`` values; only
        #    trust a probe that was built for THIS very object.
        if probe is not None and probe.machine is not machine:
            return None
        return probe

    def __setitem__(self, machine: MachineNode[Any], probe: Any) -> None:
        self._slot(machine).local.probe = probe
        self._machines.add(machine)

    def __getitem__(self, machine: MachineNode[Any]) -> Any:
        probe = self.get(machine)
        if probe is None:
            raise KeyError(machine)
        return probe

    def __contains__(self, machine: object) -> bool:
        return isinstance(machine, MachineNode) and (
            self.get(machine) is not None
        )

    def __iter__(self) -> Iterator[MachineNode[Any]]:
        return iter([m for m in list(self._machines) if m in self])

    def __len__(self) -> int:
        return sum(1 for _ in self)


_PROBE_CACHE = threading.local()


def _probes() -> _ProbeCache:
    """This thread's machine -> probe cache (created on first use)."""
    cache = getattr(_PROBE_CACHE, "probes", None)
    if cache is None:
        cache = _ProbeCache()
        _PROBE_CACHE.probes = cache
    return cast(_ProbeCache, cache)


def _make_probe_class() -> type:
    """Build the probe class once, after `SyncInterpreter` is importable.

    The import is deferred to call time to avoid a circular import at
    module load (`sync_interpreter` imports from this package too).
    """
    # ⚡ Bound once here, not on every `_execute_actions` call: an `import`
    #    statement inside the hot method cost two module-dict lookups per
    #    step of the pure API.
    from .actions import ASSIGN, resolve_builtin
    from .sync_interpreter import SyncInterpreter, _Done

    class _Probe(SyncInterpreter[Any]):
        """A SyncInterpreter that records actions rather than executing them."""

        _recorded: List[ActionDefinition]

        def _execute_actions(self, actions: Any, event: Any) -> Any:
            """Records actions without running their side effects.

            `assign` is still applied, because context updates are part of
            the computed next state rather than an external side effect.
            Returns an (already finished) awaitable of an empty failure
            list -- the shared base algorithm `await`s this leaf (#60) and
            the action-error machinery (#27) sees a clean run.
            """
            recorded = self._recorded
            for action_def in actions or []:
                recorded.append(action_def)
                if resolve_builtin(action_def.type) == ASSIGN:
                    self._apply_assign(
                        self._resolve_params(action_def.params, event) or {},
                        event,
                    )
            return _Done([])

        def _schedule_state_tasks(
            self, state: Any, trigger: Any = None
        ) -> None:
            """Suppresses timers and invoked services entirely."""
            return None

        def _schedule_teardown(self) -> None:
            """A probe owns nothing to reap; keep it reusable after `done`."""
            return None

    # 📝 `_Probe` is a local class; mypy sees a variable, not a type.
    return cast(type, _Probe)


_Probe: Any = None  # populated on first use by `_probe_class()`


def _probe_class() -> type:
    global _Probe
    if _Probe is None:
        _Probe = _make_probe_class()
    # 📝 `_Probe` is module-global Optional[Any]; it is a class once built.
    return cast(type, _Probe)


def _build_probe(
    machine: MachineNode[Any],
    snapshot: Optional[PureSnapshot],
    input: Optional[Any] = None,
) -> Tuple[Any, List[ActionDefinition]]:
    """Return the cached probe for *machine*, reset to *snapshot* (or fresh).

    Args:
        machine (MachineNode): The machine to probe.
        snapshot (Optional[PureSnapshot]): State to restore, or `None` to
            start from the machine's initial state.
        input (Optional[Any]): Input for the initial context.

    Returns:
        Tuple[Any, List[ActionDefinition]]: The probe interpreter and the list
        that will collect executed actions (already cleared).
    """
    cache = _probes()
    probe = cache.get(machine)
    if probe is None or input is not None:
        # 🆕 First use on this thread, or an explicit `input` (which shapes
        #    the initial context, so it cannot be applied to a cached one).
        probe = _probe_class()(machine, input=input)
        probe._recorded = []
        if input is None:
            cache[machine] = probe
    _reset_probe(probe, snapshot)
    return probe, probe._recorded


def _reset_probe(probe: Any, snapshot: Optional[PureSnapshot]) -> None:
    """Put a cached probe into exactly the state *snapshot* describes."""
    probe._recorded.clear()
    probe._event_queue.clear()
    probe._deferred_events.clear()
    # 🧠 History is snapshot state, not probe state (#54, 0.8.0 audit):
    #    start from exactly what the incoming snapshot remembers -- nothing,
    #    for a hand-built or initial one -- never from a previous call.
    probe._history.clear()
    if snapshot is not None and snapshot._history:
        probe._history.update(snapshot._history)
    # 🔢 Entry order is snapshot state too (same reasoning as history).
    probe._leaf_entry.clear()
    if snapshot is not None and snapshot._entry_order:
        probe._leaf_entry.update(snapshot._entry_order)
        probe._leaf_entry_seq = max(
            probe._leaf_entry_seq, max(snapshot._entry_order.values())
        )
    probe.output = None
    probe.error = None
    probe.last_transition_ok = True
    if snapshot is None:
        probe.status = "uninitialized"
        probe._active_state_nodes.clear()
        probe.context = probe._build_initial_context(
            probe.machine, probe.input
        )
        return
    probe.status = "running"
    # 🧊 ONE copy: the caller's snapshot must not be mutated by this step
    #    (PureSnapshot is documented immutable), and `_capture` copies the
    #    result on the way out. A second inbound copy was pure overhead.
    probe.context = copy.deepcopy(snapshot.context)
    # 🌳 Restore the exact configuration rather than re-deriving it. A
    #    library-made snapshot carries the resolved nodes; a hand-built one
    #    falls back to id lookup.
    probe._active_state_nodes.clear()
    nodes = getattr(snapshot, "_nodes", None)
    if nodes is not None:
        probe._active_state_nodes.update(nodes)
        return
    machine = probe.machine
    for state_id in snapshot.configuration:
        node = machine.get_state_by_id(state_id)
        if node is not None:
            probe._active_state_nodes.add(node)


def _capture(probe: Any) -> PureSnapshot:
    """Reads a `PureSnapshot` out of a probe interpreter.

    Args:
        probe (Any): The probe interpreter.

    Returns:
        PureSnapshot: The captured state.
    """
    status = "active"
    if probe.status == "done":
        status = "done"
    elif probe.status == "error":
        status = "error"
    snap = PureSnapshot(
        state_ids=probe.current_state_ids,  # the property builds a set
        configuration={node.id for node in probe._active_state_nodes},
        context=copy.deepcopy(probe.context),
        status=status,
        output=probe.output,
    )
    snap._nodes = set(probe._active_state_nodes)
    snap._history = {k: list(v) for k, v in probe._history.items()}
    entry = probe._leaf_entry
    snap._entry_order = {
        node: entry[node]
        for node in probe._active_state_nodes
        if node in entry
    }
    return snap


def initial_transition(
    machine: MachineNode[Any], *, input: Optional[Any] = None
) -> Tuple[PureSnapshot, List[ActionDefinition]]:
    """Computes a machine's initial state without running it.

    Mirrors XState's ``initialTransition()`` (v5.19.0).

    Args:
        machine (MachineNode): The machine to evaluate.
        input (Optional[Any]): Input for the initial context.

    Returns:
        Tuple[PureSnapshot, List[ActionDefinition]]: The initial snapshot and
        the entry actions a real run would have executed.
    """
    probe, recorded = _build_probe(machine, None, input)
    probe.start()
    return _capture(probe), list(recorded)


def transition(
    machine: MachineNode[Any],
    snapshot: PureSnapshot,
    event: Union[str, Dict[str, Any], Event, AfterEvent, DoneEvent],
) -> Tuple[PureSnapshot, List[ActionDefinition]]:
    """Computes the next state for an event, purely.

    Mirrors XState's ``transition()`` (v5.19.0). Nothing is started, no timer
    is scheduled and no service is invoked; the actions a real run *would*
    have executed are returned instead.

    Args:
        machine (MachineNode): The machine to evaluate.
        snapshot (PureSnapshot): The state to start from, typically from
            :func:`initial_transition`.
        event: The event to apply.

    Returns:
        Tuple[PureSnapshot, List[ActionDefinition]]: The resulting snapshot
        and the actions that would have run. A snapshot whose status is
        terminal (done/error/stopped) is returned UNCHANGED with no actions,
        exactly as a finished actor ignores events (RU-10).
    """
    if snapshot.status in TERMINAL_STATUSES:
        # 🛑 A real run never processes events after `done`; reviving the
        #    probe as "running" would resurrect it through a root-level
        #    transition.
        return snapshot, []
    probe, recorded = _build_probe(machine, snapshot, None)
    # ⚡ `send()` normalises the event itself (`_prepare_event_reporting`,
    #    the same rules as `_coerce_event`); normalising here first made
    #    every step pay twice.
    probe.send(event)
    # 📭 Hand back a COPY of the recorded list: the probe is cached and its
    #    list is cleared on the next call, so a caller holding the list
    #    across calls would otherwise see it emptied under them.
    return _capture(probe), list(recorded)


def get_initial_snapshot(
    machine: MachineNode[Any], *, input: Optional[Any] = None
) -> PureSnapshot:
    """Returns a machine's initial snapshot, discarding the actions.

    Args:
        machine (MachineNode): The machine to evaluate.
        input (Optional[Any]): Input for the initial context.

    Returns:
        PureSnapshot: The initial snapshot.
    """
    return initial_transition(machine, input=input)[0]


def get_next_snapshot(
    machine: MachineNode[Any],
    snapshot: PureSnapshot,
    event: Union[str, Dict[str, Any], Event],
) -> PureSnapshot:
    """Returns the next snapshot for an event, discarding the actions.

    Mirrors XState's ``getNextSnapshot()`` (v5.5.0).

    Args:
        machine (MachineNode): The machine to evaluate.
        snapshot (PureSnapshot): The starting snapshot.
        event: The event to apply.

    Returns:
        PureSnapshot: The resulting snapshot.
    """
    return transition(machine, snapshot, event)[0]


__all__ = [
    "PureSnapshot",
    "WaitTerminatedError",
    "get_initial_snapshot",
    "get_next_snapshot",
    "initial_transition",
    "to_promise",
    "transition",
    "wait_for",
    "wait_for_sync",
]
