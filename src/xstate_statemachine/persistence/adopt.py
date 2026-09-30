# src/xstate_statemachine/persistence/adopt.py
# -----------------------------------------------------------------------------
# 🧬 from_state_ids -- adopt an existing record into a machine (#310)
# -----------------------------------------------------------------------------
# 🏛️ The generic "this row is already in state X" primitive: a data
#    migration from ``django-fsm`` (one status column), a SQLAlchemy table
#    with an enum, a plain dict -- anything that knows WHERE a record is
#    but has never run the machine. It builds the snapshot a machine that
#    had reached that configuration would have written, WITHOUT running
#    anything: no entry actions, no services, no timers are armed (an
#    `after` in the target state starts counting when the machine is next
#    restored with ``restart_timers`` -- `persisted()` does).
#
#    Given ids are completed downwards: a compound state without an
#    explicit child enters its ``initial``; every region of a parallel
#    state is entered (its given child, else its ``initial``). Ancestors
#    are implied. The result is checked for SCXML legality (one leaf per
#    region) and round-trips through `from_snapshot` -- anything else is a
#    loud `InvalidConfigError` / `StateNotFoundError`, never a blob that
#    restores as a machine with no active leaf.
# -----------------------------------------------------------------------------
"""`from_state_ids`."""

from __future__ import annotations

import copy
import json
from typing import Any, Dict, Iterable, List, Optional, Set

from ..exceptions import InvalidConfigError, StateNotFoundError
from ..models import MachineNode, StateNode

__all__ = ["from_state_ids"]


def _resolve(machine: MachineNode[Any], sid: str) -> StateNode[Any]:
    node = machine.get_state_by_id(sid)
    if node is None and not sid.startswith(machine.id + "."):
        node = machine.get_state_by_id(f"{machine.id}.{sid}")
    if node is None:
        raise StateNotFoundError(target=sid)
    return node


def _complete(
    node: StateNode[Any], chosen: Set[StateNode[Any]], out: Set[StateNode[Any]]
) -> None:
    """Add *node* and the descendants a machine entering it would have."""
    out.add(node)
    if node.type == "final" or not node.states:
        return
    children = [c for c in node.states.values() if c.type != "history"]
    if node.type == "parallel":
        for region in children:
            _complete(region, chosen, out)
        return
    picked = [c for c in children if c in chosen or _has_chosen(c, chosen)]
    if len(picked) > 1:
        raise InvalidConfigError(
            f"from_state_ids: '{node.id}' is a compound state but "
            f"{sorted(c.id for c in picked)} were all given; exactly one "
            f"child can be active."
        )
    if picked:
        _complete(picked[0], chosen, out)
        return
    initial = node.initial
    if not initial:
        raise InvalidConfigError(
            f"from_state_ids: '{node.id}' is a compound state with no "
            f"'initial'; name the active child explicitly."
        )
    child = node.states.get(initial) or _resolve(node.machine, initial)
    _complete(child, chosen, out)


def _has_chosen(node: StateNode[Any], chosen: Set[StateNode[Any]]) -> bool:
    return any(_is_ancestor(node, c) for c in chosen)


def _is_ancestor(a: StateNode[Any], b: StateNode[Any]) -> bool:
    p = b.parent
    while p is not None:
        if p is a:
            return True
        p = p.parent
    return False


def from_state_ids(
    machine: MachineNode[Any],
    state_ids: Iterable[str],
    context: Optional[Dict[str, Any]] = None,
    *,
    status: str = "running",
) -> str:
    """The JSON snapshot of *machine* in the configuration *state_ids*.

    Args:
        machine: The chart.
        state_ids: Active states -- full ids (``"order.review.legal.ok"``)
            or ids relative to the root (``"review.legal.ok"``). Leaves or
            ancestors; see the module notes for how gaps are completed.
        context: The context; merged over the machine's initial context
            (keys given win), like a restore.
        status: ``"running"`` (default) or ``"done"`` for a final state.

    Returns:
        A ``get_snapshot()``-compatible JSON string (current layout).

    Raises:
        StateNotFoundError: an id does not exist in *machine*.
        InvalidConfigError: the ids do not form a legal configuration
            (two children of one compound state; a compound without an
            ``initial`` and no child given; nothing given).
    """
    from ..sync_interpreter import SyncInterpreter

    ids = [str(s) for s in state_ids]
    if not ids:
        raise InvalidConfigError("from_state_ids: no state ids given")
    if status not in ("running", "done"):
        raise InvalidConfigError(
            "from_state_ids: status must be 'running' or 'done'"
        )
    chosen = {_resolve(machine, s) for s in ids}
    active: Set[StateNode[Any]] = set()
    _complete(machine, chosen, active)
    missing = [n.id for n in chosen if n not in active]
    if missing:
        raise InvalidConfigError(
            f"from_state_ids: {sorted(missing)} conflict with the rest of "
            f"the configuration (different branches of one compound state)."
        )
    interp: Any = SyncInterpreter(machine)  # never started: nothing runs
    snap: Dict[str, Any] = interp.get_persisted_snapshot()
    base = copy.deepcopy(snap.get("context") or {})
    if context:
        if not isinstance(base, dict):
            base = {}
        base.update(copy.deepcopy(context))
    leaves: List[str] = sorted(
        n.id
        for n in active
        if not [c for c in n.states.values() if c.type != "history"]
    )
    interp._active_state_nodes = set(active)
    snap.update(
        status=status,
        context=base,
        state_ids=leaves,
        configuration=sorted(n.id for n in active),
        value=interp.value,
        deadlines=[],
    )
    blob = json.dumps(snap, indent=2, default=str)
    # ✅ Round-trip: the engine's own restore validates shape, identity,
    #    ids and legality -- a blob it would refuse is never returned.
    type(interp).from_snapshot(blob, machine)
    return blob
