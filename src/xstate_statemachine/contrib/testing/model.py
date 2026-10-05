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
import typing
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from ...clock import SimulatedClock
from ...events import Event
from ...exceptions import MissingExtraError
from ...factory import create_machine
from ...graph import UNKNOWN_DELAY_MS
from ...machine_logic import MachineLogic
from ...models import MachineNode, StateNode
from ...sync_interpreter import SyncInterpreter
from ...testing_utils import logic_names, stub_logic
from ...validation import walk

__all__ = ["model_test", "events_strategy", "payload_strategy"]

Check = Callable[[Any], Any]
#: Set by the pytest plugin from ``--xsm-failing-dir`` (None: next to the
#: module that called `model_test`).
FAILING_DIR: Optional[pathlib.Path] = None
FAILING_NAME = "failing.json"
_JITTER_MS = (-1, 0, 1)


def _hypothesis() -> Any:
    try:
        import hypothesis  # noqa: F401
    except ImportError as exc:
        raise MissingExtraError(
            "testing", "hypothesis", hint=f"(import failed: {exc})"
        ) from exc
    return hypothesis


# -----------------------------------------------------------------------------
# 🏗️ Machine + chart facts
# -----------------------------------------------------------------------------
def _load(
    source: Union[str, pathlib.Path, Mapping[str, Any], MachineNode],
    logic: Any,
    guards: Dict[str, bool],
) -> Tuple[MachineNode, bool, Optional[pathlib.Path]]:
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
    if not isinstance(logic, MachineLogic):
        raise TypeError(
            f"model_test: logic= must be a MachineLogic or a factory "
            f"returning one, got {type(logic).__name__}"
        )
    return create_machine(config, logic=logic), False, path


def _declared_events(machine: MachineNode) -> List[str]:
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


def _delays(machine: MachineNode) -> List[float]:
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


def _active_nodes(interp: SyncInterpreter) -> List[StateNode]:
    return list(interp._active_state_nodes)


def _declares(interp: SyncInterpreter, event: str) -> bool:
    # 📝 Battle #268: a machine whose root reached a final state is `done`
    #    but keeps its last configuration; an event declared there is NOT
    #    sendable (InterpreterStoppedError) -- the run has settled.
    if interp.status != "running":
        return False
    return any(event in n.on for n in _active_nodes(interp))


def _timer_armed(interp: SyncInterpreter) -> bool:
    if interp.status != "running":
        return False
    return any(n.after for n in _active_nodes(interp))


# -----------------------------------------------------------------------------
# 📦 Payload strategies
# -----------------------------------------------------------------------------
def _annotation_strategy(st: Any, ann: Any) -> Any:
    origin = typing.get_origin(ann)
    args = typing.get_args(ann)
    if ann is Any:
        return st.none()
    if origin is typing.Literal:
        return st.sampled_from(args)
    if origin is Union:
        inner = [_annotation_strategy(st, a) for a in args]
        if any(s is None for s in inner):
            return None
        return st.one_of(*inner)
    if origin in (list, List, Sequence) and args:
        item = _annotation_strategy(st, args[0])
        return None if item is None else st.lists(item, max_size=5)
    table = {
        type(None): st.none(),
        bool: st.booleans(),
        int: st.integers(-1000, 1000),
        float: st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False),
        str: st.text(max_size=20),
    }
    return table.get(ann)


def payload_strategy(schema: Any) -> Any:
    """A Hypothesis strategy of payload dicts inferred from a pydantic model
    (an `EventModel`, or a validator built by `events_union`).

    Minimal type mapping: ``bool``, ``int``, ``float``, ``str``, ``None``,
    ``Literal[...]``, ``Optional`` / ``Union`` of those and ``List[...]``.

    Raises:
        ValueError: A required field whose type is outside that mapping --
            pass ``payloads={EVENT: strategy}`` for it instead.
    """
    hyp = _hypothesis()
    st = hyp.strategies
    model = getattr(schema, "__xsm_event_model__", schema)
    fields = getattr(model, "model_fields", None)
    if not isinstance(fields, dict):
        return st.just({})
    required: Dict[str, Any] = {}
    optional: Dict[str, Any] = {}
    for name, info in fields.items():
        if name == "type":
            continue
        strat = _annotation_strategy(st, info.annotation)
        if strat is None:
            if info.is_required():
                raise ValueError(
                    f"model_test: cannot infer a strategy for "
                    f"{getattr(model, '__name__', model)}.{name}: "
                    f"{info.annotation!r}; pass payloads={{...: strategy}}"
                )
            continue
        (required if info.is_required() else optional)[name] = strat
    return st.fixed_dictionaries(required, optional=optional)


def _payload_strategies(
    machine: MachineNode, events: List[str], payloads: Mapping[str, Any]
) -> Dict[str, Any]:
    st = _hypothesis().strategies
    out: Dict[str, Any] = {}
    unknown = sorted(set(payloads) - set(events))
    if unknown:
        raise ValueError(
            f"model_test: payloads= names events the chart does not "
            f"declare: {unknown}"
        )
    for ev in events:
        if ev in payloads:
            out[ev] = payloads[ev]
        elif ev in machine.event_schemas:
            out[ev] = payload_strategy(machine.event_schemas[ev])
        else:
            out[ev] = st.just({})
    return out


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
    machine_or_path: Union[str, pathlib.Path, Mapping[str, Any], MachineNode],
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
        clock: Generate a rule advancing the `SimulatedClock` by a declared
            ``after`` delay (±1 ms jitter) while a timer is armed.
        max_steps: Hypothesis ``stateful_step_count``.
        settings: A ``hypothesis.settings`` to start from.
        allow_denied: Also send events ``can()`` refuses (the precondition
            becomes "some active state declares the event"). A refused
            event is never a failure either way.
        snapshot_roundtrip: A rule persisting the interpreter mid-sequence
            and continuing on the restored copy; a context that is not
            JSON-serialisable (or does not survive the trip) fails.
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
        self.interp = SyncInterpreter(machine, clock=self.clock).start()
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
            try:
                ok = fn(self.interp)
            except AssertionError as exc:
                self._fail(f"invariant {name!r} failed: {exc}")
            if not ok:
                self._fail(f"invariant {name!r} violated")
        for state, fn in state_assertions.items():
            if not self.interp.matches(state):
                continue
            try:
                ok = fn(self.interp)
            except AssertionError as exc:
                self._fail(f"state assertion {state!r} failed: {exc}")
            if ok is False:
                self._fail(f"state assertion {state!r} violated")

    body.update(
        __init__=__init__,
        _fail=_fail,
        _send=_send,
        teardown=teardown,
        xsm_check=hs.invariant()(check),
    )
    for event in events:
        body[f"send_{_ident(event)}"] = _event_rule(
            hs, hyp, event, strategies[event], allow_denied
        )
    if delays:
        body["advance_clock"] = _clock_rule(hs, hyp, delays)
    if snapshot_roundtrip:
        body["snapshot_roundtrip"] = _roundtrip_rule(hs, machine)
    if guard_names:
        body["flip_guard"] = _guard_rule(hs, hyp, guard_names, guards)
    if not snapshot_roundtrip and not guard_names:
        # 📝 A final / event-less configuration leaves no rule enabled and
        #    Hypothesis refuses the run ("no progress can be made"). This
        #    no-op is enabled exactly then, so the run simply settles.
        body["settled"] = _settled_rule(hs, events, bool(delays))

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


def _ident(text: str) -> str:
    out = "".join(c if c.isalnum() else "_" for c in text)
    return out or "_"


def _event_rule(
    hs: Any, hyp: Any, event: str, strategy: Any, allow_denied: bool
) -> Any:
    def _pre(self: Any) -> bool:
        return _declares(self.interp, event)

    def _rule(self: Any, payload: Dict[str, Any]) -> None:
        payload = dict(payload or {})
        # ✅ Payload first, then `can()` on THAT payload (#271 amendment):
        #    a payload-dependent guard is judged on what will be sent.
        if not allow_denied and not self.interp.can(Event(event, payload)):
            return
        self._send(event, payload)

    _rule.__name__ = f"send_{_ident(event)}"
    return hs.precondition(_pre)(hs.rule(payload=strategy)(_rule))


def _settled_rule(hs: Any, events: List[str], clock: bool) -> Any:
    def _pre(self: Any) -> bool:
        if clock and _timer_armed(self.interp):
            return False
        return not any(_declares(self.interp, e) for e in events)

    def _rule(self: Any) -> None:
        return None

    return hs.precondition(_pre)(hs.rule()(_rule))


def _clock_rule(hs: Any, hyp: Any, delays: List[float]) -> Any:
    st = hyp.strategies

    def _rule(self: Any, delay: float, jitter: int) -> None:
        ms = max(0.0, delay + jitter)
        self.trace.append({"clock": ms})
        self.clock.increment(ms)

    return hs.precondition(lambda self: _timer_armed(self.interp))(
        hs.rule(
            delay=st.sampled_from(delays), jitter=st.sampled_from(_JITTER_MS)
        )(_rule)
    )


def _roundtrip_rule(hs: Any, machine: MachineNode) -> Any:
    def _rule(self: Any) -> None:
        interp = self.interp
        try:
            json.dumps(interp.context)
        except (TypeError, ValueError) as exc:
            self._fail(
                f"snapshot round-trip: context is not JSON-serialisable: {exc}"
            )
        blob = interp.get_snapshot()
        before = (
            set(interp.current_state_ids),
            json.loads(json.dumps(interp.context)),
        )
        interp.stop()
        restored: SyncInterpreter[Any] = SyncInterpreter.from_snapshot(
            blob, machine, clock=self.clock, restart_timers="resume"
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
    machine_or_path: Union[str, pathlib.Path, Mapping[str, Any], MachineNode],
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

    @st.composite
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
