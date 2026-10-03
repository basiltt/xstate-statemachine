"""#267 battle (agent A, part 2): from_async_iterator / from_iterator --
stream order under load, `StreamEvent` shape (`e.data` is the item), leaks,
the Stately corpus.  Part 1 (`test_battle_267_actor_logic.py`) covers
`from_callback` delivery, cleanup and `receive()`."""

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
from typing import Any, List

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    PluginBase,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.actor_logic import (
    from_async_iterator,
    from_callback,
    from_iterator,
)
from .test_battle_267_actor_logic import CFG, Counting, apump, logic, pump

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
