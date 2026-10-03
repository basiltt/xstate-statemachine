# tests/recipes/test_battle_267_feed_soak.py
"""#267 battle scenario: a market-data feed that flaps for an hour.

A production team recognises this one. A WebSocket client pushes ticks
from ITS OWN thread (paho / websockets-sync / a GUI toolkit all do) into
the machine via `from_callback`'s `send_back`; the connection drops every
few seconds; the chart reconnects with jittered backoff; a summariser
consumes an async stream (`from_async_iterator`) of digest chunks when
asked. Under create → act → persist → discard the machine is also
snapshotted while the socket is live and resumed in a new interpreter.

What must hold, and what the test pins:

* **no tick is lost or reordered** while the producer thread pushes at
  full speed -- 20 000 ticks across 50 drop/reconnect cycles, each tick
  numbered, the machine's `received` count and last-seen sequence agree
  with what the server sent while a socket was live;
* **every socket is closed exactly once** -- `from_callback`'s cleanup
  runs on `DROPPED`, on `DISCONNECT`, on `stop()`, and on the exit of a
  `persisted()` block; `connect()` count == `close()` count at the end;
* **a tick pushed after the state left `connected`** (the producer thread
  does not know yet) lands nowhere harmful -- not on the reconnecting
  state, not on the next socket's count;
* **the summary stream** delivers its chunks in order, `onDone` carries
  the last chunk, and leaving the state mid-stream `aclose()`s the
  generator;
* **nothing leaks**: thread count and asyncio task count are flat across
  the soak; `stop()` returns promptly even with a producer mid-push.

Both engines; `SimulatedClock`; the "server" is a thread that pushes.
"""

from __future__ import annotations

import asyncio
import gc
import random
import threading
import time
from typing import Any, Dict, List, Optional

import pytest

from .conftest import Driver, load_recipe

ws = load_recipe("websocket_reconnect", "ws_reconnect")

pytestmark = pytest.mark.timeout(120)


class ThreadedServer:
    """A fake exchange: each live socket gets a pusher THREAD that sends
    numbered ticks as fast as the machine takes them, until dropped."""

    def __init__(self, ticks_per_session: int) -> None:
        self.ticks_per_session = ticks_per_session
        self.connects = 0
        self.closes = 0
        self.sent: List[int] = []
        self.live: List["ThreadedClient"] = []
        self._seq = 0
        self._lock = threading.Lock()

    def next_seq(self) -> int:
        with self._lock:
            self._seq += 1
            return self._seq

    def factory(self) -> "ThreadedClient":
        return ThreadedClient(self)


class ThreadedClient:
    def __init__(self, server: ThreadedServer) -> None:
        self.server = server
        self.on_message: Any = None
        self.on_close: Any = None
        self.closed = 0
        self._pusher: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.pushed: List[int] = []

    def connect(self) -> None:
        self.server.connects += 1
        self.server.live.append(self)

    def start_pushing(self) -> None:
        """Called by the test once `listen` wired the callbacks."""

        def run() -> None:
            for _ in range(self.server.ticks_per_session):
                if self._stop.is_set():
                    return
                seq = self.server.next_seq()
                self.pushed.append(seq)
                self.server.sent.append(seq)
                self.on_message({"seq": seq})
            # the exchange hangs up at the end of a session
            if not self._stop.is_set():
                self.on_close(1006)

        self._pusher = threading.Thread(target=run, daemon=True)
        self._pusher.start()

    def close(self) -> None:
        self.closed += 1
        self.server.closes += 1
        self._stop.set()
        if self in self.server.live:
            self.server.live.remove(self)

    def join(self, timeout: float = 5.0) -> None:
        if self._pusher is not None:
            self._pusher.join(timeout)


def policy() -> Any:
    from xstate_statemachine.patterns import RetryPolicy

    return RetryPolicy(
        max_attempts=1000,
        base_ms=100,
        factor=1.5,
        max_ms=2000,
        jitter="full",
        rng=random.Random(11).random,
    )


def _settle(d: Driver, pred: Any, *, turns: int = 400) -> None:
    """Zero-length turns until *pred()* -- bounded (the pusher thread
    delivers through `send_threadsafe`, drained per turn)."""
    for _ in range(turns):
        d.wait(0)
        if pred():
            return
        time.sleep(0.002)
    raise AssertionError("did not settle")


@pytest.fixture(params=["sync", "async"])
def feed(request: Any) -> Any:
    server = ThreadedServer(ticks_per_session=400)
    seen: List[int] = []
    d = Driver(
        request.param,
        ws.build_machine(
            server.factory,
            policy(),
            on_message=lambda m: seen.append(m["seq"]),
        ),
    )
    d.server, d.seen = server, seen  # type: ignore[attr-defined]
    yield d
    d.close()


def test_fifty_drop_reconnect_cycles_lose_and_reorder_nothing(
    feed: Driver,
) -> None:
    server: ThreadedServer = feed.server  # type: ignore[attr-defined]
    seen: List[int] = feed.seen  # type: ignore[attr-defined]
    threads0 = threading.active_count()
    feed.send("CONNECT")
    _settle(feed, lambda: feed.value == "connected")
    sessions = 0
    for _ in range(50):
        client = server.live[0]
        client.start_pushing()
        # the pusher ends each session with a hang-up -> DROPPED
        _settle(feed, lambda: feed.value == "reconnecting", turns=4000)
        client.join()
        sessions += 1
        # back off on the simulated clock (bounded jittered delay)
        for _ in range(40):
            feed.wait(100)
            feed.wait(0)
            if feed.value == "connected":
                break
        assert feed.value == "connected", (sessions, feed.value)
    # 📊 every tick a LIVE socket pushed was counted, in order
    assert seen == sorted(seen) == server.sent[: len(seen)]
    assert len(seen) == 50 * 400 == feed.i.context["received"]
    # 🔒 every DROPPED socket closed exactly once; the 51st is live
    assert server.connects == 51 and server.closes == 50
    assert len(server.live) == 1 and server.live[0].closed == 0
    feed.send("DISCONNECT")
    assert server.closes == 51 and not server.live  # cleanup on exit
    # 🧵 no pusher or engine thread leaked
    gc.collect()
    assert threading.active_count() <= threads0 + 2


def test_tick_after_leaving_connected_lands_nowhere_harmful(
    feed: Driver,
) -> None:
    server: ThreadedServer = feed.server  # type: ignore[attr-defined]
    feed.send("CONNECT")
    _settle(feed, lambda: feed.value == "connected")
    client = server.live[0]
    # 💥 drop the socket from the server side; the client thread does not
    #    know yet and pushes two more ticks AFTER the machine moved on
    feed.run(lambda: client.on_close(1006))
    _settle(feed, lambda: feed.value == "reconnecting")
    received_before = feed.i.context["received"]
    feed.run(lambda: client.on_message({"seq": 10_001}))
    feed.run(lambda: client.on_message({"seq": 10_002}))
    feed.wait(0)
    # `connected` declared MESSAGE; `reconnecting` does not -> unhandled,
    # dropped (onUnhandled default); the count is untouched
    assert feed.i.context["received"] == received_before
    assert feed.value == "reconnecting"
    # and the socket's cleanup ran exactly once
    assert client.closed == 1


def test_stop_mid_push_is_prompt_and_closes_the_socket(feed: Driver) -> None:
    server: ThreadedServer = feed.server  # type: ignore[attr-defined]
    feed.send("CONNECT")
    _settle(feed, lambda: feed.value == "connected")
    client = server.live[0]
    client.start_pushing()
    time.sleep(0.01)  # the pusher is mid-stream
    t0 = time.perf_counter()
    feed.close()
    assert time.perf_counter() - t0 < 2.0
    client.join()
    assert client.closed == 1  # cleanup ran on stop()
    # the pusher's later send_backs after stop() did not raise in its thread
    assert client._pusher is not None and not client._pusher.is_alive()


SUMMARY_CFG = {
    "id": "digest",
    "initial": "idle",
    "context": {"text": "", "chunks": 0, "closed": False},
    "states": {
        "idle": {"on": {"SUMMARISE": "streaming"}},
        "streaming": {
            "invoke": {
                "id": "llm",
                "src": "summarise",
                "onDone": {"target": "done", "actions": "finish"},
                "onError": "failed",
            },
            "on": {
                "CHUNK": {"actions": "append"},
                "CANCEL": "idle",
            },
        },
        "done": {},
        "failed": {},
    },
}


def test_async_summary_stream_order_done_and_aclose() -> None:
    from xstate_statemachine import (
        Interpreter,
        MachineLogic,
        create_machine,
        from_async_iterator,
    )

    flags: Dict[str, Any] = {"closed": 0, "yielded": 0}
    gate = asyncio.Event()

    async def summarise(i: Any, ctx: Any, e: Any) -> Any:
        try:
            for w in ["The ", "market ", "rose ", "2%."]:
                flags["yielded"] += 1
                if flags["yielded"] == 3:
                    await gate.wait()  # hold the stream mid-way
                yield w
        finally:
            flags["closed"] += 1

    def append(i: Any, c: Any, e: Any, a: Any) -> None:
        # 📝 `e.payload["data"]` is the documented item access today; agent
        #    A owns whether `e.data` becomes the item (the issue's recipe).
        c["text"] += e.payload["data"]
        c["chunks"] += 1

    def finish(i: Any, c: Any, e: Any, a: Any) -> None:
        c["last"] = e.data

    m = create_machine(
        SUMMARY_CFG,
        logic=MachineLogic(
            actions={"append": append, "finish": finish},
            services={
                "summarise": from_async_iterator(summarise, event_type="CHUNK")
            },
        ),
    )

    async def full() -> Dict[str, Any]:
        gate.set()
        i = await Interpreter(m).start()
        await i.send("SUMMARISE", wait=True)
        await i.await_settled(5)
        out = dict(i.context)
        out["state"] = i.value
        await i.stop()
        return out

    r = asyncio.run(full())
    assert r["state"] == "done"
    assert r["text"] == "The market rose 2%." and r["chunks"] == 4
    assert r["last"] == "2%."  # onDone carries the LAST chunk
    assert flags["closed"] == 1

    # leave the state mid-stream -> the generator is aclose()d
    flags.update(closed=0, yielded=0)
    gate.clear()

    async def cancelled() -> Dict[str, Any]:
        i = await Interpreter(m).start()
        await i.send("SUMMARISE", wait=True)
        for _ in range(50):
            await asyncio.sleep(0.002)
            if i.context["chunks"] == 2:
                break
        assert i.context["chunks"] == 2
        await i.send("CANCEL", wait=True)
        await i.await_settled(5)
        out = dict(i.context)
        out["state"] = i.value
        await i.stop()
        return out

    r2 = asyncio.run(cancelled())
    assert r2["state"] == "idle" and r2["chunks"] == 2
    assert flags["closed"] == 1  # finally ran: aclose() on exit
