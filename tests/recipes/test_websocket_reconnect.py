# tests/recipes/test_websocket_reconnect.py
"""WebSocket reconnect: a fake client, seeded RetryPolicy jitter, both
engines on a SimulatedClock."""

from __future__ import annotations

import random
from typing import Any, List

import pytest

from .conftest import Driver, load_recipe

ws = load_recipe("websocket_reconnect", "ws_reconnect")


class FakeServer:
    """Decides whether the next connect() succeeds; tracks live sockets."""

    def __init__(self) -> None:
        self.fail_next = 0
        self.connects = 0
        self.live: List["FakeClient"] = []

    def factory(self) -> "FakeClient":
        return FakeClient(self)


class FakeClient:
    def __init__(self, server: FakeServer) -> None:
        self.server = server
        self.on_message: Any = None
        self.on_close: Any = None
        self.closed = False

    def connect(self) -> None:
        self.server.connects += 1
        if self.server.fail_next:
            self.server.fail_next -= 1
            raise ConnectionRefusedError("server down")
        self.server.live.append(self)

    def close(self) -> None:
        self.closed = True
        if self in self.server.live:
            self.server.live.remove(self)

    # -- server-side pushes --
    def push(self, msg: Any) -> None:
        self.on_message(msg)

    def drop(self) -> None:
        self.server.live.remove(self)
        self.on_close(1006)


def policy(seed: int = 7) -> Any:
    from xstate_statemachine.patterns import RetryPolicy

    return RetryPolicy(
        max_attempts=3,
        base_ms=1000,
        factor=2,
        jitter="full",
        rng=random.Random(seed).random,
    )


@pytest.fixture(params=["sync", "async"])
def sock(request: Any) -> Any:
    server = FakeServer()
    got: List[Any] = []
    d = Driver(
        request.param,
        ws.build_machine(server.factory, policy(), on_message=got.append),
    )
    d.server, d.got = server, got  # type: ignore[attr-defined]
    yield d
    d.close()


def settle(d: Driver) -> None:
    """Let callback-delivered events drain (they are queued sends)."""
    d.wait(0)


def test_connect_receive_and_disconnect(sock: Driver) -> None:
    sock.send("CONNECT")
    settle(sock)
    assert sock.value == "connected" and len(sock.server.live) == 1
    sock.run(lambda: sock.server.live[0].push("hello"))
    settle(sock)
    assert sock.got == ["hello"] and sock.i.context["received"] == 1
    client = sock.server.live[0]
    sock.send("DISCONNECT")
    assert sock.value == "disconnected"
    assert client.closed  # from_callback cleanup ran


def test_drop_reconnects_after_jittered_backoff(sock: Driver) -> None:
    sock.send("CONNECT")
    settle(sock)
    sock.run(lambda: sock.server.live[0].drop())
    settle(sock)
    assert sock.value == "reconnecting"
    assert sock.i.context["attempt"] == 1
    expected_ms = policy().delay_ms(1)  # same seed, same jitter
    assert 0 <= expected_ms <= 1000
    sock.wait(expected_ms - 1)
    assert sock.value == "reconnecting"
    sock.wait(1)
    settle(sock)
    assert sock.value == "connected"
    assert sock.i.context["attempt"] == 0  # reset on success
    assert sock.server.connects == 2


def test_gives_up_after_max_attempts(sock: Driver) -> None:
    sock.server.fail_next = 99
    sock.send("CONNECT")
    for _ in range(5):
        sock.wait(4_000)  # beyond any backoff for 3 attempts
    assert sock.value == "failed"
    assert sock.server.connects == 3  # max_attempts, not one more
    sock.server.fail_next = 0
    sock.send("CONNECT")
    settle(sock)
    assert sock.value == "connected"


def test_disconnect_while_backing_off_cancels_the_retry(sock: Driver) -> None:
    sock.server.fail_next = 1
    sock.send("CONNECT")
    assert sock.value == "reconnecting"
    sock.send("DISCONNECT")
    sock.wait(60_000)
    assert sock.value == "disconnected" and sock.server.connects == 1


def test_jitter_spreads_clients() -> None:
    """Why jitter: ten clients dropped together do not retry together."""
    from xstate_statemachine.patterns import RetryPolicy

    rng = random.Random(1).random
    p = RetryPolicy(base_ms=1000, jitter="full", rng=rng)
    delays = {round(p.delay_ms(1)) for _ in range(10)}
    assert len(delays) == 10 and all(0 <= d <= 1000 for d in delays)
