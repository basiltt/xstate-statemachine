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
import contextlib
import copy
import heapq
import itertools
import logging
import threading
from collections import deque
from dataclasses import dataclass
from typing import (
    Any,
    Deque,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from .clock import SimulatedClock
from .exceptions import XStateMachineError
from .models import MachineNode, StateNode
from .sync_interpreter import SyncInterpreter
from .testing_utils import logic_names, stub_logic
from .validation import _collect_findings, transitions_of, walk

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

#: ⏰ Clock advance used to fire a NAMED `after` delay whose duration is not
#: known statically. Large enough to exceed any realistic delay.
UNKNOWN_DELAY_MS = 10**9

#: ⚡ Upper bound on cached prefix snapshots (each is a small JSON blob);
#: beyond it the explorer falls back to replaying the prefix.
_CACHE_MAX = 50_000

_GUARD_MODES = ("true", "false", "both")
_WEIGHTS = ("steps", "time")

Config = FrozenSet[str]


# -----------------------------------------------------------------------------
# 🧱 Data model
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class Step:
    """One edge: an event sent, or a clock advance firing an `after`.

    Attributes:
        event: Event type sent, or ``None`` for a clock advance.
        delay_ms: Clock advance in ms for `after` steps; ``None`` for
            events and for named delays of unknown duration (the latter
            carry a ``"delay:<name>=unknown"`` assumption).
        from_states: Configuration before the step.
        to_states: Configuration after the step.
        assumptions: Forced guard / service outcomes, e.g.
            ``("guard:isValid=False",)`` or ``("service:fetch=error",)``.
    """

    event: Optional[str]
    delay_ms: Optional[float]
    from_states: FrozenSet[str]
    to_states: FrozenSet[str]
    assumptions: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Path:
    """A replayable sequence of steps ending in ``final_states``."""

    steps: Tuple[Step, ...]
    final_states: FrozenSet[str]

    def replay(
        self, interp: SyncInterpreter[Any], clock: SimulatedClock
    ) -> None:
        """Drive *interp* (on *clock*) through every step.

        Starts the interpreter if it has not been started. Each step's
        ``assumptions`` are forced on ``interp.machine.logic`` for the
        duration of that step only.
        """
        if interp.status == "uninitialized":
            interp.start()
        # 🔇 #269 battle: a `service:<name>=error` assumption is the path's
        #    intent, not an incident -- the engine logs each forced failure
        #    at ERROR with a traceback (one per generated test under
        #    `xsm_path`). Quiet the library logger for forced steps only.
        for step in self.steps:
            if any(a.startswith("service:") for a in step.assumptions):
                with _quiet():
                    _apply_step(interp, clock, step)
            else:
                _apply_step(interp, clock, step)

    def event_string(self) -> str:
        """The ``xsm simulate --events`` grammar: ``"SUBMIT,+2000,PAY"``."""
        parts: List[str] = []
        for step in self.steps:
            if step.event is not None:
                parts.append(step.event)
            else:
                parts.append(f"+{_fmt_ms(_advance_of(step))}")
        return ",".join(parts)

    @property
    def total_delay_ms(self) -> float:
        """Sum of every clock advance on the path."""
        return sum(_advance_of(s) for s in self.steps if s.event is None)


_QUIET_LOCK = threading.Lock()
_quiet_depth = 0
_quiet_saved = logging.NOTSET


@contextlib.contextmanager
def _quiet() -> Iterator[None]:
    """Silence the library logger; re-entrant and thread-safe.

    🐛 #269 battle (A5): each caller used to save/restore the level
    itself. Two overlapping traversals on different threads restored in
    the wrong order (A saves INFO, B saves CRITICAL, A restores INFO, B
    restores CRITICAL) and the library logger stayed muted for the rest
    of the process. Now the FIRST entrant saves and the LAST restores.
    """
    global _quiet_depth, _quiet_saved
    lib_logger = logging.getLogger("xstate_statemachine")
    with _QUIET_LOCK:
        if _quiet_depth == 0:
            _quiet_saved = lib_logger.level
            lib_logger.setLevel(logging.CRITICAL)
        _quiet_depth += 1
    try:
        yield
    finally:
        with _QUIET_LOCK:
            _quiet_depth -= 1
            if _quiet_depth == 0:
                lib_logger.setLevel(_quiet_saved)


def _fmt_ms(ms: float) -> str:
    return str(int(ms)) if float(ms).is_integer() else str(ms)


def _advance_of(step: Step) -> float:
    return UNKNOWN_DELAY_MS if step.delay_ms is None else step.delay_ms


# -----------------------------------------------------------------------------
# 🔧 Step execution (shared by exploration and `Path.replay`)
# -----------------------------------------------------------------------------
def _forced_guard(value: bool) -> Any:
    def _guard(c: Any, e: Any) -> bool:
        return value

    return _guard


def _failing_service(name: str) -> Any:
    def _service(i: Any, c: Any, e: Any) -> Any:
        raise RuntimeError(f"graph: service '{name}' forced to error")

    return _service


@contextlib.contextmanager
def _forced(logic: Any, assumptions: Tuple[str, ...]) -> Iterator[None]:
    """Temporarily force guard / service outcomes named in *assumptions*."""
    saved: List[Tuple[Dict[str, Any], str, Any]] = []

    def patch(table: Dict[str, Any], key: str, value: Any) -> None:
        saved.append((table, key, table.get(key, _MISSING)))
        table[key] = value

    try:
        for a in assumptions:
            kind, _, rest = a.partition(":")
            name, _, val = rest.rpartition("=")
            if kind == "guard":
                keys = list(logic.guards) if name == "*" else [name]
                for k in keys:
                    patch(logic.guards, k, _forced_guard(val == "True"))
            elif kind == "service" and val == "error":
                patch(logic.services, name, _failing_service(name))
        yield
    finally:
        for table, key, old in reversed(saved):
            if old is _MISSING:
                table.pop(key, None)
            else:
                table[key] = old


_MISSING = object()


def _apply_step(
    interp: SyncInterpreter[Any], clock: SimulatedClock, step: Step
) -> None:
    with _forced(interp.machine.logic, step.assumptions):
        if step.event is not None:
            interp.send(step.event)
        else:
            clock.increment(_advance_of(step))


# -----------------------------------------------------------------------------
# 🧭 Explorer
# -----------------------------------------------------------------------------
class _Explorer:
    """Discovers successors of a path by replaying it on the real engine."""

    def __init__(self, machine: MachineNode[Any], guards: str) -> None:
        if guards not in _GUARD_MODES:
            raise ValueError(
                f"guards must be one of {_GUARD_MODES}, got {guards!r}"
            )
        self.machine = machine
        self.mode = guards
        _, guard_names, service_names = logic_names(machine)
        self.guard_names = sorted(guard_names)
        self.service_names = sorted(service_names)
        self.named_delays = set(machine.logic.delays)
        self.nodes: Dict[str, StateNode[Any]] = {
            n.id: n for n in walk(machine)
        }
        self.eventless_guards: Set[str] = set()
        for node in self.nodes.values():
            for label, t in transitions_of(node):
                if not label.startswith(("on ", "after ")):
                    _collect_guards(t.guard_def, self.eventless_guards)
        # 📝 Mode-wide default carried on every step so `replay` on an
        #    interpreter with all-True stubs reproduces a "false" run.
        self.base: Tuple[str, ...] = (
            ("guard:*=False",) if guards == "false" else ()
        )
        #: ⚡ prefix (step tuple) → (snapshot JSON, clock.now() s, wall_now()).
        self._snapshots: Dict[Tuple[Step, ...], Tuple[str, float, float]] = {}
        #: ⚡ #269 battle (A1): BFS keeps only the FIRST path into each
        #: configuration, in exactly the order `_try` discovers them, so it
        #: needs one snapshot per configuration -- not one per edge. With
        #: every edge cached, `addressFields` (3 456 configurations,
        #: ~19 000 edges) filled `_CACHE_MAX` and the prefixes it then
        #: needed fell back to replay (77 % hit rate). Dijkstra / DFS keep
        #: non-first paths and leave this off.
        self.first_only = False
        self.max_configs: Optional[int] = None
        self._seen_configs: Set[Config] = set()

    @contextlib.contextmanager
    def stubbed(self) -> Iterator[None]:
        """Explore a private copy of the machine carrying `stub_logic`.

        🐛 #269 battle (A5): this used to swap ``machine.logic`` on the
        CALLER's machine. Anything else using that machine meanwhile -- a
        second thread generating paths (pytest-xdist threads, a web app
        per request) or the application's own interpreter -- ran on the
        all-True stubs, and `_forced` patched a table shared between
        threads. Only a private copy is stubbed now (see `_private_copy`);
        the caller's machine is never written.
        """
        original = self.machine
        stub = stub_logic(original)
        stub.delays.update(original.logic.delays)
        self.machine = _private_copy(original, stub)
        # 🔇 Forced service failures are the POINT of a `guards="both"`
        #    probe, not incidents: the engine would otherwise log each one
        #    at ERROR with a traceback. Silence the library logger for the
        #    traversal only (thread-safe; see `_quiet`).
        try:
            with _quiet():
                yield
        finally:
            self.machine = original
            self._snapshots.clear()

    def run(
        self, steps: Tuple[Step, ...]
    ) -> Tuple[SyncInterpreter[Any], SimulatedClock]:
        """A fresh interpreter positioned after *steps*.

        ⚡ #269 battle: the original design replayed the WHOLE prefix for
        every candidate edge -- O(depth) engine runs per edge, so a
        35-state parallel chart (3 456 configurations) took 60 s and a
        deeper one never finished. The prefix's end state is now cached
        as a snapshot (`get_snapshot` + the virtual clock) keyed by the
        step tuple, and candidates restore from it: one engine run per
        configuration instead of one per edge. The engine still performs
        every step; nothing is simulated. A prefix that cannot be
        snapshotted (an uncopyable stub context) falls back to replay.
        """
        cached = self._snapshots.get(steps)
        if cached is not None:
            blob, now, wall = cached
            # 🕰️ Deadlines are persisted as ABSOLUTE wall time; the restore
            #    clock must share the original's wall origin and elapsed
            #    virtual time, or every `after` is already due / shifted.
            clock = SimulatedClock(wall_start=wall - now)
            clock.increment(now * 1000.0)
            # 📝 `restart_timers="resume"`: the default leaves persisted
            #    `after` deadlines DORMANT (a scanner's job, #264); here
            #    the restored machine IS the live one, so re-arm them with
            #    their remaining time on this clock.
            # 📝 `start()` on a restore re-runs `always` transitions. A
            #    configuration that is only STABLE under the last step's
            #    forced outcomes (`guards="both"`: `Passive` holds while
            #    `FeatureError=False`) would otherwise move on with the
            #    all-True stubs -- the cached edge would describe a run the
            #    replay never performs. Restore under those assumptions.
            last = steps[-1].assumptions if steps else self.base
            with _forced(self.machine.logic, last):
                restored: SyncInterpreter[Any] = SyncInterpreter.from_snapshot(
                    blob, self.machine, clock=clock, restart_timers="resume"
                ).start()
            return restored, clock
        clock = SimulatedClock()
        interp = SyncInterpreter(self.machine, clock=clock).start()
        for step in steps:
            _apply_step(interp, clock, step)
        self._remember(steps, interp, clock)
        return interp, clock

    def _remember(
        self,
        steps: Tuple[Step, ...],
        interp: SyncInterpreter[Any],
        clock: SimulatedClock,
    ) -> None:
        if steps in self._snapshots or len(self._snapshots) >= _CACHE_MAX:
            return
        try:
            self._snapshots[steps] = (
                interp.get_snapshot(),
                clock.now(),
                clock.wall_now(),
            )
        except Exception:  # noqa: BLE001 -- replay remains correct
            logger.debug("graph: prefix not snapshottable", exc_info=True)

    def _wanted(self, to: Config) -> bool:
        """Should the prefix ending in *to* be snapshotted?"""
        if not self.first_only:
            return True
        if to in self._seen_configs:
            return False
        self._seen_configs.add(to)
        return True

    def initial(self) -> Tuple[Config, bool]:
        interp, _ = self.run(())
        try:
            return frozenset(interp.current_state_ids), self._done(interp)
        finally:
            interp.stop()

    @staticmethod
    def _done(interp: SyncInterpreter[Any]) -> bool:
        return interp.status != "running"

    def _active_nodes(self, config: Config) -> List[StateNode[Any]]:
        seen: Dict[str, StateNode[Any]] = {}
        for sid in config:
            node: Optional[StateNode[Any]] = self.nodes.get(sid)
            while node is not None and node.id not in seen:
                seen[node.id] = node
                node = node.parent
        return list(seen.values())

    def _candidates(
        self, config: Config
    ) -> List[Tuple[Optional[str], Optional[float], Tuple[str, ...]]]:
        """``(event, delay_ms, extra_assumptions)`` to try from *config*."""
        events: Set[str] = set()
        delays: Dict[str, Tuple[Optional[float], Tuple[str, ...]]] = {}
        for node in self._active_nodes(config):
            events.update(k for k in node.on if k and "*" not in k)
            events.update(_wildcard_probe(k) for k in node.on if "*" in k)
            for key in node.after:
                ms = _numeric_delay(key)
                if ms is not None:
                    delays[repr(ms)] = (ms, ())
                elif str(key) in self.named_delays:
                    delays[f"n:{key}"] = (None, (f"delay:{key}=unknown",))
                else:
                    logger.debug("graph: skipping unresolvable delay %r", key)
        out: List[Tuple[Optional[str], Optional[float], Tuple[str, ...]]]
        out = [(e, None, ()) for e in sorted(events)]
        for _, (ms, extra) in sorted(delays.items()):
            out.append((None, ms, extra))
        return out

    def _variants(
        self, config: Config, event: Optional[str]
    ) -> List[Tuple[str, ...]]:
        """Default outcome, plus (``"both"``) one flip per relevant name.

        📝 Flipped: guards on the active states' transitions FOR THIS
        candidate (``on <event>``; for a clock step, the ``after``
        transitions), guards on EVENTLESS transitions anywhere (``always``
        / ``onDone`` / invoke results run inside the step's macrostep, in
        states not yet active), and every service (a service entered
        during the step resolves within it).

        ⚡ #269 battle: the flips used to be the union over EVERY event of
        the active states and were tried for EVERY candidate -- a guard
        on ``on 'X'`` cannot change what ``send('Y')`` does, yet each such
        pair cost one engine run. On a 53-state / 78-guard chart that was
        43 variants × 17 candidates per configuration (137 s); scoping the
        event guards to their own event keeps the result identical.
        """
        variants: List[Tuple[str, ...]] = [()]
        if self.mode != "both":
            return variants
        guards: Set[str] = set(self.eventless_guards)
        want = "after" if event is None else f"on '{event}'"
        for node in self._active_nodes(config):
            for label, t in transitions_of(node):
                if label.startswith(want):
                    _collect_guards(t.guard_def, guards)
        known_g = set(self.guard_names)
        variants += [(f"guard:{g}=False",) for g in sorted(guards & known_g)]
        variants += [(f"service:{s}=error",) for s in self.service_names]
        return variants

    def successors(
        self, steps: Tuple[Step, ...], config: Config
    ) -> List[Tuple[Step, bool]]:
        """Every distinct step out of *config* (reached via *steps*)."""
        out: List[Tuple[Step, bool]] = []
        for event, ms, extra in self._candidates(config):
            seen: Set[Config] = set()
            for variant in self._variants(config, event):
                step = Step(
                    event=event,
                    delay_ms=ms,
                    from_states=config,
                    to_states=frozenset(),
                    assumptions=self.base + extra + variant,
                )
                result = self._try(steps, step)
                if result is None:
                    continue
                to, done = result
                # 📝 A variant that lands where the default did adds
                #    nothing; a step that changes nothing is a self-loop.
                if to in seen or (to == config and not done):
                    continue
                seen.add(to)
                out.append((_with_target(step, to), done))
        return out

    def _try(
        self, steps: Tuple[Step, ...], step: Step
    ) -> Optional[Tuple[Config, bool]]:
        try:
            interp, clock = self.run(steps)
        except Exception:  # pragma: no cover - prefix was replayable once
            logger.debug("graph: prefix replay failed", exc_info=True)
            return None
        try:
            _apply_step(interp, clock, step)
            to = frozenset(interp.current_state_ids)
            done = self._done(interp)
            if not done and self._wanted(to):
                self._remember(
                    steps + (_with_target(step, to),), interp, clock
                )
            return to, done
        except Exception:
            logger.debug("graph: step %r failed", step, exc_info=True)
            return None
        finally:
            with contextlib.suppress(Exception):
                interp.stop()


#: Attributes `create_machine` sets AFTER the parse; a rebuild from the
#: source config must carry them over to behave like the caller's machine.
_POST_PARSE_ATTRS = ("event_schemas", "context_validator")


def _private_copy(machine: MachineNode[Any], logic: Any) -> MachineNode[Any]:
    """An independent tree equal to *machine*, carrying *logic*.

    📝 Rebuilt from ``source_config`` (never mutated by the library),
    which is iterative-safe and as cheap as the original parse. A
    ``deepcopy`` recursed through target references and blew the stack
    on a 200-state chain. Hand-built nodes without a usable source config
    fall back to ``deepcopy`` (logic and config shared by reference).
    """
    try:
        private: MachineNode[Any] = MachineNode(machine.source_config, logic)
    except Exception:  # noqa: BLE001 -- hand-built / non-reparseable
        memo: Dict[int, Any] = {
            id(machine.logic): machine.logic,
            id(machine.source_config): machine.source_config,
        }
        private = copy.deepcopy(machine, memo)
        private.logic = logic
        return private
    for attr in _POST_PARSE_ATTRS:
        setattr(private, attr, getattr(machine, attr))
    # ⚡ Memoise `resolved_target` exactly as `create_machine` does (the
    #    caller's machine already passed validation; findings are moot).
    _collect_findings(private)
    return private


#: Event sent to exercise a wildcard handler (``"*"`` / ``"mouse.*"``).
WILDCARD_PROBE = "xsm.graph.any"


def _wildcard_probe(key: str) -> str:
    """A concrete event the wildcard *key* matches and nothing else does.

    🐛 #269 battle (A2): wildcard keys were skipped outright, so a state
    reachable only through ``"*"`` (any event the chart does not name)
    or ``"mouse.*"`` was reported unreachable although every real run
    can take it. The probe is sent like any event and kept only if the
    engine actually moves.
    """
    if key == "*":
        return WILDCARD_PROBE
    return key.replace("*", "xsm_graph_any")


def _with_target(step: Step, to: Config) -> Step:
    return Step(
        event=step.event,
        delay_ms=step.delay_ms,
        from_states=step.from_states,
        to_states=to,
        assumptions=step.assumptions,
    )


def _collect_guards(guard: Any, out: Set[str]) -> None:
    """Leaf guard names of a (possibly composite) guard definition."""
    if guard is None:
        return
    if getattr(guard, "is_composite", False):
        for child in getattr(guard, "children", None) or []:
            _collect_guards(child, out)
        return
    name = getattr(guard, "type", None)
    if isinstance(name, str) and name:
        out.add(name)


def _numeric_delay(key: Union[int, float, str]) -> Optional[float]:
    if isinstance(key, (int, float)):
        return float(key)
    try:
        return float(key)
    except (TypeError, ValueError):
        return None


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
