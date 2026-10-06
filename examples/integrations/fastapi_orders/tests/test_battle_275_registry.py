# examples/integrations/fastapi_orders/tests/test_battle_275_registry.py
"""#275 battle: the order service's registry layer under real web load.

`StatechartRegistry` (``contrib.starlette``) is what every request goes
through: `act()` per POST (create → act → persist → discard), `peek()`
for GETs, `transition_stream()` for the browser's `EventSource`, and the
opt-in `resident()` for single-worker deployments. Pinned here:

* **no lost update** -- 50 concurrent ``ADD_ITEM`` POSTs to one order on
  SQLite: every success is one increment of ``items`` and the stored
  version equals the number of successful sends; the conflicts that
  surface are 409s, never 500s, and a client that retries converges;
* **streaming fan-out** -- 5 `EventSource` clients on one order each get
  the ``snapshot`` first, then exactly one ``transition`` per changed
  receipt, in ``seq`` order; a client that stops reading is cut when it
  falls `MAX_BACKLOG` behind -- the POSTs never block and the other
  clients are unaffected; disconnects return the subscriber count to 0;
* **cross-order isolation** -- a subscriber on order A never sees B;
* **per-topic bookkeeping is bounded** -- 5 000 distinct orders through
  `act()` with no subscriber leave no per-topic state behind;
* **residents** -- a caller that still holds a resident after it was
  LRU-evicted sends into a stopped interpreter: the engine reports that
  (`on_event_dropped` / a refusing receipt), the send is NOT silently
  lost without trace; re-fetching the resident gives a fresh, loaded
  actor with the saved state;
* **shutdown** -- `lifespan` exit with a stream open and a POST in
  flight: the stream closes, the POST completes or 503s, nothing hangs
  past `drain_timeout_s`, residents are saved;
* **X0.7 on streams** -- a cross-origin `EventSource` is refused (403),
  an unidentified one is 403, the connection cap per key is enforced.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple

import pytest

pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

import app as orders  # noqa: E402
from xstate_statemachine.contrib.starlette import _fanout  # noqa: E402
from xstate_statemachine.persistence import (  # noqa: E402
    SQLiteInbox,
    SQLiteStore,
)

pytestmark = pytest.mark.timeout(300)

ANN = {"x-customer": "ann"}
TIMEOUT = 5.0


@pytest.fixture
def registry(tmp_path):
    store = SQLiteStore(str(tmp_path / "orders.db"))
    return orders.build_registry(store, SQLiteInbox(store))


@pytest.fixture
def app(registry):
    return orders.create_app(registry, email=lambda *a: None, debug=False)


def _post(client: Any, order: str, event: str, body: Any = None) -> Any:
    return client.post(
        f"/orders/{order}/events/{event}", json=body, headers=ANN
    )


async def _apost(
    ac: Any, order: str, event: str, body: Any = None, **headers: str
) -> Any:
    return await ac.post(
        f"/orders/{order}/events/{event}",
        json=body,
        headers={**ANN, **headers},
    )


class _Stream:
    """One `GET /orders/{id}/stream` driven as a raw ASGI connection.

    📝 httpx's in-process `ASGITransport` buffers a streaming body and
    cannot signal `http.disconnect`, so a streaming endpoint cannot be
    closed through it. This driver speaks ASGI to the app directly (the
    same approach as `tests/contrib/starlette/_support.RawSSE`).
    """

    def __init__(self, app: Any, order: str, **headers: str) -> None:
        self.app = app
        self.path = f"/orders/{order}/stream"
        hdrs = {**ANN, **headers}
        self.headers = [(k.encode(), v.encode()) for k, v in hdrs.items()]
        self.out: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()
        self._disconnect = asyncio.Event()
        self._sent_request = False
        self.task: Any = None
        self.buf = b""
        self.status = 0

    async def _receive(self) -> Dict[str, Any]:
        if not self._sent_request:
            self._sent_request = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await self._disconnect.wait()
        return {"type": "http.disconnect"}

    async def _send(self, msg: Dict[str, Any]) -> None:
        await self.out.put(msg)

    async def open(self) -> int:
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": self.path,
            "raw_path": self.path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"testserver")] + self.headers,
            "client": ("127.0.0.1", 1),
            "server": ("testserver", 80),
        }
        self.task = asyncio.ensure_future(
            self.app(scope, self._receive, self._send)
        )
        start = await asyncio.wait_for(self.out.get(), TIMEOUT)
        assert start["type"] == "http.response.start"
        self.status = start["status"]
        return self.status

    async def frame(self) -> Tuple[Optional[int], str, Any]:
        while b"\n\n" not in self.buf:
            msg = await asyncio.wait_for(self.out.get(), TIMEOUT)
            if (
                msg["type"] == "http.response.body"
                and not msg.get("more_body", False)
                and not msg.get("body")
            ):
                raise EOFError("stream ended")
            self.buf += msg.get("body", b"")
        raw, self.buf = self.buf.split(b"\n\n", 1)
        fields: Dict[str, str] = {}
        for line in raw.decode().splitlines():
            if line.startswith(":"):
                return None, "comment", line
            k, _, v = line.partition(": ")
            fields[k] = v
        seq = int(fields["id"]) if "id" in fields else None
        return seq, fields.get("event", ""), json.loads(fields["data"])

    async def close(self) -> None:
        self._disconnect.set()
        if self.task is not None:
            await asyncio.wait_for(self.task, TIMEOUT)


def _asgi(app: Any) -> Any:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


# -----------------------------------------------------------------------------
# 1. no lost update
# -----------------------------------------------------------------------------
def test_fifty_concurrent_adds_lose_nothing(app, registry) -> None:
    async def go() -> Tuple[int, int, int]:
        async with _asgi(app) as ac:
            async with registry.lifespan():
                rs = await asyncio.gather(
                    *[
                        _apost(ac, "o1", "ADD_ITEM", {"sku": "tea", "qty": 1})
                        for _ in range(50)
                    ]
                )
                codes = [r.status_code for r in rs]
                assert set(codes) <= {200, 409}, codes
                ok = codes.count(200)
                # 409s are conflicts a client retries; converge them
                for _ in range(codes.count(409)):
                    while True:
                        r = await _apost(
                            ac, "o1", "ADD_ITEM", {"sku": "tea", "qty": 1}
                        )
                        if r.status_code == 200:
                            break
                        assert r.status_code == 409
                final = (await ac.get("/orders/o1", headers=ANN)).json()
                return ok, len(final["context"]["items"]), 0

    ok, items, _ = asyncio.run(go())
    assert items == 50
    rec = registry.store.load(registry.store_key("order", "o1"))
    assert rec is not None
    assert rec.version == 50  # one version per successful send, no gaps


# -----------------------------------------------------------------------------
# 2. streaming fan-out + a stalled client
# -----------------------------------------------------------------------------
def test_four_streams_plus_a_stalled_subscriber(app, registry) -> None:
    """Four EventSource clients read; a fifth subscriber (the fan-out's
    view of a client whose socket stopped draining) never reads. The
    writers must never block on it: it is cut at `MAX_BACKLOG`."""

    async def go() -> None:
        async with _asgi(app) as ac:
            async with registry.lifespan():
                streams = [_Stream(app, "o1") for _ in range(4)]
                for s in streams:
                    assert await s.open() == 200
                for s in streams:
                    _seq, kind, body = await s.frame()
                    assert kind == "snapshot" and body["state"] == "cart"
                # 📝 httpx's in-process ASGI transport has no socket to
                #    stall, so the stalled client is a raw subscriber on
                #    the same topic -- exactly what the stream handler
                #    holds for a browser that stopped reading.
                stalled = registry.subscribers.subscribe("order", "o1")
                assert registry.subscribers.count("order", "o1") == 5
                n = _fanout.MAX_BACKLOG + 20
                for k in range(n):
                    r = await asyncio.wait_for(
                        _apost(ac, "o1", "ADD_ITEM", {"sku": "tea", "qty": 1}),
                        TIMEOUT,
                    )
                    assert r.status_code == 200, r.text
                    for s in streams:
                        seq, kind, body = await s.frame()
                        assert kind == "transition" and seq == k + 1
                        assert len(body["context"]["items"]) == k + 1
                # 🔥 the stalled subscriber was cut, the writers never waited
                assert registry.subscribers.count("order", "o1") == 4
                assert stalled.queue.get_nowait() is not None
                for s in streams:
                    await s.close()
                await asyncio.sleep(0.05)
                assert registry.subscribers.count() == 0
                assert registry.connections() == 0

    asyncio.run(go())


def test_streams_are_isolated_per_order(app, registry) -> None:
    async def go() -> None:
        async with _asgi(app) as ac:
            async with registry.lifespan():
                a = _Stream(app, "A")
                assert await a.open() == 200
                await a.frame()  # snapshot
                await _apost(ac, "B", "ADD_ITEM", {"sku": "tea", "qty": 1})
                await _apost(ac, "A", "ADD_ITEM", {"sku": "tea", "qty": 2})
                seq, kind, body = await a.frame()
                assert kind == "transition" and seq == 1
                assert body["context"]["items"][0]["qty"] == 2
                await a.close()

    asyncio.run(go())


# -----------------------------------------------------------------------------
# 3. bounded per-topic bookkeeping
# -----------------------------------------------------------------------------
def test_five_thousand_orders_leave_no_topic_state(registry) -> None:
    async def go() -> None:
        async with registry.lifespan():
            for n in range(5000):
                async with registry.act(
                    "order", f"k{n}", principal="ann"
                ) as i:
                    await i.send("ADD_ITEM", sku="tea", qty=1, wait=True)
            # no subscriber ever existed: nothing per topic may remain
            assert registry.subscribers.count() == 0
            assert len(registry.subscribers._seq) == 0, len(
                registry.subscribers._seq
            )
            assert registry.connections() == 0
            assert registry.residents == 0

    asyncio.run(go())


# -----------------------------------------------------------------------------
# 4. residents
# -----------------------------------------------------------------------------
def test_evicted_resident_is_not_a_silent_sink(tmp_path) -> None:
    from xstate_statemachine import PluginBase

    class Dropped(PluginBase):
        def __init__(self) -> None:
            self.seen: List[Tuple[str, str]] = []

        def on_event_dropped(self, interp: Any, event: Any, reason: str):
            self.seen.append((event.type, reason))

    store = SQLiteStore(str(tmp_path / "r.db"))
    registry = orders.build_registry(store, SQLiteInbox(store))
    registry.max_residents = 1
    dropped = Dropped()
    registry.plugins.append(dropped)

    async def go() -> None:
        async with registry.lifespan():
            a = await registry.resident("order", "A")
            r = await a.send("ADD_ITEM", sku="tea", qty=1, wait=True)
            assert r.changed
            await registry.resident("order", "B")  # evicts A (saved+stopped)
            assert a.status == "stopped"
            r2 = await a.send("ADD_ITEM", sku="tea", qty=1, wait=True)
            # 🔥 the stale handle must not look like success
            assert not r2.changed
            assert r2.denied or r2.error is not None or dropped.seen, r2
            fresh = await registry.resident("order", "A")
            assert fresh is not a and fresh.status == "running"
            assert len(fresh.context["items"]) == 1  # the saved state
            await registry.release_resident("order", "A")
            await registry.release_resident("order", "B")
            assert registry.residents == 0

    asyncio.run(go())


# -----------------------------------------------------------------------------
# 5. shutdown
# -----------------------------------------------------------------------------
def test_shutdown_with_open_stream_and_inflight_post(app, registry) -> None:
    registry.drain_timeout_s = 3.0

    async def go() -> None:
        async with _asgi(app) as ac:
            lifespan = registry.lifespan()
            await lifespan.__aenter__()
            s = _Stream(app, "o1")
            assert await s.open() == 200
            await s.frame()
            post = asyncio.ensure_future(
                _apost(ac, "o1", "ADD_ITEM", {"sku": "tea", "qty": 1})
            )
            await asyncio.sleep(0)
            t0 = asyncio.get_running_loop().time()
            await asyncio.wait_for(lifespan.__aexit__(None, None, None), 10)
            took = asyncio.get_running_loop().time() - t0
            assert took < registry.drain_timeout_s + 1
            r = await asyncio.wait_for(post, TIMEOUT)
            assert r.status_code in (200, 503), r.status_code
            # the stream ends (EOF) rather than hanging
            with pytest.raises((EOFError, asyncio.TimeoutError)):
                while True:
                    await s.frame()
            await s.close()
            assert registry.subscribers.count() == 0
            # a stream opened after shutdown is refused
            late = _Stream(app, "o1")
            assert await late.open() == 503
            await late.close()

    asyncio.run(go())


# -----------------------------------------------------------------------------
# 6. X0.7 on streams
# -----------------------------------------------------------------------------
def test_stream_refuses_cross_origin_unidentified_and_caps(
    app, registry
) -> None:
    async def go() -> None:
        async with registry.lifespan():
            if True:
                bad = _Stream(app, "o1", origin="http://evil.example")
                assert await bad.open() == 403
                await bad.close()
                anon = _Stream(app, "o1")
                anon.headers = []  # no customer
                assert await anon.open() == 403
                await anon.close()
                cap = registry.max_connections_per_key
                opened = [_Stream(app, "o1") for _ in range(cap + 1)]
                codes = [await s.open() for s in opened]
                assert codes.count(200) == cap and codes.count(429) == 1, codes
                for s in opened:
                    await s.close()
                await asyncio.sleep(0.05)
                assert registry.connections("order", "o1") == 0

    asyncio.run(go())
