"""battle #274 (adversary A): InspectorPlugin / protocol / SseSink."""

from __future__ import annotations

import asyncio
import http.client
import json
import threading
import time

import pytest

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.inspect import (
    InspectorPlugin,
    MemorySink,
    SseSink,
)
from src.xstate_statemachine.inspect import plugin as plugin_mod
from src.xstate_statemachine.inspect.protocol import actor_message

PINGER = {
    "id": "kid",
    "initial": "a",
    "states": {
        "a": {
            "entry": {
                "type": "sendParent",
                "params": {"event": {"type": "PING"}},
            }
        }
    },
}


def _two_pingers():
    cfg = {
        "id": "p",
        "initial": "run",
        "states": {
            "run": {
                "type": "parallel",
                "states": {
                    "x": {"invoke": {"id": "c1", "src": "k1"}},
                    "y": {"invoke": {"id": "c2", "src": "k2"}},
                },
                "on": {"PING": {}},
            }
        },
    }
    return create_machine(
        cfg,
        logic=MachineLogic(
            services={
                "k1": create_machine(dict(PINGER)),
                "k2": create_machine(dict(PINGER)),
            }
        ),
    )


def _check_root_consistency(messages):
    """Every message's rootId is the sessionId of an actor with no parent."""
    roots = {
        m["sessionId"]
        for m in messages
        if m["type"] == "@xstate.actor" and "parentId" not in m
    }
    actors = {m["sessionId"] for m in messages if m["type"] == "@xstate.actor"}
    for m in messages:
        assert m["rootId"] in roots, m
        assert m["sessionId"] in actors, m
        if "parentId" in m:
            assert m["parentId"] in actors, m


# -- 1/2: identity and source attribution ----------------------------------
class TestAttribution:
    def test_same_type_from_two_children_attributed_per_sender(self):
        sink = MemorySink()
        pl = InspectorPlugin(sink).install()
        try:
            i = SyncInterpreter(_two_pingers()).start()
            i.stop()
        finally:
            pl.uninstall()
        pings = [
            m["sourceId"]
            for m in sink.messages
            if m["type"] == "@xstate.event" and m["event"]["type"] == "PING"
        ]
        assert sorted(pings) == ["p:c1", "p:c2"]
        _check_root_consistency(sink.messages)
        assert pl._sent == {}

    def test_async_engine_parity(self):
        async def run():
            sink = MemorySink()
            pl = InspectorPlugin(sink).install()
            try:
                i = await Interpreter(_two_pingers()).start()
                await asyncio.sleep(0.2)
                await i.stop()
            finally:
                pl.uninstall()
            return sink.messages

        msgs = asyncio.run(run())
        pings = sorted(
            m["sourceId"]
            for m in msgs
            if m["type"] == "@xstate.event" and m["event"]["type"] == "PING"
        )
        assert pings == ["p:c1", "p:c2"]
        _check_root_consistency(msgs)

    def test_persisted_parent_children_rerooted(self):
        sink = MemorySink()
        pl = InspectorPlugin(sink).install()
        try:
            i = SyncInterpreter(_two_pingers())
            i.store_key = "order-42"
            i.start()
            i.stop()
        finally:
            pl.uninstall()
        sids = {m["sessionId"] for m in sink.messages}
        assert sids == {"order-42", "order-42:c1", "order-42:c2"}
        pings = sorted(
            m["sourceId"]
            for m in sink.messages
            if m["type"] == "@xstate.event" and m["event"]["type"] == "PING"
        )
        assert pings == ["order-42:c1", "order-42:c2"]
        _check_root_consistency(sink.messages)

    def test_unreceived_sends_do_not_grow_without_bound(self):
        pl = InspectorPlugin(MemorySink())
        ev = type("E", (), {"type": "X"})()
        src = type("S", (), {"id": "s", "parent": None})()
        for n in range(plugin_mod._MAX_TARGETS * 5):
            pl.on_event_sent(src, f"gone-{n}", ev)
        assert len(pl._sent) == plugin_mod._MAX_TARGETS
        # newest kept, oldest evicted
        assert f"gone-{plugin_mod._MAX_TARGETS * 5 - 1}" in pl._sent
        assert "gone-0" not in pl._sent


# -- 3: protocol -----------------------------------------------------------
class TestProtocol:
    def test_non_json_definition_values_do_not_leak_repr(self):
        class Secret:
            def __repr__(self):
                return "sk_live_SECRET"

            __str__ = __repr__

        msg = actor_message(
            session_id="s",
            name="n",
            root_id="s",
            parent_id=None,
            definition={"id": "n", "meta": {"x": Secret(), "b": b"\x00"}},
            snapshot={},
        )
        assert "SECRET" not in msg["definition"]
        assert "[Secret]" in msg["definition"]
        assert "[bytes]" in msg["definition"]


# -- 4: SseSink security ---------------------------------------------------
class TestHost:
    @pytest.mark.parametrize(
        "host",
        [
            "127.0.0.1.evil.com",
            "127.0.0.1.evil.com:8765",
            "127.evil.com",
            "localhost.evil.com",
            "[::1]x",
            "[::1]:abc",
            "127.0.0.1:x",
            "evil.com",
            "",
        ],
    )
    def test_rebinding_hosts_refused(self, host):
        s = SseSink()
        try:
            assert not s.host_ok(host)
        finally:
            s.close()

    @pytest.mark.parametrize(
        "host",
        [
            "127.0.0.1",
            "127.0.0.1:8765",
            "127.5.6.7:1",
            "localhost:9",
            "LOCALHOST",
            "[::1]:8765",
            "[::1]",
        ],
    )
    def test_loopback_hosts_accepted(self, host):
        s = SseSink()
        try:
            assert s.host_ok(host)
        finally:
            s.close()

    def test_rebinding_host_gets_421_over_the_wire(self):
        with SseSink() as s:
            c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=5)
            c.putrequest("GET", "/messages", skip_host=True)
            c.putheader("Host", f"127.0.0.1.evil.com:{s.port}")
            c.putheader("Authorization", f"Bearer {s.token}")
            c.endheaders()
            assert c.getresponse().status == 421


class TestSseMisc:
    def _get(self, s, path, **headers):
        c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=5)
        c.request("GET", path, headers=headers)
        r = c.getresponse()
        return r.status, r.getheader("Set-Cookie"), r.read()

    def test_wrong_first_load_token_sets_no_cookie(self):
        with SseSink() as s:
            status, cookie, _ = self._get(s, "/?token=nope")
            assert status == 401 and cookie is None

    def test_messages_and_odd_paths_need_token(self):
        with SseSink() as s:
            s.send({"type": "@xstate.event"})
            for path in ("/messages", "//events", "/events/../messages"):
                assert self._get(s, path)[0] == 401
            assert self._get(s, "/", Origin="null")[0] == 403

    def test_huge_authorization_header_refused_cleanly(self):
        with SseSink() as s:
            status = self._get(
                s, "/messages", Authorization="Bearer " + "x" * 60_000
            )[0]
            assert status in (400, 401, 431)

    def test_keepalive_is_injectable_and_close_does_not_hang(self):
        with pytest.raises(ValueError):
            SseSink(keepalive=0)
        s = SseSink(keepalive=0.05).start()
        c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=5)
        c.request(
            "GET", "/events", headers={"Authorization": f"Bearer {s.token}"}
        )
        r = c.getresponse()
        assert r.status == 200
        assert b"keep-alive" in r.fp.readline()
        t0 = time.monotonic()
        s.close()
        assert time.monotonic() - t0 < 3
        s.send({"type": "late"})  # after close: no error
        assert s.clients == []

    def test_many_clients_connect_and_disconnect_while_sending(self):
        with SseSink(keepalive=0.05, max_queue=200) as s:
            stop = threading.Event()

            def produce():
                while not stop.is_set():
                    s.send({"type": "@xstate.event"})
                    time.sleep(0.001)

            prod = threading.Thread(target=produce)
            prod.start()
            conns = []
            for _ in range(50):
                c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=5)
                c.request(
                    "GET",
                    "/events",
                    headers={"Authorization": f"Bearer {s.token}"},
                )
                r = c.getresponse()
                assert r.status == 200
                r.fp.readline()
                conns.append((c, r))
            for c, r in conns:
                r.close()  # the response holds the socket open
                c.close()
            stop.set()
            prod.join()
            deadline = time.monotonic() + 20
            while s.clients and time.monotonic() < deadline:
                s.send({"type": "x"})  # writes surface the broken pipes
                time.sleep(0.02)
            assert s.clients == []


# -- 5: bounds -------------------------------------------------------------
def test_100k_messages_without_clients_stay_bounded():
    s = SseSink(history=1000)
    try:
        for n in range(100_000):
            s.send({"n": n})
        assert len(s.messages) == 1000 and s.sent == 100_000
        assert s.messages[-1] == {"n": 99_999}
    finally:
        s.close()


def test_frames_are_json():
    s = SseSink()
    try:
        s.send({"a": object()})
        json.dumps(s.messages, default=str)
    finally:
        s.close()
