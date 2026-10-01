# tests/test_battle_305_mailbox_plugins_validator.py
# -----------------------------------------------------------------------------
# ⚔️ Battle tests for #305 part A: `SyncInterpreter.send_threadsafe` mailbox,
#    the global plugin registry, the `context_validator` seam and the
#    `__xstate_event__` adapter -- both engines wherever an engine is
#    involved. Async cases use `IsolatedAsyncioTestCase` / `asyncio.run`
#    (the CI test cells have no pytest-asyncio).
# -----------------------------------------------------------------------------
"""Adversarial coverage for #305 part A; defects found are pinned here."""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
from __future__ import annotations

import asyncio
import gc
import importlib
import logging
import subprocess
import sys
import threading
import time
import unittest
import weakref
from typing import Any, Dict, List

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from src.xstate_statemachine import (
    Event,
    Interpreter,
    MachineLogic,
    PluginBase,
    SyncInterpreter,
    create_machine,
    global_plugins,
    register_global,
    unregister_global,
)
from src.xstate_statemachine.exceptions import (
    InvalidEventError,
    UnknownEventError,
)

CFG: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {
            "on": {
                "GO": "b",
                "BUMP": {"actions": "bump"},
                "NOOP": {"actions": "noop"},
                "TWO": {"actions": ["bump", "bump", "noop"]},
                "SET": {
                    "actions": {
                        "type": "assign",
                        "params": {"assignment": {"n": 50}},
                    }
                },
                "SPAWN": {"actions": "spawn_kid"},
            }
        },
        "b": {"on": {"BACK": "a"}},
    },
}
KID = {
    "id": "kid",
    "initial": "x",
    "context": {"k": 0},
    "states": {"x": {"on": {"KB": {"actions": "kbump"}}}},
}


def bump(i: Any, c: Any, e: Any, a: Any) -> None:
    c["n"] = c.get("n", 0) + e.payload.get("by", 1)


def noop(i: Any, c: Any, e: Any, a: Any) -> None:
    return None


def kbump(i: Any, c: Any, e: Any, a: Any) -> None:
    c["k"] += 1


def logic() -> MachineLogic:
    kid = create_machine(KID, logic=MachineLogic(actions={"kbump": kbump}))
    return MachineLogic(
        actions={"bump": bump, "noop": noop}, services={"kid": kid}
    )


def machine(policy: str = "continue", validator: Any = None) -> Any:
    return create_machine(
        dict(CFG, actionErrorPolicy=policy),
        logic=logic(),
        context_validator=validator,
    )


class Counter:
    """A validator that counts calls and can be told to raise."""

    def __init__(self, limit: int = 10**9) -> None:
        self.calls = 0
        self.limit = limit

    def __call__(self, ctx: Any) -> None:
        self.calls += 1
        if ctx.get("n", 0) > self.limit:
            raise ValueError(f"n too big: {ctx['n']}")


class Recorder(PluginBase):
    def __init__(self) -> None:
        self.started: List[str] = []
        self.dropped: List[str] = []

    def on_interpreter_start(self, interpreter: Any) -> None:
        self.started.append(interpreter.id)

    def on_event_dropped(self, interpreter: Any, event: Any, why: Any) -> None:
        self.dropped.append(why)


class CountingAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def __xstate_event__(self) -> dict:
        self.calls += 1
        return {"type": "BUMP", "by": 1}


class _QuietLogs(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


# -----------------------------------------------------------------------------
# 🧵 Mailbox
# -----------------------------------------------------------------------------
class TestMailboxBattle(_QuietLogs):
    def test_sixteen_producers_with_concurrent_owner_sends_exact(self) -> None:
        # Arrange
        seen: List[tuple] = []

        def rec(i: Any, c: Any, e: Any, a: Any) -> None:
            c["n"] += 1
            seen.append((e.payload.get("t"), e.payload.get("k")))

        cfg = {
            "id": "q",
            "initial": "s",
            "context": {"n": 0},
            "states": {"s": {"on": {"E": {"actions": "rec"}}}},
        }
        i = SyncInterpreter(
            create_machine(cfg, logic=MachineLogic(actions={"rec": rec}))
        ).start()
        threads, per = 16, 2000
        go = threading.Event()

        def produce(t: int) -> None:
            go.wait(5)
            for k in range(per):
                i.send_threadsafe("E", t=t, k=k)

        ts = [threading.Thread(target=produce, args=(t,)) for t in range(16)]
        for t in ts:
            t.start()
        # Act -- the OWNER keeps sending while producers run
        go.set()
        owner = 0
        while any(t.is_alive() for t in ts):
            i.send("E", t="owner", k=owner)
            owner += 1
        for t in ts:
            t.join(10)
        i.tick()
        # Assert
        self.assertEqual(i.context["n"], threads * per + owner)
        self.assertEqual(len(set(seen)), len(seen))  # no duplicate
        for t in list(range(threads)) + ["owner"]:
            ks = [k for tt, k in seen if tt == t]
            self.assertEqual(ks, sorted(ks))  # FIFO per producer
            self.assertEqual(len(ks), per if t != "owner" else owner)
        i.stop()

    def test_producer_during_reentrant_send_in_action_runs_after(self) -> None:
        # Arrange: an action calls send() re-entrantly while a producer
        # posts to the mailbox mid-step.
        order: List[str] = []
        holder: Dict[str, Any] = {}

        def outer(i: Any, c: Any, e: Any, a: Any) -> None:
            order.append("outer")
            t = threading.Thread(target=lambda: i.send_threadsafe("X"))
            t.start()
            t.join(5)
            i.send("INNER")

        def mark(i: Any, c: Any, e: Any, a: Any) -> None:
            order.append(e.type)

        cfg = {
            "id": "r",
            "initial": "s",
            "states": {
                "s": {
                    "on": {
                        "OUTER": {"actions": "outer"},
                        "INNER": {"actions": "mark"},
                        "X": {"actions": "mark"},
                        "LATER": {"actions": "mark"},
                    }
                }
            },
        }
        holder["i"] = SyncInterpreter(
            create_machine(
                cfg, logic=MachineLogic(actions={"outer": outer, "mark": mark})
            )
        ).start()
        # Act
        holder["i"].send("OUTER")
        self.assertEqual(order, ["outer", "INNER"])  # X not mid-step
        holder["i"].send("LATER")
        # Assert -- mailbox drained ahead of the owner's next event
        self.assertEqual(order, ["outer", "INNER", "X", "LATER"])
        holder["i"].stop()

    def test_send_threadsafe_after_stop_is_reported_drop(self) -> None:
        # 🐛 DEFECT (fixed): the event sat in the mailbox forever, silently.
        rec = Recorder()
        i = SyncInterpreter(machine()).use(rec).start()
        i.stop()
        i.send_threadsafe("BUMP")
        self.assertEqual(len(i._mailbox), 0)
        self.assertEqual(rec.dropped, ["not_running"])

    def test_pending_mailbox_events_at_stop_are_reported(self) -> None:
        rec = Recorder()
        i = SyncInterpreter(machine()).use(rec).start()
        i.send_threadsafe("BUMP")
        i.send_threadsafe("BUMP")
        i.stop()
        self.assertEqual(rec.dropped, ["stopped", "stopped"])
        self.assertEqual(len(i._mailbox), 0)

    def test_batch_events_after_machine_finishes_mid_drain_are_reported(
        self,
    ) -> None:
        # 🐛 DEFECT (fixed): a mailbox batch whose middle event drove the
        #    machine to `final` kept running the trailing events through
        #    the finished machine, which discarded them with no hook.
        # Arrange
        cfg = {
            "id": "fin",
            "initial": "a",
            "context": {"n": 0},
            "states": {
                "a": {"on": {"INC": {"actions": "inc"}, "DIE": "done"}},
                "done": {"type": "final"},
            },
        }

        def inc(i: Any, c: Any, e: Any, a: Any) -> None:
            c["n"] += 1

        rec = Recorder()
        i = SyncInterpreter(
            create_machine(cfg, logic=MachineLogic(actions={"inc": inc}))
        ).use(rec)
        i.start()
        for _ in range(3):
            i.send_threadsafe("INC")
        i.send_threadsafe("DIE")
        for _ in range(5):
            i.send_threadsafe("INC")

        # Act
        i.tick()

        # Assert: 3 ran, the machine finished, 5 reported -- none lost
        self.assertEqual(i.status, "done")
        self.assertEqual(i.context["n"], 3)
        self.assertEqual(rec.dropped, ["not_running"] * 5)
        self.assertEqual(len(i._mailbox), 0)

    def test_tick_on_finished_machine_drains_stranded_mailbox(self) -> None:
        # Arrange: machine finishes via its own send(), THEN a producer posts
        rec = Recorder()
        cfg = {
            "id": "fin2",
            "initial": "a",
            "states": {
                "a": {"on": {"DIE": "done"}},
                "done": {"type": "final"},
            },
        }
        i = SyncInterpreter(create_machine(cfg)).use(rec).start()
        i.send("DIE")
        self.assertEqual(i.status, "done")
        # 📝 bypass send_threadsafe's own status gate to model the race
        #    where the producer enqueued just before the machine finished
        with i._mailbox_lock:
            i._mailbox.append(i._prepare_event("X"))

        # Act
        i.tick()

        # Assert
        self.assertEqual(rec.dropped, ["not_running"])
        self.assertEqual(len(i._mailbox), 0)

    def test_send_threadsafe_before_start_delivered_on_first_pump(
        self,
    ) -> None:
        # 📝 Documented behaviour: queued, NOT run by start(); the first
        # send()/tick() after start delivers it.
        i = SyncInterpreter(machine())
        i.send_threadsafe("BUMP")
        i.start()
        self.assertEqual(i.context["n"], 0)
        i.tick()
        self.assertEqual(i.context["n"], 1)
        i.stop()

    def test_hundred_thousand_queued_then_one_tick_is_bounded(self) -> None:
        i = SyncInterpreter(machine()).start()
        for _ in range(100_000):
            i.send_threadsafe("NOOP")
        i.send_threadsafe("BUMP")
        t0 = time.perf_counter()
        i.tick()  # would RecursionError if drained recursively
        self.assertLess(time.perf_counter() - t0, 60)
        self.assertEqual(i.context["n"], 1)
        self.assertEqual(len(i._mailbox), 0)
        i.stop()

    def test_payload_is_aliased_not_copied(self) -> None:
        # 📝 Documented: the engine does not copy payload VALUES; a producer
        # that mutates after enqueue is visible at drain time.
        seen: List[Any] = []

        def grab(i: Any, c: Any, e: Any, a: Any) -> None:
            seen.append(list(e.payload["items"]))

        cfg = {
            "id": "p",
            "initial": "s",
            "states": {"s": {"on": {"E": {"actions": "grab"}}}},
        }
        i = SyncInterpreter(
            create_machine(cfg, logic=MachineLogic(actions={"grab": grab}))
        ).start()
        items = [1]
        i.send_threadsafe("E", items=items)
        items.append(2)
        i.tick()
        self.assertEqual(seen, [[1, 2]])
        i.stop()

    def test_cross_thread_send_is_not_rejected_on_sync_engine(self) -> None:
        # 📝 Documented: the sync engine has no thread check (AGENTS.md:
        # "send() is not thread-safe and never was"). WrongThreadError is
        # async-only; the sync contract is "use send_threadsafe".
        i = SyncInterpreter(machine()).start()
        out: List[Any] = []
        t = threading.Thread(target=lambda: out.append(i.send("BUMP")))
        t.start()
        t.join(5)
        self.assertEqual(i.context["n"], 1)
        i.stop()

    def test_async_cross_thread_send_raises_actionable_error(self) -> None:
        from src.xstate_statemachine.exceptions import WrongThreadError

        async def go() -> Any:
            i = await Interpreter(machine()).start()
            box: List[Any] = []

            def other() -> None:
                try:
                    i.send("BUMP")
                except Exception as exc:  # noqa: BLE001
                    box.append(exc)

            t = threading.Thread(target=other)
            t.start()
            t.join(5)
            await i.stop()
            return box

        box = asyncio.run(go())
        self.assertIsInstance(box[0], WrongThreadError)
        self.assertIn("send_threadsafe()", str(box[0]))

    def test_interpreter_gc_after_stop_with_live_producer_no_hang(
        self,
    ) -> None:
        i = SyncInterpreter(machine()).start()
        ref = weakref.ref(i)
        stop = threading.Event()

        def produce(target: Any) -> None:
            while not stop.is_set():
                target.send_threadsafe("BUMP")
                time.sleep(0.001)

        t = threading.Thread(target=produce, args=(i,), daemon=True)
        t.start()
        time.sleep(0.02)
        i.stop()
        stop.set()
        t.join(5)
        self.assertFalse(t.is_alive())
        del i, t
        gc.collect()
        self.assertIsNone(ref())


# -----------------------------------------------------------------------------
# 🔌 __xstate_event__ adapter
# -----------------------------------------------------------------------------
class Raising:
    def __xstate_event__(self) -> Any:
        raise RuntimeError("adapter boom")


class ReturnsInt:
    def __xstate_event__(self) -> Any:
        return 7


class Undeclared:
    def __xstate_event__(self) -> Any:
        return "NOT_IN_CHART"


class TestAdapterBattle(_QuietLogs):
    def test_raising_adapter_fails_at_call_site_all_sync_paths(self) -> None:
        i = SyncInterpreter(machine()).start()
        for call in (
            lambda: i.send(Raising()),
            lambda: i.send_events([Raising()]),
            lambda: i.send_threadsafe(Raising()),
        ):
            with self.assertRaises(RuntimeError):
                call()
        self.assertEqual(len(i._mailbox), 0)
        i.stop()

    def test_non_event_return_is_invalid_event_on_threadsafe(self) -> None:
        i = SyncInterpreter(machine()).start()
        with self.assertRaises(InvalidEventError):
            i.send_threadsafe(ReturnsInt())
        i.stop()

    def test_strict_undeclared_type_fails_loud(self) -> None:
        m = create_machine(dict(CFG, strict=True), logic=logic())
        i = SyncInterpreter(m).start()
        with self.assertRaises(UnknownEventError):
            i.send(Undeclared())
        # 📝 threadsafe: strict runs on the OWNER at drain time.
        i.send_threadsafe(Undeclared())
        i.tick()
        self.assertIsInstance(i._last_action_error, UnknownEventError)
        i.stop()

    def test_adapter_called_once_per_sync_send_path(self) -> None:
        i = SyncInterpreter(machine()).start()
        for call in (
            lambda o: i.send(o),
            lambda o: i.send(o, wait=True),
            lambda o: i.send_events([o]),
            lambda o: i.send_threadsafe(o),
        ):
            o = CountingAdapter()
            call(o)
            i.tick()
            self.assertEqual(o.calls, 1)
        self.assertEqual(i.context["n"], 4)
        i.stop()


class TestAdapterAsync(unittest.IsolatedAsyncioTestCase):
    async def test_adapter_called_once_per_async_send_path(self) -> None:
        i = await Interpreter(machine()).start()
        a1, a2, a3 = CountingAdapter(), CountingAdapter(), CountingAdapter()
        await i.send(a1, wait=True)
        await i.send_events([a2])
        await asyncio.wrap_future(i.send_threadsafe(a3))
        await asyncio.sleep(0.05)
        self.assertEqual((a1.calls, a2.calls, a3.calls), (1, 1, 1))
        self.assertEqual(i.context["n"], 3)
        with self.assertRaises(RuntimeError):
            i.send_threadsafe(Raising())
        await i.stop()


# -----------------------------------------------------------------------------
# 🌐 Global registry
# -----------------------------------------------------------------------------
class TestGlobalRegistryBattle(_QuietLogs):
    def setUp(self) -> None:
        super().setUp()
        before = global_plugins()
        self.addCleanup(self._restore, before)

    @staticmethod
    def _restore(before: List[Any]) -> None:
        for p in global_plugins():
            if not any(p is b for b in before):
                unregister_global(p)

    def test_import_does_not_populate_registry(self) -> None:
        code = (
            "import src.xstate_statemachine as x;"
            "print(x.global_plugins() == [])"
        )
        out = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(out.stdout.strip(), "True", out.stderr)
        importlib.import_module("src.xstate_statemachine.plugins")

    def test_concurrent_register_and_construct_snapshots(self) -> None:
        # Arrange
        m = machine()
        errors: List[BaseException] = []
        made: List[Any] = []
        mine: List[Recorder] = [Recorder() for _ in range(100)]
        go = threading.Event()

        def churn(p: Recorder) -> None:
            go.wait(5)
            try:
                for _ in range(20):
                    register_global(p)
                    unregister_global(p)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        def build() -> None:
            go.wait(5)
            try:
                for _ in range(5):
                    snap = global_plugins()
                    i = SyncInterpreter(m)
                    after = global_plugins()
                    made.append((snap, i, after))
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        ts = [threading.Thread(target=churn, args=(p,)) for p in mine]
        ts += [threading.Thread(target=build) for _ in range(100)]
        for t in ts:
            t.start()
        # Act
        go.set()
        for t in ts:
            t.join(30)
        # Assert -- each interpreter's set lies between the two reads
        self.assertEqual(errors, [])
        for snap, i, after in made:
            got = [p.wrapped for p in i._plugins]
            self.assertEqual(len(got), len({id(p) for p in got}))
            for p in got:
                self.assertTrue(
                    any(p is q for q in snap)
                    or any(p is q for q in after)
                    or p in mine
                )
        for p in mine:
            self.assertFalse(unregister_global(p))

    def test_from_snapshot_and_spawned_child_receive_global(self) -> None:
        rec = Recorder()
        register_global(rec)
        try:
            i = SyncInterpreter(machine()).start()
            snap = i.get_snapshot()
            i.send("SPAWN")
            i.stop()
            j = SyncInterpreter.from_snapshot(snap, machine()).start()
            j.stop()
        finally:
            unregister_global(rec)
        self.assertEqual(rec.started.count("m"), 2)
        self.assertTrue(any(s != "m" for s in rec.started))

    def test_global_and_use_attach_twice_documented(self) -> None:
        # 📝 Documented: `.use()` does not deduplicate against the
        # registry -- the same object registered both ways sees each hook
        # TWICE. Register globally OR per instance, not both.
        rec = Recorder()
        register_global(rec)
        try:
            SyncInterpreter(machine()).use(rec).start().stop()
        finally:
            unregister_global(rec)
        self.assertEqual(rec.started, ["m", "m"])

    def test_unregister_never_registered_is_false_noop(self) -> None:
        self.assertFalse(unregister_global(Recorder()))

    def test_raising_global_start_hook_is_contained(self) -> None:
        class Boom(PluginBase):
            def on_interpreter_start(self, interpreter: Any) -> None:
                raise RuntimeError("plugin boom")

        b = Boom()
        register_global(b)
        try:
            i = SyncInterpreter(machine()).start()
            i.send("BUMP")
            self.assertEqual(i.context["n"], 1)
            i.stop()

            async def go() -> int:
                a = await Interpreter(machine()).start()
                await a.send("BUMP", wait=True)
                n = a.context["n"]
                await a.stop()
                return n

            self.assertEqual(asyncio.run(go()), 1)
        finally:
            unregister_global(b)


# -----------------------------------------------------------------------------
# 🧪 context_validator
# -----------------------------------------------------------------------------
class TestValidatorBattle(_QuietLogs):
    def test_rollback_after_assign_builtin_sync(self) -> None:
        v = Counter(limit=10)
        i = SyncInterpreter(machine("rollback", v)).start()
        r = i.send("SET", wait=True)
        self.assertEqual(i.context["n"], 0)
        self.assertIsInstance(r.error, ValueError)
        self.assertEqual(v.calls, 1)
        i.stop()

    def test_continue_keeps_mutation_and_sets_receipt_error(self) -> None:
        v = Counter(limit=10)
        i = SyncInterpreter(machine("continue", v)).start()
        r = i.send("SET", wait=True)
        self.assertEqual(i.context["n"], 50)
        self.assertIsInstance(r.error, ValueError)
        i.stop()

    def test_called_once_per_mutating_action_not_per_list(self) -> None:
        v = Counter()
        i = SyncInterpreter(machine("continue", v)).start()
        i.send("TWO")  # bump, bump, noop
        self.assertEqual(v.calls, 2)
        i.send("NOOP")
        i.send("GO")
        self.assertEqual(v.calls, 2)
        i.stop()

    def test_validator_coercion_is_kept(self) -> None:
        def coerce(ctx: Any) -> None:
            ctx["n"] = str(ctx["n"])

        i = SyncInterpreter(machine("continue", coerce)).start()
        i.send("BUMP")
        self.assertEqual(i.context["n"], "1")
        i.stop()

    def test_raising_on_initial_entry_action_keeps_machine_running(
        self,
    ) -> None:
        # 📝 The initial context itself is NOT validated; an entry action
        # that mutates is, and its failure is an action error (contained).
        v = Counter(limit=-1)
        cfg = dict(CFG, entry="bump")
        m = create_machine(cfg, logic=logic(), context_validator=v)
        i = SyncInterpreter(m).start()
        self.assertEqual(i.status, "running")
        self.assertEqual(v.calls, 1)
        i.stop()
        v0 = Counter(limit=-1)
        SyncInterpreter(machine("continue", v0)).start().stop()
        self.assertEqual(v0.calls, 0)

    def test_spawned_child_uses_its_own_machine_validator(self) -> None:
        parent_v, kid_v = Counter(), Counter()
        kid = create_machine(
            KID,
            logic=MachineLogic(actions={"kbump": kbump}),
            context_validator=kid_v,
        )
        m = create_machine(
            CFG,
            logic=MachineLogic(
                actions={"bump": bump, "noop": noop}, services={"kid": kid}
            ),
            context_validator=parent_v,
        )
        i = SyncInterpreter(m).start()
        i.send("SPAWN")
        parent_calls = parent_v.calls
        child = next(iter(i._actors.values()))
        child.send("KB")
        self.assertEqual(kid_v.calls, 1)
        self.assertEqual(parent_v.calls, parent_calls)
        i.stop()

    def test_uncopyable_context_does_not_break_send(self) -> None:
        # 🐛 DEFECT (fixed): with a validator configured, a context holding
        # a lock made every action raise TypeError out of send().
        v = Counter()
        i = SyncInterpreter(machine("continue", v)).start()
        i.context["lock"] = threading.Lock()
        i.send("BUMP")
        self.assertEqual(i.context["n"], 1)
        self.assertEqual(v.calls, 1)
        i.stop()

    def test_receipt_with_uncopyable_context_sync(self) -> None:
        # 🐛 DEFECT (fixed): `send(wait=True)` raised TypeError.
        i = SyncInterpreter(machine()).start()
        i.context["lock"] = threading.Lock()
        r = i.send("BUMP", wait=True)
        self.assertTrue(r.changed)
        self.assertEqual(i.context["n"], 1)
        i.stop()

    def test_non_json_context_objects_reach_validator(self) -> None:
        seen: List[Any] = []
        i = SyncInterpreter(machine("continue", seen.append)).start()
        i.context["when"] = {1, 2}
        i.send("BUMP")
        self.assertEqual(seen[0]["when"], {1, 2})
        i.stop()

    def test_slow_validator_skipped_on_noop_actions_perf(self) -> None:
        v = Counter()
        i = SyncInterpreter(machine("continue", v)).start()
        for _ in range(10_000):
            i.send("NOOP")
        self.assertEqual(v.calls, 0)
        i.stop()


class TestValidatorAsync(unittest.IsolatedAsyncioTestCase):
    async def test_rollback_after_assign_and_uncopyable_async(self) -> None:
        v = Counter(limit=10)
        i = await Interpreter(machine("rollback", v)).start()
        r = await i.send("SET", wait=True)
        self.assertEqual(i.context["n"], 0)
        self.assertIsInstance(r.error, ValueError)
        await i.stop()
        v2 = Counter()
        j = await Interpreter(machine("continue", v2)).start()
        j.context["lock"] = threading.Lock()
        await j.send("BUMP", wait=True)
        self.assertEqual((j.context["n"], v2.calls), (1, 1))
        await j.stop()

    async def test_receipt_with_uncopyable_context_resolves_async(
        self,
    ) -> None:
        # 🐛 DEFECT (fixed): the receipt before-image deepcopy raised inside
        # the run loop -- the loop died, status flipped to "stopped" and
        # `send(wait=True)` never resolved (hung forever). No validator.
        i = await Interpreter(machine()).start()
        i.context["lock"] = threading.Lock()
        r = await asyncio.wait_for(i.send("BUMP", wait=True), 5)
        self.assertTrue(r.changed)
        self.assertIsNone(r.error)
        self.assertEqual(i.status, "running")
        await i.stop()


if __name__ == "__main__":
    unittest.main()
