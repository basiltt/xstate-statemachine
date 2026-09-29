# tests/recipes/test_circuit_breaker_retry.py
"""Circuit breaker & retry recipe over a fake HTTP transport."""

from __future__ import annotations

import json
import random
from typing import Any, List, Tuple

import pytest

from .conftest import load_recipe

hc = load_recipe("circuit_breaker_retry", "http_client")
URL = "https://quotes.example/v1/eurusd"


class FakeTransport:
    """Replays a script of responses; an Exception instance is raised."""

    def __init__(self, *script: Any) -> None:
        self.script: List[Any] = list(script)
        self.calls: List[Tuple[str, str]] = []

    def __call__(self, method: str, url: str) -> Tuple[int, bytes]:
        self.calls.append((method, url))
        step = self.script.pop(0) if self.script else (200, b'{"px": 1}')
        if isinstance(step, BaseException):
            raise step
        return step


@pytest.fixture
def env() -> Any:
    from xstate_statemachine import SimulatedClock
    from xstate_statemachine.patterns import CircuitBreaker, RetryPolicy

    clock = SimulatedClock()
    breaker = CircuitBreaker(
        failure_threshold=3, cooldown_ms=10_000, clock=clock
    )
    policy = RetryPolicy(
        max_attempts=3, base_ms=100, jitter="full", rng=random.Random(3).random
    )
    return clock, breaker, policy


def run(env: Any, transport: FakeTransport) -> Any:
    clock, breaker, policy = env
    m = hc.build_machine(transport, breaker, policy)
    i = hc.fetch(m, URL, clock=clock)
    for _ in range(10):
        clock.increment(1_000)  # > any backoff here
    return i


def test_503_then_success_is_retried(env: Any) -> None:
    t = FakeTransport((503, b""), (200, b'{"px": 1.08}'))
    i = run(env, t)
    assert i.value == "succeeded" and i.context["result"] == {"px": 1.08}
    assert len(t.calls) == 2 and t.calls[0] == ("GET", URL)


def test_timeout_is_retried(env: Any) -> None:
    t = FakeTransport(TimeoutError("read timed out"), (200, b"{}"))
    assert run(env, t).value == "succeeded"


def test_404_is_final_not_retried(env: Any) -> None:
    t = FakeTransport((404, b""))
    i = run(env, t)
    assert i.value == "failed" and len(t.calls) == 1
    assert i.context["error"] == "HTTPStatusError: HTTP 404"


def test_429_is_retried(env: Any) -> None:
    t = FakeTransport((429, b""), (200, b"{}"))
    assert run(env, t).value == "succeeded"


def test_gives_up_after_max_attempts(env: Any) -> None:
    t = FakeTransport(*[(500, b"")] * 10)
    i = run(env, t)
    assert i.value == "failed" and len(t.calls) == 3
    assert i.has_tag("dead-letter")


def test_breaker_opens_and_later_requests_fail_fast(env: Any) -> None:
    clock, breaker, _ = env
    down = FakeTransport(*[(503, b"")] * 3)
    run(env, down)  # 3 failures -> breaker trips
    assert breaker.state == "open"
    probe = FakeTransport()
    i = hc.fetch(hc.build_machine(probe, breaker, env[2]), URL, clock=clock)
    assert i.value == "failed" and probe.calls == []  # upstream untouched
    assert i.context["error"].startswith("CircuitOpenError")


def test_breaker_half_open_probe_recovers(env: Any) -> None:
    clock, breaker, policy = env
    run(env, FakeTransport(*[(503, b"")] * 3))
    clock.increment(10_001)  # cooldown elapses
    ok = FakeTransport((200, b'{"px": 2}'))
    i = hc.fetch(hc.build_machine(ok, breaker, policy), URL, clock=clock)
    assert i.value == "succeeded" and breaker.state == "closed"


def test_urllib_transport_is_stdlib(monkeypatch: Any) -> None:
    import io
    import urllib.error
    import urllib.request

    class Resp(io.BytesIO):
        status = 200

    def fake_urlopen(req: Any, timeout: float) -> Any:
        if req.full_url.endswith("/missing"):
            raise urllib.error.HTTPError(
                req.full_url, 404, "nf", {}, io.BytesIO(b"no")
            )
        assert timeout == 5 and req.get_method() == "GET"
        return Resp(json.dumps({"ok": True}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert hc.urllib_transport("GET", "https://x/y") == (200, b'{"ok": true}')
    assert hc.urllib_transport("GET", "https://x/missing") == (404, b"no")
