# src/xstate_statemachine/graph.py
# -----------------------------------------------------------------------------
# 🗺️ graph -- reachability, shortest / simple paths over a statechart (#269)
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: traversal EXECUTES THE REAL ENGINE. Every edge is
#    discovered by building a fresh `SyncInterpreter` on a `SimulatedClock`,
#    replaying the path that reached a configuration, and then trying one
#    candidate step (an event `send`, or a clock advance for an `after`).
#    Nothing here re-implements transition selection, entry/exit ordering,
#    `always` microsteps, history, `onDone` or parallel semantics -- whatever
#    the engine does IS the graph. The price is speed (paths are replayed
#    rather than cached); the pay-off is that a `Path` can never describe a
#    run the engine would not actually perform, which is exactly the
#    property `Path.replay()` is tested against for the whole corpus.
# -----------------------------------------------------------------------------
"""Graph traversal of a machine by driving the real sync engine.

A *configuration* is the frozenset of active leaf state ids. Guards and
services are replaced with `stub_logic` stand-ins while exploring; any
deviation from the "every guard True, every service succeeds" default is
written into ``Step.assumptions`` and re-applied by `Path.replay`.
"""

from __future__ import annotations

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import heapq
import itertools
import logging
from collections import deque
from typing import (
    Any,
    Deque,
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    Tuple,
)

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from .exceptions import XStateMachineError
from .models import MachineNode
from .validation import transitions_of, walk
from ._graph_explorer import _Explorer
from ._graph_explorer import WILDCARD_PROBE  # noqa: F401
from ._graph_model import (  # noqa: F401
    UNKNOWN_DELAY_MS,
    Config,
    Path,
    Step,
    _advance_of,
    _apply_step,
    _forced,
    _quiet,
)

__all__ = [
    "Step",
    "Path",
    "ExplorationLimitError",
    "reachable_states",
    "shortest_paths",
    "simple_paths",
    "transition_coverage_targets",
]

logger = logging.getLogger(__name__)

_WEIGHTS = ("steps", "time")


# -----------------------------------------------------------------------------
# 🚀 Public API
# -----------------------------------------------------------------------------
def shortest_paths(
    machine: MachineNode[Any],
    *,
    guards: str = "true",
    max_depth: int = 50,
    weight: str = "steps",
    max_configs: Optional[int] = 100_000,
) -> Dict[FrozenSet[str], Path]:
    """Shortest path to every reachable configuration.

    Args:
        machine: The machine to explore. Never modified: the traversal
            runs on a private copy carrying `stub_logic` stand-ins, so
            concurrent calls and live interpreters are unaffected.
        guards: ``"true"``, ``"false"`` or ``"both"`` (also explores each
            guard forced False and each service forced to error).
        max_depth: Maximum number of steps in any path.
        weight: ``"steps"`` (BFS) or ``"time"`` (Dijkstra over total
            clock advance; events weigh 0).
        max_configs: Stop with `ExplorationLimitError` once this many
            configurations are found (``None``: unbounded). Parallel
            regions multiply: 16 two-state regions are 65 536
            configurations, each one engine run plus a cached snapshot.

    Returns:
        Mapping of configuration to the shortest `Path` reaching it. The
        initial configuration maps to the empty path.

    Raises:
        ValueError: On an unknown ``guards`` / ``weight`` or a negative
            bound.
        ExplorationLimitError: More than *max_configs* configurations.
    """
    if weight not in _WEIGHTS:
        raise ValueError(f"weight must be one of {_WEIGHTS}, got {weight!r}")
    _check_bounds(max_depth=max_depth, max_configs=max_configs)
    explorer = _Explorer(machine, guards)
    explorer.max_configs = max_configs
    with explorer.stubbed():
        if weight == "steps":
            return _bfs(explorer, max_depth)
        return _dijkstra(explorer, max_depth)


class ExplorationLimitError(XStateMachineError):
    """`shortest_paths` found more configurations than ``max_configs``.

    🐛 #269 battle (A3): a wide parallel chart has a configuration count
    exponential in its regions; with no bound the traversal ran until the
    snapshot cache or the clock gave out. ``found`` is the partial result
    so far (shortest paths are already final for every entry).
    """

    def __init__(self, limit: int, found: Dict[FrozenSet[str], Path]):
        super().__init__(
            f"graph: more than {limit} reachable configurations; raise "
            f"max_configs (or None), lower max_depth, or explore a "
            f"sub-chart."
        )
        self.limit = limit
        self.found = found


def _check_bounds(**bounds: Optional[int]) -> None:
    for name, value in bounds.items():
        if value is not None and value < 0:
            raise ValueError(f"{name} must be >= 0, got {value!r}")


def _over(explorer: _Explorer, best: Dict[Config, Path]) -> None:
    limit = explorer.max_configs
    if limit is not None and len(best) > limit:
        raise ExplorationLimitError(limit, best)


def _bfs(explorer: _Explorer, max_depth: int) -> Dict[Config, Path]:
    explorer.first_only = True
    start, done = explorer.initial()
    explorer._seen_configs.add(start)
    best: Dict[Config, Path] = {start: Path((), start)}
    queue: Deque[Tuple[Path, bool]] = deque([(best[start], done)])
    while queue:
        path, is_done = queue.popleft()
        if is_done or len(path.steps) >= max_depth:
            continue
        for step, nxt_done in explorer.successors(
            path.steps, path.final_states
        ):
            if step.to_states in best:
                continue
            nxt = Path(path.steps + (step,), step.to_states)
            best[step.to_states] = nxt
            _over(explorer, best)
            queue.append((nxt, nxt_done))
    return best


def _dijkstra(explorer: _Explorer, max_depth: int) -> Dict[Config, Path]:
    start, done = explorer.initial()
    best: Dict[Config, Path] = {}
    tie = itertools.count()
    heap: List[Tuple[float, int, int, Path, bool]] = [
        (0.0, 0, next(tie), Path((), start), done)
    ]
    while heap:
        cost, depth, _, path, is_done = heapq.heappop(heap)
        if path.final_states in best:
            continue
        best[path.final_states] = path
        _over(explorer, best)
        if is_done or depth >= max_depth:
            continue
        for step, nxt_done in explorer.successors(
            path.steps, path.final_states
        ):
            if step.to_states in best:
                continue
            w = _advance_of(step) if step.event is None else 0.0
            nxt = Path(path.steps + (step,), step.to_states)
            heapq.heappush(
                heap, (cost + w, depth + 1, next(tie), nxt, nxt_done)
            )
    return best


def reachable_states(
    machine: MachineNode[Any], *, guards: str = "true", max_depth: int = 50
) -> Set[str]:
    """Every state id (leaves AND their ancestors) the engine can reach."""
    explorer = _Explorer(machine, guards)
    out: Set[str] = set()
    for config in shortest_paths(machine, guards=guards, max_depth=max_depth):
        out.update(n.id for n in explorer._active_nodes(config))
    return out


def simple_paths(
    machine: MachineNode[Any],
    *,
    guards: str = "true",
    max_paths: int = 1000,
    max_depth: int = 50,
) -> List[Path]:
    """Every non-empty path that never revisits a configuration.

    Depth-first; stops after *max_paths* paths or at *max_depth* steps.
    """
    _check_bounds(max_depth=max_depth, max_paths=max_paths)
    explorer = _Explorer(machine, guards)
    found: List[Path] = []
    with explorer.stubbed():
        start, done = explorer.initial()
        if done:
            return found
        # 📝 Explicit stack instead of recursion: max_depth may exceed
        #    what is comfortable for Python's recursion limit.
        stack: List[Tuple[Path, FrozenSet[Config]]] = [
            (Path((), start), frozenset([start]))
        ]
        while stack and len(found) < max_paths:
            path, on_path = stack.pop()
            if len(path.steps) >= max_depth:
                continue
            succ = explorer.successors(path.steps, path.final_states)
            for step, nxt_done in reversed(succ):
                if step.to_states in on_path:
                    continue
                nxt = Path(path.steps + (step,), step.to_states)
                found.append(nxt)
                if len(found) >= max_paths:
                    break
                if not nxt_done:
                    stack.append((nxt, on_path | {step.to_states}))
    return found


def transition_coverage_targets(
    machine: MachineNode[Any],
) -> Set[Tuple[str, str, str]]:
    """``(from_state_id, label, to_state_id)`` for every chart transition.

    Static: read from the parsed chart, no execution. Labels are those of
    `validation.transitions_of` (``"on 'GO'"``, ``"after 2000"``, …);
    targetless transitions point back at their source.
    """
    out: Set[Tuple[str, str, str]] = set()
    for node in walk(machine):
        for label, t in transitions_of(node):
            target = t.resolved_target
            out.add((node.id, label, (target or node).id))
    return out
