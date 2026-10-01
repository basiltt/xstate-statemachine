# tests/test_battle_304_leaks_failures.py
# -----------------------------------------------------------------------------
# 🔥 Battle test for #304: leaks, perf, complex scenarios, failure injection
# -----------------------------------------------------------------------------
# 🏛️ `on_before_send` / `on_event_processed` / `Receipt.duplicate` /
#    `stub_logic` sit on the hot path of EVERY send on both engines. This
#    file attacks them where a unit test does not: ten thousand discarded
#    interpreters, ten thousand events through one, real Stately charts,
#    hostile payloads and event names, malformed receipts.
# 📝 Perf numbers are printed (run with `-s`), never asserted: budgets are
#    recorded on the reference runner, not on a laptop.
"""Leak, perf, complex-scenario and failure-injection tests for #304."""

from __future__ import annotations

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import asyncio
import gc
import json
import logging
import pathlib
import threading
import time
import tracemalloc
from typing import Any, Dict, List, Optional, Set, Tuple

# -------------------------------------------------------------------------
# 📦 Third-Party Imports
# -------------------------------------------------------------------------
import pytest

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    PluginBase,
    Receipt,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import (
    ImplementationMissingError,
    InvalidConfigError,
)
from src.xstate_statemachine.testing_utils import stub_logic

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"
ITERATIONS = 10_000
#: 📝 Measured growth stays in the low tens of KB; 200 KB is the ceiling
#:    from the contract. A real per-interpreter leak (~1 KB each) would
#:    blow through it by 50x.
GROWTH_CEILING_BYTES = 200 * 1024

LEAK_CFG = {
    "id": "leak",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {"on": {"GO": "b", "NOOP": {"actions": "touch"}}},
        "b": {"on": {"BACK": "a"}},
    },
}


# -------------------------------------------------------------------------
# 🧰 Helpers
# -------------------------------------------------------------------------
class Counter(PluginBase):
    """Counts hooks, stores nothing."""

    def __init__(self, block: Optional[str] = None) -> None:
        self.received = 0
        self.processed = 0
        self.block = block

    def on_before_send(self, interpreter, event):
        if self.block is not None and event.type == self.block:
            return Receipt(
                frozenset(interpreter.current_state_ids),
                False,
                duplicate=True,
            )
        return None

    def on_event_received(self, interpreter, event):
        self.received += 1

    def on_event_processed(self, interpreter, event, receipt):
        self.processed += 1


class Hoarder(PluginBase):
    """A user bug: keeps every receipt forever."""

    def __init__(self) -> None:
        self.kept: List[Receipt] = []

    def on_event_processed(self, interpreter, event, receipt):
        self.kept.append(receipt)


class NoopBoth(PluginBase):
    def on_before_send(self, interpreter, event):
        return None

    def on_event_processed(self, interpreter, event, receipt):
        return None


def _leak_logic() -> MachineLogic:
    return MachineLogic(actions={"touch": lambda i, c, e, a: None})


def _count_receipts() -> int:
    return sum(1 for o in gc.get_objects() if issubclass(type(o), Receipt))


def _traced_growth(step, warmup: int = 300) -> Tuple[int, int]:
    """Run ``step`` ITERATIONS times; return (growth N/2->N, total)."""
    for _ in range(warmup):
        step()
    gc.collect()
    tracemalloc.start()
    try:
        half = ITERATIONS // 2
        for _ in range(half):
            step()
        gc.collect()
        mid, _ = tracemalloc.get_traced_memory()
        for _ in range(ITERATIONS - half):
            step()
        gc.collect()
        end, _ = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return end - mid, end


async def _atraced_growth(step, warmup: int = 300) -> Tuple[int, int]:
    for _ in range(warmup):
        await step()
    gc.collect()
    tracemalloc.start()
    try:
        half = ITERATIONS // 2
        for _ in range(half):
            await step()
        gc.collect()
        mid, _ = tracemalloc.get_traced_memory()
        for _ in range(ITERATIONS - half):
            await step()
        gc.collect()
        end, _ = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return end - mid, end


# -------------------------------------------------------------------------
# 💧 1. Leaks
# -------------------------------------------------------------------------
class TestLeaksSync:
    def test_create_send_stop_discard_growth_is_bounded(self) -> None:
        # Arrange
        machine = create_machine(LEAK_CFG, logic=_leak_logic())

        def step() -> None:
            plug = Counter(block="NOOP")
            i = SyncInterpreter(machine).use(plug).start()
            i.send("GO")
            i.send("NOOP")  # short-circuited
            i.send("BACK")
            i.stop()

        # Act
        growth, total = _traced_growth(step)
        print(f"\n[leak sync] growth N/2->N={growth} B total={total} B")

        # Assert
        assert growth < GROWTH_CEILING_BYTES

    def test_long_lived_interpreter_does_not_accumulate_receipts(self) -> None:
        # Arrange
        machine = create_machine(LEAK_CFG, logic=_leak_logic())
        plug = Counter()
        i = SyncInterpreter(machine).use(plug).start()
        gc.collect()
        before_receipts = _count_receipts()
        before_threads = threading.active_count()

        # Act
        for n in range(ITERATIONS):
            i.send("GO" if n % 2 == 0 else "BACK")
        gc.collect()

        # Assert
        assert plug.processed == ITERATIONS
        assert _count_receipts() - before_receipts <= 2
        assert threading.active_count() == before_threads
        assert len(i._event_queue) == 0 if hasattr(i, "_event_queue") else True
        i.stop()

    def test_plugin_that_hoards_receipts_owns_the_growth(self) -> None:
        # Arrange
        machine = create_machine(LEAK_CFG, logic=_leak_logic())
        hoard = Hoarder()
        i = SyncInterpreter(machine).use(hoard).start()
        gc.collect()
        before = _count_receipts()

        # Act
        for n in range(2_000):
            i.send("GO" if n % 2 == 0 else "BACK")
        gc.collect()
        live = _count_receipts() - before
        hoard.kept.clear()
        gc.collect()
        after_clear = _count_receipts() - before

        # Assert: growth is exactly the plugin's list, gone once cleared
        assert live >= 2_000
        assert after_clear <= 2
        i.stop()


class TestLeaksAsync:
    @pytest.mark.asyncio
    async def test_create_send_stop_discard_growth_is_bounded(self) -> None:
        # Arrange
        machine = create_machine(LEAK_CFG, logic=_leak_logic())

        async def step() -> None:
            plug = Counter(block="NOOP")
            i = await Interpreter(machine).use(plug).start()
            await i.send("GO", wait=True)
            await i.send("NOOP", wait=True)  # short-circuited
            await i.send("BACK", wait=True)
            await i.stop()

        # Act
        growth, total = await _atraced_growth(step)
        print(f"\n[leak async] growth N/2->N={growth} B total={total} B")

        # Assert
        assert growth < GROWTH_CEILING_BYTES

    @pytest.mark.asyncio
    async def test_long_lived_interpreter_does_not_accumulate(self) -> None:
        # Arrange
        machine = create_machine(LEAK_CFG, logic=_leak_logic())
        plug = Counter()
        i = await Interpreter(machine).use(plug).start()
        gc.collect()
        before_receipts = _count_receipts()
        before_tasks = len(asyncio.all_tasks())

        # Act
        for n in range(ITERATIONS):
            await i.send("GO" if n % 2 == 0 else "BACK", wait=True)
        await asyncio.sleep(0.05)
        gc.collect()

        # Assert
        assert plug.processed == ITERATIONS
        assert _count_receipts() - before_receipts <= 2
        assert len(asyncio.all_tasks()) <= before_tasks
        await i.stop()
        await asyncio.sleep(0)
        assert len(asyncio.all_tasks()) < before_tasks + 1

    @pytest.mark.asyncio
    async def test_hoarding_plugin_is_the_only_growth(self) -> None:
        # Arrange
        machine = create_machine(LEAK_CFG, logic=_leak_logic())
        hoard = Hoarder()
        i = await Interpreter(machine).use(hoard).start()
        gc.collect()
        before = _count_receipts()

        # Act
        for n in range(2_000):
            await i.send("GO" if n % 2 == 0 else "BACK", wait=True)
        hoard.kept.clear()
        gc.collect()

        # Assert
        assert _count_receipts() - before <= 2
        await i.stop()


# -------------------------------------------------------------------------
# ⏱️ 2. Perf micro-check (report only)
# -------------------------------------------------------------------------
PERF_SENDS = 10_000


def _sync_us_per_send(plugins: int) -> float:
    machine = create_machine(LEAK_CFG, logic=_leak_logic())
    i = SyncInterpreter(machine)
    for _ in range(plugins):
        i.use(NoopBoth())
    i.start()
    t0 = time.perf_counter()
    for n in range(PERF_SENDS):
        i.send("GO" if n % 2 == 0 else "BACK")
    dt = time.perf_counter() - t0
    i.stop()
    return dt / PERF_SENDS * 1e6


async def _async_us_per_send(plugins: int) -> float:
    machine = create_machine(LEAK_CFG, logic=_leak_logic())
    i = Interpreter(machine)
    for _ in range(plugins):
        i.use(NoopBoth())
    await i.start()
    t0 = time.perf_counter()
    for n in range(PERF_SENDS):
        await i.send("GO" if n % 2 == 0 else "BACK", wait=True)
    dt = time.perf_counter() - t0
    await i.stop()
    return dt / PERF_SENDS * 1e6


class TestPerfReport:
    def test_sync_cost_of_hooks_is_reported_and_sane(self) -> None:
        # Act
        base = min(_sync_us_per_send(0) for _ in range(3))
        one = min(_sync_us_per_send(1) for _ in range(3))
        five = min(_sync_us_per_send(5) for _ in range(3))
        print(
            f"\n[perf sync] us/send 0={base:.1f} 1={one:.1f} 5={five:.1f} "
            f"ratios 1/0={one / base:.2f} 5/0={five / base:.2f}"
        )

        # Assert: report-only, but a hook must not cost an order of
        # magnitude (that would be a per-send `inspect` or similar).
        assert one / base < 10

    @pytest.mark.asyncio
    async def test_async_cost_of_hooks_is_reported_and_sane(self) -> None:
        # Act
        base = min([await _async_us_per_send(0) for _ in range(3)])
        one = min([await _async_us_per_send(1) for _ in range(3)])
        five = min([await _async_us_per_send(5) for _ in range(3)])
        print(
            f"\n[perf async] us/send 0={base:.1f} 1={one:.1f} 5={five:.1f} "
            f"ratios 1/0={one / base:.2f} 5/0={five / base:.2f}"
        )

        # Assert
        assert one / base < 10

    def test_guard_cache_is_invalidated_when_a_hook_is_rebound(self) -> None:
        """⚡ `_SafePlugin` caches its guarded wrapper per hook (battle
        #304 profiling). The cache is keyed on the underlying function,
        so rebinding a hook on a live plugin must take effect at once."""
        # Arrange
        seen: List[str] = []
        plugin = Counter()
        plugin.on_event_processed = lambda i, e, r: seen.append("first")
        interp = SyncInterpreter(
            create_machine(LEAK_CFG, logic=_leak_logic())
        ).use(plugin)
        interp.start()
        interp.send("GO")

        # Act: swap the hook on the same instance
        plugin.on_event_processed = lambda i, e, r: seen.append("second")
        interp.send("GO")
        interp.stop()

        # Assert
        assert seen == ["first", "second"]

    def test_guard_cache_returns_the_same_wrapper_object(self) -> None:
        # Arrange
        from src.xstate_statemachine.base_interpreter import _SafePlugin

        safe = _SafePlugin(NoopBoth())

        # Act / Assert: repeated lookups hit the cache (no fresh closure)
        assert safe.on_before_send is safe.on_before_send
        assert safe.on_event_processed is safe.on_event_processed


# -------------------------------------------------------------------------
# 🧩 3. Complex scenarios
# -------------------------------------------------------------------------
COMPLEX_CFG = {
    "id": "cx",
    "type": "parallel",
    "context": {"hits": 0},
    "states": {
        "editor": {
            "initial": "idle",
            "states": {
                "idle": {"on": {"TYPE": "typing"}},
                "typing": {
                    "initial": "word",
                    "states": {
                        "word": {"on": {"SPACE": "line"}},
                        "line": {},
                        "hist": {"type": "history", "history": "deep"},
                    },
                    "on": {"PAUSE": "paused", "SAVE": {"actions": "bump"}},
                },
                "paused": {"on": {"RESUME": "typing.hist"}},
            },
        },
        "net": {
            "initial": "up",
            "states": {
                "up": {
                    "on": {"DROP": "down", "CHECK": {"guard": "boomGuard"}},
                },
                "down": {
                    "entry": [{"type": "raise", "params": {"event": "RETRY"}}],
                    "on": {"RETRY": "up"},
                },
            },
        },
    },
}


def _complex_logic(ran: List[str]) -> MachineLogic:
    def boom_guard(c, e):
        raise ZeroDivisionError("guard bug")

    def bump(i, c, e, a):
        ran.append("bump")
        c["hits"] += 1

    return MachineLogic(
        actions={"bump": bump}, guards={"boomGuard": boom_guard}
    )


class Tape(PluginBase):
    def __init__(self) -> None:
        self.received: List[str] = []
        self.processed: List[Tuple[str, Receipt]] = []

    def on_event_received(self, interpreter, event):
        self.received.append(event.type)

    def on_event_processed(self, interpreter, event, receipt):
        self.processed.append((event.type, receipt))


class TestComplexScenarios:
    def test_nested_parallel_history_fire_once_with_correct_changed(
        self,
    ) -> None:
        # Arrange
        ran: List[str] = []
        tape = Tape()
        i = (
            SyncInterpreter(
                create_machine(COMPLEX_CFG, logic=_complex_logic(ran))
            )
            .use(tape)
            .start()
        )
        base = len(tape.processed)

        # Act
        steps = ["TYPE", "SPACE", "PAUSE", "RESUME", "NOPE", "SAVE"]
        for ev in steps:
            i.send(ev)

        # Assert: one hook per event, changed matches reality
        got = [(t, r.changed) for t, r in tape.processed[base:]]
        assert got == [
            ("TYPE", True),
            ("SPACE", True),
            ("PAUSE", True),
            ("RESUME", True),
            ("NOPE", False),
            ("SAVE", True),  # context changed via `bump`
        ]
        assert "cx.editor.typing.line" in i.current_state_ids  # deep history

    def test_raised_internal_event_gets_its_own_single_hook(self) -> None:
        # Arrange
        tape = Tape()
        i = (
            SyncInterpreter(
                create_machine(COMPLEX_CFG, logic=_complex_logic([]))
            )
            .use(tape)
            .start()
        )
        base = len(tape.processed)

        # Act
        i.send("DROP")  # entry raises RETRY -> up

        # Assert
        kinds = [t for t, _ in tape.processed[base:]]
        assert kinds.count("DROP") == 1
        assert kinds.count("RETRY") == 1
        assert len(tape.processed) == len(tape.received)

    def test_guard_that_raises_is_denied_and_hook_fires_once(self) -> None:
        # Arrange
        tape = Tape()
        i = (
            SyncInterpreter(
                create_machine(COMPLEX_CFG, logic=_complex_logic([]))
            )
            .use(tape)
            .start()
        )
        base = len(tape.processed)

        # Act
        receipt = i.send("CHECK", wait=True)

        # Assert: a raising guard is "False" -> denied, not an error
        assert receipt.denied is True
        assert receipt.changed is False
        assert receipt.error is None
        assert [t for t, _ in tape.processed[base:]] == ["CHECK"]

    def test_action_raising_mid_list_still_delivers_one_receipt(self) -> None:
        # Arrange
        ran: List[str] = []

        def boom(i, c, e, a):
            raise RuntimeError("mid-list")

        cfg = {
            "id": "ml",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "X": {
                            "target": "b",
                            "actions": ["one", "boom", "two"],
                        }
                    }
                },
                "b": {},
            },
        }
        logic = MachineLogic(
            actions={
                "one": lambda i, c, e, a: ran.append("one"),
                "boom": boom,
                "two": lambda i, c, e, a: ran.append("two"),
            }
        )
        tape = Tape()
        i = SyncInterpreter(create_machine(cfg, logic=logic)).use(tape)
        i.start()

        # Act
        receipt = i.send("X", wait=True)

        # Assert
        assert ran == ["one"]
        assert isinstance(receipt.error, RuntimeError)
        assert [t for t, _ in tape.processed] == ["X"]
        assert tape.processed[0][1] is receipt

    def test_after_and_raise_interleaved_hook_per_event(self) -> None:
        # Arrange
        cfg = {
            "id": "ar",
            "initial": "a",
            "states": {
                "a": {
                    "on": {"GO": "b"},
                },
                "b": {
                    "entry": [{"type": "raise", "params": {"event": "INNER"}}],
                    "after": {"50": "c"},
                    "on": {"INNER": {"actions": []}},
                },
                "c": {},
            },
        }
        clk = SimulatedClock()
        tape = Tape()
        i = SyncInterpreter(create_machine(cfg), clock=clk).use(tape).start()

        # Act
        i.send("GO")
        clk.increment(60)
        i.tick()

        # Assert
        kinds = [t for t, _ in tape.processed]
        assert kinds[0] == "GO"
        assert "INNER" in kinds
        assert any(k.startswith("after.") for k in kinds)
        assert len(tape.processed) == len(tape.received)
        assert "ar.c" in i.current_state_ids

    @pytest.mark.asyncio
    async def test_snapshot_restores_on_other_engine_with_hooks(self) -> None:
        # Arrange: run on SYNC, snapshot, restore on ASYNC (and back)
        machine = create_machine(COMPLEX_CFG, logic=_complex_logic([]))
        src = SyncInterpreter(machine).start()
        src.send("TYPE")
        src.send("SPACE")
        snap = src.get_snapshot()
        tape = Tape()

        # Act
        restored = Interpreter.from_snapshot(snap, machine, plugins=[tape])
        await restored.start()
        receipt = await restored.send("PAUSE", wait=True)

        # Assert
        assert receipt.duplicate is False
        assert "PAUSE" in [t for t, _ in tape.processed]
        assert tape.processed[-1][1].duplicate is False
        snap2 = restored.get_snapshot()
        await restored.stop()
        tape2 = Tape()
        back = SyncInterpreter.from_snapshot(snap2, machine, plugins=[tape2])
        back.start()
        back.send("RESUME")
        assert [t for t, _ in tape2.processed][-1] == "RESUME"


def _collect_events(node: Any, out: Set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "on" and isinstance(value, dict):
                out.update(k for k in value if k and k != "*")
            _collect_events(value, out)
    elif isinstance(node, list):
        for value in node:
            _collect_events(value, out)


CHARTS = [
    "APA_Logic",
    "ConsoleLifecycle",
    "CopilotChat",
    "ED",
    "Hierarchy",
    "Parallelism",
    "Parking",
    "Kiosk",
    "atm",
    "authStateMachine",
    "hiLoGame",
    "slot",
    "game_v2",
    "debt_v8",
]


def _load(name: str) -> Dict[str, Any]:
    return json.loads((CORPUS / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _quiet_logs():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


class TestCorpusCharts:
    @pytest.mark.parametrize("name", CHARTS)
    def test_sync_hook_count_equals_events_admitted(self, name) -> None:
        # Arrange
        cfg = _load(name)
        events: Set[str] = set()
        _collect_events(cfg, events)
        tape = Tape()
        machine = create_machine(cfg, logic=stub_logic(cfg))
        i = SyncInterpreter(machine, clock=SimulatedClock()).use(tape)
        i.start()

        # Act
        for ev in sorted(events):
            i.send(ev)

        # Assert
        assert events
        assert len(tape.processed) == len(tape.received)
        assert len(tape.processed) >= 1
        assert all(isinstance(r, Receipt) for _, r in tape.processed)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", CHARTS)
    async def test_async_hook_count_equals_events_admitted(self, name) -> None:
        # Arrange
        cfg = _load(name)
        events: Set[str] = set()
        _collect_events(cfg, events)
        tape = Tape()
        machine = create_machine(cfg, logic=stub_logic(cfg))
        i = Interpreter(machine, clock=SimulatedClock()).use(tape)
        await i.start()

        # Act
        for ev in sorted(events):
            await asyncio.wait_for(i.send(ev, wait=True), timeout=5)
        await asyncio.sleep(0.02)

        # Assert
        assert events
        assert len(tape.processed) == len(tape.received)
        assert len(tape.processed) >= 1
        await i.stop()


# -------------------------------------------------------------------------
# 💉 4. Failure injection
# -------------------------------------------------------------------------
SMALL_CFG = {
    "id": "s",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {}},
}


class TestFailureInjection:
    def test_five_field_unpacking_of_receipt_fails_clearly(self) -> None:
        # Arrange
        receipt = Receipt(frozenset({"x"}), True)

        # Act / Assert: documented break -- loud ValueError naming the arity
        with pytest.raises(ValueError, match="too many values"):
            state_ids, changed, error, deferred, denied = receipt

    def test_receipt_with_wrong_arity_raises_clear_typeerror(self) -> None:
        with pytest.raises(TypeError, match="positional argument"):
            Receipt(frozenset(), True, None, False, False, False, "extra")
        with pytest.raises(TypeError, match="state_ids|changed|missing"):
            Receipt()  # type: ignore[call-arg]

    def test_interceptor_returning_list_state_ids_is_passed_through(
        self,
    ) -> None:
        # Arrange: a Receipt whose `state` is not a frozenset (NamedTuple
        #    does not coerce) -- the engine hands it back untouched.
        class Sloppy(PluginBase):
            def on_before_send(self, interpreter, event):
                return Receipt(["s.a"], False, duplicate=True)  # type: ignore

        i = SyncInterpreter(create_machine(SMALL_CFG)).use(Sloppy()).start()

        # Act
        receipt = i.send("GO", wait=True)

        # Assert: no crash, event not admitted, caller sees the plugin's value
        assert receipt.duplicate is True
        assert receipt.state_ids == ["s.a"]
        assert i.current_state_ids == {"s.a"}

    @pytest.mark.parametrize("engine", ["sync", "async"])
    def test_one_megabyte_payload_flows_through_both_hooks(
        self, engine
    ) -> None:
        # Arrange
        blob = "x" * (1024 * 1024)
        seen: List[int] = []

        class Probe(PluginBase):
            def on_before_send(self, interpreter, event):
                seen.append(len(event.payload["blob"]))

            def on_event_processed(self, interpreter, event, receipt):
                seen.append(len(event.payload["blob"]))

        machine = create_machine(SMALL_CFG)

        # Act
        if engine == "sync":
            i = SyncInterpreter(machine).use(Probe()).start()
            receipt = i.send("GO", wait=True, blob=blob)
        else:

            async def run():
                j = await Interpreter(machine).use(Probe()).start()
                r = await j.send("GO", wait=True, blob=blob)
                await j.stop()
                return r

            receipt = asyncio.run(run())

        # Assert
        assert receipt.changed
        assert seen == [len(blob), len(blob)]

    @pytest.mark.parametrize(
        "name",
        ["BAD\x00NAME", "‮RTL‬", "E" * 10_240, "ünï-事件-🔥"],
    )
    def test_hostile_event_names_get_exactly_one_hook(self, name) -> None:
        # Arrange
        tape = Tape()
        i = SyncInterpreter(create_machine(SMALL_CFG)).use(tape).start()

        # Act
        receipt = i.send(name, wait=True)

        # Assert: an undeclared event is a clean no-op with one hook
        assert receipt.changed is False
        assert [t for t, _ in tape.processed] == [name]

    def test_stub_logic_covers_unicode_and_object_actions(self) -> None:
        # Arrange
        cfg = {
            "id": "u",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [{"type": "действие"}, "ação_直"],
                    "exit": "🔥",
                    "on": {
                        "GO": {
                            "target": "b",
                            "actions": [{"type": "obj", "params": {"k": 1}}],
                        }
                    },
                },
                "b": {},
            },
        }
        ran: List[str] = []

        # Act
        machine = create_machine(cfg, logic=stub_logic(cfg, ran=ran))
        i = SyncInterpreter(machine).start()
        i.send("GO")

        # Assert
        assert set(ran) >= {"действие", "ação_直", "obj", "🔥"}

    def test_stub_logic_supplies_every_guard_form_and_invoke(self) -> None:
        # Arrange
        cfg = {
            "id": "g",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "S": {"target": "b", "guard": "plain"},
                        "O": {"target": "b", "guard": {"type": "obj"}},
                        "P": {
                            "target": "b",
                            "guard": {"type": "param", "params": {"n": 1}},
                        },
                        "N": {"target": "b", "guard": "!neg"},
                        "C": {
                            "target": "b",
                            "guard": {
                                "type": "and",
                                "children": [
                                    "c1",
                                    {"type": "or", "children": ["c2", "c3"]},
                                    {"type": "not", "children": ["c4"]},
                                ],
                            },
                        },
                        "I": {
                            "target": "b",
                            "guard": {
                                "type": "stateIn",
                                "params": {"state": "#g.a"},
                            },
                        },
                        "L": "loading",
                    }
                },
                "b": {"on": {"BACK": "a"}},
                "loading": {
                    "invoke": {
                        "src": "fetch",
                        "onDone": {"target": "b", "guard": "ok"},
                        "onError": "a",
                    }
                },
            },
        }

        for ev in ("S", "O", "P", "N", "C", "I", "L"):
            # Act: nothing may raise ImplementationMissingError
            try:
                machine = create_machine(cfg, logic=stub_logic(cfg))
                i = SyncInterpreter(machine).start()
                i.send(ev)
            except ImplementationMissingError as exc:  # pragma: no cover
                pytest.fail(f"{ev}: {exc}")

            # Assert
            assert i.current_state_ids != {"g.a"} or ev in {"N", "C"}

    @pytest.mark.parametrize("bad", [5, None, [], "machine", 3.5])
    def test_stub_logic_non_mapping_raises_what_create_machine_raises(
        self, bad
    ) -> None:
        # Arrange
        with pytest.raises(InvalidConfigError) as expected:
            create_machine(bad)  # type: ignore[arg-type]

        # Act / Assert: not a misleading TypeError
        with pytest.raises(InvalidConfigError) as got:
            stub_logic(bad)  # type: ignore[arg-type]
        assert str(got.value) == str(expected.value)

    @pytest.mark.parametrize(
        "bad",
        [
            {"initial": "a", "states": {"a": {}}},  # no id
            {"id": "m", "states": []},  # states wrong type
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"E": {"target": "zz"}}}},
            },  # unresolvable target
        ],
    )
    def test_stub_logic_invalid_mapping_raises_create_machine_error(
        self, bad
    ) -> None:
        # Arrange
        with pytest.raises(InvalidConfigError) as expected:
            create_machine(bad)

        # Act / Assert
        with pytest.raises(InvalidConfigError) as got:
            stub_logic(bad)
        assert str(got.value) == str(expected.value)
