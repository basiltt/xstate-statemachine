"""#267 battle (agent B): `from_interpreter`, `sendTo` routing to
invocation ids, child actors per invocation, forged completions, leaks."""

from __future__ import annotations

import asyncio
import threading
import time
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    PluginBase,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.actor_logic import from_callback, from_interpreter


class _Drops(PluginBase):
    def __init__(self) -> None:
        self.dropped: List[Any] = []

    def on_event_dropped(self, interp: Any, event: Any, reason: str) -> None:
        self.dropped.append((getattr(event, "type", event), reason))


def _routing_fixture() -> Any:
    got: Dict[str, List[str]] = {"a": [], "b": []}
    send_backs: Dict[str, Any] = {}
    cleanups = {"a": 0, "b": 0}

    def mk(name: str) -> Any:
        def setup(send_back: Any, receive: Any, ctx: Any, ev: Any) -> Any:
            send_backs[name] = send_back
            receive(lambda e: got[name].append(e.type))

            def cleanup() -> None:
                cleanups[name] += 1

            return cleanup

        return from_callback(setup)

    def to_a(evt: str, delay: Any = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"to": "a", "event": {"type": evt}}
        if delay is not None:
            params["delay"] = delay
        return {"actions": {"type": "sendTo", "params": params}}

    cfg = {
        "id": "p",
        "type": "parallel",
        "states": {
            "r1": {
                "initial": "on",
                "states": {
                    "on": {
                        "invoke": {"src": "cb", "id": "a"},
                        "on": {"OFF": "off"},
                    },
                    "off": {"on": {"ON": "on"}},
                },
            },
            "r2": {
                "initial": "on",
                "states": {"on": {"invoke": {"src": "cb", "id": "b"}}},
            },
        },
        "on": {"PING": to_a("HI"), "LATE": to_a("LATE", 50)},
    }
    cfg["states"]["r2"]["states"]["on"]["invoke"]["src"] = "cb2"
    logic = MachineLogic(services={"cb": mk("a"), "cb2": mk("b")})
    return create_machine(cfg, logic=logic), got, send_backs, cleanups


class TestSendToInvocationSync(unittest.TestCase):
    def test_reaches_only_target_and_reports_after_exit(self) -> None:
        machine, got, _, cleanups = _routing_fixture()
        drops = _Drops()
        i = SyncInterpreter(machine).use(drops).start()
        i.send("PING")
        self.assertEqual(got, {"a": ["HI"], "b": []})
        i.send("OFF")
        self.assertEqual(cleanups["a"], 1)
        i.send("PING")
        self.assertEqual(got["a"], ["HI"])
        self.assertIn(("HI", "unresolved_target"), drops.dropped)
        i.send("ON")  # re-entry: fresh setup, receive works again
        i.send("PING")
        self.assertEqual(got["a"], ["HI", "HI"])
        i.stop()
        self.assertEqual(cleanups, {"a": 2, "b": 1})

    def test_forged_engine_completions_via_send_back_ignored(self) -> None:
        machine, _, send_backs, _ = _routing_fixture()
        i = SyncInterpreter(machine).start()
        for forged in ("done.invoke.b", "error.platform.b", "invoke.zzz"):
            send_backs["b"](forged, data=1)
            i.tick()
        self.assertEqual(i.current_state_ids, {"p.r1.on", "p.r2.on"})
        i.stop()


class TestSendToInvocationAsync(unittest.IsolatedAsyncioTestCase):
    async def test_delayed_sendto_after_exit_is_dropped_not_delivered(
        self,
    ) -> None:
        # 📝 #267 battle BUG: the delayed event used to reach the torn-down
        #    logic's `receive` handler after its cleanup had run.
        machine, got, _, cleanups = _routing_fixture()
        drops = _Drops()
        i = await Interpreter(machine).use(drops).start()
        await i.send("LATE")
        await i.send("OFF")
        await asyncio.sleep(0.2)
        self.assertEqual(cleanups["a"], 1)
        self.assertEqual(got["a"], [])
        self.assertIn(("LATE", "unresolved_target"), drops.dropped)
        await i.stop()

    async def test_delayed_sendto_after_reentry_reaches_new_invocation(
        self,
    ) -> None:
        # 📝 reviewer LOW-1: the delay captured the OLD handle; after OFF/ON
        #    a live invocation with the same id exists -- it is the
        #    addressee, not a drop.
        machine, got, _, cleanups = _routing_fixture()
        drops = _Drops()
        i = await Interpreter(machine).use(drops).start()
        await i.send("LATE")
        await i.send("OFF")
        await i.send("ON", wait=True)
        await asyncio.sleep(0.2)
        self.assertEqual(cleanups["a"], 1)
        self.assertEqual(got["a"], ["LATE"])
        self.assertEqual(drops.dropped, [])
        await i.stop()

    async def test_between_steps_drop_does_not_taint_next_receipt(
        self,
    ) -> None:
        # 📝 reviewer LOW-2: the timer fires between steps; its drop must
        #    not surface as the NEXT unrelated event's soft error.
        machine, _, _, _ = _routing_fixture()
        drops = _Drops()
        i = await Interpreter(machine).use(drops).start()
        await i.send("LATE")
        await i.send("OFF", wait=True)
        await asyncio.sleep(0.2)
        self.assertIn(("LATE", "unresolved_target"), drops.dropped)
        r = await i.send("ON", wait=True)
        self.assertIsNotNone(r)
        self.assertIsNone(r.error)
        self.assertTrue(i.last_transition_ok)
        await i.stop()

    async def test_forged_done_ignored(self) -> None:
        machine, _, send_backs, _ = _routing_fixture()
        i = await Interpreter(machine).start()
        await asyncio.sleep(0.02)
        send_backs["b"]("done.invoke.b", data=1)
        send_backs["b"]("error.platform.b", data=1)
        await asyncio.sleep(0.05)
        self.assertEqual(i.current_state_ids, {"p.r1.on", "p.r2.on"})
        await i.stop()


CHILD = {
    "id": "c",
    "initial": "x",
    "context": {"n": 0},
    "states": {"x": {"on": {"GO": "y"}}, "y": {"type": "final"}},
}


class TestFromInterpreter(unittest.TestCase):
    def test_instance_not_adopted_and_type_errors(self) -> None:
        c = SyncInterpreter(create_machine(CHILD)).start()
        self.assertIs(from_interpreter(c), c.machine)
        c.stop()
        self.assertIs(from_interpreter(c), c.machine)  # stopped: fine
        with self.assertRaises(TypeError):
            from_interpreter(object())

    def test_invoked_child_starts_fresh_and_original_untouched(self) -> None:
        donor = SyncInterpreter(create_machine(CHILD)).start()
        donor.context["n"] = 41
        parent_cfg = {
            "id": "par",
            "initial": "run",
            "states": {
                "run": {
                    "invoke": {"src": "kid", "id": "kid"},
                    "on": {
                        "FWD": {
                            "actions": {
                                "type": "sendTo",
                                "params": {"to": "kid", "event": "GO"},
                            }
                        }
                    },
                }
            },
        }
        p = SyncInterpreter(
            create_machine(
                parent_cfg,
                logic=MachineLogic(services={"kid": from_interpreter(donor)}),
            )
        ).start()
        kids = list(p._actors.values())
        self.assertEqual(len(kids), 1)
        self.assertIsNot(kids[0], donor)
        self.assertEqual(kids[0].context["n"], 0)
        p.stop()
        self.assertEqual(donor.status, "running")  # orphaned donor lives
        donor.stop()

    def test_thousand_handovers_do_not_leak_threads(self) -> None:
        base = threading.active_count()
        for _ in range(1000):
            c = SyncInterpreter(create_machine(CHILD)).start()
            from_interpreter(c)
            c.stop()
        self.assertLessEqual(threading.active_count(), base + 2)


class TestChildActorLifecycle(unittest.TestCase):
    def _parent(self) -> Any:
        cfg = {
            "id": "par",
            "initial": "run",
            "context": {"done": 0},
            "states": {
                "run": {
                    "invoke": {
                        "src": "kid",
                        "id": "kid",
                        "onDone": {"target": "ok", "actions": "count"},
                    },
                    "on": {
                        "FWD": {
                            "actions": {
                                "type": "sendTo",
                                "params": {"to": "kid", "event": "GO"},
                            }
                        }
                    },
                },
                "ok": {"on": {"AGAIN": "run"}},
            },
        }
        logic = MachineLogic(
            services={"kid": create_machine(CHILD)},
            actions={
                "count": lambda i, c, e, a: c.__setitem__(
                    "done", c["done"] + 1
                )
            },
        )
        return create_machine(cfg, logic=logic)

    def test_thousand_child_final_ondone_exactly_once_flat(self) -> None:
        p = SyncInterpreter(self._parent()).start()
        base = threading.active_count()
        for n in range(1, 1001):
            p.send("FWD")
            end = time.monotonic() + 5
            while p.context["done"] < n and time.monotonic() < end:
                p.tick()  # sync: child completion hops via the mailbox
                time.sleep(0.001)
            self.assertEqual(p.context["done"], n)
            p.send("AGAIN")
        self.assertLessEqual(threading.active_count(), base + 2)
        self.assertEqual(len(p._actors), 1)
        p.stop()
        self.assertEqual(len(p._actors), 0)


class TestStopBound(unittest.IsolatedAsyncioTestCase):
    async def test_stop_with_fifty_callback_invocations_is_fast(self) -> None:
        cleaned: List[int] = []

        def setup(send_back: Any, receive: Any, ctx: Any, ev: Any) -> Any:
            return lambda: cleaned.append(1)

        regions = {
            f"r{k}": {
                "initial": "s",
                "states": {"s": {"invoke": {"src": "cb", "id": f"cb{k}"}}},
            }
            for k in range(50)
        }
        m = create_machine(
            {"id": "big", "type": "parallel", "states": regions},
            logic=MachineLogic(services={"cb": from_callback(setup)}),
        )
        i = await Interpreter(m).start()
        t0 = time.monotonic()
        await i.stop()
        self.assertLess(time.monotonic() - t0, 2.0)
        self.assertEqual(len(cleaned), 50)


if __name__ == "__main__":
    unittest.main()
