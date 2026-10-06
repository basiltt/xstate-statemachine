# examples/integrations/eda_fulfilment/tests/test_battle_274_inspector.py
"""#274 battle: the fulfilment team watches the pipeline live.

An `InspectorPlugin` is attached to every interpreter the choreography
router builds; the `SseSink` streams to a browser; a `JsonLinesSink`
records sessions for post-mortems. An engineer looking at the Stately
Inspector must see ONE actor per order, not one actor named "order"
that every order's snapshots are written into. Pinned:

* **one session per instance** -- 20 orders through the router give 20
  distinct order sessions (the persisted `store_key` is the identity),
  each with its own actor registration, and the warehouse sessions are
  distinct too; replaying a recording per session reproduces each
  order's final state;
* **X0.7 hygiene** -- with `context_allowlist=("orderId", "total",
  "trackingId")` nothing else leaves (`failure` with a card number in
  it never appears); payloads are redacted; the `definition`'s initial
  context is filtered the same way;
* **stalled browser** -- an SSE client that never reads must not grow
  the process without bound: the per-client queue is bounded, the
  machine never blocks on it, the client is disconnected and
  `dropped` is counted; a client that reads keeps receiving;
* **sink outage** -- a sink that raises never reaches the machine;
  orders ship; the failure is reported once, not once per message;
* **recording** -- `JsonLinesSink` written at 0600, every line a
  protocol message, `replay_messages` into a fresh sink yields the same
  messages; a recording truncated mid-line is skipped, not fatal;
* **the SSE endpoint under load** -- 3 readers over one sink, 300 orders:
  every reader sees every message in order, `/messages` matches the
  history cap, no handler thread leaks after close;
* **threads** -- 8 router threads over one sink: no interleaved frames,
  the message count equals the per-thread sum.
"""

from __future__ import annotations

import http.client
import json
import os
import stat
import sys
import threading
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List

import pytest

import app

from xstate_statemachine.inspect import (
    InspectorPlugin,
    JsonLinesSink,
    MemorySink,
    SseSink,
    read_jsonl,
    replay_messages,
)

pytestmark = pytest.mark.timeout(300)


def _place(a: Any, oid: str, total: int = 10) -> None:
    a.command(oid, "PAY", orderId=oid, total=total)


def _inspector(fulfilment: Any) -> Any:
    return next(
        p
        for p in fulfilment.instruments.plugins
        if isinstance(p, InspectorPlugin)
    )


def _by_session(msgs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for m in msgs:
        out[m["sessionId"]].append(m)
    return out


# -----------------------------------------------------------------------------
# 1. one session per instance
# -----------------------------------------------------------------------------
def test_twenty_orders_are_twenty_sessions(fulfilment: Any) -> None:
    ids = [f"o-{n:02d}" for n in range(20)]
    for oid in ids:
        _place(fulfilment, oid, total=5)
    fulfilment.pump()
    msgs = fulfilment.instruments.inspector.messages
    sessions = _by_session(msgs)
    order_sessions = {
        s for s, ms in sessions.items() if ms[0]["name"] == "order"
    }
    # 🔥 one actor per ORDER, keyed by the persisted instance key
    assert len(order_sessions) == 20, sorted(order_sessions)[:5]
    for sid in order_sessions:
        actor = [m for m in sessions[sid] if m["type"] == "@xstate.actor"]
        assert len(actor) >= 1
        last = [m for m in sessions[sid] if m["type"] == "@xstate.snapshot"][
            -1
        ]
        assert last["snapshot"]["value"] == "shipped", (sid, last)
        assert last["snapshot"]["status"] == "done"
    warehouse_sessions = {
        s for s, ms in sessions.items() if ms[0]["name"] == "warehouse"
    }
    assert len(warehouse_sessions) == 20
    assert order_sessions.isdisjoint(warehouse_sessions)


# -----------------------------------------------------------------------------
# 2. X0.7 hygiene
# -----------------------------------------------------------------------------
def test_only_allow_listed_context_leaves(fulfilment: Any) -> None:
    _place(fulfilment, "o-1", total=10)
    fulfilment.command(
        "o-2", "PAYMENT_FAILED", reason="card 4111-1111 declined"
    )
    fulfilment.pump()
    blob = json.dumps(fulfilment.instruments.inspector.messages)
    assert "4111" not in blob
    assert '"failure"' not in blob
    for m in fulfilment.instruments.inspector.messages:
        ctx = (m.get("snapshot") or {}).get("context") or {}
        assert set(ctx) <= {"orderId", "total", "trackingId"}, ctx
        if m["type"] == "@xstate.actor":
            definition = json.loads(m["definition"])
            assert set(definition.get("context", {})) <= {
                "orderId",
                "total",
                "trackingId",
            }


# -----------------------------------------------------------------------------
# 3. stalled browser
# -----------------------------------------------------------------------------
def _connect(sink: SseSink) -> http.client.HTTPResponse:
    c = http.client.HTTPConnection("127.0.0.1", sink.port, timeout=10)
    c.request(
        "GET",
        "/events",
        headers={"Authorization": f"Bearer {sink.token}", "Host": "127.0.0.1"},
    )
    r = c.getresponse()
    assert r.status == 200
    r._xsm_conn = c  # type: ignore[attr-defined]
    return r


def _read_frames(resp: Any, n: int, deadline: float = 20.0) -> List[Dict]:
    out: List[Dict[str, Any]] = []
    end = time.monotonic() + deadline
    buf = b""
    while len(out) < n and time.monotonic() < end:
        chunk = resp.fp.readline()
        if not chunk:
            break
        buf += chunk
        if chunk == b"\n":
            for line in buf.decode().splitlines():
                if line.startswith("data: "):
                    out.append(json.loads(line[6:]))
            buf = b""
    return out


def test_stalled_sse_client_is_bounded_and_dropped() -> None:
    from xstate_statemachine import SyncInterpreter

    sink = SseSink(port=0, history=50).start()
    try:
        stalled = _connect(sink)
        reader = _connect(sink)
        m = app.order_machine()
        plug = InspectorPlugin(sink, context_allowlist=("orderId",))
        t0 = time.perf_counter()
        for n in range(3000):
            i = SyncInterpreter(m).use(plug).start()
            i.send("PAY", orderId=f"o-{n}", total=1)
            i.stop()
        assert time.perf_counter() - t0 < 30
        # 🔥 the stalled client's queue is BOUNDED and it was disconnected;
        #    the machine never waited on it
        assert sink.dropped > 0
        assert sink.max_queue >= sink.dropped
        assert len(sink.clients) <= 2
        # the reader still gets a live frame
        i = SyncInterpreter(m).use(plug).start()
        i.send("PAY", orderId="o-last", total=1)
        i.stop()
        frames = _read_frames(reader, 1, deadline=10)
        assert frames, "reader starved"
        stalled._xsm_conn.close()  # type: ignore[attr-defined]
        reader._xsm_conn.close()  # type: ignore[attr-defined]
    finally:
        sink.close()


# -----------------------------------------------------------------------------
# 4. sink outage
# -----------------------------------------------------------------------------
def test_raising_sink_is_contained_and_reported_once(tmp_path: Any) -> None:
    import logging

    class Down:
        def __init__(self) -> None:
            self.calls = 0

        def send(self, message: Dict[str, Any]) -> None:
            self.calls += 1
            raise ConnectionError("inspector UI unreachable")

    class Capture(logging.Handler):
        def __init__(self) -> None:
            super().__init__(logging.WARNING)
            self.records: List[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    cap = Capture()
    root = logging.getLogger("xstate_statemachine")
    root.addHandler(cap)
    down = Down()
    a = app.build_app("fake", tmp_path, celery=False)
    try:
        a.router.dispatcher.plugins.append(InspectorPlugin(down))
        for n in range(5):
            _place(a, f"o-{n}")
        a.pump()
        for n in range(5):
            assert a.state_of(f"order:o-{n}") == ["order.shipped"]
    finally:
        root.removeHandler(cap)
        a.close()
    assert down.calls >= 1
    warned = [r for r in cap.records if "inspector sink" in r.getMessage()]
    assert len(warned) == 1, [r.getMessage() for r in cap.records][:5]
    contained = [r for r in cap.records if "contained" in r.getMessage()]
    assert contained == [], [r.getMessage() for r in contained][:3]


# -----------------------------------------------------------------------------
# 5. recording
# -----------------------------------------------------------------------------
def test_recording_is_private_replayable_and_tolerates_truncation(
    tmp_path: Any,
) -> None:
    path = tmp_path / "session.jsonl"
    a = app.build_app("fake", tmp_path / "w", celery=False)
    try:
        with JsonLinesSink(path) as rec:
            a.router.dispatcher.plugins.append(
                InspectorPlugin(
                    rec, context_allowlist=("orderId", "total", "trackingId")
                )
            )
            for n in range(3):
                _place(a, f"o-{n}", total=n + 1)
            a.pump()
    finally:
        a.close()
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    recorded = list(read_jsonl(path))
    assert recorded and all(m["type"].startswith("@xstate.") for m in recorded)
    copy = MemorySink()
    assert replay_messages(str(path), copy) == len(recorded)
    assert copy.messages == recorded
    finals = {
        m["sessionId"]: m["snapshot"]["value"]
        for m in recorded
        if m["type"] == "@xstate.snapshot"
    }
    assert Counter(finals.values()) == {"shipped": 3, "packed": 3}
    # a crash mid-write leaves a truncated last line: skipped, not fatal
    raw = path.read_bytes()
    (tmp_path / "trunc.jsonl").write_bytes(raw[: len(raw) - 40])
    partial = list(read_jsonl(tmp_path / "trunc.jsonl"))
    assert len(partial) == len(recorded) - 1


# -----------------------------------------------------------------------------
# 6. the SSE endpoint under load
# -----------------------------------------------------------------------------
def test_three_readers_see_every_message_in_order(tmp_path: Any) -> None:
    sink = SseSink(port=0, history=200).start()
    a = app.build_app("fake", tmp_path, celery=False)
    readers = [_connect(sink) for _ in range(3)]
    try:
        a.router.dispatcher.plugins.append(
            InspectorPlugin(sink, context_allowlist=("orderId",))
        )
        for n in range(300):
            _place(a, f"o-{n:03d}", total=1)
        a.pump()
        total = sink.sent
        assert total > 300 * 6
        got = [_read_frames(r, total, deadline=60) for r in readers]
        for frames in got:
            assert len(frames) == total, (len(frames), total)
        assert got[0] == got[1] == got[2]
        # the JSON view is the capped history
        c = http.client.HTTPConnection("127.0.0.1", sink.port, timeout=10)
        c.request(
            "GET",
            "/messages",
            headers={
                "Authorization": f"Bearer {sink.token}",
                "Host": "127.0.0.1",
            },
        )
        body = json.loads(c.getresponse().read())
        c.close()
        assert len(body) == 200 and body == got[0][-200:]
    finally:
        for r in readers:
            r._xsm_conn.close()  # type: ignore[attr-defined]
        a.close()
        before = threading.active_count()
        sink.close()
        time.sleep(0.3)
        assert threading.active_count() <= before
        assert sink.clients == []


# -----------------------------------------------------------------------------
# 7. threads
# -----------------------------------------------------------------------------
def test_eight_router_threads_over_one_sink(tmp_path: Any) -> None:
    sink = MemorySink()
    plug = InspectorPlugin(sink, context_allowlist=("orderId",))
    apps = []
    for t in range(8):
        a = app.build_app("fake", tmp_path / f"w{t}", celery=False)
        a.router.dispatcher.plugins.append(plug)
        apps.append(a)
    errors: List[BaseException] = []
    barrier = threading.Barrier(8)

    def work(t: int) -> None:
        try:
            barrier.wait(10)
            for k in range(10):
                _place(apps[t], f"t{t}-{k}")
            apps[t].pump()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    ths = [threading.Thread(target=work, args=(t,)) for t in range(8)]
    for th in ths:
        th.start()
    for th in ths:
        th.join(60)
    try:
        assert errors == []
        sessions = _by_session(sink.messages)
        orders = [s for s, ms in sessions.items() if ms[0]["name"] == "order"]
        assert len(orders) == 80
        for sid in orders:
            kinds = [m["type"] for m in sessions[sid]]
            assert kinds[0] == "@xstate.actor"
            assert kinds[-1] == "@xstate.snapshot"
    finally:
        for a in apps:
            a.close()
