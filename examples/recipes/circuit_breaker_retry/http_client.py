# examples/recipes/circuit_breaker_retry/http_client.py
# -----------------------------------------------------------------------------
# ⚡ A real-shaped HTTP client: retry + backoff inside, breaker around (#308)
# -----------------------------------------------------------------------------
# 🏛️ Layering, outermost first:
#      CircuitBreaker   -- shared by every request to one upstream; fails
#                          fast (no network) while the upstream is sick.
#      RetryPolicy chart -- per request: retry 5xx / timeouts with jittered
#                          backoff, give up after N, never retry a 4xx.
#      Transport        -- `send(method, url) -> (status, body)`; `urllib`
#                          in production, a fake in tests. No new dependency.
#    A breaker rejection is NOT retried by the chart (it would just be
#    rejected again): `CircuitOpenError` is marked non-retryable.
# -----------------------------------------------------------------------------
"""Resilient GET over any transport, driven by `machine.json`."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from xstate_statemachine import (
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from xstate_statemachine.patterns import (
    CircuitBreaker,
    CircuitOpenError,
    RetryPolicy,
)

HERE = Path(__file__).resolve().parent
Transport = Callable[[str, str], Tuple[int, bytes]]


class HTTPStatusError(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status


def urllib_transport(method: str, url: str) -> Tuple[int, bytes]:
    """Production transport: stdlib only, 5 s timeout."""
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _retryable(exc: Any) -> bool:
    if isinstance(exc, CircuitOpenError):
        return False
    if isinstance(exc, HTTPStatusError):
        return exc.status >= 500 or exc.status == 429
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


def build_machine(
    transport: Transport,
    breaker: CircuitBreaker,
    policy: Optional[RetryPolicy] = None,
) -> Any:
    policy = policy or RetryPolicy(max_attempts=4, base_ms=200, max_ms=5_000)

    def http_get(i: Any, ctx: Dict, e: Any) -> Any:
        def call() -> Any:
            status, body = transport("GET", ctx["url"])
            if status >= 400:
                raise HTTPStatusError(status)
            return json.loads(body)

        return breaker.call(call)  # CircuitOpenError if open

    def store_url(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        ctx["url"] = e.payload["url"]

    def store_result(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        ctx["result"] = e.data

    def store_error(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        ctx["error"] = f"{type(e.error).__name__}: {e.error}"

    logic = MachineLogic(
        services={"httpGet": http_get},
        actions={
            "storeUrl": store_url,
            "storeResult": store_result,
            "storeError": store_error,
        },
        guards={"notRetryable": lambda ctx, e: not _retryable(e.error)},
    ).merge(policy.logic())
    config = json.loads((HERE / "machine.json").read_text("utf-8"))
    return create_machine(config, logic=logic)


def fetch(machine: Any, url: str, clock: Any = None) -> Any:
    """Start one request; returns the running interpreter.

    With a real clock, call ``interp.tick()`` in a loop (or sleep) until
    ``interp.status == "done"``; in tests pass a `SimulatedClock` and
    advance it -- no sleeping.
    """
    interp = SyncInterpreter(machine, clock=clock).start()
    interp.send("GET", url=url)
    return interp
