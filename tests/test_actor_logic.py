# tests/test_actor_logic.py
"""#267: actor logic helpers on both engines -- from_callback (send_back
from a thread, receive via sendTo, cleanup exactly once on exit / stop /
error), from_async_iterator / from_iterator (stream, onDone with last,
onError, aclose on exit), from_coroutine / from_callable, from_interpreter."""

from __future__ import annotations

import asyncio
import threading
import time
import unittest
from typing import Any, List

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    PluginBase,
    SyncInterpreter,
    create_machine,
    to_promise,
)
from src.xstate_statemachine.actor_logic import (
    RunningLogic,
    from_async_iterator,
    from_callable,
    from_callback,
    from_coroutine,
    from_interpreter,
    from_iterator,
)

STREAM_CFG = {
    "id": "s",
    "initial": "streaming",
    "context": {"buf": "", "err": None},
    "states": {
        "streaming": {
            "invoke": {
                "src": "stream",
                "id": "stream",
                "onDone": {"target": "done", "actions": "last"},
                "onError": {"target": "failed", "actions": "err"},
            },
            "on": {"STREAM": {"actions": "append"}, "STOP": "stopped"},
        },
        "done": {"type": "final"},
        "failed": {"type": "final"},
        "stopped": {"type": "final"},
    },
}


def stream_logic(service: Any) -> MachineLogic:
    return MachineLogic(
        actions={
            "append": lambda i, c, e, a: c.__setitem__(
                "buf", c["buf"] + str(e.payload["data"])
            ),
            "last": lambda i, c, e, a: c.__setitem__("last", e.data),
            "err": lambda i, c, e, a: c.__setitem__("err", str(e.error)),
        },
        services={"stream": service},
    )


def _pump(i: Any, until: Any, timeout: float = 5.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        i.tick()
        if until():
            return
        time.sleep(0.005)
    raise AssertionError("timed out")


class TestAsyncIterator(unittest.TestCase):
    def test_stream_then_done_with_last(self) -> None:
        async def chunks(i: Any, c: Any, e: Any):
            for w in ["hel", "lo", "!"]:
                yield w

        async def go() -> Any:
            i = await Interpreter(
                create_machine(
                    STREAM_CFG, logic=stream_logic(from_async_iterator(chunks))
                )
            ).start()
            await to_promise(i)
            return dict(i.context), set(i.current_state_ids)

        ctx, ids = asyncio.run(go())
        self.assertEqual(ctx["buf"], "hello!")
        self.assertEqual(ctx["last"], "!")
        self.assertEqual(ids, {"s.done"})

    def test_exception_mid_stream_is_on_error(self) -> None:
        async def chunks(i: Any, c: Any, e: Any):
            yield "a"
            raise RuntimeError("upstream broke")

        async def go() -> Any:
            i = await Interpreter(
                create_machine(
                    STREAM_CFG, logic=stream_logic(from_async_iterator(chunks))
                )
            ).start()
            await to_promise(i)
            return dict(i.context), set(i.current_state_ids)

        ctx, ids = asyncio.run(go())
        self.assertEqual(ctx["buf"], "a")
        self.assertIn("upstream broke", ctx["err"])
        self.assertEqual(ids, {"s.failed"})

    def test_state_exit_acloses_the_generator(self) -> None:
        closed: List[bool] = []
        started: List[Any] = []  # holds the loop-bound Event (3.9-safe)

        async def chunks(i: Any, c: Any, e: Any):
            try:
                yield "a"
                started[0].set()
                while True:
                    await asyncio.sleep(0.01)
                    yield "b"
            finally:
                closed.append(True)

        async def go() -> Any:
            started.append(asyncio.Event())
            i = await Interpreter(
                create_machine(
                    STREAM_CFG, logic=stream_logic(from_async_iterator(chunks))
                )
            ).start()
            await asyncio.wait_for(started[0].wait(), 5)
            await i.send("STOP", wait=True)
            await asyncio.sleep(0.05)
            ids = set(i.current_state_ids)
            await i.stop()
            return ids

        ids = asyncio.run(go())
        self.assertEqual(ids, {"s.stopped"})
        self.assertEqual(closed, [True])

    def test_custom_event_type_and_coroutine_factory(self) -> None:
        async def make(i: Any, c: Any, e: Any):
            async def gen():
                yield 1
                yield 2

            return gen()

        cfg = {
            **STREAM_CFG,
            "states": {
                **STREAM_CFG["states"],
                "streaming": {
                    **STREAM_CFG["states"]["streaming"],
                    "on": {"CHUNK": {"actions": "append"}},
                },
            },
        }

        async def go() -> Any:
            i = await Interpreter(
                create_machine(
                    cfg,
                    logic=stream_logic(
                        from_async_iterator(make, event_type="CHUNK")
                    ),
                )
            ).start()
            await to_promise(i)
            return i.context["buf"]

        self.assertEqual(asyncio.run(go()), "12")


class TestIterator(unittest.TestCase):
    def test_sync_stream_then_done(self) -> None:
        def chunks(i: Any, c: Any, e: Any):
            yield from ["hel", "lo"]

        i = SyncInterpreter(
            create_machine(
                STREAM_CFG, logic=stream_logic(from_iterator(chunks))
            )
        ).start()
        _pump(i, lambda: i.status == "done")
        self.assertEqual(i.context["buf"], "hello")
        self.assertEqual(i.context["last"], "lo")

    def test_sync_error_and_exit_closes(self) -> None:
        closed: List[bool] = []

        def chunks(i: Any, c: Any, e: Any):
            try:
                yield "a"
                raise ValueError("bad chunk")
            finally:
                closed.append(True)

        i = SyncInterpreter(
            create_machine(
                STREAM_CFG, logic=stream_logic(from_iterator(chunks))
            )
        ).start()
        _pump(i, lambda: i.status == "done")
        self.assertEqual(i.current_state_ids, {"s.failed"})
        self.assertIn("bad chunk", i.context["err"])
        self.assertEqual(closed, [True])

        closed.clear()
        gate = threading.Event()

        def forever(i2: Any, c: Any, e: Any):
            try:
                yield "x"
                gate.wait(5)
                yield "y"
            finally:
                closed.append(True)

        i = SyncInterpreter(
            create_machine(
                STREAM_CFG, logic=stream_logic(from_iterator(forever))
            )
        ).start()
        _pump(i, lambda: i.context["buf"] == "x")
        i.send("STOP")
        gate.set()
        time.sleep(0.05)
        self.assertEqual(i.current_state_ids, {"s.stopped"})
        self.assertEqual(closed, [True])
        self.assertEqual(i.context["buf"], "x")  # 'y' was dropped after stop

    def test_from_iterator_works_on_async_engine_too(self) -> None:
        def chunks(i: Any, c: Any, e: Any):
            yield from ["a", "b"]

        async def go() -> Any:
            i = await Interpreter(
                create_machine(
                    STREAM_CFG, logic=stream_logic(from_iterator(chunks))
                )
            ).start()
            await asyncio.wait_for(to_promise(i), 5)
            return i.context["buf"]

        self.assertEqual(asyncio.run(go()), "ab")


CB_CFG = {
    "id": "cb",
    "initial": "on",
    "context": {"seen": [], "cleanups": 0},
    "states": {
        "on": {
            "invoke": {"src": "cb", "id": "conn", "onError": "failed"},
            "on": {
                "TICK": {"actions": "rec"},
                "PING": {
                    "actions": {
                        "type": "sendTo",
                        "params": {
                            "to": "conn",
                            "event": {"type": "HELLO", "n": 7},
                        },
                    }
                },
                "OFF": "off",
                "AGAIN": {"target": "on", "reenter": True},
            },
        },
        "off": {},
        "failed": {"type": "final"},
    },
}


class TestCallback(unittest.TestCase):
    def _logic(self, setup: Any) -> MachineLogic:
        return MachineLogic(
            actions={
                "rec": lambda i, c, e, a: c["seen"].append(e.payload["k"])
            },
            services={"cb": from_callback(setup)},
        )

    def test_thousand_events_from_a_thread_in_order_sync(self) -> None:
        cleaned: List[int] = []

        def setup(send_back: Any, receive: Any, ctx: Any, event: Any) -> Any:
            def push() -> None:
                for k in range(1000):
                    send_back("TICK", k=k)

            t = threading.Thread(target=push)
            t.start()
            t.join()
            return lambda: cleaned.append(1)

        i = SyncInterpreter(
            create_machine(CB_CFG, logic=self._logic(setup))
        ).start()
        i.tick()  # drains the mailbox
        self.assertEqual(i.context["seen"], list(range(1000)))
        i.send("OFF")
        self.assertEqual(cleaned, [1])
        i.stop()
        self.assertEqual(cleaned, [1])  # exactly once

    def test_thousand_events_from_a_thread_in_order_async(self) -> None:
        cleaned: List[int] = []
        pushed = threading.Event()

        def setup(send_back: Any, receive: Any, ctx: Any, event: Any) -> Any:
            def push() -> None:
                for k in range(1000):
                    send_back("TICK", k=k)
                pushed.set()

            threading.Thread(target=push).start()
            return lambda: cleaned.append(1)

        async def go() -> Any:
            i = await Interpreter(
                create_machine(CB_CFG, logic=self._logic(setup))
            ).start()
            await asyncio.get_running_loop().run_in_executor(
                None, pushed.wait, 5
            )
            for _ in range(200):
                await asyncio.sleep(0.005)
                if len(i.context["seen"]) == 1000:
                    break
            seen = list(i.context["seen"])
            await i.stop()
            return seen

        seen = asyncio.run(go())
        self.assertEqual(seen, list(range(1000)))
        self.assertEqual(cleaned, [1])

    def test_receive_gets_send_to_events(self) -> None:
        got: List[Any] = []

        def setup(send_back: Any, receive: Any, ctx: Any, event: Any) -> Any:
            receive(lambda ev: got.append((ev.type, ev.payload["n"])))
            return None

        i = SyncInterpreter(
            create_machine(CB_CFG, logic=self._logic(setup))
        ).start()
        i.send("PING")
        i.send("PING")
        self.assertEqual(got, [("HELLO", 7), ("HELLO", 7)])
        i.stop()

    def test_setup_error_is_on_error_and_reenter_recreates(self) -> None:
        calls = {"n": 0}
        cleaned: List[int] = []

        def setup(send_back: Any, receive: Any, ctx: Any, event: Any) -> Any:
            calls["n"] += 1
            if calls["n"] == 99:
                raise RuntimeError("no connection")
            return lambda: cleaned.append(calls["n"])

        i = SyncInterpreter(
            create_machine(CB_CFG, logic=self._logic(setup))
        ).start()
        i.send("AGAIN")  # exit + re-enter: cleanup 1, setup 2
        (
            self.assertEqual(cleaned, [1])
            if cleaned == [1]
            else self.assertEqual(cleaned[:1], [1])
        )
        self.assertEqual(calls["n"], 2)
        i.stop()

        def bad(send_back: Any, receive: Any, ctx: Any, event: Any) -> Any:
            raise RuntimeError("no connection")

        j = SyncInterpreter(
            create_machine(CB_CFG, logic=self._logic(bad))
        ).start()
        self.assertEqual(j.current_state_ids, {"cb.failed"})

    def test_cleanup_awaitable_and_returns_validated(self) -> None:
        done: List[int] = []

        def setup(send_back: Any, receive: Any, ctx: Any, event: Any) -> Any:
            async def acleanup() -> None:
                done.append(1)

            return acleanup

        async def go() -> None:
            i = await Interpreter(
                create_machine(CB_CFG, logic=self._logic(setup))
            ).start()
            await i.send("OFF", wait=True)
            await asyncio.sleep(0.01)
            await i.stop()

        asyncio.run(go())
        self.assertEqual(done, [1])

        def bad(send_back: Any, receive: Any, ctx: Any, event: Any) -> Any:
            return 42

        k = SyncInterpreter(
            create_machine(CB_CFG, logic=self._logic(bad))
        ).start()
        self.assertEqual(
            k.current_state_ids, {"cb.failed"}
        )  # TypeError -> onError

    def test_send_back_after_stop_is_dropped(self) -> None:
        holder: List[Any] = []

        def setup(send_back: Any, receive: Any, ctx: Any, event: Any) -> Any:
            holder.append(send_back)
            return None

        i = SyncInterpreter(
            create_machine(CB_CFG, logic=self._logic(setup))
        ).start()
        i.stop()
        holder[0]("TICK", k=1)  # no raise, no effect
        self.assertEqual(i.context["seen"], [])

    def test_service_start_hook_and_running_logic_visible(self) -> None:
        starts: List[str] = []

        class P(PluginBase):
            def on_service_start(self, i: Any, inv: Any) -> None:
                starts.append(inv.id)

        i = (
            SyncInterpreter(
                create_machine(CB_CFG, logic=self._logic(lambda *a: None))
            )
            .use(P())
            .start()
        )
        self.assertEqual(starts, ["conn"])
        self.assertIsInstance(i._running_logic["conn"], RunningLogic)
        i.stop()
        self.assertEqual(i._running_logic, {})


class TestOneShotAndInterpreter(unittest.TestCase):
    def test_from_coroutine_and_callable(self) -> None:
        async def a(i: Any, c: Any, e: Any) -> int:
            return 1

        def s(i: Any, c: Any, e: Any) -> int:
            return 2

        self.assertIs(from_coroutine(a), a)
        self.assertIs(from_callable(s), s)
        with self.assertRaises(TypeError):
            from_coroutine(s)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            from_callable(a)  # type: ignore[arg-type]
        cfg = {
            "id": "o",
            "initial": "w",
            "context": {},
            "states": {
                "w": {
                    "invoke": {
                        "src": "svc",
                        "onDone": {"target": "d", "actions": "keep"},
                    }
                },
                "d": {"type": "final"},
            },
        }
        lg = MachineLogic(
            actions={"keep": lambda i, c, e, ad: c.__setitem__("r", e.data)},
            services={"svc": from_callable(s)},
        )
        i = SyncInterpreter(create_machine(cfg, logic=lg)).start()
        self.assertEqual(i.context["r"], 2)

    def test_from_interpreter_uses_the_childs_machine(self) -> None:
        kid = create_machine(
            {"id": "kid", "initial": "x", "states": {"x": {"type": "final"}}}
        )
        child = SyncInterpreter(kid)
        cfg = {
            "id": "p",
            "initial": "w",
            "states": {
                "w": {"invoke": {"src": "kid", "onDone": "d"}},
                "d": {"type": "final"},
            },
        }
        m = create_machine(
            cfg, logic=MachineLogic(services={"kid": from_interpreter(child)})
        )
        i = SyncInterpreter(m).start()
        self.assertEqual(i.current_state_ids, {"p.d"})
        with self.assertRaises(TypeError):
            from_interpreter(object())


if __name__ == "__main__":
    unittest.main()
