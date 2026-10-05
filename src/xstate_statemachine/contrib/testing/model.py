# src/xstate_statemachine/contrib/testing/model.py
# -----------------------------------------------------------------------------
# 🎲 Model-based testing: a Hypothesis state machine generated from the chart
# -----------------------------------------------------------------------------
# 🏛️ #271: Hypothesis's `RuleBasedStateMachine` explores random sequences
#    and SHRINKS a failure to a minimal one -- but the developer normally
#    hand-writes which rules are legal when. The chart already declares
#    exactly that. `model_test()` generates the rules (one per declared
#    event, gated by `interp.can(Event(type, payload))`; a clock rule over
#    the declared `after` delays; optional snapshot round-trips and stub
#    guard flips), checks invariants after every step, and writes the
#    minimal failing sequence as an `xsm simulate --script` file.
#
# 🪶 `hypothesis` is imported LAZILY, inside the functions: this module is
#    importable (and `contrib.testing` stays importable) without it;
#    calling `model_test` / `events_strategy` without it raises
#    `MissingExtraError` naming the `[testing]` extra.
#
# ⚠️ `can()` evaluates the machine's REAL guards when real logic is used.
#    That is what makes the generated sequences legal, and it is safe as
#    long as guards are pure (they should be). A payload-dependent guard is
#    evaluated against the payload that will actually be sent: the payload
#    is drawn first, then `can(Event(type, payload))` decides.
# -----------------------------------------------------------------------------
"""Hypothesis model-based testing generated from a statechart (#271)."""

from __future__ import annotations

import json
import pathlib
import sys
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Union,
)

from ...clock import SimulatedClock
from ...events import Event
from ...factory import create_machine
from ...graph import UNKNOWN_DELAY_MS  # type: ignore[attr-defined]
from ...machine_logic import MachineLogic
from ...models import MachineNode, StateNode
from ...sync_interpreter import SyncInterpreter
from ...testing_utils import logic_names, stub_logic
from ...validation import walk
from ._model_payloads import (
    _hypothesis,
    _payload_strategies,
    payload_strategy,
)

__all__ = ["model_test", "events_strategy", "payload_strategy"]

Check = Callable[[Any], Any]
#: Set by the pytest plugin from ``--xsm-failing-dir`` (None: next to the
#: module that called `model_test`).
FAILING_DIR: Optional[pathlib.Path] = None
FAILING_NAME = "failing.json"
_JITTER_MS = (-1, 0, 1)


# -----------------------------------------------------------------------------
# 🏗️ Machine + chart facts
# -----------------------------------------------------------------------------
def _load(
    source: Union[str, pathlib.Path, Mapping[str, Any], MachineNode[Any]],
    logic: Any,
    guards: Dict[str, bool],
) -> Tuple[MachineNode[Any], bool, Optional[pathlib.Path]]:
    """``(machine, stubbed, json_path)``."""
    if isinstance(source, MachineNode):
        if logic is not None:
            raise ValueError(
                "model_test: a MachineNode is already built; pass the config "
                "or JSON path to combine it with logic="
            )
        return source, False, None
    path: Optional[pathlib.Path] = None
    if isinstance(source, (str, pathlib.Path)):
        path = pathlib.Path(source).resolve()
        config = json.loads(path.read_text(encoding="utf-8"))
    elif isinstance(source, Mapping):
        config = json.loads(json.dumps(dict(source)))
    else:
        raise TypeError(
            f"model_test: expected a JSON path, a config dict or a "
            f"MachineNode, got {type(source).__name__}"
        )
    if logic is None:
        return (
            create_machine(config, logic=stub_logic(config, guards=guards)),
            True,
            path,
        )
    if callable(logic) and not isinstance(logic, MachineLogic):
        logic = logic()
    if not _is_machine_logic(logic):
        raise TypeError(
            f"model_test: logic= must be a MachineLogic or a factory "
            f"returning one, got {type(logic).__name__}"
        )
    return create_machine(config, logic=logic), False, path


def _is_machine_logic(obj: Any) -> bool:
    """`isinstance` that also accepts a `MachineLogic` from a SECOND copy
    of the package (an example app importing the installed library while
    the test imports `src.`) -- duck-typed on the three tables."""
    if isinstance(obj, MachineLogic):
        return True
    return type(obj).__name__ == "MachineLogic" and all(
        isinstance(getattr(obj, k, None), dict)
        for k in ("actions", "guards", "services")
    )


def _declared_events(machine: MachineNode[Any]) -> List[str]:
    """Every concrete event a state declares in ``on`` (no wildcards, no
    ``always``, no engine-minted ``done.*`` / ``error.*`` / ``after``)."""
    found: Set[str] = set()
    for node in walk(machine):
        for key in node.on:
            if (
                key
                and "*" not in key
                and not key.startswith(("done.", "error.", "xstate."))
            ):
                found.add(key)
    return sorted(found)


def _delays(machine: MachineNode[Any]) -> List[float]:
    out: Set[float] = set()
    for node in walk(machine):
        for key in node.after:
            try:
                out.add(float(key))
                continue
            except (TypeError, ValueError):
                pass
            named = machine.logic.delays.get(str(key))
            if isinstance(named, (int, float)) and not isinstance(named, bool):
                out.add(float(named))
            else:
                # 📝 Dynamic / unknown named delay (#269 amendment): a large
                #    advance fires it whatever it evaluates to.
                out.add(float(UNKNOWN_DELAY_MS))
    return sorted(out)


def _active_nodes(interp: SyncInterpreter[Any]) -> List[StateNode[Any]]:
    return list(interp._active_state_nodes)


def _declares(interp: SyncInterpreter[Any], event: str) -> bool:
    # 📝 Battle #268: a machine whose root reached a final state is `done`
    #    but keeps its last configuration; an event declared there is NOT
    #    sendable (InterpreterStoppedError) -- the run has settled.
    if interp.status != "running":
        return False
    return any(event in n.on for n in _active_nodes(interp))


def _timer_armed(interp: SyncInterpreter[Any], clock: SimulatedClock) -> bool:
    """A live timer on the model's clock (battle #271: ``after`` only
    missed ``raise``/``sendTo`` ``delay`` and spawned children's timers,
    which share the clock)."""
    if interp.status != "running":
        return False
    return clock.pending > 0 or any(n.after for n in _active_nodes(interp))


# -----------------------------------------------------------------------------
# 🧾 The replayable artefact
# -----------------------------------------------------------------------------
def _failing_path(caller_dir: Optional[pathlib.Path]) -> pathlib.Path:
    base = FAILING_DIR or caller_dir or pathlib.Path.cwd()
    return pathlib.Path(base) / FAILING_NAME


def _write_failing(
    path: pathlib.Path, trace: List[Dict[str, Any]]
) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(trace, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return path


# -----------------------------------------------------------------------------
# 🎲 model_test
# -----------------------------------------------------------------------------
def model_test(
    machine_or_path: Union[
        str, pathlib.Path, Mapping[str, Any], MachineNode[Any]
    ],
    *,
    logic: Any = None,
    invariants: Optional[Mapping[str, Check]] = None,
    state_assertions: Optional[Mapping[str, Check]] = None,
    payloads: Optional[Mapping[str, Any]] = None,
    clock: bool = True,
    max_steps: int = 50,
    settings: Any = None,
    allow_denied: bool = False,
    snapshot_roundtrip: bool = True,
    guard_flip: bool = False,
    failing_path: Union[str, pathlib.Path, None] = None,
) -> Any:
    """Generate a Hypothesis ``RuleBasedStateMachine`` from a chart.

    ``TestCheckout = model_test("checkout.json", invariants={...})`` in a
    test module is collected by pytest (the ``[testing]`` plugin collects
    it through its ``.TestCase``; plain unittest discovery can use
    ``TestCheckout.TestCase``).

    Args:
        machine_or_path: A JSON path, a config dict, or a built
            `MachineNode` (used as-is).
        logic: A `MachineLogic` or a zero-argument factory returning one.
            ``None`` runs the chart on `stub_logic` (guards ``True``).
            Real guards are evaluated by ``can()`` -- keep them pure.
        invariants: ``name -> check(interp)``; run after start and after
            every step. A falsy return or an ``AssertionError`` fails.
        state_assertions: ``state -> check(interp)``; run whenever
            ``interp.matches(state)`` (parallel configurations too).
        payloads: ``EVENT -> strategy`` of payload dicts. Unlisted events
            are inferred from ``event_schemas`` (pydantic `EventModel`
            fields), else sent without a payload.
        clock: Generate a rule advancing the `SimulatedClock` while any
            timer is pending (``after``, ``raise``/``sendTo`` ``delay``, a
            child's timer): either to the next pending timer, or by a
            declared ``after`` delay, each ±1 ms jitter.
        max_steps: Hypothesis ``stateful_step_count``.
        settings: A ``hypothesis.settings`` to start from.
        allow_denied: Also send events ``can()`` refuses (the precondition
            becomes "some active state declares the event"). A refused
            event is never a failure either way.
        snapshot_roundtrip: A rule persisting the interpreter mid-sequence
            and continuing on the restored copy; a context that is not
            JSON-serialisable (or does not survive the trip) fails -- a
            `Decimal` in context fails on purpose: `get_snapshot()` would
            restore it as a ``str``. Dormant invokes are restarted on the
            restored copy (``restart_services=True``).
        guard_flip: With stub logic, a rule flipping stub guards (recorded
            in the script as ``{"guard": name, "value": bool}``).
        failing_path: Where to write the minimal failing sequence
            (default: ``failing.json`` next to the calling module, or in
            ``--xsm-failing-dir``).

    Returns:
        A ``RuleBasedStateMachine`` subclass.

    Raises:
        MissingExtraError: hypothesis is not installed.
        ValueError: ``guard_flip`` with real logic, an unknown event in
            ``payloads=``, or an uninferable payload field.
    """
    hyp = _hypothesis()
    from hypothesis import stateful as hs

    guards: Dict[str, bool] = {}
    machine, stubbed, json_path = _load(machine_or_path, logic, guards)
    # 🏛️ #271 battle: a logic FACTORY is called once per example, not once
    #    per class. Real logic is stateful (a gateway stub counting calls,
    #    a retry counter, a breaker); shared across examples it made
    #    generation depend on earlier examples -- Hypothesis reported
    #    `FlakyStrategyDefinition` and the planted bug reproduced only on
    #    the first run. `None` (stubs) and a bare instance keep one build.
    rebuild = (
        callable(logic)
        and not isinstance(logic, MachineLogic)
        and not isinstance(machine_or_path, MachineNode)
    )

    def _fresh_machine() -> MachineNode[Any]:
        if not rebuild:
            return machine
        built, _, _ = _load(machine_or_path, logic, guards)
        return built

    if guard_flip and not stubbed:
        raise ValueError(
            "model_test: guard_flip=True needs stub logic (logic=None and a "
            "config/path source); real guards cannot be flipped"
        )
    events = _declared_events(machine)
    strategies = _payload_strategies(machine, events, payloads or {})
    delays = _delays(machine) if clock else []
    guard_names = sorted(logic_names(machine)[1]) if guard_flip else []
    invariants = dict(invariants or {})
    state_assertions = dict(state_assertions or {})
    _check_state_keys(machine, state_assertions)
    if failing_path is not None:
        explicit: Optional[pathlib.Path] = pathlib.Path(failing_path)
        caller_dir = None
    else:
        explicit = None
        caller_file = sys._getframe(1).f_globals.get("__file__")
        caller_dir = (
            pathlib.Path(caller_file).resolve().parent if caller_file else None
        )

    body: Dict[str, Any] = {}

    def __init__(self: Any) -> None:
        hs.RuleBasedStateMachine.__init__(self)
        guards.clear()
        self.clock = SimulatedClock()
        self.machine = _fresh_machine()
        self.interp = SyncInterpreter(self.machine, clock=self.clock).start()
        self.trace = []

    def _fail(self: Any, message: str) -> None:
        target = explicit or _failing_path(caller_dir)
        _write_failing(target, self.trace)
        replay = (
            f"xsm simulate {json_path} --script {target}"
            if json_path is not None
            else f"--script {target}"
        )
        raise AssertionError(
            f"{message}\nminimal failing sequence ({len(self.trace)} "
            f"step(s)) written to {target}\nreplay: {replay}"
        )

    def _send(self: Any, event: str, payload: Dict[str, Any]) -> None:
        cmd: Dict[str, Any] = {"send": event}
        if payload:
            cmd["payload"] = payload
        self.trace.append(cmd)
        receipt = self.interp.send(event, wait=True, **payload)
        if receipt.error is not None:
            self._fail(
                f"sending {event} raised {type(receipt.error).__name__}: "
                f"{receipt.error}"
            )
        # 📝 No `receipt.denied` check (battle #268): `can()` already
        #    gated the send, and a transition that round-trips through
        #    `always` back to the same configuration reports
        #    `changed=False, denied=True` when a sibling guard was refused
        #    on the way -- a false "denied event" failure.

    def teardown(self: Any) -> None:
        if self.interp.status == "running":
            self.interp.stop()

    def check(self: Any) -> None:
        for name, fn in invariants.items():
            _run_check(self, f"invariant {name!r}", fn)
        for state, fn in state_assertions.items():
            if self.interp.matches(state):
                _run_check(self, f"state assertion {state!r}", fn)

    body.update(
        __init__=__init__,
        _fail=_fail,
        _send=_send,
        teardown=teardown,
        xsm_check=hs.invariant()(check),
    )
    for event, rule_name in _rule_names(events).items():
        body[rule_name] = _event_rule(
            hs, hyp, event, strategies[event], allow_denied, rule_name
        )
    if clock:
        body["advance_clock"] = _clock_rule(hs, hyp, delays)
    if snapshot_roundtrip:
        body["snapshot_roundtrip"] = _roundtrip_rule(hs, machine)
    if guard_names:
        body["flip_guard"] = _guard_rule(hs, hyp, guard_names, guards)
    if not snapshot_roundtrip and not guard_names:
        # 📝 A final / event-less configuration leaves no rule enabled and
        #    Hypothesis refuses the run ("no progress can be made"). This
        #    no-op is enabled exactly then, so the run simply settles.
        body["settled"] = _settled_rule(hs, events, clock)

    cls: Any = type(
        f"ModelTest_{_ident(machine.id)}", (hs.RuleBasedStateMachine,), body
    )
    base = settings if settings is not None else hyp.settings()
    cls.TestCase.settings = hyp.settings(
        base, stateful_step_count=max_steps, deadline=None
    )
    cls._xsm_model_test = True
    cls.machine = machine
    return cls


def _run_check(self: Any, label: str, fn: Check) -> None:
    """One invariant / state assertion (#271 battle).

    ``None`` passes (an ``assert``-style check returns nothing); any other
    falsy value fails. ANY exception fails through `_fail` so the
    artefact is written -- a raw ``KeyError`` escaped with no script.
    """
    try:
        ok = fn(self.interp)
    except AssertionError as exc:
        self._fail(f"{label} failed: {exc}")
        return
    except _hypothesis().errors.HypothesisException:
        # 🛑 reviewer H1 (#271): `assume(...)` inside a check raises
        #    `UnsatisfiedAssumption`, an `Exception` subclass -- treating
        #    it as a failure wrote a script and shrank a non-bug. Hypothesis
        #    control flow passes through untouched.
        raise
    except Exception as exc:  # noqa: BLE001 -- user check, reported
        self._fail(f"{label} raised {type(exc).__name__}: {exc}")
        return
    if ok is not None and not ok:
        self._fail(f"{label} violated (returned {ok!r})")


def _rule_names(events: List[str]) -> Dict[str, str]:
    """``event -> unique rule attribute`` (battle #271: ``"A.B"`` and
    ``"A_B"`` both became ``send_A_B`` and one rule silently vanished)."""
    out: Dict[str, str] = {}
    used: Set[str] = set()
    for ev in events:
        base = name = f"send_{_ident(ev)}"
        n = 2
        while name in used:
            name = f"{base}_{n}"
            n += 1
        used.add(name)
        out[ev] = name
    return out


def _check_state_keys(
    machine: MachineNode[Any], state_assertions: Mapping[str, Check]
) -> None:
    """A key that names no state never runs -- a typo must fail loudly."""
    ids = [n.id for n in walk(machine)]
    bad = sorted(
        k
        for k in state_assertions
        if not any(
            i == k.lstrip("#") or i.endswith("." + k.lstrip("#")) for i in ids
        )
    )
    if bad:
        raise ValueError(
            f"model_test: state_assertions name states the chart does not "
            f"have: {bad}"
        )


def _ident(text: str) -> str:
    out = "".join(c if c.isalnum() else "_" for c in text)
    return out or "_"


def _event_rule(
    hs: Any,
    hyp: Any,
    event: str,
    strategy: Any,
    allow_denied: bool,
    rule_name: str,
) -> Any:
    def _pre(self: Any) -> bool:
        return _declares(self.interp, event)

    def _rule(self: Any, payload: Dict[str, Any]) -> None:
        if payload is None:
            payload = {}
        if not isinstance(payload, Mapping) or "type" in payload:
            raise TypeError(
                f"model_test: the payload strategy for {event!r} must "
                f"produce dicts without a 'type' key, got {payload!r}"
            )
        payload = dict(payload)
        # ✅ Payload first, then `can()` on THAT payload (#271 amendment):
        #    a payload-dependent guard is judged on what will be sent.
        if not allow_denied and not self.interp.can(Event(event, payload)):
            return
        self._send(event, payload)

    _rule.__name__ = rule_name
    return hs.precondition(_pre)(hs.rule(payload=strategy)(_rule))


def _settled_rule(hs: Any, events: List[str], clock: bool) -> Any:
    def _pre(self: Any) -> bool:
        if clock and _timer_armed(self.interp, self.clock):
            return False
        return not any(_declares(self.interp, e) for e in events)

    def _rule(self: Any) -> None:
        return None

    return hs.precondition(_pre)(hs.rule()(_rule))


def _clock_rule(hs: Any, hyp: Any, delays: List[float]) -> Any:
    st = hyp.strategies

    def _rule(self: Any, delay: Optional[float], jitter: int) -> None:
        if delay is None:
            # 📝 "to the next live timer": reaches `raise`/`sendTo` delays
            #    and computed delays no `after` key names.
            nxt = self.clock.next_due()
            delay = 0.0 if nxt is None else (nxt - self.clock.now()) * 1000
        ms = max(0.0, delay + jitter)
        self.trace.append({"clock": ms})
        self.clock.increment(ms)

    return hs.precondition(lambda self: _timer_armed(self.interp, self.clock))(
        hs.rule(
            delay=st.sampled_from([None, *delays]),
            jitter=st.sampled_from(_JITTER_MS),
        )(_rule)
    )


def _roundtrip_rule(hs: Any, machine: MachineNode[Any]) -> Any:
    def _rule(self: Any) -> None:
        interp = self.interp
        try:
            json.dumps(interp.context)
        except (TypeError, ValueError) as exc:
            self._fail(
                f"snapshot round-trip: context is not JSON-serialisable: "
                f"{exc} -- store money as integer cents or a str, or keep "
                f"such values out of context (a persisted snapshot would "
                f"restore them as str)"
            )
        blob = interp.get_snapshot()
        before = (
            set(interp.current_state_ids),
            json.loads(json.dumps(interp.context)),
        )
        interp.stop()
        restored: SyncInterpreter[Any] = SyncInterpreter.from_snapshot(
            blob,
            self.machine,
            clock=self.clock,
            restart_timers="resume",
            # 📝 battle #271: an invoke dormant at the snapshot is re-driven
            #    on the copy, so an `onDone`-reaching invariant cannot fail
            #    only because the model hopped onto a restored interpreter.
            restart_services=True,
        )
        restored.start()
        self.interp = restored
        after = (set(restored.current_state_ids), restored.context)
        if after != before:
            self._fail(
                f"snapshot round-trip changed the interpreter: {before!r} "
                f"-> {after!r}"
            )

    return hs.rule()(_rule)


def _guard_rule(
    hs: Any, hyp: Any, names: List[str], table: Dict[str, bool]
) -> Any:
    st = hyp.strategies

    def _rule(self: Any, name: str, value: bool) -> None:
        table[name] = value
        self.trace.append({"guard": name, "value": value})

    return hs.rule(name=st.sampled_from(names), value=st.booleans())(_rule)


# -----------------------------------------------------------------------------
# 🔀 events_strategy
# -----------------------------------------------------------------------------
def events_strategy(
    machine_or_path: Union[
        str, pathlib.Path, Mapping[str, Any], MachineNode[Any]
    ],
    *,
    length: int = 10,
) -> Any:
    """A strategy of valid event sequences (lists of event names).

    Each event is drawn from those ``can()`` accepts in the configuration
    the previous ones reached (stub logic unless a built `MachineNode` is
    given). Sequences stop early when no event is enabled.
    """
    hyp = _hypothesis()
    st = hyp.strategies
    machine, _, _ = _load(machine_or_path, None, {})
    events = _declared_events(machine)

    @st.composite  # type: ignore[untyped-decorator]
    def _seq(draw: Any) -> List[str]:
        n = draw(st.integers(0, length))
        interp = SyncInterpreter(machine, clock=SimulatedClock()).start()
        out: List[str] = []
        try:
            for _ in range(n):
                enabled = [e for e in events if interp.can(e)]
                if not enabled:
                    break
                ev = draw(st.sampled_from(enabled))
                interp.send(ev)
                out.append(ev)
        finally:
            if interp.status == "running":
                interp.stop()
        return out

    return _seq()
