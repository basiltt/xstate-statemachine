# src/xstate_statemachine/_graph_explorer.py
# -----------------------------------------------------------------------------
# 🧭 The graph explorer -- step execution, prefix cache, candidate discovery
# -----------------------------------------------------------------------------
# 🏛️ Split out of `graph.py` (#269 battle: that module passed 800 lines).
#    `graph.py` keeps the public data model and the algorithms (BFS /
#    Dijkstra / DFS); this module owns HOW one step is executed on the real
#    engine and how a prefix is cached and restored. Nothing here is public.
# -----------------------------------------------------------------------------
"""Explorer internals for `xstate_statemachine.graph`."""

from __future__ import annotations

import contextlib
import copy
import logging
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Union

from .clock import SimulatedClock
from .models import MachineNode, StateNode
from .sync_interpreter import SyncInterpreter
from .testing_utils import logic_names, stub_logic
from .validation import _collect_findings, transitions_of, walk
from ._graph_model import (
    Config,
    Step,
    _apply_step,
    _forced,
    _quiet,
)

logger = logging.getLogger("xstate_statemachine.graph")

#: ⚡ Upper bound on cached prefix snapshots (each is a small JSON blob);
#: beyond it the explorer falls back to replaying the prefix.
_CACHE_MAX = 50_000

_GUARD_MODES = ("true", "false", "both")


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
