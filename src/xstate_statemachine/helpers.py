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
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .events import AfterEvent, DoneEvent, Event
from .models import ActionDefinition, MachineNode

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

#: Statuses from which a machine can no longer make progress.
TERMINAL_STATUSES = frozenset({"done", "error", "stopped"})


# -----------------------------------------------------------------------------
# ⏳ Awaiting Helpers
# -----------------------------------------------------------------------------


async def wait_for(
    interpreter: Any,
    predicate: Callable[[Any], bool],
    *,
    timeout: Optional[float] = 10.0,
    poll_interval: float = 0.005,
) -> Any:
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
        TimeoutError: If the predicate does not hold within `timeout`.
    """
    loop = asyncio.get_event_loop()
    deadline = None if timeout is None else loop.time() + timeout

    while True:
        if predicate(interpreter):
            return interpreter
        # 🛑 Stop early when the machine can no longer change.
        if interpreter.status in TERMINAL_STATUSES and not predicate(
            interpreter
        ):
            raise TimeoutError(
                f"Machine '{interpreter.id}' reached terminal status "
                f"'{interpreter.status}' before the predicate held."
            )
        if deadline is not None and loop.time() > deadline:
            raise TimeoutError(
                f"Timed out after {timeout}s waiting on '{interpreter.id}'. "
                f"Current states: {interpreter.current_state_ids}"
            )
        await asyncio.sleep(poll_interval)


def wait_for_sync(
    interpreter: Any,
    predicate: Callable[[Any], bool],
    *,
    timeout: Optional[float] = 10.0,
    poll_interval: float = 0.005,
) -> Any:
    """Blocking counterpart to :func:`wait_for` for `SyncInterpreter`.

    Args:
        interpreter (Any): The running interpreter to observe.
        predicate (Callable[[Any], bool]): The stop condition.
        timeout (Optional[float]): Seconds to wait before raising.
        poll_interval (float): Seconds between checks.

    Returns:
        Any: The interpreter, once the predicate holds.

    Raises:
        TimeoutError: If the predicate does not hold within `timeout`.
    """
    deadline = None if timeout is None else time.monotonic() + timeout
    while True:
        if predicate(interpreter):
            return interpreter
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError(
                f"Timed out after {timeout}s waiting on '{interpreter.id}'. "
                f"Current states: {interpreter.current_state_ids}"
            )
        time.sleep(poll_interval)


async def to_promise(
    interpreter: Any, *, timeout: Optional[float] = None
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
        TimeoutError: If the machine does not complete within `timeout`.
    """
    await wait_for(
        interpreter,
        lambda i: i.status in ("done", "error"),
        timeout=timeout,
    )
    if interpreter.status == "error" and interpreter.error is not None:
        raise interpreter.error
    return interpreter.output


# -----------------------------------------------------------------------------
# 🧪 Pure Transition API
# -----------------------------------------------------------------------------


class PureSnapshot:
    """An immutable view of a machine state produced by the pure API.

    Attributes:
        state_ids (Set[str]): Active atomic/final leaf ids.
        configuration (Set[str]): Every active state id, ancestors included.
        context (Dict[str, Any]): The context after the step.
        status (str): `"active"`, `"done"` or `"error"`.
        output (Any): Output when the machine completed.
    """

    __slots__ = ("state_ids", "configuration", "context", "status", "output")

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


def _build_probe(
    machine: MachineNode[Any, Any],
    snapshot: Optional[PureSnapshot],
    input: Optional[Any] = None,
) -> Tuple[Any, List[ActionDefinition]]:
    """Creates a throwaway interpreter that records actions instead of running.

    Args:
        machine (MachineNode): The machine to probe.
        snapshot (Optional[PureSnapshot]): State to restore, or `None` to
            start from the machine's initial state.
        input (Optional[Any]): Input for the initial context.

    Returns:
        Tuple[Any, List[ActionDefinition]]: The probe interpreter and the list
        that will collect executed actions.
    """
    # 🔁 Imported here to avoid a circular import at module load.
    from .sync_interpreter import SyncInterpreter

    recorded: List[ActionDefinition] = []

    class _Probe(SyncInterpreter):
        """A SyncInterpreter that records actions rather than executing them."""

        def _execute_actions(
            self, actions: List[ActionDefinition], event: Any
        ) -> None:
            """Records actions without running their side effects.

            `assign` is still applied, because context updates are part of the
            computed next state rather than an external side effect.
            """
            from .actions import ASSIGN, resolve_builtin

            for action_def in actions or []:
                recorded.append(action_def)
                if resolve_builtin(action_def.type) == ASSIGN:
                    self._apply_assign(
                        self._resolve_params(action_def.params, event) or {},
                        event,
                    )

        def _schedule_state_tasks(self, state: Any) -> None:
            """Suppresses timers and invoked services entirely."""
            return None

    probe = _Probe(machine, input=input)
    if snapshot is not None:
        probe.context = copy.deepcopy(snapshot.context)
    return probe, recorded


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
    return PureSnapshot(
        state_ids=set(probe.current_state_ids),
        configuration={node.id for node in probe._active_state_nodes},
        context=copy.deepcopy(probe.context),
        status=status,
        output=probe.output,
    )


def initial_transition(
    machine: MachineNode[Any, Any], *, input: Optional[Any] = None
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
    return _capture(probe), recorded


def transition(
    machine: MachineNode[Any, Any],
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
        and the actions that would have run.
    """
    probe, recorded = _build_probe(machine, snapshot, None)
    probe.status = "running"

    # 🌳 Restore the exact configuration rather than re-deriving it.
    probe._active_state_nodes.clear()
    for state_id in snapshot.configuration:
        node = machine.get_state_by_id(state_id)
        if node is not None:
            probe._active_state_nodes.add(node)

    # 📭 Only actions from THIS step should be reported.
    recorded.clear()
    probe.send(probe._coerce_event(event))
    return _capture(probe), recorded


def get_initial_snapshot(
    machine: MachineNode[Any, Any], *, input: Optional[Any] = None
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
    machine: MachineNode[Any, Any],
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
    "get_initial_snapshot",
    "get_next_snapshot",
    "initial_transition",
    "to_promise",
    "transition",
    "wait_for",
    "wait_for_sync",
]
