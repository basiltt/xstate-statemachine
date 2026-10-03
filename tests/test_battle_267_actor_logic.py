"""#267 battle (agent A): from_callback / from_async_iterator /
from_iterator and the engine side -- ordering under load, stale producers,
cleanup exactly once, the module-global cleanup registry across loops,
blocked iterators, sendTo -> receive routing, leaks, Stately corpus."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.actor_logic import (
    _PENDING_CLEANUPS,
    drain_pending_cleanups,
    from_callback,
)
from src.xstate_statemachine.exceptions import InvalidEventError

CFG: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "context": {"seen": [], "n": 0},
    "states": {
        "a": {
            "invoke": {"src": "cb", "id": "cb"},
            "on": {
                "PING": {"actions": "rec"},
                "GO": "b",
                "AGAIN": {"target": "a", "reenter": True},
                "TELL": {
                    "actions": {
                        "type": "sendTo",
                        "params": {"to": "cb", "event": {"type": "HI"}},
                    }
                },
            },
        },
        "b": {
            "on": {
                "PING": {"actions": "rec"},
                "BACK": "a",
                "TELL": {
                    "actions": {
                        "type": "sendTo",
                        "params": {"to": "cb", "event": {"type": "HI"}},
                    }
                },
            }
        },
    },
}


def _rec(i: Any, c: Any, e: Any, a: Any) -> None:
    c["seen"].append(e.payload.get("v"))


def logic(setup: Any) -> MachineLogic:
    return MachineLogic(
        actions={"rec": _rec}, services={"cb": from_callback(setup)}
    )


def pump(i: Any, until: Any, timeout: float = 10.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        i.tick()
        if until():
            return
        time.sleep(0.002)
    raise AssertionError("timed out")


async def apump(until: Any, timeout: float = 10.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if until():
            return
        await asyncio.sleep(0.005)
    raise AssertionError("timed out")


class Counting:
    """A setup factory that counts setups / cleanups and keeps send_back."""

    def __init__(self) -> None:
        self.setups = 0
        self.cleanups = 0
        self.sb: List[Any] = []
        self.received: List[Any] = []

    def __call__(self, send_back: Any, receive: Any, c: Any, e: Any) -> Any:
        self.setups += 1
        self.sb.append(send_back)
        receive(self.received.append)

        def cleanup() -> None:
            self.cleanups += 1

        return cleanup


# -----------------------------------------------------------------------------
# 1. delivery: order, producers, stale / stopped producers
# -----------------------------------------------------------------------------
class TestDeliverySync(unittest.TestCase):
    def test_8_producers_x_1000_per_producer_order(self) -> None:
        def setup(send_back: Any, receive: Any, c: Any, e: Any) -> Any:
            def prod(p: int) -> None:
                for k in range(1000):
                    send_back("PING", v=(p, k))

            for p in range(8):
                threading.Thread(target=prod, args=(p,), daemon=True).start()
            return None

        i = SyncInterpreter(create_machine(CFG, logic=logic(setup))).start()
        pump(i, lambda: len(i.context["seen"]) == 8000)
        for p in range(8):
            ks = [k for (q, k) in i.context["seen"] if q == p]
            self.assertEqual(ks, list(range(1000)))
        i.stop()

    def test_send_back_before_setup_returns_is_delivered(self) -> None:
        def setup(send_back: Any, receive: Any, c: Any, e: Any) -> Any:
            send_back("PING", v="early")
            return None

        i = SyncInterpreter(create_machine(CFG, logic=logic(setup))).start()
        pump(i, lambda: i.context["seen"] == ["early"])
        i.stop()

    def test_send_back_after_exit_never_lands_on_next_state(self) -> None:
        cnt = Counting()
        i = SyncInterpreter(create_machine(CFG, logic=logic(cnt))).start()
        i.send("GO")
        cnt.sb[0]("PING", v="stale")  # regression: landed in `b`
        i.tick()
        self.assertEqual(i.context["seen"], [])
        self.assertEqual(cnt.cleanups, 1)
        i.stop()

    def test_send_back_after_stop_producer_thread_survives(self) -> None:
        cnt = Counting()
        i = SyncInterpreter(create_machine(CFG, logic=logic(cnt))).start()
        i.stop()
        errs: List[BaseException] = []

        def prod() -> None:
            try:
                for _ in range(100):
                    cnt.sb[0]("PING", v=1)
            except BaseException as exc:  # pragma: no cover
                errs.append(exc)

        t = threading.Thread(target=prod)
        t.start()
        t.join(5)
        self.assertEqual(errs, [])
        self.assertEqual(cnt.cleanups, 1)

    def test_send_back_reserved_or_bad_type_raises_in_producer(self) -> None:
        cnt = Counting()
        i = SyncInterpreter(create_machine(CFG, logic=logic(cnt))).start()
        with self.assertRaises(InvalidEventError):
            cnt.sb[0](123)
        i.stop()

    def test_send_back_while_owner_mid_send_lands_next_step(self) -> None:
        cnt = Counting()
        gate = threading.Event()
        done = threading.Event()

        def rec(i: Any, c: Any, e: Any, a: Any) -> None:
            if e.payload.get("v") == "owner":
                t = threading.Thread(
                    target=lambda: (cnt.sb[0]("PING", v="x"), done.set())
                )
                t.start()
                done.wait(5)
                gate.set()
            c["seen"].append(e.payload.get("v"))

        lg = MachineLogic(
            actions={"rec": rec}, services={"cb": from_callback(cnt)}
        )
        i = SyncInterpreter(create_machine(CFG, logic=lg)).start()
        i.send("PING", v="owner")
        self.assertEqual(i.context["seen"], ["owner"])  # mailbox rule
        i.tick()
        self.assertEqual(i.context["seen"], ["owner", "x"])
        i.stop()


class TestDeliveryAsync(unittest.TestCase):
    def test_8_producers_and_stale_and_loop_task(self) -> None:
        cnt = Counting()

        async def main() -> None:
            i = await Interpreter(
                create_machine(CFG, logic=logic(cnt))
            ).start()
            await apump(lambda: cnt.setups == 1)
            sb = cnt.sb[0]

            def prod(p: int) -> None:
                for k in range(1000):
                    sb("PING", v=(p, k))

            ts = [threading.Thread(target=prod, args=(p,)) for p in range(8)]
            for t in ts:
                t.start()

            async def from_task() -> None:
                sb("PING", v=("task", 0))

            await asyncio.create_task(from_task())
            sb("PING", v=("loop", 0))  # loop thread itself
            for t in ts:
                t.join(10)
            await apump(lambda: len(i.context["seen"]) == 8002)
            for p in range(8):
                ks = [k for (q, k) in i.context["seen"] if q == p]
                self.assertEqual(ks, list(range(1000)))
            await i.send("GO", wait=True)
            sb("PING", v="stale")
            await asyncio.sleep(0.05)
            self.assertNotIn("stale", i.context["seen"])
            await i.stop()
            sb("PING", v="after-stop")  # no exception

        asyncio.run(main())
        self.assertEqual(cnt.cleanups, 1)

    def test_send_back_after_loop_closed_is_noop(self) -> None:
        cnt = Counting()
        box: Dict[str, Any] = {}

        async def main() -> None:
            i = await Interpreter(
                create_machine(CFG, logic=logic(cnt))
            ).start()
            await apump(lambda: cnt.setups == 1)
            box["i"] = i

        loop = asyncio.new_event_loop()
        loop.run_until_complete(main())
        loop.close()
        # Interpreter still says "running" but its loop is gone: the TOCTOU
        # path. Must not raise into the producer.
        box["i"]._loop = loop
        cnt.sb[0]("PING", v=1)  # status running but loop closed
        box["i"].status = "stopped"
        cnt.sb[0]("PING", v=1)


# -----------------------------------------------------------------------------
# 3. cleanup exactly once
# -----------------------------------------------------------------------------
class TestCleanup(unittest.TestCase):
    def test_reenter_parallel_and_stop_sync(self) -> None:
        cnt = Counting()
        i = SyncInterpreter(create_machine(CFG, logic=logic(cnt))).start()
        i.send("AGAIN")
        self.assertEqual((cnt.setups, cnt.cleanups), (2, 1))
        i.send("GO")
        self.assertEqual(cnt.cleanups, 2)
        i.send("BACK")
        i.stop()
        i.stop()
        self.assertEqual((cnt.setups, cnt.cleanups), (3, 3))

    def test_parallel_sibling_exit_does_not_clean_us(self) -> None:
        cnt = Counting()
        cfg = {
            "id": "p",
            "type": "parallel",
            "states": {
                "r1": {
                    "initial": "x",
                    "states": {"x": {"invoke": {"src": "cb", "id": "cb"}}},
                },
                "r2": {
                    "initial": "y",
                    "states": {"y": {"on": {"N": "z"}}, "z": {}},
                },
            },
        }
        i = SyncInterpreter(create_machine(cfg, logic=logic(cnt))).start()
        i.send("N")
        self.assertEqual(cnt.cleanups, 0)
        i.stop()
        self.assertEqual(cnt.cleanups, 1)

    def test_raising_cleanup_logged_machine_fine(self) -> None:
        def setup(*a: Any) -> Any:
            def bad() -> None:
                raise ValueError("boom")

            return bad

        i = SyncInterpreter(create_machine(CFG, logic=logic(setup))).start()
        with self.assertLogs(level=logging.ERROR):
            i.send("GO")
        i.send("BACK")
        self.assertIn("m.a", i.current_state_ids)
        i.stop()

    def test_async_cleanup_on_sync_engine_inside_running_loop(self) -> None:
        ran: List[str] = []

        def setup(*a: Any) -> Any:
            async def ac() -> None:
                ran.append("x")

            return ac

        async def host() -> None:
            # sync engine driven from a coroutine (Starlette executor shape)
            i = SyncInterpreter(create_machine(CFG, logic=logic(setup)))
            i.start()
            i.send("GO")  # cleanup scheduled on THIS running loop
            await drain_pending_cleanups()
            i.stop()

        asyncio.run(host())
        self.assertEqual(ran, ["x"])

    def test_stop_racing_send_back(self) -> None:
        for _ in range(50):
            cnt = Counting()
            i = SyncInterpreter(create_machine(CFG, logic=logic(cnt))).start()
            errs: List[BaseException] = []

            def prod() -> None:
                try:
                    for _ in range(200):
                        cnt.sb[0]("PING", v=1)
                except BaseException as exc:  # pragma: no cover
                    errs.append(exc)

            t = threading.Thread(target=prod)
            t.start()
            i.stop()
            t.join(5)
            self.assertEqual(errs, [])
            self.assertEqual(cnt.cleanups, 1)


class TestPendingCleanupsAcrossLoops(unittest.TestCase):
    def test_foreign_closed_loop_task_does_not_break_drain(self) -> None:
        async def slow() -> None:
            await asyncio.sleep(30)

        async def leave_one() -> None:
            i = await Interpreter(
                create_machine(CFG, logic=logic(lambda *a: slow))
            ).start()
            await apump(lambda: bool(i._running_logic))
            await i.send("GO", wait=True)  # async cleanup scheduled
            # loop torn down without stop(): the task is orphaned

        loop = asyncio.new_event_loop()
        loop.run_until_complete(leave_one())
        loop.close()
        self.assertTrue(_PENDING_CLEANUPS)

        async def other() -> None:
            await asyncio.wait_for(drain_pending_cleanups(), 2)

        asyncio.run(other())  # regression: ValueError("different loop")
        self.assertFalse(
            [t for t in _PENDING_CLEANUPS if t.get_loop() is loop]
        )


# -----------------------------------------------------------------------------
# 4. receive()
# -----------------------------------------------------------------------------
class TestReceive(unittest.TestCase):
    def test_send_to_both_engines_two_handlers_one_raises(self) -> None:
        got: List[str] = []

        def setup(send_back: Any, receive: Any, c: Any, e: Any) -> Any:
            def bad(ev: Any) -> None:
                raise RuntimeError("h")

            receive(bad)
            receive(lambda ev: got.append(ev.type))
            return None

        i = SyncInterpreter(create_machine(CFG, logic=logic(setup))).start()
        with self.assertLogs(level=logging.ERROR):
            i.send("TELL")
        self.assertEqual(got, ["HI"])
        i.send("GO")
        i.send("TELL")  # exited: no handler call
        self.assertEqual(got, ["HI"])
        i.stop()

        async def main() -> None:
            a = await Interpreter(
                create_machine(CFG, logic=logic(setup))
            ).start()
            await apump(lambda: bool(a._running_logic))
            await a.send("TELL", wait=True)
            await a.stop()

        asyncio.run(main())
        self.assertEqual(got, ["HI", "HI"])

    def test_secret_payload_not_logged_by_receive(self) -> None:
        def setup(send_back: Any, receive: Any, c: Any, e: Any) -> Any:
            def bad(ev: Any) -> None:
                raise RuntimeError("no")

            receive(bad)
            return None

        cfg = json.loads(json.dumps(CFG))
        cfg["states"]["a"]["on"]["TELL"]["actions"]["params"]["event"] = {
            "type": "HI",
            "pw": "hunter2",
        }
        i = SyncInterpreter(create_machine(cfg, logic=logic(setup))).start()
        with self.assertLogs(level=logging.DEBUG) as cm:
            i.send("TELL")
        self.assertNotIn("hunter2", "\n".join(cm.output))
        i.stop()

    def test_same_src_two_regions_routes_by_id(self) -> None:
        got: Dict[str, List[str]] = {"one": [], "two": []}

        def setup(send_back: Any, receive: Any, c: Any, e: Any) -> Any:
            key = e.type.split(".", 1)[1]
            receive(lambda ev: got[key].append(ev.type))
            return None

        def to(target: str) -> Dict[str, Any]:
            return {
                "actions": {
                    "type": "sendTo",
                    "params": {"to": target, "event": {"type": "X"}},
                }
            }

        cfg = {
            "id": "p",
            "type": "parallel",
            "on": {"T1": to("one"), "T2": to("two")},
            "states": {
                "r1": {"invoke": {"src": "cb", "id": "one"}},
                "r2": {"invoke": {"src": "cb", "id": "two"}},
            },
        }
        i = SyncInterpreter(create_machine(cfg, logic=logic(setup))).start()
        i.send("T2")
        i.send("T2")
        i.send("T1")
        self.assertEqual(got, {"one": ["X"], "two": ["X", "X"]})
        i.stop()
