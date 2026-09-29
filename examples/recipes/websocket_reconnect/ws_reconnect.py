# examples/recipes/websocket_reconnect/ws_reconnect.py
# -----------------------------------------------------------------------------
# 🔌 WebSocket reconnect: RetryPolicy jitter + a from_callback link (#308)
# -----------------------------------------------------------------------------
# 🏛️ Two pieces of library logic do the heavy lifting:
#    * `RetryPolicy(...).logic()` supplies `retryDelay` (a NAMED delay that
#      computes jittered exponential backoff from ctx["attempt"]),
#      `retryCanRetry`, `retryBump` and `retryReset`. The chart just names
#      them.
#    * `from_callback(listen)` wraps the live socket as an actor that exists
#      exactly while `connected` is active: it forwards messages and the
#      close as events, and its cleanup closes the socket when the state is
#      left for ANY reason (DISCONNECT, DROPPED, the interpreter stopping).
# 💡 `client_factory` is injected, so tests pass a fake; production passes
#    e.g. a `websockets.sync.client.connect`-based adapter with the same
#    three-method shape: connect(), close(), and the on_message / on_close
#    callbacks.
# -----------------------------------------------------------------------------
"""Reconnecting WebSocket client logic for `machine.json`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict

from xstate_statemachine import MachineLogic, create_machine, from_callback
from xstate_statemachine.patterns import RetryPolicy

HERE = Path(__file__).resolve().parent

#: 5 tries, 0.5 s → 1 s → 2 s → 4 s, capped at 30 s, full jitter.
DEFAULT_POLICY = RetryPolicy(
    max_attempts=5, base_ms=500, factor=2, max_ms=30_000, jitter="full"
)


def build_machine(
    client_factory: Callable[[], Any],
    policy: RetryPolicy = DEFAULT_POLICY,
    on_message: Callable[[Any], None] = lambda m: None,
) -> Any:
    holder: Dict[str, Any] = {}

    def open_socket(i: Any, ctx: Dict, e: Any) -> str:
        client = client_factory()
        client.connect()  # raises -> onError -> reconnecting
        holder["client"] = client
        return "open"

    def listen(send_back: Any, receive: Any, ctx: Any, e: Any) -> Any:
        client = holder.pop("client")
        client.on_message = lambda msg: send_back("MESSAGE", data=msg)
        client.on_close = lambda code: send_back("DROPPED", code=code)
        return client.close  # cleanup: runs once, whenever we leave

    def count_message(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        ctx["received"] += 1
        on_message(e.payload.get("data"))

    logic = MachineLogic(
        actions={"countMessage": count_message},
        services={"openSocket": open_socket, "listen": from_callback(listen)},
    ).merge(policy.logic())
    config = json.loads((HERE / "machine.json").read_text("utf-8"))
    return create_machine(config, logic=logic)
