# tests/test_core_prereqs_305_part2.py
# -----------------------------------------------------------------------------
# 🧪 #305 A0b core prerequisites, part 2: global plugin registry,
#    `context_validator` seam, `__xstate_event__` adapter,
#    `SyncInterpreter.send_threadsafe`.
# -----------------------------------------------------------------------------
"""Both engines wherever an engine is involved."""

from __future__ import annotations

import asyncio
import threading
import unittest
from typing import Any, List

from src.xstate_statemachine import (
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
    InvalidConfigError,
    InvalidEventError,
    UnknownEventError,
)
from src.xstate_statemachine.plugins import clear_global_plugins

CFG = {
    "id": "m",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {
            "on": {
                "GO": "b",
                "BUMP": {"actions": "bump"},
                "SPAWN": {"actions": "spawn_kid"},
            }
        },
        "b": {"on": {"BACK": "a"}},
    },
}
KID = {"id": "kid", "initial": "x", "states": {"x": {}}}


def bump(i: Any, c: Any, e: Any, a: Any) -> None:
    c["n"] = c.get("n", 0) + e.payload.get("by", 1)


def logic() -> MachineLogic:
    return MachineLogic(
        actions={"bump": bump},
        services={"kid": create_machine(KID)},
    )


class Recorder(PluginBase):
    def __init__(self) -> None:
        self.started: List[str] = []

    def on_interpreter_start(self, interpreter: Any) -> None:
        self.started.append(interpreter.id)


# -----------------------------------------------------------------------------
# 🌐 Global registry
# -----------------------------------------------------------------------------
class TestGlobalRegistry(unittest.TestCase):
    def tearDown(self) -> None:
        clear_global_plugins()

    def test_empty_by_default_and_opt_in(self) -> None:
        self.assertEqual(global_plugins(), [])
        p = Recorder()
        register_global(p)
        register_global(p)  # idempotent
        self.assertEqual(global_plugins(), [p])
        self.assertTrue(unregister_global(p))
        self.assertFalse(unregister_global(p))
        self.assertEqual(global_plugins(), [])

    def test_attached_to_new_not_existing_sync(self) -> None:
        before = SyncInterpreter(create_machine(CFG, logic=logic()))
        p = Recorder()
        register_global(p)
        after = SyncInterpreter(create_machine(CFG, logic=logic()))
        before.start()
        after.start()
        self.assertEqual(p.started, ["m"])  # only the one built after
        unregister_global(p)
        later = SyncInterpreter(create_machine(CFG, logic=logic())).start()
        self.assertEqual(p.started, ["m"])
        for i in (before, after, later):
            i.stop()

    def test_attached_to_async_and_from_snapshot(self) -> None:
        p = Recorder()
        register_global(p)

        async def go() -> None:
            i = await Interpreter(create_machine(CFG, logic=logic())).start()
            blob = i.get_snapshot()
            await i.stop()
            r = await Interpreter.from_snapshot(
                blob, create_machine(CFG, logic=logic())
            ).start()
            await r.stop()

        asyncio.run(go())
        self.assertEqual(p.started, ["m", "m"])

    def test_attached_to_spawned_children_both_engines(self) -> None:
        p = Recorder()
        register_global(p)
        s = SyncInterpreter(create_machine(CFG, logic=logic())).start()
        s.send("SPAWN")
        s.stop()
        self.assertEqual(p.started[0], "m")
        self.assertTrue(any(x.startswith("m:kid") for x in p.started[1:]))

        p.started.clear()

        async def go() -> None:
            i = await Interpreter(create_machine(CFG, logic=logic())).start()
            await i.send("SPAWN", wait=True)
            await i.stop()

        asyncio.run(go())
        self.assertEqual(p.started[0], "m")
        self.assertTrue(any(x.startswith("m:kid") for x in p.started[1:]))

    def test_hundred_thread_registration_is_safe(self) -> None:
        plugins = [Recorder() for _ in range(100)]
        barrier = threading.Barrier(100)

        def worker(pl: Recorder) -> None:
            barrier.wait()
            register_global(pl)
            register_global(pl)

        ts = [threading.Thread(target=worker, args=(pl,)) for pl in plugins]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        got = global_plugins()
        self.assertEqual(len(got), 100)
        self.assertEqual({id(p) for p in got}, {id(p) for p in plugins})


# -----------------------------------------------------------------------------
# 🧪 context_validator
# -----------------------------------------------------------------------------
class TestContextValidator(unittest.TestCase):
    def _machine(self, policy: str, calls: List[Any]):
        def validate(ctx: Any) -> None:
            calls.append(dict(ctx))
            if ctx.get("n", 0) > 2:
                raise ValueError(f"n too big: {ctx['n']}")

        cfg = dict(CFG, actionErrorPolicy=policy)
        return create_machine(cfg, logic=logic(), context_validator=validate)

    def test_rejects_non_callable(self) -> None:
        with self.assertRaises(InvalidConfigError):
            create_machine(
                CFG, logic=logic(), context_validator="nope"  # type: ignore
            )

    def test_stored_on_machine(self) -> None:
        f = lambda c: None  # noqa: E731
        self.assertIs(
            create_machine(
                CFG, logic=logic(), context_validator=f
            ).context_validator,
            f,
        )
        self.assertIsNone(create_machine(CFG, logic=logic()).context_validator)

    def test_not_called_when_context_unchanged_sync(self) -> None:
        calls: List[Any] = []
        i = SyncInterpreter(self._machine("continue", calls)).start()
        i.send("GO")
        i.send("BACK")  # transitions with no actions: no context change
        self.assertEqual(calls, [])
        i.send("BUMP")
        self.assertEqual(len(calls), 1)
        i.stop()

    def test_rollback_restores_context_sync(self) -> None:
        calls: List[Any] = []
        i = SyncInterpreter(self._machine("rollback", calls)).start()
        i.send("BUMP", by=2)  # n=2 ok
        r = i.send("BUMP", by=5, wait=True)  # n=7 -> validator raises
        self.assertEqual(i.context["n"], 2)  # rolled back
        self.assertIsInstance(r.error, ValueError)
        self.assertIn("n too big", str(r.error))
        i.stop()

    def test_continue_policy_keeps_context_but_reports_sync(self) -> None:
        calls: List[Any] = []
        i = SyncInterpreter(self._machine("continue", calls)).start()
        r = i.send("BUMP", by=5, wait=True)
        self.assertEqual(i.context["n"], 5)
        self.assertIsInstance(r.error, ValueError)
        i.stop()

    def test_rollback_and_counter_async(self) -> None:
        calls: List[Any] = []

        async def go() -> Any:
            i = await Interpreter(self._machine("rollback", calls)).start()
            await i.send("GO", wait=True)
            self.assertEqual(calls, [])
            await i.send("BACK", wait=True)
            await i.send("BUMP", by=2, wait=True)
            r = await i.send("BUMP", by=5, wait=True)
            ctx = dict(i.context)
            await i.stop()
            return r, ctx

        r, ctx = asyncio.run(go())
        self.assertEqual(ctx["n"], 2)
        self.assertIsInstance(r.error, ValueError)
        self.assertEqual(len(calls), 2)

    def test_on_action_error_hook_fires_for_validator(self) -> None:
        seen: List[Any] = []

        class P(PluginBase):
            def on_action_error(self, i, action_def, exc):  # noqa
                seen.append((action_def.type, type(exc).__name__))

        calls: List[Any] = []
        i = SyncInterpreter(self._machine("continue", calls)).use(P()).start()
        i.send("BUMP", by=9)
        self.assertEqual(seen, [("bump", "ValueError")])
        i.stop()


# -----------------------------------------------------------------------------
# 🔌 __xstate_event__ adapter
# -----------------------------------------------------------------------------
class Order:
    def __init__(self, oid: int) -> None:
        self.oid = oid

    def __xstate_event__(self) -> dict:
        return {"type": "BUMP", "by": self.oid}


class Named:
    def __xstate_event__(self) -> str:
        return "GO"


class Bad:
    def __xstate_event__(self) -> int:
        return 42


class TestXStateEventAdapter(unittest.TestCase):
    def test_dict_adapter_sync(self) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=logic())).start()
        i.send(Order(3))
        self.assertEqual(i.context["n"], 3)
        # keyword payload merges over the adapter's dict
        i.send(Order(3), by=10)
        self.assertEqual(i.context["n"], 13)
        i.stop()

    def test_str_adapter_and_send_events_sync(self) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=logic())).start()
        i.send(Named())
        self.assertIn("m.b", i.current_state_ids)
        i.send_events(["BACK", Order(1)])
        self.assertIn("m.a", i.current_state_ids)
        self.assertEqual(i.context["n"], 1)
        i.stop()

    def test_adapter_async_send_and_threadsafe(self) -> None:
        async def go() -> Any:
            i = await Interpreter(create_machine(CFG, logic=logic())).start()
            await i.send(Order(4), wait=True)
            fut = i.send_threadsafe(Order(1))
            await asyncio.wrap_future(fut) if hasattr(fut, "result") else fut
            await asyncio.sleep(0.01)
            ctx = dict(i.context)
            await i.stop()
            return ctx

        self.assertEqual(asyncio.run(go())["n"], 5)

    def test_bad_adapter_return_is_invalid_event(self) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=logic())).start()
        with self.assertRaises(InvalidEventError):
            i.send(Bad())
        i.stop()

    def test_native_events_are_not_adapted(self) -> None:
        # An Event subclass with __xstate_event__ is still passed through.
        from src.xstate_statemachine import Event

        class Weird(Event):
            def __xstate_event__(self) -> str:  # never called
                raise AssertionError("must not adapt a native Event")

        i = SyncInterpreter(create_machine(CFG, logic=logic())).start()
        i.send(Weird(type="GO"))
        self.assertIn("m.b", i.current_state_ids)
        i.stop()


# -----------------------------------------------------------------------------
# 🧵 SyncInterpreter.send_threadsafe
# -----------------------------------------------------------------------------
class TestSyncSendThreadsafe(unittest.TestCase):
    def test_eight_threads_thousand_events_fifo_none_lost(self) -> None:
        seen: List[tuple] = []

        def record(i: Any, c: Any, e: Any, a: Any) -> None:
            seen.append((e.payload["t"], e.payload["k"]))

        cfg = {
            "id": "q",
            "initial": "s",
            "states": {"s": {"on": {"E": {"actions": "record"}}}},
        }
        m = create_machine(cfg, logic=MachineLogic(actions={"record": record}))
        i = SyncInterpreter(m).start()

        def worker(t: int) -> None:
            for k in range(1000):
                i.send_threadsafe("E", t=t, k=k)

        ts = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
        for th in ts:
            th.start()
        for th in ts:
            th.join()
        self.assertEqual(seen, [])  # nothing ran on producer threads
        i.tick()  # owner drains
        self.assertEqual(len(seen), 8000)
        for t in range(8):
            ks = [k for (tt, k) in seen if tt == t]
            self.assertEqual(ks, list(range(1000)), f"thread {t} order")
        i.stop()

    def test_drained_before_callers_own_event(self) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=logic())).start()
        i.send_threadsafe("BUMP", by=1)
        i.send_threadsafe(Order(2))
        r = i.send("GO", wait=True)
        self.assertEqual(i.context["n"], 3)
        self.assertIn("m.b", r.state_ids)
        self.assertTrue(r.changed)
        i.stop()

    def test_admission_refusal_surfaces_on_owner_as_drop(self) -> None:
        drops: List[tuple] = []

        class P(PluginBase):
            def on_event_dropped(self, i, e, reason):  # noqa
                drops.append((e.type, reason))

        cfg = dict(CFG, strict=True)
        i = SyncInterpreter(create_machine(cfg, logic=logic())).use(P())
        i.start()
        i.send_threadsafe("NOT_DECLARED")
        i.tick()  # must not raise on the owner
        self.assertEqual(drops, [("NOT_DECLARED", "invalid")])
        self.assertIsInstance(i.last_error, UnknownEventError)
        i.stop()

    def test_malformed_fails_on_sender(self) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=logic())).start()
        with self.assertRaises(InvalidEventError):
            i.send_threadsafe({"no": "type"})
        i.stop()

    def test_not_drained_inside_a_running_step(self) -> None:
        order: List[str] = []

        def inner(i: Any, c: Any, e: Any, a: Any) -> None:
            order.append("inner-start")
            i.send_threadsafe("MARK")  # from "another thread", conceptually
            i.send("NOOP")  # re-entrant send must not drain the mailbox
            order.append("inner-end")

        def mark(i: Any, c: Any, e: Any, a: Any) -> None:
            order.append("mark")

        cfg = {
            "id": "r",
            "initial": "s",
            "states": {
                "s": {
                    "on": {
                        "GO": {"actions": "inner"},
                        "MARK": {"actions": "mark"},
                        "NOOP": {"actions": []},
                    }
                }
            },
        }
        m = create_machine(
            cfg, logic=MachineLogic(actions={"inner": inner, "mark": mark})
        )
        i = SyncInterpreter(m).start()
        i.send("GO")
        # `MARK` was mailboxed mid-step and delivered only at the owner's
        # next top-level call, after `inner` finished.
        self.assertEqual(order, ["inner-start", "inner-end"])
        i.tick()
        self.assertEqual(order, ["inner-start", "inner-end", "mark"])
        i.stop()


if __name__ == "__main__":
    unittest.main()
