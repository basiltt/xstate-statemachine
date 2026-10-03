"""#267 battle (agent A): from_callback / from_async_iterator /
from_iterator and the engine side -- ordering under load, stale producers,
cleanup exactly once, the module-global cleanup registry across loops,
blocked iterators, sendTo -> receive routing, leaks, Stately corpus."""

from __future__ import annotations

import asyncio
import gc
import json
import logging
import random
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    PluginBase,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.actor_logic import (
    _PENDING_CLEANUPS,
    drain_pending_cleanups,
    from_async_iterator,
    from_callback,
    from_iterator,
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


# -----------------------------------------------------------------------------
# 5. async streams
# -----------------------------------------------------------------------------
SCFG = {
    "id": "s",
    "initial": "a",
    "context": {"items": [], "last": None, "err": None},
    "states": {
        "a": {
            "invoke": {
                "src": "st",
                "id": "st",
                "onDone": {"target": "done", "actions": "last"},
                "onError": {"target": "failed", "actions": "err"},
            },
            "on": {"STREAM": {"actions": "item"}, "GO": "b"},
        },
        "b": {},
        "done": {},
        "failed": {},
    },
}


def slogic(svc: Any, item: Any = None) -> MachineLogic:
    def _item(i: Any, c: Any, e: Any, a: Any) -> None:
        c["items"].append(e.payload["data"])

    return MachineLogic(
        actions={
            "item": item or _item,
            "last": lambda i, c, e, a: c.__setitem__("last", e.data),
            "err": lambda i, c, e, a: c.__setitem__("err", repr(e.error)),
        },
        services={"st": svc},
    )


class TestAsyncStreams(unittest.TestCase):
    def _run(self, svc: Any, until: Any, item: Any = None) -> Any:
        async def main() -> Any:
            i = await Interpreter(
                create_machine(SCFG, logic=slogic(svc, item))
            ).start()
            await apump(lambda: until(i))
            await i.stop()
            return i

        return asyncio.run(main())

    def test_10000_items_in_order_then_done(self) -> None:
        async def gen(i: Any, c: Any, e: Any) -> Any:
            for k in range(10_000):
                yield k

        t0 = time.perf_counter()
        i = self._run(
            from_async_iterator(gen), lambda i: "s.done" in i.current_state_ids
        )
        rate = 10_000 / (time.perf_counter() - t0)
        self.assertEqual(i.context["items"], list(range(10_000)))
        self.assertEqual(i.context["last"], 9_999)
        self.assertGreater(rate, 500)  # receipts cost, not quadratic

    def test_non_iterator_factory_is_on_error(self) -> None:
        i = self._run(
            from_async_iterator(lambda *a: 42),
            lambda i: "s.failed" in i.current_state_ids,
        )
        self.assertIn("TypeError", i.context["err"])

    def test_factory_raising_synchronously_is_on_error(self) -> None:
        def f(*a: Any) -> Any:
            raise KeyError("k")

        i = self._run(
            from_async_iterator(f), lambda i: "s.failed" in i.current_state_ids
        )
        self.assertIn("KeyError", i.context["err"])

    def test_consumer_action_raising_keeps_stream_going(self) -> None:
        async def gen(i: Any, c: Any, e: Any) -> Any:
            for k in range(1000):
                yield k

        def item(i: Any, c: Any, e: Any, a: Any) -> None:
            if e.payload["data"] == 500:
                raise ValueError("bad item")
            c["items"].append(e.payload["data"])

        i = self._run(
            from_async_iterator(gen),
            lambda i: "s.done" in i.current_state_ids,
            item,
        )
        self.assertEqual(len(i.context["items"]), 999)

    def test_exit_mid_stream_acloses(self) -> None:
        closed = threading.Event()

        async def gen(i: Any, c: Any, e: Any) -> Any:
            try:
                k = 0
                while True:
                    yield k
                    k += 1
                    await asyncio.sleep(0.001)
            finally:
                closed.set()

        async def main() -> None:
            i = await Interpreter(
                create_machine(SCFG, logic=slogic(from_async_iterator(gen)))
            ).start()
            await apump(lambda: len(i.context["items"]) > 3)
            await i.send("GO", wait=True)
            await apump(closed.is_set)
            await i.stop()

        asyncio.run(main())


# -----------------------------------------------------------------------------
# 6. from_iterator
# -----------------------------------------------------------------------------
class TestSyncIterator(unittest.TestCase):
    def test_blocked_iterator_cleanup_is_honest(self) -> None:
        blk = threading.Event()

        def it(*a: Any) -> Any:
            def g() -> Any:
                yield 1
                blk.wait(10)

            return g()

        i = SyncInterpreter(
            create_machine(SCFG, logic=slogic(from_iterator(it)))
        ).start()
        pump(i, lambda: i.context["items"] == [1])
        with self.assertLogs(level=logging.WARNING) as cm:
            i.send("GO")
        self.assertIn("blocked inside next()", "\n".join(cm.output))
        blk.set()
        i.stop()

    def test_1000_streams_thread_count_flat(self) -> None:
        def it(*a: Any) -> Any:
            return iter(range(3))

        base = threading.active_count()
        cfg = json.loads(json.dumps(SCFG))
        cfg["states"]["done"] = {"on": {"BACK": "a"}}
        i = SyncInterpreter(
            create_machine(cfg, logic=slogic(from_iterator(it)))
        ).start()
        for _ in range(1000):
            pump(i, lambda: "s.done" in i.current_state_ids)
            i.send("BACK")
        i.stop()
        time.sleep(0.2)
        self.assertLessEqual(threading.active_count(), base + 2)

    def test_completion_races_owner_mid_send(self) -> None:
        for _ in range(100):

            def it(*a: Any) -> Any:
                return iter([1, 2])

            i = SyncInterpreter(
                create_machine(SCFG, logic=slogic(from_iterator(it)))
            ).start()
            for _ in range(5):
                i.send("STREAM", data=0)
            pump(i, lambda: "s.done" in i.current_state_ids)
            self.assertEqual(i.context["last"], 2)
            i.stop()

    def test_on_async_engine(self) -> None:
        def it(*a: Any) -> Any:
            return iter("abc")

        async def main() -> None:
            i = await Interpreter(
                create_machine(SCFG, logic=slogic(from_iterator(it)))
            ).start()
            await apump(lambda: "s.done" in i.current_state_ids)
            self.assertEqual(i.context["items"], list("abc"))
            await i.stop()

        asyncio.run(main())


# -----------------------------------------------------------------------------
# 9. leaks
# -----------------------------------------------------------------------------
class TestLeaks(unittest.TestCase):
    def test_10000_enter_exit_sync_flat(self) -> None:
        import tracemalloc

        cnt = Counting()
        i = SyncInterpreter(create_machine(CFG, logic=logic(cnt))).start()
        base_threads = threading.active_count()
        tracemalloc.start()
        snap = 0
        for k in range(10_000):
            i.send("GO")
            i.send("BACK")
            cnt.sb.clear()
            cnt.received.clear()
            if k == 4_999:
                gc.collect()
                snap = tracemalloc.get_traced_memory()[0]
        gc.collect()
        grew = tracemalloc.get_traced_memory()[0] - snap
        tracemalloc.stop()
        i.stop()
        self.assertLess(grew, 64 * 1024)
        self.assertEqual(cnt.setups, cnt.cleanups)
        self.assertLessEqual(threading.active_count(), base_threads)
        self.assertEqual(i._running_logic, {})

    def test_async_enter_exit_tasks_flat(self) -> None:
        cnt = Counting()

        async def main() -> None:
            i = await Interpreter(
                create_machine(CFG, logic=logic(cnt))
            ).start()
            await apump(lambda: cnt.setups == 1)
            base = len(asyncio.all_tasks())
            for _ in range(2000):
                await i.send("GO", wait=True)
                await i.send("BACK", wait=True)
            await apump(lambda: cnt.setups == 2001)
            self.assertLessEqual(len(asyncio.all_tasks()), base + 2)
            await i.stop()

        asyncio.run(main())
        self.assertEqual(cnt.setups, cnt.cleanups)


# -----------------------------------------------------------------------------
# 10. Stately corpus
# -----------------------------------------------------------------------------
CORPUS = Path(__file__).parent / "tests_cli" / "stately_machines"


def _srcs(node: Any, out: set) -> None:
    if isinstance(node, dict):
        inv = node.get("invoke")
        for d in inv if isinstance(inv, list) else [inv] if inv else []:
            if isinstance(d, dict) and isinstance(d.get("src"), str):
                out.add(d["src"])
        for v in node.values():
            _srcs(v, out)
    elif isinstance(node, list):
        for v in node:
            _srcs(v, out)


def _events(node: Any, out: set) -> None:
    if isinstance(node, dict):
        on = node.get("on")
        if isinstance(on, dict):
            out.update(k for k in on if not k.startswith(("xstate", "done")))
        for v in node.values():
            _events(v, out)
    elif isinstance(node, list):
        for v in node:
            _events(v, out)


def _names(node: Any, out: set) -> None:
    """Every string that could name an action / guard."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("actions", "entry", "exit", "guard", "cond"):
                for x in v if isinstance(v, list) else [v]:
                    if isinstance(x, str):
                        out.add(x)
                    elif isinstance(x, dict) and isinstance(
                        x.get("type"), str
                    ):
                        out.add(x["type"])
            _names(v, out)
    elif isinstance(node, list):
        for v in node:
            _names(v, out)


class _Quiet(PluginBase):
    pass


class TestStreamEventShape(unittest.TestCase):
    """Coordinator defect: a stream item's ``e.data`` was the payload dict."""

    def test_issue_script_verbatim(self) -> None:
        async def chunks(i: Any, c: Any, e: Any) -> Any:
            for w in ["hel", "lo"]:
                yield w

        cfg = {
            "id": "s",
            "initial": "streaming",
            "context": {"buf": ""},
            "states": {
                "streaming": {
                    "invoke": {"src": "stream", "onDone": "done"},
                    "on": {"STREAM": {"actions": "append"}},
                },
                "done": {"type": "final"},
            },
        }
        lg = MachineLogic(
            actions={
                "append": lambda i, c, e, a: c.__setitem__(
                    "buf", c["buf"] + e.data
                )
            },
            services={"stream": from_async_iterator(chunks)},
        )

        async def main() -> None:
            from src.xstate_statemachine import to_promise

            i = await Interpreter(create_machine(cfg, logic=lg)).start()
            await to_promise(i)
            self.assertEqual(i.context["buf"], "hello")

        asyncio.run(main())

    def test_data_is_item_payload_is_dict_sync(self) -> None:
        seen: List[Any] = []

        def item(i: Any, c: Any, e: Any, a: Any) -> None:
            seen.append((e.data, e.payload))

        i = SyncInterpreter(
            create_machine(
                SCFG,
                logic=slogic(from_iterator(lambda *a: iter(["x"])), item),
            )
        ).start()
        pump(i, lambda: "s.done" in i.current_state_ids)
        self.assertEqual(seen, [("x", {"data": "x"})])
        i.stop()

    def test_persist_round_trip_keeps_stream_shape(self) -> None:
        from src.xstate_statemachine.events import (
            StreamEvent,
            persist_event,
            restore_event,
        )

        ev = StreamEvent("STREAM", {"data": [1, 2]})
        back = restore_event(json.loads(json.dumps(persist_event(ev))))
        self.assertIsInstance(back, StreamEvent)
        self.assertEqual((back.data, back.payload), ([1, 2], {"data": [1, 2]}))
        self.assertEqual(back, ev)

    def test_pending_stream_event_survives_snapshot(self) -> None:
        from src.xstate_statemachine.events import StreamEvent

        cfg = json.loads(json.dumps(SCFG))
        cfg["states"]["a"]["invoke"]["src"] = "idle"
        lg = slogic(None)
        lg.services["idle"] = from_callback(lambda *a: None)
        m = create_machine(cfg, logic=lg)

        async def main() -> str:
            i = Interpreter(m)
            await i.start()
            i._event_queue.put_nowait(StreamEvent("STREAM", {"data": "q"}))
            snap = i.get_snapshot()
            await i.stop()
            return snap

        snap = asyncio.run(main())
        self.assertIn('"stream": true', snap)

        async def restored() -> None:
            r = await Interpreter.from_snapshot(snap, m).start()
            await apump(lambda: r.context["items"] == ["q"])
            await r.stop()

        asyncio.run(restored())
        i = SyncInterpreter.from_snapshot(snap, m).start()
        pump(i, lambda: i.context["items"] == ["q"])
        i.stop()


class TestStatelyCorpus(unittest.TestCase):
    def test_corpus_cleanup_count_matches_setups(self) -> None:
        files = sorted(CORPUS.glob("*.json")) if CORPUS.exists() else []
        tried = 0
        rnd = random.Random(267)
        for f in files:
            try:
                cfg = json.loads(f.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 -- not a machine
                continue
            srcs: set = set()
            _srcs(cfg, srcs)
            if not srcs:
                continue
            evs: set = set()
            _events(cfg, evs)
            cnt = Counting()

            def setup(sb: Any, rc: Any, c: Any, e: Any) -> Any:
                sb("__CORPUS_PING__")
                return cnt(sb, rc, c, e)

            svc = from_callback(setup)
            names: set = set()
            _names(cfg, names)
            try:
                m = create_machine(
                    cfg,
                    logic=MachineLogic(
                        actions={n: (lambda *a: None) for n in names},
                        guards={n: (lambda *a: True) for n in names},
                        services={s: svc for s in srcs},
                    ),
                    strict_targets=False,
                )
                i = SyncInterpreter(m).start()
            except Exception:  # noqa: BLE001 -- unrelated construct
                continue
            tried += 1
            for _ in range(10):
                try:
                    i.send(rnd.choice(sorted(evs) or ["NOPE"]))
                except Exception:  # noqa: BLE001 -- user impls absent
                    pass
            i.stop()
            self.assertEqual(cnt.setups, cnt.cleanups, f.name)
        if files:
            self.assertGreater(tried, 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
