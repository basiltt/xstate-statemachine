# tests/test_review_fixes_runtime.py
# -----------------------------------------------------------------------------
# 🧪 Regression tests for the "runtime-utils" code-quality review (RU-*)
# -----------------------------------------------------------------------------
"""Pins the fixes for clock, helpers, exceptions, task manager, plugins,
receipts, graph, testing utils, actor logic and the package front door."""

from __future__ import annotations

import asyncio
import doctest
import gc
import inspect
import logging
import pickle
import re
import weakref
from collections import namedtuple
from pathlib import Path
from typing import Any, List

import pytest

import xstate_statemachine as xsm
from xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
    exceptions,
    plugins,
)
from xstate_statemachine.clock import RealClock
from xstate_statemachine.events import Receipt
from xstate_statemachine.helpers import (
    WaitTerminatedError,
    get_initial_snapshot,
    get_next_snapshot,
    to_promise,
    transition,
    wait_for,
    wait_for_sync,
)
from xstate_statemachine.plugins import PluginBase, redact
from xstate_statemachine.receipts import (
    ReceiptError,
    receipt_to_json,
    receipt_to_status,
)
from xstate_statemachine.task_manager import TaskManager

SRC = Path(xsm.__file__).parent

TOGGLE = {
    "id": "t",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {"on": {"BACK": "a"}}},
}
DONE_CHART = {
    "id": "d",
    "initial": "a",
    "on": {"RESET": ".a"},
    "states": {"a": {"on": {"GO": "b"}}, "b": {"type": "final"}},
}


# =============================================================================
# RU-01 / RU-02 / RU-26 -- clock delivery contract and boundary validation
# =============================================================================
@pytest.mark.parametrize("clock_cls", [SimulatedClock, RealClock])
def test_raising_timer_does_not_drop_the_rest_of_the_batch(clock_cls) -> None:
    # Arrange
    clock = clock_cls()
    fired: List[str] = []

    def boom() -> None:
        raise RuntimeError("first")

    clock.set_timeout(boom, 0.0, sync=True)
    clock.set_timeout(lambda: fired.append("B"), 0.0, sync=True)

    # Act / Assert: the first error surfaces AFTER the batch ran
    with pytest.raises(RuntimeError, match="first"):
        clock.pump()
    assert fired == ["B"]
    assert clock.pending == 0


def test_simulated_increment_survives_a_raising_timer() -> None:
    clock = SimulatedClock()
    fired: List[str] = []

    def boom() -> None:
        raise ValueError("x")

    clock.set_timeout(boom, 1.0)
    clock.set_timeout(lambda: fired.append("B"), 1.0)
    clock.set_timeout(lambda: fired.append("C"), 2.0)

    with pytest.raises(ValueError):
        clock.increment(5000)

    assert fired == ["B", "C"]
    assert clock.now() == 5.0  # the clock is not left mid-window


@pytest.mark.parametrize("clock_cls", [SimulatedClock, RealClock])
def test_timer_cleared_by_an_earlier_sibling_does_not_fire(clock_cls) -> None:
    clock = clock_cls()
    fired: List[str] = []
    handles: List[Any] = []

    def a() -> None:
        fired.append("A")
        clock.clear_timeout(handles[0])

    clock.set_timeout(a, 0.0, sync=True)
    handles.append(
        clock.set_timeout(lambda: fired.append("B"), 0.0, sync=True)
    )

    clock.pump()

    assert fired == ["A"]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_simulated_clock_rejects_non_finite_numbers(bad: float) -> None:
    clock = SimulatedClock()
    for call in (
        lambda: clock.increment(bad),
        lambda: clock.set(bad),
        lambda: clock.fire_until(bad),
        lambda: clock.set_timeout(lambda: None, bad),
    ):
        with pytest.raises(ValueError, match="finite"):
            call()
    clock.increment(10)  # still usable: nothing wedged
    assert clock.now() == pytest.approx(0.01)


def test_real_clock_rejects_nan_delay() -> None:
    with pytest.raises(ValueError, match="finite"):
        RealClock().set_timeout(lambda: None, float("nan"), sync=True)


def test_typed_advance_entry_points() -> None:
    clock = SimulatedClock()
    fired: List[int] = []
    clock.set_timeout(lambda: fired.append(1), 1.0)
    clock.advance_sync(1000)
    assert fired == [1]

    clock.set_timeout(lambda: fired.append(2), 1.0)
    asyncio.run(clock.advance(1000))
    assert fired == [1, 2]
    with pytest.raises(ValueError):
        clock.advance_sync(-1)


# =============================================================================
# RU-03 -- the pure API must not pin machines in memory
# =============================================================================
def test_pure_api_does_not_leak_machines() -> None:
    machine = create_machine(TOGGLE)
    snap = get_next_snapshot(machine, get_initial_snapshot(machine), "GO")
    assert snap.matches("b")
    ref = weakref.ref(machine)

    del machine, snap
    gc.collect()

    assert ref() is None


def test_pure_api_probe_cache_still_reuses_the_probe() -> None:
    from xstate_statemachine import helpers

    machine = create_machine(TOGGLE)
    p1, _ = helpers._build_probe(machine, None, None)
    p2, _ = helpers._build_probe(machine, None, None)
    assert p1 is p2
    assert machine in helpers._probes()


def test_copied_machine_gets_its_own_probe() -> None:
    import copy

    from xstate_statemachine import helpers

    machine = create_machine(TOGGLE)
    helpers._build_probe(machine, None, None)
    clone = copy.copy(machine)
    probe, _ = helpers._build_probe(clone, None, None)
    assert probe.machine is clone
    copy.deepcopy(machine)  # a threading.local in the slot must not break this


# =============================================================================
# RU-08 / RU-09 / RU-10 / RU-44 -- helpers
# =============================================================================
def test_wait_for_sync_stops_on_a_finished_machine() -> None:
    machine = create_machine(TOGGLE)
    interp = SyncInterpreter(machine).start()
    interp.stop()

    with pytest.raises(WaitTerminatedError) as info:
        wait_for_sync(interp, lambda i: False, timeout=None)

    assert info.value.status == "stopped"
    assert isinstance(info.value, TimeoutError)


def test_wait_for_sync_still_returns_when_predicate_holds() -> None:
    interp = SyncInterpreter(create_machine(TOGGLE)).start()
    interp.send("GO")
    assert (
        wait_for_sync(interp, lambda i: "t.b" in i.current_state_ids) is interp
    )


def test_wait_for_evaluates_the_predicate_once_per_iteration() -> None:
    async def go() -> int:
        interp = await Interpreter(create_machine(TOGGLE)).start()
        await interp.stop()
        calls = 0

        def predicate(_: Any) -> bool:
            nonlocal calls
            calls += 1
            return False

        with pytest.raises(WaitTerminatedError):
            await wait_for(interp, predicate, timeout=1)
        return calls

    assert asyncio.run(go()) == 1


def test_wait_terminated_error_pickles() -> None:
    err = pickle.loads(pickle.dumps(WaitTerminatedError("m", "done")))
    assert (str(err), err.status) == ("m", "done")


def test_to_promise_raises_when_error_status_has_no_error() -> None:
    class Fake:
        id = "fake"
        status = "error"
        error = None
        output = None
        current_state_ids: set = set()

    with pytest.raises(
        exceptions.XStateMachineError, match="without recording"
    ):
        asyncio.run(to_promise(Fake()))  # type: ignore[arg-type]


def test_transition_does_not_revive_a_done_snapshot() -> None:
    machine = create_machine(DONE_CHART)
    snap = get_next_snapshot(machine, get_initial_snapshot(machine), "GO")
    assert snap.status == "done"

    again, actions = transition(machine, snap, "RESET")

    assert again is snap
    assert actions == []
    assert again.status == "done"


# =============================================================================
# RU-11 / RU-37 -- exceptions survive pickling
# =============================================================================
_SAMPLES = {
    "StateNotFoundError": ("missing", "m.a"),
    "UnhandledEventError": ("EV", {"a"}),
    "TransitionFailedError": ("act", "m.a"),
    "TransitionNotAllowedError": ("EV", ["a"]),
    "SnapshotVersionError": (9, 4),
    "QueueOverflowError": ("m", 3, 2),
    "UnknownEventError": ("EV", "m", ["X"]),
    "InvalidEventPayloadError": ("EV", ValueError("why")),
    "ReentrantWaitError": ("m", "EV"),
    "RunawayChainError": ("m", 10, 2),
    "SnapshotMidStepError": ("m",),
    "SnapshotSerializationError": ("EV", ValueError("why")),
    "MissingExtraError": ("fastapi", "fastapi"),
    "ConflictError": ("k", 1, 2),
    "LockTimeoutError": ("k", 1.5),
    "SnapshotTooLargeError": ("k", 10, 5),
    "RestoredChainError": ("msg",),
    "ExplorationLimitError": (3, {}),
}


@pytest.mark.parametrize("name", exceptions.__all__)
def test_every_public_exception_round_trips_through_pickle(name: str) -> None:
    cls = getattr(exceptions, name)
    args = _SAMPLES.get(name, ("some message",))
    original = cls(*args)

    clone = pickle.loads(pickle.dumps(original))

    assert type(clone) is cls
    assert str(clone) == str(original)
    assert clone.__dict__.keys() == original.__dict__.keys()


def test_state_not_found_keeps_its_attributes_after_pickle() -> None:
    clone = pickle.loads(pickle.dumps(exceptions.StateNotFoundError("x", "y")))
    assert clone.target == "x"


def test_receipt_error_pickles() -> None:
    clone = pickle.loads(pickle.dumps(ReceiptError("Boom", "msg")))
    assert (clone.type, clone.message) == ("Boom", "msg")


def test_receipt_status_follows_the_error_mro() -> None:
    class IdempotencyMismatchError(Exception):
        pass

    class Sub(IdempotencyMismatchError):
        pass

    receipt = Receipt(frozenset(), False, Sub("x"))
    assert receipt_to_status(receipt) == 422


def test_receipt_to_json_can_omit_error_messages() -> None:
    receipt = Receipt(frozenset({"a"}), False, ValueError("card=4111"))
    assert receipt_to_json(receipt)["error"]["message"] == "card=4111"
    omitted = receipt_to_json(receipt, include_messages=False)
    assert omitted["error"] == {"type": "ValueError", "message": ""}


def test_status_no_op_alias() -> None:
    from xstate_statemachine import receipts

    assert receipts.STATUS_NO_OP == receipts.STATUS_NOT_MODIFIED_OK == 200


# =============================================================================
# RU-12 / RU-13 / RU-14 -- redaction
# =============================================================================
def test_redact_handles_namedtuples_and_cycles() -> None:
    nt = namedtuple("nt", "a b")
    data: dict = {"x": nt(1, {"token": "s"})}
    data["self"] = data

    out = redact(data)

    assert out["x"] == nt(1, {"token": "***"})
    assert out["self"] == "<cycle>"


@pytest.mark.parametrize(
    "key",
    ["shipping", "company", "footprint", "discard", "author", "spinner"],
)
def test_redact_does_not_over_redact_common_keys(key: str) -> None:
    assert redact({key: "visible"}) == {key: "visible"}


@pytest.mark.parametrize(
    "key",
    ["pin", "user_pin", "userPin", "cardNumber", "credit_card", "OTP", "auth"],
)
def test_redact_still_catches_short_secret_words(key: str) -> None:
    assert redact({key: "s"}) == {key: "***"}


def test_logging_inspector_redacts_error_args_and_output(caplog) -> None:
    inspector = plugins.LoggingInspector()
    interp = SyncInterpreter(create_machine(TOGGLE))

    with caplog.at_level(logging.INFO, logger="xstate_statemachine"):
        inspector.on_error(interp, ValueError({"password": "hunter2"}))
        inspector.on_done(interp, {"token": "t0k"})

    text = caplog.text
    assert "hunter2" not in text and "t0k" not in text
    assert "ValueError" in text


# =============================================================================
# RU-15 / RU-16 / RU-19 -- plugin contract
# =============================================================================
def _hooks() -> List[str]:
    return [n for n in vars(PluginBase) if n.startswith("on_")]


@pytest.mark.parametrize("hook", _hooks())
def test_every_plugin_hook_documents_engine_and_permissions(hook: str) -> None:
    doc = inspect.getdoc(getattr(PluginBase, hook)) or ""
    assert "Engines:" in doc, hook
    assert "May:" in doc, hook
    assert "Must not:" in doc, hook


def test_on_receipt_dropped_is_documented_async_only() -> None:
    doc = inspect.getdoc(PluginBase.on_receipt_dropped) or ""
    assert "Engines: async only" in doc


def test_event_drop_reasons_cover_every_emit_site() -> None:
    emitted = set()
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf8")
        emitted.update(
            re.findall(r"on_event_dropped\([^)]*?,\s*\"(\w+)\"\s*\)", text)
        )
    assert emitted, "the regex found no emit sites"
    assert emitted <= set(plugins.EVENT_DROP_REASONS), emitted


def test_register_global_rejects_non_plugins() -> None:
    with pytest.raises(TypeError, match="instantiate"):
        plugins.register_global(PluginBase)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        plugins.register_global("not a plugin")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        plugins.register_global(object())  # type: ignore[arg-type]
    assert plugins.global_plugins() == []


def test_register_global_accepts_duck_typed_plugins() -> None:
    class Duck:
        def on_transition(self, *args: Any) -> None:
            pass

    duck = Duck()
    try:
        plugins.register_global(duck)  # type: ignore[arg-type]
        assert plugins.global_plugins() == [duck]
    finally:
        plugins.clear_global_plugins()


# =============================================================================
# RU-30 / RU-31 -- TaskManager
# =============================================================================
def test_task_added_during_cancel_stays_tracked() -> None:
    async def go() -> bool:
        manager = TaskManager()
        gate = asyncio.Event()

        async def slow() -> None:
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                gate.set()
                await asyncio.sleep(0)  # a cancellation callback yields
                raise

        async def late() -> None:
            await asyncio.sleep(10)

        old = asyncio.ensure_future(slow())
        manager.add("o", old)
        await asyncio.sleep(0)
        newcomer = asyncio.ensure_future(late())

        async def add_late() -> None:
            await gate.wait()
            manager.add("o", newcomer)

        adder = asyncio.ensure_future(add_late())
        await manager.cancel_by_owner("o")
        await adder
        tracked = newcomer in manager.get_tasks_by_owner("o")
        await manager.cancel_all()
        return tracked

    assert asyncio.run(go()) is True


def test_finished_tasks_prune_their_owner_key() -> None:
    async def go() -> int:
        manager = TaskManager()

        async def quick() -> None:
            return None

        for i in range(5):
            manager.add(f"owner{i}", asyncio.ensure_future(quick()))
        await asyncio.sleep(0.01)
        return len(manager._tasks_by_owner)

    assert asyncio.run(go()) == 0


def test_cancel_by_owner_from_inside_an_owned_task() -> None:
    async def go() -> bool:
        manager = TaskManager()
        finished = False

        async def self_cancelling() -> None:
            nonlocal finished
            await manager.cancel_by_owner("o")
            finished = True

        task = asyncio.ensure_future(self_cancelling())
        manager.add("o", task)
        await asyncio.wait_for(task, 1)
        return finished

    assert asyncio.run(go()) is True


# =============================================================================
# RU-25 -- logic_names agrees for config and machine
# =============================================================================
_COMPOSITE = {
    "id": "m",
    "initial": "a",
    "states": {
        "a": {
            "on": {
                "GO": {
                    "target": "b",
                    "guard": {"type": "and", "children": ["g1", "g2"]},
                    "actions": ["save", "spawn_child"],
                }
            }
        },
        "b": {},
    },
}


def test_logic_names_agrees_for_config_and_machine() -> None:
    from xstate_statemachine.testing_utils import logic_names

    machine = create_machine(
        _COMPOSITE,
        logic=MachineLogic(
            actions={"save": lambda *a: None},
            guards={"g1": lambda c, e: True, "g2": lambda c, e: True},
            services={"child": lambda *a: None},
        ),
    )

    from_config = logic_names(_COMPOSITE)
    from_machine = logic_names(machine)

    assert from_config == from_machine
    actions, guards, services = from_config
    assert guards == {"g1", "g2"}
    assert actions == {"save"}
    assert services == {"child"}  # spawn_child is a SERVICE, as in LogicLoader


# =============================================================================
# RU-36 -- ExplorationLimitError is public and central
# =============================================================================
def test_exploration_limit_error_is_exported_and_shared() -> None:
    from xstate_statemachine import graph

    assert xsm.ExplorationLimitError is exceptions.ExplorationLimitError
    assert graph.ExplorationLimitError is exceptions.ExplorationLimitError
    assert "ExplorationLimitError" in exceptions.__all__
    assert issubclass(
        exceptions.ExplorationLimitError, exceptions.XStateMachineError
    )


def test_shortest_paths_still_raises_the_limit_error() -> None:
    from xstate_statemachine.graph import shortest_paths

    machine = create_machine(TOGGLE)
    with pytest.raises(xsm.ExplorationLimitError) as info:
        shortest_paths(machine, max_configs=1)
    assert info.value.limit == 1


# =============================================================================
# RU-32 / RU-33 -- actor logic
# =============================================================================
def test_send_back_to_a_stopped_interpreter_reports_the_drop() -> None:
    from xstate_statemachine.actor_logic import _send_back_for

    seen: List[Any] = []

    class Recorder(PluginBase):
        def on_event_dropped(self, interpreter, event, reason) -> None:
            seen.append((event.type, reason))

    interp = SyncInterpreter(create_machine(TOGGLE)).use(Recorder()).start()
    interp.stop()

    _send_back_for(interp)("LATE", n=1)

    assert seen == [("LATE", "stopped")]


def test_iterator_cleanup_on_a_loop_thread_does_not_warn(caplog) -> None:
    import threading

    from xstate_statemachine.actor_logic import from_iterator

    release = threading.Event()

    def stream(i: Any, c: Any, e: Any):
        yield 1
        release.wait(2)
        yield 2

    cfg = {
        "id": "s",
        "initial": "run",
        "states": {
            "run": {
                "invoke": {"src": "stream", "id": "st"},
                "on": {"STOP": "idle", "STREAM": {"actions": []}},
            },
            "idle": {},
        },
    }

    async def go() -> None:
        machine = create_machine(
            cfg, logic=MachineLogic(services={"stream": from_iterator(stream)})
        )
        interp = await Interpreter(machine).start()
        await asyncio.sleep(0.05)
        await interp.send("STOP", wait=True)
        release.set()
        await interp.stop()

    with caplog.at_level(logging.WARNING):
        asyncio.run(go())

    assert "blocked inside next()" not in caplog.text


# =============================================================================
# RU-38 -- deprecations hot path and namespace
# =============================================================================
def test_deprecated_is_once_per_call_site_and_registers_lazily() -> None:
    from xstate_statemachine import deprecations as dep

    dep.reset_deprecation_warnings()
    import warnings

    def shim() -> bool:
        return dep.deprecated(
            "RU-test-thing", since="0.12.0", removal="1.0", alternative="x"
        )

    def user() -> List[bool]:
        return [shim() for _ in range(3)]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = user()

    assert results == [True, False, False] or results.count(True) == 1
    assert not hasattr(dep, "_name")
    assert any(d.what == "RU-test-thing" for d in dep.deprecations())


# =============================================================================
# RU-07 / RU-40 -- package front door
# =============================================================================
def test_package_docstring_example_runs() -> None:
    failures, attempted = doctest.testmod(
        xsm, optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
    )
    assert attempted > 0
    assert failures == 0


def test_dir_lists_the_public_surface_without_typing_leaks() -> None:
    names = set(dir(xsm))
    assert set(xsm.__all__) <= names
    for leaked in ("Any", "Dict", "List", "Tuple", "TYPE_CHECKING"):
        assert leaked not in names


def test_star_import_and_lazy_attributes_resolve() -> None:
    namespace: dict = {}
    exec("from xstate_statemachine import *", namespace)
    for name in xsm.__all__:
        assert name in namespace, name
    for name in xsm._LAZY_ATTRS:
        assert getattr(xsm, name) is not None
